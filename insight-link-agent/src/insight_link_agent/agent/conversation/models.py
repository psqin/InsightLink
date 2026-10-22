"""聊天业务快照与可替换读取协议，不包含任务识别规则。"""

from dataclasses import dataclass
from typing import Protocol

from insight_link_agent.app.schemas import Material


@dataclass(frozen=True)
class Conversation:
    """已验证导师可访问的HOT会话快照；version用于追加消息的乐观锁。"""

    id: str
    user_id: int
    material_id: int | None
    version: int
    created_at: str
    updated_at: str
    title: str | None = None


class ReadTools(Protocol):
    """只读业务适配契约；不包含身份参数和正式提交，凭据来自请求上下文。"""

    async def search_materials(
        self, student_name: str, title_keyword: str = ""
    ) -> dict: ...
    async def material(self, material_id: int) -> Material: ...
    async def student_name(self, student_user_id: int) -> str: ...
    async def attachment(
        self,
        material_id: int,
        offset: int = 0,
        limit: int = 8,
        page: int | None = None,
    ) -> dict: ...
    async def history(self, student_user_id: int, current_material_id: int) -> list: ...
    async def student_profile(self, student_user_id: int) -> dict: ...
    async def search_my_students(
        self, student_name: str = "", student_no: str = ""
    ) -> dict: ...
    async def student_page(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        class_name: str = "",
        major: str = "",
        college: str = "",
        student_name: str = "",
        student_no: str = "",
    ) -> dict: ...
    async def material_page(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        student_name: str = "",
        student_no: str = "",
        student_user_id: int | None = None,
        class_name: str = "",
        title_keyword: str = "",
        evaluated: int | None = None,
        material_type: int | None = None,
    ) -> dict: ...
    async def message_history(self, student_user_id: int, page: int = 1) -> dict: ...
