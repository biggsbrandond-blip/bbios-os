# BBIOS OS Persistence Abstraction

## 1. Document Control

- Document: Persistence Abstraction
- Phase: 2G Persistence Abstraction
- Branch: `phase-2/repository-contract-cleanup`
- Baseline before Phase 2G: commit `e97ce06`, 125 tests passing
- Scope: repository protocol contracts and service dependency abstraction
- Out of scope: PostgreSQL, SQLAlchemy, Alembic, ORM models, database sessions, migrations, authentication, deployment, route changes, response-envelope changes, JSON schema changes, filesystem layout changes, dependency injection frameworks, service locators, and global containers

## 2. Executive Summary

Phase 2G introduces a narrow persistence abstraction layer in `bbi_os/persistence.py`. The abstraction lets selected services type their repository collaborators by stable public contracts instead of concrete JSON repository classes.

JSON remains the only runtime persistence implementation. The new protocols describe existing public methods and do not change repository behavior, serialization, file layout, route behavior, response envelopes, or service outputs.

## 3. Persistence Architecture

The current persistence architecture remains:

```text
Handlers and FastAPI adapters
Application services
Repository protocols
JSON repository implementations
JSON files
```

The approved future insertion point for PostgreSQL or another durable store is below the repository protocol layer. Future implementations must satisfy the same public contracts before being wired into application services.

## 4. Protocol Ownership

`bbi_os/entity_repository.py` continues to own the existing `EntityRepository` protocol for entity records. Phase 2G does not duplicate that contract.

`bbi_os/persistence.py` owns the new narrow protocols:

- `TaskRepository`
- `ExecutionStateRepositoryContract`
- `ClientPlanRepository`
- `UsageRepository`

These protocols are intentionally small and mirror only the public methods currently consumed by selected services.

## 5. Repository Contract Map

| Protocol | Default JSON implementation | Current service consumers | Public methods |
| --- | --- | --- | --- |
| `EntityRepository` | `JsonEntityRepository` | Client management, execution, monetization, onboarding actions, cockpit dashboards | `list`, `get`, `exists`, `count`, `save`, `delete` |
| `TaskRepository` | `JsonTaskRepository` | `TaskService` | `list`, `get`, `exists`, `count`, `save`, `delete` |
| `ExecutionStateRepositoryContract` | `ExecutionStateRepository` | `ClientExecutionService` | `save`, `get`, `exists`, `count`, `list`, `latest_for_client`, `list_for_client` |
| `ClientPlanRepository` | `ClientPlanRegistry` | `ClientMonetizationService` | `plan_for`, `assign` |
| `UsageRepository` | `UsageTracker` | `ClientMonetizationService` | `record`, `for_client`, `total_units`, `recent_count` |

## 6. JSON Implementation Role

The JSON repositories remain canonical runtime implementations for the current baseline. Existing constructors and composition paths still provide JSON-backed repositories by default where they did before Phase 2G.

The abstraction layer is a typing and substitution boundary. It does not add runtime selection, change storage paths, change record ordering, alter mutation semantics, or introduce a new persistence backend.

## 7. Future PostgreSQL Insertion Point

Future database work should implement the repository protocols with parity tests before any service wiring changes. Database-backed implementations would sit behind the same public methods currently used by services.

Required future work includes schema design, transaction ownership, migration generation, rollback planning, runtime configuration, data migration, repository parity tests, and compatibility validation.

No PostgreSQL, SQLAlchemy, Alembic, database sessions, migrations, or ORM models are implemented in Phase 2G.

## 8. Phase 2G Compatibility Guarantees

- Existing zero-argument or established service construction remains valid.
- Current JSON repositories remain accepted collaborators.
- Protocol-compatible test doubles can substitute for selected repositories.
- Task persistence still writes the same dictionary record shape.
- Execution state persistence still uses `ClientExecutionRecord` values.
- Monetization plan and usage behavior remains unchanged.
- Existing APIs, handlers, response envelopes, status codes, exception messages, and JSON files remain unchanged.

## 9. Deferred Persistence Debt

1. Workflow, workflow-template, integration, webhook, cockpit dashboard, and execution-engine collaborators still expose concrete repository annotations.
2. Runtime composition still directly instantiates JSON repositories in established call sites.
3. A database-backed implementation strategy remains unapproved.
4. Repository record DTO migration remains deferred.
5. Transaction boundaries and unit-of-work ownership remain deferred.

## 10. Phase 2G Exit Criteria

- Selected service constructors depend on repository protocols instead of concrete JSON repository classes.
- Existing JSON repositories satisfy the relevant public contracts.
- Focused unittest coverage proves repository substitution for the changed services.
- Default runtime behavior remains JSON-backed and unchanged.
- Full unittest discovery passes.
- `compileall` passes.
- `git diff --check` passes.
- No files are staged, committed, pushed, merged, or tagged during the Phase 2G implementation task.
