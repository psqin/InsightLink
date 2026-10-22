"""为导师生成有证据、可复核的 AI 建议评价；此模块没有业务写入。"""

from insight_link_agent.agent.evaluation.attachment_context import (
    AttachmentContext,
    read_attachment_context,
)
from insight_link_agent.agent.evaluation.drafting import mechanical_review
from insight_link_agent.agent.evaluation.harness_policy import load_review_rubrics
from insight_link_agent.agent.grading.policy import GradingStandardSnapshot
from insight_link_agent.agent.observability.progress import (
    current_progress,
    observed_read,
    reviewing,
)
from insight_link_agent.agent.skills.guidance import guidance_for
from insight_link_agent.app.schemas import Draft, Material, Source
from insight_link_agent.integrations.java_client import JavaAPIError


async def suggest_evaluation(
    reader,
    generator,
    material_id: int,
    material: Material | None = None,
    *,
    grading_store=None,
    teacher_user_id: int | None = None,
) -> tuple[Material, Draft]:
    """读取导师可访问的材料，生成建议分数与评语，并做证据和独立模型复核。"""
    material = material or await observed_read(
        "get_material", reader.material, material_id
    )
    sources: list[Source] = []
    if material.content.strip():
        sources.append(
            Source(
                id=material.id,
                kind="material",
                text=material.content,
                title=material.title,
            )
        )
    attachment_context = AttachmentContext()
    if material.file_url:
        try:
            attachment_context = await read_attachment_context(
                reader, material, observe=True
            )
        except JavaAPIError as exc:
            if exc.status not in (422, 503):
                raise
            attachment_context = AttachmentContext.unavailable()
        else:
            sources.extend(attachment_context.sources)
    if not sources:
        raise ValueError("材料正文为空且附件不可用，无法形成有依据的 AI 评价")
    sources.extend(
        await observed_read(
            "get_student_history", reader.history, material.student_user_id, material.id
        )
    )
    rubrics = load_review_rubrics()
    if grading_store is not None:
        standard = await grading_store.snapshot(teacher_user_id, material.material_type)
    else:
        standard = GradingStandardSnapshot(
            source="default", version=0, content=rubrics.scoring[material.material_type]
        )
    rubric = (
        rubrics.for_suggestion(material.material_type, standard)
        + attachment_context.rules()
    )
    if progress := current_progress():
        progress.state({"harness_phase": "executing"})
    draft = await generator.generate_suggestion(
        material,
        sources,
        guidance_for(material.material_type) + attachment_context.rules(),
        rubric,
    )
    draft = attachment_context.disclose(draft)
    # 来源由服务端注入，不能相信模型自报的标准版本。
    draft = draft.model_copy(update={"grading_standard": standard})
    checked = mechanical_review(draft, sources, allow_suggested_score=True)
    if not checked.passed:
        raise ValueError("AI 评价未通过证据校验：" + "；".join(checked.issues))
    reviewing()
    reviewed = await generator.review(draft, sources, rubric)
    if not reviewed.passed:
        raise ValueError("AI 评价未通过复核：" + "；".join(reviewed.issues))
    if progress := current_progress():
        progress.state(
            {"harness_review_status": "satisfied", "harness_review_iterations": 1}
        )
    return material, draft
