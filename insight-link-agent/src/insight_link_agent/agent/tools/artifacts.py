"""图表、分析和文档工具：复用本轮沙箱并保存到已验证导师的产物存储。"""

import base64
import json
from typing import Literal

from langchain_core.tools import BaseTool, tool

from insight_link_agent.app.storage.artifact_store import ArtifactStore
from insight_link_agent.integrations.analysis_sandbox import AnalysisSandbox
from insight_link_agent.integrations.processes import ResourceCleanupError


def build_artifact_tools(
    *,
    sandbox: AnalysisSandbox,
    artifact_store: ArtifactStore,
    teacher_user_id: int,
    artifact_sink: list[dict],
) -> list[BaseTool]:
    """创建五个产物工具；沙箱实例由装配层显式传入，便于替换与验证。

    文件本体只交给 ArtifactStore，模型仅获得文件摘要。取消和清理状态未知继续向上
    传播，避免将仍在运行的资源误报为已停止；普通参数或执行错误保留原有 JSON 反馈。
    """

    async def run_and_save(payload: dict) -> str:
        """工具结果只传摘要与文件信息，生成文件本体不进入模型上下文。"""
        try:
            result = await sandbox.run(payload)
            saved = []
            for item in result.get("artifacts", []):
                content = base64.b64decode(item["content"], validate=True)
                saved.append(
                    await artifact_store.create(
                        teacher_user_id,
                        item["name"],
                        content,
                    )
                )
            artifact_sink.extend(saved)
            structure = (
                {
                    "columns": [
                        str(value)[:80] for value in payload.get("columns", [])
                    ],
                    "row_count": len(payload.get("rows", [])),
                    "notice": "表格文件仅写入提供的列名与行数据，未自动添加来源说明或其他备注。",
                }
                if payload.get("mode") == "table"
                else {}
            )
            return json.dumps(
                {
                    "ok": True,
                    "output": result.get("message", "")[:12000],
                    "file_structure": structure,
                    "files": [
                        {"name": item["name"], "size": item["size"]} for item in saved
                    ],
                },
                ensure_ascii=False,
            )
        except ResourceCleanupError:
            # 清理状态未知不能转换成普通工具失败，否则上层会错误宣称“已停止”。
            raise
        except (ValueError, RuntimeError, KeyError) as exc:
            return json.dumps(
                {"ok": False, "error": str(exc)[:300]}, ensure_ascii=False
            )

    @tool
    async def create_chart(
        title: str,
        chart_type: Literal[
            "line",
            "bar",
            "pie",
            "bar_horizontal",
            "donut",
            "scatter",
            "histogram",
            "radar",
            "heatmap",
            "grouped_bar",
            "stacked_bar",
        ],
        labels: list[str] = [],
        values: list[float] = [],
        series: list[dict] = [],
        matrix: list[list[float]] = [],
        x_values: list[float] = [],
        y_labels: list[str] = [],
        bins: int = 10,
    ) -> str:
        """用真实数据制作11类PNG图表。分类图用labels/values；分组/堆积柱图用series=[{name,values}]。

        散点图用x_values/values，直方图用values/bins，雷达用3–12维，热力图用matrix/labels/y_labels。
        不编造数据。数据规模与数值由沙箱再次验证；失败应说明原因。
        """
        return await run_and_save(
            {
                "mode": "chart",
                "title": title[:100],
                "chart_type": chart_type,
                "labels": [str(x)[:80] for x in labels],
                "values": values,
                "series": series,
                "matrix": matrix,
                "x_values": x_values,
                "y_labels": y_labels,
                "bins": bins,
            }
        )

    @tool
    async def run_analysis_code(code: str, data: dict) -> str:
        """在无网络一次性 Docker 沙箱运行 Python 分析；data仅放必要数据。

        可打印结果，将PNG/PDF/DOCX/CSV/TXT/XLSX/MD/HTML/JSON写入OUTPUT_DIR；INPUT_FILE是输入文件。
        """
        return await run_and_save({"mode": "code", "code": code, "data": data})

    @tool
    async def create_report(title: str, sections: list[dict]) -> str:
        """根据授权学情证据或导师本轮提供的数据生成可下载的 Word 报告；sections 包含 heading 和 body。"""
        return await run_and_save(
            {"mode": "report", "title": title[:100], "sections": sections}
        )

    @tool
    async def create_document(
        title: str,
        content: str = "",
        format: Literal["md", "html", "txt", "json", "csv", "xlsx"] = "md",
        sections: list[dict] = [],
    ) -> str:
        """根据真实证据制作通用文档。sections为heading/body章节，html按文字转义，不执行脚本。"""
        return await run_and_save(
            {
                "mode": "document",
                "title": title[:100],
                "content": content,
                "format": format,
                "sections": sections,
            }
        )

    @tool
    async def create_table(
        title: str,
        columns: list[str],
        rows: list[list],
        format: Literal["csv", "xlsx", "json", "md"] = "xlsx",
    ) -> str:
        """用真实数据制作Excel/CSV/JSON/Markdown表格，columns与rows列数须对应。"""
        return await run_and_save(
            {
                "mode": "table",
                "title": title[:100],
                "columns": columns,
                "rows": rows,
                "format": format,
            }
        )

    return [
        create_chart,
        run_analysis_code,
        create_report,
        create_document,
        create_table,
    ]
