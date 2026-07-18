# BBIOS OS Engineering Master Plan

## 1. Document Control

- Status: Accepted as governing engineering direction
- Date: 2026-07-18
- Scope: BBIOS OS backend, cockpit integration, tests, and future infrastructure sequencing
- Related documents: `docs/ARCHITECTURE_DECISIONS.md`, `docs/DEVELOPMENT_STANDARDS.md`, `docs/TESTING_STRATEGY.md`, `docs/CONTRIBUTING.md`
- Current evidence base: `README.md`, cockpit stabilization work, JSON repositories, internal handlers, service modules, observability modules, and passing `unittest` baseline

## 2. Executive Summary

BBIOS OS is currently a modular Python backend with a preserved FastAPI cockpit prototype, internal Handler / Adapter classes for versioned routes, Application Services, Domain Services, Workflow Control components, JSON-file Repository implementations, process-local Observability, and a React cockpit UI. The approved direction is to evolve this baseline into a versioned FastAPI application with clear boundaries, explicit configuration, transaction-aware persistence, and controlled backward compatibility.

PostgreSQL, SQLAlchemy, Alembic, Docker, CI/CD, and production deployment are planned work, not current implementation.

## 3. Engineering Mission

Build BBIOS OS as a maintainable enterprise system whose behavior is traceable, testable, secure, and migration-ready. Every change must preserve known working behavior unless a human-approved decision explicitly authorizes a compatibility break.

## 4. Current Baseline

Confirmed current baseline:

- FastAPI app exists in `bbi_os/cockpit/api.py`.
- `bbi_os/__main__.py` exposes an app factory with root, health, and cockpit router inclusion.
- The README documents prototype routes under `/cockpit/*`.
- Cockpit baseline drift has been stabilized by adding a compatibility Handler / Adapter and a richer `CockpitService` facade while preserving zero-argument `CockpitService()`.
- Backend dependencies are declared in `pyproject.toml`, with Python 3.12.13 recorded in `.python-version` as the validated development runtime and `>=3.12,<3.13` declared as the supported project range.
- Centralized local application settings are implemented in `bbi_os/settings.py`.
- The immediate test baseline is `python3 -m unittest discover tests`.
- Current baseline result after Phase 1 foundation implementation: 95 tests passing, 0 failures, 0 errors.
- Persistence is JSON-file and in-memory; PostgreSQL is not implemented.

## 5. Confirmed System Capabilities

Confirmed capabilities include:

- Prototype cockpit client creation, lookup, search, and test pipeline.
- Versioned internal request handling through `TaskRequestHandler` and `EntityRouteRegistry`.
- Task CRUD through `TaskService` and `JsonTaskRepository`.
- Generic entity persistence through `JsonEntityRepository`.
- Workflow definitions, instances, step execution, retry, rollback, and history through `WorkflowEngine` and `WorkflowRepository`.
- Workflow templates and lineage through `WorkflowTemplateService` and `WorkflowTemplateRepository`.
- Client pipeline, onboarding, execution, monetization, connector, webhook, cockpit dashboard, and cockpit control modules.
- Structured response envelopes where internal handlers use `success_response()` and `error_response()`.
- Structured Observability through request context, JSON log records, event listeners, and execution summaries.

## 6. Current Architecture

Current architecture is mixed but bounded:

- Router: FastAPI routes in `bbi_os/cockpit/router.py`.
- Handler / Adapter: internal classes such as `TaskRequestHandler`, `WorkflowApiHandler`, `ClientExecutionApiHandler`, `ClientMonetizationApiHandler`, `ClientManagementApiHandler`, and `CockpitApiHandler`.
- Application Service: orchestration classes such as `TaskService`, `ClientPipelineService`, `OnboardingService`, `ClientExecutionService`, `ClientMonetizationService`, and `CockpitService`.
- Domain Service and Workflow Control: workflow engines, action registries, execution controls, cockpit controls, and dashboard renderers.
- Repository: JSON-backed classes for tasks, entities, workflows, templates, execution state, client plans, usage, and integrations.
- Persistence: in-memory prototype state plus JSON-file storage.
- Observability: process-local structured logging and metrics.

## 7. Approved Target Architecture

Approved target architecture:

```text
Client / Frontend
        |
Versioned FastAPI Routes
        |
Request Handlers / Adapters
        |
Application Services
        |
Domain Services and Workflow Controls
        |
Repository Interfaces
        |
Persistence
        |
PostgreSQL
```

Cross-cutting concerns:

- Observability spans routes, handlers, services, repositories, workflows, and external calls.
- Authentication and authorization are request-boundary controls.
- Configuration is centralized infrastructure, not scattered module state.
- Python runtime upgrades require validation in a clean environment before support claims are changed.
- Backward compatibility is required during migration.

This target architecture is approved direction, not fully implemented current state.

## 8. Architectural Principles

