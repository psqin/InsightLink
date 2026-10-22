"""摘要与配置授权使用的辅助模型参数，保持主 Agent 的设置独立。

保留既有 review_model_name 配置名称以兼容 .env，不代表普通问答仍有复核关卡。
"""

from urllib.parse import urlsplit


def build_auxiliary_model(model, settings):
    """构造轻量辅助模型；仅在已知支持的原生端点关闭思考。"""
    updates = {"model_name": settings.review_model_name or settings.model_name}
    if urlsplit(settings.model_base_url or "").hostname == "api.deepseek.com":
        updates["extra_body"] = {
            **(getattr(model, "extra_body", None) or {}),
            "thinking": {"type": "disabled"},
        }
    # 共享本响应器拥有的 HTTP 客户端，不修改主模型或其他请求的配置。
    return model.model_copy(update=updates)
