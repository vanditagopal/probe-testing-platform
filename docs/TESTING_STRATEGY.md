# Testing Strategy

## Backend
- Unit tests for OpenAPI validation and normalization.
- Unit tests for deterministic test generation, including incomplete schemas.
- Unit tests for assertion evaluation.
- Unit tests for URL validation and IP classification.
- URL safety tests use an injected resolver and never contact target hosts; cover
  malformed URLs, alternate IP spellings, all DNS answers, redirects, and connection
  address pinning.
- API tests for all FastAPI routes using `TestClient`.
- Integration tests using a local in-process mock HTTP server; do not rely on public demo services for required CI tests.
- Persistence tests verifying specs, runs, and results survive application restart.
- Security tests for SSRF, redirects, response limits, and secret redaction.
- Report tests for valid JSON and HTML escaping.

## Frontend
- Component tests for file upload, spec validation state, operation selection, candidate selection, run progress, and result rendering.
- Test loading, empty, success, validation-error, server-error, and partial-result states.
- Ensure keyboard navigation and labels are tested where practical.
- Do not make tests depend on public demo websites.

## End-to-end
After API MVP works, create one local fixture OpenAPI document and a local mock target. Test the full flow:
upload spec -> parse operations -> generate tests -> select tests -> execute -> inspect results -> download report.

## Test design rules
- No live external endpoint is required for the default test suite.
- Public demo targets may be used for manual smoke tests only.
- Test both positive and negative paths.
- Keep tests deterministic and independent.
- Never run destructive tests against third-party targets.
- Assert safe error shape without asserting internal stack traces.
