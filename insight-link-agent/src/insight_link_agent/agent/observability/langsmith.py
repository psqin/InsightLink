"""只上报运行结构的 LangSmith 适配器；业务原文永远不进入 SDK 队列。

不要在本项目直接启用环境变量自动 tracing 或 LangChainTracer：它们会序列化
messages、工具参数、metadata 和异常。入口统一使用 ``bind_run``，通过请求级
ContextVar 为所有嵌套 Runnable 注册本模块的统计回调。真实 SDK 仅负责发送
已经白名单化的运行 ID、父子关系、数量、状态和 token 用量。
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from queue import Empty, Full, Queue
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.runnables.config import var_child_runnable_config
from langchain_core.tracers.context import register_configure_hook
from langsmith import Client, tracing_context
from requests import Session
from urllib3.util.retry import Retry

from .progress import SUBAGENT_LABELS, TOOL_LABELS

_active_callback: ContextVar[Any] = ContextVar("safe_langsmith_callback", default=None)
# 无环境变量触发器；只有 bind_run 设置的当前请求回调会被继承。
register_configure_hook(_active_callback, inheritable=True)
_SAFE_NAMES = (
    frozenset(TOOL_LABELS)
    | frozenset(SUBAGENT_LABELS)
    | {
        "academic-assistant",
        "insight-link-teacher",
        "public-research",
        "LangGraph",
        "model",
        "tools",
        "task",
        "ChatOpenAI",
        "RunnableSequence",
        "RunnableLambda",
        "review",
        "routing",
        "context-summary",
        "PrivateAssistantState",
    }
)
_RUN_TYPES = frozenset({"chain", "llm", "tool", "retriever"})
_USAGE_KEYS = frozenset(
    {
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "prompt_tokens",
        "completion_tokens",
    }
)


@contextmanager
def observe_model():
    """补齐直接 OpenAI SDK 调用的模型节点，只接收数字用量，不接收提示词。

    LangChain Runnable 使用自动继承的统计回调；原生 SDK 没有该回调，故在
    同一个请求 trace 内显式登记。工具上下文存在时沿用其父节点，否则归根节点。
    解析异常和取消均保留真实控制流，观测层不吞业务异常。
    """
    callback = _active_callback.get()
    usage: dict = {}
    identifier = uuid4()
    if callback:
        config = var_child_runnable_config.get() or {}
        parent = getattr(config.get("callbacks"), "parent_run_id", None)
        callback._start(identifier, parent, "llm", "model", {})
    try:
        yield usage
    except BaseException as error:
        if callback:
            callback._end(identifier, error=error)
        raise
    else:
        if callback:
            clean = {
                key: value
                for key, value in usage.items()
                if key in _USAGE_KEYS and type(value) is int and 0 <= value <= 10**9
            }
            callback._end(identifier, usage=clean)


def disable_automatic_tracing() -> None:
    """启动时关闭 SDK 的原文自动上报；不修改任何密钥或项目配置。

    bind_run 另外使用 enabled=False 阻断继承上下文中的自动 tracer，避免用户
    在系统环境中设置 LANGSMITH_TRACING=true 后绕过本模块的白名单出口。
    """
    for name in (
        "LANGSMITH_TRACING",
        "LANGCHAIN_TRACING_V2",
        "LANGCHAIN_TRACING",
        "LANGCHAIN_HANDLER",
    ):
        os.environ[name] = "false"


def _secret(value: Any) -> str:
    """兼容 Settings 的 SecretStr；从不格式化或记录密钥。"""
    return (
        value.get_secret_value()
        if hasattr(value, "get_secret_value")
        else str(value or "")
    )


def _shape(value: Any) -> dict[str, int]:
    """只统计浅层容器大小；不遍历内容、不保留键名，也不调用用户对象的 repr。"""
    if isinstance(value, dict):
        return {"field_count": len(value)}
    if isinstance(value, (list, tuple)):
        return {"item_count": len(value)}
    if isinstance(value, str):
        return {"character_count": len(value)}
    return {}


def _usage(response: Any) -> dict[str, int]:
    """只提取有界非负整数，丢弃 provider 附带的字符串、metadata 和原始响应。"""
    found: dict[str, int] = {}
    llm_output = getattr(response, "llm_output", None)
    candidates = (
        [llm_output.get("token_usage", {})] if isinstance(llm_output, dict) else []
    )
    for batch in getattr(response, "generations", ()) or ():
        for generation in batch:
            message = getattr(generation, "message", None)
            candidates.append(getattr(message, "usage_metadata", None))
    for candidate in candidates:
        if isinstance(candidate, dict):
            for key in _USAGE_KEYS:
                value = candidate.get(key)
                if type(value) is int and 0 <= value <= 10**9:
                    found[key] = value
    return found


def _safe_name(name: Any, run_type: str) -> str:
    """run_name 也可能携带姓名或问题，只有已知的项目常量可以出站。"""
    if isinstance(name, str) and name in _SAFE_NAMES:
        return name
    return {"llm": "chat-model", "tool": "tool", "retriever": "retriever"}.get(
        run_type, "chain"
    )


class _BoundedClient(Client):
    """固定单一出口并禁止重试/重定向；SDK 不读取运行时环境来补充 trace。"""

    def request_with_retries(self, method, pathname, **kwargs):
        kwargs["stop_after_attempt"] = 1
        kwargs["allow_redirects"] = False
        return super().request_with_retries(method, pathname, **kwargs)


class _StatisticsCallback(BaseCallbackHandler):
    """回调只持有净化运行状态，原始模型输入和工具结果在当前栈内即被丢弃。"""

    run_inline = True
    raise_error = False

    def __init__(self, owner: "SafeLangSmithTracer", metadata: dict[str, str]):
        self.owner, self.metadata = owner, metadata
        self.root_id = uuid4()
        self.lock = threading.RLock()
        self.runs: dict[UUID, dict] = {}
        self._start(self.root_id, None, "chain", "academic-assistant", {})

    def _start(self, run_id, parent_run_id, run_type, name, counts):
        with self.lock:
            if run_id in self.runs or len(self.runs) >= 2000:
                return
            parent = self.runs.get(parent_run_id)
            if run_id != self.root_id and parent is None:
                parent_run_id, parent = self.root_id, self.runs[self.root_id]
            stamp = datetime.now(timezone.utc)
            order = stamp.strftime("%Y%m%dT%H%M%S%fZ") + str(run_id)
            if parent:
                order = parent["dotted_order"] + "." + order
            state = {
                "id": run_id,
                "parent_run_id": parent_run_id,
                "trace_id": self.root_id,
                "dotted_order": order,
            }
            self.runs[run_id] = state
            self.owner._enqueue(
                "create",
                {
                    **state,
                    "name": _safe_name(name, run_type),
                    "run_type": run_type,
                    "start_time": stamp,
                    "inputs": counts,
                    "extra": {"metadata": self.metadata},
                },
            )

    def _end(self, run_id, outputs=None, error=None, usage=None):
        with self.lock:
            state = self.runs.get(run_id)
            if not state or state.get("ended"):
                return
            state["ended"] = True
            status = (
                "cancelled"
                if isinstance(error, asyncio.CancelledError)
                else "error"
                if error is not None
                else "success"
            )
            result = {**_shape(outputs), "status": status}
            if isinstance(outputs, dict) and type(outputs.get("ok")) is bool:
                result["result_success"] = outputs["ok"]
            self.owner._enqueue(
                "update",
                {
                    **{key: value for key, value in state.items() if key != "ended"},
                    "end_time": datetime.now(timezone.utc),
                    "outputs": result,
                    "error": status if error is not None else None,
                    "extra": {
                        "metadata": self.metadata,
                        **({"usage": usage} if usage else {}),
                    },
                },
            )

    def finish(self, error=None):
        """请求结束时关闭残余节点；取消沿原异常继续传播，不以追踪失败替换业务异常。"""
        with self.lock:
            for run_id in list(self.runs):
                if run_id != self.root_id and not self.runs[run_id].get("ended"):
                    self._end(run_id, error=error or RuntimeError())
            self._end(self.root_id, error=error)

    def on_chain_start(
        self, serialized, inputs, *, run_id, parent_run_id=None, **kwargs
    ):
        self._start(
            run_id,
            parent_run_id,
            "chain",
            kwargs.get("name") or (serialized or {}).get("name"),
            _shape(inputs),
        )

    def on_chain_end(self, outputs, *, run_id, **kwargs):
        self._end(run_id, outputs)

    def on_chain_error(self, error, *, run_id, **kwargs):
        self._end(run_id, error=error)

    def on_chat_model_start(
        self, serialized, messages, *, run_id, parent_run_id=None, **kwargs
    ):
        counts = {
            "batch_count": len(messages),
            "message_count": sum(len(batch) for batch in messages),
        }
        self._start(
            run_id,
            parent_run_id,
            "llm",
            kwargs.get("name") or (serialized or {}).get("name"),
            counts,
        )

    def on_llm_start(
        self, serialized, prompts, *, run_id, parent_run_id=None, **kwargs
    ):
        self._start(
            run_id,
            parent_run_id,
            "llm",
            kwargs.get("name") or (serialized or {}).get("name"),
            {"prompt_count": len(prompts)},
        )

    def on_llm_end(self, response, *, run_id, **kwargs):
        self._end(run_id, usage=_usage(response))

    def on_llm_error(self, error, *, run_id, **kwargs):
        self._end(run_id, error=error)

    def on_tool_start(
        self, serialized, input_str, *, run_id, parent_run_id=None, **kwargs
    ):
        self._start(
            run_id,
            parent_run_id,
            "tool",
            (serialized or {}).get("name"),
            _shape(kwargs.get("inputs")),
        )

    def on_tool_end(self, output, *, run_id, **kwargs):
        self._end(run_id, output)

    def on_tool_error(self, error, *, run_id, **kwargs):
        self._end(run_id, error=error)

    def on_retriever_start(
        self, serialized, query, *, run_id, parent_run_id=None, **kwargs
    ):
        self._start(run_id, parent_run_id, "retriever", None, {})

    def on_retriever_end(self, documents, *, run_id, **kwargs):
        self._end(run_id, documents)

    def on_retriever_error(self, error, *, run_id, **kwargs):
        self._end(run_id, error=error)


class SafeLangSmithTracer:
    """进程级受控发送器；单个请求的 callback 与父子图状态分别隔离。

    正常请求不等待 LangSmith 网络。满队列丢弃、网络错误计数，不记录原始异常。
    close/flush 有等待上限；后台线程为 daemon，不会拖住服务关闭。
    """

    def __init__(
        self,
        *,
        enabled=False,
        api_key="",
        project="insight-link-agent",
        endpoint="https://api.smith.langchain.com",
        workspace_id="",
        session: Session | None = None,
    ):
        disable_automatic_tracing()
        self.enabled = False
        self.state = "disabled"
        self._closed = False
        self._stop = threading.Event()
        self._queue: Queue = Queue(maxsize=4096)
        self._client = None
        self._worker = None
        self._key = _secret(api_key).encode()
        self._project = project
        self.sent = self.failed = self.dropped = 0
        if not enabled:
            return
        if not self._key:
            self.state = "missing_key"
            return
        target = urlsplit(endpoint)
        if (
            target.scheme != "https"
            or not target.hostname
            or target.username
            or target.password
            or target.query
            or target.fragment
            or target.path not in ("", "/")
        ):
            self.state = "invalid_endpoint"
            return
        try:
            owned_session = session if session is not None else Session()
            owned_session.trust_env = False
            self._client = _BoundedClient(
                api_urls={endpoint.rstrip("/"): self._key.decode()},
                api_key=self._key.decode(),
                workspace_id=workspace_id or "",
                auto_batch_tracing=False,
                tracing_mode="langsmith",
                tracing_sampling_rate=1.0,
                omit_traced_runtime_info=True,
                disable_prompt_cache=True,
                timeout_ms=(1000, 1500),
                retry_config=Retry(total=0),
                session=owned_session,
                info={"version": "safe-statistics"},
            )
        except Exception:
            self.state = "configuration_error"
            return
        self.enabled, self.state = True, "ready"
        self._worker = threading.Thread(
            target=self._send_loop, daemon=True, name="safe-langsmith"
        )
        self._worker.start()

    @classmethod
    def from_settings(cls, settings):
        """配置由项目 Settings 显式提供，不读取 SDK 的自动 tracing 开关。"""
        return cls(
            enabled=getattr(settings, "langsmith_enabled", False),
            api_key=getattr(settings, "langsmith_api_key", ""),
            project=getattr(settings, "langsmith_project", "insight-link-agent"),
            endpoint=getattr(
                settings, "langsmith_endpoint", "https://api.smith.langchain.com"
            ),
            workspace_id=getattr(settings, "langsmith_workspace_id", ""),
        )

    def correlation_id(self, kind: str, value: Any) -> str:
        """HMAC 避免从短教师 ID 反查身份，并使重启后的会话/执行仍可关联。"""
        return hmac.new(
            self._key, (kind + ":" + str(value or "")).encode(), hashlib.sha256
        ).hexdigest()[:32]

    @contextmanager
    def bind_run(
        self, *, execution_id=None, conversation_id=None, teacher_user_id=None
    ):
        """包裹完整生产任务，而非仅 ainvoke；分流、压缩和复核也在观测范围内。"""
        if active := _active_callback.get():
            # 同一生产任务内部的评价草稿入口复用其根节点，避免一个任务分裂成两个trace。
            yield active
            return
        callback = None
        with tracing_context(enabled=False, parent=False):
            if self.enabled and not self._closed:
                metadata = {"privacy_mode": "statistics-only-v1"}
                for kind, value in (
                    ("execution", execution_id),
                    ("session", conversation_id),
                    ("teacher", teacher_user_id),
                ):
                    if value is not None:
                        metadata[kind + "_ref"] = self.correlation_id(kind, value)
                callback = _StatisticsCallback(self, metadata)
            token = _active_callback.set(callback)
            try:
                yield callback
            except BaseException as error:
                if callback:
                    callback.finish(error)
                raise
            else:
                if callback:
                    callback.finish()
            finally:
                _active_callback.reset(token)

    def _enqueue(self, operation: str, payload: dict) -> None:
        """只接收本模块构造的白名单 dict；不把原消息放入后台队列。"""
        if self._closed:
            return
        try:
            self._queue.put_nowait((operation, payload))
        except Full:
            self.dropped += 1

    def _send_loop(self):
        """单线程保证同一队列中 create 在 update 前到达；失败不重试、不落盘。"""
        try:
            while not self._stop.is_set():
                try:
                    operation, payload = self._queue.get(timeout=0.05)
                except Empty:
                    continue
                try:
                    if operation == "create":
                        self._client.create_run(project_name=self._project, **payload)
                    else:
                        self._client.update_run(run_id=payload.pop("id"), **payload)
                    self.sent += 1
                except Exception:
                    self.failed += 1
                finally:
                    self._queue.task_done()
        finally:
            if self._client:
                try:
                    self._client.close(timeout=0)
                except Exception:
                    pass

    def flush(self, timeout: float = 1.0) -> bool:
        """仅等已排队统计，最多 timeout 秒；业务返回路径不应调用。"""
        deadline = time.monotonic() + max(0, min(timeout, 5.0))
        while self._queue.unfinished_tasks and time.monotonic() < deadline:
            time.sleep(0.005)
        return self._queue.unfinished_tasks == 0

    def close(self, timeout: float = 0.5) -> None:
        """停收新事件并有界等待；不可达的观测服务不会阻塞业务取消/关闭。"""
        self._closed = True
        self.flush(timeout)
        self._stop.set()
        if self._worker:
            self._worker.join(timeout=0)

    async def aclose(self, timeout: float = 0.5) -> None:
        """兼容 FastAPI lifespan，不在事件循环里等待线程。"""
        await asyncio.to_thread(self.close, timeout)
