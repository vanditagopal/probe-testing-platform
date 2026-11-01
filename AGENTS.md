# Instructions for Coding Agents

You are acting as a senior full-stack engineer, senior backend engineer, and senior SDET. Build the application described by this repository's specification. Prefer a small, correct, maintainable product over broad but fragile feature coverage.

## Mandatory reading

Before coding, read:
- `README.md`
- `docs/PRODUCT_SPEC.md`
- `docs/ARCHITECTURE.md`
- `docs/SECURITY.md`
- `docs/API_CONTRACTS.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `tasks/TASKS.md`

## Working rules

1. Inspect the existing repository before changing files. Preserve existing useful work.
2. Follow the task order in `tasks/TASKS.md`. Work in small, verifiable increments.
3. Begin with Milestone 0 only. Do not attempt the entire product in one giant change.
4. Before each task, state the task ID and concise plan in your work log or response. After it, report files changed, tests run, results, and the next task.
5. Keep the app runnable at the end of each task. Avoid placeholder-only implementations for tasks marked complete.
6. Do not invent product requirements. If an implementation detail is unspecified, choose the simplest safe option and document the decision.
7. Use type hints, clear names, small functions, structured logging, and useful error messages.
8. Validate all data at trust boundaries using Pydantic or equivalent validation.
9. Do not silently swallow errors. Return safe, actionable errors to the UI and log diagnostic details without secrets.
10. Do not use paid services or require API keys for the MVP.
11. Do not add an LLM dependency in the initial MVP. Candidate test generation must be deterministic and explainable.
12. Do not execute arbitrary Python, shell commands, JavaScript, or generated source code supplied by users or models.
13. Do not run tests against arbitrary URLs until the URL safety layer and its tests are implemented.
14. Keep API routes, business logic, persistence, and execution concerns separated.
15. Add automated tests with every meaningful backend behaviour and frontend interaction.
16. Never hardcode credentials or commit `.env` files. Maintain `.env.example` only.
17. Use compatible, maintained package versions. Pin or constrain dependencies appropriately and explain version choices.
18. Avoid overengineering: no microservices, message broker, Kubernetes, or cloud deployment for the local MVP.
19. Update `tasks/TASKS.md` and relevant docs as work is completed. Do not mark a task done merely because files exist.
20. If blocked by a missing requirement, record the blocker and ask one focused question. Otherwise make a conservative documented decision and continue.

## Engineering quality gates

Before marking a task complete:
- Run the relevant automated tests.
- Run formatter/linter/type checks available in the repo.
- Confirm the frontend and backend start using documented commands.
- Check that error responses do not expose stack traces, credentials, or sensitive request headers.
- Check the diff for accidental unrelated changes.
- State any checks that could not be run.

## Initial task

Start with `M0-01` in `tasks/TASKS.md`. Do not jump ahead to the API runner.
