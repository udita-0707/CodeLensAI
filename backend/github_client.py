"""
github_client.py — GitHub PR diff fetcher using PyGithub.

Parses a GitHub PR URL (https://github.com/owner/repo/pull/123),
fetches the full diff via the GitHub REST API, and truncates to
MAX_DIFF_LINES if the diff is too large for the LLM context window.
"""

import os
import re
import logging
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from github import Github, GithubException, UnknownObjectException

load_dotenv()

logger = logging.getLogger(__name__)

# Max number of changed lines to pass to the LLM.
# Larger diffs are truncated to avoid context-window overflow.
MAX_DIFF_LINES = 200

# Regex to parse GitHub PR URLs in any of these forms:
#   https://github.com/owner/repo/pull/123
#   https://github.com/owner/repo/pull/123/files
PR_URL_RE = re.compile(
    r"https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)",
    re.IGNORECASE,
)


@dataclass
class DiffResult:
    diff: str
    language: str          # best-guess language from file extensions
    truncated: bool        # True if the diff was cut at MAX_DIFF_LINES
    pr_title: str
    pr_url: str


def fetch_pr_diff(pr_url: str) -> DiffResult:
    """
    Fetch the unified diff for a GitHub pull request.

    Args:
        pr_url: Full GitHub PR URL, e.g. https://github.com/owner/repo/pull/42

    Returns:
        DiffResult with the diff string and metadata.

    Raises:
        ValueError: If the URL is not a valid GitHub PR URL.
        RuntimeError: If the GitHub API call fails.
    """
    match = PR_URL_RE.search(pr_url)
    if not match:
        raise ValueError(
            f"Could not parse a GitHub PR URL from: '{pr_url}'. "
            "Expected format: https://github.com/owner/repo/pull/123"
        )

    owner = match.group("owner")
    repo_name = match.group("repo")
    pr_number = int(match.group("number"))

    logger.info("Fetching PR diff  owner=%s  repo=%s  pr=%d", owner, repo_name, pr_number)

    # Authenticate if a token is available (raises rate limit from 60 → 5000 req/hr)
    github_token = os.getenv("GITHUB_TOKEN")
    g = Github(github_token) if github_token else Github()

    try:
        repo = g.get_repo(f"{owner}/{repo_name}")
        pr = repo.get_pull(pr_number)
    except UnknownObjectException:
        raise RuntimeError(
            f"PR not found: {pr_url}. "
            "Make sure the repository is public (or provide a GITHUB_TOKEN with access)."
        )
    except GithubException as exc:
        raise RuntimeError(f"GitHub API error: {exc.data.get('message', str(exc))}")

    # Collect changed lines from all files in the PR
    diff_lines: list[str] = []
    extensions: list[str] = []
    truncated = False

    files = pr.get_files()
    for f in files:
        if f.patch is None:
            continue  # binary files have no patch

        # Track file extensions for language detection
        ext = _extension(f.filename)
        if ext:
            extensions.append(ext)

        diff_lines.append(f"--- a/{f.filename}")
        diff_lines.append(f"+++ b/{f.filename}")

        for line in f.patch.splitlines():
            diff_lines.append(line)
            if len(diff_lines) >= MAX_DIFF_LINES:
                truncated = True
                break

        if truncated:
            diff_lines.append(f"\n# ... diff truncated at {MAX_DIFF_LINES} lines ...")
            break

    raw_diff = "\n".join(diff_lines)
    language = _detect_language(extensions) or "Unknown"

    logger.info(
        "Diff fetched  lines=%d  truncated=%s  language=%s",
        len(diff_lines), truncated, language,
    )

    return DiffResult(
        diff=raw_diff,
        language=language,
        truncated=truncated,
        pr_title=pr.title,
        pr_url=pr.html_url,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extension(filename: str) -> Optional[str]:
    """Return the lowercase file extension (without dot), or None."""
    if "." in filename:
        return filename.rsplit(".", 1)[-1].lower()
    return None


_EXT_TO_LANG: dict[str, str] = {
    "py": "Python",
    "js": "JavaScript",
    "ts": "TypeScript",
    "tsx": "TypeScript",
    "jsx": "JavaScript",
    "go": "Go",
    "rs": "Rust",
    "java": "Java",
    "cpp": "C++",
    "cc": "C++",
    "c": "C",
    "rb": "Ruby",
    "php": "PHP",
    "cs": "C#",
    "swift": "Swift",
    "kt": "Kotlin",
    "sh": "Shell",
    "yaml": "YAML",
    "yml": "YAML",
    "json": "JSON",
    "html": "HTML",
    "css": "CSS",
    "sql": "SQL",
}


def _detect_language(extensions: list[str]) -> Optional[str]:
    """Pick the most common language from a list of file extensions."""
    if not extensions:
        return None
    counts: dict[str, int] = {}
    for ext in extensions:
        lang = _EXT_TO_LANG.get(ext)
        if lang:
            counts[lang] = counts.get(lang, 0) + 1
    if not counts:
        return None
    return max(counts, key=counts.__getitem__)
