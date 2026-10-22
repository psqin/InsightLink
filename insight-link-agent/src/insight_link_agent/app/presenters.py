"""HTTP响应投影：隐藏内部字段并统一文件、工作流与消息展示。"""

from insight_link_agent.agent.conversation.formatting import clean_teacher_answer


def _config(run_id: str) -> dict:
    return {"configurable": {"thread_id": run_id}}


def _public_chat_messages(messages: list[dict]) -> list[dict]:
    return [
        {**item, "content": clean_teacher_answer(item["content"])}
        if item["role"] == "assistant"
        else item
        for item in messages
    ]


def _artifact_markers(artifacts: list[dict]) -> str:
    return "".join(
        f"\n\n[[artifact:{item['id']}:{item['name']}]]" for item in artifacts
    )


def _public_state(run_id: str, status: str, state: dict) -> dict:
    return {
        "run_id": run_id,
        "status": status,
        "phase": state.get("phase", "running"),
        "plan": state.get("plan", []),
        "material_id": state.get("material_id"),
        "sources": [
            {"id": source["id"], "kind": source["kind"], "title": source["title"]}
            for source in state.get("sources", [])
        ],
        "warnings": state.get("warnings", []),
        "draft": state.get("draft"),
        "review": state.get("review"),
        "revisions": state.get("revisions", 0),
        "final_comment": state.get("final_comment"),
        "phase_trace": state.get("phase_trace", []),
    }
