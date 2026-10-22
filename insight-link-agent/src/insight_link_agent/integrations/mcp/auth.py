"""仅在当前请求中转发Java凭据，不传给模型或共享客户端默认头。"""

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

from insight_link_agent.integrations.java_client import JavaAPIError

_request_token: ContextVar[str | None] = ContextVar("java_token", default=None)


@contextmanager
def use_java_token(token: str) -> Iterator[None]:
    marker = _request_token.set(token)
    try:
        yield
    finally:
        _request_token.reset(marker)


def _token(explicit: str | None = None) -> str:
    token = explicit or _request_token.get()
    if not token:
        raise JavaAPIError(401, "当前请求没有 Java 登录凭据")
    return token
