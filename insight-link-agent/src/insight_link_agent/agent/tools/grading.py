"""导师评分标准工具：长期配置更新必须来自本轮明确的修改要求。"""

import json

from langchain_core.tools import BaseTool, tool

from insight_link_agent.agent.configuration import resolve_configuration


def build_grading_tools(
    *, grading_store, teacher_user_id: int, authorization
) -> list[BaseTool]:
    """绑定当前导师及冻结的模型授权，保留评分标准的版本冲突检查。

    expected_version 仍由存储层作乐观锁校验，工厂不能替模型推断修改授权。
    """

    @tool
    async def get_grading_standard() -> str:
        """读取当前导师长期评分标准；未自定义时使用系统按材料类型的默认标准。"""
        from insight_link_agent.app.storage.grading_store import defaults

        return json.dumps(
            {**await grading_store.get(teacher_user_id), "defaults": defaults()},
            ensure_ascii=False,
        )

    @tool
    async def set_grading_standard(content: str, expected_version: int) -> str:
        """按当前导师明确要求修改长期评分标准；先读旧标准，完整保留未要求修改的维度。"""
        if (await resolve_configuration(authorization)).grading_change != "save":
            return json.dumps(
                {"ok": False, "message": "本轮未明确要求修改长期评分标准，未保存"},
                ensure_ascii=False,
            )
        try:
            saved = await grading_store.update(
                teacher_user_id, content, expected_version
            )
        except ValueError as exc:
            return json.dumps({"ok": False, "message": str(exc)}, ensure_ascii=False)
        return json.dumps({"ok": True, "standard": saved}, ensure_ascii=False)

    @tool
    async def reset_grading_standard(expected_version: int) -> str:
        """导师明确要求恢复系统默认评分标准时调用，仍须先读取当前版本。"""
        if (await resolve_configuration(authorization)).grading_change != "reset":
            return json.dumps(
                {"ok": False, "message": "本轮未授权恢复默认标准"}, ensure_ascii=False
            )
        try:
            saved = await grading_store.update(teacher_user_id, None, expected_version)
        except ValueError as exc:
            return json.dumps({"ok": False, "message": str(exc)}, ensure_ascii=False)
        return json.dumps({"ok": True, "standard": saved}, ensure_ascii=False)

    return [get_grading_standard, set_grading_standard, reset_grading_standard]
