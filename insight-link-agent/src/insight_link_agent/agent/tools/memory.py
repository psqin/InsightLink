"""长期记忆工具：只使用归属已验证导师的 MemoryKeeper 和明确的白名单内容。"""

import asyncio
from typing import Literal

from langchain_core.tools import BaseTool, tool

from insight_link_agent.agent.configuration import resolve_configuration
from insight_link_agent.agent.memory.keeper import MemoryKeeper


def build_memory_tools(*, keeper: MemoryKeeper, authorization) -> list[BaseTool]:
    """将冻结的模型授权与当前导师的 Keeper 绑定，隔离检索和记忆写入。

    偏好或程序记忆仍须与本轮解析出的固定白名单完全匹配；学生案例不会在这里
    自动沉淀。同步 Mongo 访问保留在线程中执行，取消行为由上层统一管理。
    """

    @tool
    async def read_memory(query: str, limit: int = 5) -> str:
        """按需检索当前导师的偏好、脱敏任务和预设做事方法。"""
        return await asyncio.to_thread(keeper.search_text, query, limit)

    @tool
    async def remember(
        key: Literal[
            "language",
            "style",
            "format",
            "evaluation_method",
            "chart_method",
            "report_method",
        ],
        value: str,
        memory_type: Literal["semantic", "procedural"] = "semantic",
    ) -> str:
        """仅在导师明确要求长期沿用时保存白名单偏好或方法。

        semantic 允许语言、详略、格式和评价方法；procedural 允许
        评价方法，以及“图表标注数据来源/区分未评分材料”、
        “报告区分事实与建议/列出证据来源”。不保存学生案例。
        """
        requested = {
            item.key: item.value
            for item in (await resolve_configuration(authorization)).memory_changes
            if item.memory_type == memory_type
        }
        if requested.get(key) != value:
            return "本轮没有明确要求长期采用这项偏好或方法，未保存记忆。"
        if memory_type == "procedural":
            saved = await asyncio.to_thread(
                keeper.remember_procedure,
                key,
                value,
                "tool",
            )
        else:
            saved = await asyncio.to_thread(keeper.remember, key, value, "tool")
        if not saved:
            return "该内容不属于允许长期保存的偏好或方法，未保存记忆。"
        return "已保存这项导师长期偏好或方法。"

    return [read_memory, remember]
