"""可恢复的材料评价流程：取证、草拟、复核与导师审阅。"""

from hashlib import sha256
from typing import NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from insight_link_agent.agent.evaluation.attachment_context import (
    AttachmentContext,
    read_attachment_context,
)
from insight_link_agent.agent.evaluation.drafting import (
    DraftGenerator,
    mechanical_review,
)
from insight_link_agent.agent.evaluation.harness_policy import load_review_rubrics
from insight_link_agent.agent.skills.guidance import guidance_for
from insight_link_agent.app.schemas import DecisionRequest, Draft, Material, Source
from insight_link_agent.integrations.java_client import JavaAPIError
from insight_link_agent.integrations.mcp.client import MCPReader


class EvaluationState(TypedDict):
    """正式点评草稿的检查点字段，不保存当前请求的 Java token。

    ``sources`` 是生成和复核共用的取证快照；``material_hash`` 用于审批前
    检测材料变化。``phase`` 反映当前节点结果，不能据此宣称 Java 已写入。
    """

    material_id: int
    actor_id: int
    phase: str
    revisions: int
    plan: NotRequired[list[str]]
    material: NotRequired[dict]
    material_hash: NotRequired[str]
    sources: NotRequired[list[dict]]
    attachment_digest: NotRequired[str | None]
    attachment_scope_note: NotRequired[str]
    attachment_complete: NotRequired[bool]
    warnings: NotRequired[list[str]]
    draft: NotRequired[dict]
    review: NotRequired[dict]
    decision: NotRequired[str]
    final_comment: NotRequired[str]
    phase_trace: NotRequired[list[dict[str, str]]]


def material_hash(material: Material) -> str:
    """记录取证时的材料快照摘要，供确认草稿前校验材料是否变化。"""
    return sha256(material.model_dump_json().encode("utf-8")).hexdigest()


