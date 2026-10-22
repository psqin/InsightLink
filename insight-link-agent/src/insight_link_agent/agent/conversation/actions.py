"""导师对话中的业务写入：先准备可核对预览，再由导师确认执行。"""

from typing import Literal, Protocol

from pydantic import BaseModel, Field, model_validator

from insight_link_agent.agent.grading.policy import GradingStandardSnapshot
from insight_link_agent.app.schemas import Material

ActionKind = Literal[
    "create_evaluation",
    "update_evaluation",
    "delete_evaluation",
    "send_student_message",
]


class ExecutionReceipt(BaseModel):
    """服务端验证业务成功后持久化的回执，不能由模型或聊天请求构造。"""

    action_id: str
    kind: ActionKind
    completed_at: str
    summary: str
    target_name: str = ""


class ActionReader(Protocol):
    async def material(self, material_id: int) -> Material: ...
    async def student_profile(self, student_user_id: int) -> dict: ...
    async def create_evaluation(
        self, material_id: int, score: float, content: str
    ) -> None: ...
    async def update_evaluation(
        self, material_id: int, evaluation_id: int, score: float, content: str
    ) -> None: ...
    async def delete_evaluation(self, material_id: int, evaluation_id: int) -> None: ...
    async def send_student_message(
        self, student_user_id: int, content: str
    ) -> None: ...


class ActionProposal(BaseModel):
    """确认页使用的目标快照；执行前需重新与 Java 当前状态比对。"""

    kind: ActionKind
    material_id: int | None = Field(default=None, gt=0)
    student_user_id: int | None = Field(default=None, gt=0)
    score: float | None = Field(default=None, ge=0, le=100)
    content: str | None = Field(default=None, max_length=1000)
    evaluation_id: int | None = Field(default=None, gt=0)
    expected_evaluated: int | None = None
    expected_score: float | None = None
    expected_content: str | None = None
    target_name: str = ""
    target_title: str = ""
    ai_suggested: bool = False
    score_rationale: str = ""
    grading_standard: GradingStandardSnapshot | None = None

    @model_validator(mode="after")
    def validate_target(self):
        """禁止缺少目标、分数或内容的写操作进入确认流程。"""
        if self.kind == "send_student_message":
            if not self.student_user_id or not (self.content or "").strip():
                raise ValueError("发送留言需要明确的学生和留言内容")
        elif not self.material_id:
            raise ValueError("能力评价操作需要明确的材料")
        if self.kind in ("create_evaluation", "update_evaluation"):
            if self.score is None or not (self.content or "").strip():
                raise ValueError("评价需要 0–100 分的分数和具体评语")
        return self

    def preview(self) -> dict:
        """仅向页面返回人可核对的字段，不暴露内部评价 ID。"""
        labels = {
            "create_evaluation": "新增能力评价",
            "update_evaluation": "修改能力评价",
            "delete_evaluation": "删除能力评价",
            "send_student_message": "发送留言",
        }
        return {
            "kind": self.kind,
            "label": labels[self.kind],
            "target_name": self.target_name,
            "target_title": self.target_title,
            "score": self.score if self.kind != "delete_evaluation" else None,
            "content": self.content
            if self.kind != "delete_evaluation"
            else self.expected_content,
            "ai_suggested": self.ai_suggested,
            "score_rationale": self.score_rationale if self.ai_suggested else "",
            "grading_standard": self.grading_standard.model_dump()
            if self.ai_suggested and self.grading_standard
            else None,
        }


async def prepare_action(
    reader: ActionReader,
    kind: ActionKind,
    material_id: int | None = None,
    student_user_id: int | None = None,
    score: float | None = None,
    content: str | None = None,
) -> ActionProposal:
    """只读取并检查目标；绝不在模型调用期间执行写入。"""
    if kind == "send_student_message":
        if not student_user_id:
            raise ValueError("请先明确学生")
        profile = await reader.student_profile(student_user_id)
        return ActionProposal(
            kind=kind,
            student_user_id=student_user_id,
            content=content,
            target_name=str(profile.get("name") or ""),
        )
    if not material_id:
        raise ValueError("请先明确材料")
    material = await reader.material(material_id)
    profile = await reader.student_profile(material.student_user_id)
    if kind == "create_evaluation" and material.evaluated:
        raise ValueError("这份材料已经评价，需使用修改评价")
    if kind != "create_evaluation" and (
        not material.evaluated or not material.evaluation_id
    ):
        raise ValueError("这份材料尚无可修改或删除的评价")
    if kind == "update_evaluation":
        score = material.score if score is None else score
        content = material.evaluation_content if content is None else content
    return ActionProposal(
        kind=kind,
        material_id=material_id,
        student_user_id=material.student_user_id,
        score=score,
        content=content,
        evaluation_id=material.evaluation_id,
        expected_evaluated=material.evaluated,
        expected_score=material.score,
        expected_content=material.evaluation_content,
        target_name=str(profile.get("name") or ""),
        target_title=material.title,
    )


async def execute_action(reader: ActionReader, proposal: ActionProposal) -> str:
    """确认时重新读取目标，发现评价已变化则拒绝过期操作。"""
    if proposal.kind == "send_student_message":
        profile = await reader.student_profile(proposal.student_user_id)
        if profile.get("name") != proposal.target_name:
            raise ValueError("学生资料已变化，请重新发起留言")
        await reader.send_student_message(proposal.student_user_id, proposal.content)
        return f"已向{proposal.target_name}发送留言。"
    material = await reader.material(proposal.material_id)
    if (
        material.student_user_id != proposal.student_user_id
        or material.evaluation_id != proposal.evaluation_id
        or material.evaluated != proposal.expected_evaluated
        or material.score != proposal.expected_score
        or material.evaluation_content != proposal.expected_content
    ):
        raise ValueError("材料或评价已变化，请重新查询后再操作")
    if proposal.kind == "create_evaluation":
        await reader.create_evaluation(
            proposal.material_id, proposal.score, proposal.content
        )
        return f"已为{proposal.target_name}的《{proposal.target_title}》新增能力评价。"
    if proposal.kind == "update_evaluation":
        await reader.update_evaluation(
            proposal.material_id,
            proposal.evaluation_id,
            proposal.score,
            proposal.content,
        )
        return f"已修改{proposal.target_name}的《{proposal.target_title}》能力评价。"
    await reader.delete_evaluation(proposal.material_id, proposal.evaluation_id)
    return f"已删除{proposal.target_name}的《{proposal.target_title}》能力评价。"
