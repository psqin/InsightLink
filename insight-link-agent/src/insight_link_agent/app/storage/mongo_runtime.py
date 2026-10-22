"""统一的 MongoDB 连接、应用集合与 LangGraph 检查点。"""

from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient

from insight_link_agent.app.storage.interaction_store import interaction_indexes


class MongoRuntimeStore:
    """所有 Agent 状态共用 MongoDB；集合名按配置前缀隔离。"""

    def __init__(self, url: str, database: str, collection_prefix: str, *, client=None):
        self.client = (
            client
            if client is not None
            else MongoClient(
                url,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=10000,
            )
        )
        self.db = db = self.client[database]
        self.prefix = collection_prefix
        self.chats = db[f"{collection_prefix}_hot_chats"]
        self.memories = db[f"{collection_prefix}_long_memory"]
        self.runs = db[f"{collection_prefix}_runs"]
        self.interactions = db[f"{collection_prefix}_interactions"]
        self.artifacts = db[f"{collection_prefix}_artifacts"]
        self.leases = db[f"{collection_prefix}_execution_leases"]
        self.grading_standards = db[f"{collection_prefix}_grading_standards"]
        self.context_files = db[f"{collection_prefix}_context_files"]
        # 与评分标准一样长期保留；读取不会创建集合，首次安装个人技能才建库索引。
        self.skills = db[f"{collection_prefix}_skills"]

    def open(self) -> None:
        """启动时验证 MongoDB 并建立导师范围索引与到期删除索引。"""
        # 启动时主动验证连接，避免聊天运行一半才发现记忆无法持久化。
        self.client.admin.command("ping")
        existing = set(self.db.list_collection_names())
        legacy = [
            f"{self.prefix}_{suffix}"
            for suffix in ("pending_inputs", "pending_actions", "harness_traces")
        ]
        if any(
            name in existing and self.db[name].count_documents({}, limit=1)
            for name in legacy
        ):
            raise RuntimeError(
                "发现旧存储集合，请先备份并迁移到当前 MongoDB 存储结构后再启动"
            )
        self.chats.create_index([("user_id", 1), ("updated_at", -1)])
        self.memories.create_index([("user_id", 1), ("type", 1), ("updated_at", -1)])
        self.memories.create_index("expires_at", expireAfterSeconds=0)
        self.runs.create_index([("user_id", 1), ("updated_at", -1)])
        # 有数据的现存集合补齐索引；可选集合首次写入时再创建。
        if self.interactions.name in existing:
            interaction_indexes(self.interactions).ensure()
        self.artifacts.create_index([("user_id", 1), ("created_at", -1)])
        self.artifacts.create_index("expires_at", expireAfterSeconds=0)
        if self.leases.name in existing:
            self.leases.create_index("expires_at", expireAfterSeconds=0)
        if self.grading_standards.name in existing:
            self.grading_standards.create_index("user_id", unique=True)
        if self.context_files.name in existing:
            self.context_files.create_index(
                [("user_id", 1), ("conversation_id", 1), ("branch", 1), ("key", 1)],
                unique=True,
            )

    def checkpointer(self):
        """使用官方 MongoDBSaver；客户端仍由本对象统一关闭。"""
        return MongoDBSaver(
            self.client,
            self.db.name,
            checkpoint_collection_name=f"{self.prefix}_checkpoints",
            writes_collection_name=f"{self.prefix}_checkpoint_writes",
        )

    def close(self) -> None:
        """释放应用生命周期内共享的 MongoDB 客户端。"""
        self.client.close()
