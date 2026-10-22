"""聊天编排的可替换响应器边界，不绑定具体DeepAgent类型。"""

import inspect
import logging
import re

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from insight_link_agent.agent.conversation.actions import ActionProposal
from insight_link_agent.agent.conversation.hitl import (
    ActionInput,
    ask_for_fields,
)
from insight_link_agent.agent.execution.context import begin_commit
from insight_link_agent.app.dependencies import RequestIdentity
from insight_link_agent.app.presenters import _artifact_markers, _public_chat_messages
from insight_link_agent.app.schemas import (
    ChatMessageRequest,
)
from insight_link_agent.app.services.interactions import (
    check_proposal_scope,
    finish_interaction,
    start_interaction,
)
from insight_link_agent.integrations.java_client import JavaAPIError
from insight_link_agent.integrations.mcp.auth import use_java_token
from insight_link_agent.integrations.processes import ResourceCleanupError

logger = logging.getLogger(__name__)


async def call_responder(responder, history, reader, material_id, **context):
    """生产响应器接收完整上下文；测试或插件只接收其声明支持的参数。"""
    method = responder.respond_with_tools
    parameters = inspect.signature(method).parameters
    if not any(
        value.kind == inspect.Parameter.VAR_KEYWORD for value in parameters.values()
    ):
        context = {key: value for key, value in context.items() if key in parameters}
    return await method(history, reader, material_id, **context)


async def cancel_pending(request, current, conversation):
    """执行模型识别的取消请求，只取消未提交待办；不会撤销已完成业务写入。"""
    services = request.app.state
    await begin_commit()
    for store in (services.input_store, services.action_store):
        pending = await store.latest_pending(conversation.id, current.actor.user_id)
        if pending is not None:
            await finish_interaction(
                request, current, pending, "cancel", "导师取消待办"
            )
            await store.transition(
                pending.id, current.actor.user_id, "pending", "canceled"
            )


