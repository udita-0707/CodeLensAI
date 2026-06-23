"""
Reviewer Agent — LangGraph node that identifies bugs, style, complexity, and perf issues.

Queries ChromaDB for similar codebase patterns before the LLM call when available.
"""

import logging
from typing import Any, Dict

from agents.common import invoke_issues_llm
from rag.retriever import retrieve_similar_chunks, format_chunks_for_prompt

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an expert code reviewer. Identify bugs, style issues, complexity problems, "
    "and performance issues. Return ONLY a valid JSON array of issues. No markdown, no preamble.\n\n"
    "Each issue must have: severity (critical|warning|info), category (bug|style|complexity|perf), "
    "line (int or null), description (str), suggestion (str).\n\n"
    "{format_instructions}"
)

STRICT_SYSTEM_PROMPT = (
    "You are an expert code reviewer. Your ONLY output must be a single raw JSON array of issue objects. "
    "Do not include any text before or after the JSON. Do not use markdown code fences.\n\n"
    "Each issue: severity, category (bug|style|complexity|perf), line, description, suggestion.\n\n"
    "{format_instructions}"
)


def reviewer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: run the Reviewer Agent and append issues to state.

    Writes to ``reviewer_issues`` (reducer: operator.add).
    """
    code = state["code"]
    language = state.get("language", "Unknown")

    rag_context = ""
    try:
        chunks = retrieve_similar_chunks(code)
        rag_context = format_chunks_for_prompt(chunks)
    except Exception as exc:
        logger.warning("RAG context retrieval failed in reviewer — continuing: %s", exc)

    if rag_context:
        human_content = (
            f"{rag_context}\n\nNow review:\n\n"
            f"Language: {language}\n\n"
            f"Code to review:\n```\n{code}\n```"
        )
    else:
        human_content = (
            f"Language: {language}\n\n"
            f"Code to review:\n```\n{code}\n```"
        )

    logger.info("Reviewer agent running  lang=%s  chars=%d", language, len(code))
    issues = invoke_issues_llm(SYSTEM_PROMPT, STRICT_SYSTEM_PROMPT, human_content)

    # Filter out security categories — those belong to the Security Agent
    filtered = [i for i in issues if i.get("category") != "security"]
    logger.info("Reviewer agent found %d issues", len(filtered))

    return {"reviewer_issues": filtered}
