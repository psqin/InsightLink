"""补充表单、原生中断与确认预览的共用服务。"""

import logging
from uuid import uuid4

from fastapi import HTTPException, Request
from openai import OpenAIError

from insight_link_agent.agent.conversation.actions import ActionProposal
from insight_link_agent.agent.conversation.hitl import (
    ActionInput,
)
from insight_link_agent.agent.evaluation.suggestion import suggest_evaluation
from insight_link_agent.agent.observability.progress import (
    current_progress,
    observed_read,
)
from insight_link_agent.app.dependencies import RequestIdentity
from insight_link_agent.integrations.mcp.auth import use_java_token

logger = logging.getLogger(__name__)


async def start_interaction(
    request, current, conversation_id, *, action=None, proposal=None
):
    """将新待办挂到原生图；替换旧待办时同时关闭其旧中断。"""
    services = request.app.state
    for store in (services.input_store, services.action_store):
        old = await store.latest_pending(conversation_id, current.actor.user_id)
        if old is not None:
            await finish_interaction(request, current, old, "cancel", "已被新操作替代")
            await store.transition(old.id, current.actor.user_id, "pending", "canceled")
    return await services.chat_interaction.start(
        current.actor.user_id,
        conversation_id,
        action=action,
        proposal=proposal,
    )


async def resume_input_graph(request, current, waiting, updated):
    """表单与聊天共用原生恢复入口；旧表单保持兼容。"""
    services = request.app.state
    if not waiting.graph_thread_id:
        return None
    snapshot = await services.chat_interaction.state(
        waiting.graph_thread_id,
        current.actor.user_id,
        waiting.conversation_id,
    )
    if snapshot.next != ("input",):
        raise HTTPException(status_code=409, detail="补充信息任务已更新，请刷新对话")
    with use_java_token(current.token):
        result = await services.chat_interaction.resume(
            waiting.graph_thread_id,
            current.actor.user_id,
            waiting.conversation_id,
            {"decision": "supplement", "action": updated.model_dump()},
        )
    if not result.get("proposal") and not updated.missing_fields():
        raise HTTPException(
            status_code=409,
            detail=result.get("error") or "目标已变化，请重新核对操作信息",
        )
    return (
        ActionProposal.model_validate(result["proposal"])
        if result.get("proposal")
        else None
    )


async def finish_interaction(request, current, pending, decision, receipt):
    """关闭原生中断；正式写入完成后恢复失败不能诱发第二次写入。"""
    services = request.app.state
    if not pending.graph_thread_id:
        return
    try:
        snapshot = await services.chat_interaction.state(
            pending.graph_thread_id,
            current.actor.user_id,
            pending.conversation_id,
        )
        if snapshot.next:
            await services.chat_interaction.resume(
                pending.graph_thread_id,
                current.actor.user_id,
                pending.conversation_id,
                {"decision": decision, "receipt": receipt},
            )
    except Exception:
        logger.exception("待办已处理，图回执恢复失败；重复确认不会再次执行写入")


async def check_proposal_scope(
    request: Request,
    current: RequestIdentity,
    pinned_material_id: int | None,
    proposal: ActionProposal,
) -> None:
    """材料会话中的写操作仍只允许落在当前学生和当前材料。"""
    services = request.app.state
    if pinned_material_id is None:
        return
    material = await services.java.material(current.token, pinned_material_id)
    if proposal.student_user_id != material.student_user_id or (
        proposal.material_id is not None and proposal.material_id != pinned_material_id
    ):
        raise HTTPException(
            status_code=409, detail="当前对话已绑定另一份材料或学生，请新建对话"
        )


async def build_ai_suggestion(
    request: Request,
    current: RequestIdentity,
    action: ActionInput,
    pinned_material_id: int | None,
    material_id: int,
    conversation_id: str | None = None,
) -> ActionInput:
    """复用同一条授权查询、证据校验和评分复核链。"""
    services = request.app.state
    if action.kind not in ("create_evaluation", "update_evaluation"):
        raise HTTPException(status_code=422, detail="此操作不支持 AI 建议评价")
    if pinned_material_id is not None and pinned_material_id != material_id:
        raise HTTPException(status_code=409, detail="当前对话已绑定另一份材料")
    if progress := current_progress():
        progress.state(
            {
                "harness_phase": "planning",
                "harness_plan": [
                    "读取授权材料",
                    "起草建议分数与评语",
                    "复核评分与引用依据",
                    "交由导师核对",
                ],
            }
        )
    with (
        use_java_token(current.token),
        services.langsmith.bind_run(
            execution_id=str(uuid4()),
            conversation_id=conversation_id,
            teacher_user_id=current.actor.user_id,
        ),
    ):
        material = await observed_read(
            "get_material", services.reader.material, material_id
        )
        if action.kind == "create_evaluation" and material.evaluated:
            raise HTTPException(
                status_code=409, detail="这份材料已有评价，请改用修改评价"
            )
        try:
            _material, draft = await suggest_evaluation(
                services.reader,
                services.draft_generator,
                material_id,
                material,
                grading_store=services.grading_store,
                teacher_user_id=current.actor.user_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except (RuntimeError, OpenAIError) as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    return action.supplemented(
        {
            "material_id": material_id,
            "score": draft.suggested_score,
            "content": draft.comment,
        }
    ).model_copy(
        update={
            "ai_suggested": True,
            "score_rationale": draft.score_rationale,
            "grading_standard": draft.grading_standard,
        }
    )
