# CodeLens AI — v3 Tech Spec

**GitHub App Integration + Live Deployment**
`GitHub App · Webhooks · Octokit · Railway · Vercel · Docker`

> This is the version that makes CodeRabbit recruiters stop scrolling.
> You are building a simplified version of their actual product.

---

## What v3 adds

| | v2 | v3 |
|---|---|---|
| How it's triggered | Manual paste / URL input | Automatic on every PR opened |
| Where results appear | CodeLens dashboard | Inline GitHub PR review comments |
| Deployment | localhost only | Live on Railway + Vercel |
| GitHub integration | PyGithub (read-only) | GitHub App (read + write) |
| Demo | Screenshot | Real PR with bot comments visible |
| Recruiter signal | "built an AI tool" | "built what CodeRabbit does" |

---

## How it works (end-to-end)

```
Developer opens a PR on GitHub
        │
        ▼
GitHub sends webhook → POST /webhook on Railway
        │
        ▼
FastAPI verifies webhook signature (HMAC-SHA256)
        │
        ▼
Extract PR diff via GitHub App installation token
        │
        ▼
LangGraph multi-agent review (v2 agents)
        │
        ▼
Post results as inline PR review comments via GitHub API
        │
        ▼
Developer sees CodeLens AI review directly in their PR
```

---

## Phase 1 — GitHub App setup (Day 1)

### What is a GitHub App?

A GitHub App is an OAuth application that:
- Gets installed on a GitHub repo or org
- Receives webhook events (PR opened, PR updated, push)
- Has its own identity — comments appear as `codelens-ai[bot]`
- Uses short-lived installation tokens (not your personal PAT)

### Create the GitHub App

1. Go to `github.com/settings/apps/new`
2. Fill in:
   - **App name:** `CodeLens AI`
   - **Homepage URL:** your Vercel frontend URL
   - **Webhook URL:** `https://your-railway-app.up.railway.app/webhook`
   - **Webhook secret:** generate a random string, save it as `GITHUB_WEBHOOK_SECRET`
3. **Permissions needed:**
   - Pull requests: Read & Write
   - Contents: Read
4. **Subscribe to events:**
   - Pull request (opened, synchronize, reopened)
5. Generate and download a **private key** (`.pem` file) — save as `GITHUB_APP_PRIVATE_KEY`
6. Note your **App ID** — save as `GITHUB_APP_ID`

### Environment variables added in v3

```bash
# backend/.env
OPENROUTER_API_KEY=your_openrouter_key_here
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n..."
GITHUB_WEBHOOK_SECRET=your_random_secret_here
CHROMA_PERSIST_DIR=./chroma_db
```

---

## Phase 2 — Webhook handler (Day 1–2)

### New file: `backend/webhook.py`

```python
import hmac
import hashlib
from fastapi import Request, HTTPException

async def verify_webhook_signature(request: Request, secret: str) -> dict:
    """Verify GitHub webhook HMAC-SHA256 signature."""
    signature = request.headers.get("X-Hub-Signature-256", "")
    body = await request.body()

    expected = "sha256=" + hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    return await request.json()
```

### New endpoint in `backend/main.py`

```python
@app.post("/webhook")
async def github_webhook(request: Request):
    payload = await verify_webhook_signature(
        request,
        os.getenv("GITHUB_WEBHOOK_SECRET")
    )

    event = request.headers.get("X-GitHub-Event")

    # Only process pull_request events
    if event != "pull_request":
        return {"status": "ignored"}

    action = payload.get("action")
    if action not in ["opened", "synchronize", "reopened"]:
        return {"status": "ignored"}

    # Extract PR info
    pr_number  = payload["pull_request"]["number"]
    repo_name  = payload["repository"]["full_name"]
    install_id = payload["installation"]["id"]

    # Run review in background (don't block webhook response)
    background_tasks.add_task(
        run_pr_review,
        repo_name=repo_name,
        pr_number=pr_number,
        install_id=install_id
    )

    return {"status": "review queued"}
```

> **Why background tasks?** GitHub expects a webhook response within 10 seconds. LLM review takes 15–30 seconds. Use FastAPI `BackgroundTasks` to respond immediately and run the review async.

---

## Phase 3 — GitHub App client (Day 2)

### New file: `backend/github_app.py`

