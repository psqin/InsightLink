"""技能安装的来源约束；配置变更由按需授权工具验证。"""

import re

import httpx


def provided_skill_url(url: str, question: str) -> bool:
    """安装地址必须出现在本轮导师消息中，模型不能从网页中另选下载目标。"""
    try:
        target = httpx.URL(url).copy_with(fragment=None)
        candidates = re.findall(r"https?://[^\s<>\"'`“”‘’]+", question)
    except (ValueError, httpx.InvalidURL):
        return False
    for candidate in candidates:
        try:
            if (
                httpx.URL(candidate.rstrip(".,;!?，。；？！、)]}）】")).copy_with(
                    fragment=None
                )
                == target
            ):
                return True
        except (ValueError, httpx.InvalidURL):
            continue
    return False
