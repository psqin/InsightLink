"""MongoDB 中的正式点评任务归属与状态。"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from insight_link_agent.app.storage.mongo_store import MongoCollectionStore


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    user_id: int
    material_id: int
    status: str


class RunStore(MongoCollectionStore):
    """任务归属与检查点分集合保存，API 恢复前复核导师和材料权限。"""

    async def create(self, run_id: str, user_id: int, material_id: int) -> None:
        """插入新任务，不覆盖已有任务身份。"""
        now = datetime.now(timezone.utc)
        await asyncio.to_thread(
            self.collection.insert_one,
            {
                "_id": run_id,
                "user_id": user_id,
                "material_id": material_id,
                "status": "running",
                "created_at": now,
                "updated_at": now,
            },
        )

    async def get(self, run_id: str) -> RunRecord | None:
        """读取任务元数据，供 HTTP 层执行归属检查。"""
        row = await asyncio.to_thread(self.collection.find_one, {"_id": run_id})
        return (
            RunRecord(row["_id"], row["user_id"], row["material_id"], row["status"])
            if row
            else None
        )

    async def set_status(self, run_id: str, status: str) -> None:
        """更新状态而不修改任务归属。"""
        await asyncio.to_thread(
            self.collection.update_one,
            {"_id": run_id},
            {
                "$set": {"status": status, "updated_at": datetime.now(timezone.utc)},
            },
        )

    async def claim_approval(self, run_id: str) -> bool:
        """原子领取审批权，阻止重复图恢复。"""
        result = await asyncio.to_thread(
            self.collection.update_one,
            {"_id": run_id, "status": "awaiting_approval"},
            {"$set": {"status": "resuming", "updated_at": datetime.now(timezone.utc)}},
        )
        return result.modified_count == 1
