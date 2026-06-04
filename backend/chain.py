"""
chain.py — LangChain review chain powered by OpenRouter (Claude 3.5 Sonnet).

Uses ChatOpenAI pointed at OpenRouter's OpenAI-compatible endpoint.
Parses LLM output into a typed ReviewResult via PydanticOutputParser.
Retries once with a stricter prompt on JSON parse failure.
"""

import os
import json
import logging
from typing import List, Optional, Literal

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic output schema
# ---------------------------------------------------------------------------

class Issue(BaseModel):
    severity: Literal["critical", "warning", "info"]
    category: Literal["bug", "security", "style", "complexity", "perf"]
    line: Optional[int] = None
    description: str
    suggestion: str


class ReviewResult(BaseModel):
    quality_score: int  # 0-100
    summary: str
    issues: List[Issue]


# ---------------------------------------------------------------------------
# LLM — OpenRouter via LangChain's ChatOpenAI
# ---------------------------------------------------------------------------

def _build_llm() -> ChatOpenAI:
    """Construct a ChatOpenAI instance pointed at OpenRouter."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENROUTER_API_KEY is not set. "
            "Copy backend/.env.example to backend/.env and fill in your key."
        )

    model_name = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
    return ChatOpenAI(
        model=model_name,
        temperature=0,
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": "CodeLens AI",
        },
    )


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are an expert code reviewer at a top-tier software engineering company.\n\n"
    "Review the provided code and return ONLY valid JSON — no markdown fences, no preamble, "
    "no explanation outside the JSON object.\n\n"
    "Rules:\n"
    "- Review for bugs, security vulnerabilities, style violations, and code complexity.\n"
    "- Include line numbers wherever possible — line-level feedback is the most valuable output.\n"
    "- Do not hallucinate fixes you are not certain about.\n"
    "- Return JSON matching the exact schema provided.\n\n"
    "{format_instructions}"
)

HUMAN_PROMPT = (
    "Language: {language}\n\n"
    "Code to review:\n"
    "```\n"
    "{code}\n"
    "```"
)

STRICT_SYSTEM_PROMPT = (
    "You are an expert code reviewer. Your ONLY output must be a single raw JSON object. "
    "Do not include any text before or after the JSON. "
    "Do not use markdown code fences. "
    "Return JSON matching EXACTLY this schema:\n\n"
    "{format_instructions}"
)


def _make_prompt(system_template: str, parser: PydanticOutputParser) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_template),
        HumanMessagePromptTemplate.from_template(HUMAN_PROMPT),
    ]).partial(format_instructions=parser.get_format_instructions())


# ---------------------------------------------------------------------------
# Public review function
# ---------------------------------------------------------------------------

def run_review(code: str, language: str) -> ReviewResult:
    """
    Run the LangChain review chain on the given code.

    Retries once with a stricter prompt if the first parse fails.
    Raises RuntimeError on second failure (caller should return HTTP 500).
    """
    llm = _build_llm()
    parser = PydanticOutputParser(pydantic_object=ReviewResult)

    # --- First attempt ---
    prompt = _make_prompt(SYSTEM_PROMPT, parser)
    chain = prompt | llm

    logger.info("Running review chain (attempt 1)  lang=%s  chars=%d", language, len(code))
    response = chain.invoke({"code": code, "language": language})
    raw_text = response.content if hasattr(response, "content") else str(response)

    try:
        return _parse_output(raw_text, parser)
    except (OutputParserException, ValidationError, json.JSONDecodeError) as first_err:
        logger.warning("First parse attempt failed: %s — retrying with strict prompt", first_err)

    # --- Second attempt with stricter prompt ---
    strict_prompt = _make_prompt(STRICT_SYSTEM_PROMPT, parser)
    strict_chain = strict_prompt | llm

    logger.info("Running review chain (attempt 2 — strict prompt)")
    response2 = strict_chain.invoke({"code": code, "language": language})
    raw_text2 = response2.content if hasattr(response2, "content") else str(response2)

    try:
        return _parse_output(raw_text2, parser)
    except (OutputParserException, ValidationError, json.JSONDecodeError) as second_err:
        logger.error("Both parse attempts failed. Last error: %s", second_err)
        raise RuntimeError(
            f"LLM returned malformed JSON after two attempts. "
            f"Last error: {second_err}. "
            f"Raw output (truncated): {raw_text2[:500]}"
        ) from second_err


def _parse_output(raw: str, parser: PydanticOutputParser) -> ReviewResult:
    """
    Try PydanticOutputParser first; fall back to manual JSON extraction
    (strips accidental markdown fences the model may have added).
    """
    # Strip markdown fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        # Remove opening ``` line and closing ``` line
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()

    try:
        return parser.parse(cleaned)
    except (OutputParserException, ValidationError):
        # Try raw JSON parse as a last resort
        data = json.loads(cleaned)
        return ReviewResult(**data)
