"""待补字段与待确认操作共用集合，使用 record_type 严格隔离。"""

from pymongo import IndexModel

from insight_link_agent.app.storage.indexes import DeferredIndexes
from insight_link_agent.app.storage.mongo_store import MongoCollectionStore


def interaction_indexes(collection):
    """同一导师会话每种交互只能有一个 pending，两个类型互不覆盖。"""
    return DeferredIndexes(
        collection,
        IndexModel(
            [("conversation_id", 1), ("user_id", 1), ("record_type", 1)],
            unique=True,
            partialFilterExpression={"status": "pending"},
        ),
        IndexModel(
            [
                ("user_id", 1),
                ("conversation_id", 1),
                ("record_type", 1),
                ("updated_at", -1),
            ]
        ),
    )


class InteractionStore(MongoCollectionStore):
    """统一交互集合的类型过滤和延迟索引，业务状态机仍由各子类维护。"""

    record_type: str

    def __init__(self, collection):
        super().__init__(collection)
        self.indexes = interaction_indexes(collection)

    def scope(self, fields):
        """每次读写强制限定记录类型，防止表单 ID 被当成审批 ID。"""
        return {**fields, "record_type": self.record_type}
