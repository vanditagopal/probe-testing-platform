# Website & API Testing Platform

An agent-ready specification pack for building a local-first application that discovers, generates, runs, and reports UI and API tests against targets the user is authorized to test.

## Local development setup (Windows PowerShell)

Prerequisites:

- Python 3.11 or newer
- Node.js 20.19 or newer (or 22.12 or newer) with npm
- Git

### Backend

From the repository root, create and activate a Python virtual environment, then install the backend and development dependencies:

```powershell
Set-Location backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Run backend formatting, lint, and tests from the `backend` directory:

```powershell
python -m ruff format --check .
python -m ruff check .
python -m pytest
```

To format Python files after making changes, run `python -m ruff format .`.

Start the API:

```powershell
python -m uvicorn app.main:app
```

Check `http://127.0.0.1:8000/health`; it should return `{"status":"healthy"}`. Run the backend tests from the `backend` directory with:

```powershell
python -m pytest
```

The backend creates its SQLite schema on startup. By default, `DATABASE_URL` is `sqlite:///./app.db`, so the database file is created in the backend working directory. Set `DATABASE_URL` before starting Uvicorn to use another SQLAlchemy-supported database URL. Parsed specs store normalized metadata and operations, not the uploaded source document.

Do not commit `.env` files, virtual environments, `node_modules`, or generated build output. `.env.example` documents local configuration keys and contains no credentials.

### Frontend

In a separate PowerShell terminal, from the repository root:

```powershell
Set-Location frontend
npm install
npm run dev
```

Vite serves the shell at `http://localhost:5173`. The backend health URL defaults to `http://127.0.0.1:8000`; override it before starting Vite if needed:

```powershell
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000"
npm run dev
```

The backend allows the frontend origins configured by `FRONTEND_ORIGIN` (defaults to `http://localhost:5173,http://127.0.0.1:5173`). To use different frontend origins, set that environment variable to a comma-separated list before starting Uvicorn. The shell checks only the configured backend `/health` endpoint; it does not contact API or website targets.

Run frontend lint, tests, and the production type-check/build from the `frontend` directory:

```powershell
npm run lint
npm test
npm run build
```

With both local services running, open `http://localhost:5173`, choose an OpenAPI
`.json`, `.yaml`, or `.yml` file (up to 1 MiB), and select **Validate and discover**.
The application sends the file only to its local backend, which validates and stores
the normalized specification before returning its operations. Invalid files and
backend failures are shown in the page; no target API is called during import.
Select the operations to review and choose **Generate candidate tests**. Review each
candidate's rationale, request summary, assertions, warnings, and support status.
Only candidates marked **Ready** can be selected; candidate selection is local review
state and does not send requests to the described API. Test execution is a later task.

## Product direction

Build an **API-first MVP**, then add browser/UI testing. The initial product must work locally and use free/open-source components. AI-assisted test generation is explicitly out of scope for the first milestone; use deterministic rules first.

## Technology baseline

- Frontend: React + TypeScript + Vite
- Backend: Python + FastAPI + Pydantic
- API testing: HTTPX + pytest (the platform orchestrates structured test cases; it must not execute arbitrary user-supplied Python)
- OpenAPI: `openapi-spec-validator` for OpenAPI 3.x validation and PyYAML safe loading for YAML
- UI testing in a later phase: Playwright for Python
- Persistence: SQLite + SQLAlchemy initially
- Reports: HTML and JSON
- Tests: pytest for backend; Vitest + React Testing Library for frontend; Playwright for platform end-to-end tests only after core flows exist
- Local development: Windows PowerShell-compatible instructions; Python virtual environment; npm

## Start here

1. Read `AGENTS.md`.
2. Read `docs/PRODUCT_SPEC.md`, `docs/ARCHITECTURE.md`, and `docs/SECURITY.md`.
3. Read `docs/IMPLEMENTATION_PLAN.md` and `tasks/TASKS.md`.
4. Implement only **Milestone 0** first: scaffold, health endpoint, frontend shell, quality gates, and documentation.
5. Continue in the listed task order. Keep the app runnable after each milestone.

## MVP user journey

1. User chooses API testing.
2. User provides an OpenAPI JSON/YAML URL or uploads a local OpenAPI file.
3. Backend validates and parses the specification.
4. UI shows discovered operations.
5. User generates deterministic candidate tests.
6. User reviews/selects candidate tests.
7. User starts a run.
8. Runner executes supported HTTP requests with strict safety limits.
9. User sees run progress and per-test outcomes.
10. User opens or downloads an HTML/JSON report and can view run history.

## Non-goals for the first MVP

- Public multi-tenant SaaS deployment
- User accounts, teams, billing, or cloud execution
- Arbitrary code execution
- AI/LLM-generated executable tests
- Load/stress testing
- Browser testing of arbitrary URLs (planned later, behind the same security model)
- Automatic destructive testing against third-party systems
- Secrets management beyond local development safeguards

## Definition of done

A milestone is complete only when:
- Its acceptance criteria are met.
- Tests pass.
- Lint/type checks pass where configured.
- Documentation and examples are updated.
- No secrets are committed.
- No known security-critical issue is left unaddressed.
