"""显式管理生产任务，不将浏览器连接存活等同于模型和容器的存活。"""

import asyncio
import json
from contextlib import nullcontext, suppress
from dataclasses import dataclass, field
from hashlib import sha256

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from langchain_core.messages import ToolMessage

from insight_link_agent.agent.execution.context import bind_execution
from insight_link_agent.agent.observability.progress import (
    ProgressChannel,
    bind_progress,
)
from insight_link_agent.agent.subagents.runtime import delegation_id
from insight_link_agent.app.storage.execution_store import ExecutionConflict
from insight_link_agent.integrations.java_client import JavaAPIError
from insight_link_agent.integrations.processes import ResourceCleanupError


async def settled(awaitable, *, propagate_cancel=False):
    """短数据库写入一旦发出就等待其结果；重复取消不能制造结果未知的线程写入。

    仅用于有网络超时上限的落库/回执，不用于模型、代码执行或其他长任务。
    """
    task = asyncio.ensure_future(awaitable)
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
    result = task.result()
    if cancelled and propagate_cancel:
        raise asyncio.CancelledError()
    return result


@dataclass
class ExecutionHandle:
    """仅供当前进程投递事件；Mongo 记录才是跨进程任务状态的依据。"""

    conversation_id: str
    user_id: int
    item: dict
    channel: ProgressChannel
    task: asyncio.Task | None = None
    shutdown: bool = False
    started: asyncio.Event = field(default_factory=asyncio.Event)
    cancel_sent: bool = False
    failure: bool = False
    ticket: object = None
    committing: bool = False
    commit_pending: bool = False


