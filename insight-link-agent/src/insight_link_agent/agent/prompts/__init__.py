"""统一加载版本化中文提示词；不把业务流程散落在Python字符串中。"""

from functools import lru_cache
from importlib.resources import files


@lru_cache
def load_prompt(name: str) -> str:
    """名称只由应用常量传入，不接受用户文件路径。"""
    if name not in {"teacher", "public"}:
        raise ValueError("未知的系统提示词")
    return files(__package__).joinpath(name + ".md").read_text(encoding="utf-8")
