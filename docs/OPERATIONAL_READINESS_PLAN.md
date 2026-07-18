# BBIOS OS Operational Readiness Plan

## 1. Document Control

- Document: Operational Readiness Plan
- Phase: 3.1 Operational Foundation
- Branch: `phase-2/repository-contract-cleanup`
- Baseline before Phase 3.1: commit `468e537`, 130 tests passing
- Status: Approved for incremental implementation
- Scope: operational observability, correlation IDs, exception handling, health, readiness, basic metrics, and request tracing
- Out of scope: PostgreSQL, SQLAlchemy, Alembic, migrations, Docker, authentication, authorization, CI/CD, deployment, runtime persistence switching, JSON removal, domain redesign, dependency injection containers, and service locators

## 2. Objectives

Phase 3.1 increases operational maturity while preserving the stable architecture established in Phase 2. The objective is not to add product features. The objective is to make the current backend service easier to operate, observe, and validate in a production-like environment.

## 3. Compatibility Gates

Every Phase 3.1 subphase must preserve:

- API response envelopes
- HTTP status codes
- Route paths
- Repository contracts
- Service contracts
- JSON persistence format
- Existing response-body `request_id` fields
- Existing tests

Failure of any gate blocks commit.

## 4. Architecture

The current runtime architecture remains:

```text
FastAPI
Request handlers and adapters
Application services
Repository protocols
JSON repository implementations
JSON persistence
```

Operational infrastructure wraps the FastAPI boundary and delegates business behavior to the existing handlers, adapters, and services.

## 5. Middleware Contract

Middleware is infrastructure. It must never contain business logic.

Allowed responsibilities:

- correlation IDs
- timing
- observability
- request lifecycle

Not allowed:

- validation
- authorization
- persistence
- business decisions

## 6. Correlation ID Policy

Correlation ID precedence:

1. A valid inbound `X-Request-ID` is reused.
2. A missing or invalid header generates a UUID.
3. The selected request ID is stored in request context.
4. Logs include the selected request ID.
5. Responses echo the selected ID in `X-Request-ID`.
6. Existing response-body `request_id` behavior is preserved.

## 7. Logging Architecture

Structured logging remains owned by `bbi_os.observability`. Phase 3.1 must extend the existing observer rather than introduce parallel logging.

Request lifecycle logs should capture method, endpoint, selected request ID, response status, and duration. Request bodies, credentials, tokens, secrets, and internal exception details must not be logged.

## 8. Exception Handling Architecture

FastAPI-level exception handling should map unexpected exceptions to generic operational responses without leaking internals. Existing handler-level error envelopes and status codes must remain unchanged.

Central exception handling is a separate subphase after correlation ID middleware.

## 9. Metrics Contract

Phase 3.1 metrics are process-local and JSON-only:

- requests received
- requests completed
- requests failed
- average duration
- current uptime
- application version

Metric names should be stable enough to map later to Prometheus or OpenTelemetry, but Phase 3.1 does not add those integrations.

## 10. Health and Readiness

`/health` answers: is the application process alive?

The existing lightweight `/health` behavior must remain compatible.

`/ready` answers: can this instance serve requests?

For the current JSON-backed system, readiness means:

- settings loaded
- JSON data path accessible
- required directories exist
- startup completed

Future PostgreSQL readiness can extend `/ready` after database work is approved.

## 11. Execution Tracing

Request tracing should use existing request context and execution summary support. Middleware establishes the outer FastAPI request context. Handler-style APIs may continue to manage their existing request lifecycle until a separate deduplication phase is approved.

## 12. Rollout Sequence

Phase 3.1A: Operational Readiness Design, no production code.

Phase 3.1B: Correlation ID middleware.

Phase 3.1C: Central exception handling.

Phase 3.1D: Readiness endpoint.

Phase 3.1E: Metrics endpoint.

Phase 3.1F: Documentation, regression validation, and architecture review.

## 13. Rollback Strategy

Each subphase must be independently revertible. Middleware and endpoints should be additive. Existing `/health` behavior, route paths, response envelopes, status codes, repository contracts, service contracts, and JSON persistence format must remain protected by tests.
