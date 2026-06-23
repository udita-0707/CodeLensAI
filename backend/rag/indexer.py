"""
Codebase indexer — clones/fetches a GitHub repo, AST-chunks source files, embeds into ChromaDB.

Chunks Python files by AST function/class boundaries; JS/TS by declaration heuristics.
Skips binary files and files exceeding 500 lines.
"""

import ast
import logging
import os
import re
from typing import List, Optional
from urllib.parse import urlparse

from dotenv import load_dotenv
from github import Github, GithubException, UnknownObjectException

from rag.compat import import_chromadb

load_dotenv()

logger = logging.getLogger(__name__)

COLLECTION_NAME = "codelens_codebase"
MAX_FILE_LINES = 500
INDEXABLE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx"}


def _parse_repo_url(repo_url: str) -> tuple[str, str]:
    """Extract owner and repo name from a GitHub URL."""
    parsed = urlparse(repo_url)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        raise ValueError(
            f"Could not parse GitHub repo URL: '{repo_url}'. "
            "Expected format: https://github.com/owner/repo"
        )
    return parts[0], parts[1].replace(".git", "")


def _get_embeddings():
    """Build OpenAIEmbeddings pointed at OpenRouter."""
    from langchain_openai import OpenAIEmbeddings

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENROUTER_API_KEY is not set. "
            "Copy backend/.env.example to backend/.env and fill in your key."
        )

    return OpenAIEmbeddings(
        model=os.getenv("OPENROUTER_EMBEDDING_MODEL", "openai/text-embedding-3-small"),
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": "CodeLens AI v2",
        },
    )


def _get_chroma_collection():
    """Return ChromaDB collection, creating the persistent client if needed."""
    chromadb = import_chromadb()
    if chromadb is None:
        raise RuntimeError(
            "ChromaDB is not available in this environment. "
            "Install chromadb>=1.0 on Python 3.11–3.13 for RAG indexing."
        )

    persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    os.makedirs(persist_dir, exist_ok=True)
    client = chromadb.PersistentClient(path=persist_dir)
    return client.get_or_create_collection(name=COLLECTION_NAME)


def chunk_python_source(source: str, filepath: str) -> List[dict]:
    """Chunk Python source by AST function and class boundaries."""
    chunks: List[dict] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        logger.warning("Skipping unparseable Python file %s: %s", filepath, exc)
        return chunks

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            segment = ast.get_source_segment(source, node)
            if not segment:
                continue
            chunks.append({
                "content": segment,
                "function_name": node.name,
                "line_start": node.lineno,
                "line_end": node.end_lineno or node.lineno,
                "file_path": filepath,
                "language": "python",
            })
    return chunks


def chunk_js_ts_source(source: str, filepath: str) -> List[dict]:
    """
    Chunk JS/TS source by splitting on function, const, and class declarations.

    Simple heuristic — splits on lines matching declaration patterns.
    """
    lang = "typescript" if filepath.endswith((".ts", ".tsx")) else "javascript"
    pattern = re.compile(
        r"^(export\s+)?(async\s+)?(function\s+\w+|const\s+\w+\s*=|class\s+\w+)",
        re.MULTILINE,
    )

    matches = list(pattern.finditer(source))
    if not matches:
        return [{
            "content": source,
            "function_name": os.path.basename(filepath),
            "line_start": 1,
            "line_end": source.count("\n") + 1,
            "file_path": filepath,
            "language": lang,
        }]

    chunks: List[dict] = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(source)
        chunk_text = source[start:end].strip()
        if not chunk_text:
            continue

        line_start = source[:start].count("\n") + 1
        line_end = line_start + chunk_text.count("\n")
        name_match = re.search(r"(?:function|class)\s+(\w+)|const\s+(\w+)", match.group())
        func_name = (name_match.group(1) or name_match.group(2)) if name_match else "anonymous"

        chunks.append({
            "content": chunk_text,
            "function_name": func_name,
            "line_start": line_start,
            "line_end": line_end,
            "file_path": filepath,
            "language": lang,
        })

    return chunks


