"""为点评生成收集有界附件上下文，并把未读范围作为生成和复核约束。"""

from dataclasses import dataclass, field
from functools import partial

from insight_link_agent.agent.observability.progress import observed_read
from insight_link_agent.app.schemas import Draft, Material, Source
from insight_link_agent.integrations.java_client import JavaAPIError

MAX_ATTACHMENT_CHARACTERS = 24_000
MAX_ATTACHMENT_READS = 8
READ_BATCH_SIZE = 8
SOURCE_CHARACTERS = 1500


@dataclass
class AttachmentContext:
    """只记录本轮实际提供给模型的来源及范围，不改变公开 Draft 结构。"""

    sources: list[Source] = field(default_factory=list)
    digest: str | None = None
    complete: bool = False
    scope_note: str = ""

    @classmethod
    def unavailable(cls):
        """附件暂不可用时，正文仍可评价，但不能把附件未读当作学生没有写。"""
        return cls(scope_note="附件阅读范围：本轮未取得附件正文，附件完整性未知。")

    def rules(self) -> str:
        """把服务端范围放入生成与复核提示，不能由附件文本改变此约束。"""
        if not self.scope_note:
            return ""
        return (
            "\n\n【服务端核实的附件阅读范围】\n" + self.scope_note + "\n"
            "只依据已经提供的文字证据评价。图片、扫描文字等未读取部分不能推定为没有内容。"
            "若未完整读取，必须在总结和评分依据中说明局限；不得声称看过全文，"
            "不得将未读后文中的未知内容认定为缺失、敷衍或据此扣分。"
            "可以评价已读片段的具体表现，但不能把读取预算、解析限制当成学生问题，"
            "也不能因此要求学生重新提交或重写。复核时必须拒绝违反这些范围约束的草稿。"
        )

    def disclose(self, draft: Draft) -> Draft:
        """部分阅读时保证导师预览可见范围说明，不修改正式评语或建议分数。"""
        if (
            self.scope_note
            and not self.complete
            and self.scope_note not in draft.summary
        ):
            return draft.model_copy(
                update={"summary": draft.summary + "\n\n" + self.scope_note}
            )
        return draft


