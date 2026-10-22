"""导师授权范围内的元数据分页：先完整筛选，再对匹配结果分页。

Java 的列表接口按当前请求 token 限定导师关系。这里始终使用该列表，
不调用管理员接口，也不通过逐个猜测学生编号扩大范围。班级名称、专业
名称和材料标题并非 Java 的原生查询参数，因此必须扫描授权结果后筛选；
达到硬上限、分页重复或数据变动时，明确返回不完整，不能用于全体统计。
"""

import math
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

MAX_SOURCE_PAGES = 100
SOURCE_PAGE_SIZE = 50
Request = Callable[..., Awaitable[dict]]


class AcademicPageInputError(ValueError):
    """模型或调用方提供的筛选、分页参数不符合业务范围。"""


@dataclass
class ScanResult:
    """一次有界扫描的证据；complete 不等同于当前返回页包含全部记录。"""

    rows: list[dict]
    source_total: int | None
    scanned_pages: int
    complete: bool
    limitation_reason: str = ""


def positive_int(value: object) -> int | None:
    """仅接受正整数标识，避免 True 或浮点值被当作学生编号。"""
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.isascii() and value.isdecimal():
        parsed = int(value)
        return parsed if parsed > 0 else None
    return None


def validate_page(page: int, page_size: int) -> None:
    """逻辑页与底层扫描分别限流，拒绝 bool、负数及超大响应。"""
    if type(page) is not int or not 1 <= page <= 10000:
        raise AcademicPageInputError("页码必须为 1–10000 的整数")
    if type(page_size) is not int or not 1 <= page_size <= 100:
        raise AcademicPageInputError("每页数量必须为 1–100 的整数")


def validate_text(value: str, label: str, maximum: int = 30) -> str:
    """接受空条件以查询全体，非空条件采用精确匹配而非模糊扩大范围。"""
    if not isinstance(value, str):
        raise AcademicPageInputError(f"{label}必须为文本")
    value = value.strip()
    if len(value) > maximum or any(ord(char) < 32 for char in value):
        raise AcademicPageInputError(f"{label}无效或过长")
    return value


def validate_choice(value: int | None, choices: tuple[int, ...], label: str) -> None:
    """None 表示不限；0 是合法未评状态，不按真假值丢弃。"""
    if value is not None and (type(value) is not int or value not in choices):
        raise AcademicPageInputError(f"{label}不在允许范围内")


def _total(value: object) -> int | None:
    if type(value) is int and value >= 0:
        return value
    if isinstance(value, str) and value.isascii() and value.isdecimal():
        return int(value)
    return None


async def scan_authorized_pages(
    request: Request,
    path: str,
    token: str,
    *,
    params: Mapping,
    id_field: str,
) -> ScanResult:
    """遍历 Java 原生页并校验总量与去重，异常页绝不误报完整。

    不缓存 token 或元数据；每次调用反映当前授权范围。Java 不提供快照
    游标，故总数变化和跨页重复只能作为不完整信号，不伪装一致性快照。
    """
    rows: list[dict] = []
    identities: set[int] = set()
    source_total: int | None = None
    for page in range(1, MAX_SOURCE_PAGES + 1):
        data = await request(
            "GET",
            path,
            token,
            params={**params, "page": page, "pageSize": SOURCE_PAGE_SIZE},
        )
        current_total = _total(data.get("total"))
        if current_total is None:
            return ScanResult(rows, source_total, page, False, "后端分页总量无效")
        if source_total is None:
            source_total = current_total
        elif current_total != source_total:
            return ScanResult(
                rows, source_total, page, False, "查询期间记录总量发生变化，请重新查询"
            )
        native_rows = data.get("records")
        if not isinstance(native_rows, list) or len(native_rows) > SOURCE_PAGE_SIZE:
            return ScanResult(
                rows, source_total, page, False, "后端分页记录格式或页大小异常"
            )
        invalid = False
        repeated = False
        for row in native_rows:
            identity = (
                positive_int(row.get(id_field)) if isinstance(row, dict) else None
            )
            if identity is None:
                invalid = True
                continue
            if identity in identities:
                repeated = True
                continue
            identities.add(identity)
            rows.append(row)
        if invalid or repeated:
            reason = (
                "后端分页含重复记录，查询可能发生变动"
                if repeated
                else "后端分页含缺少有效标识的记录"
            )
            return ScanResult(rows, source_total, page, False, reason)
        if len(rows) > source_total:
            return ScanResult(
                rows, source_total, page, False, "后端分页记录数超过报告总量"
            )
        if len(rows) == source_total:
            return ScanResult(rows, source_total, page, True)
        if len(native_rows) < SOURCE_PAGE_SIZE:
            return ScanResult(
                rows, source_total, page, False, "后端提前结束分页，尚未取得报告总量"
            )
    return ScanResult(
        rows,
        source_total,
        MAX_SOURCE_PAGES,
        False,
        "达到授权分页扫描上限，结果仅覆盖已读取部分",
    )


