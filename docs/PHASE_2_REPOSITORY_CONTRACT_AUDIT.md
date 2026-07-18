# BBIOS OS Phase 2 Repository Contract Audit

## 1. Executive Summary

Phase 2A reviewed the repository contract surface after the published `v0.1.0` baseline. Confirmed current state: BBIOS OS is a Python 3.12 project with FastAPI cockpit prototype routes, focused FastAPI adapters for stable handler-style routes, internal `/v1/*` handler-style routes, layered services, JSON-backed repositories, process-local observability, and a React cockpit UI.

The most important safe cleanup found and implemented was removal of application-service dependence on the private execution repository `_read()` method. `ExecutionStateRepository.list()` now provides the public all-record read contract, and `CockpitService._execution_records()` uses it. `_read()` remains in place as a private implementation detail for repository internals.

No PostgreSQL, SQLAlchemy, Alembic, new authentication system, Docker, CI/CD, deployment, endpoint removal, request shape change, response shape change, or file format change was introduced.

## 2. Current Architecture Map

- Runtime entry points: `bbi_os/app.py` defines the canonical FastAPI `create_app()` factory and module-level `app`. `bbi_os/cockpit/api.py` and `bbi_os/__main__.py` preserve legacy imports by re-exporting the canonical objects.
- Prototype API: `bbi_os/cockpit/router.py` exposes `/create-client`, `/client/{client_id}`, `/clients/search`, and `/test-pipeline` under `settings.api_prefix`, which defaults to `/cockpit` in `bbi_os/settings.py`.
- FastAPI adapter API: `bbi_os/api/v1.py` exposes stable handler-backed FastAPI routes for `/v1/tasks`, `/v1/tasks/{task_id}`, `/clients`, and `/v1/clients`.
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

- Location: `bbi_os/app.py`, `bbi_os/cockpit/api.py`, `bbi_os/cockpit/router.py`, `bbi_os/__main__.py`, `bbi_os/task_management/api.py`.
- Current behavior: Importing `bbi_os.app` constructs the canonical FastAPI app. Legacy app modules re-export that app. Importing `bbi_os/api/v1.py` constructs an `APIRouter` and lightweight cached adapter factories. Importing `bbi_os/cockpit/router.py` still constructs an `APIRouter` and module-level `CockpitService()`. Importing `bbi_os/task_management/api.py` still constructs an `Authenticator()` and `EntityRouteRegistry()`.
- Intended contract: Import-time construction should remain lightweight and deterministic until app factory consolidation is approved.
- Risk: Medium. Side effects are currently simple, but future settings, auth, or persistence changes could make imports stateful.
- Recommended action: Keep app creation centralized in `bbi_os.app`; defer broader import-side-effect cleanup.
- Safe now: Partially implemented for FastAPI app creation.
- Tests protecting behavior: `tests/test_settings.py`, `tests/test_task_api.py`, `tests/test_cockpit.py`, `tests/test_api_v1_adapter.py`.

## 4. Runtime Contract Findings

### RC-RUN-001 - FastAPI app instance consolidated

- Location: `bbi_os/app.py`, `bbi_os/cockpit/api.py`, `bbi_os/__main__.py`, `tests/test_runtime_contract.py`.
- Current behavior: `bbi_os.app.create_app()` is the canonical factory and `bbi_os.app.app` is the canonical module-level instance. Legacy imports from `bbi_os.__main__` and `bbi_os.cockpit.api` reference the same canonical app object.
- Intended contract: FastAPI app construction happens in one place while legacy import paths remain compatible.
- Risk: Low after test coverage. Route inventory and metadata are now explicitly tested.
- Recommended action: Preserve this contract until `/v1/*` FastAPI adapters are approved.
- Safe now: Yes, implemented.
- Tests protecting behavior: `tests/test_runtime_contract.py`, `tests/test_settings.py`.

### RC-RUN-003 - Versioned FastAPI adapter router added

