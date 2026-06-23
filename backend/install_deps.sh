#!/usr/bin/env bash
# Staged dependency install — avoids pip "resolution-too-deep" on the full graph.
set -euo pipefail

cd "$(dirname "$0")"

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip

echo "==> Core API + LangGraph"
pip install fastapi uvicorn langchain langchain-openai langgraph pydantic PyGithub python-dotenv httpx gitpython

echo "==> ChromaDB (RAG vector store)"
pip install chromadb

echo "==> LlamaIndex (optional RAG backend — not yet wired)"
pip install llama-index llama-index-vector-stores-chroma || {
  echo "WARNING: llama-index install failed — RAG still works via ChromaDB directly."
}

echo "==> Done. Activate with: source .venv/bin/activate"
