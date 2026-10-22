"""请求运行状态与图恢复：只处理检查点、流式结果和失败收口。"""

import asyncio
from dataclasses import dataclass

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.errors import NodeCancelledError

from insight_link_agent.agent.conversation.actions import (
    ActionProposal,
    ExecutionReceipt,
)
from insight_link_agent.agent.conversation.formatting import clean_teacher_answer
from insight_link_agent.agent.conversation.hitl import ActionInput
from insight_link_agent.agent.conversation.models import ReadTools
from insight_link_agent.agent.execution.context import current_execution
from insight_link_agent.agent.observability.progress import (
    SafeProgressCallback,
    current_progress,
)
from insight_link_agent.agent.observability.result import public_result
from insight_link_agent.agent.skills.registry import builtin_files, load_active_files
from insight_link_agent.app.storage.artifact_store import ArtifactStore
from insight_link_agent.integrations.java_client import JavaAPIError
from insight_link_agent.integrations.processes import ResourceCleanupError


@dataclass
class TurnContext:
    """一次请求的依赖、待办和结果容器；不保存Java token。"""

    history: list[dict]
    reader: ReadTools
    pinned_material_id: int | None = None
    proposal_sink: list[ActionProposal] | None = None
    clarification_sink: list[ActionInput] | None = None
    pending_input: ActionInput | None = None
    teacher_user_id: int | None = None
    artifact_store: ArtifactStore | None = None
    artifact_sink: list[dict] | None = None
    memory_tool_sink: list[str] | None = None
    checkpointer: object = None
    conversation_id: str | None = None
    turn_number: int = 1
    harness_sink: list[dict] | None = None
    pending_proposal: ActionProposal | None = None
    draft_generator: object = None
    execution_receipts: list[ExecutionReceipt] | None = None
    control_sink: list | None = None


def _answer_text(messages: list) -> str:
    """只取最终模型答复，不把工具 JSON 或推理过程显示给导师。"""
    for message in reversed(messages):
        if not isinstance(message, AIMessage) or message.tool_calls:
            continue
        content = message.content
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(content, list):
            text = "\n".join(
                str(block.get("text", ""))
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ).strip()
            if text:
                return text
    raise RuntimeError("模型未返回可用内容，请稍后重试")


def finish_result(result, turn) -> str:
    """交付同一个模型的回答；工具失败不再触发第二个模型整轮否决。

    正式业务写入、目标归属、版本冲突和字段合法性在工具/确认接口校验。
    草稿、预览和文件仅来自真实工具回执，模型文本不能生成这些结构。
    """
    if turn.harness_sink is not None:
        turn.harness_sink.append(public_result(result))
    return clean_teacher_answer(_answer_text(result["messages"])[:6000])


async def run_agent(owner, turn, agent, capture, call_limit):
    """恢复同轮节点，加载当前技能；取消沿原生异常传播。"""
    question = turn.history[-1]["content"]
    model_history = turn.history[-12:]
    progress = current_progress()
    skill_store = getattr(owner, "_skill_store", None)
    skill_files = builtin_files()
    if skill_store is not None and turn.teacher_user_id is not None:
        skill_files.update(await load_active_files(skill_store, turn.teacher_user_id))
    graph_config = None
    saved_version = 0
    resume_execution = False
    if turn.checkpointer is not None:
        if turn.teacher_user_id is None or turn.conversation_id is None:
            raise ValueError("持久化聊天需要已验证的导师与会话")
        # 沿用私有业务图thread_id；公开研究独立分支，不混入学业任务恢复。
        graph_config = {
            "configurable": {
                "thread_id": f"chat-model:{turn.teacher_user_id}:{turn.conversation_id}:private"
            }
        }
        snapshot = await agent.aget_state(graph_config)
        # 文件采用增量合并；停用的个人技能与已移除的内置技能均显式删除，防止旧检查点回流。
        skill_files = {
            **{
                path: None
                for path in snapshot.values.get("files", {})
                if path.startswith(("/skills/", "/user-skills/"))
                and path not in skill_files
            },
            **skill_files,
        }
        saved_version = snapshot.values.get("hot_version", 0)
        if saved_version == turn.turn_number:
            if snapshot.values.get("turn_question") != question:
                raise RuntimeError(
                    "上一条任务尚未完成，请重发原消息继续，或输入“取消上次任务”。"
                )
            # 工具循环失败后的重试从最近节点继续，保留已完成工具产生的待办和文件。
            capture.restore(snapshot.values)
            if execution := current_execution():
                execution.restore(capture)
            if not snapshot.next:
                if progress:
                    progress.state(snapshot.values)
                return finish_result(snapshot.values, turn)
            resume_execution = True
    # 最早一次工具结果可能早于首个完整结果检查点；没有同轮图状态时也读取回执。
    if execution := current_execution():
        execution.restore(capture)
    messages = []
    offset = 2 * (turn.turn_number - 1) - (len(model_history) - 1)
    for index, item in enumerate(model_history):
        if item.get("role") not in ("user", "assistant"):
            continue
        version = (offset + index) // 2 + 1
        if graph_config is not None and version <= saved_version:
            continue
        message_type = HumanMessage if item["role"] == "user" else AIMessage
        messages.append(
            message_type(
                content=item["content"],
                id=f"hot:{version}:{item['role']}" if graph_config else None,
            )
        )
    try:
        inputs = {
            "messages": messages,
            "files": skill_files,
            "skills_metadata": None,
            "hot_version": turn.turn_number,
            "harness_turn_number": None,
            "turn_question": question,
            "prepared_actions": [],
            "prepared_inputs": [],
            "produced_artifacts": [],
            "business_tool_names": [],
            "turn_controls": [],
        }
        if resume_execution:
            # 失败恢复仍重读当前导师技能配置，不使用已经停用的虚拟文件副本。
            await agent.aupdate_state(
                graph_config, {"files": skill_files, "skills_metadata": None}
            )
            inputs = None
        # LangGraph递归预算也需同步，否则会先于分页工具预算终止循环。
        invoke_config = {**(graph_config or {}), "recursion_limit": call_limit * 8 + 64}
        if progress:
            stream_config = {
                **(invoke_config or {}),
                "callbacks": [SafeProgressCallback(progress)],
            }
            result = None
            async for state in agent.astream(
                inputs, stream_config, stream_mode="values"
            ):
                result = state
                progress.state(state)
            if result is None:
                raise RuntimeError("未取得图执行结果")
        else:
            result = (
                await agent.ainvoke(inputs, invoke_config)
                if invoke_config is not None
                else await agent.ainvoke(inputs)
            )
    except (ResourceCleanupError, JavaAPIError):
        raise
    except NodeCancelledError as exc:
        # LangGraph 将节点内部的原生取消包装成普通 Exception；还原控制流，
        # 不能交给通用模型错误分支，否则执行管理器无法区分停止与模型故障。
        raise asyncio.CancelledError from exc
    except Exception as exc:
        raise RuntimeError("模型或工具暂时不可用，请稍后重试") from exc
    return finish_result(result, turn)
