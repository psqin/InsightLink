"""材料评价工作流接口；鉴权和归属检查由应用工厂显式注入。"""

import logging
from uuid import uuid4

from fastapi import Depends, HTTPException, Request
from langgraph.types import Command

from insight_link_agent.agent.evaluation.harness import material_hash
from insight_link_agent.app.dependencies import RequestIdentity
from insight_link_agent.app.presenters import _config, _public_state
from insight_link_agent.app.schemas import (
    DecisionRequest,
    StartRunRequest,
)
from insight_link_agent.integrations.attachments import AttachmentError
from insight_link_agent.integrations.mcp.auth import use_java_token

logger = logging.getLogger(__name__)


def register_runs_routes(app, dependencies):
    """注册现有HTTP地址，保持前端契约稳定。"""
    identity = dependencies.identity
    owned_run = dependencies.owned_run

    @app.post("/api/runs", status_code=201)
    async def start_run(
        body: StartRunRequest,
        request: Request,
        current: RequestIdentity = Depends(identity),
    ):
        """按授权材料启动可恢复的评价草稿工作流。"""
        services = request.app.state
        run_id = str(uuid4())
        await services.store.create(run_id, current.actor.user_id, body.material_id)
        try:
            with (
                use_java_token(current.token),
                services.langsmith.bind_run(
                    execution_id=run_id,
                    teacher_user_id=current.actor.user_id,
                ),
            ):
                result = await services.graph.ainvoke(
                    {
                        "material_id": body.material_id,
                        "actor_id": current.actor.user_id,
                        "phase": "planning",
                        "revisions": 0,
                    },
                    _config(run_id),
                )
        except ValueError as exc:
            await services.store.set_status(run_id, "failed")
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeError as exc:
            await services.store.set_status(run_id, "failed")
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception:
            await services.store.set_status(run_id, "failed")
            raise
        status = "awaiting_approval" if result.get("__interrupt__") else result["phase"]
        await services.store.set_status(run_id, status)
        return _public_state(run_id, status, result)

    @app.get("/api/runs/{run_id}")
    async def get_run(
        run_id: str,
        request: Request,
        current: RequestIdentity = Depends(identity),
    ):
        services = request.app.state
        record = await owned_run(request, run_id, current)
        snapshot = await services.graph.aget_state(_config(run_id))
        return _public_state(run_id, record.status, snapshot.values)

    @app.post("/api/runs/{run_id}/decision")
    async def decide(
        run_id: str,
        body: DecisionRequest,
        request: Request,
        current: RequestIdentity = Depends(identity),
    ):
        """记录导师对草稿的决定；正式业务评价仍走单独确认操作。"""
        services = request.app.state
        record = await owned_run(request, run_id, current)
        snapshot = await services.graph.aget_state(_config(run_id))
        state = snapshot.values
        if record.status != "awaiting_approval":
            raise HTTPException(status_code=409, detail="任务不在等待确认状态")
        current_material = await services.java.material(
            current.token, record.material_id
        )
        if current_material.evaluated or material_hash(current_material) != state.get(
            "material_hash"
        ):
            raise HTTPException(
                status_code=409, detail="材料或点评状态已变化，请重新生成草稿"
            )
        if state.get("attachment_digest"):
            try:
                latest_digest = await services.attachment_reader.digest(
                    current_material.file_url or ""
                )
            except AttachmentError as exc:
                raise HTTPException(
                    status_code=409, detail="附件目前无法复核，请重新生成草稿"
                ) from exc
            if latest_digest != state["attachment_digest"]:
                raise HTTPException(
                    status_code=409, detail="附件已变化，请重新生成草稿"
                )
        if not await services.store.claim_approval(run_id):
            raise HTTPException(status_code=409, detail="该任务正在被处理")
        try:
            with (
                use_java_token(current.token),
                services.langsmith.bind_run(
                    execution_id=run_id,
                    teacher_user_id=current.actor.user_id,
                ),
            ):
                result = await services.graph.ainvoke(
                    Command(resume=body.model_dump()), _config(run_id)
                )
        except Exception:
            await services.store.set_status(run_id, "awaiting_approval")
            raise
        await services.store.set_status(run_id, result["phase"])
        return _public_state(run_id, result["phase"], result)