class ExecutionContext:
    """绑定一次 attempt 的所有权，隔离迟到回包和子图的工具回执。"""

    RETRYABLE = {
        "create_chart",
        "create_report",
        "create_document",
        "create_table",
        "run_analysis_code",
        "draft_evaluation",
        "request_teacher_info",
        "prepare_business_action",
    }

    def __init__(self, manager, handle):
        self.manager, self.handle = manager, handle
        self.store = manager.store
        self.lock = asyncio.Lock()

    def require_owner(self):
        """续租一旦报告失权就同步阻止新工具和提交，轮询不能代替执行边界校验。"""
        handle = self.handle
        if handle.failure or (handle.ticket and handle.ticket.lost.is_set()):
            handle.failure = True
            raise asyncio.CancelledError()

    async def begin_commit(self):
        """与停止请求竞争提交边界；重复调用不会重复改变执行阶段。"""
        handle = self.handle
        if not handle.committing:
            self.require_owner()
            # 提交 CAS 的数据库线程一旦发出，先确定哪方赢，不能取消等待后放走线程。
            # 用户停止由同一状态 CAS 仲裁；失权观察器不能截断已开始的提交写入。
            handle.commit_pending = True
            try:
                await settled(
                    self.store.commit(
                        handle.user_id, handle.conversation_id, handle.item
                    )
                )
                handle.committing = True
            finally:
                handle.commit_pending = False
        current = await self.store.get(handle.user_id, handle.conversation_id)
        handle.channel.publish("execution", self.store.public(current))

    def restore(self, capture):
        """检查点尚未捕获的工具结果从最新回执补齐，避免丢失待确认卡片或产物。"""
        completed = [
            row
            for row in self.handle.item.get("receipts", {}).values()
            if row.get("status") == "finished" and row.get("snapshot")
        ]
        if completed:
            capture.restore(max(completed, key=lambda row: row["sequence"])["snapshot"])

    async def tool(self, request, handler, capture):
        """先记录开始，再执行，再可靠记录结束；未确认的外部写入禁止自动重试。"""
        handle, call = self.handle, request.tool_call
        self.require_owner()
        fingerprint = json.dumps(
            [delegation_id.get(), call["name"], call["id"], call.get("args")],
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
        key = sha256(fingerprint.encode()).hexdigest()
        async with self.lock:
            previous = handle.item.get("receipts", {}).get(key)
            if previous and previous["status"] == "finished":
                self.restore(capture)
                return ToolMessage.model_validate(previous["result"])
            if previous and previous["status"] == "started":
                raise ExecutionConflict("工具结果尚待核实，禁止恢复时重复执行")
            record = {"name": call["name"], "status": "started"}
            try:
                await settled(
                    self.store.receipt(
                        handle.user_id, handle.conversation_id, handle.item, key, record
                    ),
                    propagate_cancel=True,
                )
            except asyncio.CancelledError:
                # 此时工具尚未开始；等开始回执确定落库后改为 aborted，可安全恢复。
                await settled(
                    self.store.receipt(
                        handle.user_id,
                        handle.conversation_id,
                        handle.item,
                        key,
                        {"name": call["name"], "status": "aborted"},
                    )
                )
                raise
        try:
            # 此处不 shield：模型、容器和解析必须能收到真正的 CancelledError。
            result = await handler(request)
        except asyncio.CancelledError:
            if call["name"] in self.RETRYABLE:
                await settled(
                    self.store.receipt(
                        handle.user_id,
                        handle.conversation_id,
                        handle.item,
                        key,
                        {"name": call["name"], "status": "aborted"},
                    )
                )
            # 配置/记忆的在途数据库写入可能已完成，保留 started，不伪称可安全重放。
            raise
        async with self.lock:
            snapshot = capture._capture()
            receipt = {
                "name": call["name"],
                "status": "finished",
                "sequence": sum(
                    row.get("status") == "finished"
                    for row in handle.item["receipts"].values()
                )
                + 1,
                "result": result.model_dump(mode="json"),
                "snapshot": snapshot,
            }
            # 单个副作用结果仍限制128KB；累计分页证据随快照保存，整体另限1MB。
            # 两种预算分开，避免完整统计后的报告/预览因历史页数增多而无法恢复。
            if (
                len(
                    json.dumps(
                        receipt["result"], ensure_ascii=False, default=str
                    ).encode()
                )
                > 128_000
                or len(json.dumps(receipt, ensure_ascii=False, default=str).encode())
                > 1_000_000
            ):
                raise ExecutionConflict("工具结果超过可恢复回执大小，已停止自动处理")
            await settled(
                self.store.receipt(
                    handle.user_id, handle.conversation_id, handle.item, key, receipt
                ),
                propagate_cancel=True,
            )
        return result


class ExecutionManager:
    """进程内运行句柄 + Mongo 取消信号；断线继续，显式停止才终止生产任务。"""

    def __init__(self, store, tracer=None):
        self.store = store
        self.tracer = tracer
        self.handles = {}
        self.live = {}

    def launch(self, user_id, conversation_id, item, operation, lease, ticket=None):
        """调用方已验证身份并领取租约，生产者负责在所有退出路径释放它。"""
        handle = ExecutionHandle(
            conversation_id, user_id, item, ProgressChannel(), ticket=ticket
        )
        self.handles[item["id"]] = handle
        handle.task = asyncio.create_task(self._produce(handle, operation, lease))
        self.live[handle.task] = handle

        def forget(_task):
            # 恢复沿用 execution ID；迟到旧尝试不能移除新尝试的本地取消入口。
            if self.handles.get(item["id"]) is handle:
                self.handles.pop(item["id"], None)
            self.live.pop(_task, None)

        handle.task.add_done_callback(forget)
        return handle

    async def _watch(self, handle):
        """其他进程收到停止请求时也通过 Mongo 信号终止本地执行。"""
        try:
            while True:
                await asyncio.sleep(0.4)
                if handle.ticket and handle.ticket.lost.is_set():
                    handle.failure = True
                    if not handle.committing and not handle.commit_pending:
                        self._signal_cancel(handle)
                    return
                current = await self.store.get(handle.user_id, handle.conversation_id)
                if (
                    not current
                    or current["id"] != handle.item["id"]
                    or current["attempt"] != handle.item["attempt"]
                    or current["status"] == "cancel_requested"
                ):
                    if not handle.committing and not handle.commit_pending:
                        self._signal_cancel(handle)
                    return
        except asyncio.CancelledError:
            raise
        except Exception:
            # 无法持续证明任务所有权时停止运行，避免网络故障后两个进程同时操作。
            handle.failure = True
            if not handle.committing and not handle.commit_pending:
                self._signal_cancel(handle)

    @staticmethod
    def _signal_cancel(handle):
        """同一次尝试只投递一次取消，避免第二次取消打断第一次的资源清理。"""
        if not handle.cancel_sent and not handle.task.done():
            handle.cancel_sent = True
            handle.task.cancel()

    async def _produce(self, handle, operation, lease):
        """清理完成后落终态；停止失败不得冒充已停止，最终提交阶段不接受用户取消。"""
        handle.started.set()
        watcher = asyncio.create_task(self._watch(handle))
        status, message, unsafe = "failed", "任务未完成，可重新打开会话检查。", False
        event, data = "error", {}
        try:
            # 整个生产任务绑定同一脱敏 trace；包括路由、专家、压缩、工具及复核。
            # ContextVar 随异步任务隔离，导师 token 和正文不进入追踪参数。
            tracing = (
                self.tracer.bind_run(
                    execution_id=handle.item["id"],
                    conversation_id=handle.conversation_id,
                    teacher_user_id=handle.user_id,
                )
                if self.tracer
                else nullcontext()
            )
            with (
                tracing,
                bind_progress(handle.channel),
                bind_execution(ExecutionContext(self, handle)),
            ):
                result = await operation()
            if isinstance(result, JSONResponse):
                data = {**json.loads(result.body), "status": result.status_code}
            else:
                event, data, status, message = (
                    "result",
                    result,
                    "completed",
                    "任务处理已结束。",
                )
        except asyncio.CancelledError:
            status = (
                "failed"
                if handle.failure
                else "interrupted"
                if handle.shutdown
                else "cancelled"
            )
            unsafe = handle.failure
            message = (
                "任务所有权无法核实，已停止执行，请检查服务状态。"
                if handle.failure
                else "服务已停止，本轮保留检查点，可重新登录后恢复。"
                if handle.shutdown
                else "任务已停止，已完成的工具结果和检查点已保留。"
            )
            event, data = "execution", {}
        except (HTTPException, JavaAPIError) as exc:
            code = exc.status_code if isinstance(exc, HTTPException) else exc.status
            data = {
                "detail": exc.detail if isinstance(exc, HTTPException) else str(exc),
                "status": code,
            }
        except Exception as exc:
            # 包括不能证明容器已终止的 ResourceCleanupError；禁止自动恢复未知副作用。
            current = await self.store.get(handle.user_id, handle.conversation_id)
            unsafe = isinstance(exc, ResourceCleanupError) or bool(
                current and current.get("status") == "cancel_requested"
            )
            data = {
                "detail": "任务未完成，运行资源或执行结果需要核实，请重新打开对话查看状态。",
                "status": 503,
            }
        finally:
            watcher.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await watcher
            # 终态必须在仍持有租约时落库，不能让新任务抢先开始后被旧结果覆盖。
            try:
                current = await settled(
                    self.store.finish(
                        handle.user_id,
                        handle.conversation_id,
                        handle.item,
                        status,
                        message,
                        unsafe=unsafe,
                    )
                )
            finally:
                await settled(lease.__aexit__(None, None, None))
        public = self.store.public(current)
        if event == "execution":
            data = public
        else:
            data = {
                **data,
                "conversation_id": handle.conversation_id,
                "execution": public,
            }
            if event == "error":
                data["retryable"] = bool(public and public["can_resume"])
        return event, data, public

    async def cancel(self, user_id, conversation_id, identifier, *, attempt=None):
        """停止是幂等请求；只对仍处于 cancel_requested 的当前尝试发取消。"""
        current = await self.store.cancel(
            user_id, conversation_id, identifier, attempt=attempt
        )
        if current["status"] == "cancel_requested" and (
            handle := self.handles.get(identifier)
        ):
            await handle.started.wait()
            self._signal_cancel(handle)
            # 等待一小段清理时间；超时只返回“正在停止”，前端继续查状态。
            await asyncio.wait({handle.task}, timeout=2)
        return await self.store.reconcile(user_id, conversation_id)

    async def close(self):
        """停服终止可取消阶段；已进入提交的任务等数据库结果确定后再退出。"""
        # 最新 ID 映射用于按钮投递；live 还跟踪过期尝试的迟到收尾，停服不能漏掉它。
        handles = list(self.live.values())
        for handle in handles:
            handle.shutdown = True
            await handle.started.wait()
            try:
                current = await self.store.cancel(
                    handle.user_id,
                    handle.conversation_id,
                    handle.item["id"],
                    attempt=handle.item["attempt"],
                )
            except ExecutionConflict:
                continue  # 提交已获胜，等它得到明确结果再关闭共享数据库连接。
            if current and current["status"] == "cancel_requested":
                self._signal_cancel(handle)
        if handles:
            # 数据库已配置 socket 超时；不在 12 秒后强制截断正在提交的线程写入。
            # 强制杀进程后的结果由下次打开会话时核对 HOT 版本，禁止盲目重放。
            await asyncio.gather(
                *(handle.task for handle in handles), return_exceptions=True
            )
