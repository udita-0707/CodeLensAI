"""
main.py — FastAPI application for CodeLens AI v2.

Endpoints:
  GET  /health       — health check
  POST /review/code  — multi-agent review of raw code snippet
  POST /review/pr    — fetch GitHub PR diff and review it
  POST /index/repo   — index a GitHub repo into ChromaDB for RAG
  GET  /eval/run     — run evaluation suite and return metrics
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from chain import ReviewResult, Issue
from graph import run_graph_review
from github_client import fetch_pr_diff
from rag.indexer import index_repo
from eval.run_eval import run_evaluation

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CORS — comma-separated list of allowed origins from env var.
# Example: ALLOWED_ORIGINS=https://codelens-ai.pages.dev,https://localhost:5173
# ---------------------------------------------------------------------------
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]
logger.info("CORS allowed origins: %s", ALLOWED_ORIGINS)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("CodeLens AI v2 backend starting up…")
    yield
    logger.info("CodeLens AI v2 backend shutting down.")


app = FastAPI(
    title="CodeLens AI",
    description="AI-powered multi-agent code review via LangGraph + OpenRouter.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class CodeReviewRequest(BaseModel):
    code: str
    language: str = "Unknown"


class PRReviewRequest(BaseModel):
    pr_url: str


class PRReviewResponse(ReviewResult):
    """ReviewResult extended with PR-level metadata."""
    pr_title: str = ""
    pr_url: str = ""
    truncated: bool = False


class IndexRepoRequest(BaseModel):
    repo_url: str


class IndexRepoResponse(BaseModel):
    chunks_indexed: int
    status: str


class EvalSummary(BaseModel):
    avg_precision: float
    avg_recall: float
    avg_actionability: float


class EvalRunResponse(BaseModel):
    results: list
    summary: EvalSummary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dict_to_review_result(result_dict: dict) -> ReviewResult:
    """Convert graph final_result dict to a ReviewResult Pydantic model."""
    return ReviewResult(
        quality_score=result_dict["quality_score"],
        summary=result_dict["summary"],
        issues=[Issue(**i) if isinstance(i, dict) else i for i in result_dict["issues"]],
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["meta"])
def health():
    """Simple liveness check."""
    return {"status": "ok"}


@app.post("/review/code", response_model=ReviewResult, tags=["review"])
def review_code(body: CodeReviewRequest):
    """
    Accept a raw code snippet and return structured review JSON.

    Body: { "code": "...", "language": "Python" }
    """
    if not body.code.strip():
        raise HTTPException(status_code=422, detail="'code' must not be empty.")

    logger.info("POST /review/code  lang=%s  chars=%d", body.language, len(body.code))

    try:
        result_dict = run_graph_review(code=body.code, language=body.language)
    except EnvironmentError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return _dict_to_review_result(result_dict)


@app.post("/review/pr", response_model=PRReviewResponse, tags=["review"])
def review_pr(body: PRReviewRequest):
    """
    Accept a GitHub PR URL, fetch the diff, and return structured review JSON.

    Body: { "pr_url": "https://github.com/owner/repo/pull/123" }
    """
    if not body.pr_url.strip():
        raise HTTPException(status_code=422, detail="'pr_url' must not be empty.")

    logger.info("POST /review/pr  url=%s", body.pr_url)

    try:
        diff_result = fetch_pr_diff(body.pr_url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    if not diff_result.diff.strip():
        raise HTTPException(
            status_code=422,
            detail="The pull request has no text diff to review (all binary files?)."
        )

    try:
        result_dict = run_graph_review(
            code=diff_result.diff,
            language=diff_result.language,
            truncated=diff_result.truncated,
        )
    except EnvironmentError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    review = _dict_to_review_result(result_dict)

    return PRReviewResponse(
        **review.model_dump(),
        pr_title=diff_result.pr_title,
        pr_url=diff_result.pr_url,
        truncated=diff_result.truncated,
    )


@app.post("/index/repo", response_model=IndexRepoResponse, tags=["rag"])
def index_repository(body: IndexRepoRequest):
    """
    Index a GitHub repository into ChromaDB for RAG-powered review context.

    Body: { "repo_url": "https://github.com/owner/repo" }
    """
    if not body.repo_url.strip():
        raise HTTPException(status_code=422, detail="'repo_url' must not be empty.")

    logger.info("POST /index/repo  url=%s", body.repo_url)

    try:
        result = index_repo(body.repo_url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except EnvironmentError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return IndexRepoResponse(**result)


@app.get("/eval/run", response_model=EvalRunResponse, tags=["eval"])
def eval_run():
    """
    Run the full evaluation suite (15 test cases) and return metrics.

    Note: this endpoint invokes the LLM for every test case — may take several minutes.
    """
    logger.info("GET /eval/run — starting evaluation suite")

    try:
        eval_output = run_evaluation()
    except EnvironmentError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        logger.error("Evaluation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {exc}")

    return EvalRunResponse(**eval_output)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