def _chunk_file(filepath: str, source: str) -> List[dict]:
    """Route chunking to the appropriate strategy based on file extension."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".py":
        return chunk_python_source(source, filepath)
    if ext in (".js", ".ts", ".jsx", ".tsx"):
        return chunk_js_ts_source(source, filepath)
    return []


def _fetch_repo_files(owner: str, repo_name: str) -> List[tuple[str, str]]:
    """Fetch all indexable text files from a GitHub repo via PyGithub."""
    github_token = os.getenv("GITHUB_TOKEN")
    g = Github(github_token) if github_token else Github()

    try:
        repo = g.get_repo(f"{owner}/{repo_name}")
    except UnknownObjectException:
        raise ValueError(
            f"Repository not found: {owner}/{repo_name}. "
            "Make sure it is public or provide a GITHUB_TOKEN with access."
        )
    except GithubException as exc:
        raise RuntimeError(f"GitHub API error: {exc.data.get('message', str(exc))}")

    files: List[tuple[str, str]] = []

    def walk_contents(path: str = "") -> None:
        try:
            contents = repo.get_contents(path)
        except GithubException as exc:
            logger.warning("Could not list contents at %s: %s", path, exc)
            return

        if not isinstance(contents, list):
            contents = [contents]

        for item in contents:
            if item.type == "dir":
                walk_contents(item.path)
            elif item.type == "file":
                ext = os.path.splitext(item.name)[1].lower()
                if ext not in INDEXABLE_EXTENSIONS:
                    continue
                if item.size and item.size > MAX_FILE_LINES * 80:
                    # Rough byte-size guard before downloading
                    logger.debug("Skipping large file %s (%d bytes)", item.path, item.size)
                    continue
                try:
                    decoded = item.decoded_content.decode("utf-8", errors="replace")
                except Exception:
                    logger.debug("Skipping binary/unreadable file %s", item.path)
                    continue
                if decoded.count("\n") + 1 > MAX_FILE_LINES:
                    logger.debug("Skipping file > %d lines: %s", MAX_FILE_LINES, item.path)
                    continue
                files.append((item.path, decoded))

    walk_contents()
    logger.info("Fetched %d indexable files from %s/%s", len(files), owner, repo_name)
    return files


def index_repo(repo_url: str) -> dict:
    """
    Index a GitHub repository into ChromaDB.

    Returns {"chunks_indexed": int, "status": "ready"}.
    """
    owner, repo_name = _parse_repo_url(repo_url)
    repo_files = _fetch_repo_files(owner, repo_name)

    all_chunks: List[dict] = []
    for filepath, source in repo_files:
        all_chunks.extend(_chunk_file(filepath, source))

    if not all_chunks:
        logger.warning("No chunks extracted from %s", repo_url)
        return {"chunks_indexed": 0, "status": "ready"}

    embeddings = _get_embeddings()
    collection = _get_chroma_collection()

    # Clear existing index before re-indexing
    try:
        existing_ids = collection.get()["ids"]
        if existing_ids:
            collection.delete(ids=existing_ids)
    except Exception as exc:
        logger.warning("Could not clear existing ChromaDB index: %s", exc)

    documents = [c["content"] for c in all_chunks]
    metadatas = [{
        "file_path": c["file_path"],
        "function_name": c["function_name"],
        "language": c["language"],
        "line_start": c["line_start"],
        "line_end": c["line_end"],
    } for c in all_chunks]
    ids = [f"chunk_{i}" for i in range(len(all_chunks))]

    # Embed in batches to avoid rate limits
    batch_size = 50
    for start in range(0, len(documents), batch_size):
        end = start + batch_size
        batch_docs = documents[start:end]
        batch_meta = metadatas[start:end]
        batch_ids = ids[start:end]
        batch_embeddings = embeddings.embed_documents(batch_docs)
        collection.add(
            ids=batch_ids,
            documents=batch_docs,
            metadatas=batch_meta,
            embeddings=batch_embeddings,
        )

    logger.info("Indexed %d chunks from %s into ChromaDB", len(all_chunks), repo_url)
    return {"chunks_indexed": len(all_chunks), "status": "ready"}


# TODO: Integrate llama-index vector store as an alternative backend per TECH_SPEC_V2.md
