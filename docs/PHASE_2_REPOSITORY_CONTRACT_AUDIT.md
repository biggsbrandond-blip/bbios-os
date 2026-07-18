# BBIOS OS Phase 2 Repository Contract Audit

## 1. Executive Summary

Phase 2A reviewed the repository contract surface after the published `v0.1.0` baseline. Confirmed current state: BBIOS OS is a Python 3.12 project with FastAPI cockpit prototype routes, internal `/v1/*` handler-style routes, layered services, JSON-backed repositories, process-local observability, and a React cockpit UI.

The most important safe cleanup found and implemented was removal of application-service dependence on the private execution repository `_read()` method. `ExecutionStateRepository.list()` now provides the public all-record read contract, and `CockpitService._execution_records()` uses it. `_read()` remains in place as a private implementation detail for repository internals.

No PostgreSQL, SQLAlchemy, Alembic, authentication, Docker, CI/CD, deployment, route consolidation, endpoint removal, request shape change, response shape change, or file format change was introduced.

## 2. Current Architecture Map

- Runtime entry points: `bbi_os/cockpit/api.py` defines a module-level FastAPI `app`; `bbi_os/__main__.py` defines `create_app()` and a second module-level FastAPI `app`.
- Prototype API: `bbi_os/cockpit/router.py` exposes `/create-client`, `/client/{client_id}`, `/clients/search`, and `/test-pipeline` under `settings.api_prefix`, which defaults to `/cockpit` in `bbi_os/settings.py`.
- Versioned internal API: `TaskRequestHandler` in `bbi_os/task_management/api.py` uses `EntityRouteRegistry` in `bbi_os/entity_routing.py` to dispatch `/v1/*` routes to handler adapters.
- Cockpit compatibility API: `CockpitApiHandler` in `bbi_os/cockpit/handler.py` handles `/v1/cockpit/*` request paths for tests and frontend expectations.
- Services: `TaskService`, `ClientExecutionService`, `ClientMonetizationService`, `ClientPipelineService`, `OnboardingService`, `ClientManagementService`, and `CockpitService` own application behavior.
- Repositories: JSON-backed repositories currently persist tasks, entities, workflow definitions/instances, workflow templates/lineage, execution state, plan assignments, usage events, and integrations.
- Frontend: `cockpit-ui/src/lib/api.js` calls `/v1/cockpit/*` read paths and `/clients` client-management paths.

## 3. Package Contract Findings

### RC-PKG-001 - Minimal package exports

- Location: `bbi_os/__init__.py`, package-level `__init__.py` files under `bbi_os/*`.
- Current behavior: Package files contain docstrings only and do not define `__all__`.
- Intended contract: Public imports are module-level paths such as `bbi_os.settings`, `bbi_os.cockpit.api`, `bbi_os.cockpit.service`, `bbi_os.client_execution.state`, and handler/service modules used by tests.
- Risk: Low. Missing exports are not currently breaking tests, but they leave public package boundaries implicit.
- Recommended action: Add explicit exports only after a public import inventory is approved.
- Safe now: Deferred. Adding broad exports could accidentally widen the public API.
- Tests protecting behavior: `tests/test_*` and nested module re-export tests import specific modules directly.

### RC-PKG-002 - Test package compatibility wrappers

- Location: top-level files such as `tests/test_cockpit.py` and `tests/test_execution.py`.
- Current behavior: Top-level tests import nested package tests with wildcard imports.
- Intended contract: `python -m unittest discover tests` remains the canonical test entry.
- Risk: Low operational risk, moderate maintenance risk because nested tests are part of the discoverable contract indirectly.
- Recommended action: Keep wrappers until test layout governance approves consolidation.
- Safe now: No.
- Tests protecting behavior: Full unittest discovery.

### RC-PKG-003 - Import side effects through module-level objects

