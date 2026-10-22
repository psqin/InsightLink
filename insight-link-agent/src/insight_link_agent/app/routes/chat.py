"""chat资源接口；权限和业务执行依赖由应用工厂显式注入。"""

from fastapi import Depends, Request

from insight_link_agent.app.dependencies import RequestIdentity
from insight_link_agent.app.presenters import _public_chat_messages
from insight_link_agent.app.services.chat import ChatService


def register_chat_routes(app, dependencies):
    """注册现有HTTP地址，保持前端契约稳定。"""
    identity = dependencies.identity
    owned_conversation = dependencies.owned_conversation

    @app.get("/api/chat/conversations/{conversation_id}")
    async def get_conversation(
        conversation_id: str,
        request: Request,
        current: RequestIdentity = Depends(identity),
    ):
        services = request.app.state
        conversation = await owned_conversation(request, conversation_id, current)
        messages = _public_chat_messages(
            await services.chat_store.messages(conversation.id)
        )
        execution = await services.execution_store.reconcile(
            current.actor.user_id, conversation.id
        )
        return {
            "id": conversation.id,
            "material_id": conversation.material_id,
            "messages": messages,
            "execution": services.execution_store.public(execution),
            # 未交付的一轮不写 HOT 假答复；页面从执行记录还原原问题气泡。
            "pending_question": (
                execution["question"]
                if execution
                and execution["status"] != "completed"
                and conversation.version <= execution["base_version"]
                else None
            ),
            "harness": await services.trace_store.get(
                current.actor.user_id,
                conversation.id,
                conversation.version,
            ),
            "pending_action": (
                pending.public()
                if (
                    pending := await services.action_store.latest_pending(
                        conversation.id, current.actor.user_id
                    )
                )
                else None
            ),
            "pending_input": (
                pending.public()
                if (
                    pending := await services.input_store.latest_pending(
                        conversation.id, current.actor.user_id
                    )
                )
                else None
            ),
        }

    return ChatService(dependencies).send_message
