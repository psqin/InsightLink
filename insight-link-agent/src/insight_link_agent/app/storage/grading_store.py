"""导师评分标准的永久 Mongo 配置，不使用聊天或长期记忆的 TTL。"""

import asyncio
import re
from datetime import datetime, timezone

from pymongo import IndexModel, ReturnDocument
from pymongo.errors import DuplicateKeyError

from insight_link_agent.agent.evaluation.harness_policy import load_review_rubrics
from insight_link_agent.agent.grading.policy import GradingStandardSnapshot
from insight_link_agent.app.storage.indexes import DeferredIndexes


class GradingConflict(ValueError):
    """当前评分标准已被其他请求修改。"""


class GradingStandardStore:
    """每位导师一份当前配置，原子更新并保留最近十次历史，无自动过期。"""

    def __init__(self, collection):
        self.collection = collection
        self.indexes = DeferredIndexes(collection, IndexModel("user_id", unique=True))

    async def get(self, user_id: int) -> dict:
        """未配置时返回虚拟默认版本，不为所有导师预写一份重复量表。"""
        if type(user_id) is not int or user_id <= 0:
            raise ValueError("评分标准需要已验证的导师身份")
        row = await asyncio.to_thread(
            self.collection.find_one, {"_id": user_id, "user_id": user_id}
        )
        return self._public(row)

    @staticmethod
    def _public(row) -> dict:
        """页面和工具只取得当前配置，不暴露数据库键或他人的配置。"""
        return {
            "source": "custom" if row and row.get("content") else "default",
            "content": row.get("content") if row else None,
            "version": row.get("version", 0) if row else 0,
            "updated_at": row["updated_at"].isoformat() if row else None,
        }

    async def update(
        self, user_id: int, content: str | None, expected_version: int
    ) -> dict:
        """None 恢复默认；完整内容替换当前标准，禁止无版本覆盖与空文本保存。

        前置读取用于生成替换历史，真正防并发覆盖的是更新条件中的 version。
        首次保存以导师 ID 为唯一键；并发 upsert 的重复键也按版本冲突处理，
        不覆盖另一请求已保存的标准。默认量表只返回，不为每位导师预写副本。
        """
        current = await self.get(user_id)
        if content is not None:
            content = content.strip()
            if not content or len(content) > 4000:
                raise ValueError("评分标准须为 1–4000 字的完整内容")
            if not re.search(r"[^\W_]", content, re.UNICODE):
                raise ValueError("请填写具体的评分维度或要求，不能仅包含标点")
        if current["version"] != expected_version:
            raise GradingConflict("评分标准已更新，请重新查看后再保存")
        if current["content"] == content:
            return current
        await asyncio.to_thread(self.indexes.ensure)
        now = datetime.now(timezone.utc)
        try:
            row = await asyncio.to_thread(
                self.collection.find_one_and_update,
                {"_id": user_id, "user_id": user_id, "version": expected_version},
                {
                    "$set": {"user_id": user_id, "content": content, "updated_at": now},
                    "$inc": {"version": 1},
                    "$push": {
                        "history": {
                            "$each": [
                                {
                                    "content": current["content"],
                                    "version": expected_version,
                                    "replaced_at": now,
                                }
                            ],
                            "$slice": -10,
                        }
                    },
                },
                upsert=expected_version == 0,
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError as exc:
            raise GradingConflict("评分标准已更新，请重新查看后再保存") from exc
        if row is None:
            raise GradingConflict("评分标准已更新，请重新查看后再保存")
        return self._public(row)

    async def snapshot(
        self, user_id: int, material_type: int
    ) -> GradingStandardSnapshot:
        """每次评分读取最新配置，一轮生成与复核固定使用此快照。"""
        current = await self.get(user_id)
        scoring = load_review_rubrics().scoring
        if material_type not in scoring:
            raise ValueError(f"未知的材料类型: {material_type}")
        content = current["content"] or scoring[material_type]
        return GradingStandardSnapshot(
            source=current["source"], version=current["version"], content=content
        )


def defaults() -> list[dict]:
    """默认按材料类型选择；导师自定义标准替换评分维度，固定证据底线仍生效。"""
    names = {1: "学习计划", 2: "进度汇报", 3: "自我总结"}
    return [
        {"material_type": kind, "label": names[kind], "content": value}
        for kind, value in load_review_rubrics().scoring.items()
    ]
