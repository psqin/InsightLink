"""原生人机协作图：持久化补字段与审批，恢复时不重放模型或正式写入。"""

from typing import NotRequired, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from insight_link_agent.agent.conversation.actions import ActionProposal
from insight_link_agent.agent.conversation.hitl import ActionInput, prepare_from_input
from insight_link_agent.integrations.java_client import JavaAPIError


class InteractionState(TypedDict):
    """检查点只保存业务草稿与执行回执，凭据由当前请求重新注入。"""

    user_id: int
    conversation_id: str
    action_input: NotRequired[dict | None]
    proposal: NotRequired[dict | None]
    status: str
    receipt: NotRequired[str]
    error: NotRequired[str]


class ConversationInteraction:
    """模型完成准备后进入原生图中断；后续表单和聊天回复共用 resume。"""

    def __init__(self, checkpointer, reader):
        self.reader = reader
        graph = StateGraph(InteractionState)
        graph.add_node("input", self._input)
        graph.add_node("prepare", self._prepare)
        graph.add_node("approval", self._approval)
        graph.add_conditional_edges(
            START,
            self._route,
            {
                "input": "input",
                "approval": "approval",
                "done": END,
            },
        )
        graph.add_conditional_edges(
            "input",
            self._after_input,
            {
                "prepare": "prepare",
                "done": END,
            },
        )
        graph.add_conditional_edges(
            "prepare",
            self._route,
            {
                "input": "input",
                "approval": "approval",
                "done": END,
            },
        )
        graph.add_edge("approval", END)
        self.graph = graph.compile(checkpointer=checkpointer)

    @staticmethod
    def _config(thread_id: str) -> dict:
        """使用独立命名空间，避免覆盖正式点评和模型图的检查点。"""
        return {"configurable": {"thread_id": thread_id}}

    @staticmethod
    def _route(state: InteractionState) -> str:
        """优先展示已验证的预览，否则等待补字段。"""
        if state.get("proposal"):
            return "approval"
        return "input" if state.get("action_input") else "done"

    @staticmethod
    def _after_input(state: InteractionState) -> str:
        """取消直接结束，补充信息交给重新授权的准备节点。"""
        return "done" if state["status"] == "canceled" else "prepare"

    @staticmethod
    def _input(state: InteractionState) -> dict:
        """节点重入仅重建中断，不创建记录或执行业务操作。"""
        response = interrupt({"type": "input", "action": state["action_input"]})
        if response.get("decision") == "cancel":
            return {"status": "canceled", "action_input": None}
        action = ActionInput.model_validate(response["action"])
        if action.kind != state["action_input"]["kind"]:
            raise ValueError("恢复时不能更换操作类型")
        return {"action_input": action.model_dump(), "status": "preparing"}

    async def _prepare(self, state: InteractionState) -> dict:
        """每次补充后重新读取 Java 权限与目标快照，绝不执行写入。"""
        action = ActionInput.model_validate(state["action_input"])
        if action.missing_fields():
            return {"status": "awaiting_input", "proposal": None}
        try:
            proposal = await prepare_from_input(self.reader, action)
        except (ValueError, JavaAPIError) as exc:
            # 首次校验与图恢复之间若目标变化，重新等待导师修正，不留下卡死的 prepare 节点。
            return {"status": "awaiting_input", "proposal": None, "error": str(exc)}
        return {
            "proposal": proposal.model_dump(),
            "action_input": None,
            "status": "awaiting_approval",
            "error": "",
        }

    @staticmethod
    def _approval(state: InteractionState) -> dict:
        """确认接口完成一次性写入后只传回执；图中不存在正式写工具。"""
        response = interrupt({"type": "approval", "proposal": state["proposal"]})
        decision = response.get("decision")
        if decision not in {"completed", "cancel", "failed"}:
            raise ValueError("审批恢复需要确认接口的执行回执")
        return {
            "status": "canceled" if decision == "cancel" else decision,
            "receipt": str(response.get("receipt", "")),
            "proposal": None,
        }

    async def start(
        self,
        user_id: int,
        conversation_id: str,
        *,
        action: ActionInput | None = None,
        proposal: ActionProposal | None = None,
    ) -> str:
        """为一项待办创建持久图；返回值仅由服务端写入待办记录。"""
        thread_id = f"chat-hitl:{user_id}:{conversation_id}:{uuid4().hex}"
        await self.graph.ainvoke(
            {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "action_input": action.model_dump() if action else None,
                "proposal": proposal.model_dump() if proposal else None,
                "status": "awaiting_approval" if proposal else "awaiting_input",
            },
            self._config(thread_id),
        )
        return thread_id

    async def state(self, thread_id: str, user_id: int, conversation_id: str):
        """检查前缀和持久身份，不能用客户端提供的 thread_id 越权恢复。"""
        if not thread_id.startswith(f"chat-hitl:{user_id}:{conversation_id}:"):
            raise ValueError("无权恢复该对话任务")
        snapshot = await self.graph.aget_state(self._config(thread_id))
        if (
            snapshot.values.get("user_id") != user_id
            or snapshot.values.get("conversation_id") != conversation_id
        ):
            raise ValueError("对话检查点不存在或归属不符")
        return snapshot

    async def resume(
        self,
        thread_id: str,
        user_id: int,
        conversation_id: str,
        response: dict,
    ) -> dict:
        """只恢复当前等待的图；已经结束的任务不能再次恢复。"""
        snapshot = await self.state(thread_id, user_id, conversation_id)
        if not snapshot.next:
            raise ValueError("该对话任务已经处理")
        return await self.graph.ainvoke(
            Command(resume=response), self._config(thread_id)
        )