async def read_attachment_context(
    reader,
    material: Material,
    *,
    character_budget: int = MAX_ATTACHMENT_CHARACTERS,
    max_reads: int = MAX_ATTACHMENT_READS,
    observe: bool = False,
) -> AttachmentContext:
    """按后端游标继续授权回读，限制正文预算、调用次数并校验同一附件快照。

    首次不传分页参数，兼容只支持旧单次读取接口的测试替身；只有结果明确
    声明存在后续片段时才继续，且不能仅凭材料编号或旧缓存跳过权限复核。
    """
    if (
        isinstance(character_budget, bool)
        or not isinstance(character_budget, int)
        or not 1 <= character_budget <= 32_000
        or isinstance(max_reads, bool)
        or not isinstance(max_reads, int)
        or not 1 <= max_reads <= 16
    ):
        raise ValueError("附件上下文预算无效")
    context, remaining, offset = AttachmentContext(), character_budget, 0
    processed_chunks = 0
    seen_indices: set[int] = set()
    page_numbers: set[int] = set()
    total_chunks, parsed_pages, document_pages = None, None, None
    parser_known, parsed_truncated = False, None
    stop_reason, has_more = "", None
    for call_number in range(max_reads):
        operation = (
            reader.attachment
            if call_number == 0
            else partial(
                reader.attachment,
                offset=offset,
                limit=READ_BATCH_SIZE,
            )
        )
        try:
            extracted = (
                await observed_read("get_attachment_text", operation, material.id)
                if observe
                else await operation(material.id)
            )
        except JavaAPIError as exc:
            # 认证/归属错误必须向上抛出；读取过一部分后遇到暂时失败则显式缩小范围。
            if call_number == 0 or exc.status not in (422, 503):
                raise
            stop_reason = "后续片段暂不可读取"
            break
        if not isinstance(extracted, dict) or not isinstance(
            extracted.get("chunks"), list
        ):
            raise ValueError("附件读取结果无效")
        digest = extracted.get("sha256")
        if call_number == 0:
            context.digest = digest if isinstance(digest, str) and digest else None
            total_chunks = extracted.get("total_chunks")
            parsed_pages, document_pages = (
                extracted.get("parsed_pages"),
                extracted.get("document_pages"),
            )
            parser_known = extracted.get("parser_scope_known") is True
            parsed_truncated = extracted.get("parsed_truncated")
        elif not context.digest or digest != context.digest:
            raise ValueError("附件在读取期间发生变化，已停止生成；请重新发起本次评价")
        elif extracted.get("total_chunks") != total_chunks:
            raise ValueError(
                "附件片段范围在读取期间变化，已停止生成；请重新发起本次评价"
            )
        reported_offset = extracted.get("offset", offset)
        if (
            isinstance(reported_offset, bool)
            or not isinstance(reported_offset, int)
            or reported_offset != offset
        ):
            raise ValueError("附件回读偏移没有按请求前进，已停止以避免重复读取")
        raw_chunks = extracted["chunks"]
        if not raw_chunks:
            raise ValueError("附件回读没有返回新的有效片段，已停止以避免重复读取")
        for chunk in raw_chunks:
            if (
                not isinstance(chunk, dict)
                or not isinstance(chunk.get("text"), str)
                or not chunk["text"].strip()
            ):
                raise ValueError("附件回读包含无效正文片段")
            index = chunk.get("chunk_index")
            if index is not None:
                if (
                    isinstance(index, bool)
                    or not isinstance(index, int)
                    or index < 0
                    or index in seen_indices
                ):
                    raise ValueError("附件回读重复了已读取片段，已停止以避免循环")
                seen_indices.add(index)
            body = chunk["text"]
            accepted = body[:remaining]
            page = chunk.get("page")
            if isinstance(page, int) and not isinstance(page, bool) and page > 0:
                page_numbers.add(page)
            for start in range(0, len(accepted), SOURCE_CHARACTERS):
                context.sources.append(
                    Source(
                        id=-(10**12 + material.id * 100 + len(context.sources) + 1),
                        kind="attachment",
                        text=accepted[start : start + SOURCE_CHARACTERS],
                        title=f"{material.title} 附件 {str(chunk.get('locator') or '正文片段')[:80]}",
                    )
                )
            remaining -= len(accepted)
            if len(accepted) < len(body):
                stop_reason = "达到本轮附件正文预算"
                break
            processed_chunks += 1
            if remaining == 0 and chunk is not raw_chunks[-1]:
                stop_reason = "达到本轮附件正文预算"
                break
        has_more = extracted.get("has_more")
        if stop_reason or remaining == 0 and has_more is not False:
            stop_reason = stop_reason or "达到本轮附件正文预算"
            break
        if has_more is not True:
            break
        next_offset = extracted.get("next_offset")
        if (
            not context.digest
            or isinstance(next_offset, bool)
            or not isinstance(next_offset, int)
            or next_offset != offset + len(raw_chunks)
            or next_offset <= offset
        ):
            raise ValueError(
                "附件回读缺少可靠快照或有效的下一片段偏移，已停止以避免循环"
            )
        offset = next_offset
    else:
        stop_reason = "达到本轮附件回读次数上限"
    context.complete = (
        parser_known
        and parsed_truncated is False
        and has_more is False
        and not stop_reason
        and isinstance(total_chunks, int)
        and not isinstance(total_chunks, bool)
        and total_chunks == processed_chunks
    )
    read_characters = character_budget - remaining
    span = (
        f"PDF 第 {min(page_numbers)}–{max(page_numbers)} 页中的已读文字，"
        if page_numbers
        else ""
    )
    context.scope_note = f"附件阅读范围：{span}已提供 {len(context.sources)} 个证据片段、{read_characters} 字符正文。"
    if isinstance(parsed_pages, int) and isinstance(document_pages, int):
        context.scope_note += f"解析器处理 {parsed_pages}/{document_pages} 页。"
    if context.complete:
        context.scope_note += (
            "已完整遍历本次解析得到的文字层；图片和扫描文字不在覆盖范围内。"
        )
    else:
        reasons = [stop_reason] if stop_reason else []
        if parsed_truncated:
            reasons.append("附件解析范围受安全限制，未覆盖全文")
        if not parser_known or parsed_truncated is None or has_more is None:
            reasons.append("解析器未报告完整性")
        context.scope_note += (
            "仅覆盖部分已读文字，不能视为完整附件。" + "；".join(reasons) + "。"
        )
    return context
