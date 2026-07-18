# BBIOS OS Architecture Decisions

## ADR Governance

Architecture Decision Records document significant technical choices for BBIOS OS. They are required when a change affects architectural boundaries, persistence, API compatibility, security, deployment, observability, or test strategy.

Status values:

- Proposed: recommended but not implemented or not fully validated.
- Accepted: approved as governing direction.
- Deprecated: no longer preferred but still relevant to existing behavior.
- Superseded: replaced by a later ADR.
- Rejected: considered and explicitly not chosen.

Numbering convention: `ADR-###`, assigned sequentially. Each ADR records authorship through commit history and review notes. Approval occurs through human review. Superseding decisions must name the older ADR and explain compatibility implications. ADRs should be reviewed when related tests, production behavior, dependencies, or infrastructure assumptions change.

## ADR Index

- ADR-001: Preserve Backward Compatibility During Architectural Migration - Accepted
- ADR-002: Adopt Layered Application Architecture - Accepted
- ADR-003: Use FastAPI as the Canonical HTTP Boundary - Accepted
- ADR-004: Use Dependency Injection for Rich Service Composition - Accepted
- ADR-005: Keep Business Logic Out of HTTP Handlers - Accepted
- ADR-006: Introduce PostgreSQL Through Repository Abstractions - Proposed
- ADR-007: Use SQLAlchemy and Alembic for Persistence Management - Proposed
- ADR-008: Require Explicit Transaction Boundaries - Proposed
- ADR-009: Treat Observability as a Cross-Cutting Requirement - Accepted
- ADR-010: Require Automated Tests Before Infrastructure Expansion - Accepted
- ADR-011: Maintain Versioned APIs and Controlled Deprecation - Accepted
- ADR-012: Prohibit Direct Access to Private Repository Methods - Accepted
- ADR-013: Centralize Application Settings with Standard Library Configuration - Accepted

## ADR-001 - Preserve Backward Compatibility During Architectural Migration

- Status: Accepted
- Date: 2026-07-18
- Context: The cockpit stabilization preserved `/cockpit/*` FastAPI prototype behavior while adding a richer cockpit compatibility facade.
- Decision: Architectural migrations must preserve known public behavior unless a later ADR approves deprecation or removal.
- Alternatives Considered: Immediate replacement of prototype routes; test-only changes.
- Consequences: Migration work may carry temporary Compatibility Layers.
- Risks: Compatibility layers can become permanent unless tracked.
- Validation: Existing route imports and `python3 -m unittest discover tests`.
- Review Trigger: API consolidation or route deprecation proposal.

## ADR-002 - Adopt Layered Application Architecture

- Status: Accepted
- Date: 2026-07-18
- Context: The repository already separates Routers, Handlers / Adapters, Application Services, Workflow Controls, and Repositories.
- Decision: Use layered architecture as the governing pattern.
- Alternatives Considered: Router-centric logic; direct persistence calls from handlers.
- Consequences: More explicit wiring, clearer test seams.
- Risks: Over-abstraction if interfaces are created before use.
- Validation: Service and handler contract tests.
- Review Trigger: New module boundaries or major feature additions.

## ADR-003 - Use FastAPI as the Canonical HTTP Boundary

- Status: Accepted
- Date: 2026-07-18
- Context: Current FastAPI routes coexist with internal handler-style APIs. The approved target architecture identifies Versioned FastAPI Routes as the future canonical HTTP boundary, but full `/v1/*` API consolidation is not yet implemented.
- Decision: FastAPI is the approved canonical future HTTP boundary. Existing prototype routes and internal handler paths remain Compatibility Layers during migration, and acceptance of this architectural direction does not claim that API consolidation is complete.
- Alternatives Considered: Continue `BaseHTTPRequestHandler`; expose only internal handlers.
- Consequences: Requires route inventory, compatibility handling, and handler delegation.
- Risks: Breaking existing tests or prototype routes.
- Validation: FastAPI route contract tests and handler tests.
- Review Trigger: Start of API consolidation implementation or any change to supported HTTP route surfaces.

## ADR-004 - Use Dependency Injection for Rich Service Composition

- Status: Accepted
- Date: 2026-07-18
- Context: Rich cockpit, execution, monetization, pipeline, onboarding, and workflow tests compose services with explicit collaborators.
- Decision: Prefer explicit constructor dependencies for rich service composition.
- Alternatives Considered: Module-level singletons everywhere.
- Consequences: Easier focused tests and future database repository substitution.
- Risks: Optional dependencies may be necessary for compatibility but should remain controlled.
- Validation: Cockpit and service tests.
- Review Trigger: New service construction patterns.

## ADR-005 - Keep Business Logic Out of HTTP Handlers

- Status: Accepted
- Date: 2026-07-18
- Context: README states Router Layer has no business logic; internal handlers generally delegate to services.
- Decision: Routers and Handlers / Adapters translate transport concerns and delegate business behavior.
- Alternatives Considered: Implement validation and orchestration in handlers.
- Consequences: Services remain testable outside HTTP.
- Risks: Thin handlers still need consistent error mapping.
- Validation: Handler contract tests and service tests.
- Review Trigger: Any route or handler adding domain rules.

## ADR-006 - Introduce PostgreSQL Through Repository Abstractions

