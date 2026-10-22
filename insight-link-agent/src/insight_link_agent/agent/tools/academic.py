"""学业只读工具：授权校验和输出裁剪委托给当前请求的读取回调。"""

import json
from collections.abc import Awaitable, Callable
from typing import Annotated

from langchain_core.tools import BaseTool, tool
from pydantic import Field

from insight_link_agent.agent.conversation.models import ReadTools


def build_academic_tools(
    *, reader: ReadTools, validated_read: Callable[..., Awaitable[dict]]
) -> list[BaseTool]:
    """创建学业读取工具；reader 和校验回调仅保留在本轮闭包中。

    工具名称、参数和 JSON 输出与主图保持一致；认证仍由 reader 的调用上下文处理。
    调用方继续统一包装审计与进度，工厂不重复登记结果。
    """

    @tool
    async def search_student_materials(
        student_name: str, title_keyword: str = ""
    ) -> str:
        """按学生姓名和可选标题关键词，分页查询当前导师有权查看的材料。"""
        result = await validated_read(
            reader,
            "search_student_materials",
            {
                "student_name": student_name,
                "title_keyword": title_keyword,
            },
        )
        return json.dumps(result, ensure_ascii=False)

    @tool
    async def get_material(material_id: int) -> str:
        """读取当前导师有权查看的材料正文、批阅状态和正式分数。"""
        result = await validated_read(
            reader, "get_material", {"material_id": material_id}
        )
        return json.dumps(result, ensure_ascii=False)

    @tool
    async def get_attachment_text(
        material_id: int, offset: int = 0, limit: int = 40, page: int | None = None
    ) -> str:
        """分段读取授权 PDF/DOCX 附件；有后续片段时按 next_offset 继续，可指定 PDF 页码。

        默认最多40片且总正文不超过12000字符；limit可调小，DOCX无稳定页码。扫描件不含OCR；以返回的解析范围判断是否读完。
        """
        result = await validated_read(
            reader,
            "get_attachment_text",
            {
                "material_id": material_id,
                "offset": offset,
                "limit": limit,
                "page": page,
            },
        )
        return json.dumps(result, ensure_ascii=False)

    @tool
    async def get_student_history(
        student_user_id: int, current_material_id: int
    ) -> str:
        """读取同一学生的近期材料和既往点评，用于比较学习进展。"""
        result = await validated_read(
            reader,
            "get_student_history",
            {
                "student_user_id": student_user_id,
                "current_material_id": current_material_id,
            },
        )
        return json.dumps(result, ensure_ascii=False)

    @tool
    async def search_my_students(student_name: str = "", student_no: str = "") -> str:
        """分页查找当前导师的学生，查询姓名、学号、班级、专业、学院。"""
        result = await validated_read(
            reader,
            "search_my_students",
            {
                "student_name": student_name,
                "student_no": student_no,
            },
        )
        return json.dumps(result, ensure_ascii=False)

    @tool
    async def get_student_profile(student_user_id: int) -> str:
        """读取已绑定学生的学校、学院、专业、班级和入学年份。"""
        result = await validated_read(
            reader,
            "get_student_profile",
            {
                "student_user_id": student_user_id,
            },
        )
        return json.dumps(result, ensure_ascii=False)

    @tool
    async def get_message_history(student_user_id: int, page: int = 1) -> str:
        """分页读取导师和已绑定学生的既有留言；不发送或修改留言。"""
        result = await validated_read(
            reader,
            "get_message_history",
            {
                "student_user_id": student_user_id,
                "page": page,
            },
        )
        return json.dumps(result, ensure_ascii=False)

    @tool
    async def list_my_students(
        page: Annotated[int, Field(strict=True, ge=1, le=10_000)] = 1,
        page_size: Annotated[int, Field(strict=True, ge=1, le=100)] = 50,
        class_name: str = "",
        major: str = "",
        college: str = "",
        student_name: str = "",
        student_no: str = "",
    ) -> str:
        """分页读取当前导师的学生花名册，筛选全空即查询所指导的全体学生。

        支持班级、专业、姓名、学号筛选；学院筛选取决于后端支持，拒绝时说明限制。
        page为1–10000，page_size为1–100。records是完整当前页，不是全体结果。
        需全部学生时按has_more和next_page继续，不要向导师索要已有系统中的姓名。
        只有读到最后一页且complete=true才能声称已查全；complete=false时必须说明范围。
        """
        result = await validated_read(
            reader,
            "list_my_students",
            {
                "page": page,
                "page_size": page_size,
                "class_name": class_name,
                "major": major,
                "college": college,
                "student_name": student_name,
                "student_no": student_no,
            },
        )
        return json.dumps(result, ensure_ascii=False)

    @tool
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
    ) -> str:
        """分页读取导师可见的全部、某班或某学生材料与正式分数，筛选均可为空。

        evaluated为0（未批阅）或1（已批阅），material_type为1/2/3；正式0分有效。
        page为1–10000，page_size为1–100。records返回当前整页，不能当作全部。
        统计全班平均分或未交名单须按next_page遍历has_more页，并确认complete=true。
        未交名单还须用list_my_students取全体花名册作比较；缺数据时说明实际范围。
        """
        result = await validated_read(
            reader,
            "list_student_materials",
            {
                "page": page,
                "page_size": page_size,
                "student_name": student_name,
                "student_no": student_no,
                "student_user_id": student_user_id,
                "class_name": class_name,
                "title_keyword": title_keyword,
                "evaluated": evaluated,
                "material_type": material_type,
            },
        )
        return json.dumps(result, ensure_ascii=False)

    # 前七项保持历史顺序，新增的整页读取入口追加；调用方按名称决定专家权限。
    return [
        search_student_materials,
        get_material,
        get_attachment_text,
        get_student_history,
        search_my_students,
        get_student_profile,
        get_message_history,
        list_my_students,
        list_student_materials,
    ]
