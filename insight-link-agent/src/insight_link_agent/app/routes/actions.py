"""导师待办与正式操作确认接口；鉴权和归属检查由应用工厂显式注入。"""

import logging

from fastapi import Depends, HTTPException, Request

from insight_link_agent.agent.conversation.actions import execute_action
from insight_link_agent.agent.conversation.hitl import (
    ask_for_fields,
    prepare_from_input,
)
from insight_link_agent.app.dependencies import RequestIdentity
from insight_link_agent.app.schemas import (
    ActionDetailsRequest,
    SuggestActionRequest,
)
from insight_link_agent.app.services.interactions import (
    build_ai_suggestion,
    check_proposal_scope,
    finish_interaction,
    resume_input_graph,
)
from insight_link_agent.integrations.java_client import JavaAPIError
from insight_link_agent.integrations.mcp.auth import use_java_token

logger = logging.getLogger(__name__)


def register_actions_routes(app, dependencies):
    """注册现有HTTP地址，保持前端契约稳定。"""
    identity = dependencies.identity
    owned_conversation = dependencies.owned_conversation
    chat_mutation = dependencies.chat_mutation

    @app.post(
        "/api/chat/inputs/{input_id}/suggest", dependencies=[Depends(chat_mutation)]
    )
    async def suggest_chat_evaluation(
        input_id: str,
        body: SuggestActionRequest,
        request: Request,
        current: RequestIdentity = Depends(identity),
    ):
        """AI 根据授权材料起草建议；导师仍须提交预览并再次确认。"""
        services = request.app.state
        waiting = await services.input_store.get(input_id, current.actor.user_id)
        if waiting is None:
            raise HTTPException(status_code=404, detail="待补充信息不存在")
        conversation = await owned_conversation(
            request, waiting.conversation_id, current
        )
        if waiting.status != "pending":
            raise HTTPException(status_code=409, detail="补充信息已处理，请刷新对话")
        updated = await build_ai_suggestion(
            request,
            current,
            waiting.action,
            conversation.material_id,
            body.material_id,
            conversation_id=conversation.id,
        )
        answer = "已根据材料生成建议分数和评语。请核对上方材料与下方草稿，可修改后再提交预览。"
        if not await services.chat_store.append_turn(
            conversation, "请 AI 根据材料起草评价", answer, conversation.material_id
        ):
            raise HTTPException(status_code=409, detail="对话已更新，请刷新后重试")
        next_input = await services.input_store.create(
            conversation.id,
            current.actor.user_id,
            updated,
            waiting.graph_thread_id,
        )
        return {
            "conversation_id": conversation.id,
            "answer": answer,
            "pending_input": next_input.public(),
            "pending_action": None,
        }

    @app.post(
        "/api/chat/inputs/{input_id}/submit", dependencies=[Depends(chat_mutation)]
    )
    async def submit_chat_input(
        input_id: str,
        body: ActionDetailsRequest,
        request: Request,
        current: RequestIdentity = Depends(identity),
    ):
        """导师通过表单补齐操作字段，验证目标后产生待确认预览。"""
        services = request.app.state
        waiting = await services.input_store.get(input_id, current.actor.user_id)
        if waiting is None:
            raise HTTPException(status_code=404, detail="待补充信息不存在")
        conversation = await owned_conversation(
            request, waiting.conversation_id, current
        )
        if waiting.status != "pending":
            raise HTTPException(status_code=409, detail="补充信息已处理，请刷新对话")
        values = body.model_dump(exclude_none=True)
        if not values or all(value == "" for value in values.values()):
            raise HTTPException(status_code=422, detail="请至少填写一项信息")
        updated = waiting.action.supplemented(values)
        if updated.missing_fields():
            await resume_input_graph(request, current, waiting, updated)
            answer = ask_for_fields(updated)
            if not await services.chat_store.append_turn(
                conversation, "通过表单补充操作信息", answer, conversation.material_id
            ):
                raise HTTPException(status_code=409, detail="对话已更新，请刷新后重试")
            next_input = await services.input_store.create(
                conversation.id,
                current.actor.user_id,
                updated,
                waiting.graph_thread_id,
            )
            return {
                "conversation_id": conversation.id,
                "answer": answer,
                "pending_input": next_input.public(),
                "pending_action": None,
            }
        try:
            with use_java_token(current.token):
                proposal = await prepare_from_input(services.reader, updated)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        await check_proposal_scope(request, current, conversation.material_id, proposal)
        restored = await resume_input_graph(request, current, waiting, updated)
        if restored is not None:
            proposal = restored
            await check_proposal_scope(
                request, current, conversation.material_id, proposal
            )
        answer = "信息已补齐，请核对下方预览，再点击确认执行。"
        if not await services.chat_store.append_turn(
            conversation, "通过表单补充操作信息", answer, conversation.material_id
        ):
            raise HTTPException(status_code=409, detail="对话已更新，请刷新后重试")
        await services.input_store.transition(
            waiting.id, current.actor.user_id, "pending", "completed"
        )
        pending = await services.action_store.create(
            conversation.id,
            current.actor.user_id,
            conversation.version + 1,
            proposal,
            waiting.graph_thread_id,
        )
        return {
            "conversation_id": conversation.id,
            "answer": answer,
            "pending_input": None,
            "pending_action": pending.public(),
        }

    @app.post(
        "/api/chat/inputs/{input_id}/cancel", dependencies=[Depends(chat_mutation)]
    )
    async def cancel_chat_input(
        input_id: str,
        request: Request,
        current: RequestIdentity = Depends(identity),
    ):
        services = request.app.state
        waiting = await services.input_store.get(input_id, current.actor.user_id)
        if waiting is None:
            raise HTTPException(status_code=404, detail="待补充信息不存在")
        conversation = await owned_conversation(
            request, waiting.conversation_id, current
        )
        if not await services.input_store.transition(
            waiting.id, current.actor.user_id, "pending", "canceled"
        ):
            raise HTTPException(status_code=409, detail="补充信息已处理")
        answer = "已取消本次操作，未写入任何评价或留言。"
        await finish_interaction(request, current, waiting, "cancel", answer)
        await services.chat_store.append_turn(
            conversation, "取消本次操作", answer, conversation.material_id
        )
        return {"conversation_id": conversation.id, "answer": answer}

    @app.post(
        "/api/chat/actions/{action_id}/confirm", dependencies=[Depends(chat_mutation)]
    )
    async def confirm_chat_action(
        action_id: str,
        request: Request,
        current: RequestIdentity = Depends(identity),
    ):
        """确认前重查归属、时效和 Java 当前状态，并执行一次受控写入。"""
        services = request.app.state
        action = await services.action_store.get(action_id, current.actor.user_id)
        if action is None:
            raise HTTPException(status_code=404, detail="待确认操作不存在")
        conversation = await owned_conversation(
            request, action.conversation_id, current
        )
        if action.status == "completed":
            # 若上次在 Java 成功后进程中止，重复请求仅补图回执，不能重写 Java。
            await finish_interaction(
                request, current, action, "completed", "业务操作已完成"
            )
        if (
            action.status != "pending"
            or conversation.version != action.conversation_version
        ):
            raise HTTPException(status_code=409, detail="操作已过期，请重新发起")
        if action.graph_thread_id:
            snapshot = await services.chat_interaction.state(
                action.graph_thread_id,
                current.actor.user_id,
                action.conversation_id,
            )
            if (
                snapshot.next != ("approval",)
                or snapshot.values.get("proposal") != action.proposal.model_dump()
            ):
                raise HTTPException(
                    status_code=409, detail="操作预览与图状态不一致，请重新发起"
                )
        if not await services.action_store.transition(
            action.id, current.actor.user_id, "pending", "executing"
        ):
            raise HTTPException(status_code=409, detail="操作已过期或正在执行")
        try:
            with use_java_token(current.token):
                answer = await execute_action(services.reader, action.proposal)
        except (ValueError, JavaAPIError) as exc:
            await services.action_store.transition(
                action.id, current.actor.user_id, "executing", "failed"
            )
            await finish_interaction(
                request, current, action, "failed", "确认时校验或业务调用失败"
            )
            if isinstance(exc, JavaAPIError):
                raise
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        await services.action_store.transition(
            action.id, current.actor.user_id, "executing", "completed"
        )
        await finish_interaction(request, current, action, "completed", answer)
        refreshed = await services.chat_store.get(
            action.conversation_id, current.actor.user_id
        )
        if refreshed is not None:
            await services.chat_store.append_turn(
                refreshed, "确认执行", answer, refreshed.material_id
            )
        return {"conversation_id": action.conversation_id, "answer": answer}

    @app.post(
        "/api/chat/actions/{action_id}/cancel", dependencies=[Depends(chat_mutation)]
    )
    async def cancel_chat_action(
        action_id: str,
        request: Request,
        current: RequestIdentity = Depends(identity),
    ):
        services = request.app.state
        action = await services.action_store.get(action_id, current.actor.user_id)
        if action is None:
            raise HTTPException(status_code=404, detail="待确认操作不存在")
        await owned_conversation(request, action.conversation_id, current)
        if not await services.action_store.transition(
            action.id, current.actor.user_id, "pending", "canceled"
        ):
            raise HTTPException(status_code=409, detail="操作已处理")
        answer = "已取消，未执行业务操作。"
        await finish_interaction(request, current, action, "cancel", answer)
        conversation = await services.chat_store.get(
            action.conversation_id, current.actor.user_id
        )
        if conversation is not None:
            await services.chat_store.append_turn(
                conversation, "取消执行", answer, conversation.material_id
            )
        return {"conversation_id": action.conversation_id, "answer": answer}
