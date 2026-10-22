"""stdio进程生命周期、MCP调用、远端附件取消确认和只读协议适配。"""

import asyncio
import os
import sys
from pathlib import Path
from uuid import uuid4

from fastmcp import Client, FastMCP
from fastmcp.client.transports import StdioTransport

from insight_link_agent.app.config import Settings
from insight_link_agent.app.schemas import Material, Source
from insight_link_agent.integrations.java_client import JavaAPIError
from insight_link_agent.integrations.mcp.auth import _token
from insight_link_agent.integrations.processes import (
    ResourceCleanupError,
    finish_cleanup,
)


def local_stdio_transport(settings: Settings) -> StdioTransport:
    """启动业务 stdio MCP 子进程，不把模型凭据传入子进程。"""
    inherited = {
        key: value
        for key, value in os.environ.items()
        if key.upper()
        in {
            "PATH",
            "SYSTEMROOT",
            "WINDIR",
            "TEMP",
            "TMP",
            "COMSPEC",
            "USERPROFILE",
            "HOME",
            "PYTHONUTF8",
            "DOCKER_CONFIG",
            "SSH_AUTH_SOCK",
        }
    }
    inherited.update(
        {
            "JAVA_BASE_URL": settings.java_base_url,
            "DOCKER_CONTEXT": settings.docker_context,
            "MAX_HISTORY_PAGES": str(settings.max_history_pages),
            "MAX_SEARCH_PAGES": str(settings.max_search_pages),
            "ATTACHMENT_ALLOWED_HOSTS": settings.attachment_allowed_hosts,
            "ATTACHMENT_MAX_BYTES": str(settings.attachment_max_bytes),
            "ATTACHMENT_SANDBOX_IMAGE": settings.attachment_sandbox_image,
            "ATTACHMENT_TIMEOUT_SECONDS": str(settings.attachment_timeout_seconds),
            "PYTHONIOENCODING": "utf-8",
        }
    )
    return StdioTransport(
        command=sys.executable,
        args=["-m", "insight_link_agent.integrations.mcp.server"],
        env=inherited,
        cwd=str(Path(__file__).resolve().parents[4]),
        keep_alive=True,
    )


