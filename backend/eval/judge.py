"""
LLM-as-Judge chain — scores review quality against expected issues.

Returns precision, recall, and actionability scores for a single test case.
"""

import json
import logging
from typing import List

from pydantic import BaseModel, ValidationError
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException

from chain import _build_llm
from agents.common import clean_llm_json

logger = logging.getLogger(__name__)

JUDGE_PROMPT = """You are evaluating an AI code reviewer's output.

Expected issues for this code:
{expected_issues}

Issues found by the AI reviewer:
{found_issues}

Score the reviewer on:
1. Precision (0-1): What fraction of found issues are real and relevant?
2. Recall (0-1): What fraction of real/expected issues were found?
3. Actionability (0-1): Are suggestions specific and implementable?

Return only valid JSON: {{"precision": float, "recall": float, "actionability": float}}"""


class JudgeScores(BaseModel):
    precision: float
    recall: float
    actionability: float


def judge_review(expected_issues: List[dict], found_issues: List[dict]) -> dict:
    """
    Score a reviewer's output against expected issues using LLM-as-Judge.

    Returns {"precision": float, "recall": float, "actionability": float}.
    """
    llm = _build_llm()
    parser = PydanticOutputParser(pydantic_object=JudgeScores)

    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(JUDGE_PROMPT),
        HumanMessagePromptTemplate.from_template("Evaluate now."),
    ])

    chain = prompt | llm
    response = chain.invoke({
        "expected_issues": json.dumps(expected_issues, indent=2),
        "found_issues": json.dumps(found_issues, indent=2),
    })

    raw_text = response.content if hasattr(response, "content") else str(response)
    cleaned = clean_llm_json(raw_text)

    try:
        scores = parser.parse(cleaned)
    except (OutputParserException, ValidationError):
        try:
            data = json.loads(cleaned)
            scores = JudgeScores(**data)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.error("Judge parse failed: %s", exc)
            return {"precision": 0.0, "recall": 0.0, "actionability": 0.0}

    return {
        "precision": round(scores.precision, 3),
        "recall": round(scores.recall, 3),
        "actionability": round(scores.actionability, 3),
    }
