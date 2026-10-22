"""统一启动和关闭模型、MCP、Mongo与执行管理器。"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from insight_link_agent.agent.conversation.interaction import ConversationInteraction
from insight_link_agent.agent.conversation.mongo_chat import MongoChatStore
from insight_link_agent.agent.evaluation.drafting import OpenAIDraftGenerator
from insight_link_agent.agent.evaluation.harness import build_graph
from insight_link_agent.agent.main_agent import DeepAgentChatResponder
from insight_link_agent.agent.observability.langsmith import SafeLangSmithTracer
from insight_link_agent.app.execution.manager import ExecutionManager
from insight_link_agent.app.storage.action_store import ActionStore
from insight_link_agent.app.storage.artifact_store import ArtifactStore
from insight_link_agent.app.storage.execution_store import ExecutionStore
from insight_link_agent.app.storage.grading_store import GradingStandardStore
from insight_link_agent.app.storage.input_store import InputStore
from insight_link_agent.app.storage.lease_store import ConversationLeaseStore
from insight_link_agent.app.storage.mongo_runtime import MongoRuntimeStore
from insight_link_agent.app.storage.run_store import RunStore
from insight_link_agent.app.storage.skill_store import SkillStore
from insight_link_agent.app.storage.trace_store import TraceStore
from insight_link_agent.integrations.attachments import AttachmentReader
from insight_link_agent.integrations.java_client import JavaClient
from insight_link_agent.integrations.mcp.client import MCPReader, local_stdio_transport
from insight_link_agent.integrations.mcp.server import build_mcp


def create_lifespan(
    settings,
    generator=None,
    java_transport=None,
    chat_responder=None,
    attachment_reader=None,
):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """仅使用 MongoDB，连接或配置失败即停止启动；退出时统一释放资源。"""
        if not settings.mongodb_url:
            raise RuntimeError("请配置 MONGODB_URL；Agent 仅使用 MongoDB 存储")
        mongo = MongoRuntimeStore(
            settings.mongodb_url, settings.mongodb_database, settings.mongodb_collection
        )
        java = JavaClient(settings.java_base_url, java_transport)
        attachment = attachment_reader or AttachmentReader(settings)
        responder = None
        reader = None
        tracer = SafeLangSmithTracer.from_settings(settings)
        try:
            await asyncio.to_thread(mongo.open)
            saver = await asyncio.to_thread(mongo.checkpointer)
            store = RunStore(mongo.runs)
            chat_store = MongoChatStore(mongo.chats, mongo.memories)
            action_store = ActionStore(mongo.interactions)
            input_store = InputStore(mongo.interactions)
            artifact_store = ArtifactStore(mongo.artifacts)
            lease_store = ConversationLeaseStore(mongo.leases)
            grading_store = GradingStandardStore(mongo.grading_standards)
            skill_store = SkillStore(mongo.skills)
            responder = chat_responder or DeepAgentChatResponder(
                settings,
                memory_collection=mongo.memories,
                grading_store=grading_store,
                context_collection=mongo.context_files,
                skill_store=skill_store,
            )
            reader = MCPReader(
                build_mcp(
                    java,
                    settings.max_history_pages,
                    attachment,
                    max_search_pages=settings.max_search_pages,
                )
                if java_transport is not None or attachment_reader is not None
                else local_stdio_transport(settings)
            )
            app.state.mongo = mongo
            app.state.java = java
            app.state.store = store
            app.state.chat_store = chat_store
            app.state.memory_collection = mongo.memories
            app.state.action_store = action_store
            app.state.input_store = input_store
            app.state.artifact_store = artifact_store
            app.state.chat_leases = lease_store
            app.state.trace_store = TraceStore(mongo.chats)
            app.state.grading_store = grading_store
            app.state.skill_store = skill_store
            app.state.chat_checkpointer = saver
            app.state.chat_responder = responder
            app.state.draft_generator = generator or OpenAIDraftGenerator(settings)
            app.state.attachment_reader = attachment
            app.state.reader = reader
            app.state.langsmith = tracer
            app.state.graph = build_graph(
                reader, app.state.draft_generator, saver, settings.max_revisions
            )
            app.state.chat_interaction = ConversationInteraction(saver, reader)
            app.state.execution_store = ExecutionStore(mongo.chats, mongo.leases)
            app.state.execution_manager = ExecutionManager(
                app.state.execution_store, tracer=tracer
            )
            yield
        finally:
            # 先中断任务并等资源清理，再关闭 MCP、Docker 与 Mongo 的共享连接。
            if hasattr(app.state, "execution_manager"):
                await app.state.execution_manager.close()
            if reader is not None:
                await reader.close()
            if responder is not None and chat_responder is None:
                await responder.close()
            if attachment_reader is None:
                await attachment.close()
            await java.close()
            await asyncio.to_thread(mongo.close)
            await tracer.aclose()

    return lifespan
