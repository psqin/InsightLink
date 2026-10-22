"""MongoDB 二进制产物：导师隔离、格式限制与三十天过期。"""

import asyncio
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from insight_link_agent.app.storage.mongo_store import MongoCollectionStore

MIME = {
    ".png": "image/png",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".csv": "text/csv",
    ".txt": "text/plain",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".md": "text/markdown",
    ".html": "text/html",
    ".json": "application/json",
}


class ArtifactStore(MongoCollectionStore):
    """单文件最大 4 MB，含元数据的 BSON 文档低于 MongoDB 16 MB 上限。"""

    async def create(self, user_id: int, name: str, content: bytes) -> dict:
        """净化文件名并保存内容；不接受宿主文件路径。"""
        suffix = Path(name).suffix.lower()
        if suffix not in MIME or not 0 < len(content) <= 4_000_000:
            raise ValueError("文件格式或大小不受支持")
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", Path(name).name)[:100]
        now = datetime.now(timezone.utc)
        row = {
            "_id": str(uuid4()),
            "user_id": user_id,
            "name": safe_name,
            "mime": MIME[suffix],
            "content": bytes(content),
            "created_at": now,
            "expires_at": now + timedelta(days=30),
        }
        await asyncio.to_thread(self.collection.insert_one, row)
        return {
            "id": row["_id"],
            "name": safe_name,
            "mime": row["mime"],
            "size": len(content),
        }

    async def get(self, artifact_id: str, user_id: int):
        """应用层也检查有效期，避免 TTL 后台删除延迟导致过期文件可读。"""
        row = await asyncio.to_thread(
            self.collection.find_one,
            {
                "_id": artifact_id,
                "user_id": user_id,
                "expires_at": {"$gt": datetime.now(timezone.utc)},
            },
        )
        return (row["name"], row["mime"], bytes(row["content"])) if row else None
