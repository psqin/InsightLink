"""主模型选择子 Agent 后，自动注入上下文并封装实际工具结果，不重放子任务。"""

import json
from dataclasses import replace

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from insight_link_agent.agent.subagents.contracts import DelegatedResult
from insight_link_agent.agent.subagents.runtime import delegation_id


class DelegationMiddleware(AgentMiddleware):
    """每次 task 调用有独立证据作用域；结果协议不能授予任何写权限。"""

    def __init__(self, specs, context, evidence):
        self.specs = {spec.name: spec for spec in specs}
        self.context, self.evidence = context, evidence

    def _request(self, request):
        """只注入 YAML 声明的字段；目标和待办来自服务端而非模型重复填写。"""
        call = request.tool_call
        spec = self.specs.get(call.get("args", {}).get("subagent_type"))
        if call["name"] != "task" or spec is None:
            return request, None
        args = call["args"]
        values = {
            **self.context,
            "task_objective": str(args.get("description", ""))[:2000],
        }
        methods = [
            str(message.content)[:1600]
            for message in request.state.get("messages", [])
            if isinstance(message, ToolMessage) and message.name == "read_memory"
        ][-2:]
        values["methods"] = methods
        context = {
            item.field: values.get(item.field) for item in spec.protocol.input_context
        }
        for field in spec.protocol.input_context:
            if field.required and context[field.field] is None:
                raise ValueError("子 Agent 委派缺少必需上下文")
        description = json.dumps(
            {"task": values["task_objective"], "context": context}, ensure_ascii=False
        )
        return request.override(
            tool_call={**call, "args": {**args, "description": description}}
        ), spec

    def _result(self, result, identifier, spec):
        """保留框架 Command 的其他更新，只替换对应 task 的工具消息。"""
        messages = (
            result.update.get("messages", [])
            if isinstance(result, Command)
            else [result]
        )
        events = [
            event
            for event in self.evidence.events
            if event.get("delegation_id") == identifier
        ]
        outputs = []
        for message in messages:
            if (
                not isinstance(message, ToolMessage)
                or message.tool_call_id != identifier
            ):
                outputs.append(message)
                continue
            status, operation, missing, artifacts = "answered", None, [], []
            for event in events:
                try:
                    data = json.loads(event["content"])
                except (ValueError, TypeError):
                    data = {}
                if not isinstance(data, dict):
                    continue
                if event["ok"] and event["name"] == "prepare_business_action":
                    status, operation = "awaiting_confirmation", data.get("preview")
                elif (
                    event["ok"]
                    and event["name"] == "draft_evaluation"
                    and status != "awaiting_confirmation"
                ):
                    status = "draft_ready"
                elif event["name"] in {
                    "request_teacher_info",
                    "prepare_business_action",
                } and data.get("missing_fields"):
                    if status not in {"awaiting_confirmation", "draft_ready"}:
                        status = "needs_input"
                    missing = data["missing_fields"]
                if event["ok"]:
                    artifacts.extend(data.get("files", []))
            failures = [event for event in events if not event["ok"]]
            if failures and status == "answered":
                status = "failed"
            if getattr(message, "status", "") == "error":
                status = "failed"
            text = str(message.content)[:6000]
            wrapped = DelegatedResult(
                summary=text,
                findings=text,
                status=status,
                sources=list(
                    dict.fromkeys(event["name"] for event in events if event["ok"])
                ),
                limitations=["部分工具未成功，结论须按实际证据核对"]
                if failures
                else [],
                artifacts=artifacts[:5],
                operation=operation,
                missing_fields=missing,
            )
            # 模型叙述不能覆盖服务端推导的状态，外层结构始终通过 Schema 校验。
            payload = {
                field: getattr(wrapped, field)
                for field in spec.protocol.output_format.sections
            }
            outputs.append(
                message.model_copy(
                    update={"content": json.dumps(payload, ensure_ascii=False)}
                )
            )
        if isinstance(result, Command):
            return replace(result, update={**result.update, "messages": outputs})
        return outputs[0]

    async def awrap_tool_call(self, request, handler):
        """只执行一次；异常交给现有工具／Harness 处理，不自动重试带副作用任务。"""
        call = request.tool_call
        if (
            call["name"] == "task"
            and call.get("args", {}).get("subagent_type") not in self.specs
        ):
            return ToolMessage(
                content=json.dumps(
                    {
                        "ok": False,
                        "error": "只能委派已配置的学情分析专家或评价沟通专家",
                    },
                    ensure_ascii=False,
                ),
                tool_call_id=call["id"],
                name="task",
                status="error",
            )
        prepared, spec = self._request(request)
        if spec is None:
            return await handler(request)
        identifier = request.tool_call["id"]
        token = delegation_id.set(identifier)
        try:
            result = await handler(prepared)
            return self._result(result, identifier, spec)
        finally:
            delegation_id.reset(token)
