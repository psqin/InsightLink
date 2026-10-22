"""统一的长期记忆写入口：偏好版本、去敏情节、规则和遗忘。"""

import time
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from insight_link_agent.agent.memory.config import DEFAULT_MEMORY_CONFIG, MemoryConfig
from insight_link_agent.agent.memory.extractor import summarize_episode
from insight_link_agent.agent.memory.scoring import rank

PREFERENCE_VALUES = {
    "language": {"中文", "英文"},
    "style": {"简洁", "详细"},
    "format": {"表格", "列表", "段落"},
    "evaluation_method": {"先列证据再评价", "给出具体改进建议"},
}
PROCEDURE_VALUES = {
    "evaluation_method": PREFERENCE_VALUES["evaluation_method"],
    "chart_method": {"图表标注数据来源", "图表区分未评分材料"},
    "report_method": {"报告区分事实与建议", "报告列出证据来源"},
}
_LAST_SWEEP: dict[tuple[int, int], float] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MemoryKeeper:
    """和 ERP-AGENT 一样提供单一写入口，但限制学业场景的跨会话字段。"""

    def __init__(
        self,
        collection,
        user_id: int,
        config: MemoryConfig = DEFAULT_MEMORY_CONFIG,
    ):
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("长期记忆需要经过验证的导师 ID")
        self.collection = collection
        self.user_id = user_id
        self.config = config

    def _items(self, types: list[str], limit: int | None = None) -> list[dict]:
        """按导师、记忆类型及有效期过滤可见记录。"""
        return list(
            self.collection.find(
                {
                    "user_id": self.user_id,
                    "type": {"$in": types},
                    "$or": [
                        {"expires_at": {"$exists": False}},
                        {"expires_at": {"$gt": _now()}},
                    ],
                }
            )
            .sort("updated_at", -1)
            .limit(limit or self.config.max_candidates)
        )

    def remember(self, key: str, value: str, conversation_id: str) -> bool:
        """只写入白名单偏好；变更前将上一版本转入有限历史。"""
        if value not in PREFERENCE_VALUES.get(key, set()):
            return False
        now = _now()
        current_id = f"sem:{self.user_id}:{key}"
        current = self.collection.find_one({"_id": current_id, "user_id": self.user_id})
        if current and current.get("content") == value:
            return True
        if current:
            self.collection.insert_one(
                {
                    **{
                        field: item for field, item in current.items() if field != "_id"
                    },
                    "_id": f"hist:{self.user_id}:{key}:{uuid4().hex}",
                    "type": "semantic_history",
                    "invalidated_at": now,
                }
            )
        self.collection.replace_one(
            {"_id": current_id, "user_id": self.user_id},
            {
                "_id": current_id,
                "user_id": self.user_id,
                "type": "semantic",
                "key": key,
                "content": value,
                "confidence": 0.9,
                "source_conversation_id": conversation_id,
                "created_at": current.get("created_at", now) if current else now,
                "valid_from": now,
                "updated_at": now,
                "access_count": 0,
                "schema_version": 2,
            },
            upsert=True,
        )
        if key == "evaluation_method":
            # 这类导师原话本身是明确的方法约定，才同步进入程序记忆。
            self.remember_procedure(key, value, conversation_id)
        # 被取代版本最多保留三条。
        history = list(
            self.collection.find(
                {
                    "user_id": self.user_id,
                    "type": "semantic_history",
                    "key": key,
                }
            )
            .sort("updated_at", -1)
            .skip(self.config.max_semantic_history)
        )
        if history:
            self.collection.delete_many(
                {"_id": {"$in": [item["_id"] for item in history]}}
            )
        return True

    def remember_procedure(self, key: str, value: str, conversation_id: str) -> bool:
        """只保存导师明确要求的预设方法，不接受模型自由编造的业务规则。"""
        if value not in PROCEDURE_VALUES.get(key, set()):
            return False
        now = _now()
        record_id = f"rule:{self.user_id}:{key}"
        existing = self.collection.find_one({"_id": record_id, "user_id": self.user_id})
        self.collection.replace_one(
            {"_id": record_id, "user_id": self.user_id},
            {
                "_id": record_id,
                "user_id": self.user_id,
                "type": "procedural",
                "key": key,
                "content": value,
                "confidence": 0.9,
                "source_conversation_id": conversation_id,
                "created_at": existing.get("created_at", now) if existing else now,
                "updated_at": now,
                "access_count": existing.get("access_count", 0) if existing else 0,
                "schema_version": 2,
            },
            upsert=True,
        )
        return True

    def record_turn(self, conversation_id: str, tool_names: Sequence[str] = ()) -> None:
        """HOT提交后按真实工具归档去敏情节；偏好仅由remember工具明确写入。"""
        episode = summarize_episode(tool_names)
        if episode:
            now = _now()
            self.collection.update_one(
                {
                    "_id": f"ep:{self.user_id}:{conversation_id}",
                    "user_id": self.user_id,
                },
                {
                    "$set": {
                        "user_id": self.user_id,
                        "type": "episodic",
                        "key": conversation_id,
                        "content": episode["summary"],
                        "summary": episode["summary"],
                        "task_type": episode["task_type"],
                        "goal": episode["goal"],
                        "outcome": episode["outcome"],
                        "tools": episode["tools"],
                        "confidence": 0.8,
                        "updated_at": now,
                        "expires_at": now
                        + timedelta(days=self.config.episode_ttl_days),
                        "schema_version": 2,
                    },
                    "$setOnInsert": {"access_count": 0, "created_at": now},
                },
                upsert=True,
            )
        self.forget()

    def warm_brief(self) -> str:
        """只注入有效语义偏好和近七天情节；更早情节留待 COLD 检索。"""
        now = _now()
        warm_start = now - timedelta(days=self.config.warm_episode_days)
        semantic = self._items(["semantic"], limit=20)
        episodes = [
            item
            for item in self._items(["episodic"], limit=self.config.max_warm_episodes)
            if self._aware_time(item.get("updated_at")) >= warm_start
        ]
        lines = [f"- {item['key']}：{item['content']}" for item in semantic]
        lines.extend(
            f"- 近期任务：{str(item.get('summary') or item['content'])[:160]}"
            for item in episodes
        )
        return "\n".join(lines)[: self.config.warm_brief_chars]

    @staticmethod
    def _aware_time(value) -> datetime:
        """兼容旧 Mongo 文档中的无时区时间；缺失时间不进入 WARM。"""
        if not isinstance(value, datetime):
            return datetime.min.replace(tzinfo=timezone.utc)
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    def search_text(self, query: str, limit: int | None = None) -> str:
        """按需检索 COLD 记忆并记录命中次数，不访问学生业务事实。"""
        candidates = self._items(["semantic", "episodic", "procedural"])
        requested = self.config.retrieval_k if limit is None else limit
        hits = rank(query, candidates)[
            : max(1, min(requested, self.config.max_retrieval_k))
        ]
        if not hits:
            return "没有找到相关的历史记忆。"
        self.collection.update_many(
            {
                "_id": {"$in": [item["_id"] for item, _ in hits]},
                "user_id": self.user_id,
            },
            {"$inc": {"access_count": 1}},
        )
        return "检索到的历史记忆：\n" + "\n".join(
            f"{index}. [{item['type']}] {item.get('summary') or item['content']}"
            for index, (item, _) in enumerate(hits, 1)
        )

    def forget(self, *, force: bool = False) -> None:
        """定期清理过期情节，并限制每位导师保留的情节数量。"""
        sweep_key = (id(self.collection), self.user_id)
        if (
            not force
            and time.monotonic() - _LAST_SWEEP.get(sweep_key, 0)
            < self.config.sweep_interval_seconds
        ):
            return
        _LAST_SWEEP[sweep_key] = time.monotonic()
        self.collection.delete_many(
            {"user_id": self.user_id, "expires_at": {"$lte": _now()}}
        )
        stale = list(
            self.collection.find({"user_id": self.user_id, "type": "episodic"})
            .sort("updated_at", -1)
            .skip(self.config.max_episodes)
        )
        if stale:
            self.collection.delete_many(
                {"_id": {"$in": [item["_id"] for item in stale]}}
            )
