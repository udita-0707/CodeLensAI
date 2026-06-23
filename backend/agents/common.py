"""
Shared helpers for LangGraph agent nodes — LLM issue parsing and output cleaning.
"""

import json
import logging
from typing import List

from pydantic import BaseModel, ValidationError
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException

from chain import Issue, _build_llm

logger = logging.getLogger(__name__)


class IssueListOutput(BaseModel):
    """Wrapper so PydanticOutputParser can target a JSON array of issues."""

    issues: List[Issue]


def clean_llm_json(raw: str) -> str:
    """Strip markdown fences and whitespace from LLM output."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    return cleaned


def parse_issues_array(raw: str, parser: PydanticOutputParser) -> List[dict]:
    """
    Parse a JSON array of issues using PydanticOutputParser.

    Accepts either a bare JSON array or {"issues": [...]}.
    """
    cleaned = clean_llm_json(raw)

    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            issues = [Issue(**item) for item in data]
            return [issue.model_dump() for issue in issues]
        wrapped = IssueListOutput(**data)
        return [issue.model_dump() for issue in wrapped.issues]
    except (json.JSONDecodeError, ValidationError, TypeError):
        pass

    try:
        parsed = parser.parse(cleaned)
        if isinstance(parsed, IssueListOutput):
            return [issue.model_dump() for issue in parsed.issues]
    except (OutputParserException, ValidationError):
        pass

    raise OutputParserException(f"Could not parse issues from LLM output: {cleaned[:200]}")


def invoke_issues_llm(
    system_prompt: str,
    strict_system_prompt: str,
    human_content: str,
) -> List[dict]:
    """
    Call the LLM with system + human messages, parse issues JSON, retry once on failure.
    """
    llm = _build_llm()
    parser = PydanticOutputParser(pydantic_object=IssueListOutput)

    from langchain_core.prompts import (
        ChatPromptTemplate,
        SystemMessagePromptTemplate,
        HumanMessagePromptTemplate,
    )

    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_prompt),
        HumanMessagePromptTemplate.from_template("{content}"),
    ]).partial(format_instructions=parser.get_format_instructions())

    chain = prompt | llm
    response = chain.invoke({"content": human_content})
    raw_text = response.content if hasattr(response, "content") else str(response)

    try:
        return parse_issues_array(raw_text, parser)
    except OutputParserException as first_err:
        logger.warning("First parse attempt failed: %s — retrying with strict prompt", first_err)

    strict_prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(strict_system_prompt),
        HumanMessagePromptTemplate.from_template("{content}"),
    ]).partial(format_instructions=parser.get_format_instructions())

    strict_chain = strict_prompt | llm
    response2 = strict_chain.invoke({"content": human_content})
    raw_text2 = response2.content if hasattr(response2, "content") else str(response2)

    try:
        return parse_issues_array(raw_text2, parser)
    except OutputParserException as second_err:
        logger.error("Both parse attempts failed: %s", second_err)
        raise RuntimeError(
            f"LLM returned malformed JSON after two attempts. "
            f"Last error: {second_err}. "
            f"Raw output (truncated): {raw_text2[:500]}"
        ) from second_err
