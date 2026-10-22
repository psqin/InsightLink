"""Typed boundaries for Java data, model drafts, and API responses."""

from typing import Literal

from pydantic import BaseModel, Field

from insight_link_agent.agent.grading.policy import GradingStandardSnapshot


class Actor(BaseModel):
    user_id: int
    role_id: int
    name: str = ""


class Material(BaseModel):
    id: int
    student_user_id: int
    material_type: int
    title: str
    content: str
    file_url: str | None = None
    evaluated: int = 0
    submit_time: str | None = None
    score: float | None = None
    evaluation_time: str | None = None
    evaluation_content: str | None = None
    evaluation_id: int | None = None
    evaluation_teacher_id: int | None = None


class Source(BaseModel):
    id: int
    kind: Literal["material", "evaluation", "attachment"]
    text: str
    title: str = ""


class Claim(BaseModel):
    text: str = Field(min_length=1)
    source_id: int
    quote: str = Field(min_length=1)


class Draft(BaseModel):
    summary: str = Field(min_length=1)
    strengths: list[Claim]
    concerns: list[Claim]
    actions: list[str] = Field(min_length=1)
    comment: str = Field(min_length=1, max_length=1000)
    suggested_score: float | None = Field(default=None, ge=0, le=100)
    score_rationale: str = Field(default="", max_length=1000)
    grading_standard: GradingStandardSnapshot | None = None


class Review(BaseModel):
    passed: bool
    issues: list[str] = Field(default_factory=list)


class StartRunRequest(BaseModel):
    material_id: int = Field(gt=0)


class DecisionRequest(BaseModel):
    decision: Literal["approve", "reject"]
    edited_comment: str | None = Field(default=None, min_length=1, max_length=1000)


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None
    material_id: int | None = Field(default=None, gt=0)


class ActionDetailsRequest(BaseModel):
    """导师通过表单补齐字段；不允许前端替换操作类型。"""

    material_id: int | None = Field(default=None, gt=0)
    student_name: str | None = Field(default=None, max_length=100)
    score: float | None = Field(default=None, ge=0, le=100)
    content: str | None = Field(default=None, max_length=1000)


class SuggestActionRequest(BaseModel):
    material_id: int = Field(gt=0)
