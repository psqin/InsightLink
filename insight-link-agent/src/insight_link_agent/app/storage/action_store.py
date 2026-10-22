"""MongoDB 中一次性审批记录；不保存请求 token。"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from insight_link_agent.agent.conversation.actions import (
    ActionProposal,
    ExecutionReceipt,
)
from insight_link_agent.app.storage.interaction_store import InteractionStore


@dataclass(frozen=True)
class PendingAction:
    id: str
    conversation_id: str
    user_id: int
    conversation_version: int
    proposal: ActionProposal
    status: str
    graph_thread_id: str | None = None

    def public(self) -> dict:
        """只向页面公开预览及审批 ID。"""
        return {"id": self.id, **self.proposal.preview()}


class ActionStore(InteractionStore):
    """用单文档条件更新领取执行权，保持十五分钟确认有效期。

    与补字段记录共用 interactions 集合，所有查询经 scope 附带 record_type，
    防止相同会话中的另一类记录被误领取。领取成功只表示可以执行；必须等
    Java 明确返回业务成功，确认入口才可把 executing 更新为 completed。
    """

    record_type = "action"

    @staticmethod
    def _record(row):
        """将持久快照转换为业务提案。"""
        return (
            PendingAction(
                row["_id"],
                row["conversation_id"],
                row["user_id"],
                row["conversation_version"],
                ActionProposal.model_validate(row["payload"]),
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
        conversation_version: int,
        proposal: ActionProposal,
        graph_thread_id: str | None = None,
    ) -> PendingAction:
        """租约内替换旧预览，取消旧记录但保留审计状态。"""
        now = datetime.now(timezone.utc)
        await asyncio.to_thread(self.indexes.ensure)
        await asyncio.to_thread(
            self.collection.update_many,
            self.scope(
                {
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "status": "pending",
                }
            ),
            {"$set": {"status": "canceled", "updated_at": now}},
        )
        row = {
            "_id": str(uuid4()),
            "record_type": self.record_type,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "conversation_version": conversation_version,
            "payload": proposal.model_dump(),
            "status": "pending",
            "created_at": now,
            "updated_at": now,
            "graph_thread_id": graph_thread_id,
        }
        await asyncio.to_thread(self.collection.insert_one, row)
        return self._record(row)

    async def get(self, action_id: str, user_id: int) -> PendingAction | None:
        """按审批 ID 与导师 ID 读取，避免跨导师审批。"""
        return self._record(
            await asyncio.to_thread(
                self.collection.find_one,
                self.scope({"_id": action_id, "user_id": user_id}),
            )
        )

    async def latest_pending(
        self, conversation_id: str, user_id: int
    ) -> PendingAction | None:
        """恢复当前会话的活动预览。"""
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

    async def completed_receipts(
        self, conversation_id: str, user_id: int
    ) -> list[ExecutionReceipt]:
        """按导师和会话读取最近成功操作，区分 API 执行回执与模型自述。

        只接受 completed，pending/executing/failed 均不能作为成功证据。
        摘要不包含留言正文、评分或凭据，足以核对已经完成的操作类型和对象。
        """

        def load():
            rows = (
                self.collection.find(
                    self.scope(
                        {
                            "conversation_id": conversation_id,
                            "user_id": user_id,
                            "status": "completed",
                        }
                    )
                )
                .sort("updated_at", -1)
                .limit(5)
            )
            receipts = []
            for row in rows:
                proposal = ActionProposal.model_validate(row["payload"])
                target = proposal.target_name
                title = proposal.target_title
                summary = (
                    f"已向{target}发送留言。"
                    if proposal.kind == "send_student_message"
                    else f"已为{target}的《{title}》"
                    + {
                        "create_evaluation": "新增能力评价。",
                        "update_evaluation": "修改能力评价。",
                        "delete_evaluation": "删除能力评价。",
                    }[proposal.kind]
                )
                completed_at = row["updated_at"]
                if completed_at.tzinfo is None:
                    completed_at = completed_at.replace(tzinfo=timezone.utc)
                receipts.append(
                    ExecutionReceipt(
                        action_id=row["_id"],
                        kind=proposal.kind,
                        completed_at=completed_at.astimezone(
                            timezone(timedelta(hours=8))
                        ).isoformat(),
                        summary=summary,
                        target_name=target,
                    )
                )
            return receipts

        return await asyncio.to_thread(load)

    async def transition(
        self, action_id: str, user_id: int, old: str, new: str
    ) -> bool:
        """状态比较交换；只有未过期的 pending 才能领取执行权。

        数据库按导师、记录类型和旧状态原子匹配，重复点击只会有一个请求
        领取成功。executing 不能回退 pending；外部写入结果不明时不能据此
        自动重发，因为 Java 写入和 Mongo 状态更新并非同一个事务。
        """
        if new not in {
            "pending": {"executing", "canceled"},
            "executing": {"completed", "failed"},
        }.get(old, set()):
            raise ValueError("无效的审批状态流转")
        now = datetime.now(timezone.utc)
        query = self.scope({"_id": action_id, "user_id": user_id, "status": old})
        if new == "executing":
            query["created_at"] = {"$gte": now - timedelta(minutes=15)}
        result = await asyncio.to_thread(
            self.collection.update_one,
            query,
            {"$set": {"status": new, "updated_at": now}},
        )
        return result.modified_count == 1
