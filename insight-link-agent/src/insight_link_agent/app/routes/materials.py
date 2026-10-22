"""材料摘要与产物下载接口；鉴权和归属检查由应用工厂显式注入。"""

import logging

from fastapi import Depends, HTTPException, Request
from fastapi.responses import Response

from insight_link_agent.app.dependencies import RequestIdentity
from insight_link_agent.integrations.mcp.auth import use_java_token

logger = logging.getLogger(__name__)


def register_materials_routes(app, dependencies):
    """注册现有HTTP地址，保持前端契约稳定。"""
    identity = dependencies.identity

    @app.get("/api/chat/materials/{material_id}/summary")
    async def chat_material_summary(
        material_id: int,
        request: Request,
        current: RequestIdentity = Depends(identity),
    ):
        """表单上方展示经 Java 验权的材料信息，不返回正文或附件地址。"""
        services = request.app.state
        with use_java_token(current.token):
            material = await services.reader.material(material_id)
            profile = await services.reader.student_profile(material.student_user_id)
        return {
            "material_id": material.id,
            "title": material.title,
            "student_name": profile.get("name") or "",
            "submit_time": material.submit_time,
            "material_type": material.material_type,
            "evaluated": bool(material.evaluated),
            "content_excerpt": material.content[:280],
        }

    @app.get("/api/chat/artifacts/{artifact_id}")
    async def get_chat_artifact(
        artifact_id: str,
        request: Request,
        current: RequestIdentity = Depends(identity),
    ):
        services = request.app.state
        row = await services.artifact_store.get(
            artifact_id,
            current.actor.user_id,
        )
        if row is None:
            raise HTTPException(status_code=404, detail="文件不存在或已过期")
        name, mime, content = row
        return Response(
            content=content,
            media_type=mime,
            headers={
                "Content-Disposition": f'attachment; filename="{name}"',
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "private, no-store",
            },
        )
