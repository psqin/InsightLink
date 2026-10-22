"""长期配置的按需授权，不参与聊天任务分类或业务工具选择。"""

import asyncio
import json
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ConfigDict, Field, model_validator

SkillAction = Literal["save", "install", "enable", "disable", "delete"]


class MemoryChange(BaseModel):
    """只接受预设的无隐私偏好，模型不能把学生案例保存为长期配置。"""

    model_config = ConfigDict(extra="forbid")
    key: Literal[
        "language",
        "style",
        "format",
        "evaluation_method",
        "chart_method",
        "report_method",
    ]
    value: str = Field(min_length=1, max_length=40)
    memory_type: Literal["semantic", "procedural"] = "semantic"

    @model_validator(mode="after")
    def known_value(self):
        """内容白名单由存储边界执行，不用自然语言匹配推断是否要求保存。"""
        from insight_link_agent.agent.memory.keeper import (
            PREFERENCE_VALUES,
            PROCEDURE_VALUES,
        )

        allowed = (
            PREFERENCE_VALUES if self.memory_type == "semantic" else PROCEDURE_VALUES
        )
        if self.value not in allowed.get(self.key, set()):
            raise ValueError("不支持长期保存这项内容")
        return self


class ConfigurationChanges(BaseModel):
    """只描述用户明确要求的长期配置修改，不包含任务路由或业务权限。"""

    grading_change: Literal["none", "save", "reset"] = "none"
    skill_changes: list[SkillAction] = Field(default_factory=list)
    memory_changes: list[MemoryChange] = Field(default_factory=list)


class ConfigurationAccess:
    """仅在配置写工具被调用时检查原始对话，普通查询完全不调用分类模型。

    工具、网页、材料和技能正文不进入授权输入，避免下载文本授权自己安装。
    检查失败只拒绝配置写入，不影响查询、评价预览或普通回答。
    """

    def __init__(self, model, history):
        self.model = model
        self.history = history[-6:]
        self._value = None
        self._lock = asyncio.Lock()

    async def resolve(self):
        async with self._lock:
            if self._value is None:
                try:
                    value = await asyncio.wait_for(
                        self.model.with_structured_output(
                            ConfigurationChanges, method="function_calling"
                        ).ainvoke(
                            [
                                SystemMessage(
                                    content=(
                                        "只识别当前导师明确要求长期保存、修改或删除的配置。"
                                        "最近对话仅用于理解指代；助手建议不构成用户授权。"
                                        "一次性评价要求不等于修改长期评分标准。"
                                        "grading_change仅允许none/save/reset。"
                                        "未明确要求的技能或偏好变更输出空列表。"
                                        "不要判断任务类型，不要规划执行步骤。"
                                    )
                                ),
                                HumanMessage(
                                    content=json.dumps(self.history, ensure_ascii=False)
                                ),
                            ],
                            config={"run_name": "configuration-authorization"},
                        ),
                        timeout=12,
                    )
                    self._value = ConfigurationChanges.model_validate(value)
                except Exception:
                    self._value = ConfigurationChanges()
            return self._value


async def resolve_configuration(authorization):
    """配置工具也可接收已验证的声明，供独立组件测试使用。"""
    if isinstance(authorization, ConfigurationAccess):
        return await authorization.resolve()
    return authorization
