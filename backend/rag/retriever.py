"""
Semantic retrieval over indexed codebase chunks stored in ChromaDB.

Queries ChromaDB for the top-k most similar code chunks to a given query string.
Degrades gracefully when ChromaDB is empty or unavailable.
"""

import logging
import os
from typing import List

from dotenv import load_dotenv

from rag.compat import import_chromadb

load_dotenv()

logger = logging.getLogger(__name__)

COLLECTION_NAME = "codelens_codebase"
DEFAULT_TOP_K = 5


def _get_chroma_collection():
    """Return the ChromaDB collection, or None if unavailable."""
    persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    try:
        chromadb = import_chromadb()
        if chromadb is None:
            return None, None

        from langchain_openai import OpenAIEmbeddings

        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            logger.warning("OPENROUTER_API_KEY not set — RAG retrieval skipped")
            return None, None

        client = chromadb.PersistentClient(path=persist_dir)
        collection = client.get_or_create_collection(name=COLLECTION_NAME)

        embeddings = OpenAIEmbeddings(
            model=os.getenv("OPENROUTER_EMBEDDING_MODEL", "openai/text-embedding-3-small"),
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "http://localhost:5173",
                "X-Title": "CodeLens AI v2",
            },
        )
        return collection, embeddings
    except Exception as exc:
        logger.warning("ChromaDB unavailable — proceeding without RAG context: %s", exc)
        return None, None


def retrieve_similar_chunks(code: str, top_k: int = DEFAULT_TOP_K) -> List[dict]:
    """
    Query ChromaDB for the top-k most semantically similar code chunks.

    Returns a list of dicts with ``content`` and ``metadata`` keys.
    Returns an empty list if the index is empty or retrieval fails.
    """
    collection, embeddings = _get_chroma_collection()
    if collection is None or embeddings is None:
        return []

    try:
        if collection.count() == 0:
            logger.info("ChromaDB collection is empty — no RAG context")
            return []

        query_embedding = embeddings.embed_query(code)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas"],
        )

        chunks: List[dict] = []
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        for doc, meta in zip(documents, metadatas):
            chunks.append({
                "content": doc,
                "metadata": meta or {},
            })

        logger.info("Retrieved %d similar chunks from ChromaDB", len(chunks))
        return chunks
    except Exception as exc:
        logger.warning("RAG retrieval failed — proceeding without context: %s", exc)
        return []


def format_chunks_for_prompt(chunks: List[dict]) -> str:
    """Format retrieved chunks as context for the reviewer prompt."""
    if not chunks:
        return ""

    lines = ["Similar patterns in this codebase:"]
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        file_path = meta.get("file_path", "unknown")
        func_name = meta.get("function_name", "unknown")
        lang = meta.get("language", "unknown")
        line_start = meta.get("line_start", "?")
        line_end = meta.get("line_end", "?")
        lines.append(
            f"\n--- Chunk {i}: {file_path} :: {func_name} "
            f"({lang}, lines {line_start}-{line_end}) ---"
        )
        lines.append(chunk.get("content", ""))
    return "\n".join(lines)
