"""在工具与检查点之间补齐回执窗口，防止取消恢复重放已经完成的副作用。"""

from langchain.agents.middleware import AgentMiddleware

from insight_link_agent.agent.execution.context import current_execution
from insight_link_agent.agent.observability.evidence import SIDE_EFFECT_TOOLS


class ExecutionToolMiddleware(AgentMiddleware):
    """同时安装在主图和专家图；读工具仍由 LangGraph 的检查点正常恢复。"""

    def __init__(self, capture):
        self.capture = capture

    async def awrap_tool_call(self, request, handler):
        """只为受控应用工具留回执，不把 token、文件二进制或原始查询全文复制入库。"""
        execution = current_execution()
        if execution is None or request.tool_call["name"] not in SIDE_EFFECT_TOOLS:
            return await handler(request)
        return await execution.tool(request, handler, self.capture)
