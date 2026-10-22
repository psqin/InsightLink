"""限定 DeepAgents 的实际专家集合，避免框架隐式添加通用专家。"""

from deepagents import (
    GeneralPurposeSubagentProfile,
    HarnessProfile,
    register_harness_profile,
)
from langchain_core.language_models.chat_models import BaseChatModel


def configure_expert_scope(model):
    """按当前模型注册关闭默认专家的配置，保留框架的其他默认设置。

    DeepAgents 0.7 没有逐次调用的 profile 参数，使用其公开注册接口。
    配置只控制能力范围，不含导师身份、凭据或请求数据，可安全复用于并发请求。
    """
    if not isinstance(model, BaseChatModel):
        return  # 离线工厂替身不构建真实框架图。
    provider = model._get_ls_params().get("ls_provider")
    if not isinstance(provider, str) or not provider:
        raise RuntimeError("无法识别模型提供方，不能安全限定专家范围")
    identifier = getattr(model, "model_name", None) or getattr(model, "model", None)
    key = (
        f"{provider}:{identifier}"
        if isinstance(identifier, str) and identifier
        else provider
    )
    register_harness_profile(
        key,
        HarnessProfile(
            general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
            tool_description_overrides={
                "task": (
                    "将明确任务委派给下列已配置专家，只能使用这里列出的名称。"
                    "主助手负责整合结果；评价沟通专家仅准备草稿和预览，正式写入仍须导师确认。\n"
                    "{available_agents}\n"
                    "description 写清目标与范围，必要上下文由服务端注入。不要重复执行已经完成的子任务。"
                )
            },
        ),
    )
