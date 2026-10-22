"""MongoDB 持久化待补字段；图引用只在服务端使用。"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from insight_link_agent.agent.conversation.hitl import ActionInput
from insight_link_agent.app.storage.interaction_store import InteractionStore


@dataclass(frozen=True)
class PendingInput:
    id: str
    conversation_id: str
    user_id: int
    action: ActionInput
    status: str
    graph_thread_id: str | None = None

    def public(self) -> dict:
        """向页面返回业务草稿，不暴露图引用。"""
        return {"id": self.id, **self.action.public()}


class InputStore(InteractionStore):
    """表单与聊天共用待补字段记录，更新时按状态和导师比较交换。"""

    record_type = "input"

    @staticmethod
    def _record(row):
        """反序列化可信集合中的业务草稿。"""
        return (
            PendingInput(
                row["_id"],
                row["conversation_id"],
                row["user_id"],
                ActionInput.model_validate(row["payload"]),
                row["status"],
                row.get("graph_thread_id"),
            )
            if row
            else None
        )

    async def create(
        self,
        conversation_id: str,
        user_id: int,
        action: ActionInput,
        graph_thread_id: str | None = None,
    ) -> PendingInput:
        """会话执行租约内替换旧表单，部分唯一索引禁止多个活动表单。"""
        await asyncio.to_thread(self.indexes.ensure)
        now = datetime.now(timezone.utc)
        await asyncio.to_thread(
            self.collection.update_many,
            self.scope(
                {
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "status": "pending",
                }
            ),
            {"$set": {"status": "canceled"}},
        )
        row = {
            "_id": str(uuid4()),
            "record_type": self.record_type,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "payload": action.model_dump(),
            "status": "pending",
            "graph_thread_id": graph_thread_id,
            "created_at": now,
            "updated_at": now,
        }
        await asyncio.to_thread(self.collection.insert_one, row)
        return self._record(row)

    async def get(self, request_id: str, user_id: int) -> PendingInput | None:
        """同时匹配请求和已验证导师 ID。"""
        return self._record(
            await asyncio.to_thread(
                self.collection.find_one,
                self.scope({"_id": request_id, "user_id": user_id}),
            )
        )

    async def latest_pending(
        self, conversation_id: str, user_id: int
    ) -> PendingInput | None:
        """读取当前会话的活动表单。"""
        return self._record(
            await asyncio.to_thread(
                self.collection.find_one,
                self.scope(
                    {
                        "conversation_id": conversation_id,
                        "user_id": user_id,
                        "status": "pending",
                    }
                ),
                sort=[("created_at", -1)],
            )
        )

    async def transition(
        self, request_id: str, user_id: int, old: str, new: str
    ) -> bool:
        """原子消费待补表单，重复提交返回 False。"""
        if old != "pending" or new not in {"completed", "canceled"}:
            raise ValueError("无效的待补字段状态流转")
        result = await asyncio.to_thread(
            self.collection.update_one,
            self.scope({"_id": request_id, "user_id": user_id, "status": old}),
            {"$set": {"status": new, "updated_at": datetime.now(timezone.utc)}},
        )
        return result.modified_count == 1
