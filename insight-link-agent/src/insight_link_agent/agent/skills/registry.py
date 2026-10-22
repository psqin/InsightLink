"""组合只读项目技能与导师私有技能，恢复到内存虚拟文件系统。"""

import re
from datetime import datetime, timezone
from importlib.resources import files

import yaml

from insight_link_agent.agent.skills.validation import render_skill_markdown


def builtin_root():
    """定位安装包内的中文技能资源；物理目录调整不影响模型的虚拟路径。"""
    return files("insight_link_agent").joinpath("agent", "skills", "builtin")


def builtin_files() -> dict[str, dict]:
    """将只读内置技能映射到稳定的 /skills 路径，兼容已有会话检查点。"""
    stamp = datetime.now(timezone.utc).isoformat()
    result = {}
    for folder in builtin_root().iterdir():
        document = folder.joinpath("SKILL.md")
        if document.is_file():
            result[f"/skills/{folder.name}/SKILL.md"] = {
                "content": document.read_text(encoding="utf-8"),
                "encoding": "utf-8",
                "created_at": stamp,
                "modified_at": stamp,
            }
    return result


def builtin_skills() -> list[dict]:
    """读取安装包内的内置技能，不提供写回项目文件的入口。"""
    result = []
    for folder in builtin_root().iterdir():
        document = folder.joinpath("SKILL.md")
        if not document.is_file():
            continue
        markdown = document.read_text(encoding="utf-8")
        pieces = markdown.split("---", 2)
        metadata = yaml.safe_load(pieces[1]) if len(pieces) == 3 else {}
        body = pieces[2].strip() if len(pieces) == 3 else markdown
        heading = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        result.append(
            {
                "name": str(metadata.get("name") or folder.name),
                "slug": folder.name,
                "display_name": str(
                    metadata.get("display_name")
                    or (heading.group(1).strip() if heading else None)
                    or metadata.get("name")
                    or folder.name
                ),
                "description": str(metadata.get("description") or ""),
                "instructions": body,
                "builtin": True,
                "enabled": True,
                "version": 0,
                "markdown": markdown,
            }
        )
    return sorted(result, key=lambda item: item["name"])


def builtin_names() -> set[str]:
    """目录名和 frontmatter 名称都保留，避免别名绕过内置保护。"""
    return {
        str(value)
        for item in builtin_skills()
        for value in (item["name"], item["slug"], item["display_name"])
    }


async def load_active_files(store, user_id: int) -> dict[str, dict]:
    """每轮读取当前有效版本；调用方须移除上轮停用/删除文件并刷新技能元数据。"""
    result = {}
    stamp = datetime.now(timezone.utc).isoformat()
    for skill in await store.list(user_id, include_disabled=False):
        result[f"/user-skills/{skill['slug']}/SKILL.md"] = {
            "content": render_skill_markdown(skill),
            "encoding": "utf-8",
            "created_at": skill.get("created_at") or stamp,
            "modified_at": skill.get("updated_at") or stamp,
        }
    return result