- Location: `bbi_os/cockpit/api.py`, `bbi_os/cockpit/router.py`, `bbi_os/__main__.py`, `bbi_os/task_management/api.py`.
- Current behavior: Importing these modules constructs FastAPI apps, an `APIRouter`, a module-level `CockpitService()`, an `Authenticator()`, and an `EntityRouteRegistry()`.
- Intended contract: Import-time construction should remain lightweight and deterministic until app factory consolidation is approved.
- Risk: Medium. Side effects are currently simple, but future settings, auth, or persistence changes could make imports stateful.
- Recommended action: Consolidate app creation around `create_app()` in a later API-runtime cleanup.
- Safe now: Deferred.
- Tests protecting behavior: `tests/test_settings.py`, `tests/test_task_api.py`, `tests/test_cockpit.py`.

## 4. Runtime Contract Findings

### RC-RUN-001 - Duplicate FastAPI app instances

- Location: `bbi_os/cockpit/api.py`, `bbi_os/__main__.py`.
- Current behavior: Both files create a FastAPI `app`; `bbi_os/__main__.py` also provides `create_app()`.
- Intended contract: `create_app()` should become the canonical application factory; FastAPI remains the accepted future HTTP boundary.
- Risk: Medium. Duplicate apps can drift in metadata, route inclusion, and health endpoints.
- Recommended action: Later consolidate runtime entry points while preserving existing import paths.
- Safe now: Deferred because changing app imports may affect callers.
- Tests protecting behavior: `tests/test_settings.py` validates app settings indirectly; API route tests are not yet comprehensive for FastAPI.

### RC-RUN-002 - Centralized settings are partial

- Location: `bbi_os/settings.py`, `bbi_os/auth.py`, `bbi_os/integrations/outbound.py`, `bbi_os/integrations/webhooks.py`.
- Current behavior: App metadata, host, port, debug, API prefix, and data dir use `get_settings()`; auth tokens and integration secrets read environment directly.
- Intended contract: `bbi_os.settings.get_settings()` is canonical for non-secret application settings; secret access remains a deferred security/configuration task.
- Risk: Medium if future secret handling is changed casually.
- Recommended action: Document and later centralize secret configuration through an approved security task.
- Safe now: No.
- Tests protecting behavior: `tests/test_settings.py`, `tests/test_auth.py`, `tests/test_integrations.py`.

## 5. API Contract Findings

### RC-API-001 - Prototype cockpit routes remain `/cockpit/*`

- Location: `bbi_os/cockpit/router.py`.
- Current behavior: FastAPI prototype endpoints return direct dictionaries such as `{"status": "success", "client": ...}`.
- Intended contract: Preserve these routes as compatibility behavior until API consolidation is approved.
- Risk: Medium. Their response shape differs from internal handler envelopes.
- Recommended action: Keep behavior unchanged; document deprecation only after replacement routes exist.
- Safe now: No route change.
- Tests protecting behavior: `bbi_os/cockpit/tests/test_client_management.py` and cockpit baseline tests indirectly protect coexistence.

### RC-API-002 - Versioned handler envelope

- Location: `bbi_os/task_management/api.py`, `bbi_os/response_contract.py`, `bbi_os/cockpit/handler.py`.
- Current behavior: Internal handlers return envelopes with `request_id`, `status`, `data`, and `execution_summary`.
- Intended contract: This envelope should be preserved for `/v1/*` handler-style APIs and future FastAPI route adapters.
- Risk: High if changed, because tests and frontend error handling rely on it.
- Recommended action: Add explicit route-contract tests during API consolidation.
- Safe now: No broad change.
- Tests protecting behavior: `tests/test_task_api.py`, `tests/test_cockpit.py`, workflow, integration, monetization, onboarding, pipeline, and execution tests.

### RC-API-003 - Frontend expects `/v1/cockpit/*` and `/clients`

- Location: `cockpit-ui/src/lib/api.js`, `cockpit-ui/README.md`.
- Current behavior: Read views call `/v1/cockpit/system-overview`, `/usage`, `/billing-summary`, `/executions`, and `/client/{id}`. Client list/create call `/clients`.
- Intended contract: Frontend/backend contract is current but not fully documented in backend runtime wiring.
- Risk: Medium. FastAPI default prefix remains `/cockpit`, so `/v1/cockpit/*` is not served by `bbi_os/cockpit/api.py` as currently written.
- Recommended action: Later create explicit versioned FastAPI route adapters or document the separate internal handler runtime.
- Safe now: Deferred; adding routes changes public API.
- Tests protecting behavior: `bbi_os/cockpit/tests/test_cockpit.py`, `bbi_os/cockpit/tests/test_client_management.py`.

