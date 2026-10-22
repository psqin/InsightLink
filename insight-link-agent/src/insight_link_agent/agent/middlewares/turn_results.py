"""捕获并恢复工具结果，把受控回执同步到模型图的持久状态。"""

import json

from langchain.agents.middleware import AgentMiddleware

from insight_link_agent.agent.conversation.actions import ActionProposal
from insight_link_agent.agent.conversation.hitl import ActionInput
from insight_link_agent.agent.state import ChatAgentState


class CaptureTurnResults(AgentMiddleware):
    """模型再次运行前将本轮工具的待办和文件元数据提交到图状态。"""

    state_schema = ChatAgentState

    def __init__(
        self, proposals, inputs, artifacts, tool_names, evidence=None, controls=None
    ):
        self.proposals = proposals
        self.inputs = inputs
        self.artifacts = artifacts
        self.tool_names = tool_names
        self.evidence = evidence
        self.controls = controls

    def _capture(self) -> dict:
        """复制受控结果；文件本体和工具参数不进入这些附加字段。"""
        return {
            "turn_controls": list(self.controls or []),
            "prepared_actions": [item.model_dump() for item in self.proposals or []],
            "prepared_inputs": [item.model_dump() for item in self.inputs or []],
            "produced_artifacts": list(self.artifacts or []),
            "business_tool_names": list(self.tool_names or []),
            "harness_tools": list(self.evidence.events) if self.evidence else [],
        }

    def restore(self, snapshot: dict) -> None:
        """合并检查点和工具完成回执，补齐“工具已完成、图尚未提交”的取消窗口。

        回执只恢复应用控制的业务结果和元数据，绝不恢复令牌或二进制文件。重复
        调用必须幂等：图检查点、主图与专家回执可能包含相同结果。补字段列表是
        单一当前状态，完整快照中的空列表表示它已被预览替代，不能与旧输入合并
        后把已撤销的表单复活；其他累计结果保序去重。
        """

        def merge(sink, values, parser=lambda item: item, *, replace=False):
            if sink is None:
                return
            combined = ([] if replace else list(sink)) + [
                parser(value) for value in values
            ]
            seen, restored = set(), []
            for value in combined:
                normalized = (
                    value.model_dump() if hasattr(value, "model_dump") else value
                )
                key = json.dumps(
                    normalized, ensure_ascii=False, sort_keys=True, default=str
                )
                if key not in seen:
                    seen.add(key)
                    restored.append(value)
            sink[:] = restored

        merge(self.controls, snapshot.get("turn_controls", []), dict)
        merge(
            self.proposals,
            snapshot.get("prepared_actions", []),
            ActionProposal.model_validate,
        )
        if "prepared_inputs" in snapshot:
            merge(
                self.inputs,
                snapshot["prepared_inputs"],
                ActionInput.model_validate,
                replace=True,
            )
        merge(self.artifacts, snapshot.get("produced_artifacts", []), dict)
        merge(self.tool_names, snapshot.get("business_tool_names", []))
        if self.evidence is not None:
            events = list(self.evidence.events)
            merge(events, snapshot.get("harness_tools", []), dict)
            self.evidence.restore(events)

    def before_model(self, state, runtime):
        """工具完成后、下一次模型调用前捕获结果，减少失败后的重复执行。"""
        return self._capture()

    def after_agent(self, state, runtime):
        """最终答复完成时再次保存结果，避免只留下自然语言答复。"""
        return self._capture()
