"""会话文档只保留最新一轮去敏 Harness 结果，不再单独建立轨迹集合。"""

import asyncio
from datetime import datetime, timedelta, timezone

from insight_link_agent.app.storage.mongo_store import MongoCollectionStore


class TraceStore(MongoCollectionStore):
    """完整执行状态在检查点中，聊天文档内嵌一个有界的页面恢复摘要。"""

    async def save(
        self, user_id: int, conversation_id: str, turn: int, summary: dict
    ) -> None:
        """只保存明确列出的公开摘要字段，避免调用方误传完整图状态。"""
        fields = {
            key: summary.get(key)
            for key in (
                "task_type",
                "phase",
                "review_status",
                "review_iterations",
                "checks",
                "delivery_status",
                "signals",
                "plan",
                "plan_steps",
                "plan_source",
                "route_source",
                "route_decision",
                "trace",
                "blocked",
            )
        }
        now = datetime.now(timezone.utc)
        result = await asyncio.to_thread(
            self.collection.update_one,
            {
                "_id": conversation_id,
                "user_id": user_id,
                "$or": [
                    {"harness": {"$exists": False}},
                    {"harness.turn": {"$lte": turn}},
                ],
            },
            {
                "$set": {
                    "harness": {
                        "turn": turn,
                        "summary": fields,
                        "updated_at": now,
                        "expires_at": now + timedelta(days=30),
                    }
                }
            },
        )
        if not result.matched_count:
            # 不能通过保存轨迹创建无归属的幽灵会话；旧轮次也不能覆盖新结果。
            row = await asyncio.to_thread(
                self.collection.find_one,
                {"_id": conversation_id, "user_id": user_id},
                {"harness.turn": 1},
            )
            if row is None:
                raise ValueError("轨迹所属会话不存在或无权访问")

    async def get(self, user_id: int, conversation_id: str, turn: int):
        """仅返回当前 HOT 轮次的轨迹，不把上一轮通过冒充当前操作通过。"""
        row = await asyncio.to_thread(
            self.collection.find_one,
            {
                "_id": conversation_id,
                "user_id": user_id,
                "harness.turn": turn,
                "harness.expires_at": {"$gt": datetime.now(timezone.utc)},
            },
            {"harness.summary": 1},
        )
        return row["harness"]["summary"] if row else None
