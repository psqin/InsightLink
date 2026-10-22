"""对页面公开的执行摘要；只展示真实计划和工具状态，不伪称经过内容复核。"""


def public_result(state: dict) -> dict:
    """保留页面协议，移除回答评分和失败清空结果的旧语义。"""
    return {
        "task_type": "general",
        "route_source": "agent",
        "route_decision": "direct",
        "phase": state.get("harness_phase", "result"),
        "review_status": "not_required",
        "review_iterations": 0,
        "checks": [],
        "delivery_status": "ready"
        if state.get("produced_artifacts")
        else "not_requested",
        "signals": [],
        "plan": state.get("harness_plan", []),
        "trace": [],
        "plan_steps": state.get("harness_plan_steps", []),
        "plan_source": "model",
        "blocked": False,
    }