def build_graph(
    reader: MCPReader,
    generator: DraftGenerator,
    checkpointer,
    max_revisions: int,
):
    """装配带 checkpoint 的评价图，复核失败可限次修订。

    ``approval`` 节点通过 LangGraph interrupt 等待导师审阅；批准结果
    只是草稿决定，不会写入 Java。恢复决定时，API 还会重新核验材料快照、
    附件摘要与导师权限。
    """
    rubrics = load_review_rubrics()

    def trace(state: EvaluationState, phase: str, event: str) -> list[dict[str, str]]:
        """只保存阶段和事件，不把材料正文或凭据写入轨迹。"""
        return [*state.get("phase_trace", []), {"phase": phase, "event": event}]

    async def plan(state: EvaluationState) -> dict:
        """开始一份新草稿，初始化修订次数并持久化可展示的固定步骤。"""
        return {
            "phase": "planning",
            "plan": ["读取材料和历史", "形成有依据的草稿", "复核草稿", "导师确认"],
            "revisions": 0,
            "phase_trace": trace(state, "planning", "已制定点评步骤"),
        }

    async def gather(state: EvaluationState) -> dict:
        """先授权取证，再合并正文、附件和历史；附件不完整必须显式披露。

        只有解析不可用类错误可以由已有正文兜底，鉴权或目标失效不能被
        当作附件警告吞掉。后续节点只使用此快照，避免生成与复核各读一份材料。
        """
        material = await reader.material(state["material_id"])
        if material.evaluated:
            raise ValueError("材料已经点评，不能生成新的待提交点评草稿")
        history = await reader.history(material.student_user_id, material.id)
        sources = []
        if material.content.strip():
            sources.append(
                Source(
                    id=material.id,
                    kind="material",
                    text=material.content,
                    title=material.title,
                )
            )
        warnings = []
        attachment_digest = None
        attachment_context = AttachmentContext()
        if material.file_url:
            try:
                attachment_context = await read_attachment_context(reader, material)
                attachment_digest = attachment_context.digest
                sources.extend(attachment_context.sources)
            except JavaAPIError as exc:
                if exc.status not in (422, 503):
                    raise
                warnings.append(f"附件未解析：{exc}")
                attachment_context = AttachmentContext.unavailable()
            if not attachment_context.complete:
                warnings.append(attachment_context.scope_note)
        if not any(source.kind in ("material", "attachment") for source in sources):
            raise ValueError("材料正文为空且附件不可用，无法生成有依据的点评")
        sources.extend(history)
        return {
            "phase": "executing",
            "material": material.model_dump(),
            "material_hash": material_hash(material),
            "sources": [source.model_dump() for source in sources],
            "attachment_digest": attachment_digest,
            "attachment_scope_note": attachment_context.scope_note,
            "attachment_complete": attachment_context.complete,
            "warnings": warnings,
            "phase_trace": trace(state, "executing", "已读取授权材料和历史"),
        }

    async def draft(state: EvaluationState) -> dict:
        """使用同一证据快照起草；重入修订时仅追加上次复核意见。"""
        material = Material.model_validate(state["material"])
        sources = [Source.model_validate(x) for x in state["sources"]]
        feedback = state.get("review", {}).get("issues", [])
        attachment_context = AttachmentContext(
            complete=state.get("attachment_complete", False),
            scope_note=state.get("attachment_scope_note", ""),
        )
        result = await generator.generate(
            material,
            sources,
            guidance_for(material.material_type) + attachment_context.rules(),
            feedback,
        )
        result = attachment_context.disclose(result)
        return {
            "phase": "executing",
            "draft": result.model_dump(),
            "phase_trace": trace(state, "executing", "已生成待复核草稿"),
        }

    async def review(state: EvaluationState) -> dict:
        """先校验引用等机械约束，通过后再调用没有业务写工具的复核器。"""
        result = Draft.model_validate(state["draft"])
        sources = [Source.model_validate(x) for x in state["sources"]]
        mechanical = mechanical_review(result, sources)
        if mechanical.passed:
            material = Material.model_validate(state["material"])
            attachment_context = AttachmentContext(
                complete=state.get("attachment_complete", False),
                scope_note=state.get("attachment_scope_note", ""),
            )
            assessed = await generator.review(
                result,
                sources,
                rubrics.for_material(material.material_type)
                + attachment_context.rules(),
            )
        else:
            assessed = mechanical
        return {
            "phase": "reviewing",
            "review": assessed.model_dump(),
            "phase_trace": trace(
                state, "reviewing", "复核通过" if assessed.passed else "复核未通过"
            ),
        }

    def review_route(state: EvaluationState) -> str:
        """通过才进入导师审批；失败的自动修订受固定次数限制。"""
        if state["review"]["passed"]:
            return "approval"
        if state["revisions"] < max_revisions:
            return "retry"
        return "failed"

    async def retry(state: EvaluationState) -> dict:
        """只推进修订计数，不重新下载附件或变更已取得的材料快照。"""
        return {
            "revisions": state["revisions"] + 1,
            "phase_trace": trace(state, "reviewing", "根据复核问题修订草稿"),
        }

    async def failed(state: EvaluationState) -> dict:
        """用明确失败终态结束，不能把未通过的草稿当成已完成点评。"""
        return {
            "phase": "failed",
            "phase_trace": trace(state, "result", "复核未通过，已停止"),
        }

    async def approval(state: EvaluationState) -> dict:
        """在检查点暂停；导师恢复只决定草稿去留，不调用 Java 写入接口。

        LangGraph 恢复中断时会从节点开头再次执行，因此中断之前不能放
        有副作用的写操作，否则重复恢复可能导致重复提交。
        """
        answer = interrupt(
            {
                "kind": "teacher_review",
                "material_id": state["material_id"],
                "draft": state["draft"],
                "review": state["review"],
            }
        )
        decision = DecisionRequest.model_validate(answer)
        if decision.decision == "reject":
            return {
                "phase": "rejected",
                "decision": "reject",
                "phase_trace": trace(state, "result", "导师已拒绝草稿"),
            }
        comment = decision.edited_comment or state["draft"]["comment"]
        return {
            "phase": "approved",
            "decision": "approve",
            "final_comment": comment,
            "phase_trace": trace(state, "result", "导师已确认草稿"),
        }

    workflow = StateGraph(EvaluationState)
    workflow.add_node("plan", plan)
    workflow.add_node("gather", gather)
    workflow.add_node("draft", draft)
    workflow.add_node("review", review)
    workflow.add_node("retry", retry)
    workflow.add_node("failed", failed)
    workflow.add_node("approval", approval)
    workflow.add_edge(START, "plan")
    workflow.add_edge("plan", "gather")
    workflow.add_edge("gather", "draft")
    workflow.add_edge("draft", "review")
    workflow.add_conditional_edges(
        "review",
        review_route,
        {
            "approval": "approval",
            "retry": "retry",
            "failed": "failed",
        },
    )
    workflow.add_edge("retry", "draft")
    workflow.add_edge("failed", END)
    workflow.add_edge("approval", END)
    return workflow.compile(checkpointer=checkpointer)
