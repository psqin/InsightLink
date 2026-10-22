"""SSE 只观察独立执行任务；断开接收与取消执行是两个不同动作。"""

import asyncio
import json
from contextlib import suppress

from fastapi.responses import StreamingResponse

from insight_link_agent.app.storage.execution_store import ExecutionStore


def sse_event(event: str, data: dict) -> str:
    """JSON 转义换行，事件名仅由服务端常量提供。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def chat_stream_response(handle):
    """生产者拥有任务与租约，观察者退出只关闭自己的进度队列。"""
    task, channel, conversation_id = handle.task, handle.channel, handle.conversation_id

    async def events():
        try:
            yield sse_event(
                "session",
                {
                    "conversation_id": conversation_id,
                    "execution_id": handle.item["id"],
                    "attempt": handle.item["attempt"],
                },
            )
            yield sse_event("execution", ExecutionStore.public(handle.item))
            while not task.done() or not channel.queue.empty():
                if not channel.queue.empty():
                    event, data = channel.queue.get_nowait()
                    yield sse_event(event, data)
                    continue
                pending = asyncio.create_task(channel.queue.get())
                try:
                    done, _ = await asyncio.wait(
                        {pending, task}, timeout=15, return_when=asyncio.FIRST_COMPLETED
                    )
                    if pending in done:
                        event, data = pending.result()
                        yield sse_event(event, data)
                    elif not done:
                        yield ": heartbeat\n\n"
                finally:
                    pending.cancel()
                    with suppress(asyncio.CancelledError):
                        await pending
            event, data, execution = task.result()
            if event != "execution":
                yield sse_event("execution", execution)
            if event == "result" and (
                data.get("pending_input") or data.get("pending_action")
            ):
                yield sse_event(
                    "interrupt",
                    {"kind": "input" if data.get("pending_input") else "approval"},
                )
            # 正文及文件信息只在现有业务校验与 Harness 结束后发布。
            yield sse_event(event, data)
            yield sse_event(
                "done",
                {"conversation_id": conversation_id, "status": execution["status"]},
            )
        finally:
            channel.closed = True

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store",
            "X-Accel-Buffering": "no",
            "X-Content-Type-Options": "nosniff",
        },
    )
