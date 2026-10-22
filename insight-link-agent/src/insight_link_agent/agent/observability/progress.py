"""请求内进度通道：白名单事件、主／子 Agent 工具观测与图阶段变化。"""

import asyncio
import json
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import uuid4

from langchain_core.callbacks import AsyncCallbackHandler
from langgraph.types import Command

_channel = ContextVar("academic_progress", default=None)
TOOL_LABELS = {
    "search_student_materials": "查找学生材料",
    "get_material": "读取学习材料",
    "get_attachment_text": "解析材料附件",
    "get_student_history": "比较历史学习记录",
    "search_my_students": "查询指导学生",
    "get_student_profile": "读取学生资料",
    "list_my_students": "分页读取指导学生",
    "list_student_materials": "分页读取学生材料",
    "get_message_history": "查询留言记录",
    "research_public": "查询公开资料",
    "cancel_pending_operation": "撤回待确认操作",
    "web_search": "搜索公开资料",
    "web_fetch": "读取网页正文",
    "create_chart": "生成图表",
    "run_analysis_code": "运行分析代码",
    "create_report": "制作报告",
    "create_document": "制作分析文档",
    "create_table": "制作数据表格",
    "list_user_skills": "查看导师技能",
    "save_user_skill": "保存导师技能",
    "install_skill": "安装导师技能",
    "set_user_skill_enabled": "更新技能启用状态",
    "delete_user_skill": "删除导师技能",
    "export_user_skill": "导出导师技能",
    "request_teacher_info": "整理待补充信息",
    "prepare_business_action": "准备操作预览",
    "read_memory": "查阅已有偏好与方法",
    "remember": "保存导师明确偏好",
    "get_grading_standard": "读取导师评分标准",
    "set_grading_standard": "保存导师评分标准",
    "reset_grading_standard": "恢复默认评分标准",
    "draft_evaluation": "生成评价草稿",
    "write_todos": "更新任务步骤",
    "compact_conversation": "压缩会话上下文",
}
SUBAGENT_LABELS = {
    "learning-analyst": "学情分析专家",
    "evaluation-communication-specialist": "评价沟通专家",
}
PHASE_LABELS = {
    "planning": "整理任务步骤",
    "executing": "正在处理任务",
    "reviewing": "正在核对证据与结果",
    "result": "处理已结束",
}


class ProgressChannel:
    """有界且可跨线程投递；慢客户端不能无限占用内存或阻塞工具。"""

    def __init__(self):
        self.loop = asyncio.get_running_loop()
        self.queue = asyncio.Queue(maxsize=128)
        self.closed = False
        self.signatures = {}

    def publish(self, event: str, data: dict):
        """只由本模块生成固定字段；关闭后丢弃进度，终态由生产任务返回。"""

        def deliver():
            if not self.closed and not self.queue.full():
                self.queue.put_nowait((event, data))

        self.loop.call_soon_threadsafe(deliver)

    def state(self, state: dict):
        """只读取服务端 Harness 字段，不转发 messages、文件或内部图状态。"""
        # LangGraph先输出新输入与旧检查点合并后的状态，再执行本轮入口hook。
        # 未由本轮Harness盖章前，旧的satisfied/plan不能被前端当作新进度。
        # 旧版本恢复记录没有此字段时仍可正常观察，不要求离线迁移检查点。
        if "harness_turn_number" in state and state["harness_turn_number"] != state.get(
            "hot_version", 0
        ):
            return
        phase = state.get("harness_phase")
        if phase in PHASE_LABELS and self.signatures.get("phase") != phase:
            self.signatures["phase"] = phase
            self.publish("phase", {"phase": phase, "label": PHASE_LABELS[phase]})
        plan = state.get("harness_plan")
        steps = state.get("harness_plan_steps", [])
        signature = (list(plan or []), steps)
        if plan and self.signatures.get("plan") != signature:
            self.signatures["plan"] = signature
            self.publish(
                "plan",
                {
                    "items": list(plan),
                    "steps": steps,
                    "source": state.get("harness_plan_source", "template"),
                },
            )
        status = state.get("harness_review_status")
        iteration = state.get("harness_review_iterations", 0)
        signature = (status, iteration)
        if status and self.signatures.get("review") != signature:
            self.signatures["review"] = signature
            self.publish("review", {"status": status, "iteration": iteration})