- Preserve public behavior until a documented Architecture Decision Record approves a change.
- Keep business logic out of Routers and Handlers / Adapters.
- Use Application Services for orchestration.
- Keep Domain Services and Workflow Controls responsible for domain-specific rules and state transitions.
- Access persistence through Repository interfaces.
- Treat Observability, security, validation, and rollback planning as first-class requirements.
- Prefer small, reversible changes over broad rewrites.

## 9. Engineering Governance Model

Governance is documentation-led:

- Significant technical direction requires an Architecture Decision Record in `docs/ARCHITECTURE_DECISIONS.md`.
- Bounded implementation plans should cite repository evidence.
- Tests must define or confirm behavior before infrastructure expansion.
- Human approval is required before broad architecture changes, persistence changes, authentication changes, deployment changes, or compatibility breaks.

## 10. Development Lifecycle

Standard lifecycle:

1. Investigate repository evidence.
2. Document findings and proposed scope.
3. Obtain approval for implementation.
4. Implement bounded changes.
5. Run focused tests.
6. Run `python3 -m unittest discover tests`.
7. Review unified diff.
8. Commit intentionally.
9. Open a pull request when requested.
10. Merge after review and approval.

## 11. Phase Plan

### Phase 0 - Baseline Stabilization

- Objective: restore a trustworthy test baseline.
- Scope: cockpit drift resolution, test baseline restoration, no database work.
- Prerequisites: accepted readiness assessment and cockpit stabilization plan.
- Deliverables: `CockpitApiHandler`, compatible `CockpitService` facade, passing test suite.
- Validation: focused cockpit tests and full `python3 -m unittest discover tests`.
- Risks: accidental route behavior changes, overextending the cockpit fix.
- Exit criteria: 87 tests pass with 0 failures and 0 errors.
- Prohibited scope expansion: PostgreSQL, SQLAlchemy, Alembic, auth changes, frontend changes, broad API consolidation.
- Status: Complete based on repository evidence.

### Phase 1 - Engineering Foundation

- Objective: define engineering rules before infrastructure work.
- Scope: documentation package, dependency manifest, centralized settings, development standards, ADR process.
- Prerequisites: Phase 0 complete.
- Deliverables: this documentation package, backend dependency manifest, settings module, environment example, and focused settings tests.
- Validation: docs exist, are internally consistent, focused settings tests pass, and full tests still pass.
- Risks: documenting future capabilities as current behavior.
- Exit criteria: human-approved foundation docs, dependency manifest, centralized settings, and no prohibited infrastructure work.
- Prohibited scope expansion: implementation of database, auth, deployment, or API redesign.
- Status: Complete based on repository evidence.

### Phase 2 - Persistence Foundation

- Objective: introduce PostgreSQL safely behind Repository boundaries.
- Scope: PostgreSQL, SQLAlchemy, Alembic, repository migration strategy, transaction boundaries, JSON metadata decisions, compatibility requirements.
- Prerequisites: dependency manifest, settings layer, ADR approval, repository contract tests.
- Deliverables: SQLAlchemy models, Alembic migrations, database repositories, migration tooling, rollback plan.
- Validation: repository equivalence tests, migration upgrade, safe downgrade where applicable, transaction commit/rollback tests.
- Risks: relationship modeling mistakes, timestamp drift, concurrency assumptions, metadata loss.
- Exit criteria: JSON and PostgreSQL implementations show behavioral parity.
- Prohibited scope expansion: unrelated feature work or authentication redesign.

### Phase 3 - Authentication and Authorization

- Objective: formalize request-boundary identity and authorization.
- Scope: identity model, role-based access, request authentication, authorization enforcement, audit requirements.
- Prerequisites: canonical configuration and API boundary decisions.
- Deliverables: auth policy, request identity integration, audit event expectations, security tests.
- Validation: allowed/denied route tests, audit log tests, no secret exposure.
- Risks: breaking anonymous prototype behavior prematurely.
- Exit criteria: documented compatibility and authorization coverage.
- Prohibited scope expansion: unrelated persistence or UI redesign.

### Phase 4 - API Consolidation

- Objective: make Versioned API routing canonical through FastAPI.
- Scope: canonical `/v1/*` routes, FastAPI integration, Handler / Adapter pattern, service/repository layering, compatibility and deprecation strategy.
- Prerequisites: ADR approval and passing handler contract tests.
- Deliverables: FastAPI route modules delegating to Handlers / Adapters and Application Services.
- Validation: route contract tests, internal handler tests, backward-compatible endpoint tests.
- Risks: breaking README-documented prototype routes or frontend calls.
- Exit criteria: documented canonical route inventory and migration/deprecation plan.
- Prohibited scope expansion: persistence redesign without Phase 2 controls.

### Phase 5 - Production Operations

- Objective: prepare operational runtime standards.
- Scope: Docker, CI/CD, environment separation, health checks, structured logging, monitoring, deployment readiness.
- Prerequisites: stable tests, settings layer, health semantics, deployment ADRs.
- Deliverables: container/runtime files, CI validation, environment documentation, monitoring plan.
- Validation: reproducible environment, automated tests, health and smoke checks.
- Risks: premature operational complexity.
- Exit criteria: repeatable deployment process approved by review.
- Prohibited scope expansion: changing domain behavior to satisfy deployment tooling.

