"""ERP 式 web_search / web_fetch：与学业业务、历史记忆完全分开的只读图。"""

import asyncio
from datetime import datetime, timedelta, timezone

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage
from langgraph.errors import NodeCancelledError
from langgraph.graph.message import REMOVE_ALL_MESSAGES

from insight_link_agent.agent.middlewares.conversation import ConversationMiddleware
from insight_link_agent.agent.middlewares.research_budget import ResearchBudget
from insight_link_agent.agent.middlewares.turn_results import CaptureTurnResults
from insight_link_agent.agent.observability.evidence import ExecutionEvidence
from insight_link_agent.agent.observability.progress import (
    SafeProgressCallback,
    current_progress,
)
from insight_link_agent.agent.observability.result import public_result
from insight_link_agent.agent.prompts import load_prompt
from insight_link_agent.agent.skills.registry import builtin_root
from insight_link_agent.agent.state import PublicResearchState
from insight_link_agent.agent.tools.web import build_web_tools


def _answer(messages) -> str:
    """只交付最后一次不含工具调用的模型文本。"""
    for message in reversed(messages):
        if not isinstance(message, AIMessage) or message.tool_calls:
            continue
        text = (
            message.content
            if isinstance(message.content, str)
            else "\n".join(
                str(block.get("text", ""))
                for block in message.content
                if isinstance(block, dict) and block.get("type") == "text"
            )
        )
        if text.strip():
            return text.strip()[:6000]
    raise RuntimeError("模型未返回可用内容，请稍后重试")


class PublicResearchAgent:
    """只接收本轮公开问题，不接受业务 reader、历史、回执、记忆或登录 token。

    工具由应用封装的搜索客户端和网页客户端提供，密钥从不拼入系统提示或工具
    描述。图仅装配两个网页工具，没有默认终端、文件系统、专家或业务写入能力。
    """

    def __init__(self, model, search_client, fetch_client):
        self.model = model
        self.search_client, self.fetch_client = search_client, fetch_client

    async def respond(
        self,
        question: str,
        *,
        teacher_user_id=None,
        conversation_id=None,
        turn_number=1,
        checkpointer=None,
        harness_sink=None,
        memory_tool_sink=None,
    ) -> str:
        """独立保存公开上下文以理解追问；同轮恢复检查点，不包含私有图消息。"""
        if not isinstance(question, str) or not question.strip():
            raise ValueError("请提供需要查询的公开问题")
        search_configured = bool(getattr(self.search_client, "configured", False))
        if self.model is None:
            raise RuntimeError("请先配置模型名称和 API Key")
        evidence = ExecutionEvidence()
        names = memory_tool_sink if memory_tool_sink is not None else []
        today = datetime.now(timezone(timedelta(hours=8))).date().isoformat()

        web_tools = build_web_tools(
            search_client=self.search_client,
            fetch_client=self.fetch_client,
            search_configured=search_configured,
            evidence=evidence,
            names=names,
        )

        skill = (
            builtin_root()
            .joinpath("public-research", "SKILL.md")
            .read_text(encoding="utf-8")
        )
        system = (
            load_prompt("public").replace("{today}", today).replace("{skill}", skill)
        )
        capture = CaptureTurnResults(None, None, None, names, evidence)
        budget = ResearchBudget(evidence)
        agent = create_agent(
            model=self.model,
            tools=web_tools,
            system_prompt=system,
            state_schema=PublicResearchState,
            checkpointer=checkpointer,
            name="insight-link-public-research",
            middleware=[
                budget,
                ConversationMiddleware(limit=8),
                capture,
            ],
        )
        graph_config, resume = None, False
        if checkpointer is not None:
            if teacher_user_id is None or conversation_id is None:
                raise ValueError("持久化聊天需要已验证的导师与会话")
            graph_config = {
                "configurable": {
                    "thread_id": f"chat-model:{teacher_user_id}:{conversation_id}:public"
                }
            }
            snapshot = await agent.aget_state(graph_config)
            # 旧搜索实现曾使用同一公开 thread_id，不能把旧工具或答案误当作当前完成结果。
            # 引擎标记不匹配时走下方干净的新输入，保留 thread_id 供执行管理器继续定位。
            if (
                snapshot.values.get("research_engine") == "direct-research-v2"
                and snapshot.values.get("hot_version") == turn_number
            ):
                if snapshot.values.get("turn_question") != question:
                    raise RuntimeError(
                        "上一条任务尚未完成，请重发原消息继续，或输入“取消上次任务”。"
                    )
                capture.restore(snapshot.values)
                if not snapshot.next:
                    if progress := current_progress():
                        progress.state(snapshot.values)
                    return self._finish(snapshot.values, harness_sink)
                budget.configure_resume(snapshot.values)
                resume = True
        previous_engine = (
            snapshot.values.get("research_engine") if graph_config else None
        )
        inputs = (
            None
            if resume
            else {
                "messages": [
                    *(
                        [RemoveMessage(id=REMOVE_ALL_MESSAGES)]
                        if previous_engine != "direct-research-v2"
                        else []
                    ),
                    HumanMessage(content=question),
                ],
                "hot_version": turn_number,
                "harness_turn_number": None,
                "turn_question": question,
                "research_engine": "direct-research-v2",
                "research_model_calls": 0,
                "research_tool_calls": 0,
                "research_tool_reservations": [],
                "research_allowed_tool_ids": [],
                "business_tool_names": [],
                "harness_tools": [],
                "prepared_actions": [],
                "prepared_inputs": [],
                "produced_artifacts": [],
            }
        )
        try:
            # 联网是不可撤回的外部请求，预占额度必须先落库再启动工具节点；
            # 默认 async durability 允许写检查点与下一步并行，进程崩溃时会丢失预占。
            durability = {"durability": "sync"} if checkpointer is not None else {}
            if progress := current_progress():
                result = None
                async for state in agent.astream(
                    inputs,
                    {
                        **(graph_config or {}),
                        "callbacks": [SafeProgressCallback(progress)],
                    },
                    stream_mode="values",
                    **durability,
                ):
                    result = state
                    progress.state(state)
                if result is None:
                    raise RuntimeError("未取得公开检索结果")
            else:
                result = await agent.ainvoke(inputs, graph_config, **durability)
        except NodeCancelledError as exc:
            raise asyncio.CancelledError from exc
        except Exception as exc:
            raise RuntimeError("公开检索模型或工具暂时不可用，请稍后重试") from exc
        return self._finish(result, harness_sink)

    @staticmethod
    def _finish(result, harness_sink):
        """交付公开工具循环的回答和真实进度，不再追加答案复核关卡。"""
        summary = public_result(result)
        if harness_sink is not None:
            harness_sink.append(summary)
        return _answer(result["messages"])
