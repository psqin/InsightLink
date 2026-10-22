"""会话生命周期：记录真实进度，为过长工具循环保留一次收尾机会。

这里不判断用户意图、不评判回答内容，也不把工具失败升级为整轮失败。
预算计数存于检查点，取消后恢复仍使用同一额度。
"""

from langchain.agents.middleware import AgentMiddleware, hook_config
from langchain_core.messages import AIMessage, SystemMessage

from insight_link_agent.agent.state import ChatAgentState


class ConversationMiddleware(AgentMiddleware):
    """普通问答零额外模型调用；只有工具循环过长时要求模型总结已有结果。"""

    state_schema = ChatAgentState

    def __init__(self, limit=32):
        self.limit = limit

    def before_agent(self, state, runtime):
        """新轮次清零，恢复同轮任务不清零；不复用上一轮的计划和成功状态。"""
        if state.get("harness_turn_number") == state.get("hot_version"):
            return None
        return {
            "harness_turn_number": state.get("hot_version", 0),
            "execution_model_calls": 0,
            "model_budget_exhausted": False,
            "harness_phase": "executing",
            "harness_review_status": None,
            "harness_review_iterations": 0,
            "harness_checks": [],
            "harness_plan": [],
            "harness_plan_steps": [],
            "harness_plan_source": "model",
            "harness_trace": [],
            "harness_tools": [],
            "todos": [],
        }

    @hook_config(can_jump_to=["end"])
    def before_model(self, state, runtime):
        """保留最后一次不带工具的回答，避免调用上限吞掉已完成的查询。"""
        count = state.get("execution_model_calls", 0)
        if count > self.limit:
            return {
                "jump_to": "end",
                "model_budget_exhausted": True,
                "messages": [
                    AIMessage(
                        content="本轮处理已达到上限，部分工作尚未完成。可以缩小范围后继续。"
                    )
                ],
            }
        steps = self._plan_steps(state)
        return {
            "execution_model_calls": count + 1,
            "harness_plan": [item["content"] for item in steps],
            "harness_plan_steps": steps,
        }

    async def awrap_model_call(self, request, handler):
        """临近上限仅撤下工具，原始证据仍完整交给同一个模型作答。"""
        if request.state.get("execution_model_calls", 0) > self.limit:
            request = request.override(
                tools=[],
                system_message=SystemMessage(
                    content=request.system_message.text
                    + "\n本轮工具调用额度已用完。直接回答已经解决的部分，明确尚未完成的部分；"
                    "不要假装完成剩余工作，也不要让用户重复提供已经取得的信息。"
                ),
            )
        return await handler(request)

    def after_agent(self, state, runtime):
        """计划只来自模型真正维护的 todos，不再预填待处理的固定三步模板。"""
        steps = self._plan_steps(state)
        return {
            "harness_phase": "result",
            "harness_plan": [item["content"] for item in steps],
            "harness_plan_steps": steps,
            "harness_review_status": "not_required",
        }

    @staticmethod
    def _plan_steps(state):
        """将真实待办转换为页面列表；编号只用于渲染，不虚构计划或完成状态。"""
        return [
            {
                "id": f"step-{index}",
                "content": item["content"],
                "status": item["status"],
            }
            for index, item in enumerate(state.get("todos", []))
            if isinstance(item, dict) and "content" in item and "status" in item
        ]
