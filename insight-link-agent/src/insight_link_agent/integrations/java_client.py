"""InsightLink Java 适配层：每次调用都使用当前请求的登录令牌。"""

from collections.abc import Mapping

import httpx

from insight_link_agent.app.schemas import Actor, Material, Source
from insight_link_agent.integrations.academic_pages import (
    AcademicPageInputError,
    ScanResult,
    normalize_material,
    normalize_student,
    positive_int,
    result_page,
    scan_authorized_pages,
    validate_choice,
    validate_page,
    validate_text,
)


class JavaAPIError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


class JavaClient:
    def __init__(
        self, base_url: str, transport: httpx.AsyncBaseTransport | None = None
    ):
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"), transport=transport, timeout=15.0
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        token: str,
        params: Mapping | None = None,
        json_body: Mapping | None = None,
    ) -> dict:
        if not token:
            raise JavaAPIError(401, "登录凭据缺失")
        try:
            response = await self._client.request(
                method,
                path,
                headers={"token": token},
                params=params,
                json=json_body,
            )
        except httpx.HTTPError as exc:
            raise JavaAPIError(502, "点评系统暂时不可用") from exc
        if response.status_code == 401:
            raise JavaAPIError(401, "登录已过期，请重新登录")
        if response.status_code >= 400:
            raise JavaAPIError(response.status_code, "点评系统请求失败")
        try:
            payload = response.json()
        except ValueError as exc:
            raise JavaAPIError(502, "点评系统返回了非 JSON 数据") from exc
        if not isinstance(payload, dict) or str(payload.get("code")) != "1":
            raise JavaAPIError(403, str(payload.get("msg") or "点评系统拒绝了请求"))
        data = payload.get("data")
        return data if isinstance(data, dict) else {}

    async def identify(self, token: str) -> Actor:
        data = await self._request("POST", "/user/info", token)
        try:
            return Actor(
                user_id=data["id"],
                role_id=data["roleId"],
                name=data.get("realName") or "",
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise JavaAPIError(502, "点评系统返回了无效用户信息") from exc

    async def material(self, token: str, material_id: int) -> Material:
        data = await self._request("GET", f"/teacher/evaluation/{material_id}", token)
        try:
            return Material(
                id=data["id"],
                student_user_id=data["studentUserId"],
                material_type=data["materialType"],
                title=data.get("title") or "",
                content=data.get("content") or "",
                file_url=data.get("fileUrl"),
                evaluated=data.get("evaluated") or 0,
                submit_time=data.get("submitTime"),
                score=data.get("score"),
                evaluation_time=data.get("evaluationTime"),
                evaluation_content=data.get("evaluationContent"),
                evaluation_id=data.get("evaluationId"),
                evaluation_teacher_id=data.get("teacherUserId"),
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise JavaAPIError(502, "点评系统返回了无效材料信息") from exc

    async def search_materials(
        self,
        token: str,
        student_name: str,
        title_keyword: str,
        max_pages: int,
    ) -> dict:
        """分页遍历当前导师的材料，仅返回筛选后的元数据，不返回正文。

        Java 按提交时间降序分页；姓名在本地再次精确匹配。最多读取
        ``max_pages`` 页，``complete`` 表示后端结果已读完；展示列表最多
        返回 10 条，``truncated`` 还会标记展示截断。最新已评分材料取遍历
        顺序中的首条；若存在相同提交时间的已评分材料，则标记时间并列。
        """
        student_name = student_name.strip()
        title_keyword = title_keyword.strip()
        if not 2 <= len(student_name) <= 30 or len(title_keyword) > 30:
            raise JavaAPIError(422, "学生姓名或材料关键词无效")
        matches: list[dict] = []
        related: list[dict] = []
        keywords = [title_keyword.casefold()]
        core_keyword = title_keyword
        for suffix in ("材料", "文档", "报告"):
            if core_keyword.endswith(suffix) and len(core_keyword) > len(suffix):
                core_keyword = core_keyword[: -len(suffix)]
                keywords.append(core_keyword.casefold())
                break
        if core_keyword.endswith("学习") and len(core_keyword) > 2:
            keywords.append(core_keyword[:-2].casefold())
        total = 0
        page_size = 20
        seen = 0
        complete = False
        latest_scored: dict | None = None
        latest_scored_tie = False
        for page in range(1, max_pages + 1):
            data = await self._request(
                "GET",
                "/teacher/evaluation/page",
                token,
                params={
                    "page": page,
                    "pageSize": page_size,
                    "realName": student_name,
                },
            )
            rows = data.get("records") or []
            if page == 1:
                total = int(data.get("total") or 0)
            seen += len(rows)
            for row in rows:
                if row.get("studentRealName") != student_name:
                    continue
                material_id = row.get("id")
                if not isinstance(material_id, int) or material_id <= 0:
                    continue
                candidate = {
                    "id": material_id,
                    "student_user_id": row.get("studentUserId"),
                    "student_name": student_name,
                    "student_no": row.get("studentNo"),
                    "title": row.get("title") or "",
                    "submit_time": row.get("submitTime"),
                    "evaluated": row.get("evaluated") or 0,
                    "score": row.get("score"),
                    "evaluation_time": row.get("evaluationTime"),
                }
                candidate["review_status"] = (
                    "尚未批阅"
                    if candidate["evaluated"] != 1
                    else "已批阅，尚未记录分数"
                    if candidate["score"] is None
                    else "已批阅，已有正式分数"
                )
                related.append(candidate)
                if (
                    latest_scored is None
                    and candidate["evaluated"] == 1
                    and candidate["score"] is not None
                ):
                    latest_scored = candidate
                elif (
                    latest_scored is not None
                    and candidate["evaluated"] == 1
                    and candidate["score"] is not None
                    and candidate["submit_time"] == latest_scored["submit_time"]
                ):
                    latest_scored_tie = True
                if not title_keyword or any(
                    keyword in candidate["title"].casefold() for keyword in keywords
                ):
                    matches.append(candidate)
            if seen >= total:
                complete = True
                break
            if len(rows) < page_size:
                break
        return {
            "matches": matches[:10],
            "related": related[:10],
            "latest_scored": latest_scored,
            "latest_scored_tie": latest_scored_tie,
            "oldest": related[-1] if complete and related else None,
            "match_count": len(matches),
            "related_count": len(related),
            "students": list(
                {
                    row["student_user_id"]: {
                        "id": row["student_user_id"],
                        "student_no": row["student_no"],
                    }
                    for row in related
                    if row["student_user_id"] is not None
                }.values()
            ),
            "complete": complete,
            "truncated": not complete or len(matches) > 10 or len(related) > 10,
            "order": "submit_time_desc",
        }

    async def list_students_page(
        self,
        token: str,
        *,
        page: int = 1,
        page_size: int = 50,
        class_name: str = "",
        major: str = "",
        college: str = "",
        student_name: str = "",
        student_no: str = "",
    ) -> dict:
        """查询当前导师的全部或指定班级学生，支持匹配结果继续翻页。

        StudentSearchDTO 不支持名称形式的班级、专业和学生姓名，因此
        先遍历当前导师授权列表再精确筛选。空姓名合法；不要求导师提供
        内部编号。学院不在实际 StudentsPageVO 中，不能假装完成该筛选。
        """
        try:
            validate_page(page, page_size)
            class_name = validate_text(class_name, "班级", 100)
            major = validate_text(major, "专业", 100)
            college = validate_text(college, "学院", 100)
            student_name = validate_text(student_name, "学生姓名")
            student_no = validate_text(student_no, "学号")
            if college:
                raise AcademicPageInputError(
                    "当前导师学生列表未提供学院字段，暂不支持按学院筛选；可按班级或专业筛选"
                )
        except AcademicPageInputError as exc:
            raise JavaAPIError(422, str(exc)) from exc
        scan = await scan_authorized_pages(
            self._request,
            "/teacher/ts/page",
            token,
            params={"studentNo": student_no} if student_no else {},
            id_field="userId",
        )
        students = [normalize_student(row) for row in scan.rows]
        matches = [
            student
            for student in students
            if (
                (not class_name or student["class_name"] == class_name)
                and (not major or student["major"] == major)
                and (not student_name or student["name"] == student_name)
                and (not student_no or student["student_no"] == student_no)
            )
        ]
        return result_page(
            matches,
            scan,
            page=page,
            page_size=page_size,
            filters={
                "class_name": class_name,
                "major": major,
                "student_name": student_name,
                "student_no": student_no,
            },
            extra={"order": "entry_year_desc_student_no_asc"},
        )

    async def list_materials_page(
        self,
        token: str,
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
    ) -> dict:
        """列出导师授权材料元数据，按学生、班级、标题及批阅状态筛选。

        使用 Java 已实现的 realName/studentNo/evaluated/materialType 缩小
        扫描后，再做精确复核；标题、学生编号由本地筛选。班级名称需要
        先扫描导师花名册，用学生 userId 关联，避免同名学生互相混淆。
        列表不读取正文、评语或附件，也不调用管理员端点。
        """
        try:
            validate_page(page, page_size)
            student_name = validate_text(student_name, "学生姓名")
            student_no = validate_text(student_no, "学号")
            class_name = validate_text(class_name, "班级", 100)
            title_keyword = validate_text(title_keyword, "材料标题关键词")
            validate_choice(evaluated, (0, 1), "批阅状态")
            validate_choice(material_type, (1, 2, 3), "材料类型")
            if student_user_id is not None and (
                type(student_user_id) is not int or student_user_id <= 0
            ):
                raise AcademicPageInputError("学生编号必须为正整数")
        except AcademicPageInputError as exc:
            raise JavaAPIError(422, str(exc)) from exc

        roster: ScanResult | None = None
        students: dict[int, dict] = {}
        if class_name:
            roster = await scan_authorized_pages(
                self._request,
                "/teacher/ts/page",
                token,
                params={},
                id_field="userId",
            )
            students = {
                student["user_id"]: student
                for student in map(normalize_student, roster.rows)
                if student["class_name"] == class_name
            }
        params = {
            **({"realName": student_name} if student_name else {}),
            **({"studentNo": student_no} if student_no else {}),
            **({"evaluated": evaluated} if evaluated is not None else {}),
            **({"materialType": material_type} if material_type is not None else {}),
        }
        scan = await scan_authorized_pages(
            self._request,
            "/teacher/evaluation/page",
            token,
            params=params,
            id_field="id",
        )
        matches: list[dict] = []
        invalid_identity = False
        for row in scan.rows:
            identity = positive_int(row.get("studentUserId"))
            if identity is None:
                invalid_identity = True
                continue
            material = normalize_material(row, students.get(identity))
            if (
                (student_name and material["student_name"] != student_name)
                or (student_no and material["student_no"] != student_no)
                or (student_user_id is not None and identity != student_user_id)
                or (class_name and identity not in students)
                or (
                    title_keyword
                    and title_keyword.casefold() not in material["title"].casefold()
                )
                or (evaluated is not None and material["evaluated"] != evaluated)
                or (
                    material_type is not None
                    and material["material_type"] != material_type
                )
            ):
                continue
            matches.append(material)
        reasons = [scan.limitation_reason] if scan.limitation_reason else []
        if roster is not None and not roster.complete:
            reasons.append("班级花名册尚未完整读取：" + roster.limitation_reason)
        if invalid_identity:
            reasons.append("部分材料缺少有效学生标识，未纳入结果")
        combined_scan = ScanResult(
            scan.rows,
            scan.source_total,
            scan.scanned_pages + (roster.scanned_pages if roster else 0),
            scan.complete
            and (roster is None or roster.complete)
            and not invalid_identity,
            "；".join(reasons),
        )
        return result_page(
            matches,
            combined_scan,
            page=page,
            page_size=page_size,
            filters={
                "student_name": student_name,
                "student_no": student_no,
                "student_user_id": student_user_id,
                "class_name": class_name,
                "title_keyword": title_keyword,
                "evaluated": evaluated,
                "material_type": material_type,
            },
            extra={
                "order": "submit_time_desc",
                "roster_scanned_pages": roster.scanned_pages if roster else 0,
                "material_scanned_pages": scan.scanned_pages,
                "score_notice": "仅 evaluated=1 且 score 非空的记录具有有效正式分数；0 分合法，未批阅不计作 0 分。",
            },
        )

    async def student_name(self, token: str, student_user_id: int) -> str:
        data = await self._request("GET", f"/teacher/ts/{student_user_id}", token)
        name = data.get("realName")
        if not isinstance(name, str) or not name.strip():
            raise JavaAPIError(502, "点评系统返回了无效学生姓名")
        return name.strip()

    async def student_profile(self, token: str, student_user_id: int) -> dict:
        """Java 在该详情接口中验证学生与当前导师的绑定关系。"""
        data = await self._request("GET", f"/teacher/ts/{student_user_id}", token)
        return {
            "user_id": data.get("userId"),
            "name": data.get("realName"),
            "student_no": data.get("studentNo"),
            "university": data.get("universityName"),
            "college": data.get("collegeName"),
            "major": data.get("majorName"),
            "class_name": data.get("className"),
            "entry_year": data.get("entryYear"),
        }

    async def search_my_students(
        self,
        token: str,
        name: str = "",
        student_no: str = "",
        max_pages: int = 100,
    ) -> dict:
        """分页遍历当前导师的学生，姓名在 Agent 侧精确筛选。"""
        name, student_no = name.strip(), student_no.strip()
        if not name and not student_no:
            raise JavaAPIError(422, "请提供学生姓名或学号")
        if len(name) > 30 or len(student_no) > 30:
            raise JavaAPIError(422, "学生查询条件过长")
        matches = []
        seen = 0
        total = 0
        complete = False
        for page in range(1, max_pages + 1):
            data = await self._request(
                "GET",
                "/teacher/ts/page",
                token,
                params={
                    "page": page,
                    "pageSize": 20,
                    **({"studentNo": student_no} if student_no else {}),
                },
            )
            rows = data.get("records") or []
            if page == 1:
                total = int(data.get("total") or 0)
            seen += len(rows)
            for row in rows:
                if name and row.get("realName") != name:
                    continue
                if student_no and row.get("studentNo") != student_no:
                    continue
                student_id = row.get("userId")
                if isinstance(student_id, int) and student_id > 0:
                    matches.append(
                        {
                            "user_id": student_id,
                            "name": row.get("realName"),
                            "student_no": row.get("studentNo"),
                            "class_name": row.get("className"),
                            "major": row.get("majorName"),
                            "college": row.get("collegeName"),
                        }
                    )
            if seen >= total:
                complete = True
                break
            if len(rows) < 20:
                break
        return {
            "matches": matches[:20],
            "match_count": len(matches),
            "complete": complete,
        }

    async def create_evaluation(
        self, token: str, material_id: int, score: float, content: str
    ) -> None:
        await self._request(
            "POST",
            "/teacher/evaluation",
            token,
            json_body={
                "materialId": material_id,
                "score": score,
                "content": content,
            },
        )

    async def update_evaluation(
        self,
        token: str,
        evaluation_id: int,
        material_id: int,
        score: float,
        content: str,
    ) -> None:
        await self._request(
            "PUT",
            "/teacher/evaluation",
            token,
            json_body={
                "id": evaluation_id,
                "materialId": material_id,
                "score": score,
                "content": content,
            },
        )

    async def delete_evaluation(self, token: str, evaluation_id: int) -> None:
        await self._request(
            "DELETE", "/teacher/evaluation", token, params={"id": evaluation_id}
        )

    async def send_message(self, token: str, receiver_id: int, content: str) -> None:
        await self._request(
            "POST",
            "/message",
            token,
            json_body={
                "receiverId": receiver_id,
                "content": content,
            },
        )

    async def message_history(
        self, token: str, student_user_id: int, page: int = 1
    ) -> dict:
        await self.student_profile(token, student_user_id)
        return await self._request(
            "GET",
            f"/message/history/{student_user_id}",
            token,
            params={"page": page, "pageSize": 20},
        )

    async def history(
        self,
        token: str,
        student_user_id: int,
        current_material_id: int,
        max_pages: int,
        limit: int = 3,
    ) -> list[Source]:
        student = await self._request("GET", f"/teacher/ts/{student_user_id}", token)
        student_no = student.get("studentNo")
        if not student_no:
            return []
        sources: list[Source] = []
        for page in range(1, max_pages + 1):
            data = await self._request(
                "GET",
                "/teacher/evaluation/page",
                token,
                params={"page": page, "pageSize": 20, "studentNo": student_no},
            )
            rows = data.get("records") or []
            for row in rows:
                if row.get("studentUserId") != student_user_id:
                    continue
                material_id = row.get("id")
                if not material_id or material_id == current_material_id:
                    continue
                detail = await self.material(token, material_id)
                if detail.student_user_id != student_user_id:
                    continue
                if detail.content:
                    sources.append(
                        Source(
                            id=detail.id,
                            kind="material",
                            text=detail.content,
                            title=detail.title,
                        )
                    )
                evaluation = await self._request(
                    "GET", f"/teacher/evaluation/{material_id}", token
                )
                if evaluation.get("evaluationContent"):
                    sources.append(
                        Source(
                            id=-material_id,
                            kind="evaluation",
                            text=evaluation["evaluationContent"],
                            title=f"对材料 {material_id} 的历史点评",
                        )
                    )
                if len(sources) >= limit * 2:
                    return sources[: limit * 2]
            if len(rows) < 20:
                break
        return sources