## 6. Service Contract Findings

### RC-SVC-001 - CockpitService is a compatibility facade

- Location: `bbi_os/cockpit/service.py`.
- Current behavior: Zero-argument construction supports prototype client CRUD/search/test-pipeline; dependency-injected construction supports rich dashboard/control methods.
- Intended contract: Preserve both until cockpit/API consolidation is approved.
- Risk: Medium. Optional collaborators make unsupported rich paths fail at runtime with `RuntimeError`.
- Recommended action: Keep compatibility behavior and document richer constructor dependencies.
- Safe now: Documentation only.
- Tests protecting behavior: `bbi_os/cockpit/tests/test_cockpit.py`.

### RC-SVC-002 - Private repository access removed from CockpitService

- Location before cleanup: `bbi_os/cockpit/service.py`, method `_execution_records()`.
- Current behavior after cleanup: `CockpitService._execution_records()` calls `self._execution_repository.list()`.
- Intended contract: Application services use public repository methods.
- Risk: Low. The new method delegates to the same JSON data and hydrates the same `ClientExecutionRecord` objects.
- Recommended action: Keep `_read()` private and transitional; use `list()` for all-record reads.
- Safe now: Yes, implemented.
- Tests protecting behavior: `bbi_os/cockpit/tests/test_cockpit.py`, `bbi_os/client_execution/tests/test_execution.py`.

## 7. Repository Contract Findings

### RC-REP-001 - ExecutionStateRepository lacked public list-all method

- Location: `bbi_os/client_execution/state.py`.
- Current behavior before cleanup: Public methods were `save()`, `get()`, `latest_for_client()`, and `list_for_client()`; all-record access required `_read()`.
- Intended contract: Repositories expose public methods for supported reads and writes.
- Risk: Low to fix because all-record hydration already existed in `latest_for_client()` and `list_for_client()`.
- Recommended action: Add `list()` returning `List[ClientExecutionRecord]`.
- Safe now: Yes, implemented.
- Tests protecting behavior: new `ClientExecutionTests.test_state_repository_lists_all_execution_records`.

### RC-REP-002 - JSON repositories duplicate atomic file operations

- Location: `bbi_os/entity_repository.py`, `bbi_os/task_management/repository.py`, `bbi_os/client_execution/state.py`, `bbi_os/workflows/repository.py`, `bbi_os/workflows/templates.py`, `bbi_os/client_monetization/registry.py`, `bbi_os/client_monetization/usage_tracker.py`, `bbi_os/integrations/registry.py`.
- Current behavior: Each repository owns its own `_read()`/`_write()` implementation.
- Intended contract: Public repository methods should hide storage details; common JSON mechanics may later be centralized.
- Risk: Medium. Mechanical consolidation can change file format, ordering, locking, or exceptions.
- Recommended action: Defer to a dedicated JSON utility cleanup with parity tests.
- Safe now: No.
- Tests protecting behavior: repository and service tests across task, domain, workflow, integration, monetization, execution.

### RC-REP-003 - No transaction boundary abstraction

- Location: JSON repositories and multi-service workflows.
- Current behavior: Multiple related writes occur without a shared unit of work.
- Intended contract: Future PostgreSQL work must define explicit transaction ownership.
- Risk: High for persistence migration.
- Recommended action: Defer until repository contract tests and transaction ADR implementation.
- Safe now: No.
- Tests protecting behavior: workflow rollback tests, onboarding/pipeline/execution/monetization tests.

## 8. Data Contract Findings

### RC-DATA-001 - Mixed dictionaries and typed dataclasses

- Location: `bbi_os/domain.py`, `bbi_os/client_execution/models.py`, `bbi_os/workflows/models.py`, `bbi_os/client_monetization/models.py`, `bbi_os/task_management/service.py`, `bbi_os/cockpit/service.py`.
- Current behavior: Stable domains use dataclasses with `to_dict()`/`from_dict()` or `to_record()`/`from_record()`; task and cockpit prototype paths still use dictionaries.
- Intended contract: Typed objects should protect domain boundaries; dictionaries are acceptable at request/response and flexible metadata boundaries.
- Risk: Medium. Over-converting could break existing response shapes.
- Recommended action: Add types only where behavior is already stable.
- Safe now: Deferred except small annotations.
- Tests protecting behavior: full unittest suite.

