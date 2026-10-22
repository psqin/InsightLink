"""任务级 Docker 沙箱：无网络、无宿主挂载，超时强制结束。"""

import asyncio
import json
from uuid import uuid4

from insight_link_agent.integrations.processes import (
    finish_cleanup,
    start_docker_task,
    stop_docker_task,
)


class AnalysisSandbox:
    def __init__(
        self, image: str, timeout: int = 30, *, docker_context: str = "default"
    ):
        self.image = image
        self.timeout = timeout
        self.docker_context = docker_context

    async def run(self, payload: dict) -> dict:
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode(
            "utf-8"
        )
        if len(encoded) > 100_000:
            raise ValueError("分析输入超过 100 KB")
        name = f"insight-analysis-{uuid4().hex[:20]}"
        args = [
            "run",
            "--rm",
            "-i",
            "--name",
            name,
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "64",
            "--memory",
            "512m",
            "--cpus",
            "1",
            "--user",
            "65534:65534",
            "--tmpfs",
            "/tmp:rw,nosuid,nodev,size=64m",
            self.image,
        ]
        try:
            process = await start_docker_task(
                args, name, docker_context=self.docker_context
            )
        except OSError as exc:
            raise RuntimeError(
                "分析沙箱不可用，请检查 Docker CLI 与配置的 Context"
            ) from exc
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(encoded),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError as exc:
            await finish_cleanup(
                stop_docker_task(process, name, docker_context=self.docker_context)
            )
            raise RuntimeError("分析超过时间限制，已停止执行") from exc
        except asyncio.CancelledError:
            # 一次性容器和 Python 请求有不同的生命周期，不能只停止本地等待。
            # 清理失败会作为失败上抛；只有确认容器不存在后才传播取消成功信号。
            await finish_cleanup(
                stop_docker_task(process, name, docker_context=self.docker_context)
            )
            raise
        if process.returncode != 0:
            raise RuntimeError(
                "分析沙箱运行失败：" + stderr.decode("utf-8", "replace")[:300]
            )
        if len(stdout) > 8_000_000:
            raise RuntimeError("分析输出超过大小限制")
        try:
            result = json.loads(stdout)
        except (ValueError, UnicodeDecodeError) as exc:
            raise RuntimeError("分析沙箱返回格式无效") from exc
        if not result.get("ok"):
            raise ValueError(str(result.get("error") or "分析执行失败")[:300])
        return result
