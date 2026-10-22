"""把任务控制传到主图和子图，避免将取消状态混入模型消息。"""

from contextlib import contextmanager
from contextvars import ContextVar

_execution = ContextVar("insight_execution", default=None)


def current_execution():
    """只有 HTTP 执行管理器绑定的当前任务可以修改其持久状态。"""
    return _execution.get()


@contextmanager
def bind_execution(execution):
    """并发 asyncio 任务继承独立上下文；退出时必须恢复原绑定。"""
    token = _execution.set(execution)
    try:
        yield execution
    finally:
        _execution.reset(token)


async def begin_commit():
    """进入最终提交边界：一旦开始落库，不再将其声称为可撤销操作。

    任务取消先赢得状态竞争时，此处抛出 CancelledError 阻止交付；提交先赢时，
    停止接口返回状态冲突并等待真实结果，避免“页面已停、数据却已保存”的误报。
    """
    if execution := current_execution():
        await execution.begin_commit()
