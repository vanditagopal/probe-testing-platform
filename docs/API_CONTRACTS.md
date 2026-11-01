# API Contracts (MVP)

Prefix all routes with `/api/v1`. The exact response models should be implemented as Pydantic schemas and mirrored with TypeScript types.

## Conventions

- JSON request/response bodies.
- Use consistent error shape:
```json
{
  "error": {
    "code": "INVALID_OPENAPI_SPEC",
    "message": "The OpenAPI document could not be validated.",
    "details": []
  }
}
```
- Never return stack traces, secrets, or raw internal exception messages.
- Use HTTP status codes appropriately: 400 malformed input, 413 size limit, 422 validation failure, 404 missing resource, 409 invalid state, 429 rate/limit exceeded, 500 unexpected server failure.

## `GET /health`
Returns:
```json
{"status":"healthy"}
```
No external network calls.

## `POST /api/v1/specs/parse`
Accept multipart upload for MVP:
- `file`: OpenAPI JSON/YAML file.
- Accept UTF-8 JSON or YAML up to 1 MiB.
- Validate OpenAPI 3.x and parse operations.
- Resolve local JSON Pointer `$ref` values; reject external references without fetching.
- Reject malformed, unresolved, excessively nested, or overly complex documents.

Response:
```json
{
  "spec_id": "uuid",
  "title": "Example API",
  "version": "1.0.0",
  "openapi_version": "3.0.3",
  "operations": [
    {
      "operation_id": "getItems",
      "method": "GET",
      "path": "/items",
      "summary": "List items",
      "parameters": [],
      "request_body": null,
      "responses": [
        {"status_code": "200", "content_types": ["application/json"], "schema_summary": "array"}
      ]
    }
  ],
  "warnings": []
}
```
Exact fields can evolve, but document changes and keep frontend types synchronized.
Each operation includes optional `summary` and `description`, a `parameters` list
(`name`, `location`, `required`, `description`, and `schema_summary`), an optional
`request_body` (`required`, `content_types`, and `schema_summary`), and a `responses`
list (`status_code`, `content_types`, and `schema_summary`). Missing optional metadata
uses `null` or an empty list. If `operationId` is absent or blank, the parser generates a
stable ID from the method, path, and a short SHA-256 digest of both.
Successful uploads return HTTP 201 and are persisted. Invalid OpenAPI content returns
HTTP 422 with `error.code` set to `INVALID_OPENAPI_SPEC`; uploads above the 1 MiB
limit return HTTP 413. `GET /api/v1/specs/{spec_id}` returns the stored normalized
parse result or the standard 404 error response.

## `POST /api/v1/specs/{spec_id}/tests:generate`
Request:
```json
{
  "operation_ids": ["getItems"],
  "options": {
    "include_negative_cases": true,
    "max_candidates_per_operation": 10,
    "response_time_threshold_ms": 1000
  }
}
```
Response:
```json
{
  "tests": [
    {
      "id": "uuid",
      "operation_id": "getItems",
      "title": "Validate documented success response",
      "category": "response_schema",
      "rationale": "The specification documents a successful JSON response.",
      "support_status": "ready",
      "request": {"method": "GET", "path": "/items", "parameters": []},
      "assertions": [
        {"type": "status_code_in", "expected": [200]}
      ],
      "warnings": []
    }
  ]
}
```
Do not generate a test if its request cannot be safely constructed. Mark incomplete candidates as `needs_input` or `unsupported`.
Generation is deterministic: candidate IDs are UUIDv5 values derived from the stored
specification ID and operation identity. The generator only uses normalized metadata;
it does not invent parameter values or request bodies. Candidates requiring missing
request inputs are marked `needs_input`, and response schemas that cannot be represented
by the allowlisted assertions are not guessed. Documented error statuses are
`unsupported` unless a safe trigger can be inferred (the MVP does not infer triggers).
`response_time_threshold_ms` is a positive threshold from 1 to 60,000 ms used for
response-time candidates; the per-operation candidate cap is from 1 to 50. A
response-time candidate is omitted when required request inputs are missing.
Candidate `support_status` is restricted to `ready`, `needs_input`, or `unsupported`.
Candidate requests are structured data, and assertions are restricted to the
documented discriminated set: `status_code_equals`, `status_code_in`,
`header_exists`, `header_equals`, `json_path_exists`, `json_value_type`,
`enum_membership`, and `duration_under`. Candidate definitions do not accept
arbitrary scripts or client-supplied `selected` flags. Categories are restricted to
`response_schema`, `required_parameter`, `boundary`, `content_type`,
`documented_error`, and `response_time`. Request bodies are JSON values only;
request paths are absolute-path references, not full URLs. Status assertions use
HTTP status values from 100 through 599, and duration thresholds must be positive.

## `POST /api/v1/runs`
Request:
```json
{
  "spec_id": "uuid",
  "base_url": "https://api.example.test",
  "test_ids": ["uuid"],
  "options": {
    "timeout_seconds": 10,
    "max_response_bytes": 1048576,
    "allow_non_get_methods": false,
    "stop_on_failure": false
  }
}
```
Response:
```json
{
  "run_id": "uuid",
  "status": "queued",
  "created_at": "2026-01-01T00:00:00Z"
}
```
For the local MVP, execution may be synchronous if the UI stays responsive and total runtime is bounded. Prefer a background task abstraction if it can be implemented simply without adding a broker. The response contract may use `running` or `completed` if execution is synchronous.

Before execution:
- Verify `spec_id` and every test ID exist and are compatible.
- Reject unknown test IDs.
- Validate base URL and target network safety.
- Accept only HTTP(S) on standard ports 80/443; reject credentials, fragments, ambiguous
  host encodings, metadata/local targets, and any DNS result that is not globally
  routable. Validate the selected connection IP against the prevalidated DNS answers.
- Reject non-GET methods unless explicitly enabled.
- Never trust request paths or assertions supplied directly by the browser without checking against stored validated test definitions.
- Redirects are disabled by default. If enabled later, validate every redirect
  destination before following it, reject HTTPS-to-HTTP downgrades, and enforce a
  bounded redirect count.

## `GET /api/v1/runs`
Returns newest-first run summaries with pagination.

## `GET /api/v1/runs/{run_id}`
Returns run summary and per-test results.

## `GET /api/v1/runs/{run_id}/report?format=json`
Returns a downloadable JSON report. `format=html` returns a standalone HTML report with escaped values.

## `GET /api/v1/specs/{spec_id}`
Returns stored spec metadata and normalized operations, excluding sensitive source material unless needed.

## Data models

### Run status
`queued | running | completed | failed | cancelled`

### Test outcome
`passed | failed | error | skipped`

### Candidate support status
`ready | needs_input | unsupported`

### Result fields
Include test ID/title, outcome, start/end time or duration, sanitized request summary, status code when available, assertion outcomes, safe response excerpt, and safe error code/message. Do not persist raw authorization headers, cookies, or secrets.
