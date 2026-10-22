"""HTTP应用工厂：仅装配资源、依赖和路由，不放自然语言业务逻辑。"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from insight_link_agent.agent.observability.langsmith import disable_automatic_tracing
from insight_link_agent.app.config import get_settings
from insight_link_agent.app.dependencies import build_dependencies
from insight_link_agent.app.execution.routes import register_execution_routes
from insight_link_agent.app.routes.actions import register_actions_routes
from insight_link_agent.app.routes.chat import register_chat_routes
from insight_link_agent.app.routes.grading import register_grading_routes
from insight_link_agent.app.routes.history import register_history_routes
from insight_link_agent.app.routes.materials import register_materials_routes
from insight_link_agent.app.routes.runs import register_runs_routes
from insight_link_agent.app.routes.skills import register_skill_routes
from insight_link_agent.app.runtime import create_lifespan
from insight_link_agent.app.storage.execution_store import ExecutionConflict
from insight_link_agent.integrations.java_client import JavaAPIError


def create_app(
    settings=None,
    generator=None,
    java_transport=None,
    chat_responder=None,
    attachment_reader=None,
):
    """装配唯一应用；测试可替换外部模型、Java与附件实现。"""
    settings = settings or get_settings()
    disable_automatic_tracing()
    app = FastAPI(
        title="InsightLink Academic Agent",
        lifespan=create_lifespan(
            settings, generator, java_transport, chat_responder, attachment_reader
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            origin.strip()
            for origin in settings.cors_origins.split(",")
            if origin.strip()
        ],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["content-type", "token"],
    )

    @app.exception_handler(ExecutionConflict)
    async def execution_conflict(_request: Request, exc: ExecutionConflict):
        """并发与恢复冲突在响应头发出前报告。"""
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(JavaAPIError)
    async def java_error(_request: Request, exc: JavaAPIError):
        """统一转换Java业务拒绝，不把HTTP 200误当业务成功。"""
        return JSONResponse(status_code=exc.status, content={"detail": str(exc)})

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    dependencies = build_dependencies()
    send_message = register_chat_routes(app, dependencies)
    register_actions_routes(app, dependencies)
    register_runs_routes(app, dependencies)
    register_grading_routes(app, dependencies)
    register_materials_routes(app, dependencies)
    register_history_routes(app, dependencies.identity)
    register_skill_routes(app, dependencies.identity)
    register_execution_routes(
        app, dependencies.identity, dependencies.owned_conversation, send_message
    )
    return app


app = create_app()
