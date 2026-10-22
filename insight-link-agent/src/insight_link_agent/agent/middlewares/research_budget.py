"""限制公开检索请求并保留答复额度，防止反复搜索耗尽整个任务。"""

import asyncio
import json

from langchain.agents.middleware import AgentMiddleware, hook_config
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage

from insight_link_agent.agent.state import PublicResearchState


class ResearchBudget(AgentMiddleware):
    """前四次模型调用可取证，后续只答复，网络调用至多八次。"""

    state_schema = PublicResearchState

    def __init__(self, evidence):
        self.evidence = evidence
        # 额度在 after_model 节点预占并随图检查点提交；实例集合只负责阻断同一
        # 批中的重复 ID 与本次恢复的旧调用，不能用它代替持久化计数。
        self._claimed_ids: set[str] = set()
        self._resumed_pending_ids: set[str] = set()
        self._legacy_exhausted = False
        self._tool_lock = asyncio.Lock()

    @staticmethod
    def _ledger(state):
        """检查账本完整性；旧检查点没有预占信息时不能猜测请求从未发出。"""
        count, reserved = (
            state.get("research_tool_calls"),
            state.get("research_tool_reservations"),
        )
        valid = (
            type(count) is int
            and 0 <= count <= 8
            and isinstance(reserved, list)
            and len(reserved) == count
            and all(isinstance(item, str) and item for item in reserved)
            and len(set(reserved)) == count
        )
        return (count, list(reserved)) if valid else (8, [])

    def configure_resume(self, state):
        """恢复旧轮次时禁止再次联网执行未完成 ID，避免取消窗口造成重复计费。

        即使请求尚未离开本机也不退额度，因为检查点不能区分“尚未发出”和
        “供应商已收到但结果尚未保存”。模型可以在剩余额度内使用新 ID 重查。
        """
        pending = set()
        for message in state.get("messages", []):
            if isinstance(message, AIMessage):
                pending.update(
                    call["id"] for call in message.tool_calls if call.get("id")
                )
            elif isinstance(message, ToolMessage):
                pending.discard(message.tool_call_id)
        self._resumed_pending_ids.update(pending)
        count, reserved = self._ledger(state)
        self._legacy_exhausted = count == 8 and not reserved

    def _quota(self, state):
        """旧格式恢复保持整轮耗尽，后续节点会把保守结果写回检查点。"""
        return (8, []) if self._legacy_exhausted else self._ledger(state)

    @hook_config(can_jump_to=["end"])
    def before_model(self, state, runtime):
        """在实际模型节点前提交计数，失败重试也不能无限获得新额度。"""
        count = state.get("research_model_calls", 0)
        if count >= 8:
            return {
                "jump_to": "end",
                "messages": [
                    AIMessage(
                        content=(
                            "本轮公开资料不足以支持可靠结论，检索与答复额度已用尽，请稍后重试。"
                        )
                    )
                ],
            }
        spent, reserved = self._quota(state)
        return {
            "research_model_calls": count + 1,
            "research_tool_calls": spent,
            "research_tool_reservations": reserved,
            "research_allowed_tool_ids": [],
        }

    def after_model(self, state, runtime):
        """工具节点启动前原子预占整批额度；并行请求读取同一已提交账本。

        每个新 ID 最多占一次，已使用或超额的 ID 不会获得执行许可。取消后
        仍保留预占，即使尚无工具结果，也不会把真实请求次数恢复成零。
        """
        spent, reserved = self._quota(state)
        allowed, seen = [], set(reserved)
        message = next(
            (
                item
                for item in reversed(state.get("messages", []))
                if isinstance(item, AIMessage)
            ),
            None,
        )
        if message is not None and state.get("research_model_calls", 0) <= 4:
            for call in message.tool_calls:
                identifier = call.get("id")
                if (
                    call.get("name") in {"web_search", "web_fetch"}
                    and isinstance(identifier, str)
                    and identifier
                    and identifier not in seen
                    and spent < 8
                ):
                    spent += 1
                    reserved.append(identifier)
                    allowed.append(identifier)
                    seen.add(identifier)
        return {
            "research_tool_calls": spent,
            "research_tool_reservations": reserved,
            "research_allowed_tool_ids": allowed,
        }

    async def awrap_model_call(self, request, handler):
        """取证额度耗尽后撤去工具绑定，保留自然语言答复。"""
        spent, _ = self._quota(request.state)
        if request.state.get("research_model_calls", 0) > 4 or spent >= 8:
            request = request.override(
                tools=[],
                tool_choice="none",
                messages=[
                    *request.messages,
                    SystemMessage(
                        content="本轮取证已结束。现在只依据已有工具证据直接答复或修订答复；"
                        "证据不足时如实说明限制。禁止继续调用任何工具，不得编造已经检索或读取的来源。"
                    ),
                ],
            )
        return await handler(request)

    async def awrap_tool_call(self, request, handler):
        """服务端再把关；即使模型忽略工具列表，也不会执行超额网络请求。"""
        async with self._tool_lock:
            identifier = request.tool_call["id"]
            interrupted = identifier in self._resumed_pending_ids
            denied = (
                interrupted
                or self._legacy_exhausted
                or request.state.get("research_model_calls", 0) > 4
                or identifier not in request.state.get("research_allowed_tool_ids", [])
                or identifier in self._claimed_ids
            )
            if not denied:
                self._claimed_ids.add(identifier)
        if denied:
            message = (
                "上次网页读取已中断，未重放原请求；该请求的预占额度仍计入本轮。"
                "如需重新检索，请在剩余额度内发起新的工具调用。"
                if interrupted
                else "本轮取证额度已结束或调用未获执行许可，请依据已有来源回答，并如实说明证据限制。"
            )
            return ToolMessage(
                content=json.dumps(
                    {"ok": False, "message": message}, ensure_ascii=False
                ),
                tool_call_id=request.tool_call["id"],
                status="error",
            )
        return await handler(request)
