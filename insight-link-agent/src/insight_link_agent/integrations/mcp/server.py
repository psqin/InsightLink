"""导师业务MCP服务端；身份验证、工具schema与Java调用在此登记。"""

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from insight_link_agent.app.config import Settings
from insight_link_agent.integrations.attachments import (
    AttachmentError,
    AttachmentReader,
)
from insight_link_agent.integrations.java_client import JavaAPIError, JavaClient
from insight_link_agent.integrations.mcp.auth import _token
from insight_link_agent.integrations.mcp.cancellation import AttachmentRequests
from insight_link_agent.integrations.processes import ResourceCleanupError


def build_mcp(
    java: JavaClient,
    max_history_pages: int,
    attachment_reader: AttachmentReader | None = None,
    max_search_pages: int = 100,
) -> FastMCP:
    mcp = FastMCP("InsightLink Academic Business Tools")
    attachment_requests = AttachmentRequests()

    async def verified_teacher(explicit: str | None) -> tuple[str, int]:
        token = _token(explicit)
        actor = await java.identify(token)
        if actor.role_id != 2:
            raise JavaAPIError(403, "只有导师可以执行该操作")
        return token, actor.user_id

    @mcp.tool
    async def get_material(material_id: int, auth_token: str | None = None) -> dict:
        """仅在 Java 确认当前导师有权访问时读取材料。"""
        try:
            material = await java.material(_token(auth_token), material_id)
        except JavaAPIError as exc:
            return {"ok": False, "status": exc.status, "message": str(exc)}
        return {"ok": True, "value": material.model_dump()}

    @mcp.tool
    async def search_student_materials(
        student_name: str, title_keyword: str = "", auth_token: str | None = None
    ) -> dict:
        """按学生姓名检索当前导师可见材料，返回提交时间、批阅状态及正式评分；标题关键词可留空。"""
        try:
            found = await java.search_materials(
                _token(auth_token), student_name, title_keyword, max_search_pages
            )
        except JavaAPIError as exc:
            return {"ok": False, "status": exc.status, "message": str(exc)}
        return {"ok": True, "value": found}

    @mcp.tool
    async def get_student_name(
        student_user_id: int, auth_token: str | None = None
    ) -> dict:
        """在 Java 校验导师绑定关系后读取学生真实姓名。"""
        try:
            name = await java.student_name(_token(auth_token), student_user_id)
        except JavaAPIError as exc:
            return {"ok": False, "status": exc.status, "message": str(exc)}
        return {"ok": True, "value": name}

    @mcp.tool
    async def get_student_profile(
        student_user_id: int, auth_token: str | None = None
    ) -> dict:
        """查询当前导师所指导学生的班级、专业、学院等资料。"""
        try:
            value = await java.student_profile(_token(auth_token), student_user_id)
        except JavaAPIError as exc:
            return {"ok": False, "status": exc.status, "message": str(exc)}
        return {"ok": True, "value": value}

    @mcp.tool
    async def search_my_students(
        student_name: str = "", student_no: str = "", auth_token: str | None = None
    ) -> dict:
        """分页查找当前导师的学生，可用姓名或学号定位。"""
        try:
            value = await java.search_my_students(
                _token(auth_token), student_name, student_no, max_search_pages
            )
        except JavaAPIError as exc:
            return {"ok": False, "status": exc.status, "message": str(exc)}
        return {"ok": True, "value": value}

    @mcp.tool
    async def list_my_students(
        page: Annotated[int, Field(strict=True, ge=1, le=10_000)] = 1,
        page_size: Annotated[int, Field(strict=True, ge=1, le=100)] = 50,
        class_name: str = "",
        major: str = "",
        college: str = "",
        student_name: str = "",
        student_no: str = "",
        auth_token: str | None = None,
    ) -> dict:
        """分页读取当前导师的学生花名册；筛选可全空，班级和专业按名称筛选。

        records 是完整当前页。has_more 时用 next_page 继续；complete=false 表示
        数据源未遍历完整，不能给出全体精确统计。学院筛选以当前后端支持范围为准。
        """
        try:
            # 该入口允许无姓名读取全体，因此每次调用都先核验登录身份为导师。
            # token 仅在 Java 请求上下文中使用，不加入工具结果或学生记录。
            token, _teacher_id = await verified_teacher(auth_token)
            value = await java.list_students_page(
                token,
                page=page,
                page_size=page_size,
                class_name=class_name,
                major=major,
                college=college,
                student_name=student_name,
                student_no=student_no,
            )
        except JavaAPIError as exc:
            return {"ok": False, "status": exc.status, "message": str(exc)}
        return {"ok": True, "value": value}

    @mcp.tool
    async def list_student_materials(
        page: Annotated[int, Field(strict=True, ge=1, le=10_000)] = 1,
        page_size: Annotated[int, Field(strict=True, ge=1, le=100)] = 50,
        student_name: str = "",
        student_no: str = "",
        student_user_id: Annotated[int, Field(strict=True, gt=0)] | None = None,
        class_name: str = "",
        title_keyword: str = "",
        evaluated: Annotated[int, Field(strict=True, ge=0, le=1)] | None = None,
        material_type: Annotated[int, Field(strict=True, ge=1, le=3)] | None = None,
        auth_token: str | None = None,
    ) -> dict:
        """分页读取当前导师可见材料，可查全体、班级或指定学生及批阅状态。

        evaluated=0 是未批阅，1 是已批阅；零分是有效正式分数。has_more 时继续
        next_page，完整统计必须读完所有页并确认 complete=true；不隐式截取前十条。
        """
        try:
            token, _teacher_id = await verified_teacher(auth_token)
            value = await java.list_materials_page(
                token,
                page=page,
                page_size=page_size,
                student_name=student_name,
                student_no=student_no,
                student_user_id=student_user_id,
                class_name=class_name,
                title_keyword=title_keyword,
                evaluated=evaluated,
                material_type=material_type,
            )
        except JavaAPIError as exc:
            return {"ok": False, "status": exc.status, "message": str(exc)}
        return {"ok": True, "value": value}

    @mcp.tool
    async def get_student_history(
        student_user_id: int,
        current_material_id: int,
        auth_token: str | None = None,
    ) -> dict:
        """读取已绑定学生近期的材料和评价记录。"""
        try:
            sources = await java.history(
                _token(auth_token),
                student_user_id,
                current_material_id,
                max_history_pages,
            )
        except JavaAPIError as exc:
            return {"ok": False, "status": exc.status, "message": str(exc)}
        return {"ok": True, "value": [source.model_dump() for source in sources]}

    @mcp.tool
    async def get_attachment_text(
        material_id: int,
        offset: int = 0,
        limit: int = 40,
        page: int | None = None,
        auth_token: str | None = None,
        request_id: str | None = None,
    ) -> dict:
        """每次授权后分页读取 PDF/DOCX；offset 从零计数，PDF 可指定 page。"""

        async def read() -> dict:
            return await read_attachment(material_id, offset, limit, page, auth_token)

        if request_id is None:
            return await read()
        # stdio 单向取消通知没有确认响应；关联号让客户端另行等待此任务的清理。
        # 先注册任务再执行 Java 授权，覆盖下载/解析之前被取消的窗口。
        try:
            return await attachment_requests.run(_token(auth_token), request_id, read())
        except ValueError:
            return {"ok": False, "status": 422, "message": "附件读取请求标识无效"}

    async def read_attachment(
        material_id: int,
        offset: int,
        limit: int,
        page: int | None,
        auth_token: str | None,
    ) -> dict:
        """共享原有鉴权和分页路径，命中解析缓存也必须再次校验材料归属。"""
        try:
            if (
                isinstance(offset, bool)
                or not isinstance(offset, int)
                or not 0 <= offset <= 10_000
                or isinstance(limit, bool)
                or not isinstance(limit, int)
                or not 1 <= limit <= 40
                or page is not None
                and (isinstance(page, bool) or not isinstance(page, int) or page < 1)
            ):
                raise AttachmentError(422, "附件片段偏移、数量或页码无效")
            # 即使命中正文缓存也重新询问 Java，不能借缓存绕过导师材料归属校验。
            material = await java.material(_token(auth_token), material_id)
            if not material.file_url:
                raise AttachmentError(422, "材料没有附件")
            if attachment_reader is None:
                raise AttachmentError(503, "附件解析尚未配置")
            extracted = await attachment_reader.extract(
                material.file_url,
                offset=offset,
                limit=limit,
                page=page,
            )
        except (JavaAPIError, AttachmentError) as exc:
            return {"ok": False, "status": exc.status, "message": str(exc)}
        return {"ok": True, "value": extracted}

    @mcp.tool
    async def cancel_attachment_read(
        request_id: str, auth_token: str | None = None
    ) -> dict:
        """内部取消确认：仅同一请求凭据可停止附件读取，不读取或修改业务记录。"""
        try:
            return await attachment_requests.cancel(_token(auth_token), request_id)
        except (ValueError, ResourceCleanupError):
            return {"ok": False, "status": 503, "message": "未能确认附件任务已停止"}

    @mcp.tool
    async def get_message_history(
        student_user_id: int, page: int = 1, auth_token: str | None = None
    ) -> dict:
        """分页查看当前导师与已绑定学生的留言记录。"""
        try:
            if not 1 <= page <= max_search_pages:
                raise JavaAPIError(422, "页码无效")
            value = await java.message_history(
                _token(auth_token), student_user_id, page
            )
        except JavaAPIError as exc:
            return {"ok": False, "status": exc.status, "message": str(exc)}
        return {"ok": True, "value": value}

    @mcp.tool
    async def create_evaluation(
        material_id: int, score: float, content: str, auth_token: str | None = None
    ) -> dict:
        """确认后为当前导师的学生材料新增正式能力评价。"""
        try:
            if (
                not isinstance(material_id, int)
                or material_id <= 0
                or isinstance(score, bool)
                or not 0 <= score <= 100
                or not content.strip()
                or len(content) > 1000
            ):
                raise JavaAPIError(422, "评价目标、分数或评语无效")
            token, _teacher_id = await verified_teacher(auth_token)
            material = await java.material(token, material_id)
            if material.evaluated:
                raise JavaAPIError(409, "材料已经评价")
            await java.create_evaluation(token, material_id, score, content)
        except JavaAPIError as exc:
            return {"ok": False, "status": exc.status, "message": str(exc)}
        return {"ok": True, "value": {"completed": True}}

    @mcp.tool
    async def update_evaluation(
        material_id: int,
        evaluation_id: int,
        score: float,
        content: str,
        auth_token: str | None = None,
    ) -> dict:
        """确认后修改当前导师本人对材料的正式能力评价。"""
        try:
            if (
                not isinstance(material_id, int)
                or material_id <= 0
                or not isinstance(evaluation_id, int)
                or evaluation_id <= 0
                or isinstance(score, bool)
                or not 0 <= score <= 100
                or not content.strip()
                or len(content) > 1000
            ):
                raise JavaAPIError(422, "评价目标、分数或评语无效")
            token, teacher_id = await verified_teacher(auth_token)
            material = await java.material(token, material_id)
            if material.evaluation_id != evaluation_id:
                raise JavaAPIError(409, "评价已变化，请重新查询")
            if material.evaluation_teacher_id != teacher_id:
                raise JavaAPIError(403, "只能修改本人评价")
            await java.update_evaluation(
                token, evaluation_id, material_id, score, content
            )
        except JavaAPIError as exc:
            return {"ok": False, "status": exc.status, "message": str(exc)}
        return {"ok": True, "value": {"completed": True}}

    @mcp.tool
    async def delete_evaluation(
        material_id: int, evaluation_id: int, auth_token: str | None = None
    ) -> dict:
        """确认后删除当前导师本人对材料的正式能力评价。"""
        try:
            if (
                not isinstance(material_id, int)
                or material_id <= 0
                or not isinstance(evaluation_id, int)
                or evaluation_id <= 0
            ):
                raise JavaAPIError(422, "评价目标无效")
            token, teacher_id = await verified_teacher(auth_token)
            material = await java.material(token, material_id)
            if material.evaluation_id != evaluation_id:
                raise JavaAPIError(409, "评价已变化，请重新查询")
            if material.evaluation_teacher_id != teacher_id:
                raise JavaAPIError(403, "只能删除本人评价")
            await java.delete_evaluation(token, evaluation_id)
        except JavaAPIError as exc:
            return {"ok": False, "status": exc.status, "message": str(exc)}
        return {"ok": True, "value": {"completed": True}}

    @mcp.tool
    async def send_student_message(
        student_user_id: int, content: str, auth_token: str | None = None
    ) -> dict:
        """确认后给当前导师已绑定的学生发送留言。"""
        try:
            if (
                not isinstance(student_user_id, int)
                or student_user_id <= 0
                or not content.strip()
                or len(content) > 1000
            ):
                raise JavaAPIError(422, "留言接收人或内容无效")
            token, _teacher_id = await verified_teacher(auth_token)
            await java.student_profile(token, student_user_id)
            await java.send_message(token, student_user_id, content)
        except JavaAPIError as exc:
            return {"ok": False, "status": exc.status, "message": str(exc)}
        return {"ok": True, "value": {"completed": True}}

    return mcp


def main() -> None:
    settings = Settings(_env_file=None)
    java = JavaClient(settings.java_base_url)
    attachment = AttachmentReader(settings)
    server = build_mcp(
        java,
        settings.max_history_pages,
        attachment,
        max_search_pages=settings.max_search_pages,
    )
    server.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
