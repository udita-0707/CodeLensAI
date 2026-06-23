"""
Security Agent — LangGraph node focused on OWASP vulnerabilities and security risks.

Runs in parallel with the Reviewer Agent via LangGraph fan-out from __start__.
"""

import logging
from typing import Any, Dict

from agents.common import invoke_issues_llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a security-focused code reviewer. Only identify security vulnerabilities — "
    "OWASP Top 10, injection risks, hardcoded secrets, insecure dependencies, and unvalidated inputs. "
    "Return ONLY a valid JSON array of issues. No markdown, no preamble.\n\n"
    "Each issue must have: severity (critical|warning|info), category (always \"security\"), "
    "line (int or null), description (str), suggestion (str).\n\n"
    "{format_instructions}"
)

STRICT_SYSTEM_PROMPT = (
    "You are a security-focused code reviewer. Your ONLY output must be a single raw JSON array. "
    "Do not include any text before or after the JSON. Do not use markdown code fences. "
    "Every issue must have category \"security\".\n\n"
    "{format_instructions}"
)


def security_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: run the Security Agent and append issues to state.

    Writes to ``security_issues`` (reducer: operator.add).
    """
    code = state["code"]
    language = state.get("language", "Unknown")

    human_content = (
        f"Language: {language}\n\n"
        f"Code to review:\n```\n{code}\n```"
    )

    logger.info("Security agent running  lang=%s  chars=%d", language, len(code))
    issues = invoke_issues_llm(SYSTEM_PROMPT, STRICT_SYSTEM_PROMPT, human_content)

    # Enforce category = security on all issues
    for issue in issues:
        issue["category"] = "security"

    logger.info("Security agent found %d issues", len(issues))
    return {"security_issues": issues}
