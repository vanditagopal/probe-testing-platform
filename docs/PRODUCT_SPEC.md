# Product Specification

## 1. Summary

The Website & API Testing Platform helps a user discover testable behaviours from a website or API contract, generate candidate test cases, choose which tests to run, execute them, and inspect a report.

The initial release is a local developer tool for targets the user owns or is explicitly authorized to test.

## 2. Problem

Manual test setup requires users to inspect routes or pages, write repetitive test cases, run them, and assemble results. This tool should reduce setup effort without pretending it can infer every business requirement automatically.

## 3. Personas

- QA/SDET who wants to accelerate test design and execution.
- Developer who wants a quick validation run against an API they own.
- Learner building an understanding of test automation.

## 4. Core workflow

### API MVP
1. Open the app.
2. Select **API Testing**.
3. Provide either:
   - an OpenAPI JSON/YAML URL, or
   - a local OpenAPI file upload.
4. Review specification validation status and discovered operations.
5. Select operations to generate candidate tests for.
6. Review candidates, their rationale, and expected assertions.
7. Select tests and configure safe run options.
8. Start a run.
9. See run status and per-test outcomes.
10. Open a run detail page and download HTML/JSON report.

### Later UI workflow
1. Select **UI Testing** and enter an authorized website URL.
2. Safely inspect the page in an isolated browser.
3. Display discovered elements with locator confidence and evidence.
4. Generate candidate tests from observable page structure.
5. Let the user review and edit assertions before execution.
6. Execute selected tests in a clean browser context.
7. Capture screenshots, traces, and results.

UI testing is not part of the API MVP and must not be represented as available until implemented.

## 5. Functional requirements

### FR-01 App shell
- Show product name and clear navigation.
- Show API Testing as available; UI Testing may be labelled “Planned” until implemented.
- Show a clear empty state and useful errors.

### FR-02 OpenAPI input
- Accept OpenAPI 3.x JSON or YAML via upload.
- Later allow a remote URL after SSRF protections are complete.
- Enforce file size limits and supported content types.
- Validate the spec and show readable validation errors.
- Never treat the spec as executable code.

### FR-03 Operation discovery
For each operation, display:
- HTTP method
- path
- operation summary/description when present
- path/query/header parameters
- request body schema summary
- documented response codes and response schema summary
- operationId when present

Handle missing optional metadata gracefully. Preserve stable identifiers for operations.

### FR-04 Deterministic candidate generation
Generate candidate tests from specification facts, with a human-readable rationale. Supported initial categories:
- documented success response/schema validation, only where a plausible example or schema-driven request can be constructed
- required parameter presence/validation
- enum/boundary candidates where schema constraints make them meaningful
- response content type and JSON parsing where applicable
- documented error responses, only when a safe request can be constructed
- basic response-time threshold as a configurable operational check, not a claim about business correctness

Do not invent success payloads for complex schemas without sufficient information. Mark unsupported cases as “needs input” rather than generating invalid requests.

### FR-05 Test review and selection
- Show generated tests before execution.
- Each candidate has ID, title, operation, category, rationale, request summary, assertions, and support status.
- User can select/deselect tests.
- User can edit a small safe set of options such as timeout and expected status, with validation and clear warnings.
- No arbitrary script/code editor.

### FR-06 Execution
- Execute only user-selected, validated test definitions.
- Apply connect/read/total timeouts, maximum response size, per-run test count, and total run duration.
- Initially support GET by default. Permit non-GET methods only for explicit user selection and with a clear side-effect warning. The initial safe default is to disable non-GET execution unless the user enables it.
- Do not follow redirects to disallowed destinations.
- Do not send credentials unless explicitly provided for a target the user is authorized to test. Redact credentials in logs and reports.
- Store structured outcomes: passed, failed, error, skipped.
- Store request method/URL with secrets redacted, status, duration, safe response excerpt, assertion results, and sanitized error details.

### FR-07 Reports and run history
- Store test definitions and run results in SQLite.
- Show runs newest first.
- Run detail includes summary counts and per-test result details.
- Download JSON report.
- Download standalone HTML report with escaped user-controlled text.
- Reports must not include authorization headers, cookies, API keys, or unredacted secrets.

### FR-08 UX and accessibility
- Responsive layout suitable for desktop first.
- Accessible labels, keyboard focus, semantic headings, and clear status text.
- Distinguish validation errors from runtime failures.
- Do not communicate only with colour; include text/icons/labels.

## 6. Non-functional requirements

- Local-first and zero-cost for MVP.
- Windows development support; commands documented for PowerShell.
- Predictable, reproducible execution.
- Modular design and automated tests.
- Safe defaults for arbitrary inputs and external network access.
- No collection or transmission of user data to third parties.
- Errors must be understandable without exposing internal stack traces.
- UI should make it clear when a result is an inference/candidate rather than a guaranteed test oracle.

## 7. Out of scope for MVP

- LLM-generated code or test execution.
- Load, stress, penetration, or vulnerability scanning.
- CAPTCHA bypass, authentication bypass, or anti-bot circumvention.
- Multi-user cloud SaaS, account management, billing, and remote workers.
- Full Postman collection support (possible later).
- Automatic login to arbitrary websites.
- Browser UI discovery and execution.
- Test scheduling and CI integration.

## 8. MVP acceptance criteria

The API MVP is accepted when a user can:
1. Start frontend and backend locally using documented commands.
2. Upload a valid OpenAPI 3.x file and see its operations.
3. See clear validation errors for invalid specs.
4. Generate candidate tests with an explanation of each candidate.
5. Select a subset and execute only those tests.
6. View per-test status, assertions, duration, and safe error details.
7. View previous runs after backend restart.
8. Download a JSON and HTML report.
9. Run all automated tests successfully.
10. Verify that unsafe targets, redirect tricks, oversized responses, and secret leakage are covered by security tests.