### RC-DATA-002 - Timestamp formats are assumed strings

- Location: `bbi_os/observability.py`, `bbi_os/domain.py`, `bbi_os/client_execution/models.py`, `bbi_os/task_management/service.py`.
- Current behavior: Timestamps are ISO-like UTC strings, usually ending in `Z`.
- Intended contract: Preserve string timestamp serialization until persistence schema design.
- Risk: Medium for database migration.
- Recommended action: Document timestamp expectations before SQL schema work.
- Safe now: No behavior change.
- Tests protecting behavior: task, domain, observability, execution tests.

### RC-DATA-003 - Status values are string enums by convention

- Location: `bbi_os/client_execution/state.py`, `bbi_os/client_execution/models.py`, `bbi_os/task_management/service.py`, workflow modules.
- Current behavior: Execution states use string constants in `STATE_TRANSITIONS`; task statuses are validated in service logic.
- Intended contract: Status values should be explicit before persistence.
- Risk: Medium.
- Recommended action: Add constants or enums only after a compatibility review.
- Safe now: Deferred.
- Tests protecting behavior: `tests/test_task_service.py`, `bbi_os/client_execution/tests/test_execution.py`.

## 9. Test Contract Findings

### RC-TST-001 - `unittest discover tests` is canonical

- Location: `docs/TESTING_STRATEGY.md`, `tests/`.
- Current behavior: Top-level test files import nested package tests so discovery from `tests` runs the baseline.
- Intended contract: Continue using `unittest`; do not introduce pytest as required tooling.
- Risk: Low if preserved.
- Recommended action: Keep top-level wrappers until test layout is intentionally changed.
- Safe now: No change.
- Tests protecting behavior: full discovery command.

### RC-TST-002 - Tests define compatibility expectations

- Location: `bbi_os/cockpit/tests/test_cockpit.py`, `bbi_os/cockpit/tests/test_client_management.py`, `tests/test_task_api.py`.
- Current behavior: Tests require `CockpitApiHandler` import from `bbi_os.cockpit.api`, `CockpitService` optional rich dependencies, `/v1/*` handler envelope, and `/clients` compatibility normalization.
- Intended contract: Treat these as stable until deliberately deprecated.
- Risk: High if changed without frontend/API plan.
- Recommended action: Add route-contract tests when FastAPI consolidation begins.
- Safe now: No route behavior change.
- Tests protecting behavior: named tests above.

## 10. Frontend/Backend Contract Findings

### RC-FE-001 - React cockpit assumes versioned cockpit reads

- Location: `cockpit-ui/src/lib/api.js`.
- Current behavior: The UI requests `/v1/cockpit/*` read endpoints and expects `body.data`.
- Intended contract: Future FastAPI `/v1/*` routes must preserve envelope semantics or update the frontend under approval.
- Risk: Medium to high.
- Recommended action: Document route inventory and add backend route adapters later.
- Safe now: Deferred.
- Tests protecting behavior: no frontend automated tests were found; backend handler tests cover expected response envelopes.

### RC-FE-002 - Client creation path differs from README prototype path

- Location: `cockpit-ui/src/lib/api.js`, `bbi_os/cockpit/router.py`, `bbi_os/cockpit/client_management.py`.
- Current behavior: UI uses `/clients`; prototype FastAPI uses `/cockpit/create-client`; internal handler compatibility normalizes `/clients` to `/v1/clients`.
- Intended contract: Keep `/clients` compatibility until route consolidation.
- Risk: Medium.
- Recommended action: Later document and test canonical route mapping.
- Safe now: No change.
- Tests protecting behavior: `bbi_os/cockpit/tests/test_client_management.py`.

## 11. Architectural Drift

