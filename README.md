# AgentForge

**Multi-Agent AI Software Development Platform** — locally runnable with zero per-token LLM charges.

AgentForge coordinates a team of specialized AI agents (Requirements Analyst, System Architect,
Task Planner, Software Developer, QA Engineer, Security Engineer, and Code Reviewer) to transform
natural-language requirements into a designed, implemented, tested, and reviewed software project.

All inference runs locally via [Ollama](https://ollama.com) — no cloud API keys required.

---

## Requirements

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | Tested on 3.11.9 |
| Ollama | 0.40+ | Must be running locally |
| Node.js | 18+ | For the frontend (Phase 4) |
| Git | Any | For project branch management |
| Docker | Optional | For code execution sandboxing |

**Hardware:** 16 GB RAM recommended. No GPU required.

---

## Quick Start (Windows)

### 1. Install and start Ollama

Download from https://ollama.com/download/windows and install.

Pull the required model:

```powershell
ollama pull qwen2.5-coder:7b
ollama list   # verify it appears
```

### 2. Clone the repository

```powershell
git clone <repo-url> agentforge
cd agentforge
```

### 3. Configure the backend

```powershell
cd backend
copy .env.example .env
# Edit .env if you need to change ports or model settings
```

### 4. Install backend dependencies

```powershell
# From agentforge/backend/
python -m pip install fastapi uvicorn[standard] pydantic pydantic-settings sqlalchemy aiosqlite httpx python-multipart
```

Or install all at once from the pyproject.toml:

```powershell
python -m pip install -e ".[dev]"
```

### 5. Start the backend

```powershell
# From agentforge/backend/
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000/api/v1
- **Interactive docs**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/api/v1/health
- **Ollama status**: http://localhost:8000/api/v1/health/ollama

---

## Running Tests

```powershell
# From agentforge/backend/
python -m pytest tests/ -v
```

Tests use in-memory SQLite — **Ollama does not need to be running** for the unit test suite.

Run with coverage:

```powershell
python -m pytest tests/ -v --cov=app --cov-report=term-missing
```

Run only integration tests (requires live Ollama):

```powershell
python -m pytest tests/ -m ollama -v
```

---

## Linting and Formatting

```powershell
# Check linting
python -m ruff check app/ tests/

# Auto-fix linting issues
python -m ruff check --fix app/ tests/

# Format code
python -m ruff format app/ tests/
```

---

## Environment Variables

See [`backend/.env.example`](backend/.env.example) for all configurable settings.

Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | LLM to use for all agents |
| `OLLAMA_NUM_CTX` | `4096` | Model context window (tokens) |
| `MAX_CONCURRENT_LLM_REQUESTS` | `1` | Concurrent inference limit |
| `MAX_REPAIR_ATTEMPTS` | `3` | Max automated bug repair cycles |
| `DATABASE_URL` | `sqlite+aiosqlite:///./agentforge.db` | Database connection string |
| `APP_ENV` | `development` | `development` \| `production` \| `test` |

---

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for a full design overview.

```
agentforge/
├── backend/
│   ├── app/
│   │   ├── main.py           ← FastAPI app factory
│   │   ├── config.py         ← Pydantic Settings
│   │   ├── database/         ← SQLAlchemy engine, init, ORM models
│   │   ├── models/           ← Database ORM models
│   │   ├── schemas/          ← Pydantic request/response schemas
│   │   ├── api/v1/           ← REST endpoints
│   │   └── services/         ← Ollama service, LLM client (Phase 3)
│   └── tests/                ← pytest test suite
├── workspace/projects/       ← Generated project files (gitignored)
└── docs/                     ← Architecture and development docs
```

---

## Security Notes

- **No code is executed autonomously.** Code execution features require Docker (Phase 5) and
  human approval for destructive operations.
- **Docker is not installed** on this machine — code sandbox features will be disabled until
  Docker is available.
- **No secrets** are committed to the repository. Use `.env` (gitignored).
- **Ollama runs locally** — no data leaves your machine during inference.
- Stack traces are never exposed in API responses.

---

## Troubleshooting

### "Ollama is not reachable"

1. Check Ollama is running: open Task Manager or run `ollama list`
2. Start Ollama: search for Ollama in Start Menu, or run `ollama serve`
3. Verify the port: `Test-NetConnection localhost -Port 11434`

### "Model 'qwen2.5-coder:7b' is not available"

```powershell
ollama pull qwen2.5-coder:7b
```

### Port 8000 already in use

Change `APP_PORT` in `.env` and restart the backend.

### pip install fails (Application Control policy)

Your organisation's application control policy may block scripts in venv directories.
Use system Python directly: `python -m pip install ...`

---

### 6. Start the frontend

```powershell
# In another terminal, from agentforge/frontend/
npm run dev
```

The frontend dashboard will be available at:
- **Dashboard**: http://localhost:3000

---

## Development Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ Complete | Environment inspection, planning |
| Phase 2 | ✅ Complete | FastAPI backend, SQLite, health checks, tests |
| Phase 3 | ✅ Complete | Ollama client, agent definitions, workflow state machine, workflow APIs & tests |
| Phase 4 | ✅ Complete | React + Vite + TypeScript frontend, SSE real-time dashboard |
| Phase 5 | ⏳ Pending | Autonomous workspace execution, git branch management |
| Phase 6 | ⏳ Pending | QA testing execution, security scanners, automated repair loops |
| Phase 7 | ⏳ Pending | End-to-end integration tests & validation |

---

## License

For local development use only. See project documentation for terms.
