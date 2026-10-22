"""模型可自主选择的业务准备工具：理解交给模型，校验和确认由代码执行。"""

import json
from typing import Literal

from langchain_core.tools import tool
from openai import OpenAIError

from insight_link_agent.agent.conversation.actions import ActionKind
from insight_link_agent.agent.conversation.hitl import (
    ActionInput,
    ask_for_fields,
    prepare_from_input,
)
from insight_link_agent.agent.evaluation.suggestion import suggest_evaluation
from insight_link_agent.integrations.java_client import JavaAPIError
from insight_link_agent.integrations.processes import ResourceCleanupError


def build_business_tools(
    reader,
    *,
    pinned_material_id,
    proposal_sink,
    clarification_sink,
    pending_input=None,
    pending_proposal=None,
    draft_generator=None,
    grading_store=None,
    teacher_user_id=None,
    control_sink=None,
) -> list:
    """按调用方提供的能力装配工具，不根据用户句子的关键词授予或撤回工具。

    返回的工具只会读取数据、生成表单或预览；真实写接口不进入模型工具集。
    评分等自然语言字段由模型理解，范围由 ActionInput 校验，语义理解交给模型，最终交导师确认，不能把正则命中当作业务授权。
    """
    if proposal_sink is None:
        return []
    drafted_materials = {}

    def encode(value):
        """只序列化业务结果，不携带请求凭据。"""
        return json.dumps(value, ensure_ascii=False)

    def action_input(
        kind,
        material_id,
        student_user_id,
        student_name,
        score,
        content,
        restore_fields=(),
    ):
        """合并明确传入字段与同一目标的待办；绑定材料不可由模型更换。"""
        material_id = material_id if material_id is not None else pinned_material_id
        if pinned_material_id is not None and material_id != pinned_material_id:
            raise ValueError("当前对话已绑定另一份材料，请新建对话")
        values = dict(
            material_id=material_id,
            student_user_id=student_user_id,
            student_name=student_name,
            score=score,
            content=content,
        )
        seed = pending_input
        if seed is None and pending_proposal is not None:
            seed = ActionInput.model_validate(
                {
                    key: value
                    for key, value in pending_proposal.model_dump().items()
                    if key in ActionInput.model_fields
                }
            )
        same_target = (
            seed is not None
            and seed.kind == kind
            and (material_id is None or seed.material_id == material_id)
            and (student_user_id is None or seed.student_user_id == student_user_id)
            and (student_name is None or seed.student_name == student_name)
        )
        action = (
            seed.supplemented(values)
            if same_target
            else ActionInput(kind=kind, **values)
        )
        if restore_fields:
            if kind != "update_evaluation":
                raise ValueError("只有修改评价可以恢复正式记录中的字段")
            action = action.model_copy(
                update={
                    **{field: None for field in restore_fields},
                    "ai_suggested": False,
                    "score_rationale": "",
                    "grading_standard": None,
                }
            )
        return action

    @tool
    async def request_teacher_info(
        kind: ActionKind,
        material_id: int | None = None,
        student_user_id: int | None = None,
        student_name: str | None = None,
        score: float | None = None,
        content: str | None = None,
    ) -> str:
        """导师要求业务操作但缺少必要信息时展示补充表单。

        只填对话中已经确定的字段；不要猜测学生、材料或分数。仅询问缺失信息，
        已明确的字段可沿用待补表单，导师也能直接在聊天框回复。
        """
        if clarification_sink is None:
            return encode({"ok": False, "message": "补充信息通道不可用"})
        try:
            action = action_input(
                kind, material_id, student_user_id, student_name, score, content
            )
        except ValueError as exc:
            return encode({"ok": False, "message": str(exc)})
        if not action.missing_fields():
            return encode(
                {"ok": False, "message": "字段已齐，请调用 prepare_business_action"}
            )
        clarification_sink[:] = [action]
        return encode(
            {
                "ok": True,
                "status": "等待导师补充信息",
                "missing_fields": action.missing_fields(),
            }
        )

    @tool
    async def prepare_business_action(
        kind: ActionKind,
        material_id: int | None = None,
        student_user_id: int | None = None,
        student_name: str | None = None,
        score: float | None = None,
        content: str | None = None,
        restore_fields: list[Literal["score", "content"]] | None = None,
    ) -> str:
        """准备评价新增/修改/删除或发送留言的确认预览，只读取，不写业务数据。

        必须基于导师实际请求。content承载导师表达的评价反馈或留言内容，转述和命令语气也应理解为内容要求，不需要导师显式说出字段名。修改只传要改的字段，未改字段沿用现有待确认预览，
        再沿用正式记录；零分合法。restore_fields 用于撤回上次未提交的分数或评语
        修改并恢复正式记录。不得编造分数；导师要求自主评价时先用 draft_evaluation。
        """
        if proposal_sink:
            return encode({"ok": False, "message": "一次只准备一项操作"})
        if drafted_materials:
            return encode(
                {
                    "ok": False,
                    "message": "本轮建议草稿已生成，请先交导师核对，再准备确认预览",
                }
            )
        try:
            action = action_input(
                kind,
                material_id,
                student_user_id,
                student_name,
                score,
                content,
                restore_fields or (),
            )
            if action.missing_fields():
                if clarification_sink is not None:
                    clarification_sink[:] = [action]
                return encode(
                    {
                        "ok": False,
                        "message": ask_for_fields(action),
                        "missing_fields": action.missing_fields(),
                    }
                )
            proposal = await prepare_from_input(reader, action)
            if (
                pending_proposal is not None
                and pending_proposal.kind == kind == "update_evaluation"
                and pending_proposal.material_id == proposal.material_id
                and any(
                    getattr(pending_proposal, field) != getattr(proposal, field)
                    for field in (
                        "student_user_id",
                        "evaluation_id",
                        "expected_evaluated",
                        "expected_score",
                        "expected_content",
                    )
                )
            ):
                raise ValueError("原评价已变化，请重新查询材料后再修改预览")
        except (ValueError, JavaAPIError) as exc:
            return encode({"ok": False, "message": str(exc)})
        proposal_sink.append(proposal)
        if clarification_sink is not None:
            clarification_sink.clear()
        return encode(
            {
                "ok": True,
                "preview": proposal.preview(),
                "status": "等待导师确认，尚未执行",
            }
        )

    @tool
    async def cancel_pending_operation() -> str:
        """导师要求放弃尚未提交的草稿、补充表单或操作预览时调用。不会撤销已完成的评价或留言；取消后仍可继续回答同一条消息中的其他问题。"""
        nonlocal pending_input, pending_proposal
        if control_sink is None:
            return encode({"ok": False, "message": "当前无待办控制通道"})
        control_sink[:] = [{"cancel_pending": True}]
        pending_input = pending_proposal = None
        proposal_sink.clear()
        if clarification_sink is not None:
            clarification_sink.clear()
        drafted_materials.clear()
        return encode({"ok": True, "status": "已撤回待办，未变更正式记录"})

    result = [request_teacher_info, prepare_business_action, cancel_pending_operation]
    if draft_generator is not None and clarification_sink is not None:

        @tool
        async def draft_evaluation(material_id: int) -> str:
            """导师要求你自主评分、起草或重新评价时调用；不得自己编造评分。

            先定位唯一材料。工具读取授权正文、附件和历史，使用当前导师长期评分
            标准（未设置则用默认标准）生成并独立复核建议。返回可编辑草稿，
            不是正式成绩；本轮交导师核对，不自动提交为正式评价。
            """
            if pinned_material_id is not None and material_id != pinned_material_id:
                return encode({"ok": False, "message": "当前对话已绑定另一份材料"})
            if material_id in drafted_materials:
                return drafted_materials[material_id]
            if proposal_sink:
                return encode(
                    {"ok": False, "message": "本轮已准备预览，请先核对或取消"}
                )
            try:
                material, draft = await suggest_evaluation(
                    reader,
                    draft_generator,
                    material_id,
                    grading_store=grading_store,
                    teacher_user_id=teacher_user_id,
                )
                action = ActionInput(
                    kind="update_evaluation"
                    if material.evaluated
                    else "create_evaluation",
                    material_id=material_id,
                    score=draft.suggested_score,
                    content=draft.comment,
                    ai_suggested=True,
                    score_rationale=draft.score_rationale,
                    grading_standard=draft.grading_standard,
                )
            except (ValueError, JavaAPIError) as exc:
                return encode({"ok": False, "message": str(exc)})
            except ResourceCleanupError:
                raise  # 容器停止未确认必须交执行管理器处理，不能当普通建议失败继续。
            except (RuntimeError, OpenAIError):
                return encode({"ok": False, "message": "建议评价暂不可用，请稍后重试"})
            clarification_sink[:] = [action]
            response = encode(
                {
                    "ok": True,
                    "status": "建议草稿已生成，等待导师核对",
                    "draft": action.public(),
                }
            )

            drafted_materials[material_id] = response
            return response

        result.append(draft_evaluation)
    return result
