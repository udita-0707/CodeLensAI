"""
CLI evaluation runner — runs all test cases through review_graph and scores with LLM-as-Judge.

Usage: python run_eval.py
Saves results to eval/results.json and prints a summary table.
"""

import json
import logging
import os
import sys

# Allow running as `python eval/run_eval.py` from the backend directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

from graph import run_graph_review
from eval.test_cases import TEST_CASES
from eval.judge import judge_review

RESULTS_PATH = os.path.join(os.path.dirname(__file__), "results.json")


def run_evaluation() -> dict:
    """
    Run all test cases through the review graph and score each with the judge.

    Returns {"results": [...], "summary": {...}}.
    """
    results = []

    for case in TEST_CASES:
        case_id = case["id"]
        logger.info("Evaluating test case %d", case_id)

        try:
            review = run_graph_review(code=case["code"], language=case["language"])
            found_issues = review.get("issues", [])
        except Exception as exc:
            logger.error("Test case %d failed: %s", case_id, exc)
            found_issues = []

        scores = judge_review(case["expected_issues"], found_issues)

        results.append({
            "id": case_id,
            "expected_issues": case["expected_issues"],
            "found_issues": found_issues,
            "scores": scores,
        })

    if results:
        avg_precision = sum(r["scores"]["precision"] for r in results) / len(results)
        avg_recall = sum(r["scores"]["recall"] for r in results) / len(results)
        avg_actionability = sum(r["scores"]["actionability"] for r in results) / len(results)
    else:
        avg_precision = avg_recall = avg_actionability = 0.0

    summary = {
        "avg_precision": round(avg_precision, 3),
        "avg_recall": round(avg_recall, 3),
        "avg_actionability": round(avg_actionability, 3),
    }

    return {"results": results, "summary": summary}


def print_summary_table(eval_output: dict) -> None:
    """Print a formatted summary table to stdout."""
    print("\n" + "=" * 72)
    print(f"{'Case':>6}  {'Precision':>10}  {'Recall':>10}  {'Actionability':>14}")
    print("-" * 72)

    for r in eval_output["results"]:
        s = r["scores"]
        print(
            f"{r['id']:>6}  "
            f"{s['precision']:>10.3f}  "
            f"{s['recall']:>10.3f}  "
            f"{s['actionability']:>14.3f}"
        )

    print("-" * 72)
    summary = eval_output["summary"]
    print(
        f"{'AVG':>6}  "
        f"{summary['avg_precision']:>10.3f}  "
        f"{summary['avg_recall']:>10.3f}  "
        f"{summary['avg_actionability']:>14.3f}"
    )
    print("=" * 72 + "\n")


def main() -> None:
    eval_output = run_evaluation()
    print_summary_table(eval_output)

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(eval_output, f, indent=2)

    print(f"Results saved to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