### Phase 6 - Enterprise Scalability

- Objective: support scale and resilience after core architecture is stable.
- Scope: distributed execution considerations, queueing, caching, tenant isolation, resilience, performance optimization.
- Prerequisites: PostgreSQL foundation, canonical API, observability, operational baseline.
- Deliverables: scalability ADRs, performance tests, tenant model, queue/retry strategy.
- Validation: load tests, failure recovery tests, tenant isolation tests.
- Risks: adding infrastructure before measured need.
- Exit criteria: documented service-level goals and validated capacity improvements.
- Prohibited scope expansion: speculative abstractions without active use cases.

## 12. Workstream Dependencies

- Persistence depends on settings, dependency manifest, repository contracts, and transaction decisions.
- Authentication depends on API boundary and request context decisions.
- API consolidation implementation depends on preserving current `/cockpit/*` compatibility and existing `/v1/*` handler contracts.
- Operations depends on reproducible dependencies, centralized settings, and deterministic tests.
- Scalability depends on persistence and observability maturity.

## 13. Quality Gates

- No implementation begins without clear scope and evidence.
- Focused tests run before full tests.
- Full baseline command is `python3 -m unittest discover tests`.
- `git diff --check` must pass before review.
- Docs must distinguish current behavior from target architecture and planned work.
- New infrastructure requires rollback planning.

## 14. Security Strategy

Current behavior includes environment-based bearer-token mapping and connector/webhook secret environment variable names. Future security work must centralize configuration, prevent committed secrets, preserve auditability, and enforce authorization at Versioned API boundaries. Current docs must not present authentication as production-grade.

## 15. Persistence Strategy

Current persistence is JSON-file and in-memory. Approved strategy is to introduce PostgreSQL through Repository interfaces, SQLAlchemy 2.x, Alembic, and explicit transaction ownership. JSON metadata fields require deliberate relational versus JSONB decisions before migration.

## 16. API Strategy

Current API surfaces include FastAPI prototype routes and internal handler contracts. The accepted target is Versioned FastAPI Routes delegating to Handlers / Adapters, which delegate to Application Services. Full `/v1/*` API consolidation is not yet implemented. Existing prototype routes remain a Compatibility Layer until deprecation is approved.

## 17. Observability Strategy

Observability remains cross-cutting. Request IDs, user identity, event names, structured metadata, execution summaries, workflow events, external calls, and error events must be preserved or deliberately migrated through ADR-approved changes.

## 18. Testing Strategy Summary

The authoritative testing strategy is `docs/TESTING_STRATEGY.md`. The current baseline is `python3 -m unittest discover tests`, with 95 tests passing after focused settings coverage was added. Future work must add focused tests before infrastructure changes and preserve deterministic isolation.

## 19. Deployment Strategy

No Docker, CI/CD, or production deployment system is currently confirmed. Deployment work belongs in Phase 5 after dependency, settings, testing, and API boundaries are stable.

## 20. Documentation Strategy

Repository docs must be evidence-based, version-controlled, and updated with architectural changes. ADRs record decisions; standards record rules; testing docs record validation; contribution docs record workflow.

## 21. Technical Debt Register

- Mixed FastAPI prototype and internal handler architecture.
- JSON repositories duplicate atomic read/write code.
- Current cockpit rich facade uses a compatibility bridge while API consolidation is deferred.
- Current cockpit compatibility code temporarily calls a private Repository `_read()` method; this is technical debt until a public execution-list Repository contract is approved.
- Some code paths use flexible dictionaries and `Any` where stable interfaces should later be introduced.
- Current persistence lacks explicit transaction ownership.
- Backend dependency manifest and centralized settings exist; future infrastructure must consume them through bounded changes.

## 22. Risk Register

- Compatibility risk during API consolidation.
- Data integrity risk during PostgreSQL migration.
- Concurrency risk from process-local locks and read-modify-write JSON storage.
- Security risk from scattered environment handling.
- Observability risk if event metadata changes without contract tests.
- Governance risk if tests are modified to force passing results.

## 23. Definition of Done

A change is done when scope is respected, implementation matches approved design, focused tests pass, `python3 -m unittest discover tests` passes, docs are updated when needed, diff is reviewed, risks are recorded, and no prohibited changes are included.

## 24. Change-Control Rules

- Do not change public routes, response shapes, storage formats, or auth behavior silently.
- Do not introduce infrastructure without rollback and validation plans.
- Do not modify tests solely to make implementation pass.
- Use ADRs for architectural decisions.
- Stop for human approval when scope expands.

## 25. Recommended Immediate Next Phase

Proceed to human review of the Phase 1 foundation implementation before any PostgreSQL persistence work begins.

## 26. Completion Criteria

The engineering foundation is complete when the five foundation docs are present, internally consistent, free of unsupported implementation claims, the backend manifest and centralized settings are in place, reviewed by humans, and the full test baseline remains green.
