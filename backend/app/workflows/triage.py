import base64
import logging
from typing import Any, TypedDict, cast

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from ..llm_provider import LLMTask, get_llm
from ..prompts import (
    CLASSIFY_SYSTEM_PROMPT,
    CODEBASE_SEARCH_SYSTEM_PROMPT,
    TRIAGE_SUMMARY_SYSTEM_PROMPT,
)
from ..schemas.triage import FileSelection, IncidentClassification
from .hooks import get_registered_hooks

logger = logging.getLogger("uvicorn.error")

MIME_TYPES: dict[str, str] = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
}


class TriageState(TypedDict):
    incident_id: str
    description: str
    reporter_name: str
    reporter_email: str
    image_data: bytes | None
    image_filename: str | None
    # Populated by workflow nodes
    category: str | None
    priority: str | None
    severity_score: int | None
    keywords: list[str] | None
    assigned_team: str | None
    relevant_files: list[dict[str, str]] | None
    triage_summary: str | None
    error: str | None


def _build_image_content(image_data: bytes, image_filename: str) -> dict[str, Any]:
    """Build a multimodal image content block for LangChain messages."""
    ext = image_filename.rsplit(".", 1)[-1].lower()
    mime = MIME_TYPES.get(ext, "image/png")
    b64 = base64.b64encode(image_data).decode()
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime};base64,{b64}"},
    }


# ─── Workflow Nodes ───────────────────────────────────────────────────────────


async def classify_node(state: TriageState) -> dict[str, Any]:
    """Classify the incident: category, priority, severity, keywords, team."""
    logger.info("Triage[classify]: starting for incident %s", state["incident_id"])

    llm = get_llm(LLMTask.CLASSIFY)
    structured_llm = llm.with_structured_output(IncidentClassification)

    content: list[str | dict[Any, Any]] = [
        {"type": "text", "text": state["description"]}
    ]

    image_data = state.get("image_data")
    image_filename = state.get("image_filename")
    if image_data and image_filename:
        content.append(_build_image_content(image_data, image_filename))

    raw = await structured_llm.ainvoke(
        [
            SystemMessage(content=CLASSIFY_SYSTEM_PROMPT),
            HumanMessage(content=content),
        ]
    )
    result = cast(IncidentClassification, raw)

    logger.info(
        "Triage[classify]: incident %s -> %s/%s (severity %d, team: %s)",
        state["incident_id"],
        result.category.value,
        result.priority.value,
        result.severity_score,
        result.assigned_team.value,
    )

    return {
        "category": result.category.value,
        "priority": result.priority.value,
        "severity_score": result.severity_score,
        "keywords": result.keywords,
        "assigned_team": result.assigned_team.value,
    }


async def search_codebase_node(state: TriageState) -> dict[str, Any]:
    """Search the e-commerce codebase for relevant files."""
    logger.info(
        "Triage[search_codebase]: searching for incident %s with keywords %s",
        state["incident_id"],
        state.get("keywords"),
    )

    try:
        from ..tools.codebase import (
            get_codebase_manifest,
            get_file_details,
            search_codebase_by_keywords,
        )

        keyword_results = search_codebase_by_keywords(state.get("keywords") or [])
        manifest = get_codebase_manifest()

        if not manifest:
            logger.warning("Triage[search_codebase]: no manifest available, skipping")
            return {"relevant_files": []}

        keyword_paths = "\n".join(f"- {r['path']}" for r in keyword_results)

        prompt = (
            f"Incident: {state['description']}\n"
            f"Category: {state.get('category')}\n"
            f"Keywords: {state.get('keywords')}\n\n"
            f"Keyword search results (top matches):\n{keyword_paths}\n\n"
            f"Full codebase manifest:\n{manifest}"
        )

        llm = get_llm(LLMTask.TRIAGE)
        structured_llm = llm.with_structured_output(FileSelection)

        raw = await structured_llm.ainvoke(
            [
                SystemMessage(content=CODEBASE_SEARCH_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        )
        result = cast(FileSelection, raw)

        details = get_file_details(result.file_paths)
        relevant = [
            {"path": fp, "snippet": details.get(fp, ""), "relevance": result.reasoning}
            for fp in result.file_paths
        ]

        logger.info(
            "Triage[search_codebase]: found %d relevant files for incident %s",
            len(relevant),
            state["incident_id"],
        )
        return {"relevant_files": relevant}

    except Exception:
        logger.exception(
            "Triage[search_codebase]: failed for incident %s", state["incident_id"]
        )
        return {"relevant_files": []}


async def generate_summary_node(state: TriageState) -> dict[str, Any]:
    """Generate the final triage summary referencing actual code."""
    logger.info(
        "Triage[generate_summary]: generating for incident %s", state["incident_id"]
    )

    llm = get_llm(LLMTask.SUMMARIZE)

    code_context = ""
    for f in state.get("relevant_files") or []:
        snippet = f.get("snippet", "")[:2000]
        code_context += f"\n### {f['path']}\n```\n{snippet}\n```\n"

    prompt = (
        f"## Incident Report\n"
        f"**Reporter:** {state.get('reporter_name', 'Unknown')} "
        f"({state.get('reporter_email', '')})\n"
        f"**Description:** {state['description']}\n\n"
        f"## Classification\n"
        f"- **Category:** {state.get('category')}\n"
        f"- **Priority:** {state.get('priority')}\n"
        f"- **Severity:** {state.get('severity_score')}/10\n"
        f"- **Assigned Team:** {state.get('assigned_team')}\n\n"
        f"## Relevant Source Code\n"
        f"{code_context or 'No codebase files available.'}\n\n"
        f"Write the triage report now."
    )

    content: list[str | dict[Any, Any]] = [{"type": "text", "text": prompt}]

    image_data = state.get("image_data")
    image_filename = state.get("image_filename")
    if image_data and image_filename:
        content.append(_build_image_content(image_data, image_filename))

    result = await llm.ainvoke(
        [
            SystemMessage(content=TRIAGE_SUMMARY_SYSTEM_PROMPT),
            HumanMessage(content=content),
        ]
    )

    summary = result.content if isinstance(result.content, str) else str(result.content)

    logger.info(
        "Triage[generate_summary]: completed for incident %s (%d chars)",
        state["incident_id"],
        len(summary),
    )
    return {"triage_summary": summary}


async def run_hooks_node(state: TriageState) -> dict[str, Any]:
    """Execute pluggable integration hooks (ticketing, notifications)."""
    hooks = get_registered_hooks()
    logger.info(
        "Triage[run_hooks]: running %d hooks for incident %s",
        len(hooks),
        state["incident_id"],
    )

    for hook in hooks:
        try:
            await hook(dict(state))
        except Exception:
            logger.exception(
                "Triage[run_hooks]: hook %s failed for incident %s",
                hook.__name__,
                state["incident_id"],
            )

    return {}


# ─── Graph Definition ─────────────────────────────────────────────────────────


def build_triage_graph() -> Any:
    """Build and compile the triage LangGraph workflow."""
    workflow = StateGraph(TriageState)

    workflow.add_node("classify", classify_node)
    workflow.add_node("search_codebase", search_codebase_node)
    workflow.add_node("generate_summary", generate_summary_node)
    workflow.add_node("run_hooks", run_hooks_node)

    workflow.add_edge(START, "classify")
    workflow.add_edge("classify", "search_codebase")
    workflow.add_edge("search_codebase", "generate_summary")
    workflow.add_edge("generate_summary", "run_hooks")
    workflow.add_edge("run_hooks", END)

    return workflow.compile()


triage_graph = build_triage_graph()
