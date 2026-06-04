# AI Code Review Dashboard — Tech Spec

**v1.0 · 1-day build · Internship project for CodeRabbit**

**Stack:** Python · FastAPI · React · LangChain · OpenRouter API

---

## 1. Problem & Goal

A full-stack AI tool that accepts a GitHub PR URL or raw code snippet, runs an LLM-powered review chain, and renders structured feedback — categorised by severity — in a clean React dashboard.

This directly mirrors CodeRabbit's core product, demonstrating both AI engineering depth and full-stack execution ability.

---

## 2. System Architecture

```
React UI  →  FastAPI  →  LangChain review chain  →  OpenRouter API (Claude / GPT-4o)
                ↕
          GitHub REST API (PyGithub — PR diff fetch)
```

| Layer | Responsibility |
|---|---|
| React UI | Input panel + results dashboard |
| FastAPI | Request routing, GitHub diff fetch, response orchestration |
| LangChain | Prompt template, LLM call, Pydantic output parser, retry logic |
| OpenRouter API | LLM inference (model: `anthropic/claude-3.5-sonnet`) |

---

## 3. Tech Stack

### Frontend

| Layer | Technology | Reason |
|---|---|---|
| Framework | React + Vite | Fast dev server, minimal config |
| Styling | Tailwind CSS | Rapid UI, consistent design |
| Code display | Prism.js | Syntax highlighting in review panel |
| HTTP client | Axios | Clean async API calls |

### Backend

| Layer | Technology | Reason |
|---|---|---|
| Framework | FastAPI | Async, typed, auto-docs |
| AI chain | LangChain | Prompt templates + output parsing |
| LLM provider | OpenRouter API | Access to Claude/GPT-4o without direct API keys |
| GitHub | PyGithub | PR diff fetch with one method call |
| Validation | Pydantic v2 | Typed models + LLM output validation |

### LLM Configuration (OpenRouter)

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="anthropic/claude-3.5-sonnet",
    temperature=0,
    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    openai_api_base="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "CodeLens AI"
    }
)
```

---

## 4. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/review/code` | Accepts raw code string → returns review JSON |
| POST | `/review/pr` | Accepts GitHub PR URL → fetches diff → returns review JSON |
| GET | `/health` | Service health check |

### Request bodies

**POST /review/code**
```json
{
  "code": "string",
  "language": "string"
}
```

**POST /review/pr**
```json
{
  "pr_url": "https://github.com/owner/repo/pull/123"
}
```

---

## 5. Review Response Schema

The LangChain chain is prompted to return only valid JSON matching this structure:

| Field | Type | Description |
|---|---|---|
| `quality_score` | int (0–100) | Overall code quality rating |
| `summary` | string | 1–2 sentence plain-English overview |
| `issues[]` | array | List of detected issues |
| `issues[].severity` | enum | `critical` · `warning` · `info` |
| `issues[].category` | enum | `bug` · `security` · `style` · `complexity` · `perf` |
| `issues[].line` | int \| null | Line number in diff (if applicable) |
| `issues[].description` | string | Human-readable explanation of the issue |
| `issues[].suggestion` | string | Concrete fix recommendation |

### Pydantic models

```python
from pydantic import BaseModel
from typing import List, Optional, Literal

class Issue(BaseModel):
    severity: Literal["critical", "warning", "info"]
    category: Literal["bug", "security", "style", "complexity", "perf"]
    line: Optional[int]
    description: str
    suggestion: str

class ReviewResult(BaseModel):
    quality_score: int  # 0–100
    summary: str
    issues: List[Issue]
```

---

## 6. LangChain Review Chain Design

### Chain steps

1. **Input formatting** — wrap code in a structured prompt template with language hint and line-numbered context.
2. **LLM call** — OpenRouter (Claude 3.5 Sonnet) with system prompt instructing structured JSON output. Temperature = 0.
3. **Output parser** — `PydanticOutputParser` validates and parses JSON into typed models.
4. **Fallback** — retry once with a stricter prompt if parsing fails. On second failure, return `500` with a readable error message.

### System prompt

```
You are an expert code reviewer at a top-tier software engineering company.

Review the provided code and return ONLY valid JSON — no markdown fences, no preamble, no explanation outside the JSON object.

Rules:
- Review for bugs, security vulnerabilities, style violations, and code complexity.
- Include line numbers wherever possible — line-level feedback is the most valuable output.
- Do not hallucinate fixes you are not certain about.
- Return JSON matching the exact schema provided.
```

---

## 7. Frontend UI Components

| Component | Spec |
|---|---|
| Input panel | Tab toggle: "Paste Code" / "GitHub PR URL". Language selector dropdown. Submit button with loading spinner. |
| Score badge | Circular score 0–100. Green ≥ 80, Amber 50–79, Red < 50. Animate count-up on load. |
| Issue cards | Color-coded left border by severity. Category pill + line number tag. Expandable suggestion section on click. |
| Filter bar | Toggle chips by severity or category. Issue count badge per filter. |
| Code panel | Prism.js syntax-highlighted code. Highlighted line(s) on issue card hover. |

---

## 8. File Structure

```
codelens-ai/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── InputPanel.jsx
│   │   │   ├── ScoreBadge.jsx
│   │   │   ├── IssueCard.jsx
│   │   │   └── FilterBar.jsx
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── backend/
│   ├── main.py          # FastAPI app + endpoints
│   ├── chain.py         # LangChain review chain
│   ├── github_client.py # GitHub PR diff fetcher
│   ├── requirements.txt
│   └── .env.example
├── TECH_SPEC.md
└── README.md
```

---

## 9. Environment Variables

```bash
# backend/.env
OPENROUTER_API_KEY=your_openrouter_key_here
GITHUB_TOKEN=your_github_token_here   # optional — raises rate limit from 60 to 5000 req/hr
```

### requirements.txt

```
fastapi
uvicorn
langchain
langchain-openai
pydantic
PyGithub
python-dotenv
httpx
```

---

## 10. Risks & Mitigations

| Severity | Risk | Mitigation |
|---|---|---|
| HIGH | LLM returns malformed JSON | `PydanticOutputParser` + one retry with stricter prompt. Fallback to plain-text display. |
| MED | GitHub API rate limit hit | Cache PR diff in memory per session. Show warning if unauthenticated (60 req/hr limit). |
| MED | Large PR diff exceeds context window | Truncate to first 200 changed lines. Add `truncated: true` flag in response. |
| LOW | CORS errors in local dev | Add `CORSMiddleware` allowing `localhost:5173` on FastAPI startup. |

---

## 11. Stretch Goals

- **Inline diff view** — show the actual PR diff with issue annotations inline, mirroring CodeRabbit's real UI.
- **Review history** — store past reviews in localStorage so scores can be compared across runs.
- **Language auto-detection** — detect language from file extension in the PR diff and pass it to the prompt.
- **Severity breakdown chart** — doughnut chart showing issue count by category.

---

> **The single detail that will impress CodeRabbit most:** line-level feedback displayed on the actual code. Line-level annotation is CodeRabbit's core differentiator — shipping it signals you understand their product deeply.