- FastAPI is accepted as the future canonical HTTP boundary, but full `/v1/*` FastAPI consolidation is unimplemented.
- Two FastAPI app definitions coexist in `bbi_os/cockpit/api.py` and `bbi_os/__main__.py`.
- Internal `BaseHTTPRequestHandler` routing supports richer `/v1/*` handler contracts than the FastAPI prototype.
- The React cockpit targets richer `/v1/cockpit/*` endpoints while the FastAPI router exposes `/cockpit/*` prototype endpoints by default.
- JSON repository implementations expose public domain methods but still use duplicated private file mechanics internally.

## 12. Duplicate or Competing Contracts

- App contract: `bbi_os.cockpit.api:app` and `bbi_os.__main__:app`.
- HTTP contract: `/cockpit/*` prototype routes and `/v1/*` internal handler routes.
- Client contract: prototype `client_name`/`plan` payload and richer client-management `name`/`plan` payload.
- Response contract: direct prototype dictionaries and standardized internal envelopes.
- Repository read contract: public typed reads and private raw `_read()` internals.

## 13. Compatibility Layers

- `CockpitService` zero-argument constructor preserves prototype behavior.
- `CockpitService` dependency-injected constructor supports rich cockpit dashboard/control behavior.
- `CockpitApiHandler` is exported from `bbi_os.cockpit.api` while implemented in `bbi_os/cockpit/handler.py`.
- `TaskRequestHandler._resolved_entity_route()` maps `/clients` to `/v1/clients`.
- Top-level `tests/test_*.py` wrappers preserve discovery of nested test packages.

## 14. Private Access Violations

- Resolved in this task: `bbi_os/cockpit/service.py` no longer calls `ExecutionStateRepository._read()` directly.
- Remaining private `_read()` usage is internal to repository classes or tests reading files directly for verification.
- `_read()` remains private and transitional in JSON repository implementations.

## 15. Dead or Unreferenced Code

- `generated_system/` appears to contain generated prototype files and is not referenced by current tests found through repository search.
- `bbi_os/generator/bbios_generator_v2.py` contains template output for generated FastAPI code and is not an active runtime entry point.
- No code was deleted because removal would require a separate compatibility decision.

## 16. Risk Classification

- Low risk: adding public repository methods that delegate to existing private reads; documentation of current contracts; focused tests.
- Medium risk: app factory consolidation, package export additions, JSON utility extraction, frontend/backend route documentation.
- High risk: API consolidation, route removal, response envelope changes, persistence migration, transaction boundary changes, authentication/security changes.

## 17. Safe Cleanup Candidates

- Implemented: add `ExecutionStateRepository.list()` and update `CockpitService` to use it.
- Candidate: add explicit docstrings for compatibility routes.
- Candidate: add route inventory tests for currently supported handler paths.
- Candidate: add package exports only for already-used public classes after approval.

## 18. Deferred Cleanup Candidates

- Consolidate FastAPI app creation around a canonical factory.
- Create versioned FastAPI route adapters for `/v1/*`.
- Centralize secret-related environment access.
- Extract shared JSON repository file utilities.
- Document and test frontend/backend route contracts end to end.

## 19. Breaking-Change Candidates

- Removing `/cockpit/*` prototype endpoints.
- Removing `/clients` compatibility path.
- Removing internal `BaseHTTPRequestHandler` handlers.
- Changing response envelopes.
- Replacing JSON storage with PostgreSQL.
- Removing private `_read()` methods before all internal repository usage and compatibility concerns are resolved.

## 20. Recommended Implementation Sequence

1. Complete repository contract cleanup for public read methods and private access removal.
2. Add explicit package export policy and minimal exports for stable public classes.
3. Inventory and test supported HTTP route surfaces.
4. Consolidate FastAPI app creation without changing route behavior.
5. Add `/v1/*` FastAPI adapters that delegate to existing handlers/services.
6. Define repository equivalence tests before PostgreSQL implementation.
7. Begin persistence work only after transaction and migration plans are approved.

## 21. Phase 2 Exit Criteria

- Public repository methods cover all application-service read/write needs.
- Application services do not call private repository methods.
- Supported import paths are documented and tested.
- Canonical runtime entry point is documented and validated.
- `/cockpit/*`, `/clients`, and `/v1/*` compatibility expectations are documented.
- Full unittest discovery and compile checks pass.
- No persistence, auth, deployment, or route-consolidation work starts without approval.
