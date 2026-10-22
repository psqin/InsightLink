"""沿用 ERP-AGENT 的 BM25 + 时间衰减思路，候选限定为当前导师的记忆。"""

import math
import re
from collections import Counter
from datetime import datetime, timezone


def tokens(text: str) -> list[str]:
    """中文同时生成单字和相邻双字，英文保留词项，供本地 BM25 匹配。"""
    result: list[str] = []
    for part in re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]+", text.lower()):
        if "\u4e00" <= part[0] <= "\u9fff":
            result.extend(part)
            result.extend(part[index : index + 2] for index in range(len(part) - 1))
        else:
            result.append(part)
    return result


def _searchable_text(document: dict) -> str:
    """新情节只索引去敏字段；旧记录和其他记忆仍使用 content。"""
    if document.get("type") == "episodic":
        fields = ("summary", "goal", "outcome", "task_type")
        parts = [
            value.strip()
            for field in fields
            if isinstance(value := document.get(field), str) and value.strip()
        ]
        tools = document.get("tools")
        if isinstance(tools, (list, tuple)):
            parts.extend(
                tool.strip() for tool in tools if isinstance(tool, str) and tool.strip()
            )
        if parts:
            return " ".join(parts)
    content = document.get("content", "")
    return content if isinstance(content, str) else ""


def rank(query: str, documents: list[dict]) -> list[tuple[dict, float]]:
    """对已按导师过滤的有限候选排序，无文本命中时不靠新鲜度强行召回。

    相关性占 60%，30 天半衰期的新鲜度占 20%，访问和置信度各占 10%。
    本函数只做纯计算，权限、过期过滤和访问计数更新由 MemoryKeeper 负责。
    """
    query_terms = set(tokens(query))
    if not query_terms or not documents:
        return []
    tokenized = [tokens(_searchable_text(doc)) for doc in documents]
    avg_length = max(1, sum(map(len, tokenized)) / len(tokenized))
    frequency = Counter(term for words in tokenized for term in set(words))
    now = datetime.now(timezone.utc)
    ranked = []
    for doc, words in zip(documents, tokenized):
        counts = Counter(words)
        bm25 = 0.0
        for term in query_terms:
            count = counts[term]
            if count:
                inverse = math.log(
                    1
                    + (len(documents) - frequency[term] + 0.5) / (frequency[term] + 0.5)
                )
                bm25 += (
                    inverse
                    * count
                    * 2.5
                    / (count + 1.5 * (0.25 + 0.75 * len(words) / avg_length))
                )
        if bm25 <= 0:
            continue
        updated = doc.get("updated_at") or now
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        age = max(0, (now - updated).total_seconds() / 86400)
        score = (
            0.6 * bm25
            + 0.2 * math.pow(0.5, age / 30)
            + 0.1 * min(1, doc.get("access_count", 0) / 10)
            + 0.1 * float(doc.get("confidence", 0.7))
        )
        ranked.append((doc, score))
    return sorted(ranked, key=lambda item: item[1], reverse=True)
