"""stdio 附件请求的取消确认，避免把单向 MCP 通知当成远端已停止。

这里只记录随机请求号、当前凭据的不可逆摘要和短期任务句柄，不写数据库，
不保存材料正文、材料地址或 token。正式评价/留言写操作不经过这个注册表。
"""

import asyncio
import re
from collections import OrderedDict
from collections.abc import Awaitable
from dataclasses import dataclass
from hashlib import sha256
from time import monotonic

from insight_link_agent.integrations.processes import (
    ResourceCleanupError,
    finish_cleanup,
)


@dataclass
class _Request:
    """完成后只保留停止状态，不通过 Task.result 延长正文和凭据的生命周期。"""

    created: float
    task: asyncio.Task | None
    cleanup_failed: bool = False


class AttachmentRequests:
    """有限容量的远端请求表；只有同一凭据持有者能取消对应附件读取。"""

    MAX_REQUESTS = 128
    RETAIN_SECONDS = 120

    def __init__(self):
        self._requests: OrderedDict[tuple[str, str], _Request] = OrderedDict()

    @staticmethod
    def _key(token: str, request_id: str) -> tuple[str, str]:
        if not re.fullmatch(r"[a-f0-9]{32}", request_id):
            raise ValueError("附件读取请求标识无效")
        return sha256(token.encode()).hexdigest(), request_id

    async def run(
        self, token: str, request_id: str, operation: Awaitable[dict]
    ) -> dict:
        """注册后才开始授权、下载与解析；在退出前等底层资源完成清理。"""
        try:
            key = self._key(token, request_id)
            now = monotonic()
            for previous, entry in list(self._requests.items()):
                if entry.task is None and entry.created + self.RETAIN_SECONDS <= now:
                    self._requests.pop(previous, None)
            if key in self._requests:
                raise ValueError("附件读取请求标识不能重复")
            if len(self._requests) >= self.MAX_REQUESTS:
                finished = next(
                    (
                        key
                        for key, entry in self._requests.items()
                        if entry.task is None
                    ),
                    None,
                )
                if finished is None:
                    raise RuntimeError("附件读取任务较多，请稍后重试")
                self._requests.pop(finished, None)
        except Exception:
            # 校验失败时关闭尚未开始的协程，不能泄漏未 await 的下载/授权操作。
            if hasattr(operation, "close"):
                operation.close()
            raise
        task = asyncio.create_task(operation)
        entry = _Request(now, task)
        self._requests[key] = entry

        def finished(completed: asyncio.Task) -> None:
            """仅留安全状态，及时释放可能含已解析正文的完成结果。"""
            try:
                failure = completed.exception()
            except asyncio.CancelledError:
                pass
            else:
                entry.cleanup_failed = isinstance(failure, ResourceCleanupError)
            entry.task = None

        task.add_done_callback(finished)
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            # 单向 MCP 通知与显式确认请求可能同时到达。重复 cancel 会在底层
            # finally 的下一次 await 再抛一次，必须只发出首次取消信号。
            if not task.cancelling():
                task.cancel()
            try:
                await finish_cleanup(task)
            except asyncio.CancelledError:
                pass
            raise

    async def cancel(self, token: str, request_id: str) -> dict:
        """显式取消并确认远端资源已退出；不存在的请求不能被误报为已停止。"""
        entry = self._requests.get(self._key(token, request_id))
        if entry is None:
            raise ResourceCleanupError("未能确认对应附件请求的停止状态")
        task = entry.task
        if task is None:
            if entry.cleanup_failed:
                raise ResourceCleanupError("未能确认对应附件请求的停止状态")
            return {"ok": True, "value": {"stopped": True}}
        if not task.done() and not task.cancelling():
            task.cancel()
        try:
            await finish_cleanup(task)
        except asyncio.CancelledError:
            pass  # 底层解析器仅在确认容器不存在后才结束为 cancelled。
        except ResourceCleanupError:
            raise
        except Exception:
            # 网络/解析本身已失败而任务已退出，也代表没有仍在执行的工作。
            pass
        return {"ok": True, "value": {"stopped": True}}
