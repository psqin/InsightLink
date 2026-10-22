"""导师技能库 HTTP 管理：身份隔离、内置只读与版本冲突保护。"""

from urllib.parse import quote

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from insight_link_agent.agent.skills.registry import builtin_skills
from insight_link_agent.agent.skills.validation import (
    SkillPermissionError,
    SkillValidationError,
)
from insight_link_agent.app.storage.skill_store import SkillConflict, SkillNotFound


class SaveSkillRequest(BaseModel):
    """创建与修改使用同一协议；必须提供当前版本，避免覆盖其他页面的修改。"""

    model_config = ConfigDict(extra="forbid")
    description: str = Field(min_length=1, max_length=300)
    instructions: str = Field(min_length=1, max_length=20000)
    expected_version: int = Field(ge=0, strict=True)


class SetSkillEnabledRequest(BaseModel):
    """启停也检查版本，内置技能不接受此操作。"""

    model_config = ConfigDict(extra="forbid")
    enabled: bool = Field(strict=True)
    expected_version: int = Field(ge=1, strict=True)


def register_skill_routes(app: FastAPI, identity) -> None:
    """沿用 Java 验证的导师身份，模型和客户端都不能指定其他导师编号。"""

    def builtin(name):
        """内置技能从项目加载，不为它们创建数据库副本。"""
        return next((item for item in builtin_skills() if item["name"] == name), None)

    async def attempt(operation):
        """只转换预期的业务异常，数据库故障保留为真实服务错误。"""
        try:
            return await operation
        except SkillNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except SkillConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except SkillPermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except SkillValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/chat/skills")
    async def list_skills(request: Request, current=Depends(identity)):
        """列表只给元信息，正文和历史版本由详情按需读取。"""
        services = request.app.state
        items = builtin_skills() + await services.skill_store.list(
            current.actor.user_id
        )
        fields = {
            "name",
            "display_name",
            "description",
            "slug",
            "builtin",
            "enabled",
            "version",
            "updated_at",
        }
        return {
            "items": [
                {
                    **{key: value for key, value in item.items() if key in fields},
                    "builtin": bool(item.get("builtin")),
                }
                for item in items
            ]
        }

    @app.get("/api/chat/skills/{name}")
    async def get_skill(name: str, request: Request, current=Depends(identity)):
        """只返回当前导师技能或项目内置技能，其他导师同名技能不可见。"""
        services = request.app.state
        item = builtin(name)
        if item is not None:
            return {key: value for key, value in item.items() if key != "markdown"}
        return await attempt(services.skill_store.get(current.actor.user_id, name))

    @app.put("/api/chat/skills/{name}")
    async def save_skill(
        name: str, body: SaveSkillRequest, request: Request, current=Depends(identity)
    ):
        """保存声明式中文技能；不执行安装脚本，也不安装宿主机依赖。"""
        services = request.app.state
        return await attempt(
            services.skill_store.save(
                current.actor.user_id,
                name,
                body.description,
                body.instructions,
                body.expected_version,
            )
        )

    @app.patch("/api/chat/skills/{name}")
    async def toggle_skill(
        name: str,
        body: SetSkillEnabledRequest,
        request: Request,
        current=Depends(identity),
    ):
        """启停结果从下一轮对话重新加载，旧检查点技能副本随之刷新。"""
        services = request.app.state
        return await attempt(
            services.skill_store.set_enabled(
                current.actor.user_id, name, body.enabled, body.expected_version
            )
        )

    @app.delete("/api/chat/skills/{name}")
    async def delete_skill(
        name: str,
        request: Request,
        expected_version: int = Query(ge=1),
        current=Depends(identity),
    ):
        """仅删除当前导师指定版本的个人技能。"""
        services = request.app.state
        return await attempt(
            services.skill_store.delete(current.actor.user_id, name, expected_version)
        )

    @app.get("/api/chat/skills/{name}/export")
    async def export_skill(name: str, request: Request, current=Depends(identity)):
        """导出为下载附件，避免 Markdown/HTML 被同源页面作为活动内容执行。"""
        services = request.app.state
        item = builtin(name)
        if item is None:
            item = await attempt(services.skill_store.get(current.actor.user_id, name))
            markdown = await attempt(
                services.skill_store.export(current.actor.user_id, name)
            )
        else:
            markdown = item["markdown"]
        filename = f"{item['slug']}.md"
        label = quote(f"{item.get('display_name') or name}.md", safe="")
        return Response(
            content=markdown,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\"; filename*=UTF-8''{label}",
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "private, no-store",
            },
        )
