"""会话内嵌的执行记录：取消、恢复和工具回执，不增加空业务集合。"""

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

ACTIVE = {"running", "cancel_requested", "committing"}
RESUMABLE = {"cancelled", "interrupted", "failed"}


class ExecutionConflict(ValueError):
    """执行已切换、仍在运行或结果待核实，禁止覆盖和自动重放。"""


def stamp():
    """数据库和页面使用同一个带时区的 UTC 时间格式。"""
    return datetime.now(timezone.utc).isoformat()


class ExecutionStore:
    """只保留每会话最新执行及其有界回执，身份始终来自 Java 验证结果。"""

    def __init__(self, chats, leases):
        self.chats, self.leases = chats, leases

    async def get(self, user_id, conversation_id):
        """按会话归属读取；不将其他导师是否有同名任务透露给调用方。"""
        row = await asyncio.to_thread(
            self.chats.find_one,
            {
                "_id": conversation_id,
                "user_id": user_id,
                "deleted_at": {"$exists": False},
            },
            {"execution": 1, "version": 1},
        )
        return row.get("execution") if row else None

    async def reconcile(self, user_id, conversation_id):
        """进程崩溃后，只有租约确已释放/过期才把运行记录标为中断。

        不保存 token，也不会在启动时自动使用旧凭据重跑。导师重新登录后主动恢复。
        """
        item = await self.get(user_id, conversation_id)
        if not item or item["status"] not in ACTIVE:
            return item
        lease = await asyncio.to_thread(
            self.leases.find_one,
            {
                "_id": f"{user_id}:{conversation_id}",
                "expires_at": {"$gt": datetime.now(timezone.utc)},
            },
        )
        if lease:
            return item
        row = await asyncio.to_thread(
            self.chats.find_one,
            {"_id": conversation_id, "user_id": user_id},
            {"version": 1},
        )
        committed = row and row.get("version", 0) > item["base_version"]
        await asyncio.to_thread(
            self.chats.update_one,
            {
                "_id": conversation_id,
                "user_id": user_id,
                "execution.id": item["id"],
                "execution.attempt": item["attempt"],
                "execution.status": {"$in": list(ACTIVE)},
            },
            {
                "$set": {
                    "execution.status": "completed" if committed else "interrupted",
                    "execution.updated_at": stamp(),
                    "execution.message": "结果已保存，请查看会话。"
                    if committed
                    else "执行已中断，可检查状态后恢复；结果不确定的写操作不会自动重放。",
                }
            },
        )
        return await self.get(user_id, conversation_id)

    @staticmethod
    def public(item):
        """页面不接收进程标识、工具参数、回执正文或数据库内部键。"""
        if not item:
            return None
        uncertain = any(
            receipt.get("status") == "started"
            for receipt in item.get("receipts", {}).values()
        )
        can_resume = (
            item["status"] in RESUMABLE and not uncertain and not item.get("unsafe")
        )
        message = item.get("message", "")
        if uncertain and item["status"] in RESUMABLE:
            message = "部分工具的写入结果尚待核实，为避免重复操作，不能自动恢复；可核对后开始新任务。"
        return {
            key: item[key]
            for key in (
                "id",
                "status",
                "question",
                "attempt",
                "created_at",
                "updated_at",
            )
            if key in item
        } | {"can_resume": can_resume, "message": message}

    async def begin(
        self,
        user_id,
        conversation_id,
        question,
        material_id,
        base_version,
        *,
        resume_id=None,
        attempt=None,
    ):
        """调用方先持有会话租约；同一执行恢复保留原问题和已完成工具回执。"""
        previous = await self.get(user_id, conversation_id)
        if attempt is not None and (not previous or previous["attempt"] != attempt):
            raise ExecutionConflict("任务已恢复到新的执行阶段，请刷新后操作")
        if previous and previous["status"] in ACTIVE:
            # 本方法只在租约持有者调用；旧 ACTIVE 是上一进程留下的记录。
            if previous["status"] == "committing":
                raise ExecutionConflict("上次任务的提交结果待核实，请先重新打开对话")
            previous = {**previous, "status": "interrupted"}
        resume = bool(
            previous
            and (resume_id or previous.get("question") == question)
            and previous.get("base_version") == base_version
            and previous["status"] in RESUMABLE
        )
        if resume_id and (not resume or previous["id"] != resume_id):
            raise ExecutionConflict("该任务已结束或被新任务替换，不能恢复旧任务")
        if resume and not self.public(previous)["can_resume"]:
            raise ExecutionConflict(self.public(previous)["message"])
        now = stamp()
        item = {
            "id": previous["id"] if resume else str(uuid4()),
            "status": "running",
            "question": question,
            "material_id": material_id,
            "base_version": base_version,
            "attempt": previous["attempt"] + 1 if resume else 1,
            "owner": uuid4().hex,
            "created_at": previous["created_at"] if resume else now,
            "updated_at": now,
            "receipts": previous.get("receipts", {}) if resume else {},
            "message": "任务正在处理。",
        }
        query = {
            "_id": conversation_id,
            "user_id": user_id,
            "version": base_version,
            "deleted_at": {"$exists": False},
        }
        changes = {"execution": item}
        if base_version == 0:
            # 首轮即使停止也能凭问题标题重新找到；不冒充一轮已交付的聊天。
            row = await asyncio.to_thread(
                self.chats.find_one,
                {"_id": conversation_id, "user_id": user_id},
                {"title": 1},
            )
            if row and not row.get("title"):
                changes["title"] = question.strip()[:80]
        if previous:
            query.update(self.scope(user_id, conversation_id, previous))
        else:
            query["execution"] = {"$exists": False}
        result = await asyncio.to_thread(
            self.chats.update_one, query, {"$set": changes}
        )
        if not result.matched_count:
            raise ExecutionConflict("对话已更新，请刷新后重试")
        return item, bool(
            previous and not resume and previous.get("base_version") == base_version
        )

    def scope(self, user_id, conversation_id, item):
        """每次尝试有独立所有权，迟到的旧取消/回执不得污染恢复后的新尝试。"""
        return {
            "_id": conversation_id,
            "user_id": user_id,
            "execution.id": item["id"],
            "execution.attempt": item["attempt"],
            "execution.owner": item["owner"],
        }

    async def commit(self, user_id, conversation_id, item):
        """取消与提交以同一 Mongo 状态 CAS 竞争，只有一方能获胜。"""
        query = self.scope(user_id, conversation_id, item) | {
            "execution.status": "running"
        }
        result = await asyncio.to_thread(
            self.chats.update_one,
            query,
            {
                "$set": {
                    "execution.status": "committing",
                    "execution.updated_at": stamp(),
                }
            },
        )
        if not result.matched_count:
            current = await self.get(user_id, conversation_id)
            if (
                current
                and current["id"] == item["id"]
                and current["status"] == "committing"
                and current["attempt"] == item["attempt"]
                and current["owner"] == item["owner"]
            ):
                return
            raise asyncio.CancelledError()

    async def cancel(self, user_id, conversation_id, identifier, *, attempt=None):
        """只请求停止；资源清理结束前不能把 cancel_requested 说成 cancelled。"""
        current = await self.get(user_id, conversation_id)
        if not current or current["id"] != identifier:
            raise ExecutionConflict("任务已被替换，不能停止新的执行")
        if attempt is not None and current["attempt"] != attempt:
            raise ExecutionConflict("任务已恢复到新的执行阶段，请刷新后操作")
        if current["status"] == "committing":
            raise ExecutionConflict("结果正在保存，已不能撤销；请等待并查看实际结果")
        await asyncio.to_thread(
            self.chats.update_one,
            self.scope(user_id, conversation_id, current)
            | {"execution.status": "running"},
            {
                "$set": {
                    "execution.status": "cancel_requested",
                    "execution.updated_at": stamp(),
                    "execution.message": "正在停止并清理运行资源。",
                }
            },
        )
        return await self.get(user_id, conversation_id)

    async def finish(
        self, user_id, conversation_id, item, status, message, *, unsafe=False
    ):
        """仅当前尝试可落终态；工具清理未确认时使用 failed/unsafe 禁止盲目恢复。"""
        if status in RESUMABLE:
            row = await asyncio.to_thread(
                self.chats.find_one,
                {"_id": conversation_id, "user_id": user_id},
                {"version": 1},
            )
            if row and row.get("version", 0) > item["base_version"]:
                unsafe = True
                message = "本轮答复已保存，但后续交付未全部完成。请查看会话核实，不能自动重放。"
        result = await asyncio.to_thread(
            self.chats.update_one,
            self.scope(user_id, conversation_id, item),
            {
                "$set": {
                    "execution.status": status,
                    "execution.message": message,
                    "execution.unsafe": unsafe,
                    "execution.updated_at": stamp(),
                }
            },
        )
        if not result.matched_count:
            if not await self.get(user_id, conversation_id):
                return None
            # 旧尝试可能晚于新尝试退出。它的 SSE 只能结束自己的视图，不能借新尝试
            # 的 running 状态触发页面误更新；数据库里的新状态完全不受影响。
            return {
                **item,
                "status": "interrupted",
                "unsafe": True,
                "updated_at": stamp(),
                "message": "该执行已被新的尝试替代，请查看当前会话状态。",
            }
        return await self.get(user_id, conversation_id)

    async def receipt(self, user_id, conversation_id, item, key, value):
        """回执只保存受限应用工具结果，最多16条，避免会话文档无限膨胀。"""
        if len(item.setdefault("receipts", {})) >= 16 and key not in item["receipts"]:
            raise ExecutionConflict("本轮工具回执已达上限，请结束当前任务后继续")
        result = await asyncio.to_thread(
            self.chats.update_one,
            self.scope(user_id, conversation_id, item),
            {"$set": {f"execution.receipts.{key}": value}},
        )
        if not result.matched_count:
            raise ExecutionConflict("执行所有权已变化，不能保存旧任务结果")
        item["receipts"][key] = value