- Location: `bbi_os/api/v1.py`, `bbi_os/app.py`, `tests/test_api_v1_adapter.py`.
- Current behavior: The canonical FastAPI app includes `bbi_os.api.v1.router` once. The adapter exposes stable task and client-management handler contracts without moving business logic into route functions.
- Intended contract: FastAPI routes translate request inputs into existing handler request surfaces, delegate to handlers/services, and return captured status codes and response envelopes unchanged.
- Risk: Medium. The adapter introduces new public HTTP routes and persistent JSON-backed runtime paths under `settings.data_dir`.
- Recommended action: Keep the adapter narrow until richer cockpit/workflow runtime composition is approved.
- Safe now: Yes, implemented for `/v1/tasks`, `/v1/tasks/{task_id}`, `/clients`, and `/v1/clients`.
- Tests protecting behavior: `tests/test_api_v1_adapter.py`.

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
- Current behavior: Internal handlers return envelopes with `request_id`, `status`, `data`, and `execution_summary`. The FastAPI adapter in `bbi_os/api/v1.py` returns the handler-generated body and status code for implemented stable routes.
- Intended contract: This envelope must be preserved for `/v1/*` handler-style APIs and FastAPI route adapters.
- Risk: High if changed, because tests and frontend error handling rely on it.
- Recommended action: Add route-contract tests for each route as it becomes safely adaptable.
- Safe now: Implemented for task CRUD and client list/create adapters only.
- Tests protecting behavior: `tests/test_task_api.py`, `tests/test_cockpit.py`, `tests/test_api_v1_adapter.py`, workflow, integration, monetization, onboarding, pipeline, and execution tests.

### RC-API-003 - Frontend expects `/v1/cockpit/*` and `/clients`

- Location: `cockpit-ui/src/lib/api.js`, `cockpit-ui/README.md`.
- Current behavior: Read views call `/v1/cockpit/system-overview`, `/usage`, `/billing-summary`, `/executions`, and `/client/{id}`. Client list/create call `/clients`. FastAPI now serves `/clients` through the client-management handler adapter; `/v1/cockpit/*` remains internal handler behavior only.
- Intended contract: Frontend/backend contract is partly served by FastAPI now and partly deferred until rich cockpit runtime composition is approved.
- Risk: Medium. FastAPI default prefix remains `/cockpit`, and `/v1/cockpit/*` is not yet served by the canonical FastAPI app.
- Recommended action: Later create explicit versioned FastAPI route adapters for `/v1/cockpit/*` after dependency-injected `CockpitService` runtime composition is approved.
- Safe now: Partially implemented for `/clients`; `/v1/cockpit/*` deferred.
- Tests protecting behavior: `bbi_os/cockpit/tests/test_cockpit.py`, `bbi_os/cockpit/tests/test_client_management.py`, `tests/test_api_v1_adapter.py`.

### RC-API-004 - Handler-to-route matrix

