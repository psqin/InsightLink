"""导师技能库的 Mongo 持久化；每导师一文档，懒建索引并保留有界版本历史。"""

import asyncio
import unicodedata
from copy import deepcopy
from datetime import datetime, timezone

from bson import BSON
from pymongo import IndexModel, ReturnDocument
from pymongo.errors import DuplicateKeyError

from insight_link_agent.agent.skills.registry import builtin_names
from insight_link_agent.agent.skills.validation import (
    SkillPermissionError,
    SkillValidationError,
    render_skill_markdown,
    skill_slug,
    validate_definition,
    validate_skill_url,
)
from insight_link_agent.app.storage.indexes import DeferredIndexes
from insight_link_agent.integrations.public_urls import (
    PublicURLValidationError,
    validate_public_url,
)


class SkillConflict(ValueError):
    """技能已被其他操作更新，不能用旧版本覆盖。"""


class SkillNotFound(LookupError):
    """当前导师技能库没有这项技能；不透露其他导师是否拥有同名技能。"""


class SkillStore:
    """技能与长期记忆分开存储；不设置 TTL，也不在读取时创建空集合。"""

    MAX_SKILLS = 20
    MAX_HISTORY = 5
    MAX_DOCUMENT_BYTES = 12 * 1024 * 1024

    def __init__(self, collection):
        self.collection = collection
        self.indexes = DeferredIndexes(collection, IndexModel("user_id", unique=True))

    @staticmethod
    def _user(user_id: int) -> int:
        """身份必须来自服务端验证结果，不能使用模型提供的用户编号。"""
        if type(user_id) is not int or user_id <= 0:
            raise SkillPermissionError("技能库需要已验证的导师身份")
        return user_id

    @staticmethod
    def _version(expected_version: int) -> None:
        """拒绝缺省、布尔值或负版本；创建时显式传入零。"""
        if type(expected_version) is not int or expected_version < 0:
            raise SkillValidationError(
                "请提供非负整数 expected_version，创建新技能时为 0"
            )

    @staticmethod
    def _name(name: str) -> str:
        """显示名用于查找，实际 Mongo 字段与文件路径仅使用生成的安全摘要。"""
        if not isinstance(name, str) or not name.strip() or len(name) > 64:
            raise SkillValidationError("技能名称无效")
        name = unicodedata.normalize("NFKC", name).strip()
        if name.casefold() in {item.casefold() for item in builtin_names()}:
            raise SkillPermissionError(
                "项目内置技能只读，不能覆盖、停用或删除；请使用新的自定义名称"
            )
        return name

    async def _portfolio(self, user_id: int) -> dict:
        """只按固定导师主键读取，集合不存在时返回虚拟空技能库。"""
        self._user(user_id)
        row = await asyncio.to_thread(
            self.collection.find_one, {"_id": user_id, "user_id": user_id}
        )
        return row or {"_id": user_id, "user_id": user_id, "revision": 0, "skills": {}}

    @staticmethod
    def _public(skill: dict) -> dict:
        """返回当前导师可见信息，去掉 Mongo 主键；版本历史最多五份。"""

        def convert(value):
            if isinstance(value, datetime):
                return value.replace(tzinfo=value.tzinfo or timezone.utc).isoformat()
            if isinstance(value, dict):
                return {key: convert(item) for key, item in value.items()}
            if isinstance(value, list):
                return [convert(item) for item in value]
            return value

        return {
            **convert(deepcopy(skill)),
            "display_name": skill["name"],
            "builtin": False,
        }

    async def list(self, user_id: int, include_disabled: bool = True) -> list[dict]:
        """最多返回二十个导师私有技能，不混入其他导师或项目内置技能。"""
        if type(include_disabled) is not bool:
            raise SkillValidationError("include_disabled 必须是布尔值")
        portfolio = await self._portfolio(user_id)
        return sorted(
            [
                self._public(skill)
                for skill in portfolio["skills"].values()
                if include_disabled or skill["enabled"]
            ],
            key=lambda item: item["name"],
        )

    async def get(self, user_id: int, name: str) -> dict:
        """用导师显示名精确查找，未命中时统一返回不存在。"""
        name = self._name(name)
        portfolio = await self._portfolio(user_id)
        skill = portfolio["skills"].get(skill_slug(name))
        if not skill or skill["name"] != name:
            raise SkillNotFound("当前导师没有这项自定义技能")
        return self._public(skill)

    async def _commit(self, portfolio: dict, skills: dict) -> int:
        """整份导师技能库使用 CAS，限额与并发更新一起原子生效。"""
        revision = portfolio["revision"]
        now = datetime.now(timezone.utc)
        update = {
            "user_id": portfolio["user_id"],
            "revision": revision + 1,
            "skills": skills,
            "updated_at": now,
        }
        if len(BSON.encode(update)) > self.MAX_DOCUMENT_BYTES:
            raise SkillValidationError(
                "导师技能库超过容量限制，请精简内容或删除不用的技能"
            )
        await asyncio.to_thread(self.indexes.ensure)
        try:
            row = await asyncio.to_thread(
                self.collection.find_one_and_update,
                {
                    "_id": portfolio["_id"],
                    "user_id": portfolio["user_id"],
                    "revision": revision,
                },
                {"$set": update, "$setOnInsert": {"created_at": now}},
                upsert=revision == 0,
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError as exc:
            raise SkillConflict("技能库已更新，请重新查看版本后再提交") from exc
        if row is None:
            raise SkillConflict("技能库已更新，请重新查看版本后再提交")
        return revision + 1

    async def save(
        self,
        user_id: int,
        name: str,
        description: str,
        instructions: str,
        expected_version: int,
        source_url: str | None = None,
        *,
        enabled: bool | None = None,
    ) -> dict:
        """创建或完整替换技能；变更保存旧快照，下轮对话才装载新版本。"""
        self._version(expected_version)
        definition = validate_definition(self._name(name), description, instructions)
        if enabled is not None and type(enabled) is not bool:
            raise SkillValidationError("enabled 必须是布尔值")
        if source_url is not None and (
            not isinstance(source_url, str) or len(source_url) > 2048
        ):
            raise SkillValidationError("技能来源地址无效")
        if source_url is not None:
            validate_skill_url(source_url)
            try:
                validate_public_url(source_url)
            except PublicURLValidationError as exc:
                raise SkillValidationError(
                    "技能来源应为不含凭据的公开 SKILL.md 地址"
                ) from exc
        portfolio = await self._portfolio(user_id)
        skills = deepcopy(portfolio["skills"])
        current = skills.get(definition.slug)
        if (current["version"] if current else 0) != expected_version:
            raise SkillConflict("技能版本已变化，请重新查看后再保存")
        if current is None and len(skills) >= self.MAX_SKILLS:
            raise SkillValidationError(
                "每位导师最多保留 20 个自定义技能，请先删除不再使用的技能"
            )
        now = datetime.now(timezone.utc)
        history = (
            (
                current.get("history", [])
                + [{key: value for key, value in current.items() if key != "history"}]
            )[-self.MAX_HISTORY :]
            if current
            else []
        )
        skill = {
            "name": definition.name,
            "slug": definition.slug,
            "description": definition.description,
            "instructions": definition.instructions,
            "enabled": enabled
            if enabled is not None
            else current.get("enabled", True)
            if current
            else True,
            "version": portfolio["revision"] + 1,
            "history": history,
            "source_url": source_url,
            "created_at": current["created_at"] if current else now,
            "updated_at": now,
        }
        skills[definition.slug] = skill
        await self._commit(portfolio, skills)
        return self._public(skill)

    async def set_enabled(
        self, user_id: int, name: str, enabled: bool, expected_version: int
    ) -> dict:
        """启停也生成版本，保证旧页面不能把更新后的内容错误停用。"""
        if type(enabled) is not bool:
            raise SkillValidationError("enabled 必须是布尔值")
        current = await self.get(user_id, name)
        return await self.save(
            user_id,
            current["name"],
            current["description"],
            current["instructions"],
            expected_version,
            current.get("source_url"),
            enabled=enabled,
        )

    async def delete(self, user_id: int, name: str, expected_version: int) -> dict:
        """仅删除当前导师指定版本；内置技能和其他导师的技能都不受影响。"""
        self._version(expected_version)
        name = self._name(name)
        portfolio = await self._portfolio(user_id)
        skills = deepcopy(portfolio["skills"])
        current = skills.get(skill_slug(name))
        if current is None:
            raise SkillNotFound("当前导师没有这项自定义技能")
        if current["version"] != expected_version:
            raise SkillConflict("技能版本已变化，请重新查看后再删除")
        del skills[current["slug"]]
        revision = await self._commit(portfolio, skills)
        return {"deleted": True, "name": name, "version": revision}

    async def export(self, user_id: int, name: str) -> str:
        """导出单个声明式 SKILL.md，不能导出数据库或其他导师的数据。"""
        return render_skill_markdown(await self.get(user_id, name))
