"""长期记忆分层、检索与遗忘的统一配置。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryConfig:
    """集中管理记忆边界，避免各读写入口使用不同的限制。"""

    # 近期情节进入 WARM 的时间窗口与数量上限。
    warm_episode_days: int = 7
    max_warm_episodes: int = 5
    warm_brief_chars: int = 1600

    # 情节过期时间、单导师容量及同一偏好的历史版本数。
    episode_ttl_days: int = 90
    max_episodes: int = 200
    max_semantic_history: int = 3

    # COLD 检索默认返回量、单次上限与候选集大小。
    retrieval_k: int = 5
    max_retrieval_k: int = 10
    max_candidates: int = 500

    # 遗忘扫描的最短间隔，单位为秒。
    sweep_interval_seconds: int = 900


DEFAULT_MEMORY_CONFIG = MemoryConfig()
