"""正式点评专用的中文技能加载器，只读取当前材料类型所需的规则。"""

from insight_link_agent.agent.skills.registry import builtin_root

SKILL_BY_TYPE = {1: "learning-plan", 2: "progress-report", 3: "self-summary"}


def guidance_for(material_type: int) -> str:
    """组合通用点评底线与类型规则，不加载导师聊天技能或授予额外工具。

    从 Python 安装包资源读取，开发目录与 wheel 安装后的路径保持一致；
    不依赖启动时工作目录，也不接收用户提供的任意文件路径。
    """
    name = SKILL_BY_TYPE.get(material_type)
    if name is None:
        raise ValueError(f"未知的材料类型: {material_type}")
    root = builtin_root()
    general = root.joinpath("comment-drafting", "SKILL.md").read_text(encoding="utf-8")
    specific = root.joinpath(name, "SKILL.md").read_text(encoding="utf-8")
    return f"{general}\n\n{specific}"
