"""导师会话历史：数据库分页、标题管理和受租约保护的软删除。"""

import asyncio

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from insight_link_agent.app.storage.lease_store import ConversationBusy


class RenameConversationRequest(BaseModel):
    """只接受可展示的会话标题，不允许客户端修改导师或业务版本。"""

    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=80)

    @field_validator("title")
    @classmethod
    def meaningful_title(cls, value: str) -> str:
        """空格不构成有效标题；保持搜索和列表中的实际文本一致。"""
        value = value.strip()
        if not value:
            raise ValueError("对话标题不能为空")
        return value


def _public_conversation(item) -> dict:
    """历史列表只包含摘要，不返回消息正文、工具上下文或导师内部标识。"""
    return {
        "id": item.id,
        "material_id": item.material_id,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "title": item.title,
    }


def register_history_routes(app: FastAPI, identity) -> None:
    """复用应用的 Java 身份依赖；会话元数据管理只校验导师自身归属。"""

    @app.get("/api/chat/conversations")
    async def list_conversations(
        request: Request,
        page: int = Query(default=1, ge=1, le=100000),
        page_size: int = Query(default=20, ge=1, le=50),
        keyword: str = Query(default="", max_length=100),
        current=Depends(identity),
    ):
        """数据库完成标题搜索和分页；总数限定在当前导师的未删除会话。"""
        services = request.app.state
        items, total = await services.chat_store.search_conversations(
            current.actor.user_id,
            page=page,
            page_size=page_size,
            keyword=keyword,
        )
        return {
            "items": [_public_conversation(item) for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def check_owned(request, conversation_id, current):
        """被删除与其他导师的会话统一返回不存在，避免暴露会话是否存在。"""
        services = request.app.state
        item = await services.chat_store.get(conversation_id, current.actor.user_id)
        if item is None:
            raise HTTPException(status_code=404, detail="对话不存在")
        return item

    @app.patch("/api/chat/conversations/{conversation_id}")
    async def rename_conversation(
        conversation_id: str,
        body: RenameConversationRequest,
        request: Request,
        current=Depends(identity),
    ):
        """与模型执行共用租约，防止标题变更被首轮回答写入覆盖。"""
        services = request.app.state
        await check_owned(request, conversation_id, current)
        try:
            async with services.chat_leases.hold(
                current.actor.user_id, conversation_id
            ):
                await check_owned(request, conversation_id, current)
                await services.chat_store.rename(
                    conversation_id, current.actor.user_id, body.title
                )
                return _public_conversation(
                    await check_owned(request, conversation_id, current)
                )
        except ConversationBusy as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.delete("/api/chat/conversations/{conversation_id}")
    async def delete_conversation(
        conversation_id: str,
        request: Request,
        current=Depends(identity),
    ):
        """软删除不清理操作回执；活跃任务或未确认完成的写入都禁止删除。"""
        services = request.app.state
        await check_owned(request, conversation_id, current)
        try:
            async with services.chat_leases.hold(
                current.actor.user_id, conversation_id
            ):
                await check_owned(request, conversation_id, current)
                executing = await asyncio.to_thread(
                    services.action_store.collection.find_one,
                    {
                        "conversation_id": conversation_id,
                        "user_id": current.actor.user_id,
                        "record_type": "action",
                        "status": "executing",
                    },
                    {"_id": 1},
                )
                if executing is not None:
                    raise HTTPException(
                        status_code=409,
                        detail="该对话有尚未核实结果的业务操作，请先核对执行结果",
                    )
                await services.chat_store.soft_delete(
                    conversation_id, current.actor.user_id
                )
                return {"id": conversation_id, "deleted": True}
        except ConversationBusy as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
