"""
RAG compatibility helpers — safe ChromaDB import with graceful fallback.

ChromaDB 1.x requires Python <=3.13 and onnxruntime; on unsupported environments
import fails and callers proceed without RAG context.
"""

import logging

logger = logging.getLogger(__name__)


def import_chromadb():
    """
    Attempt to import chromadb, returning the module or None on failure.

    Tries a pydantic v2 shim for older chromadb releases before giving up.
    """
    try:
        import chromadb
        return chromadb
    except Exception as first_err:
        logger.debug("chromadb import failed (attempt 1): %s", first_err)

    try:
        import pydantic
        from pydantic_settings import BaseSettings
        pydantic.BaseSettings = BaseSettings
        import chromadb
        return chromadb
    except Exception as second_err:
        logger.debug("chromadb import failed (attempt 2): %s", second_err)
        return None
