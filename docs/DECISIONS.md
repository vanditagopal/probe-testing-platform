# Architecture Decision Records

## ADR-001: Local-first modular monolith
**Decision:** Use one FastAPI backend and one React frontend for the MVP.
**Reason:** Lowest complexity and cost; easy to run and debug locally.
**Revisit when:** Real concurrent multi-user use or separate scaling requirements exist.

## ADR-002: API-first MVP
**Decision:** Build OpenAPI import, deterministic candidate generation, execution, and reports before UI testing.
**Reason:** API contracts are structured and easier to validate safely than arbitrary website behaviour.
**Revisit when:** API workflow is stable and covered end-to-end.

## ADR-003: Structured tests, never generated source code
**Decision:** Test cases are validated JSON-like data with allowlisted actions and assertions.
**Reason:** Avoid arbitrary code execution and make tests inspectable.
**Revisit when:** Never for untrusted user-generated tests; any extension must preserve sandboxing and validation.

## ADR-004: Deterministic generation before AI
**Decision:** Use rules derived from OpenAPI schemas first.
**Reason:** Free, reproducible, explainable, testable, and avoids data sharing with third-party AI services.
**Revisit when:** A useful AI suggestion layer can be added with explicit privacy controls and no arbitrary code execution.

## ADR-005: SQLite first
**Decision:** Use SQLite with SQLAlchemy for local persistence.
**Reason:** Zero-cost and no separate database service.
**Revisit when:** Deployment or concurrency requirements justify PostgreSQL.

## ADR-006: Local file upload before remote spec fetching
**Decision:** Implement upload first; remote URL import later.
**Reason:** Reduces SSRF exposure while parser and UI are being built.
**Revisit when:** URL safety and egress restrictions are implemented and tested.

## ADR-007: Bounded, local-reference-only OpenAPI parsing
**Decision:** Parse UTF-8 JSON/YAML up to 1 MiB, validate with `openapi-spec-validator`,
and accept only local JSON Pointer `$ref` values.
**Reason:** Standard validation avoids maintaining a partial OpenAPI validator; rejecting
non-local references before validation prevents implicit network retrieval. Document
depth and node limits bound parser work.
**Revisit when:** Any new input format or reference resolution behavior is proposed.
