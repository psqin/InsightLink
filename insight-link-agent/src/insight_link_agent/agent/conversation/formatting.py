"""导师答复展示清理；正则只用于格式，不用于判断用户意图。"""

import re


def clean_teacher_answer(answer: str) -> str:
    """清理模型答复中的内部材料编号、字段名等非导师界面信息。"""
    lines = answer.splitlines()
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        columns = [cell.strip() for cell in line.strip().strip("|").split("|")]
        id_columns = [
            position
            for position, cell in enumerate(columns)
            if re.fullmatch(r"(?:材料\s*)?(?:ID|编号)", cell, flags=re.IGNORECASE)
        ]
        if not id_columns:
            continue
        column = id_columns[0]
        for row_index in range(index, len(lines)):
            row = lines[row_index]
            if not row.lstrip().startswith("|"):
                break
            cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
            if len(cells) != len(columns):
                break
            del cells[column]
            lines[row_index] = "| " + " | ".join(cells) + " |"
        break
    answer = "\n".join(lines)
    answer = re.sub(
        r"(?:尚未评分|未评分)[（(]\s*evaluated\s*=\s*0[^（）()\n]*[）)]",
        "尚未批阅",
        answer,
        flags=re.IGNORECASE,
    )
    answer = re.sub(
        r"[（(][^（）()\n]{0,100}(?:evaluated|score\s*(?:=|为空))[^（）()\n]*[）)]",
        "",
        answer,
        flags=re.IGNORECASE,
    )
    answer = re.sub(r"\bevaluated\s*=\s*0\b", "未批阅", answer, flags=re.IGNORECASE)
    answer = re.sub(r"\bevaluated\s*=\s*1\b", "已批阅", answer, flags=re.IGNORECASE)
    answer = re.sub(
        r"\bscore\s*(?:=\s*(?:null|none)|为空)", "暂无分数", answer, flags=re.IGNORECASE
    )
    # 分页控制字段仅给模型循环使用，导师看到的是自然语言的查询范围。
    for pattern, text in (
        (r"\bhas_more\s*[=:：]\s*false\b", "已到最后一页"),
        (r"\bhas_more\s*[=:：]\s*true\b", "仍有后续页"),
        (r"\bnext_page\s*(?:[=:：]\s*(?:null|none)|为空)", "没有后续页"),
        (r"\bcomplete\s*[=:：]\s*true\b", "查询范围已完整读取"),
        (r"\bcomplete\s*[=:：]\s*false\b", "查询范围尚未完整读取"),
    ):
        answer = re.sub(pattern, text, answer, flags=re.IGNORECASE)
    answer = re.sub(r"材料\s*#\s*\d+\s*(?=《)", "", answer)
    answer = re.sub(
        r"材料\s*(?:ID|编号)\s*[:：]\s*\d+", "", answer, flags=re.IGNORECASE
    )
    answer = re.sub(r"（\s*材料\s*#\s*\d+\s*[，,]\s*", "（", answer)
    answer = re.sub(r"材料\s*#\s*\d+", "材料", answer)
    answer = re.sub(r"(?<!\w)#\s*\d+", "", answer)
    answer = re.sub(r"材料\s*ID", "具体材料", answer, flags=re.IGNORECASE)
    answer = answer.replace("（，", "（").replace("(，", "(")
    answer = answer.replace("正式批阅状态字段", "批阅状态")
    answer = answer.replace("本次检索结果被截断", "这里只列出了部分材料")
    answer = re.sub(r"材料\s*（\s*）", "材料", answer)
    return answer.strip()
