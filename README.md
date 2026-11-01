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

### 6. Start the frontend dashboard

```powershell
# In another terminal, from agentforge/frontend/
npm run dev
```

The frontend dashboard will be available at:
- **Dashboard UI**: http://localhost:3000

---

## Specialized Agent Team

AgentForge deploys 7 specialized agents cooperating through human-in-the-loop review gates:

| # | Agent | Role | Output Artifacts |
|---|-------|------|-------------------|
| 1 | **Requirements Analyst** | Acceptance criteria, functional & non-functional requirements | `requirements.md`, user stories |
| 2 | **System Architect** | Modular design, DB schemas, API specs, boundaries | `architecture.md`, `api_spec.yaml` |
| 3 | **Task Planner** | Work breakdown into atomic tasks with dependencies | Task board, implementation order |
| 4 | **Software Developer** | Modular code generation & unit test fixtures | Source code files, unit tests |
| 5 | **QA Engineer** | Verification, edge-case testing, repro steps | `test_plan.md`, `test_report.md` |
| 6 | **Security Engineer** | Secret detection, OWASP audits, input validation | `security_report.md` |
| 7 | **Code Reviewer** | Independent quality governance, style & acceptance check | Code review summary & approvals |

---

## Advanced Logs & Monitoring Center

AgentForge features an enterprise-grade Observability & Security Operations Center (SOC) dashboard designed for monitoring multi-agent software engineering workflows in real time:

- **SOC Health & Summary Command Bar:** Live system health indicators (Ollama connection, backend status, active model, DB health, running workflows) and metrics for total events, successes, warnings, errors, and critical security alerts.
- **Developer Live Terminal Stream:** High-density `#070A10` terminal with millisecond-precision timestamps, colored log-level badges (`INFO`, `AGENT`, `TOOL`, `SUCCESS`, `WARNING`, `ERROR`, `CRITICAL`), pause/resume auto-scroll, unread event indicators, and an interactive slide-over event inspector drawer.
- **Agent Activity Monitor:** Real-time state tracking (`IDLE`, `RUNNING`, `COMPLETED`, `FAILED`), active task assignments, duration timers, and task history across all 7 agents.
- **LLM Intelligence Monitor:** Local inference telemetry tracking request durations, token counts (eval/prompt tokens), context window sizing, model status, and prompt/response inspection.
- **Tool & Execution Activity:** Comprehensive logs of file operations (read/write/edit), Git operations, test runners, and process exit codes.
- **Incident & Bug Intelligence:** Automated defect discovery records with severity levels, reproduction steps, affected files, and repair attempt histories.
- **Security Event Monitor:** Vulnerability audit trails, AST security checks, and secret scanner detections with automated redaction.
- **Multi-Format Log Exporter:** Instant export of filtered logs to JSON, CSV, Markdown, or plain text formats.
- **Context-Aware Correlation & Redaction:** Distributed trace IDs (`trace_id`, `span_id`) with automatic redaction of AWS keys, GitHub PATs, JWTs, and private credentials.

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
│   │   ├── logging/          ← EventService, correlation IDs, secret redaction
│   │   ├── models/           ← Database ORM models
│   │   ├── schemas/          ← Pydantic request/response schemas
│   │   ├── api/v1/           ← REST endpoints & /monitoring/ router
│   │   └── services/         ← Ollama service, agent runners, workflow orchestrator
│   └── tests/                ← pytest test suite (218 tests)
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── monitoring/   ← LiveTerminal, AgentActivityGrid, LLMMonitorPanel, etc.
│   │   │   └── ...           ← Workspace, AgentCards, ProjectList, ReviewPanel
│   │   ├── services/         ← API client & SSE stream connectors
│   │   └── types/            ← TypeScript domain & monitoring schemas
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

## Testing

The platform includes a comprehensive automated test suite with **218 passing tests**:

```powershell
# From agentforge/backend/
python -m pytest tests/ -v
```

