# BBIOS OS Development Standards

## 1. Purpose

These standards govern code and architecture for BBIOS OS. They protect the current baseline while guiding future migration toward the approved layered target architecture.

## 2. Applicability

These rules apply to backend Python, cockpit modules, tests, documentation, frontend API interactions, and future infrastructure work.

## 3. Python Standards

- Use Python 3.12.13 for local backend development.
- The supported project range is `>=3.12,<3.13`; Python 3.9 is unsupported for new development.
- Runtime version changes require clean-environment dependency installation, focused tests, full tests, compile checks, import checks, and documentation updates.
- Use clear names and explicit control flow.
- Prefer standard library tools unless an approved dependency exists.
- Keep imports narrow and remove unused imports.
- Use type hints for public constructors and methods.
- Avoid `Any` when stable interfaces are known.
- Use `Any` only at boundaries where the repository currently passes request-like test doubles or unresolved collaborator protocols.

## 4. Module Organization

- Keep Routers, Handlers / Adapters, Application Services, Domain Services, Workflow Controls, Repositories, models, and utilities separated by responsibility.
- Do not move modules without an approved compatibility plan.
- New modules must have a clear owner and active use case.

## 5. Layer Responsibilities

- Router: HTTP route declaration and transport-level request binding.
- Handler / Adapter: translate request-like objects, map status codes, and build response envelopes.
- Application Service: orchestrate use cases across repositories and domain components.
- Domain Service: enforce domain rules and transitions.
- Workflow Control: manage workflow execution commands and safe cockpit controls.
- Repository: expose persistence operations through public interfaces.
- Persistence: store and retrieve durable state.
- Observability: cross-cutting logging, metrics, request context, and execution summaries.

## 6. Dependency Direction

Dependencies should point inward:

- Routers depend on Handlers / Adapters or Application Services.
- Handlers / Adapters depend on Application Services.
- Application Services depend on Domain Services, Workflow Controls, and Repository interfaces.
- Domain logic must not depend on HTTP transport.
- Repositories must not depend on Routers.

## 7. Service Design

- Constructors should use explicit dependencies.
- Optional dependency injection may be used only for controlled backward compatibility.
- Services should delegate specialized work rather than duplicating dashboard, workflow, monetization, or repository logic.
- Services should not know database session internals unless a future unit-of-work pattern explicitly defines ownership.

## 8. Handler and Router Design

- No business logic in Routers.
- Handlers must not mutate storage except through Application Services.
- Handlers should use existing response helpers where standardized envelopes are expected.
- Unknown routes must use existing route-not-found behavior.
- Do not swallow unexpected exceptions merely to make tests pass.

## 9. Repository Design

- Repositories expose public interfaces for all Application Service needs.
- Application code must not call private Repository methods.
- Private Repository methods such as `_read()` are implementation details. Private Repository access currently present in cockpit compatibility code is technical debt and remains only until a bounded public Repository-contract correction is approved.
- Prefer `Protocol` or abstract interfaces when more than one implementation is active or planned.

## 10. Persistence Standards

- Current persistence is JSON-file and in-memory.
- PostgreSQL is planned, not implemented.
- Storage format changes require explicit approval, migration plan, rollback plan, and tests.
- JSON metadata fields require documented relational versus JSONB decisions before database migration.

## 11. Transaction Standards

- Database transactions must have explicit ownership.
- Multi-write use cases must define commit and rollback behavior.
- External side effects require idempotency, compensation, outbox, or documented recovery strategy.
- Repository implementations must not each independently commit if the service operation needs atomicity.

## 12. Configuration Standards

- Configuration must not be scattered across modules.
- General application settings must use `bbi_os/settings.py`.
- Environment variable handling should remain centralized for non-secret application configuration.
- Existing credential-specific reads for auth tokens and connector/webhook secrets are current behavior and require a future bounded security/configuration task before consolidation.
- Secrets must not be committed.
- Secret values must not be logged or included in documentation.
- Environment variable names may be referenced when needed for configuration clarity.

## 13. Error Handling

- Use narrow exception handling.
- Map expected validation/control errors to documented error responses.
- Let unexpected exceptions surface unless an existing handler convention deliberately maps them.
- Preserve error codes where tests or clients depend on them.

## 14. Response Contracts

- Internal Handler / Adapter responses should use standardized envelopes where current contracts expect them.
- Existing prototype FastAPI responses must not change silently.
- New Versioned API work must include response contract tests.

## 15. Type Hinting

- Public methods should include parameter and return hints when practical.
- Prefer concrete domain types and repository protocols.
- Avoid broad dictionaries in stable internal APIs unless the domain intentionally stores flexible metadata.

## 16. Data Models

- Current models are a mix of Pydantic and dataclasses.
- Do not conflate transport schemas, domain models, and persistence models without an ADR.
- SQLAlchemy models, when introduced, should not leak into Routers or Handlers.

## 17. Logging and Observability

- Preserve request ID, user ID, role, event names, and structured metadata.
- New workflows and handlers should emit meaningful events.
- Avoid logging sensitive values.
- Observability event changes require regression tests.

## 18. Security Practices

- Keep secrets out of code, tests, docs, and logs.
- Authentication and authorization must be enforced at request boundaries.
- Current auth behavior is not a complete future security model.
- Future auth work requires security tests and audit requirements.

## 19. Backward Compatibility

- Public behavior must not be changed silently.
- Compatibility Layers may coexist temporarily with target architecture.
- Deprecation requires documentation, tests, and approval.

## 20. Refactoring Rules

- Refactor only when required by the approved task or when it materially reduces risk in touched code.
- Do not combine broad cleanup with feature work.
- Keep diffs reviewable.

## 21. Documentation Standards

- Use repository-relative paths.
- Distinguish confirmed current behavior, target architecture, planned work, deferred decisions, and unresolved risks.
- Update ADRs for architectural choices.

## 22. Technical Debt Rules

- Record technical debt explicitly.
- Assign a future cleanup path where possible.
- Do not hide debt by weakening tests.

## 23. Prohibited Practices

- No business logic in Routers.
- No direct private Repository access in application code, except for already-recorded temporary compatibility debt awaiting approved correction.
- No unapproved dependencies.
- No unapproved storage format changes.
- No committed secrets.
- No silent public API breaks.
- No speculative abstractions without an active use case.

## 24. Code Review Checklist

- Scope matches approval.
- Layer boundaries are preserved.
- Tests cover the changed behavior.
- Full `unittest` baseline passes.
- Response contracts remain compatible.
- Observability events remain intact.
- Security and secrets are handled correctly.
- Rollback is clear for infrastructure changes.
- Technical debt is recorded rather than hidden.

## Temporary Compatibility Note

Current prototype FastAPI paths and richer cockpit Handler / Adapter paths coexist. FastAPI is the accepted future HTTP boundary, but full `/v1/*` API consolidation is not yet implemented. Preserve both paths until consolidation implementation and any deprecation plan are formally approved through `docs/ARCHITECTURE_DECISIONS.md`.
