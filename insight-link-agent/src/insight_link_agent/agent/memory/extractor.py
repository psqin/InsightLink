"""情节仅从已执行工具归类；偏好语义由本轮模型决策提供。"""

TASKS = (
    (
        "learning_analysis",
        "分析学情并制作图表或报告",
        {
            "create_chart",
            "run_analysis_code",
            "create_report",
            "create_document",
            "create_table",
        },
    ),
    (
        "evaluation",
        "处理能力评价与反馈",
        {"prepare_business_action", "request_teacher_info", "draft_evaluation"},
    ),
    (
        "material",
        "查询或分析学习材料",
        {
            "search_student_materials",
            "list_student_materials",
            "get_material",
            "get_attachment_text",
            "get_student_history",
        },
    ),
    (
        "student_profile",
        "查询学生学籍信息",
        {"search_my_students", "list_my_students", "get_student_profile"},
    ),
    ("message", "查询或准备学生留言", {"get_message_history"}),
)


def summarize_episode(tool_names=()):
    """业务类别和结果来自执行证据，不再扫描用户或助手文字猜测任务。"""
    allowed = set().union(*(task[2] for task in TASKS))
    names = list(dict.fromkeys(name for name in tool_names if name in allowed))[:10]
    task = next((item for item in TASKS if item[2].intersection(names)), None)
    if task is None:
        return None
    kind, goal, _ = task
    outcome = (
        "已准备待确认操作"
        if "prepare_business_action" in names
        else "已生成待核对评价草稿"
        if "draft_evaluation" in names
        else "等待导师补充信息"
        if "request_teacher_info" in names
        else "已完成授权查询或分析"
    )
    return {
        "task_type": kind,
        "goal": goal,
        "outcome": outcome,
        "summary": f"目标：{goal}；结果：{outcome}",
        "tools": names,
    }
