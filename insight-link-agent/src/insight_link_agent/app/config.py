"""独立 Agent 服务的配置入口；运行凭据只从本地环境读取。"""

from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """集中声明模型、Mongo、上下文预算与沙箱限制，禁止写死运行密钥。

    env_file 相对于服务启动目录，本机从项目根目录启动；Compose读取同一份
    根目录 .env 并注入环境变量，部署专用字段由Compose处理并在这里忽略。
    AliasChoices 仅兼容已有部署的环境变量名，不代表存在多套运行时实现。
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    java_base_url: str = "http://127.0.0.1:8080"
    # validation_alias 可以读取多个配置，启用最先的
    model_name: str = Field(
        default="", validation_alias=AliasChoices("MODEL_NAME", "DEEPSEEK_MODEL")
    )
    model_api_key: str = Field(
        default="", validation_alias=AliasChoices("MODEL_API_KEY", "DEEPSEEK_API_KEY")
    )
    model_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("MODEL_BASE_URL", "DEEPSEEK_BASE_URL"),
    )
    review_model_name: str = ""
    # 显式开关控制脱敏观测；不使用 SDK 自动 tracing，防止学生正文和 token 外传。
    langsmith_enabled: bool = False
    # SecretStr：加密 / repr=False,exclude=True：print和json不出现该字段
    langsmith_api_key: SecretStr = Field(
        default=SecretStr(""), repr=False, exclude=True
    )
    langsmith_project: str = "insight-link-agent"
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_workspace_id: str = ""
    # 的网页搜索使用 DeepSeek Responses API。与主对话的提供商凭据分开，
    # 仅显式 WEB_SEARCH_API_KEY 或本项目的 DEEPSEEK_API_KEY 可用于该接口。
    # 普通 MODEL_API_KEY 不会被自动发送给另一家模型服务。
    web_search_api_key: SecretStr = Field(
        default=SecretStr(""), repr=False, exclude=True
    )
    deepseek_api_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias="DEEPSEEK_API_KEY",
        repr=False,
        exclude=True,
    )
    web_search_model: str = "deepseek-v4-pro"
    deepseek_responses_url: str = "https://api.deepseek.com/responses"
    mongodb_url: str = Field(
        default="", validation_alias=AliasChoices("MONGODB_URL", "MONGO_URL")
    )
    mongodb_database: str = Field(
        default="insight_link_agent",
        validation_alias=AliasChoices("MONGODB_DATABASE", "MONGO_DATABASE"),
    )
    mongodb_collection: str = "insight_link_agent"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    max_history_pages: int = 5
    # ge=1,le=1000, 允许的范围
    max_search_pages: int = Field(default=100, ge=1, le=1000)
    # 全体查询允许多轮翻页，仍有硬预算，避免错误模型无限调用。
    bulk_query_call_limit: int = Field(default=128, ge=8, le=256)
    # 点评草稿最多修订轮数
    max_revisions: int = 2
    # 按模型实际输入窗口配置；系统提示词与工具定义也计入触发预算。
    context_max_input_tokens: int = Field(default=32768, ge=4096, le=2_000_000)
    context_trigger_ratio: float = Field(default=0.85, ge=0.5, le=0.95)
    context_keep_messages: int = Field(default=8, ge=2, le=50)
    context_max_argument_chars: int = Field(default=2000, ge=200, le=20000)
    context_tool_result_tokens: int = Field(default=6000, ge=500, le=100000)
    context_summary_max_tokens: int = Field(default=2000, ge=200, le=8000)
    context_summary_timeout_seconds: int = Field(default=45, ge=5, le=120)
    # 固定启动及清理容器使用的引擎，不跟随 docker context use 的运行时切换。
    docker_context: str = Field(
        default="default", min_length=1, max_length=128, pattern=r"^\S+$"
    )
    attachment_allowed_hosts: str = ""
    attachment_max_bytes: int = 5_000_000
    # 解析容器镜像
    attachment_sandbox_image: str = "insight-link-attachment-parser:latest"
    # 解析时间
    attachment_timeout_seconds: int = 30
    # 跑图、代码、文档的镜像
    analysis_sandbox_image: str = "insight-link-analysis:latest"
    # 容器超时删除
    analysis_timeout_seconds: int = Field(default=30, ge=5, le=90)


@lru_cache
def get_settings() -> Settings:
    """每个进程加载一次环境配置；修改本地 .env 后需重启服务才会生效。"""
    return Settings()
