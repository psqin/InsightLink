"""HOT：MongoDB 中按导师隔离的当前会话和消息。会话和消息由统一 MongoDB 连接管理。"""

import asyncio
import logging
import re
from collections.abc import Sequence
from datetime import datetime, timezone

from pymongo import ReturnDocument

from insight_link_agent.agent.conversation.models import Conversation
from insight_link_agent.agent.execution.context import begin_commit
from insight_link_agent.agent.memory.keeper import MemoryKeeper

logger = logging.getLogger(__name__)


def _stamp() -> str:
    """统一使用 UTC ISO 时间，供会话列表按更新时间排序。"""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class MongoChatStore:
    """持久化 HOT 对话；所有会话读取入口按已验证的导师 ID 限定。"""

    def __init__(self, chats, memories):
        self.chats = chats
        self.memories = memories

    async def open(self) -> None:
        """Mongo 连接与索引由 MongoRuntimeStore 启动时统一初始化。"""
        # 索引由 MongoRuntimeStore.open() 统一建立。
        return None

    async def close(self) -> None:
        """集合不持有独立连接，关闭动作交给 MongoRuntimeStore。"""
        return None

    @staticmethod
    def _conversation(doc: dict) -> Conversation:
        """将数据库字段映射为 API 使用的会话快照。"""
        return Conversation(
            doc["_id"],
            doc["user_id"],
            doc.get("material_id"),
            doc["version"],
            doc["created_at"],
            doc["updated_at"],
            doc.get("title"),
        )

    async def search_conversations(
        self,
        user_id: int,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: str = "",
    ) -> tuple[list[Conversation], int]:
        """在数据库中分页搜索标题；仅投影摘要，绝不扫描并返回消息正文。"""
        if page < 1 or not 1 <= page_size <= 50:
            raise ValueError("会话页码或每页数量无效")
        query = {"user_id": user_id, "deleted_at": {"$exists": False}}
        if keyword.strip():
            # 用户搜索词按字面量匹配，不能把正则表达式提交给数据库执行。
            query["title"] = {
                "$regex": re.escape(keyword.strip()[:100]),
                "$options": "i",
            }

        def load():
            total = self.chats.count_documents(query)
            cursor = self.chats.find(
                query,
                {
                    "user_id": 1,
                    "material_id": 1,
                    "version": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "title": 1,
                },
            ).sort([("updated_at", -1), ("_id", -1)])
            return [
                self._conversation(doc)
                for doc in cursor.skip((page - 1) * page_size).limit(page_size)
            ], total

        return await asyncio.to_thread(load)

    async def get(self, conversation_id: str, user_id: int) -> Conversation | None:
        """同时匹配会话 ID 与导师 ID，避免跨导师取得会话。"""
        doc = await asyncio.to_thread(
            self.chats.find_one,
            {
                "_id": conversation_id,
                "user_id": user_id,
                "deleted_at": {"$exists": False},
            },
            {"messages": 0, "harness": 0},
        )
        return self._conversation(doc) if doc else None

    async def messages(self, conversation_id: str) -> list[dict]:
        """读取已完成归属检查的会话消息；调用方先执行 get。"""
        doc = await asyncio.to_thread(
            self.chats.find_one,
            {"_id": conversation_id, "deleted_at": {"$exists": False}},
            {"messages": 1},
        )
        return list(doc.get("messages", [])) if doc else []

    async def rename(self, conversation_id: str, user_id: int, title: str) -> bool:
        """修改导师自己的会话标题；不增加业务版本，避免使已核对的预览失效。"""
        result = await asyncio.to_thread(
            self.chats.update_one,
            {
                "_id": conversation_id,
                "user_id": user_id,
                "deleted_at": {"$exists": False},
            },
            {"$set": {"title": title, "updated_at": _stamp()}},
        )
        return bool(result.matched_count)

    async def soft_delete(self, conversation_id: str, user_id: int) -> bool:
        """隐藏会话入口并阻止继续执行；保留正式操作日志、检查点和有效长期记忆。"""
        result = await asyncio.to_thread(
            self.chats.update_one,
            {
                "_id": conversation_id,
                "user_id": user_id,
                "deleted_at": {"$exists": False},
            },
            {"$set": {"deleted_at": _stamp()}},
        )
        return bool(result.matched_count)

    def _remember(
        self,
        user_id: int,
        conversation_id: str,
        tool_names: Sequence[str],
    ) -> None:
        """HOT 保存成功后归档脱敏情节；长期写入失败不丢失当前会话。"""
        try:
            MemoryKeeper(self.memories, user_id).record_turn(
                conversation_id,
                tool_names,
            )
        except Exception:
            logger.exception("跨会话记忆写入失败；HOT 对话已保存")

    async def create_empty(
        self, user_id: int, material_id: int | None, conversation_id: str
    ) -> None:
        """预留导师会话；模型首轮失败时保留恢复入口，不写入伪答复。"""
        now = _stamp()
        await asyncio.to_thread(
            self.chats.insert_one,
            {
                "_id": conversation_id,
                "user_id": user_id,
                "material_id": material_id,
                "version": 0,
                "created_at": now,
                "updated_at": now,
                "messages": [],
            },
        )

    async def append_turn(
        self,
        conversation: Conversation,
        question: str,
        answer: str,
        material_id: int | None = None,
        tool_names: Sequence[str] = (),
    ) -> bool:
        """按版本号乐观锁追加一轮对话，版本冲突时返回 False。"""
        # 同一个 CAS 决定停止还是保存获胜；进入提交后只能等待结果，不能伪称撤回。
        await begin_commit()

        def update():
            data = {"updated_at": _stamp()}
            if conversation.version == 0 and not conversation.title:
                data["title"] = question.strip()[:80]
            if conversation.material_id is None and material_id is not None:
                data["material_id"] = material_id
            return self.chats.find_one_and_update(
                {
                    "_id": conversation.id,
                    "user_id": conversation.user_id,
                    "version": conversation.version,
                    "deleted_at": {"$exists": False},
                },
                {
                    "$set": data,
                    "$inc": {"version": 1},
                    "$push": {
                        "messages": {
                            "$each": [
                                {"role": "user", "content": question},
                                {"role": "assistant", "content": answer},
                            ],
                            "$slice": -100,
                        }
                    },
                },
                return_document=ReturnDocument.AFTER,
            )

        changed = await asyncio.to_thread(update)
        if changed is None:
            return False
        await asyncio.to_thread(
            self._remember,
            conversation.user_id,
            conversation.id,
            tool_names,
        )
        return True
