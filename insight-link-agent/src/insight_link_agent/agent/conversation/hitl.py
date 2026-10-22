"""导师对话的人机协作契约：补齐字段，再展示独立的写入确认。"""

import re

from pydantic import BaseModel, ConfigDict, Field

from insight_link_agent.agent.conversation.actions import (
    ActionKind,
    ActionProposal,
    prepare_action,
)
from insight_link_agent.agent.grading.policy import GradingStandardSnapshot


class ActionInput(BaseModel):
    """只存业务字段，不存模型状态或 Java token。"""

    model_config = ConfigDict(extra="forbid")

    kind: ActionKind
    material_id: int | None = Field(default=None, gt=0)
    student_user_id: int | None = Field(default=None, gt=0)
    student_name: str | None = Field(default=None, max_length=100)
    score: float | None = Field(default=None, ge=0, le=100)
    content: str | None = Field(default=None, max_length=1000)
    ai_suggested: bool = False
    score_rationale: str = Field(default="", max_length=1000)
    grading_standard: GradingStandardSnapshot | None = None

    def missing_fields(self) -> list[str]:
        """按操作类型计算真正缺少的字段，保留 0 分这一合法值。"""
        if self.kind == "send_student_message":
            return (
                ["student_name"]
                if not (self.student_user_id or self.student_name)
                else []
            ) + (["content"] if not (self.content or "").strip() else [])
        missing = ["material_id"] if not self.material_id else []
        if self.kind == "create_evaluation":
            if self.score is None:
                missing.append("score")
            if not (self.content or "").strip():
                missing.append("content")
        if (
            self.kind == "update_evaluation"
            and self.score is None
            and not (self.content or "").strip()
        ):
            missing.append("content")
        return missing

    def supplemented(self, values: dict) -> "ActionInput":
        """新字段覆盖旧草稿；空字符串不擦除先前已提供的信息。"""
        patch = {
            key: value
            for key, value in values.items()
            if key
            in {"material_id", "student_user_id", "student_name", "score", "content"}
            and value is not None
            and value != ""
        }
        updated = {**self.model_dump(), **patch}
        # 更换评价目标后，原材料的评分和评语不得自动套用到新材料。
        if (
            self.kind != "send_student_message"
            and "material_id" in patch
            and self.material_id is not None
            and patch["material_id"] != self.material_id
        ):
            updated["score"] = patch.get("score")
            updated["content"] = patch.get("content")
        # 导师修改了 AI 给出的分数或评语后，不再把修改后的值标成原始 AI 建议。
        if self.ai_suggested and any(
            key in patch and patch[key] != getattr(self, key)
            for key in ("material_id", "score", "content")
        ):
            updated["ai_suggested"] = False
            updated["score_rationale"] = ""
            updated["grading_standard"] = None
        return ActionInput.model_validate(updated)

    def public(self) -> dict:
        """向前端返回可编辑字段及待补清单，不包含任何凭据。"""
        return {**self.model_dump(), "missing_fields": self.missing_fields()}


FIELD_LABELS = {
    "material_id": "评价材料",
    "student_name": "学生姓名或学号",
    "score": "分数（0–100）",
    "content": "评语或留言内容",
}


def ask_for_fields(action: ActionInput) -> str:
    """用导师可理解的字段名提示补充，材料由页面检索选择。"""
    labels = "、".join(
        ("留言内容" if action.kind == "send_student_message" else "评语")
        if field == "content"
        else FIELD_LABELS[field]
        for field in action.missing_fields()
    )
    if "material_id" in action.missing_fields():
        return (
            f"请补充{labels}。可在下方按学生姓名或学号查找并选择材料；"
            "分数和评语可填写表单，也可以在聊天框回复。"
        )
    return f"请补充{labels}。可以填写下方表单，也可以直接在聊天框回复。"


async def prepare_from_input(reader, action: ActionInput) -> ActionProposal:
    """表单提交也要经过导师授权的 MCP 查询和原有预览校验。"""
    if action.missing_fields():
        raise ValueError(ask_for_fields(action))
    student_user_id = action.student_user_id
    if action.kind == "send_student_message" and not student_user_id:
        lookup = action.student_name.strip()
        by_number = bool(re.fullmatch(r"[A-Za-z0-9_-]{5,}", lookup))
        found = await reader.search_my_students(
            "" if by_number else lookup, lookup if by_number else ""
        )
        if not found.get("complete"):
            raise ValueError("学生检索尚未完成，请提供更明确的学号")
        matches = found.get("matches") or []
        if len(matches) != 1:
            raise ValueError("无法唯一确定学生，请填写准确的学号")
        student_user_id = matches[0]["user_id"]
    proposal = await prepare_action(
        reader,
        action.kind,
        action.material_id,
        student_user_id,
        action.score,
        action.content,
    )
    return proposal.model_copy(
        update={
            "ai_suggested": action.ai_suggested,
            "score_rationale": action.score_rationale,
            "grading_standard": action.grading_standard,
        }
    )
