"""从声明式配置装配学业子 Agent，并限制每个 Agent 的工具集合。"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from insight_link_agent.agent.subagents.contracts import ContextProtocol

CONFIG_PATH = Path(__file__).with_name("subagents.yaml")
ALLOWED_TOOLS = frozenset(
    {
        "search_student_materials",
        "get_material",
        "get_attachment_text",
        "get_student_history",
        "search_my_students",
        "get_student_profile",
        "get_message_history",
        "list_my_students",
        "list_student_materials",
        "request_teacher_info",
        "prepare_business_action",
        "draft_evaluation",
        "create_chart",
        "run_analysis_code",
        "create_report",
        "create_document",
        "create_table",
    }
)
OPERATION_TOOLS = frozenset(
    {"request_teacher_info", "prepare_business_action", "draft_evaluation"}
)


@dataclass(frozen=True)
class SubagentSpec:
    name: str
    description: str
    system_prompt: str
    tools: tuple[str, ...]
    protocol: ContextProtocol = field(default_factory=ContextProtocol)


def load_subagent_specs(path: Path = CONFIG_PATH) -> tuple[SubagentSpec, ...]:
    """配置无效时停止装配，避免意外给子 Agent 过宽的工具权限。"""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    entries = raw.get("subagents") if isinstance(raw, dict) else None
    if not isinstance(entries, list) or not entries:
        raise ValueError("子 Agent 配置必须包含非空列表")
    specs = []
    names = set()
    for item in entries:
        if not isinstance(item, dict):
            raise ValueError("子 Agent 配置项必须是对象")
        name = item.get("name")
        description = item.get("description")
        prompt = item.get("system_prompt")
        tools = item.get("tools")
        if not all(
            isinstance(value, str) and value.strip()
            for value in (name, description, prompt)
        ):
            raise ValueError("子 Agent 名称、描述和提示词不能为空")
        if name in names:
            raise ValueError("子 Agent 名称不能重复")
        if (
            not isinstance(tools, list)
            or not tools
            or any(not isinstance(value, str) for value in tools)
            or len(set(tools)) != len(tools)
            or not set(tools) <= ALLOWED_TOOLS
        ):
            raise ValueError(f"子 Agent {name} 的工具权限无效")
        if (
            set(tools) & OPERATION_TOOLS
            and name != "evaluation-communication-specialist"
        ):
            raise ValueError("仅评价与沟通专家可以准备业务操作")
        names.add(name)
        protocol = ContextProtocol.model_validate(item.get("context_protocol") or {})
        specs.append(
            SubagentSpec(
                name, description.strip(), prompt.strip(), tuple(tools), protocol
            )
        )
    return tuple(specs)
