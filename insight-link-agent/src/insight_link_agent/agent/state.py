"""模型图的持久状态定义，供主图和中间件共同引用。

本模块不导入工作流、中间件或业务工具，避免状态与装配代码互相导入。
字段名和类型保持稳定；检查点仍按原字段恢复，不因目录整理变更恢复协议。
"""

from deepagents.graph import DeepAgentState


class ChatAgentState(DeepAgentState):
    """保留模型工具消息、HOT 同步位置和待办，供进程重启后恢复。"""

    hot_version: int
    turn_question: str
    turn_controls: list[dict]
    todos: list[dict]
    prepared_actions: list[dict]
    prepared_inputs: list[dict]
    produced_artifacts: list[dict]
    business_tool_names: list[str]
    harness_turn_number: int | None
    harness_phase: str
    harness_plan: list[str]
    harness_plan_steps: list[dict]
    harness_plan_source: str
    harness_trace: list[dict]
    harness_tools: list[dict]
    harness_review_status: str | None
    harness_review_iterations: int
    harness_checks: list[dict]
    execution_model_calls: int
    model_budget_exhausted: bool


class PublicResearchState(ChatAgentState):
    """计数随检查点保存；新公开轮次显式清零，不与私有业务图共享。"""

    research_model_calls: int
    research_tool_calls: int
    research_tool_reservations: list[str]
    research_allowed_tool_ids: list[str]
    research_engine: str
