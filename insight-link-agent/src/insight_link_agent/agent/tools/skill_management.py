"""面向模型的技能管理工具；每轮绑定已验证导师与原话授权。"""

from langchain_core.tools import tool

from insight_link_agent.agent.configuration import resolve_configuration
from insight_link_agent.agent.skills.lifecycle import provided_skill_url
from insight_link_agent.agent.skills.registry import builtin_skills
from insight_link_agent.agent.skills.source import SkillSourceError, SkillSourceReader
from insight_link_agent.agent.skills.validation import (
    MAX_MARKDOWN_CHARACTERS,
    SkillPermissionError,
    SkillValidationError,
    parse_skill_markdown,
    validate_skill_url,
)
from insight_link_agent.app.storage.skill_store import SkillConflict, SkillNotFound


def _metadata(skill: dict) -> dict:
    """工具列表和写入回执仅展示元信息，正文按需导出，减少上下文占用。"""
    fields = (
        "name",
        "display_name",
        "description",
        "enabled",
        "version",
        "builtin",
        "updated_at",
    )
    return {key: skill.get(key) for key in fields}


def build_skill_tools(
    store,
    user_id: int,
    question: str,
    *,
    authorization,
    source_reader=None,
) -> list:
    """固定已验证的导师身份，不向模型暴露切换用户或直接 Mongo 写入的参数。"""
    if type(user_id) is not int or user_id <= 0:
        raise SkillPermissionError("技能工具需要已验证的导师身份")

    async def require(action):
        """写工具各自复核动作类型，不能用“查看技能”触发隐式安装。"""
        if action not in (await resolve_configuration(authorization)).skill_changes:
            raise SkillPermissionError(
                "当前消息没有明确授权这项技能变更；请由导师明确要求安装、保存、更新、启停或删除技能"
            )

    def failed(exc):
        """返回结构化失败，进度回调据此正确标记失败且不泄露底层异常。"""
        return {"ok": False, "error": str(exc)}

    @tool
    async def list_user_skills(include_disabled: bool = True) -> dict:
        """查看当前导师的自定义技能和只读内置技能，包含启停状态和最新版本。"""
        try:
            custom = await store.list(user_id, include_disabled=include_disabled)
            return {
                "ok": True,
                "skills": [_metadata(item) for item in builtin_skills() + custom],
                "notice": "项目内置技能只读；自定义技能仅属于当前导师。",
            }
        except (SkillValidationError, SkillPermissionError) as exc:
            return failed(exc)

    @tool
    async def save_user_skill(
        name: str, description: str, instructions: str, expected_version: int = 0
    ) -> dict:
        """导师明确要求保存或更新中文技能时调用；创建版本为0，更新必须先查看当前版本。"""
        try:
            await require("save")
            saved = await store.save(
                user_id, name, description, instructions, expected_version
            )
            return {
                "ok": True,
                "skill": _metadata(saved),
                "notice": "技能已长期保存，从下一轮对话开始按需加载；本轮不会重新执行或立即取得额外权限。",
            }
        except (SkillValidationError, SkillPermissionError, SkillConflict) as exc:
            return failed(exc)

    @tool
    async def install_skill(
        url: str, name: str = "", expected_version: int = 0
    ) -> dict:
        """导师明确要求安装时，校验并导入单个公开中文SKILL.md；不支持脚本包或安装依赖。"""
        owned_reader = None
        try:
            await require("install")
            validate_skill_url(url)
            if not provided_skill_url(url, question):
                raise SkillValidationError(
                    "请导师在本轮消息中明确提供要安装的公开 SKILL.md 地址，不能由模型自行选择下载地址"
                )
            reader = source_reader
            if reader is None:
                owned_reader = reader = SkillSourceReader()
            first = await reader.fetch(url, offset=0, limit=12000)
            final_url = first.get("url") or url
            validate_skill_url(final_url)
            source_characters = first.get("source_characters")
            if (
                first.get("content_type") not in {"text/plain", "text/markdown"}
                or first.get("truncated")
                or type(source_characters) is not int
                or not 1 <= source_characters <= MAX_MARKDOWN_CHARACTERS
            ):
                raise SkillValidationError(
                    "远程技能必须是完整、不过大的纯文本 SKILL.md，不接受网页或压缩包"
                )
            markdown = first.get("text", "")
            offset = first.get("next_offset")
            pages = 1
            while offset is not None:
                if (
                    type(offset) is not int
                    or offset != len(markdown)
                    or offset <= 0
                    or pages >= 3
                ):
                    raise SkillValidationError("远程技能分页结果无效")
                page = await reader.fetch(url, offset=offset, limit=12000)
                if (
                    not page.get("text")
                    or page.get("url", final_url) != final_url
                    or page.get("sha256") != first.get("sha256")
                    or page.get("source_characters") != first.get("source_characters")
                ):
                    raise SkillValidationError(
                        "远程技能在读取过程中发生变化，请重新安装"
                    )
                markdown += page.get("text", "")
                next_offset = page.get("next_offset")
                if (
                    len(markdown) > MAX_MARKDOWN_CHARACTERS
                    or next_offset is not None
                    and (type(next_offset) is not int or next_offset <= offset)
                ):
                    raise SkillValidationError("远程技能内容过大或分页结果无效")
                offset = next_offset
                pages += 1
            if len(markdown) != source_characters:
                raise SkillValidationError("远程技能原文未完整读取，请重新安装")
            definition = parse_skill_markdown(markdown, name=name or None)
            # 仅保存声明文本；下载内容本身永远不能授予安装、工具调用或业务写入权限。
            saved = await store.save(
                user_id,
                definition.name,
                definition.description,
                definition.instructions,
                expected_version,
                source_url=final_url,
            )
            return {
                "ok": True,
                "skill": _metadata(saved),
                "notice": "已校验并保存声明式技能，从下一轮对话按需加载。未安装依赖、执行脚本或授予新工具权限。",
            }
        except (
            SkillValidationError,
            SkillPermissionError,
            SkillConflict,
            SkillSourceError,
        ) as exc:
            return failed(exc)
        finally:
            if owned_reader is not None:
                await owned_reader.close()

    @tool
    async def set_user_skill_enabled(
        name: str, enabled: bool, expected_version: int
    ) -> dict:
        """导师明确要求启用或停用某项自定义技能时调用，下一轮对话生效。"""
        try:
            await require("enable" if enabled else "disable")
            saved = await store.set_enabled(user_id, name, enabled, expected_version)
            return {
                "ok": True,
                "skill": _metadata(saved),
                "notice": "技能状态已保存，下一轮对话生效；不会追溯改变当前已经执行的操作。",
            }
        except (
            SkillValidationError,
            SkillPermissionError,
            SkillConflict,
            SkillNotFound,
        ) as exc:
            return failed(exc)

    @tool
    async def delete_user_skill(name: str, expected_version: int) -> dict:
        """导师明确要求删除某项自定义技能时调用；项目内置技能不可删除。"""
        try:
            await require("delete")
            result = await store.delete(user_id, name, expected_version)
            return {
                "ok": True,
                **result,
                "notice": "技能已删除，下一轮不再加载；不会追溯改变当前已经执行的操作。",
            }
        except (
            SkillValidationError,
            SkillPermissionError,
            SkillConflict,
            SkillNotFound,
        ) as exc:
            return failed(exc)

    @tool
    async def export_user_skill(name: str) -> dict:
        """按需查看或导出某项技能的完整Markdown声明，内置技能也可只读导出。"""
        try:
            builtins = {item["name"]: item for item in builtin_skills()}
            markdown = (
                builtins[name]["markdown"]
                if name in builtins
                else await store.export(user_id, name)
            )
            return {
                "ok": True,
                "name": name,
                "markdown": markdown,
                "notice": "这是技能声明文本，仅用于查看或导出，不会自动执行。",
            }
        except (SkillValidationError, SkillPermissionError, SkillNotFound) as exc:
            return failed(exc)

    return [
        list_user_skills,
        save_user_skill,
        install_skill,
        set_user_skill_enabled,
        delete_user_skill,
        export_user_skill,
    ]