```python
import time
import jwt
import httpx
from github import Github, GithubIntegration

def get_installation_token(install_id: int) -> str:
    """Generate a short-lived installation access token."""
    app_id = os.getenv("GITHUB_APP_ID")
    private_key = os.getenv("GITHUB_APP_PRIVATE_KEY")

    # Create JWT for GitHub App authentication
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + (10 * 60),  # 10 min expiry
        "iss": app_id
    }
    jwt_token = jwt.encode(payload, private_key, algorithm="RS256")

    # Exchange JWT for installation token
    integration = GithubIntegration(app_id, private_key)
    token = integration.get_access_token(install_id)
    return token.token


def get_pr_diff(repo_name: str, pr_number: int, token: str) -> str:
    """Fetch PR diff using installation token."""
    g = Github(token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    # Get changed files with patches
    files = pr.get_files()
    diff_parts = []
    total_lines = 0

    for f in files:
        if total_lines >= 200:  # context window guard
            break
        if f.patch:
            diff_parts.append(f"--- {f.filename} ---\n{f.patch}")
            total_lines += f.patch.count('\n')

    return "\n\n".join(diff_parts)


def post_review_comments(
    repo_name: str,
    pr_number: int,
    token: str,
    result: dict
) -> None:
    """Post inline review comments + summary review on the PR."""
    g = Github(token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    # Build review body (summary + score)
    score = result["quality_score"]
    emoji = "🟢" if score >= 80 else "🟡" if score >= 50 else "🔴"
    body = f"""## CodeLens AI Review {emoji}

**Quality Score: {score}/100**

{result['summary']}

---
*Reviewed by [CodeLens AI](https://your-app.vercel.app) · {len(result['issues'])} issue(s) found*
"""

    # Determine review event based on severity
    has_critical = any(i["severity"] == "critical" for i in result["issues"])
    review_event = "REQUEST_CHANGES" if has_critical else "COMMENT"

    # Create the review with inline comments
    comments = []
    for issue in result["issues"]:
        if issue.get("line"):
            comments.append({
                "path": issue.get("file", ""),   # file path from diff
                "line": issue["line"],
                "body": format_issue_comment(issue)
            })

    pr.create_review(
        body=body,
        event=review_event,
        comments=comments if comments else []
    )


def format_issue_comment(issue: dict) -> str:
    """Format a single issue as a GitHub review comment."""
    severity_emoji = {
        "critical": "🔴",
        "warning":  "🟡",
        "info":     "🔵"
    }
    cat_emoji = {
        "bug":        "🐛",
        "security":   "🔒",
        "style":      "✨",
        "complexity": "🧩",
        "perf":       "⚡"
    }
    sev  = issue["severity"]
    cat  = issue["category"]
    return f"""{severity_emoji.get(sev, '●')} **{sev.upper()}** · {cat_emoji.get(cat, '')} {cat}

{issue['description']}

**Suggested fix:**
{issue['suggestion']}
"""
```

---

## Phase 4 — Wire everything together (Day 3)

### Updated `backend/main.py` flow

```python
async def run_pr_review(repo_name: str, pr_number: int, install_id: int):
    """Full review pipeline triggered by webhook."""

    # 1. Get installation token
    token = get_installation_token(install_id)

    # 2. Fetch PR diff
    diff = get_pr_diff(repo_name, pr_number, token)

    # 3. Run LangGraph multi-agent review (v2)
    result = await run_agent_graph(code=diff, language="auto")

    # 4. Post review comments back to PR
    post_review_comments(repo_name, pr_number, token, result)
```

### New endpoints summary (v3 adds)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/webhook` | GitHub webhook receiver |
| GET | `/webhook/health` | Confirm webhook is reachable |
| GET | `/app/installations` | List repos where app is installed |

---

## Phase 5 — Deployment (Day 4)

### Backend → Railway

Railway is the easiest free deployment for FastAPI + persistent storage (ChromaDB).

**Steps:**
1. Create `backend/Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

2. Push to GitHub
3. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
4. Set all env vars in Railway dashboard
5. Railway gives you a URL: `https://codelens-ai.up.railway.app`
6. Update your GitHub App webhook URL to this Railway URL

### Frontend → Vercel

