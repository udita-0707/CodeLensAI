"""
Explainer Agent — LangGraph node that rewrites issues in plain English for junior developers.

Computes quality_score and produces the final ReviewResult dict.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ValidationError
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException

from chain import Issue, _build_llm
from agents.common import clean_llm_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a helpful senior engineer explaining code review feedback. "
    "Rewrite each issue's description and suggestion to be clear, specific, and actionable "
    "for a junior developer. Return ONLY valid JSON matching the input schema exactly.\n\n"
    "Return a JSON object with:\n"
    '- "summary": 1-2 sentence plain-English overview of the review\n'
    '- "issues": array of issues with severity, category, line, description, suggestion\n\n'
    "{format_instructions}"
)

STRICT_SYSTEM_PROMPT = (
    "You are a helpful senior engineer. Your ONLY output must be a single raw JSON object. "
    "Do not include any text before or after the JSON. Do not use markdown code fences.\n\n"
    "{format_instructions}"
)


class ExplainerOutput(BaseModel):
    summary: str
    issues: List[Issue]


def _compute_quality_score(issues: List[dict]) -> int:
    """Start at 100, subtract per severity, floor at 0."""
    score = 100
    for issue in issues:
        severity = issue.get("severity", "info")
        if severity == "critical":
            score -= 15
        elif severity == "warning":
            score -= 7
        else:
            score -= 2
    return max(0, score)


def _parse_explainer_output(raw: str, parser: PydanticOutputParser) -> ExplainerOutput:
    cleaned = clean_llm_json(raw)
    try:
        return parser.parse(cleaned)
    except (OutputParserException, ValidationError):
        data = json.loads(cleaned)
        return ExplainerOutput(**data)


def explainer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: rewrite merged issues in plain English and build final_result.

    Writes to ``final_result``.
    """
    merged_issues = state.get("merged_issues", [])
    truncated = state.get("truncated", False)

    if not merged_issues:
        final_result = {
            "quality_score": 100,
            "summary": "No issues found. The code looks clean.",
            "issues": [],
            "truncated": truncated,
        }
        return {"final_result": final_result}

    llm = _build_llm()
    parser = PydanticOutputParser(pydantic_object=ExplainerOutput)

    issues_json = json.dumps(merged_issues, indent=2)
    human_content = f"Issues to explain:\n{issues_json}"

    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT),
        HumanMessagePromptTemplate.from_template("{content}"),
    ]).partial(format_instructions=parser.get_format_instructions())

    chain = prompt | llm
    logger.info("Explainer agent running on %d issues", len(merged_issues))

    response = chain.invoke({"content": human_content})
    raw_text = response.content if hasattr(response, "content") else str(response)

    try:
        explained = _parse_explainer_output(raw_text, parser)
    except (OutputParserException, ValidationError, json.JSONDecodeError) as first_err:
        logger.warning("Explainer parse failed: %s — retrying", first_err)
        strict_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(STRICT_SYSTEM_PROMPT),
            HumanMessagePromptTemplate.from_template("{content}"),
        ]).partial(format_instructions=parser.get_format_instructions())
        response2 = (strict_prompt | llm).invoke({"content": human_content})
        raw_text2 = response2.content if hasattr(response2, "content") else str(response2)
        try:
            explained = _parse_explainer_output(raw_text2, parser)
        except (OutputParserException, ValidationError, json.JSONDecodeError) as second_err:
            logger.error("Explainer both attempts failed — using raw issues: %s", second_err)
            explained = ExplainerOutput(
                summary=_fallback_summary(merged_issues),
                issues=[Issue(**i) for i in merged_issues],
            )

    explained_issues = [issue.model_dump() for issue in explained.issues]
    quality_score = _compute_quality_score(explained_issues)

    final_result = {
        "quality_score": quality_score,
        "summary": explained.summary,
        "issues": explained_issues,
        "truncated": truncated,
    }

    logger.info("Explainer done  quality_score=%d  issues=%d", quality_score, len(explained_issues))
    return {"final_result": final_result}


def _fallback_summary(issues: List[dict]) -> str:
    critical = sum(1 for i in issues if i.get("severity") == "critical")
    warning = sum(1 for i in issues if i.get("severity") == "warning")
    if critical:
        return f"Found {critical} critical and {warning} warning issue(s) that need attention."
    if warning:
        return f"Found {warning} warning issue(s) worth addressing."
    return f"Found {len(issues)} minor suggestion(s) for improvement."
