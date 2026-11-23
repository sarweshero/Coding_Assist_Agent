# Conding-Assist Backend (Week 1 Scaffold)

FastAPI backend for the multi-agent autonomous software engineering platform.

## Scope (Week 1)

- FastAPI app entry point with CORS, lifespan, `/health` endpoint
- Modular layout: `agents/`, `orchestrator/`, `prompts/`, `llm/`, `schemas/`, `storage/`, `api/`
- Runtime config via `ConfigManager` (`app/config_manager.py`, JSON at `./data/config.json`) with per-agent models, providers, review policy, auto-review toggle
- LLM routing via LiteLLM with per-agent model resolution (`app/llm/router.py`)
- Jinja2 prompt templates (`app/prompts/*.j2`) with dynamic context
- Agent layer: `OrchestratorAgent` (plan), `DeveloperAgent` (code), `QAAgent` (tests), `FixerAgent` (fix), `ReviewerAgent` (code review)
- Orchestrator service: module planning + implementation + test + auto-fix + auto-review flow
- Finite state machine (`app/orchestrator/state_machine.py`)
- Module gatekeeper (`app/orchestrator/gatekeeper.py`)
- Code review storage + live diff rendering (`app/schemas/review.py`, `app/storage/repository.py`)
- REST API + SSE streaming endpoints (`app/api/routes.py`, `app/api/sse.py`)
- SSH layer: asyncssh manager (`app/ssh/ssh_manager.py`), command guardrail (`app/ssh/guardrail.py`), approval store (`app/ssh/approvals.py`)
- SSH REST endpoints: connect / disconnect / status / exec / approvals / files (`app/api/ssh_routes.py`)

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Terminal Chat (no web app required)

The backend can be driven without the web frontend via a terminal REPL:

```bash
python -m app.cli
```

Commands: `new <name>`, `requirements <text>`, `plan`, `approve`, `run <index>`, `review <index>`, `review history <index>`, `status`, `mode <PLAN|EDIT|FIX|EXPLAIN>`, `config`, `help`, `quit`.

Flow: set requirements → `plan` (orchestrator generates module blueprint) → `approve` → `run <index>` (developer writes code → QA tests → auto-fix loop → auto code-review → gatekeeper advances).

### Config wizard

```
> config
  1) Add provider
  2) Set model for agent
  3) List config
  4) Delete provider
  5) Set review policy
  6) Set auto-review toggle
  7) Back
```

Review policy: `strict` | `balanced` | `permissive`. Auto-review toggle controls whether the `ReviewerAgent` runs automatically after tests pass.

## API

- `POST /api/projects` - create project
- `GET /api/projects/{id}` - get project state
- `PATCH /api/projects/{id}` - update requirements
- `POST /api/projects/{id}/approvals` - approve plan -> transitions to `IMPLEMENTING_MODULE`
- `POST /api/projects/{id}/mode` - switch mode (`PLAN`, `EDIT`, `FIX`, `EXPLAIN`)
- `POST /api/projects/{id}/modules/{module_id}/run` - run developer + QA for a module
- `POST /api/projects/{id}/modules/{module_id}/review` - run code reviewer for a module
- `GET /api/projects/{id}/modules/{module_id}/tests` - fetch latest test run
- `GET /api/projects/{id}/events` - SSE event stream

## SSH

- `POST /api/ssh/connect` - connect (host, port, username, password / private_key)
- `POST /api/ssh/disconnect` - disconnect
- `GET /api/ssh/status` - connection state
- `POST /api/ssh/exec` - run command (guarded; critical commands require approval)
- `POST /api/ssh/approvals/{approval_id}` - approve / reject pending command
- `GET /api/ssh/files?path=/` - list dir or read file (SFTP)
- `POST /api/ssh/files` - write file via SFTP `{path, content}`