1. Push frontend to GitHub
2. Go to [vercel.com](https://vercel.com) → New Project → Import repo
3. Set environment variable: `VITE_API_URL=https://codelens-ai.up.railway.app`
4. Deploy — Vercel gives you `https://codelens-ai.vercel.app`

### Update frontend API calls

```javascript
// frontend/src/config.js
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
export default API_URL;
```

---

## Phase 6 — Demo setup (Day 5)

### Create a demo repo

1. Create a public GitHub repo: `codelens-ai-demo`
2. Install your CodeLens GitHub App on it
3. Add intentionally bad code with known issues:
   - SQL injection vulnerability
   - Hardcoded API key
   - N+1 query
   - Missing error handling
4. Open a PR with this bad code
5. Watch CodeLens AI post inline comments automatically
6. Screenshot / record a GIF of the review comments

### README demo section

```markdown
## Demo

![CodeLens AI reviewing a PR](./assets/demo.gif)

CodeLens AI automatically reviews this PR and posts inline comments:
- 🔴 CRITICAL · security — SQL injection on line 14
- 🟡 WARNING · perf — N+1 query in loop on line 28
- 🔵 INFO · style — Unused import on line 3

[Try it on your repo →](https://codelens-ai.vercel.app)
```

---

## Complete v3 File Structure

```
codelens-ai/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── InputPanel.jsx
│   │   │   ├── ScoreBadge.jsx
│   │   │   ├── IssueCard.jsx
│   │   │   ├── FilterBar.jsx
│   │   │   └── AgentStatus.jsx
│   │   ├── config.js                ← NEW: API URL config
│   │   ├── App.jsx
│   │   └── main.jsx
│   └── package.json
│
├── backend/
│   ├── main.py                      # FastAPI app (updated)
│   ├── webhook.py                   # Webhook handler + signature verification ← NEW
│   ├── github_app.py                # GitHub App client + comment posting       ← NEW
│   ├── graph.py                     # LangGraph StateGraph (v2)
│   ├── agents/
│   │   ├── reviewer.py
│   │   ├── security.py
│   │   └── explainer.py
│   ├── rag/
│   │   ├── indexer.py
│   │   └── retriever.py
│   ├── eval/
│   │   ├── judge.py
│   │   ├── test_cases.py
│   │   └── run_eval.py
│   ├── github_client.py             # v1 PR diff fetcher (kept)
│   ├── chain.py                     # v1 chain (kept for reference)
│   ├── Dockerfile                   ← NEW
│   ├── requirements.txt             # updated
│   └── .env.example                 # updated
│
├── assets/
│   └── demo.gif                     ← NEW: record after deployment
│
├── TECH_SPEC.md
├── TECH_SPEC_V2.md
├── TECH_SPEC_V3.md                  ← this file
└── README.md                        # updated with demo GIF + live links
```

---

## requirements.txt (v3 additions)

```
# v1 + v2 deps (unchanged)
fastapi
uvicorn
langchain
langchain-openai
langgraph
llama-index
llama-index-vector-stores-chroma
chromadb
pydantic
PyGithub
python-dotenv
httpx
gitpython

# v3 additions
PyJWT                  # GitHub App JWT generation
cryptography           # RSA key handling for GitHub App
```

---

## Security checklist

```
☐ Webhook signature verified on every request (HMAC-SHA256)
☐ Installation tokens used (not personal PAT)
☐ Tokens never logged or exposed in responses
☐ Private key stored as env var, never committed to git
☐ .env in .gitignore
☐ Webhook secret rotated before going public
```

---

## Final resume bullets (v3)

Add to the CodeLens AI project entry:

> *"Shipped CodeLens AI as a GitHub App — webhook-triggered multi-agent reviews post inline PR comments automatically on every opened PR, mirroring CodeRabbit's core product architecture."*

> *"Deployed full-stack system on Railway (FastAPI + LangGraph backend) and Vercel (React frontend) with HMAC-SHA256 webhook verification and short-lived GitHub App installation tokens."*

---

## Complete shortlist probability after v3

| Version | What you have | Shortlist probability |
|---|---|---|
| v1 | LLM pipeline + React UI | 55% |
| v2 | Multi-agent + RAG + eval | 70% |
| **v3** | **GitHub App + deployed + demo** | **80–85%** |

---

## Build order (strict)

```
Day 1 AM  →  Create GitHub App on github.com, save all credentials
Day 1 PM  →  Implement webhook.py (signature verification + event routing)
Day 2 AM  →  Implement github_app.py (installation token + diff fetch)
Day 2 PM  →  Implement post_review_comments(), test locally with ngrok
Day 3 AM  →  Wire webhook → LangGraph graph → post_review_comments()
Day 3 PM  →  End-to-end test: open a real PR, watch bot comment appear
Day 4 AM  →  Write Dockerfile, test container locally
Day 4 PM  →  Deploy backend to Railway, set all env vars, update webhook URL
Day 5 AM  →  Deploy frontend to Vercel, update VITE_API_URL
Day 5 PM  →  Record demo GIF, update README, push final version
```

### Testing locally before Railway (use ngrok)

GitHub can't reach `localhost` — use ngrok to expose your local server
during development:

```bash
# Install ngrok (free tier is enough)
brew install ngrok   # or download from ngrok.com

# Expose your local FastAPI server
ngrok http 8000

# Copy the https URL (e.g. https://abc123.ngrok.io)
# Paste it as your GitHub App webhook URL temporarily
```

---

> **The single thing that will make a CodeRabbit recruiter forward your resume:**
> A link to a real GitHub PR where `codelens-ai[bot]` has posted inline review comments.
> That is their product. You built it. That conversation ends with an interview.