class MCPReader:
    def __init__(self, transport: FastMCP | StdioTransport):
        self._transport = transport
        self._stdio = isinstance(transport, StdioTransport)

    async def _call(self, name: str, arguments: dict):
        """调用业务工具并统一转换 MCP、Java 错误。

        stdio 子进程无法共享 ContextVar，因此显式传递本次请求的 Java
        token；进程内 FastMCP 工具则从当前请求的 ContextVar 读取。
        """
        call_arguments = dict(arguments)
        cancel_id = (
            uuid4().hex if self._stdio and name == "get_attachment_text" else None
        )
        if self._stdio:
            call_arguments["auth_token"] = _token()
        if cancel_id is not None:
            call_arguments["request_id"] = cancel_id
        try:
            async with Client(self._transport, timeout=30, init_timeout=30) as client:
                result = await client.call_tool(name, call_arguments)
        except JavaAPIError:
            raise
        except asyncio.CancelledError:
            if cancel_id is not None:
                # 取消通知仅代表发送请求，必须等远端下载/容器 finally 完成后才能
                # 让本轮任务进入已取消。只读取消确认不重试正式评价或留言写操作。
                await finish_cleanup(self._confirm_attachment_stopped(cancel_id))
            raise
        except Exception as exc:
            raise JavaAPIError(503, "本地业务 MCP 暂时不可用") from exc
        if result.is_error:
            raise JavaAPIError(502, f"MCP 工具 {name} 执行失败")
        value = getattr(result, "data", None)
        if value is None:
            value = result.structured_content
        if not isinstance(value, dict) or not isinstance(value.get("ok"), bool):
            raise JavaAPIError(502, f"MCP 工具 {name} 返回格式错误")
        if not value["ok"]:
            status = value.get("status")
            if not isinstance(status, int) or status < 400 or status > 599:
                status = 502
            raise JavaAPIError(
                status, str(value.get("message") or "点评系统拒绝了请求")
            )
        return value.get("value")

    async def _confirm_attachment_stopped(self, request_id: str) -> None:
        """复用仍健康的 stdio 通道等待清理；任何不确定结果显式上抛。"""
        try:
            async with asyncio.timeout(30):
                result = await self._call(
                    "cancel_attachment_read", {"request_id": request_id}
                )
                if not isinstance(result, dict) or result.get("stopped") is not True:
                    raise ResourceCleanupError("未能确认附件任务已停止")
        except ResourceCleanupError:
            raise
        except Exception as exc:
            raise ResourceCleanupError("未能确认远端附件任务已停止") from exc

    async def close(self) -> None:
        if self._stdio:
            await self._transport.disconnect()

    async def material(self, material_id: int) -> Material:
        return Material.model_validate(
            await self._call("get_material", {"material_id": material_id})
        )

    async def search_materials(
        self, student_name: str, title_keyword: str = ""
    ) -> dict:
        return await self._call(
            "search_student_materials",
            {"student_name": student_name, "title_keyword": title_keyword},
        )

    async def student_name(self, student_user_id: int) -> str:
        return str(
            await self._call("get_student_name", {"student_user_id": student_user_id})
        )

    async def student_profile(self, student_user_id: int) -> dict:
        return await self._call(
            "get_student_profile", {"student_user_id": student_user_id}
        )

    async def search_my_students(
        self, student_name: str = "", student_no: str = ""
    ) -> dict:
        return await self._call(
            "search_my_students",
            {
                "student_name": student_name,
                "student_no": student_no,
            },
        )

    async def student_page(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        class_name: str = "",
        major: str = "",
        college: str = "",
        student_name: str = "",
        student_no: str = "",
    ) -> dict:
        """逐页读取导师花名册；凭据仍由 _call 按当前请求注入。"""
        return await self._call(
            "list_my_students",
            {
                "page": page,
                "page_size": page_size,
                "class_name": class_name,
                "major": major,
                "college": college,
                "student_name": student_name,
                "student_no": student_no,
            },
        )

    async def material_page(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        student_name: str = "",
        student_no: str = "",
        student_user_id: int | None = None,
        class_name: str = "",
        title_keyword: str = "",
        evaluated: int | None = None,
        material_type: int | None = None,
    ) -> dict:
        """逐页读取授权材料及范围状态；不在 Reader 中做二次截断。"""
        return await self._call(
            "list_student_materials",
            {
                "page": page,
                "page_size": page_size,
                "student_name": student_name,
                "student_no": student_no,
                "student_user_id": student_user_id,
                "class_name": class_name,
                "title_keyword": title_keyword,
                "evaluated": evaluated,
                "material_type": material_type,
            },
        )

    async def message_history(self, student_user_id: int, page: int = 1) -> dict:
        return await self._call(
            "get_message_history",
            {
                "student_user_id": student_user_id,
                "page": page,
            },
        )

    async def create_evaluation(
        self, material_id: int, score: float, content: str
    ) -> None:
        await self._call(
            "create_evaluation",
            {
                "material_id": material_id,
                "score": score,
                "content": content,
            },
        )

    async def update_evaluation(
        self, material_id: int, evaluation_id: int, score: float, content: str
    ) -> None:
        await self._call(
            "update_evaluation",
            {
                "material_id": material_id,
                "evaluation_id": evaluation_id,
                "score": score,
                "content": content,
            },
        )

    async def delete_evaluation(self, material_id: int, evaluation_id: int) -> None:
        await self._call(
            "delete_evaluation",
            {
                "material_id": material_id,
                "evaluation_id": evaluation_id,
            },
        )

    async def send_student_message(self, student_user_id: int, content: str) -> None:
        await self._call(
            "send_student_message",
            {
                "student_user_id": student_user_id,
                "content": content,
            },
        )

    async def history(
        self, student_user_id: int, current_material_id: int
    ) -> list[Source]:
        raw = await self._call(
            "get_student_history",
            {
                "student_user_id": student_user_id,
                "current_material_id": current_material_id,
            },
        )
        return [Source.model_validate(item) for item in raw]

    async def attachment(
        self,
        material_id: int,
        offset: int = 0,
        limit: int = 40,
        page: int | None = None,
    ) -> dict:
        """按材料授权范围回读后续片段，隐藏实际文件 URL 与登录凭据。"""
        return await self._call(
            "get_attachment_text",
            {
                "material_id": material_id,
                "offset": offset,
                "limit": limit,
                "page": page,
            },
        )