- Status: Proposed
- Date: 2026-07-18
- Context: JSON repositories isolate current persistence, but PostgreSQL is not implemented.
- Decision: Introduce PostgreSQL by adding database-backed Repositories behind existing service seams.
- Alternatives Considered: Direct ORM access from services or handlers; big-bang storage rewrite.
- Consequences: Enables parity tests and rollback to JSON during migration.
- Risks: Current repository interfaces may need transaction-aware refinement.
- Validation: Repository contract equivalence tests.
- Review Trigger: Persistence foundation implementation.

## ADR-007 - Use SQLAlchemy and Alembic for Persistence Management

- Status: Proposed
- Date: 2026-07-18
- Context: Approved future direction names SQLAlchemy 2.x and Alembic; neither exists in the repository today.
- Decision: Use SQLAlchemy for database access and Alembic for version-controlled migrations after dependency and settings work.
- Alternatives Considered: Raw SQL only; unmanaged schema changes.
- Consequences: Requires metadata, sessions, migration workflow, and migration tests.
- Risks: ORM model leakage into domain and service layers.
- Validation: Migration upgrade tests and repository tests.
- Review Trigger: Adding persistence dependencies.

## ADR-008 - Require Explicit Transaction Boundaries

- Status: Proposed
- Date: 2026-07-18
- Context: Current JSON workflows perform multiple related writes without database transactions.
- Decision: Database-backed operations must define transaction ownership explicitly.
- Alternatives Considered: Each repository commits independently.
- Consequences: Requires unit-of-work or request transaction pattern.
- Risks: Ambiguous external side effects around connector calls.
- Validation: commit, rollback, failure recovery, and concurrency tests.
- Review Trigger: First database-backed multi-write service.

## ADR-009 - Treat Observability as a Cross-Cutting Requirement

- Status: Accepted
- Date: 2026-07-18
- Context: `bbi_os/observability.py` provides request context, structured logs, metrics, listeners, and execution summaries.
- Decision: Observability events and request identity must be preserved across architectural changes.
- Alternatives Considered: Module-specific ad hoc logging.
- Consequences: New services must emit predictable events.
- Risks: Sensitive metadata may be logged without redaction controls.
- Validation: Observability tests and security review.
- Review Trigger: Logging schema or request context changes.

## ADR-010 - Require Automated Tests Before Infrastructure Expansion

- Status: Accepted
- Date: 2026-07-18
- Context: Baseline restoration is validated by `python3 -m unittest discover tests`.
- Decision: Infrastructure work requires automated tests before expansion.
- Alternatives Considered: Manual validation only.
- Consequences: Slower but safer migrations.
- Risks: Tests can lag architecture if not maintained.
- Validation: Focused tests then full baseline.
- Review Trigger: New infrastructure workstream.

## ADR-011 - Maintain Versioned APIs and Controlled Deprecation

- Status: Accepted
- Date: 2026-07-18
- Context: Internal routing uses `/v1/*`, while README documents `/cockpit/*` prototype routes.
- Decision: Versioned API surfaces are required for new API work, and deprecation must be explicit.
- Alternatives Considered: Silent endpoint replacement.
- Consequences: Compatibility documentation and dual tests may be needed.
- Risks: Temporary route duplication.
- Validation: Route contract and compatibility tests.
- Review Trigger: Adding, renaming, or removing routes.

## ADR-012 - Prohibit Direct Access to Private Repository Methods

- Status: Accepted
- Date: 2026-07-18
- Context: Current cockpit compatibility code temporarily reads execution records through a private repository method because no public list-all method exists.
- Decision: Application Services must use public Repository contracts. Private Repository methods such as `_read()` are implementation details and must not be used by application code as a long-term pattern.
- Alternatives Considered: Continue private access as a convenience.
- Consequences: The current cockpit `_read()` usage is formally recorded technical debt. That exception remains until a bounded Repository-contract correction is approved; accepting this rule does not require modifying production code in this documentation task.
- Risks: Private access can break if repository internals change.
- Validation: Service tests after public API replacement.
- Review Trigger: Repository interface refinement.

## ADR-013 - Centralize Application Settings with Standard Library Configuration

- Status: Accepted
- Date: 2026-07-18
- Context: Phase 1 foundation work requires a single settings layer before persistence, authentication, and deployment work. The repository already uses dataclasses and does not require an additional settings dependency for current application metadata, route prefix, local runtime values, and JSON storage path defaults. Python 3.12.13 is the validated development runtime; Python 3.9 is no longer a supported project runtime.
- Decision: Use `bbi_os/settings.py` as the canonical settings module, backed by a frozen dataclass and explicit standard-library environment parsing.
- Alternatives Considered: Pydantic settings; scattered `os.environ` reads; adding dotenv.
- Consequences: Current FastAPI app creation can consume app metadata and route prefix without changing default routes or behavior. Runtime support claims must be backed by clean-environment dependency installation, imports, compile checks, and the full `unittest` baseline.
- Risks: Existing credential-specific environment reads remain in authentication and integration modules until a future bounded security/configuration task addresses secrets.
- Validation: Focused settings tests, import checks, compile checks, and full `unittest` baseline.
- Review Trigger: Adding persistence, authentication, deployment, secret management, or runtime environment expansion.
