"""仅在隔离容器内提取附件；保留定位及解析边界，供主进程分页回读。"""

import io
import json
import sys


MAX_PAGES = 200
MAX_BLOCKS = 2000
MAX_CHARACTERS = 240_000
CHUNK_CHARACTERS = 1500


def append_text(result: list[dict], text: str, locator: str, remaining: int, **metadata) -> int:
    """按固定长度切片，避免长页或表格被静默丢弃；返回剩余字符预算。"""
    text = text.strip()[:remaining]
    for start in range(0, len(text), CHUNK_CHARACTERS):
        result.append({"locator": locator, "text": text[start:start + CHUNK_CHARACTERS], **metadata})
    return remaining - len(text)


def extract_pdf(data: bytes) -> dict:
    """读取有文字层的 PDF；超过页数或字符预算时明确返回截断原因。"""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data), strict=True)
    result, remaining, parsed_pages = [], MAX_CHARACTERS, 0
    total_pages = len(reader.pages)
    text_truncated = False
    for index in range(min(total_pages, MAX_PAGES)):
        text = (reader.pages[index].extract_text() or "").strip()
        text_truncated = len(text) > remaining
        remaining = append_text(result, text, f"第 {index + 1} 页", remaining, page=index + 1)
        parsed_pages = index + 1
        if remaining == 0:
            break
    truncated = parsed_pages < total_pages or text_truncated
    return {
        "chunks": result, "document_pages": total_pages, "parsed_pages": parsed_pages,
        "parsed_truncated": truncated,
        "truncation_reason": "达到 24 万字符解析上限" if remaining == 0 and truncated else (
            "达到 200 页解析上限" if truncated else ""
        ),
    }


def extract_docx(data: bytes) -> dict:
    """依文档顺序读取段落与表格；Word 页码依赖排版，使用段落/表格定位。"""
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    document = Document(io.BytesIO(data))
    result, remaining = [], MAX_CHARACTERS
    paragraphs = tables = processed = 0
    text_truncated = False
    blocks = list(document.iter_inner_content())
    for block in blocks[:MAX_BLOCKS]:
        processed += 1
        if isinstance(block, Paragraph):
            paragraphs += 1
            text, locator = block.text, f"第 {paragraphs} 段"
        elif isinstance(block, Table):
            tables += 1
            text = "\n".join(" | ".join(cell.text for cell in row.cells) for row in block.rows)
            locator = f"第 {tables} 个表格"
        else:
            continue
        text_truncated = len(text.strip()) > remaining
        remaining = append_text(result, text, locator, remaining)
        if remaining == 0:
            break
    truncated = processed < len(blocks) or text_truncated
    return {
        "chunks": result, "document_pages": None, "parsed_pages": None,
        "document_blocks": len(blocks), "parsed_blocks": processed,
        "parsed_truncated": truncated,
        "truncation_reason": "达到 24 万字符解析上限" if remaining == 0 and truncated else (
            "达到 2000 个正文块解析上限" if truncated else ""
        ),
    }


if __name__ == "__main__":
    raw = sys.stdin.buffer.read(5_000_001)
    if len(raw) > 5_000_000:
        raise SystemExit(2)
    file_type = sys.argv[1]
    if file_type == "pdf":
        chunks = extract_pdf(raw)
    elif file_type == "docx":
        chunks = extract_docx(raw)
    else:
        raise SystemExit(2)
    sys.stdout.buffer.write(json.dumps(chunks, ensure_ascii=False).encode("utf-8"))
