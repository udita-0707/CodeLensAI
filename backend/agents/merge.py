"""
Merge node — deduplicates and ranks issues from Reviewer and Security agents.

Pure Python logic, no LLM call. Runs after parallel agent nodes complete.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

SEVERITY_RANK = {"critical": 0, "warning": 1, "info": 2}


def _severity_value(severity: str) -> int:
    return SEVERITY_RANK.get(severity, 99)


def _deduplicate_issues(issues: List[dict]) -> List[dict]:
    """
    If two issues share the same line number and category, keep the higher-severity one.
    """
    best: Dict[tuple, dict] = {}

    for issue in issues:
        line = issue.get("line")
        category = issue.get("category", "")
        key = (line, category)

        existing = best.get(key)
        if existing is None:
            best[key] = issue
        elif _severity_value(issue.get("severity", "info")) < _severity_value(
            existing.get("severity", "info")
        ):
            best[key] = issue

    return list(best.values())


def _sort_by_severity(issues: List[dict]) -> List[dict]:
    """Sort critical first, then warning, then info."""
    return sorted(issues, key=lambda i: _severity_value(i.get("severity", "info")))


def merge_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: combine reviewer_issues and security_issues, deduplicate, rank.

    Writes to ``merged_issues``.
    """
    reviewer = state.get("reviewer_issues", [])
    security = state.get("security_issues", [])
    combined = list(reviewer) + list(security)

    merged = _sort_by_severity(_deduplicate_issues(combined))
    logger.info(
        "Merge node: %d reviewer + %d security → %d merged",
        len(reviewer), len(security), len(merged),
    )

    return {"merged_issues": merged}