Test Breakdown:
- `tests/test_config.py` (17 tests) — configuration & environment isolation
- `tests/test_health.py` (11 tests) — health, Ollama availability, model detection
- `tests/test_projects.py` (39 tests) — project CRUD, tasks, approval gates, pagination
- `tests/test_workspace.py` (16 tests) — workspace filesystem isolation, Git branches, execution runner, path traversal defense
- `tests/test_qa_security.py` (16 tests) — QA test discovery/execution, deterministic security scanner, secret patterns
- `tests/test_workflow.py` (32 tests) — workflow state machine, agent invocations, approval gates, SSE events
- `tests/test_integration.py` (39 tests) — Phase 7 end-to-end integration across all subsystems
- `tests/test_monitoring.py` (19 tests) — Advanced Monitoring Center, event stream filtering, telemetry, redaction & log export
- `tests/test_terminal.py` (15 tests) — Terminal sessions, command policy enforcement, workspace isolation, SSE streaming, history, process management, export
- `tests/test_integrations.py` (14 tests) — Free developer services integrations (GitHub, Actions, Semgrep, Gitleaks, Trivy, OpenObserve, Bugsink, Better Stack, Cloudflare, Backblaze B2, RBAC)

Linting:
```powershell
python -m ruff check app/ tests/
```

---

## Development Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ Complete | Environment inspection, architecture design, and project planning |
| Phase 2 | ✅ Complete | FastAPI backend, SQLite persistence, health checks, project CRUD |
| Phase 3 | ✅ Complete | Ollama client, 7 specialized agents, workflow state machine, SSE endpoints |
| Phase 4 | ✅ Complete | React + Vite + TypeScript frontend, real-time SSE dashboard, approval gates |
| Phase 5 | ✅ Complete | Workspace filesystem isolation, Git branch management, sandboxed execution runner |
| Phase 6 | ✅ Complete | Automated QA runner, deterministic security scanner, repair loop, QA/Security UI |
| Phase 7 | ✅ Complete | End-to-end integration testing (39 integration tests, 170 total passed, 0 lint errors) |
| Phase 8 | ✅ Complete | Advanced Logs & Monitoring Center (SOC dashboard, developer terminal stream, LLM & tool monitors, security audits, log export) |
| Phase 9 | ✅ Complete | Integrated Terminal & Execution Center (real PowerShell execution, SSE streaming, multi-tab sessions, agent identity branding, command policy engine, workspace isolation, 204 total tests) |
| Phase 10 | ✅ Complete | Free Developer Services Integration (GitHub, GitHub Actions CI, Semgrep SAST, Gitleaks, Trivy, OpenObserve, Bugsink, Better Stack, Cloudflare, Backblaze B2, RBAC, 218 total tests) |

---

## Terminal & Execution Center

AgentForge ships a fully functional integrated terminal (`Terminal & Exec` button in the header).

### Features

- **Real command execution** — PowerShell commands execute as actual subprocesses; stdout/stderr stream via SSE in real time
- **Multi-tab sessions** — 5 preset sessions per project (Main Terminal, Developer Agent, QA Execution, Security Scanner, Git Operations); unlimited user-created sessions up to the configurable maximum
- **Agent identity** — commands submitted by AI agents are tagged with the agent name, project ID, task ID, and trace ID, so each execution is traceable to the originating agent
- **Command Policy Engine** — blocked patterns (e.g. `rm -rf /`, `format C:`, fork bombs) are rejected before spawning; confirmation patterns (e.g. `git push --force`) surface a warning
- **Workspace boundary enforcement** — processes cannot escape the project workspace directory; path traversal is detected and rejected
- **Credential redaction** — secrets matching known patterns are redacted from all streamed output
- **Docker detection** — reports Docker availability accurately; does not silently fall back or pretend container isolation is available when it is not
- **Split terminal** — view two sessions side-by-side
- **Specialized consoles** — collapsible bottom panel with Build / QA / Security / Git sub-tabs showing filtered command history
- **Command Inspector Drawer** — right-side panel with stdout, stderr, and JSON metadata tabs, plus a "View in Logs Center" link that carries the trace ID to the Monitoring Center
- **Command History Panel** — searchable, filterable history of all executions in the session
- **Process Monitor** — live list of running PIDs with duration, agent label, and Stop button
- **Export modal** — download session output as TXT, Markdown, or JSON

### Backend modules

