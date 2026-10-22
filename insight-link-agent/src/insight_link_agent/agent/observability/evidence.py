"""记录实际工具执行的受控证据，包含主 Agent 与子 Agent 的工具入口。"""

import json

from insight_link_agent.agent.subagents.runtime import delegation_id

SIDE_EFFECT_TOOLS = frozenset(
    {
        "create_chart",
        "run_analysis_code",
        "create_report",
        "create_document",
        "create_table",
        "prepare_business_action",
        "cancel_pending_operation",
        "request_teacher_info",
        "draft_evaluation",
        "remember",
        "set_grading_standard",
        "reset_grading_standard",
        "save_user_skill",
        "install_skill",
        "set_user_skill_enabled",
        "delete_user_skill",
    }
)


class ExecutionEvidence:
    """只记录应用登记的工具结果，不接收模型自报的成功状态。"""

    def __init__(self):
        self.events = []

    def record(self, name: str, result) -> None:
        """限制证据大小；截断仅表示当前片段有限，不判断原始资料缺失。"""
        if len(self.events) >= 160 or (
            name not in {"list_my_students", "list_student_materials"}
            and sum(
                event["name"] not in {"list_my_students", "list_student_materials"}
                for event in self.events
            )
            >= 32
        ):
            return
        try:
            data = json.loads(result) if isinstance(result, str) else result
        except (ValueError, TypeError):
            data = {"text": str(result)}
        ok = (
            isinstance(data, dict)
            and data.get("ok", True) is not False
            and not data.get("error")
        )
        content = json.dumps(data, ensure_ascii=False, default=str)
        self.events.append(
            {
                "name": name,
                "ok": ok,
                "content": content[:6000],
                "truncated": len(content) > 6000,
                "delegation_id": delegation_id.get(),
            }
        )

    def restore(self, events) -> None:
        """失败节点恢复时保留已完成工具的证据，避免要求重复执行。"""
        self.events[:] = list(events)[:160]
