# BBIOS OS Testing Strategy

## 1. Purpose

This document defines the authoritative testing strategy for BBIOS OS. It protects the current baseline and sets validation expectations for future persistence, API, authentication, and operations work.

## 2. Current Test Baseline

Confirmed current baseline:

- Command: `python3 -m unittest discover tests`
- Result: 95 tests passing
- Failures: 0
- Errors: 0
- Validated development runtime: Python 3.12.13

Pytest and CI are not confirmed by repository evidence and must not be treated as installed baseline tooling.

## 3. Testing Principles

- Focused tests first, full baseline second.
- Tests must be deterministic.
- Tests must not mutate production data.
- Tests must not rely on execution order.
- Test changes must reflect valid contract changes, not convenience.
- Infrastructure work requires tests before expansion.

## 4. Test Pyramid

- Unit tests: domain models, validation, utilities, pure calculations.
- Service tests: orchestration and business behavior.
- Handler and API contract tests: request/response mapping, status codes, envelopes, error codes.
- Repository tests: persistence behavior and isolation.
- Integration tests: workflows, connectors, onboarding, execution, monetization, and observability interactions.
- End-to-end tests: future canonical FastAPI flows after implementation of API consolidation.

## 5. Unit Tests

Unit tests should validate small, deterministic behavior in dataclasses, validators, pricing, metering, routing registries, mapping resolution, and error conditions.
Settings tests should verify defaults, environment overrides, parser failures, cache reset behavior, and absence of required secrets.

## 6. Service Tests

Service tests should verify Application Service orchestration without depending on HTTP transport. They should use temporary repositories, fakes, or stubs where appropriate.

## 7. Handler and API Contract Tests

Handler tests must verify:

- Supported methods and paths.
- Standardized response envelopes.
- Error codes.
- Route-not-found behavior.
- Request body handling.
- Compatibility with service facades.

FastAPI route contract tests are required for future Versioned API consolidation implementation.

## 8. Repository Tests

Repository tests must verify save, get, list, delete, invalid data handling, ordering where defined, isolation, and restart persistence. Future Repository interfaces require contract tests shared by JSON and database implementations.

## 9. Persistence Tests

Future persistence work must test:

- Repository contract equivalence.
- Transaction commit.
- Transaction rollback.
- Data serialization.
- Metadata handling.
- Concurrent access assumptions.
- Failure recovery.
- Compatibility with existing service behavior.

## 10. Migration Tests

Future Alembic work must test:

- Migration upgrade from empty database.
- Migration downgrade where safe.
- Seed/reference data creation.
- JSON-to-database transformation.
- Record-count parity.
- Relationship and constraint validation.

## 11. Integration Tests

Integration tests should cover workflows, connector calls, webhook invocation, onboarding, execution, monetization, and cross-module observability. External networks should be faked unless an approved integration environment exists.

## 12. End-to-End Tests

End-to-end tests should be added after canonical Versioned FastAPI Routes are implemented. They should validate user-visible flows without depending on test execution order.

## 13. Regression Tests

Every bug fix should include a regression test where practical. If no test is added, the review must record why.

## 14. Security Tests

Security tests should cover authentication, authorization, forbidden actions, missing credentials, invalid tokens, webhook signatures, secret non-exposure, and audit events. Current auth behavior is not a complete future security model.

## 15. Performance Tests

Performance tests are future work. They should focus on workflow execution duration, request latency, repository throughput, and concurrency after operational goals exist.

## 16. Observability Tests

Observability tests must verify request IDs, user identity, roles, event names, error events, workflow summaries, external call metadata, and listener behavior.

## 17. Test Data Management

- Use temporary directories and files for JSON repositories.
- Do not depend on production or developer-local data.
- Use fakes for external connectors.
- Keep fixtures small and explicit.
- Avoid hidden cross-test shared state.

## 18. Isolation Requirements

Tests must isolate filesystem paths, request context, observability streams, environment variables, and repository state. Future database tests must use isolated schemas or databases with reliable teardown.

## 19. Determinism Requirements

Tests must not rely on wall-clock ordering unless timestamps are part of the contract. Prefer explicit IDs and controlled fakes when behavior depends on ordering or failures.

## 20. Naming and Organization

- Root tests live under `tests/`.
- Package-local tests may live under `bbi_os/*/tests/`.
- Root mirror tests may import package-local tests.
- Test names should describe behavior and expected outcome.

## 21. Required Validation Sequence

For implementation work:

1. Run focused tests for the touched module.
2. Run `python3 -m unittest discover tests`.
3. Run `git diff --check`.
4. Review the diff.

Runtime standard changes must additionally validate clean-environment installation, package compilation, application imports, and `pyproject.toml` consistency with `.python-version`.

## 22. Coverage Expectations

No numeric coverage tool is confirmed. Coverage expectations are behavioral: changed public behavior needs focused tests, changed contracts need contract tests, changed persistence needs repository and migration tests, and changed security behavior needs allow/deny tests.

## 23. CI Strategy

CI/CD is not confirmed in the repository. Recommended future CI should run dependency installation, `python3 -m unittest discover tests`, frontend checks when relevant, `git diff --check`, and migration tests after persistence work begins.

## 24. Failure Handling

When tests fail:

- Record the exact command and failure.
- Determine whether the failure is existing, environment-related, or caused by the change.
- Fix only within authorized scope.
- Run focused tests before rerunning the full baseline.
- Stop for review if tests require unrelated changes.

## 25. Test Modification Governance

Do not modify tests merely to force passing results. Tests may change only when:

- The product contract changed through approval.
- The test is conclusively stale or invalid.
- The test itself contains a defect confirmed by repository evidence.

Human approval is required before changing tests for architectural drift.

## 26. Acceptance Gates

- Current baseline remains at least 87 tests, 0 failures, 0 errors; the baseline is currently 95 tests after focused settings tests were intentionally added.
- New infrastructure has rollback and failure tests.
- New Versioned API routes have contract tests.
- New Repositories have equivalence tests.
- New Observability events have assertions.
- No tests mutate production data or rely on execution order.
