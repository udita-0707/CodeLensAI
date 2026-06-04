# CodeLens AI

> AI-powered code review tool — paste raw code or drop a GitHub PR URL and get line-level feedback on bugs, security, style, complexity, and performance.

**Stack:** React + Vite (TanStack Router) · FastAPI · LangChain · OpenRouter (Claude 3.5 Sonnet) · PyGithub

---

## Architecture

```
React UI (Vite :5173)
    │
    ▼
FastAPI (:8000)
    ├── POST /review/code   ← raw snippet → LangChain chain → structured JSON
    ├── POST /review/pr     ← GitHub URL → PyGithub diff → LangChain chain → JSON
    └── GET  /health
```

---

## Quick start

### 1. Backend

```bash
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Copy the env example and fill in your keys
cp .env.example .env
# Edit .env — set OPENROUTER_API_KEY (required) and GITHUB_TOKEN (optional)

# Start the FastAPI server
uvicorn main:app --reload
# → API running at http://localhost:8000
# → Interactive docs at http://localhost:8000/docs
```

### 2. Frontend

```bash
# In a second terminal, from the project root:
npm install
npm run dev
# → App running at http://localhost:5173
```

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | ✅ Yes | Get yours at [openrouter.ai/keys](https://openrouter.ai/keys) |
| `GITHUB_TOKEN` | Optional | GitHub PAT — raises rate limit from 60 → 5 000 req/hr for PR reviews |

---

## API reference

### `GET /health`
```json
{ "status": "ok" }
```

### `POST /review/code`
**Request**
```json
{ "code": "def foo():\n    pass", "language": "Python" }
```
**Response**
```json
{
  "quality_score": 72,
  "summary": "...",
  "issues": [
    {
      "severity": "critical",
      "category": "security",
      "line": 3,
      "description": "SQL injection via string concatenation.",
      "suggestion": "Use parameterized queries."
    }
  ]
}
```

### `POST /review/pr`
**Request**
```json
{ "pr_url": "https://github.com/owner/repo/pull/123" }
```
**Response** — same shape as `/review/code`, extended with:
```json
{
  "pr_title": "Fix auth middleware",
  "pr_url": "https://github.com/owner/repo/pull/123",
  "truncated": false
}
```

> `truncated: true` means the diff exceeded 200 changed lines and was cut. The review still covers the first 200 lines.

---

## File structure

```
CodeLensAI/
├── backend/
│   ├── main.py            # FastAPI app — endpoints + CORS
│   ├── chain.py           # LangChain review chain (OpenRouter via ChatOpenAI)
│   ├── github_client.py   # GitHub PR diff fetcher (PyGithub)
│   ├── requirements.txt
│   └── .env.example
├── src/
│   ├── routes/
│   │   ├── __root.tsx     # Root layout (Toaster lives here)
│   │   ├── index.tsx      # Landing page
│   │   └── app.tsx        # Review dashboard — wired to real API
│   ├── components/
│   │   └── review/
│   │       ├── InputPanel.tsx   # Tab toggle + code editor / PR URL input
│   │       ├── ResultsPanel.tsx # Score badge + filtered issue list
│   │       ├── IssueCard.tsx    # Individual issue card
│   │       └── ScoreBadge.tsx   # Animated score ring
│   └── lib/
│       └── review-data.ts  # TypeScript types + mock data
├── TECH_SPEC.md
└── README.md
```

---

## LLM configuration

The backend uses **OpenRouter** (not the OpenAI API directly). LangChain's `ChatOpenAI` is pointed at `https://openrouter.ai/api/v1` so all model and prompt logic is identical — only the base URL and key differ.

Default model: `anthropic/claude-3.5-sonnet` (set in `backend/chain.py`). You can swap to `openai/gpt-4o` or any other OpenRouter-compatible model.