| Module | Description |
|--------|-------------|
| `app/terminal/command_policy.py` | `CommandPolicyEngine` — blocked/confirmation pattern matching, `CommandCategory` enum |
| `app/terminal/terminal_security.py` | `TerminalSecurity` — env sanitization, cwd boundary check, credential redaction, Docker detection |
| `app/terminal/terminal_schemas.py` | Pydantic schemas for sessions, commands, processes, events, export |
| `app/terminal/process_manager.py` | Async `ProcessManager` — subprocess lifecycle, stdout/stderr streaming, timeout, cancellation |
| `app/terminal/session_manager.py` | `SessionManager` — in-memory ring buffer, SSE fan-out subscriber queues |
| `app/terminal/terminal_service.py` | `TerminalService` — orchestrates policy → cwd validation → DB record → process launch → stream → log to Central Logs |
| `app/api/v1/terminal.py` | FastAPI router — REST CRUD, SSE stream, WebSocket bidirectional endpoint |

### API endpoints

```
GET    /api/v1/terminal/security/status
GET    /api/v1/terminal/sessions/
POST   /api/v1/terminal/sessions/
GET    /api/v1/terminal/sessions/{id}
PATCH  /api/v1/terminal/sessions/{id}
DELETE /api/v1/terminal/sessions/{id}
POST   /api/v1/terminal/sessions/{id}/execute
POST   /api/v1/terminal/sessions/{id}/interrupt
POST   /api/v1/terminal/sessions/{id}/clear
GET    /api/v1/terminal/sessions/{id}/history
GET    /api/v1/terminal/commands/{id}
GET    /api/v1/terminal/processes/
DELETE /api/v1/terminal/processes/{pid}/stop
GET    /api/v1/terminal/consoles/{type}
GET    /api/v1/terminal/sessions/{id}/export
GET    /api/v1/terminal/sessions/{id}/stream   (SSE)
WS     /api/v1/terminal/ws/{session_id}        (WebSocket)
```

---

## Free Developer Services Integration

AgentForge integrates a curated selection of free-tier cloud and developer services inspired by [free-for-dev](https://github.com/ripienaar/free-for-dev), enabling zero-cost enterprise observability, CI/CD, and security.

### Integrated Services

| Service | Category | Free-Tier Allowance | Integration Capabilities |
|---|---|---|---|
| **GitHub** | VCS | Unlimited public/private repos, 5,000 req/hr | Repository connection, agent task branch creation, commit history, PR lifecycle & merge |
| **GitHub Actions** | CI/CD | 2,000 Linux runner minutes/month | Automated Pytest, Ruff, TypeScript builds, Docker checks & live status sync |
| **Semgrep** | Security | 100% Free Open-Source CLI & rules | AST static analysis, OWASP Top 10, command injection detection |
| **Gitleaks** | Security | 100% Free Open-Source CLI | High-entropy secret detection, API key patterns, private key detection |
| **Trivy** | Security | 100% Free Open-Source CLI | Dependency CVE vulnerability scans, SBOM generation, Dockerfile checks |
| **OpenObserve** | Observability | 0.5 GB/day cloud or unlimited self-hosted | Centralized structured event forwarding with automatic secret redaction |
| **Bugsink** | Error Tracking | Free self-hosted or free cloud tier | Sentry-compatible exception reporting, frontend error capture |
| **Better Stack** | Monitoring | 10 monitors, 3-min check intervals | Uptime heartbeat pings, multi-subsystem health probes, status page sync |
| **Cloudflare** | Deployment | Unlimited Pages sites, 50 free tunnels | Pages static deployment guide, cloudflared development tunnel supervisor |
| **Backblaze B2** | Storage | 10 GB free storage, 1 GB/day egress | S3-compatible cloud object archival for reports, test runs & backups |
| **RBAC / Auth** | Access Control | Unlimited local users | Role-based access control (Admin, Developer, Viewer) with local developer mode |

### Local-First Guarantee

All integrations are strictly optional. If no external API credentials are configured, AgentForge seamlessly falls back to 100% local functionality:
- Local Git branches and workspaces if GitHub token is omitted.
- Native AST security analysis and regex secret detection if Semgrep/Gitleaks binaries are absent.
- SQLite event persistence if OpenObserve is not configured.
- Protected internal `/health` endpoints if Better Stack heartbeat is absent.
- Administrator developer mode without login requirement if auth is disabled.

---

## License

For local development use only. See project documentation for terms.
