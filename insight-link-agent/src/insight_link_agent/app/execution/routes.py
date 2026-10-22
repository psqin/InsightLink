"""任务的 HTTP 生命周期：登录验证、会话互斥、显式停止和原任务恢复。"""

import asyncio
from functools import partial
from uuid import uuid4

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from insight_link_agent.app.execution.manager import settled
from insight_link_agent.app.schemas import ChatMessageRequest
from insight_link_agent.app.storage.execution_store import ExecutionConflict
from insight_link_agent.app.storage.lease_store import ConversationBusy
from insight_link_agent.app.streaming.chat import chat_stream_response


class ExecutionRequest(BaseModel):
    """必须带页面实际观察到的执行 ID，旧按钮不能误停后来启动的任务。"""

    execution_id: str = Field(min_length=1, max_length=64)
    attempt: int | None = Field(default=None, ge=1)


def register_execution_routes(app, identity, owned_conversation, process_message):
    """JSON 和 SSE 共用生产者；浏览器连接不持有任务执行权。"""

    async def launch(body, request, current, *, resume_id=None, attempt=None):
        """响应头前完成鉴权与领取；成功移交后只有生产者负责释放租约。"""
        if not body.message.strip():
            raise HTTPException(422, "消息不能为空")
        state, user_id = request.app.state, current.actor.user_id
        if body.conversation_id:
            conversation = await owned_conversation(
                request, body.conversation_id, current
            )
            if (
                body.material_id is not None
                and body.material_id != conversation.material_id
            ):
                raise HTTPException(409, "对话的材料上下文不能更改")
            conversation_id, version, material_id = (
                conversation.id,
                conversation.version,
                conversation.material_id,
            )
            await state.execution_store.reconcile(user_id, conversation_id)
        else:
            material_id = body.material_id
            if material_id is not None:
                await state.java.material(current.token, material_id)
            conversation_id, version = str(uuid4()), 0
        lease = state.chat_leases.hold(user_id, conversation_id)
        try:
            ticket = await lease.__aenter__()
        except ConversationBusy as exc:
            raise HTTPException(409, str(exc)) from exc
        try:

            async def prepare():
                """即使请求在启动窗口断开，也先确定数据库结果，再释放租约。

                to_thread 的等待被取消不会终止 Mongo 工作线程。两分支清理与开始
                记录必须一并收尾，不能留下新执行记录却指向另一问题的旧图。
                """
                if not body.conversation_id:
                    await state.chat_store.create_empty(
                        user_id, material_id, conversation_id
                    )
                item, discard = await state.execution_store.begin(
                    user_id,
                    conversation_id,
                    body.message.strip(),
                    material_id,
                    version,
                    resume_id=resume_id,
                    attempt=attempt,
                )
                if discard:
                    for branch in ("public", "private"):
                        await state.chat_checkpointer.adelete_thread(
                            f"chat-model:{user_id}:{conversation_id}:{branch}"
                        )
                return item

            item = await settled(prepare(), propagate_cancel=True)
            request.state.chat_conversation_id = conversation_id
            body = body.model_copy(
                update={"conversation_id": conversation_id, "material_id": material_id}
            )
            return state.execution_manager.launch(
                user_id,
                conversation_id,
                item,
                partial(process_message, body, request, current),
                lease,
                ticket,
            )
        except BaseException:
            await lease.__aexit__(None, None, None)
            raise

    @app.post("/api/chat/messages/stream")
    async def stream(
        body: ChatMessageRequest, request: Request, current=Depends(identity)
    ):
        """POST SSE 不把凭据、问题和学生信息放入 URL。"""
        return chat_stream_response(await launch(body, request, current))

    @app.post("/api/chat/messages")
    async def message(
        body: ChatMessageRequest, request: Request, current=Depends(identity)
    ):
        """非流式客户端同样可停止；HTTP 断开只结束等待，不取消生产任务。"""
        handle = await launch(body, request, current)
        event, data, _execution = await asyncio.shield(handle.task)
        if event == "result":
            return data
        if event == "execution":
            return JSONResponse(
                status_code=409,
                content={
                    "conversation_id": handle.conversation_id,
                    "execution": data,
                    "detail": data["message"],
                },
            )
        return JSONResponse(status_code=data.get("status", 503), content=data)

    @app.get("/api/chat/conversations/{conversation_id}/execution")
    async def status(conversation_id: str, request: Request, current=Depends(identity)):
        """状态观察不领取执行租约，因此运行期间和刷新后都能查询。"""
        await owned_conversation(request, conversation_id, current)
        store = request.app.state.execution_store
        return {
            "execution": store.public(
                await store.reconcile(current.actor.user_id, conversation_id)
            )
        }

    @app.post("/api/chat/conversations/{conversation_id}/execution/cancel")
    async def cancel(
        conversation_id: str,
        body: ExecutionRequest,
        request: Request,
        current=Depends(identity),
    ):
        """这里只请求停止，返回的终态取决于真实资源清理是否已经结束。"""
        await owned_conversation(request, conversation_id, current)
        state = request.app.state
        item = await state.execution_manager.cancel(
            current.actor.user_id,
            conversation_id,
            body.execution_id,
            attempt=body.attempt,
        )
        return {"execution": state.execution_store.public(item)}

    @app.post("/api/chat/conversations/{conversation_id}/execution/resume/stream")
    async def resume(
        conversation_id: str,
        body: ExecutionRequest,
        request: Request,
        current=Depends(identity),
    ):
        """只使用这次登录的 token；从存储读取原问题，不接受改写后的恢复请求。"""
        await owned_conversation(request, conversation_id, current)
        store = request.app.state.execution_store
        item = await store.reconcile(current.actor.user_id, conversation_id)
        if (
            not item
            or item["id"] != body.execution_id
            or not store.public(item)["can_resume"]
        ):
            raise ExecutionConflict("该任务目前不能恢复，请重新打开会话核实状态")
        return chat_stream_response(
            await launch(
                ChatMessageRequest(
                    conversation_id=conversation_id, message=item["question"]
                ),
                request,
                current,
                resume_id=body.execution_id,
                attempt=body.attempt,
            )
        )
