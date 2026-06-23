"""
graph.py — LangGraph StateGraph orchestrating the multi-agent code review pipeline.

Reviewer and Security agents run in parallel from __start__, merge deduplicates
and ranks issues, then the Explainer agent produces the final ReviewResult.
"""

from typing import TypedDict, List, Optional, Annotated
import operator

from langgraph.graph import StateGraph, START, END

from agents.reviewer import reviewer_node
from agents.security import security_node
from agents.merge import merge_node
from agents.explainer import explainer_node


class AgentState(TypedDict):
    code: str
    language: str
    reviewer_issues: Annotated[List[dict], operator.add]
    security_issues: Annotated[List[dict], operator.add]
    merged_issues: List[dict]
    final_result: Optional[dict]


def build_review_graph():
    """Construct and compile the LangGraph review StateGraph."""
    graph = StateGraph(AgentState)

    graph.add_node("reviewer", reviewer_node)
    graph.add_node("security", security_node)
    graph.add_node("merge", merge_node)
    graph.add_node("explainer", explainer_node)

    # Parallel execution: both agents start from __start__
    graph.add_edge(START, "reviewer")
    graph.add_edge(START, "security")

    # Fan-in to merge, then explainer, then END
    graph.add_edge("reviewer", "merge")
    graph.add_edge("security", "merge")
    graph.add_edge("merge", "explainer")
    graph.add_edge("explainer", END)

    return graph.compile()


review_graph = build_review_graph()


def run_graph_review(code: str, language: str, truncated: bool = False) -> dict:
    """
    Invoke the review graph and return the final ReviewResult dict.

    Raises RuntimeError if the graph produces no final_result.
    """
    initial_state: AgentState = {
        "code": code,
        "language": language,
        "reviewer_issues": [],
        "security_issues": [],
        "merged_issues": [],
        "final_result": None,
        "truncated": truncated,
    }

    result = review_graph.invoke(initial_state)
    final = result.get("final_result")

    if final is None:
        raise RuntimeError("Review graph completed without producing a final_result.")

    return final
