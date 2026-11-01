# Task Backlog and Agent Execution Order

Status values: `TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`. Update statuses only after verification.

## M0 — Foundation

### M0-01 [DONE] Inspect repository and scaffold
- Inspect existing files and preserve useful work.
- Create minimal `backend/` and `frontend/` structure.
- Add `.gitignore`, `.env.example`, and root README setup instructions.
- Do not implement the API runner yet.
**Acceptance:** clean, documented project structure; no secrets or generated environments committed.

### M0-02 [DONE] Backend health endpoint
- Create FastAPI application and `GET /health`.
- Add backend dependency/configuration file and test.
- Add consistent error-handling baseline.
**Acceptance:** health returns `{"status":"healthy"}`; test passes.

### M0-03 [DONE] Frontend shell
- Create React + TypeScript + Vite app.
- Build a clean, responsive shell with product name, API Testing entry, and UI Testing marked Planned.
- Add backend health status using configurable API base URL.
- Include loading, unavailable, and healthy states.
**Acceptance:** frontend starts; health state is tested; no target URLs are contacted.

### M0-04 [DONE] Quality gates
- Configure backend formatting/linting and pytest.
- Configure frontend linting and tests.
- Add documented commands for Windows PowerShell.
**Acceptance:** quality commands run and pass locally.

## M1 — OpenAPI import and discovery

### M1-01 [DONE] Define API schemas
- Define normalized operation, parameter, request-body, response, and parse-result models.
- Use stable operation IDs; generate deterministic fallback IDs when missing.
**Acceptance:** schema tests cover optional and missing metadata.

### M1-02 [DONE] Safe OpenAPI parser
- Accept OpenAPI 3.x JSON/YAML uploads.
- Enforce size limit and validate the document.
- Resolve local references only; never fetch external `$ref`.
- Return readable validation errors.
**Acceptance:** valid/invalid fixtures and local-reference tests pass.

### M1-03 [DONE] Persist parsed specs
- Add SQLite/SQLAlchemy models and repository/service layer.
- Store metadata and normalized operations.
**Acceptance:** parse result can be retrieved after app restart.

### M1-04 [DONE] Spec upload UI and operation list
- Add upload form and operation table.
- Display method, path, summary, parameters, response codes.
- Handle loading, empty, invalid-file, and server-error states.
**Acceptance:** upload fixture and view operations end-to-end.

## M2 — Test candidate generation

### M2-01 [DONE] Define candidate-test schema
- Add allowlisted assertion types and support status.
- Ensure test definitions are data only.
**Acceptance:** invalid assertion/action types are rejected.

### M2-02 [DONE] Implement deterministic generator
- Generate supported candidates from operation metadata and schemas.
- Include rationale and warnings.
- Avoid fabricating payloads when required values cannot be safely inferred.
**Acceptance:** deterministic unit tests and unsupported-schema tests pass.

### M2-03 [DONE] Candidate review UI
- List candidates and show rationale/assertions.
- Add select/deselect and selection summary.
- Mark candidates that need input or are unsupported.
**Acceptance:** selected IDs are submitted; unsupported candidates cannot run.

## M3 — Safe API execution

### M3-01 [DONE] URL safety service
- Validate scheme, hostname, DNS answers, IPv4/IPv6, redirects and blocked ranges.
- Reject private, loopback, link-local, reserved, unspecified, multicast, and metadata targets.
- Protect against redirects and DNS rebinding as far as the local architecture permits.
**Acceptance:** extensive security tests pass before any remote runner is enabled.

### M3-02 [TODO] Bounded HTTP runner
- Run only stored, validated selected test definitions.
- GET-only default; explicit opt-in for non-GET.
- Apply timeout, response-size, total-run, test-count and concurrency limits.
- Disable redirects by default.
**Acceptance:** local mock server integration tests pass; limits are verified.

### M3-03 [TODO] Persist run and results
- Store run state, per-test outcome, duration, assertions, sanitized response excerpt, safe error.
- Redact secrets.
**Acceptance:** results survive backend restart and contain no sensitive headers.

### M3-04 [TODO] Run API and UI
- Add run creation, run list, and run detail endpoints.
- Add progress/status/results UI.
**Acceptance:** selected tests only are executed and shown accurately.

## M4 — Reports

### M4-01 [TODO] JSON report
- Include summary, test details, assertion results, timestamps and safe diagnostics.
**Acceptance:** schema is stable and secrets are redacted.

### M4-02 [TODO] HTML report
- Generate standalone HTML with all user-controlled text escaped.
**Acceptance:** XSS-like strings display as text, not markup/script.

### M4-03 [TODO] Run history and downloads
- Show newest-first history and report download actions.
**Acceptance:** prior runs are available after restart; both report formats download.

## M5 — MVP hardening

### M5-01 [TODO] Full end-to-end tests
- Test local fixture upload through report download.
- Ensure CI tests do not rely on public endpoints.
**Acceptance:** full flow passes from a clean checkout.

### M5-02 [TODO] Accessibility and UX pass
- Check keyboard navigation, labels, focus, responsive layout, and non-colour status indicators.
**Acceptance:** documented checklist completed.

### M5-03 [TODO] Security review
- Verify SSRF protections, request limits, redirect handling, secret redaction, report escaping, and no arbitrary code execution.
**Acceptance:** security tests pass; unresolved limitations documented.

### M5-04 [TODO] Documentation and demo fixtures
- Add setup, troubleshooting, manual smoke test, and supported-feature documentation.
- Include a tiny local OpenAPI fixture and a local mock target for repeatable tests.
**Acceptance:** new developer can run the app and complete the demo using README alone.

## M6 — UI testing (future, not before M0–M5)

### M6-01 [TODO] UI target safety and Playwright isolation
### M6-02 [TODO] Browser discovery and evidence model
### M6-03 [TODO] Structured UI candidate generation and review
### M6-04 [TODO] UI execution, screenshots, traces, and report integration

Do not start M6 until all M0–M5 acceptance criteria are met.