def _text(row: dict, *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def normalize_student(row: dict) -> dict:
    """使用实际 StudentsPageVO 的 major/clazz，并兼容旧字段别名。"""
    return {
        "user_id": positive_int(row.get("userId")),
        "name": _text(row, "realName"),
        "student_no": _text(row, "studentNo"),
        "class_name": _text(row, "clazz", "className"),
        "major": _text(row, "major", "majorName"),
        "college": _text(row, "collegeName"),
        "entry_year": row.get("entryYear")
        if type(row.get("entryYear")) is int
        else None,
    }


def normalize_material(row: dict, student: dict | None = None) -> dict:
    """保留 0 分；未评价或无效分数统一为 None，不参与平均分计算。"""
    evaluated = row.get("evaluated")
    evaluated = (
        int(evaluated) if type(evaluated) is int and evaluated in (0, 1) else None
    )
    raw_score = row.get("score")
    score: int | float | None = None
    if evaluated == 1 and not isinstance(raw_score, bool) and raw_score is not None:
        try:
            parsed = float(raw_score)
            if math.isfinite(parsed) and 0 <= parsed <= 100:
                score = int(parsed) if parsed.is_integer() else parsed
        except (ValueError, TypeError, OverflowError):
            pass
    return {
        "id": positive_int(row.get("id")),
        "student_user_id": positive_int(row.get("studentUserId")),
        "student_name": _text(row, "studentRealName"),
        "student_no": _text(row, "studentNo"),
        "class_name": (student or {}).get("class_name") or "",
        "title": _text(row, "title"),
        "material_type": row.get("materialType")
        if type(row.get("materialType")) is int
        else None,
        "submit_time": _text(row, "submitTime") or None,
        "evaluated": evaluated,
        "score": score,
        "evaluation_time": _text(row, "evaluationTime") or None,
        "review_status": (
            "尚未批阅"
            if evaluated == 0
            else "已批阅，已有正式分数"
            if evaluated == 1 and score is not None
            else "已批阅，尚未记录有效分数"
            if evaluated == 1
            else "批阅状态未知"
        ),
    }


def result_page(
    records: list[dict],
    scan: ScanResult,
    *,
    page: int,
    page_size: int,
    filters: dict,
    extra: dict | None = None,
) -> dict:
    """输出完整的一页；精确总量仅在授权源范围读完后给出。

    has_more 只说明还有已读取的匹配记录可翻页。complete=False 时，即使
    has_more=False 也不能推断全体已读完，必须向用户说明 limitation_reason。
    """
    start = (page - 1) * page_size
    end = start + page_size
    has_more = end < len(records)
    return {
        "records": records[start:end],
        "total": len(records) if scan.complete else None,
        "observed_total": len(records),
        "source_total": scan.source_total,
        "page": page,
        "page_size": page_size,
        "has_more": has_more,
        "next_page": page + 1 if has_more else None,
        "complete": scan.complete,
        "scanned_pages": scan.scanned_pages,
        "scope": "仅当前登录导师已绑定且后端授权可见的学生及材料，不代表全校或其他导师",
        "filters": filters,
        "filter_match": "姓名、学号、班级、专业精确匹配；材料标题包含匹配",
        "limitation_reason": scan.limitation_reason or None,
        "pagination_notice": "complete 表示底层授权范围已读完；返回 records 仍需按 next_page 翻页，才能取得全部匹配记录。",
        **(extra or {}),
    }