| Method | Route | Handler | Request Shape | Response Shape | Status Behavior | Frontend Dependency | Phase 2C Decision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/v1/tasks` | `TaskRequestHandler._get()` | Headers only | Standard envelope with task list in `data` | 200, 401 invalid token | None found | Implemented |
| POST | `/v1/tasks` | `TaskRequestHandler._post()` | JSON object with `title`, `description`, `status` | Standard envelope with task in `data` | 201, 400, 401, 403, 500 | None found | Implemented |
| GET | `/v1/tasks/{task_id}` | `TaskRequestHandler._get()` | Path `task_id` | Standard envelope with task in `data` | 200, 401, 404 | None found | Implemented |
| PATCH | `/v1/tasks/{task_id}` | `TaskRequestHandler._patch()` | JSON object with updatable fields | Standard envelope with task in `data` | 200, 400, 401, 403, 404, 500 | None found | Implemented |
| DELETE | `/v1/tasks/{task_id}` | `TaskRequestHandler._delete()` | Path `task_id` | Standard envelope with empty object in `data` | 200, 401, 403, 404 | None found | Implemented |
| GET | `/clients` | `ClientManagementApiHandler.handle()` | Headers only | Standard envelope with client list in `data` | 200, 500 | `cockpit-ui/src/lib/api.js` | Implemented |
| POST | `/clients` | `ClientManagementApiHandler.handle()` | JSON object with `name`, `plan` | Standard envelope with client in `data` | 201, 400, 500 | `cockpit-ui/src/lib/api.js` | Implemented |
| GET | `/v1/clients` | `ClientManagementApiHandler.handle()` | Headers only | Standard envelope with client list in `data` | 200, 500 | Compatibility with internal normalized path | Implemented |
| POST | `/v1/clients` | `ClientManagementApiHandler.handle()` | JSON object with `name`, `plan` | Standard envelope with client in `data` | 201, 400, 500 | Compatibility with internal normalized path | Implemented |
| GET | `/v1/cockpit/system-overview` | `CockpitApiHandler.handle()` | Rich `CockpitService` dependencies | Standard envelope with overview in `data` | 200 or 400 for cockpit control errors; default service would raise dependency errors | `cockpit-ui/src/lib/api.js` | Deferred |
| GET | `/v1/cockpit/client/{client_id}` | `CockpitApiHandler.handle()` | Rich `CockpitService` dependencies and path client id | Standard envelope with client view in `data` | 200, route-not-found for missing id, 400 for cockpit control errors | `cockpit-ui/src/lib/api.js` | Deferred |
| GET | `/v1/cockpit/executions` | `CockpitApiHandler.handle()` | Rich `CockpitService` dependencies | Standard envelope with execution monitor in `data` | 200 or 400 for cockpit control errors; default service would raise dependency errors | `cockpit-ui/src/lib/api.js` | Deferred |
| GET | `/v1/cockpit/usage` | `CockpitApiHandler.handle()` | Rich `CockpitService` dependencies | Standard envelope with usage in `data` | 200 or 400 for cockpit control errors; default service would raise dependency errors | `cockpit-ui/src/lib/api.js` | Deferred |
| GET | `/v1/cockpit/billing-summary` | `CockpitApiHandler.handle()` | Rich `CockpitService` dependencies | Standard envelope with billing summary in `data` | 200 or 400 for cockpit control errors; default service would raise dependency errors | `cockpit-ui/src/lib/api.js` | Deferred |
| GET | `/v1/cockpit/workflow/control` | `CockpitApiHandler.handle()` | Rich `CockpitService` dependencies | Standard envelope with workflow control in `data` | 200 or 400 for cockpit control errors; default service would raise dependency errors | None found | Deferred |
| POST | `/v1/cockpit/workflow/execute` | `CockpitApiHandler.handle()` | JSON object accepted by `CockpitService.execute()` | Standard envelope with execution result in `data` | 201 or 400 for cockpit control errors; default service would raise dependency errors | None found | Deferred |
| POST | `/v1/cockpit/workflow/retry/{execution_id}` | `CockpitApiHandler.handle()` | Path `execution_id` | Standard envelope with retry result in `data` | 200, route-not-found for missing id, 400 for cockpit control errors | None found | Deferred |
| POST | `/v1/cockpit/workflow/cancel/{execution_id}` | `CockpitApiHandler.handle()` | Path `execution_id` | Standard envelope with empty object in `data` | 200, route-not-found for missing id, 400 for cockpit control errors | None found | Deferred |

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

### RC-SVC-003 - Cockpit execution controls reached through service internals

- Location before cleanup: `bbi_os/cockpit/controls/execution_controls.py`, methods `retry()` and `inspect()`.
- Current behavior before cleanup: `ExecutionControls` accessed `ClientExecutionService.state_repository.get()` directly.
- Intended contract: Control adapters should call public service methods and should not depend on a service collaborator attribute when a public service read contract can represent the operation.
- Risk: Low. `ClientExecutionService.get_execution()` delegates to the same public repository `get()` method and returns the same `ClientExecutionRecord` or `None`; `ExecutionControls` preserves its existing `CockpitControlError` handling.
- Recommended action: Use `ClientExecutionService.get_execution()` for execution-id lookup from cockpit controls while retaining the previous `state_repository.get()` path only as a compatibility fallback for existing execution-service test doubles.
- Safe now: Yes, implemented.
- Tests protecting behavior: `tests/test_service_contracts.py`.

### RC-SVC-004 - Monetization helper collaborators were hard-wired

- Location before cleanup: `bbi_os/client_monetization/service.py`, constructor.
- Current behavior before cleanup: `ClientMonetizationService` always constructed `PlanEnforcer(usage)` and `BillingSummaryGenerator(usage)` internally.
- Intended contract: Services may accept explicit collaborators where doing so improves composition clarity while preserving default construction behavior.
- Risk: Low. Four-argument construction still creates the same helper objects; injected helpers are optional and do not change usage event, billing, route, or persistence contracts.
- Recommended action: Permit optional `PlanEnforcer` and `BillingSummaryGenerator` injection for focused composition and tests.
- Safe now: Yes, implemented.
- Tests protecting behavior: `tests/test_service_contracts.py`.

## 7. Repository Contract Findings

### RC-REP-001 - ExecutionStateRepository lacked public list-all method

- Location: `bbi_os/client_execution/state.py`.
- Current behavior before cleanup: Public methods were `save()`, `get()`, `latest_for_client()`, and `list_for_client()`; all-record access required `_read()`.
- Intended contract: Repositories expose public methods for supported reads and writes.
- Risk: Low to fix because all-record hydration already existed in `latest_for_client()` and `list_for_client()`.
- Recommended action: Add `list()` returning `List[ClientExecutionRecord]`.
- Safe now: Yes, implemented.
- Tests protecting behavior: new `ClientExecutionTests.test_state_repository_lists_all_execution_records`.

### RC-REP-004 - Single-record repositories lacked standard presence/count reads

- Location: `bbi_os/task_management/repository.py`, `bbi_os/entity_repository.py`, `bbi_os/client_execution/state.py`.
- Current behavior before cleanup: `JsonTaskRepository`, `JsonEntityRepository`, and `ExecutionStateRepository` exposed public entity reads through `get()` and collection reads through `list()`, but callers had no consistent public `exists()` or `count()` helpers.
- Intended contract: Single-record repositories with unambiguous identity keys should expose non-mutating public read helpers for presence and count checks.
- Risk: Low. The new methods read the same JSON-backed mappings under the existing repository locks and do not alter write behavior, return envelopes, JSON schema, file layout, service behavior, or route behavior.
- Recommended action: Use `exists()` and `count()` for future presence/count needs instead of reaching into private storage helpers.
- Safe now: Yes, implemented for the three unambiguous JSON repositories.
- Tests protecting behavior: `tests/test_repository_contracts.py`.

### RC-REP-005 - Domain-specific repositories intentionally keep explicit names

- Location: `bbi_os/workflows/repository.py`, `bbi_os/workflows/templates.py`, `bbi_os/client_monetization/registry.py`, `bbi_os/client_monetization/usage_tracker.py`, `bbi_os/integrations/registry.py`, `bbi_os/client_onboarding/registry.py`, `bbi_os/client_pipeline/templates/registry.py`, `bbi_os/entity_routing.py`.
- Current behavior: These repositories and registries expose domain-specific methods such as `save_definition()`, `get_instance()`, `create_connector()`, `register_webhook()`, `plan_for()`, `assign()`, `record()`, `for_client()`, `register()`, and `resolve()`.
- Intended contract: Public repository access should remain explicit when a generic CRUD verb would obscure which underlying collection or domain concept is being addressed.
- Risk: Medium if generic aliases are added without naming and exception semantics being approved.
- Recommended action: Defer generic aliases for multi-collection and registry-style components until their repository contracts are specified individually.
- Safe now: Documentation only.
- Tests protecting behavior: workflow, template, integration, monetization, onboarding, pipeline, and route-registry tests.

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
- Current behavior: Stable domains use dataclasses with `to_dict()`/`from_dict()` or `to_record()`/`from_record()`; task create/update service inputs now use `TaskCreateRequest` and `TaskUpdateRequest`; task records and cockpit prototype paths still use dictionaries.
- Intended contract: Typed objects should protect domain boundaries; dictionaries are acceptable at request/response and flexible metadata boundaries.
- Risk: Medium. Over-converting could break existing response shapes.
- Recommended action: Add types only where behavior is already stable.
- Safe now: Implemented for task create/update service inputs only.
- Tests protecting behavior: `tests/test_task_boundary_models.py` and full unittest suite.

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

- FastAPI is accepted as the future canonical HTTP boundary, but full `/v1/*` FastAPI consolidation is incomplete.
- FastAPI app construction is now centralized in `bbi_os/app.py`; legacy app import paths remain compatibility exports.
- Focused FastAPI adapters now exist for task CRUD and client list/create handler contracts in `bbi_os/api/v1.py`.
- Internal `BaseHTTPRequestHandler` routing supports richer `/v1/*` handler contracts than the FastAPI prototype.
- The React cockpit targets richer `/v1/cockpit/*` endpoints while the FastAPI router exposes `/cockpit/*` prototype endpoints by default.
- JSON repository implementations expose public domain methods but still use duplicated private file mechanics internally.

## 12. Duplicate or Competing Contracts

- App contract: canonical `bbi_os.app:app`, with compatibility imports from `bbi_os.cockpit.api:app` and `bbi_os.__main__:app`.
- HTTP contract: `/cockpit/*` prototype routes, FastAPI adapter routes for stable `/v1/tasks` and client-management paths, and remaining internal handler routes.
- Client contract: prototype `client_name`/`plan` payload and richer client-management `name`/`plan` payload.
- Response contract: direct prototype dictionaries and standardized internal envelopes.
- Repository read contract: public typed reads, standardized `exists()` and `count()` on single-record JSON repositories, domain-specific public methods for multi-collection registries, and private raw `_read()` internals.

## 13. Compatibility Layers

- `CockpitService` zero-argument constructor preserves prototype behavior.
- `CockpitService` dependency-injected constructor supports rich cockpit dashboard/control behavior.
- `bbi_os.api.v1` preserves handler response envelopes for implemented FastAPI adapter paths.
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
- Medium risk: package export additions, JSON utility extraction, frontend/backend route documentation, focused handler-backed FastAPI adapters.
- High risk: full API consolidation, route removal, response envelope changes, persistence migration, transaction boundary changes, authentication/security changes.

## 17. Safe Cleanup Candidates

- Implemented: add `ExecutionStateRepository.list()` and update `CockpitService` to use it.
- Implemented: add public `exists()` and `count()` helpers to `JsonTaskRepository`, `JsonEntityRepository`, and `ExecutionStateRepository`.
- Implemented: add `ClientExecutionService.get_execution()` and update cockpit execution controls to use the public service lookup contract.
- Implemented: allow optional monetization helper injection while preserving existing `ClientMonetizationService` default construction.
- Candidate: add explicit docstrings for compatibility routes.
- Implemented: add route inventory tests for currently supported FastAPI and focused adapter paths.
- Implemented: add typed task create/update service input models while preserving dictionary callers and task JSON records.
- Candidate: add package exports only for already-used public classes after approval.

## 18. Deferred Cleanup Candidates

- Continue monitoring canonical FastAPI app creation through runtime contract tests.
- Create versioned FastAPI route adapters for deferred `/v1/cockpit/*`, workflow, execution, monetization, onboarding, pipeline, integration, webhook, and workflow-template handlers after runtime composition is approved.
- Continue typed-boundary cleanup for client management and cockpit compatibility payloads only after a narrow target is approved.
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
5. Continue adding `/v1/*` FastAPI adapters that delegate to existing handlers/services when service composition is explicit.
6. Define repository equivalence tests before PostgreSQL implementation.
7. Begin persistence work only after transaction and migration plans are approved.

## 21. Phase 2 Exit Criteria

- Public repository methods cover all application-service read/write needs.
- Application services do not call private repository methods.
- Supported import paths are documented and tested.
- Canonical runtime entry point is documented and validated.
- `/cockpit/*`, `/clients`, and `/v1/*` compatibility expectations are documented.
- Stable task and client-management handler contracts are served by FastAPI adapters with route tests.
- Deferred handler contracts are explicitly listed with deferral reasons.
- Full unittest discovery and compile checks pass.
- No persistence, auth, deployment, or route-consolidation work starts without approval.
