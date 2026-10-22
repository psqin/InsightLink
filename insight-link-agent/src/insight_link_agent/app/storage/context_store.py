"""供 DeepAgents StoreBackend 使用的 MongoDB 会话文件存储。"""

import asyncio
from datetime import datetime, timezone

from bson import BSON
from langgraph.store.base import BaseStore, GetOp, Item, PutOp, SearchItem, SearchOp
from pymongo import IndexModel

from insight_link_agent.app.storage.indexes import DeferredIndexes


class MongoContextStore(BaseStore):
    """只实现虚拟文件所需的精确读写和分页枚举，不提供跨导师检索。

    范围来自服务端已验证的身份和会话，模型只能提供范围内的文件路径。
    这里的文件是上下文原文归档，不进入长期偏好记忆，也不执行宿主机代码。
    """

    MAX_DOCUMENT_BYTES = 12 * 1024 * 1024
    NAMESPACE = ("context",)

    def __init__(self, collection, user_id: int, conversation_id: str, branch: str):
        """固定当前存储实例的访问范围，禁止调用方通过 namespace 切换导师。"""
        if user_id <= 0 or not conversation_id or branch not in {"private", "public"}:
            raise ValueError("上下文归档需要有效导师、会话及分支")
        self.collection = collection
        self.scope = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "branch": branch,
        }
        self.indexes = DeferredIndexes(
            collection,
            IndexModel(
                [("user_id", 1), ("conversation_id", 1), ("branch", 1), ("key", 1)],
                unique=True,
            ),
        )

    def _item(self, row, *, search=False):
        """把 Mongo 文档转为框架文件条目，不把数据库内部字段交给模型。"""
        values = dict(
            namespace=self.NAMESPACE,
            key=row["key"],
            value=row["value"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        return SearchItem(**values) if search else Item(**values)

    def batch(self, ops):
        """依序执行文件操作；不支持的通用 Store 能力显式拒绝。"""
        results = []
        for op in ops:
            namespace = (
                op.namespace_prefix
                if isinstance(op, SearchOp)
                else getattr(op, "namespace", None)
            )
            if namespace != self.NAMESPACE:
                raise PermissionError("禁止访问当前会话以外的上下文命名空间")
            if isinstance(op, GetOp):
                row = self.collection.find_one({**self.scope, "key": op.key})
                results.append(self._item(row) if row else None)
            elif isinstance(op, PutOp):
                if op.ttl is not None:
                    raise ValueError("上下文归档不支持单文件 TTL")
                query = {**self.scope, "key": op.key}
                if op.value is None:
                    self.collection.delete_one(query)
                else:
                    self.indexes.ensure()
                    stamp = datetime.now(timezone.utc)
                    document = {**query, "value": op.value, "updated_at": stamp}
                    # 为 Mongo 的 16 MiB 文档上限留余量；超限不覆盖已保存的历史。
                    if len(BSON.encode(document)) > self.MAX_DOCUMENT_BYTES:
                        raise ValueError("上下文归档文件超过 12 MiB，请新建会话")
                    self.collection.update_one(
                        query,
                        {"$set": document, "$setOnInsert": {"created_at": stamp}},
                        upsert=True,
                    )
                results.append(None)
            elif isinstance(op, SearchOp):
                if op.query or op.filter:
                    raise NotImplementedError("上下文文件只支持精确命名空间分页枚举")
                if op.offset < 0 or op.limit < 0:
                    raise ValueError("分页参数不能为负数")
                rows = (
                    (
                        self.collection.find(self.scope)
                        .sort("key", 1)
                        .skip(op.offset)
                        .limit(op.limit)
                    )
                    if op.limit
                    else []
                )
                results.append([self._item(row, search=True) for row in rows])
            else:
                raise NotImplementedError("上下文存储不支持此类操作")
        return results

    async def abatch(self, ops):
        """同步 Mongo 驱动在线程中运行，避免阻塞聊天事件循环。"""
        return await asyncio.to_thread(self.batch, list(ops))
