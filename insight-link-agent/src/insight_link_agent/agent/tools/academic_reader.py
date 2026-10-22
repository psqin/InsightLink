"""授权读取适配器：严格参数校验与模型可见字段裁剪。"""

from insight_link_agent.agent.conversation.models import ReadTools
from insight_link_agent.app.config import Settings
from insight_link_agent.app.schemas import Material
from insight_link_agent.integrations.java_client import JavaAPIError
from insight_link_agent.integrations.processes import ResourceCleanupError


class ValidatedReadTools:
    """校验模型读取参数并将授权 MCP 结果裁剪到可控大小。"""

    def __init__(self, settings: Settings):
        self._settings = settings

    @staticmethod
    def _material_data(material: Material) -> dict:
        return {
            "id": material.id,
            "student_user_id": material.student_user_id,
            "title": material.title,
            "material_type": material.material_type,
            "submit_time": material.submit_time,
            "evaluated": material.evaluated,
            "score": material.score,
            "evaluation_time": material.evaluation_time,
            "evaluation_content": (material.evaluation_content or "")[:2000],
            "content": material.content[:6000],
            "attachment_present": bool(material.file_url),
        }

    @staticmethod
    def _positive_id(value: object) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError("材料或学生 ID 必须是正整数")
        return value

    @staticmethod
    def _page_parameters(args: dict) -> dict:
        """逻辑分页与后端扫描预算分开，避免小页长在第100页被提前截断。"""
        page, page_size = args.get("page", 1), args.get("page_size", 50)
        if (
            isinstance(page, bool)
            or not isinstance(page, int)
            or not 1 <= page <= 10_000
        ):
            raise ValueError("页码必须是1至10000的整数")
        if (
            isinstance(page_size, bool)
            or not isinstance(page_size, int)
            or not 1 <= page_size <= 100
        ):
            raise ValueError("每页数量必须是1至100的整数")
        return {"page": page, "page_size": page_size}

    @staticmethod
    def _page_filter(args: dict, key: str, maximum: int = 30) -> str:
        """允许空筛选查全体，但拒绝非字符串与超长筛选，避免模型悄悄改写查询。"""
        value = args.get(key, "")
        if not isinstance(value, str) or len(value.strip()) > maximum:
            raise ValueError("姓名、学号或范围筛选无效")
        return value.strip()

    async def _read_tool(
        self,
        reader: ReadTools,
        name: str,
        args: dict,
    ) -> dict:
        """校验模型传入的业务工具参数，并裁剪授权查询结果。"""
        try:
            if name in {"list_my_students", "list_student_materials"}:
                parameters = self._page_parameters(args)
                parameters.update(
                    {
                        "student_name": self._page_filter(args, "student_name"),
                        "student_no": self._page_filter(args, "student_no"),
                        "class_name": self._page_filter(args, "class_name", 100),
                    }
                )
                if name == "list_my_students":
                    parameters.update(
                        {
                            "major": self._page_filter(args, "major", 100),
                            "college": self._page_filter(args, "college", 100),
                        }
                    )
                    value = await reader.student_page(**parameters)
                else:
                    student_id = args.get("student_user_id")
                    if student_id is not None:
                        student_id = self._positive_id(student_id)
                    evaluated, material_type = (
                        args.get("evaluated"),
                        args.get("material_type"),
                    )
                    if evaluated is not None and (
                        isinstance(evaluated, bool)
                        or not isinstance(evaluated, int)
                        or evaluated not in (0, 1)
                    ):
                        raise ValueError("批阅状态只能是0（未批阅）或1（已批阅）")
                    if material_type is not None and (
                        isinstance(material_type, bool)
                        or not isinstance(material_type, int)
                        or material_type not in (1, 2, 3)
                    ):
                        raise ValueError("材料类型只能是1、2或3")
                    parameters.update(
                        {
                            "student_user_id": student_id,
                            "title_keyword": self._page_filter(args, "title_keyword"),
                            "evaluated": evaluated,
                            "material_type": material_type,
                        }
                    )
                    value = await reader.material_page(**parameters)
                # Java 已按请求页长生成有限 records。保留整页和 complete/has_more/
                # next_page 等范围信息，不再截前10/20条导致漏读或错误全体统计。
                return {"ok": True, "value": value}
            if name == "search_student_materials":
                student_name = str(args.get("student_name") or "").strip()
                title_keyword = str(args.get("title_keyword") or "").strip()
                if not 2 <= len(student_name) <= 30 or len(title_keyword) > 30:
                    raise ValueError("学生姓名或材料关键词无效")
                return {
                    "ok": True,
                    "value": await reader.search_materials(student_name, title_keyword),
                }
            if name == "get_material":
                material_id = self._positive_id(args.get("material_id"))
                return {
                    "ok": True,
                    "value": self._material_data(await reader.material(material_id)),
                }
            if name == "get_attachment_text":
                material_id = self._positive_id(args.get("material_id"))
                offset, limit, page = (
                    args.get("offset", 0),
                    args.get("limit", 40),
                    args.get("page"),
                )
                if (
                    isinstance(offset, bool)
                    or not isinstance(offset, int)
                    or not 0 <= offset <= 10_000
                    or isinstance(limit, bool)
                    or not isinstance(limit, int)
                    or not 1 <= limit <= 40
                    or page is not None
                    and (
                        isinstance(page, bool) or not isinstance(page, int) or page < 1
                    )
                ):
                    raise ValueError("附件片段偏移、数量或页码无效")
                extracted = await reader.attachment(
                    material_id, offset=offset, limit=limit, page=page
                )
                metadata_keys = (
                    "file_type",
                    "offset",
                    "limit",
                    "page",
                    "total_chunks",
                    "returned_chunks",
                    "next_offset",
                    "has_more",
                    "document_pages",
                    "parsed_pages",
                    "document_blocks",
                    "parsed_blocks",
                    "parsed_truncated",
                    "truncation_reason",
                    "parser_scope_known",
                    "read_scope",
                    "notice",
                    "cache_hit",
                    "cache_ttl_seconds",
                )
                return {
                    "ok": True,
                    "value": {
                        "material_id": material_id,
                        **{
                            key: extracted[key]
                            for key in metadata_keys
                            if key in extracted
                        },
                        "chunks": [
                            {
                                "locator": chunk.get("locator"),
                                "text": str(chunk.get("text") or "")[:1500],
                                **{
                                    key: chunk[key]
                                    for key in ("page", "chunk_index")
                                    if key in chunk
                                },
                            }
                            for chunk in (extracted.get("chunks") or [])[:limit]
                        ],
                    },
                }
            if name == "get_student_history":
                student_id = self._positive_id(args.get("student_user_id"))
                material_id = self._positive_id(args.get("current_material_id"))
                sources = await reader.history(student_id, material_id)
                return {
                    "ok": True,
                    "value": [
                        {
                            "id": item.id,
                            "kind": item.kind,
                            "title": item.title,
                            "text": item.text[:1200],
                        }
                        for item in sources[:6]
                    ],
                }
            if name == "search_my_students":
                student_name = str(args.get("student_name") or "").strip()
                student_no = str(args.get("student_no") or "").strip()
                if (
                    not (student_name or student_no)
                    or len(student_name) > 30
                    or len(student_no) > 30
                ):
                    raise ValueError("请提供有效的学生姓名或学号")
                return {
                    "ok": True,
                    "value": await reader.search_my_students(student_name, student_no),
                }
            if name == "get_student_profile":
                student_id = self._positive_id(args.get("student_user_id"))
                return {"ok": True, "value": await reader.student_profile(student_id)}
            if name == "get_message_history":
                student_id = self._positive_id(args.get("student_user_id"))
                page = self._positive_id(args.get("page", 1))
                if page > 100:
                    raise ValueError("页码超出范围")
                value = await reader.message_history(student_id, page)
                rows = value.get("records") or []
                return {
                    "ok": True,
                    "value": {
                        "total": value.get("total"),
                        "page": page,
                        "records": [
                            {
                                "sender_id": row.get("senderId"),
                                "receiver_id": row.get("receiverId"),
                                "content": str(row.get("content") or "")[:1000],
                                "send_time": row.get("sendTime")
                                or row.get("createTime"),
                            }
                            for row in rows[:20]
                        ],
                    },
                }
            raise ValueError("不支持的工具")
        except JavaAPIError as exc:
            if exc.status == 401:
                raise
            return {"ok": False, "status": exc.status, "message": str(exc)}
        except ResourceCleanupError:
            # 解析容器未被确认停止时必须通知执行管理器，不能作为普通 503 工具结果吞掉。
            raise
        except RuntimeError as exc:
            return {"ok": False, "status": 503, "message": str(exc)}
        except (TypeError, ValueError) as exc:
            return {"ok": False, "status": 422, "message": str(exc)}