@contextmanager
def bind_progress(channel):
    """仅绑定当前生产任务；并发导师的事件与凭据上下文相互隔离。"""
    token = _channel.set(channel)
    try:
        yield
    finally:
        _channel.reset(token)


def current_progress():
    """非流式调用返回空值，保留原 JSON 接口和测试替身的调用约定。"""
    return _channel.get()


def reviewing():
    """在复核模型开始前展示状态，不等到复核结束后才改变页面。"""
    if channel := current_progress():
        channel.publish(
            "phase", {"phase": "reviewing", "label": PHASE_LABELS["reviewing"]}
        )


async def observed_read(name, operation, *args):
    """授权资料的预读发生在模型图外，仍发布真实的开始／结束事件。"""
    channel = current_progress()
    identifier = uuid4().hex
    label = TOOL_LABELS[name]
    if channel:
        channel.publish("tool", {"id": identifier, "label": label, "status": "running"})
    try:
        result = await operation(*args)
    except BaseException:
        if channel:
            channel.publish(
                "tool", {"id": identifier, "label": label, "status": "failed"}
            )
        raise
    if channel:
        failed = isinstance(result, dict) and (
            result.get("ok") is False or bool(result.get("error"))
        )
        channel.publish(
            "tool",
            {
                "id": identifier,
                "label": label,
                "status": "failed" if failed else "completed",
            },
        )
    return result


def tool_failed(output, depth=0):
    """识别普通结果、工具消息和图 Command 内的失败，不向页面泄露正文。

    限制递归深度与列表长度，避免畸形输出拖慢进度处理；不靠回答文本猜测成功。
    """
    if depth > 6:
        return False
    if getattr(output, "status", "") == "error":
        return True
    if isinstance(output, Command):
        return tool_failed(output.update, depth + 1)
    if hasattr(output, "content"):
        return tool_failed(output.content, depth + 1)
    if isinstance(output, str):
        try:
            return tool_failed(json.loads(output), depth + 1)
        except (ValueError, TypeError):
            return False
    if isinstance(output, dict):
        if (
            output.get("ok") is False
            or output.get("error")
            or output.get("status") in ("failed", "error")
        ):
            return True
        return tool_failed(output.get("messages", []), depth + 1)
    if isinstance(output, (list, tuple)):
        return any(tool_failed(item, depth + 1) for item in output[:100])
    return False


class SafeProgressCallback(AsyncCallbackHandler):
    """接收真实工具回调；只转发名称白名单及成功状态，不传参数或输出。"""

    def __init__(self, channel):
        self.channel = channel
        self.activities = {}

    async def on_tool_start(
        self, serialized, input_str, *, run_id, inputs=None, **kwargs
    ):
        name = (serialized or {}).get("name")
        event, label = "tool", TOOL_LABELS.get(name)
        if name == "task":
            event = "subagent"
            if not isinstance(inputs, dict):
                try:
                    inputs = json.loads(input_str)
                except (ValueError, TypeError):
                    inputs = {}
            label = SUBAGENT_LABELS.get(
                inputs.get("subagent_type") if isinstance(inputs, dict) else None,
                "任务助手",
            )
        if label:
            self.activities[run_id] = (event, label)
            self.channel.publish(
                event, {"id": str(run_id), "label": label, "status": "running"}
            )

    async def on_tool_end(self, output, *, run_id, **kwargs):
        """业务失败可能以正常 ToolMessage 返回，仍应显示未完成。"""
        self._finish(run_id, "failed" if tool_failed(output) else "completed")

    async def on_tool_error(self, error, *, run_id, **kwargs):
        """异常正文可能含数据或供应商信息，不向页面转发。"""
        self._finish(run_id, "failed")

    def _finish(self, run_id, status):
        activity = self.activities.pop(run_id, None)
        if activity:
            event, label = activity
            self.channel.publish(
                event, {"id": str(run_id), "label": label, "status": status}
            )
