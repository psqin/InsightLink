"""HTTP鉴权、对象归属和会话租约；这里不判断自然语言意图。"""

from dataclasses import dataclass, field
from types import SimpleNamespace
from uuid import uuid4

from fastapi import Depends, Header, HTTPException, Request

from insight_link_agent.agent.conversation.models import Conversation
from insight_link_agent.app.schemas import (
    Actor,
)
from insight_link_agent.app.storage.lease_store import ConversationBusy
from insight_link_agent.app.storage.run_store import RunRecord


@dataclass(frozen=True)
class RequestIdentity:
    """Java确认的请求身份；token仅供服务层转发，repr也不能输出凭据。"""

    actor: Actor
    token: str = field(repr=False)


def build_dependencies():
    """创建同一组FastAPI依赖，供路由注册复用，避免出现重复的鉴权实现。"""

    async def identity(  # token验证导师身份
        request: Request, token: str = Header(min_length=1)
    ) -> RequestIdentity:
        """每个请求向 Java 重新确认导师身份，不能信任前端传来的用户 ID。"""
        actor = await request.app.state.java.identify(token)
        if actor.role_id != 2:
            raise HTTPException(status_code=403, detail="当前功能仅供导师使用")
        return RequestIdentity(actor=actor, token=token)

    # 点评任务前的准备校验，数据在mongodb agent_store_runs中
    async def owned_run(
        request: Request, run_id: str, current: RequestIdentity
    ) -> RunRecord:
        record = await request.app.state.store.get(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        if record.user_id != current.actor.user_id:
            raise HTTPException(status_code=403, detail="无权访问该任务")
        # Java verifies that this teacher still owns the student relationship.
        await request.app.state.java.material(current.token, record.material_id)
        return record

    # 导师访问材料验证
    async def owned_conversation(
        request: Request, conversation_id: str, current: RequestIdentity
    ) -> Conversation:
        conversation = await request.app.state.chat_store.get(
            conversation_id, current.actor.user_id
        )
        if conversation is None:
            raise HTTPException(status_code=404, detail="对话不存在")
        if conversation.material_id is not None:
            await request.app.state.java.material(
                current.token, conversation.material_id
            )
        return conversation

    # 检查点的互斥锁，防止多个请求覆盖图状态
    # 定位、传参、加锁，补充信息和待确认可以存在
    async def chat_mutation(
        request: Request,
        current: RequestIdentity = Depends(identity),
    ):
        """串行处理同一会话的模型执行、补字段及审批，保护持久图状态。"""
        params = request.path_params
        if "input_id" in params:
            item = await request.app.state.input_store.get(
                params["input_id"], current.actor.user_id
            )
            if item is None:
                raise HTTPException(status_code=404, detail="待补充信息不存在")
            conversation_id = item.conversation_id
        elif "action_id" in params:
            item = await request.app.state.action_store.get(
                params["action_id"], current.actor.user_id
            )
            if item is None:
                raise HTTPException(status_code=404, detail="待确认操作不存在")
            conversation_id = item.conversation_id
        else:
            body = await request.json()
            if not isinstance(body, dict):
                raise HTTPException(status_code=422, detail="请求内容必须是对象")
            conversation_id = body.get("conversation_id") or str(uuid4())
        request.state.chat_conversation_id = conversation_id
        try:
            async with request.app.state.chat_leases.hold(
                current.actor.user_id, conversation_id
            ):
                yield
        except ConversationBusy as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    return SimpleNamespace(
        identity=identity,
        owned_run=owned_run,
        owned_conversation=owned_conversation,
        chat_mutation=chat_mutation,
    )
