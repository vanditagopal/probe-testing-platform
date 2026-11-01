# Architecture

## 1. Architecture principles

- Modular monolith; no microservices.
- API-first development, then UI automation.
- Deterministic and explainable test generation.
- Structured test definitions instead of executable generated code.
- Safety validation before network execution.
- Local SQLite persistence for the MVP.

## 2. Proposed repository layout

```text
website-api-testing-platform/
├── AGENTS.md
├── README.md
├── .gitignore
├── .env.example
├── docs/
│   ├── PRODUCT_SPEC.md
│   ├── ARCHITECTURE.md
│   ├── API_CONTRACTS.md
│   ├── SECURITY.md
│   ├── TESTING_STRATEGY.md
│   ├── IMPLEMENTATION_PLAN.md
│   └── DECISIONS.md
├── tasks/
│   └── TASKS.md
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py
│   │   ├── api/routes/
│   │   ├── core/config.py
│   │   ├── core/logging.py
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── openapi_parser.py
│   │   │   ├── test_generator.py
│   │   │   ├── url_safety.py
│   │   │   ├── api_runner.py
│   │   │   └── report_service.py
│   │   ├── db/
│   │   └── models/
│   └── tests/
└── frontend/
    ├── package.json
    ├── src/
    │   ├── app/
    │   ├── components/
    │   ├── features/
    │   │   ├── api-testing/
    │   │   ├── runs/
    │   │   └── shared/
    │   ├── lib/
    │   └── types/
    └── tests/
```

This is a target layout, not a requirement to create every file in Milestone 0. Keep it lean and only add modules when needed.

## 3. Component responsibilities

### Frontend
- Collect OpenAPI input and display validation errors.
- Display operations and generated candidate tests.
- Submit only selected test IDs/configuration for execution.
- Poll or refresh run status.
- Display run history, test results, and report downloads.
- Never make arbitrary target requests directly from the browser as a substitute for backend validation.

### FastAPI routes
Thin request/response layer. Validate schemas, call services, map known exceptions to safe HTTP responses. Do not place test generation or execution logic directly in route handlers.

### OpenAPI parser
- Parse supported OpenAPI 3.x documents.
- Validate format and version.
- Normalize operations and schemas into internal models.
- Resolve local references safely.
- Do not fetch external `$ref` documents automatically in MVP.
- Limit document size, nesting, and complexity where practical.

### Test generator
Pure/deterministic service: input normalized operations and generation options; output validated candidate test definitions with rationale and support status. No network calls.

### URL safety service
Validate remote target URLs and every resolved address/redirect before any network request. Block loopback, private, link-local, multicast, reserved, unspecified, and metadata-service destinations. Guard against DNS rebinding and redirect-based bypass. See SECURITY.md.

### API runner
- Accept only validated structured definitions.
- Enforce allowed HTTP methods, timeout, response-size, test-count, and total-run limits.
- Never execute code from the specification.
- Sanitize outputs and redact secrets.
- Make results deterministic and traceable.

### Persistence
SQLite via SQLAlchemy. Store projects/spec metadata, normalized operations as needed, generated test definitions, runs, and results. Store only the minimum data needed. Avoid storing secrets.

### Report service
Create escaped HTML and JSON from persisted structured results. Reports are untrusted output contexts: HTML must escape all user-controlled text and never inject raw response bodies as markup.

## 4. API runner execution model

For each selected candidate:
1. Validate its schema again at execution boundary.
2. Resolve the final URL using a trusted base URL and a path template.
3. Validate URL and resolved IP addresses.
4. Apply parameter and request-body limits.
5. Send the request with bounded timeout and redirects disabled by default.
6. Revalidate each redirect destination if redirects are later enabled.
7. Cap response bytes while streaming.
8. Evaluate only supported declarative assertions.
9. Redact secrets and persist a result.
10. Continue or stop according to the run's configured failure policy.

## 5. Test definition model

Represent tests as data, never source code. A candidate includes:
- `id`
- `operation_id`
- `title`
- `category`
- `rationale`
- `support_status` (`ready`, `needs_input`, `unsupported`)
- `request` (method, path, safe parameters, optional body template)
- `assertions` (allowlisted assertion types and typed values)
- `tags`

Selection is UI state and is not part of the backend candidate definition; execution
must receive candidate IDs and resolve them against validated stored definitions.

Backend candidate schemas use a discriminated, allowlisted assertion union: status
code equals/in-list, header exists/equality, JSON path exists, JSON value type, enum
membership, and duration under a configured threshold. Unknown assertion types,
executable fields, and client-supplied selection state are rejected. Candidate
requests contain only typed method/path/parameter/body data; they are never source
code.

## 6. Future UI automation

Add a separate browser discovery/runner service using Playwright for Python. Run browsers in a restricted process/container where possible, with navigation allowlists/deny rules, download limits, execution timeouts, and no access to local files or private network services. UI test candidates should be structured actions/assertions, not arbitrary scripts. Require user review before running actions that submit forms, delete records, purchase items, or otherwise cause side effects.
