"""按 ERP-AGENT 的 DeepAgents 装配方式运行导师聊天助手。

模型只接触经过裁剪的业务工具结果；Java token 留在 API 请求的 ContextVar 中。
Skill 使用虚拟 StateBackend，上下文归档按会话存入 MongoDB，不写宿主机工作目录。
"""

import asyncio

from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI
from openai import DefaultAsyncHttpxClient, DefaultHttpxClient

from insight_link_agent.agent.assembly import assemble_agent
from insight_link_agent.agent.models import (
    build_auxiliary_model,
)
from insight_link_agent.agent.research.workflow import PublicResearchAgent
from insight_link_agent.agent.runtime import (
    TurnContext,
    run_agent,
)
from insight_link_agent.agent.tools.academic_reader import ValidatedReadTools
from insight_link_agent.app.config import Settings
from insight_link_agent.integrations.analysis_sandbox import AnalysisSandbox
from insight_link_agent.integrations.web.fetch import PublicWebFetchClient
from insight_link_agent.integrations.web.search import DeepSeekWebSearchClient


class DeepAgentChatResponder(ValidatedReadTools):
    """组装 DeepAgent，并复用授权工具的参数校验与输出裁剪。"""

    def __init__(
        self,
        settings: Settings,
        memory_collection=None,
        grading_store=None,
        context_collection=None,
        skill_store=None,
    ):
        """装配模型；请求级工具和导师记忆在 respond_with_tools 中创建。"""
        super().__init__(settings)
        self._memory_collection = memory_collection
        self._grading_store = grading_store
        self._context_collection = context_collection
        self._skill_store = skill_store
        if settings.model_api_key and settings.model_name:
            self._model = ChatOpenAI(
                model=settings.model_name,
                api_key=settings.model_api_key,
                base_url=settings.model_base_url or None,
                temperature=0,
                timeout=60,
                max_retries=1,
                # 显式持有客户端，避免关闭一个响应器时误关 LangChain 缓存的共享连接。
                http_client=DefaultHttpxClient(),
                http_async_client=DefaultAsyncHttpxClient(),
            )
        else:
            self._model = None
        self._auxiliary_model = (
            build_auxiliary_model(self._model, settings) if self._model else None
        )
        self._configuration_model = self._auxiliary_model
        self._web_search = self._web_fetch = self._public_research = None
        if self._model is not None:
            # ERP 的网页工具以本地函数装配；搜索使用独立提供商凭据，绝不挪用
            # 任意 MODEL_API_KEY。公开工作流不接收学业 reader、历史或业务回执。
            search_key = (
                settings.web_search_api_key.get_secret_value()
                or settings.deepseek_api_key.get_secret_value()
            )
            self._web_search = DeepSeekWebSearchClient(
                api_key=search_key,
                model=settings.web_search_model,
                url=settings.deepseek_responses_url,
            )
            self._web_fetch = PublicWebFetchClient()
            self._public_research = PublicResearchAgent(
                self._model,
                self._web_search,
                self._web_fetch,
            )

    async def close(self) -> None:
        """关闭模型 HTTP 客户端，避免热重启后留下空闲连接。"""
        for name in ("_web_search", "_web_fetch"):
            web_client = getattr(self, name, None)
            if web_client is not None:
                await web_client.close()
        client = getattr(self._model, "root_async_client", None)
        if client is not None:
            await client.close()
        sync_client = getattr(self._model, "root_client", None)
        if sync_client is not None:
            await asyncio.to_thread(sync_client.close)

    async def respond_with_tools(
        self, history, reader, pinned_material_id=None, **context
    ):
        """直接进入模型工具循环；无需预分类即可查询、追问、准备操作或委派专家。"""
        if self._model is None:
            raise RuntimeError("请先配置模型名称和 API Key")
        turn = TurnContext(history, reader, pinned_material_id, **context)
        graph, capture, call_limit = assemble_agent(
            self,
            turn,
            create_agent=create_deep_agent,
            sandbox_factory=AnalysisSandbox,
        )
        return await run_agent(self, turn, graph, capture, call_limit)
