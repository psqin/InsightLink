"""导师评分标准接口；鉴权和归属检查由应用工厂显式注入。"""

import logging

from fastapi import Depends, HTTPException, Request

from insight_link_agent.agent.grading.policy import (
    UpdateGradingStandard,
)
from insight_link_agent.app.dependencies import RequestIdentity
from insight_link_agent.app.storage.grading_store import GradingConflict, defaults

logger = logging.getLogger(__name__)


def register_grading_routes(app, dependencies):
    """注册现有HTTP地址，保持前端契约稳定。"""
    identity = dependencies.identity

    @app.get("/api/grading-standard")
    async def get_grading_standard(
        request: Request, current: RequestIdentity = Depends(identity)
    ):
        """当前导师的有效配置及默认量表，身份只来自 Java 验证结果。"""
        services = request.app.state
        return {
            **await services.grading_store.get(current.actor.user_id),
            "defaults": defaults(),
        }

    @app.post("/api/grading-standard")
    async def update_grading_standard(
        body: UpdateGradingStandard,
        request: Request,
        current: RequestIdentity = Depends(identity),
    ):
        """修改可长期沿用的评分配置；不执行任何学生评价写入。"""
        services = request.app.state
        if body.action == "save" and body.content is None:
            raise HTTPException(status_code=422, detail="请填写完整的评分标准")
        try:
            current_standard = await services.grading_store.update(
                current.actor.user_id,
                body.content if body.action == "save" else None,
                body.expected_version,
            )
        except GradingConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {**current_standard, "defaults": defaults()}
