"""委派调用的请求内作用域，隔离并行子任务的执行证据。"""

from contextvars import ContextVar

delegation_id: ContextVar[str | None] = ContextVar(
    "insight_delegation_id", default=None
)