class ChatService:
    """编排一次聊天的上下文、工具结果、HOT提交和待确认交互，不识别关键词。"""

    def __init__(self, dependencies):
        self.owned_conversation = dependencies.owned_conversation

    async def send_message(
        self, body: ChatMessageRequest, request: Request, current: RequestIdentity
    ):
        """处理普通问答、补字段与 AI 建议；执行/取消/租约由独立生命周期模块管理。"""
        services = request.app.state
        message = body.message.strip()
        if not message:
            raise HTTPException(status_code=422, detail="消息不能为空")
        conversation = None
        history: list[dict] = []
        if body.conversation_id:
            conversation = await self.owned_conversation(
                request, body.conversation_id, current
            )
            if (
                body.material_id is not None
                and body.material_id != conversation.material_id
            ):
                raise HTTPException(status_code=409, detail="对话的材料上下文不能更改")
            history = [
                {
                    **item,
                    "content": re.sub(
                        r"\[\[artifact:[0-9a-f-]{36}:[A-Za-z0-9._-]+\]\]",
                        "",
                        item["content"],
                    ),
                }
                for item in _public_chat_messages(
                    await services.chat_store.messages(conversation.id)
                )
            ]
            material_id = conversation.material_id
        else:
            material_id = body.material_id

        # 只处理已验证的会话与待办快照；语义理解统一交给模型和工具。
        if material_id is not None:
            await services.java.material(current.token, material_id)
        waiting = (
            await services.input_store.latest_pending(
                conversation.id, current.actor.user_id
            )
            if conversation is not None
            else None
        )
        previous = (
            await services.action_store.latest_pending(
                conversation.id, current.actor.user_id
            )
            if conversation is not None
            else None
        )
        if previous and previous.conversation_version != conversation.version:
            previous = None

        # 普通问答走受控工具循环；模型仅能提出待确认提案，不能直接写 Java。
        tool_response = getattr(services.chat_responder, "respond_with_tools", None)
        if callable(tool_response):
            proposals: list[ActionProposal] = []
            clarifications: list[ActionInput] = []
            artifacts: list[dict] = []
            memory_tool_names: list[str] = []
            harness_results: list[dict] = []
            controls = []
            if conversation is None:
                await services.chat_store.create_empty(
                    current.actor.user_id,
                    material_id,
                    request.state.chat_conversation_id,
                )
                conversation = await services.chat_store.get(
                    request.state.chat_conversation_id,
                    current.actor.user_id,
                )
            try:
                with use_java_token(current.token):
                    answer = await call_responder(
                        services.chat_responder,
                        [*history, {"role": "user", "content": message}],
                        services.reader,
                        material_id,
                        proposal_sink=proposals,
                        clarification_sink=clarifications,
                        teacher_user_id=current.actor.user_id,
                        artifact_store=services.artifact_store,
                        artifact_sink=artifacts,
                        memory_tool_sink=memory_tool_names,
                        checkpointer=services.chat_checkpointer,
                        conversation_id=conversation.id,
                        turn_number=conversation.version + 1,
                        harness_sink=harness_results,
                        draft_generator=services.draft_generator,
                        pending_input=waiting.action if waiting else None,
                        pending_proposal=previous.proposal if previous else None,
                        execution_receipts=await services.action_store.completed_receipts(
                            conversation.id, current.actor.user_id
                        ),
                        control_sink=controls,
                    )
                    if artifacts:
                        answer += _artifact_markers(artifacts)
            except (ResourceCleanupError, JavaAPIError):
                raise
            except RuntimeError as exc:
                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": str(exc),
                        "conversation_id": conversation.id,
                        "retryable": True,
                    },
                )
            if controls:
                await cancel_pending(
                    request,
                    current,
                    conversation,
                )
                waiting = previous = None
            if len(proposals) > 1:
                raise HTTPException(status_code=409, detail="一次只能准备一项业务操作")
            # 模型通过工具明确产生待办；关键词不能在模型答复之后擅自补出业务操作。
            harness = harness_results[-1] if harness_results else None
            if proposals:
                await check_proposal_scope(request, current, material_id, proposals[0])
                clarifications.clear()
            if proposals:
                answer = "已准备业务操作，请核对下方目标与内容，再点击确认执行。"
            elif clarifications:
                answer = ask_for_fields(clarifications[0])
            # 首轮也已在运行前创建空会话：统一按版本追加，恢复路径不另开分支。
            if not await services.chat_store.append_turn(
                conversation,
                message,
                answer,
                material_id,
                tool_names=memory_tool_names,
            ):
                raise HTTPException(status_code=409, detail="对话已更新，请刷新后重试")
            conversation_id = conversation.id
            if harness is not None:
                try:
                    await services.trace_store.save(
                        current.actor.user_id,
                        conversation_id,
                        conversation.version + 1,
                        harness,
                    )
                except Exception:
                    logger.exception("Harness 轻量轨迹保存失败；执行状态仍在图检查点中")
            pending_action = None
            pending_input = None
            if proposals:
                version = conversation.version + 1
                graph_id = await start_interaction(
                    request,
                    current,
                    conversation_id,
                    proposal=proposals[0],
                )
                pending = await services.action_store.create(
                    conversation_id,
                    current.actor.user_id,
                    version,
                    proposals[0],
                    graph_id,
                )
                pending_action = pending.public()
                if waiting is not None:
                    await services.input_store.transition(
                        waiting.id, current.actor.user_id, "pending", "completed"
                    )
            elif clarifications:
                graph_id = await start_interaction(
                    request,
                    current,
                    conversation_id,
                    action=clarifications[0],
                )
                pending = await services.input_store.create(
                    conversation_id,
                    current.actor.user_id,
                    clarifications[0],
                    graph_id,
                )
                pending_input = pending.public()
            else:
                # 后续普通聊天使旧的操作预览失效；尚未补齐的表单仍可继续填写。
                old = await services.action_store.latest_pending(
                    conversation_id, current.actor.user_id
                )
                if old is not None:
                    await services.action_store.transition(
                        old.id, current.actor.user_id, "pending", "canceled"
                    )
                    await finish_interaction(
                        request, current, old, "cancel", "后续消息使预览失效"
                    )
                if waiting is not None:
                    pending_input = waiting.public()
            return {
                "conversation_id": conversation_id,
                "material_id": material_id,
                "answer": answer,
                "warnings": [],
                "harness": harness,
                "pending_action": pending_action,
                "pending_input": pending_input,
            }
        # 正式响应器必须提供受控工具入口；不再回退到旧的编号式检索/直连模型流程。
        raise HTTPException(status_code=503, detail="聊天响应器未提供工具调用能力")
