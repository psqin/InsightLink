"""只接收声明式中文 SKILL.md；不解压、不安装依赖，也不执行包内代码。"""

import re
import unicodedata
from dataclasses import dataclass
from hashlib import sha256
from urllib.parse import unquote, urlsplit

import yaml
from yaml.tokens import AliasToken, AnchorToken

MAX_DESCRIPTION_CHARACTERS = 300
MAX_INSTRUCTION_CHARACTERS = 20_000
MAX_MARKDOWN_CHARACTERS = 24_000


class SkillValidationError(ValueError):
    """技能内容、元信息或地址不符合安全约束。"""


class SkillPermissionError(PermissionError):
    """当前导师原话没有授权这项技能变更，或者试图覆盖项目内置技能。"""


@dataclass(frozen=True)
class SkillDefinition:
    """经过校验的不可变技能声明，尚未持久化或自动运行。"""

    name: str
    description: str
    instructions: str
    slug: str


class _StrictLoader(yaml.SafeLoader):
    """拒绝重复键，避免 frontmatter 后值悄悄覆盖前值。"""


def _mapping(loader, node, deep=False):
    """仅在安全 YAML 加载器内构造键值映射。"""
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise SkillValidationError("技能 frontmatter 包含重复键或无效键")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def skill_slug(name: str) -> str:
    """虚拟路径仅使用固定前缀和摘要，中文显示名不参与路径拼接。"""
    return "mentor-" + sha256(name.encode("utf-8")).hexdigest()[:24]


def validate_definition(
    name: str, description: str, instructions: str
) -> SkillDefinition:
    """检查中文内容、大小和声明式边界；真实执行权限仍由受限工具决定。"""
    if not all(isinstance(value, str) for value in (name, description, instructions)):
        raise SkillValidationError("技能名称、说明和内容必须是文字")
    name = unicodedata.normalize("NFKC", name).strip()
    description, instructions = description.strip(), instructions.strip()
    if (
        not 1 <= len(name) <= 64
        or not re.fullmatch(r"[\w\u4e00-\u9fff][\w\u4e00-\u9fff -]*", name)
        or ".." in name
    ):
        raise SkillValidationError(
            "技能名称须为 1–64 字的中文、字母、数字、空格或短横线，不得包含路径"
        )
    if not 1 <= len(description) <= MAX_DESCRIPTION_CHARACTERS:
        raise SkillValidationError("技能说明须为 1–300 字")
    if not 1 <= len(instructions) <= MAX_INSTRUCTION_CHARACTERS:
        raise SkillValidationError("技能正文须为 1–20000 字")
    if not re.search(r"[\u4e00-\u9fff]", description) or not re.search(
        r"[\u4e00-\u9fff]", instructions
    ):
        raise SkillValidationError(
            "自定义技能的说明和正文须使用中文；外文技能请先翻译核对"
        )
    if any(
        ord(char) < 32 and char not in "\n\r\t" for char in description + instructions
    ):
        raise SkillValidationError("技能内容包含不可见控制字符")
    # 单文件声明可以说明如何调用已有分析工具，不得依赖随包脚本或宿主安装命令。
    forbidden = [
        r"(?:pip|pip3|npm|pnpm|yarn|uv\s+pip)\s+(?:install|add)\b",
        r"(?:subprocess\.|os\.(?:system|popen)|__import__\s*\(|\bexec\s*\(|\beval\s*\()",
        r"(?:scripts|assets)/[^\s\]\)]+\.(?:py|sh|ps1|bat|cmd|js)\b",
        r"\]\(\s*(?:file:|[A-Za-z]:[\\/]|/|\.\.[\\/])",
    ]
    if any(re.search(pattern, instructions, re.IGNORECASE) for pattern in forbidden):
        raise SkillValidationError(
            "目前只支持声明式 Markdown 技能，不能包含宿主安装命令、脚本依赖或本机文件引用"
        )
    return SkillDefinition(name, description, instructions, skill_slug(name))


def validate_skill_url(url: str) -> str:
    """远程安装只接受单个 SKILL.md；不接受压缩包、目录穿越或脚本包。"""
    if not isinstance(url, str) or len(url) > 2048:
        raise SkillValidationError("请提供单个公开 SKILL.md 的地址")
    try:
        parsed = urlsplit(url)
        path = unquote(parsed.path)
    except ValueError as exc:
        raise SkillValidationError("技能地址格式无效") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not path.endswith("/SKILL.md")
        or "\\" in path
        or ".." in path.split("/")
        or "%" in path
    ):
        raise SkillValidationError(
            "只支持单个公开 SKILL.md，不支持压缩包、脚本包或不安全路径"
        )
    return url


def parse_skill_markdown(markdown: str, *, name: str | None = None) -> SkillDefinition:
    """严格校验 frontmatter；外部内容不能声明工具权限、依赖或安装脚本。"""
    if not isinstance(markdown, str) or len(markdown) > MAX_MARKDOWN_CHARACTERS:
        raise SkillValidationError("SKILL.md 超过 24000 字上限")
    markdown = markdown.removeprefix("\ufeff").replace("\r\n", "\n")
    match = re.match(r"\A---\s*\n(.*?)\n---[ \t]*(?:\n|\Z)", markdown, re.DOTALL)
    if not match or len(match.group(1)) > 2000:
        raise SkillValidationError("SKILL.md 需要不超过 2000 字的 YAML frontmatter")
    try:
        if any(
            isinstance(token, (AliasToken, AnchorToken))
            for token in yaml.scan(match.group(1))
        ):
            raise SkillValidationError("技能 frontmatter 不支持 YAML 锚点或别名")
        metadata = yaml.load(match.group(1), Loader=_StrictLoader)
    except yaml.YAMLError as exc:
        raise SkillValidationError("技能 frontmatter 不是有效的安全 YAML") from exc
    allowed = {"name", "display_name", "description", "version"}
    if not isinstance(metadata, dict) or not {"name", "description"}.issubset(metadata):
        raise SkillValidationError("技能 frontmatter 必须包含 name 和 description")
    if set(metadata) - allowed or any(
        not isinstance(value, str) for value in metadata.values()
    ):
        raise SkillValidationError(
            "技能元信息只能包含文字 name、display_name、description 和 version，不得声明脚本或权限"
        )
    if not re.fullmatch(
        r"[\w\u4e00-\u9fff][\w\u4e00-\u9fff -]{0,63}", metadata["name"]
    ):
        raise SkillValidationError("技能 frontmatter 名称不安全")
    selected_name = name or metadata.get("display_name") or metadata["name"]
    return validate_definition(
        selected_name, metadata["description"], markdown[match.end() :]
    )


def render_skill_markdown(skill: dict) -> str:
    """输出兼容 DeepAgents 名称校验的 SKILL.md，保留中文显示名与正文。"""
    metadata = {
        "name": skill["slug"],
        "display_name": skill["name"],
        "description": skill["description"],
        "version": str(skill["version"]),
    }
    return (
        "---\n"
        + yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).strip()
        + "\n---\n\n"
        + skill["instructions"].strip()
        + "\n"
    )
