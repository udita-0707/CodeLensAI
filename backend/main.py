"""
main.py — FastAPI application for CodeLens AI.

Endpoints:
  GET  /health       — health check
  POST /review/code  — review raw code snippet
  POST /review/pr    — fetch GitHub PR diff and review it
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

from chain import run_review, ReviewResult
from github_client import fetch_pr_diff

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("CodeLens AI backend starting up…")
    yield
    logger.info("CodeLens AI backend shutting down.")


app = FastAPI(
    title="CodeLens AI",
    description="AI-powered code review via LangChain + OpenRouter.",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow requests from the Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
        result = run_review(code=body.code, language=body.language)
    except EnvironmentError as exc:
        # Missing API key — surface as a clear 500
        raise HTTPException(status_code=500, detail=str(exc))
    except RuntimeError as exc:
        # LLM parse failure after retries
        raise HTTPException(status_code=500, detail=str(exc))

    return result


@app.post("/review/pr", response_model=PRReviewResponse, tags=["review"])
def review_pr(body: PRReviewRequest):
    """
    Accept a GitHub PR URL, fetch the diff, and return structured review JSON.

    Body: { "pr_url": "https://github.com/owner/repo/pull/123" }
    """
    if not body.pr_url.strip():
        raise HTTPException(status_code=422, detail="'pr_url' must not be empty.")

    logger.info("POST /review/pr  url=%s", body.pr_url)

    # Fetch the PR diff from GitHub
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

    # Run the review chain on the diff
    try:
        review = run_review(code=diff_result.diff, language=diff_result.language)
    except EnvironmentError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return PRReviewResponse(
        **review.model_dump(),
        pr_title=diff_result.pr_title,
        pr_url=diff_result.pr_url,
        truncated=diff_result.truncated,
    )
