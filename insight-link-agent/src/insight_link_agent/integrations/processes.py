"""一次性 Docker 任务的进程所有权和取消清理。

取消 Python 的 ``communicate`` 只会停止等待，并不会结束 Docker 容器。
这里把「取得子进程句柄 → 杀死并回收客户端 → 删除容器 → 查询确认不存在」
作为一个必须完成的清理阶段，供分析和附件解析共用。
"""

import asyncio
import re
from collections.abc import Awaitable
from typing import TypeVar

_T = TypeVar("_T")
_DOCKER_NAME = re.compile(
    r"insight-(?:analysis-[a-f0-9]{20}|link-attachment-[a-f0-9]{12})\Z"
)


class ResourceCleanupError(RuntimeError):
    """无法确认资源已停止；上层必须标记失败，不能向导师声称取消成功。"""


async def finish_cleanup(awaitable: Awaitable[_T]) -> _T:
    """等待有界清理完成，即使调用者在清理期间再次收到 ``cancel()``。

    仅用于异常处理和退出阶段：调用方仍须在清理成功后重新抛出原始取消异常。
    独立任务避免第二次原生 asyncio 取消中断清理；清理本身必须设置超时，
    不能借 shield 把外部服务故障变成永不返回的后台任务。
    """
    task = asyncio.ensure_future(awaitable)
    while True:
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            if task.done():
                return task.result()


async def _stop_process(process: asyncio.subprocess.Process) -> None:
    """回收客户端及管道；必须读取剩余输出，避免 Windows 管道阻塞 wait。"""
    if process.returncode is None:
        try:
            process.kill()
        except ProcessLookupError:
            pass  # 正常退出与取消并发发生，句柄随后仍由 wait 回收。
    try:
        await asyncio.wait_for(process.communicate(), timeout=5)
        await asyncio.wait_for(process.wait(), timeout=5)
    except (OSError, TimeoutError) as exc:
        raise ResourceCleanupError("未能确认沙箱客户端进程已停止") from exc


async def _docker_command(*args: str, docker_context: str) -> tuple[int, bytes]:
    """运行只用于资源清理的 Docker 命令；不经 shell，不输出外部错误正文。"""
    try:
        process = await asyncio.create_subprocess_exec(
            "docker",
            "--context",
            docker_context,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except OSError as exc:
        raise ResourceCleanupError("Docker 不可用，无法确认沙箱已停止") from exc
    try:
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=5)
    except TimeoutError as exc:
        await _stop_process(process)
        raise ResourceCleanupError("Docker 清理响应超时，无法确认沙箱已停止") from exc
    return process.returncode, stdout


async def stop_docker_task(
    process: asyncio.subprocess.Process, name: str, *, docker_context: str
) -> None:
    """清理指定任务并证明容器不存在；清理异常不得被吞掉。

    ``docker rm -f`` 返回非零也可能只是 ``--rm`` 已自动删除，故最终以成功的
    ``docker ps -a`` 空结果为准。Docker 服务不可用或容器仍存在均显式报错。
    名称由程序生成并严格校验，禁止把用户输入带入清理命令。
    """
    if not _DOCKER_NAME.fullmatch(name):
        raise ResourceCleanupError("沙箱清理目标无效")
    client_error = None
    try:
        await _stop_process(process)
    except ResourceCleanupError as exc:
        client_error = exc
        # 客户端管道/回收异常也不能跳过远端容器删除，尽力消除实际运行资源。
    await _docker_command("rm", "-f", name, docker_context=docker_context)
    code, stdout = await _docker_command(
        "ps",
        "-a",
        "--filter",
        f"name=^/{name}$",
        "--format",
        "{{.ID}}",
        docker_context=docker_context,
    )
    if code != 0 or stdout.strip():
        raise ResourceCleanupError("未能确认任务容器已停止，请检查 Docker 状态")
    if client_error is not None:
        raise client_error


async def start_docker_task(
    args: list[str], name: str, *, docker_context: str
) -> asyncio.subprocess.Process:
    """原子地接管已启动的客户端，填补 create_subprocess_exec 的取消窗口。

    若任务在系统创建进程后、Python 返回句柄前被取消，直接取消 await 会遗失
    唯一可清理的句柄。先 shield 创建操作，再取得句柄并完成清理后传播取消。
    args 从子命令开始；启动及异常清理始终使用传入的同一个 Context。
    """
    spawning = asyncio.create_task(
        asyncio.create_subprocess_exec(
            "docker",
            "--context",
            docker_context,
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    )
    try:
        return await asyncio.shield(spawning)
    except asyncio.CancelledError:
        try:
            process = await finish_cleanup(spawning)
        except OSError:
            raise asyncio.CancelledError from None  # 创建失败，没有实际资源需要回收。
        await finish_cleanup(
            stop_docker_task(process, name, docker_context=docker_context)
        )
        raise
