"""评分配置的边界与明确对话命令；不从学生材料或历史记忆自动提取规则。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GradingStandardSnapshot(BaseModel):
    """草稿生成时的有效评分依据；后续配置修改不能改写这份快照。"""

    source: Literal["default", "custom"]
    version: int = Field(ge=0)
    content: str = Field(min_length=1, max_length=4000)


class UpdateGradingStandard(BaseModel):
    """只允许修改当前登录导师，版本号防止多个页面相互覆盖。"""

    model_config = ConfigDict(extra="forbid")
    action: Literal["save", "reset"] = "save"
    content: str | None = Field(default=None, max_length=4000)
    expected_version: int = Field(ge=0)
