# Implementation Plan

Build one milestone at a time. Keep each milestone runnable.

## Milestone 0 — Foundation
- Scaffold repository, backend, and frontend.
- Add FastAPI `/health`.
- Add React/TypeScript app shell and API connectivity indicator.
- Add environment example, ignore rules, formatting/lint/test scripts.
- Document local Windows PowerShell setup.
- No external target requests yet.

Exit criteria: frontend and backend start locally; health check succeeds; baseline backend/frontend tests pass.

## Milestone 1 — OpenAPI upload and discovery
- Upload a local OpenAPI 3.x JSON/YAML file.
- Validate document and version.
- Normalize operations, parameters, request body and responses.
- Show operations in the frontend.
- Persist spec metadata and normalized operations in SQLite.
- Do not support remote URL import yet.

Exit criteria: valid fixture parses; invalid spec shows useful errors; local `$ref` works within safe limits; external `$ref` is not fetched.

## Milestone 2 — Deterministic candidate test generation
- Define structured candidate test schema.
- Generate explainable candidates for supported operations.
- Display candidate title, rationale, request summary, assertions, and support status.
- Add select/deselect interactions.
- Handle unsupported cases explicitly.

Exit criteria: candidate generation is deterministic and covered by unit tests; no generated code is executed.

## Milestone 3 — Safe API execution
- Implement URL safety checks and unit/security tests before network execution.
- Implement bounded HTTPX runner for validated selected tests.
- GET-only default; explicit opt-in for non-GET.
- Apply timeouts, response-size limits, test count/run deadline and concurrency limits.
- Persist sanitized outcomes.

Exit criteria: local mock target integration test passes; blocked destinations and redirects are rejected; result storage is safe.

## Milestone 4 — Run history and reports
- Run list and run detail UI.
- Persist run state and test outcomes.
- JSON report and escaped standalone HTML report.
- Download actions and useful error/empty states.

Exit criteria: end-to-end local flow works; report escaping and secret-redaction tests pass.

## Milestone 5 — Hardening and usability
- Add robust validation, clear UX, accessibility pass, and error handling.
- Add manual smoke-test instructions for public demo targets.
- Improve logs and developer docs.
- Run all quality gates.

Exit criteria: MVP acceptance criteria in PRODUCT_SPEC.md pass.

## Milestone 6 — UI testing (after API MVP)
- Add UI Testing navigation and URL form.
- Implement safe URL validation and isolated Playwright discovery.
- Discover elements and display evidence/confidence.
- Generate structured candidate UI tests, not code.
- Add user review and side-effect warnings.
- Execute selected tests and capture screenshots/traces.
- Store and report UI results using common run abstractions.

Exit criteria: local fixture site can be tested end-to-end; external target safety is covered.

## Later possibilities (not MVP)
- OpenAPI URL import after SSRF protections are reviewed.
- Postman collection import.
- Optional local LLM-assisted suggestions (never executable code).
- CI integration.
- PostgreSQL if concurrent multi-user use becomes a real requirement.
- Deployment only after isolation and egress controls are designed.
