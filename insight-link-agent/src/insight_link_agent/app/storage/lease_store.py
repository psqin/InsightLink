"""MongoDB 会话租约：跨请求、跨进程保护同一图执行。"""

import asyncio
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from pymongo import IndexModel
from pymongo.errors import DuplicateKeyError

from insight_link_agent.app.storage.indexes import DeferredIndexes
from insight_link_agent.app.storage.mongo_store import MongoCollectionStore


class ConversationBusy(RuntimeError):
    """当前会话已被另一请求领取。"""


@dataclass(frozen=True)
class LeaseTicket:
    """本轮持有证明；lost 只表示失去所有权，正常退出不会置位。"""

    resource: str
    owner: str
    lost: asyncio.Event = field(default_factory=asyncio.Event)


async def _settle(task: asyncio.Task):
    """收尾阶段不接受重复取消，避免 Mongo 线程尚未完成便宣布租约已释放。

    这里只等待 Mongo 客户端已设置超时的操作和 heartbeat 退出；业务运行本身
    不会被 shield。调用方负责在收尾成功后继续传播原先的取消异常。
    """
    while True:
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            if task.done():
                return task.result()


class ConversationLeaseStore(MongoCollectionStore):
    """原子领取、定期续期；崩溃后两分钟过期，不依赖 TTL 及时删除。"""

    HEARTBEAT_SECONDS = 20
    LEASE_SECONDS = 120

    def __init__(self, collection):
        """租约首次使用时才创建集合和 TTL 索引，仍保留跨进程互斥。"""
        super().__init__(collection)
        self.indexes = DeferredIndexes(
            collection, IndexModel("expires_at", expireAfterSeconds=0)
        )

    async def _renew(self, ticket: LeaseTicket):
        """仅续期未过期且仍属于自己的租约，任何不确定性都通知运行器停止。

        Mongo update 成功不代表更新到记录，必须检查 matched_count。连接异常、
        TTL 删除、租约过期或其他持有者接管都意味着不能再安全执行同一张图。
        """
        while True:
            await asyncio.sleep(self.HEARTBEAT_SECONDS)
            now = datetime.now(timezone.utc)
            renewal = asyncio.create_task(
                asyncio.to_thread(
                    self.collection.update_one,
                    {
                        "_id": ticket.resource,
                        "owner": ticket.owner,
                        "expires_at": {"$gt": now},
                    },
                    {
                        "$set": {
                            "expires_at": now + timedelta(seconds=self.LEASE_SECONDS)
                        }
                    },
                )
            )
            try:
                result = await asyncio.shield(renewal)
                if result.matched_count != 1:
                    ticket.lost.set()
                    return
            except asyncio.CancelledError:
                # 取消 to_thread 的等待不会停止工作线程。先等本次续租结束，再允许
                # hold 的 finally 删除租约，避免留下仍在运行的续租操作。
                with suppress(Exception):
                    await _settle(renewal)
                raise
            except Exception:
                ticket.lost.set()
                return

    async def _release(
        self, ticket: LeaseTicket, heartbeat: asyncio.Task | None = None
    ):
        """先结束 heartbeat，再按 owner 删除；不能删除后来接管者的租约。"""
        try:
            if heartbeat is not None:
                heartbeat.cancel()
                with suppress(asyncio.CancelledError):
                    await heartbeat
        finally:
            await asyncio.to_thread(
                self.collection.delete_one,
                {"_id": ticket.resource, "owner": ticket.owner},
            )

    @asynccontextmanager
    async def hold(self, user_id: int, conversation_id: str):
        """活跃租约导致 _id 唯一键冲突，过期租约可被新请求原子替换。"""
        await asyncio.to_thread(self.indexes.ensure)
        resource, owner = f"{user_id}:{conversation_id}", uuid4().hex
        ticket = LeaseTicket(resource, owner)
        now = datetime.now(timezone.utc)
        claim = asyncio.create_task(
            asyncio.to_thread(
                self.collection.update_one,
                {"_id": resource, "expires_at": {"$lte": now}},
                {
                    "$set": {
                        "owner": owner,
                        "expires_at": now + timedelta(seconds=self.LEASE_SECONDS),
                    }
                },
                upsert=True,
            )
        )
        try:
            await asyncio.shield(claim)
        except DuplicateKeyError as exc:
            raise ConversationBusy("当前对话正在处理，请等待完成后重试") from exc
        except asyncio.CancelledError:
            # 数据库线程可能已成功领取，但 await 尚未把结果交给本请求。必须先
            # 确认线程结束，再按本轮 owner 删除；否则取消会遗留一个两分钟锁。
            try:
                with suppress(Exception):
                    await _settle(claim)
            finally:
                await _settle(asyncio.create_task(self._release(ticket)))
            raise
        heartbeat = asyncio.create_task(self._renew(ticket))
        try:
            yield ticket
        finally:
            await _settle(asyncio.create_task(self._release(ticket, heartbeat)))
