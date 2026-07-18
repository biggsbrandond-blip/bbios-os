# BBIOS OS Cockpit Baseline Stabilization Plan

## 1. Document Control

- Document: Cockpit Baseline Stabilization Plan
- Repository: `biggsbrandond-blip/bbios-os`
- Repository root assessed: current BBIOS OS repository
- Assessment date: 2026-07-18
- Scope: investigation of cockpit API, service, and test drift
- Authorized change in this task: creation of this document only
- Application code changed: No
- Tests changed: No

## 2. Executive Summary

Confirmed: The repository has a cockpit drift issue between the simple FastAPI prototype in `bbi_os/cockpit/api.py`, `bbi_os/cockpit/router.py`, and `bbi_os/cockpit/service.py`, and a richer cockpit dashboard/control contract expected by `bbi_os/cockpit/tests/test_cockpit.py`.

Confirmed root cause: `tests/test_cockpit.py` imports `bbi_os.cockpit.tests.test_cockpit`, which imports `CockpitApiHandler` from `bbi_os.cockpit.api`; `bbi_os/cockpit/api.py` defines only a FastAPI `app` and does not define or export `CockpitApiHandler`.

Decision: The evidence indicates **production code is incomplete relative to the richer cockpit test contract**, not simply that the test is stale. The richer contract is supported by existing cockpit dashboard, control, analytics, monetization, execution, repository, and frontend API code, while the README and FastAPI router still describe the older prototype surface.

Recommended smallest safe resolution: add the missing cockpit handler and extend `CockpitService` to support the dependency-injected dashboard/control contract while preserving the current zero-argument FastAPI prototype behavior and existing `/cockpit/*` routes.

## 3. Confirmed Current State

Confirmed from `bbi_os/cockpit/api.py`:

- Lines 1-2 import `FastAPI` and `router`.
- Lines 4-9 create `app = FastAPI(...)` and include `router` under `/cockpit`.
- There is no `CockpitApiHandler` class, function, or export in this file.

Confirmed from `bbi_os/cockpit/router.py`:

- Lines 1-3 import `APIRouter`, `BaseModel`, and `CockpitService`.
- Lines 5-6 instantiate `router = APIRouter()` and `service = CockpitService()`.
- Lines 12-14 define Pydantic `ClientRequest`.
- Lines 20-46 define four FastAPI prototype endpoints: `create_client`, `get_client`, `search_clients`, and `test_pipeline`.

Confirmed from `bbi_os/cockpit/service.py`:

- Lines 5-9 define `CockpitService` with a zero-argument constructor and in-memory `clients`/`executions`.
- Lines 11-18 define `validate_client(name, plan)`.
- Lines 20-43 define `create_client(name, plan)`.
- Lines 45-60 define `get_client(client_id)`.
- Lines 62-81 define `search_clients(name="", plan="")`.
- Lines 83-89 define `log_event(event_type, client_id)`.
- Lines 91-98 define `test_pipeline()`.

Confirmed from `README.md`:

- Lines 23-40 describe the prototype architecture as `Client Request -> Router Layer -> Service Layer -> In-Memory Data Store -> Response`.
- Lines 44-56 document only `/cockpit/create-client`, `/cockpit/client/{client_id}`, `/cockpit/clients/search`, and `/cockpit/test-pipeline`.
- Lines 81-83 document startup with `uvicorn bbi_os.cockpit.api:app --reload`.

Confirmed from `bbi_os/__main__.py`:

- Lines 7-15 define `create_app()` and include the same cockpit router under `/cockpit`.
- Lines 17-23 add root and health endpoints.

Confirmed from `bbi_os/cockpit/client_management.py`:

- Lines 22-31 define a separate JSON-backed `ClientManagementService` with injected `clients` and `plans`.
- Lines 84-114 define `ClientManagementApiHandler`, which follows the internal handler pattern and standardized response contract.

Confirmed from `bbi_os/cockpit/models.py`:

- Lines 11-32 define `WorkflowControlRequest`.
- Lines 35-58 define `CockpitEventStore`, a process-local event view used by dashboard tests.

## 4. Expected Test Contract

Confirmed from `bbi_os/cockpit/tests/test_cockpit.py`:

- Line 15 expects `from bbi_os.cockpit.api import CockpitApiHandler`.
- Lines 115-130 expect `CockpitService` to accept nine constructor collaborators: clients repository, execution state repository, system overview dashboard, client view dashboard, execution monitor dashboard, monetization dashboard, workflow control dashboard, workflow controls, usage insights engine, and performance metrics engine.
- Lines 148-155 expect `CockpitService.system_overview()` to aggregate active clients, running workflows, execution states, and health.
- Lines 157-170 expect `CockpitService.client(client_id)` to combine client, execution, and usage/billing data.
- Lines 172-177 expect `CockpitService.execute(data)` to route workflow execution through execution controls.
- Lines 179-184 expect `CockpitService.cancel(execution_id)` to fail safely without mutating persisted execution state.
- Lines 186-190 expect cockpit actions to emit `cockpit_view_rendered` observability events with request identity.
- Lines 192-204 expect `CockpitService.billing()` to aggregate client billing.
- Lines 206-212 expect read-only views `system_overview()`, `execution_monitor()`, and `usage()` not to modify execution persistence.
- Lines 214-237 expect `CockpitApiHandler.handle(method, entity_id, request)` to return standardized envelopes for `system-overview`, `client`, `executions`, `usage`, `billing-summary`, and `workflow/execute`.

Confirmed from `tests/test_cockpit.py`:

- Line 1 re-exports `bbi_os.cockpit.tests.test_cockpit`, so the package-local cockpit test is the root test contract.

## 5. Current Production Contract

Confirmed current production behavior:

- FastAPI app creation is present in `bbi_os/cockpit/api.py`.
- FastAPI routes are mounted under `/cockpit` and call a module-level `CockpitService()` from `bbi_os/cockpit/router.py`.
- `CockpitService` currently supports only prototype client CRUD/search/test-pipeline methods.
- The current cockpit prototype returns direct dictionaries such as `{"status": "success", "client": ...}` rather than the standardized `{"request_id", "status", "data", "execution_summary"}` envelope expected by the richer internal API handler tests.

Confirmed absent production behavior:

- No `CockpitApiHandler`.
- No `CockpitService.system_overview()`.
- No `CockpitService.client(client_id)`.
- No `CockpitService.execution_monitor()`.
- No `CockpitService.usage()`.
- No `CockpitService.billing()`.
- No `CockpitService.execute(data)`, `retry(execution_id)`, or `cancel(execution_id)`.

## 6. Drift Analysis

Confirmed drift:

- Import drift: `bbi_os/cockpit/tests/test_cockpit.py` line 15 imports `CockpitApiHandler`; `bbi_os/cockpit/api.py` lines 1-9 do not provide it.
- Constructor drift: tests instantiate `CockpitService(...)` with dependencies at lines 115-130; current `CockpitService.__init__` accepts only `self` at `bbi_os/cockpit/service.py` line 7.
- Method drift: tests call rich dashboard/control methods at lines 151, 167, 173, 183, 187, 202, 209-211; current service methods are limited to prototype methods at `bbi_os/cockpit/service.py` lines 11-98.
- API-style drift: tests expect an internal `handle()` API surface and standardized response envelope; production FastAPI cockpit routes are direct `APIRouter` endpoints.
- Persistence drift: current FastAPI cockpit service stores clients/events in process memory; richer cockpit tests use `JsonEntityRepository`, `ExecutionStateRepository`, `WorkflowRepository`, `ClientPlanRegistry`, and `UsageTracker`.

Interpretation:

- The FastAPI prototype and richer cockpit dashboard/control architecture appear to be evidence of an incomplete migration or partial layering, not a deliberate coexistence model. This is interpretation because no repository document explicitly states the intended migration plan.

## 7. Root Cause Determination

Confirmed root cause:

- The immediate test baseline failure is an import-time error because `CockpitApiHandler` is expected by `bbi_os/cockpit/tests/test_cockpit.py` but absent from `bbi_os/cockpit/api.py`.

Confirmed secondary root cause:

- Even after adding `CockpitApiHandler`, the next likely failure would be `CockpitService` constructor/method mismatch because the tests require injected dashboard/control collaborators and rich cockpit methods that the current class does not implement.

Local history evidence:

- `git log --all -S CockpitApiHandler --oneline -- bbi_os tests` identifies only commit `8c006d5 BBIOS OS initial backend system`.
- `git show 8c006d5:bbi_os/cockpit/api.py` matches the current FastAPI-only file and does not show `CockpitApiHandler`.
- `git show 8c006d5:bbi_os/cockpit/tests/test_cockpit.py` shows the same test import and expectations.
- Therefore, available local history does not prove that `CockpitApiHandler` previously existed and was removed.

## 8. Stale Test vs Incomplete Implementation Decision

Decision: **Production code is incomplete relative to the richer cockpit architecture.**

Confirmed supporting facts:

- Rich cockpit dependencies exist in production source: `SystemOverviewDashboard`, `ClientViewDashboard`, `ExecutionMonitorDashboard`, `MonetizationDashboard`, `WorkflowControlDashboard`, `WorkflowControls`, `UsageInsightsEngine`, `PerformanceMetricsEngine`, `CockpitEventStore`, and `ClientManagementApiHandler`.
- The frontend API client in `cockpit-ui/src/lib/api.js` calls `/v1/cockpit/system-overview`, `/v1/cockpit/usage`, `/v1/cockpit/billing-summary`, `/v1/cockpit/executions`, and `/v1/cockpit/client/{id}`, which aligns with the richer cockpit test expectations rather than the README's older `/cockpit/*` prototype-only surface.
- `ClientManagementApiHandler` already follows the same internal handler style expected from `CockpitApiHandler`.

Unresolved intent:

- No README or design document explicitly says whether the prototype routes and richer `/v1/cockpit/*` control-plane surfaces are intended to coexist long term.

Why this is not best classified as only stale tests:

- The test references many existing production modules that are otherwise coherent with each other.
- The missing pieces are adapter/composition pieces: `CockpitApiHandler` and a rich `CockpitService` facade over already-existing dashboards/controls.

## 9. Options Considered

Option A: Delete or skip the failing cockpit tests.

- Benefit: fastest way to make test discovery pass.
- Risk: hides a real architectural contract already reflected by cockpit modules and frontend API paths.
- Decision: Not recommended.

Option B: Modify tests to match the simple FastAPI prototype.

- Benefit: aligns tests with README and current `/cockpit/*` routes.
- Risk: abandons the richer cockpit dashboard/control architecture without evidence that it is obsolete.
- Decision: Not recommended.

Option C: Add only a stub `CockpitApiHandler`.

- Benefit: fixes the immediate import error.
- Risk: likely exposes the next constructor/method mismatch and creates a hollow API class.
- Decision: Not sufficient.

Option D: Add `CockpitApiHandler` and extend `CockpitService` as a compatibility-preserving facade.

- Benefit: restores architectural consistency, preserves existing FastAPI prototype endpoints, uses existing dashboard/control components, and minimizes blast radius.
- Risk: requires careful optional constructor design to avoid breaking `bbi_os/cockpit/router.py`.
- Decision: Recommended.

Option E: Rewrite cockpit into a single FastAPI `/v1/cockpit/*` implementation now.

- Benefit: moves toward one production HTTP architecture.
- Risk: broader refactor than needed for baseline stabilization.
- Decision: Defer until after baseline is clean and approved.

## 10. Recommended Resolution

Recommended: Implement Option D in a later approved task.

The smallest safe correction is:

- Add `CockpitApiHandler` to `bbi_os/cockpit/api.py` without removing the existing FastAPI `app`.
- Extend `CockpitService` in `bbi_os/cockpit/service.py` to support an optional dependency-injected richer mode while preserving the current zero-argument prototype mode used by `bbi_os/cockpit/router.py`.
- Keep current FastAPI endpoints and response shapes intact for compatibility.
- Do not modify tests for this correction unless later implementation reveals a confirmed test defect.

Recommended handler behavior:

- `GET system-overview` -> `service.system_overview()`
- `GET client` with path `/v1/cockpit/client/{client_id}` -> `service.client(client_id)`
- `GET executions` -> `service.execution_monitor()`
- `GET usage` -> `service.usage()`
- `GET billing-summary` -> `service.billing()`
- `POST workflow` with path `/v1/cockpit/workflow/execute` -> `service.execute(request._body())`
- Unknown routes -> `request._route_not_found()`
- Expected successful responses should use existing `success_response()` from `bbi_os.task_management.api` to produce the standardized response envelope.
- Expected control errors should use existing `error_response()` and `request._log_error(...)` patterns.

Recommended service behavior:

- Preserve `create_client`, `get_client`, `search_clients`, and `test_pipeline`.
- Add rich methods that delegate to injected dashboard/control collaborators.
- Derive execution lists from `ExecutionStateRepository` without mutating persisted state.
- Emit `cockpit_view_rendered` events for read/control surfaces using `get_observability().log(...)`.

## 11. Exact Proposed File Changes

For a future approved implementation task only:

- Modify `bbi_os/cockpit/api.py`:
  - Add `class CockpitApiHandler`.
  - Keep `app = FastAPI(...)` and `app.include_router(router, prefix="/cockpit")` unchanged.

- Modify `bbi_os/cockpit/service.py`:
  - Change `CockpitService.__init__` to accept optional dependencies while still allowing `CockpitService()` with no arguments.
  - Add `system_overview`, `client`, `execution_monitor`, `usage`, `billing`, `workflow_control`, `execute`, `retry`, and `cancel` methods as thin delegators to existing cockpit dashboard/control classes.
  - Keep existing prototype methods and in-memory behavior unchanged when dependencies are not supplied.

- Do not modify `bbi_os/cockpit/router.py` unless later verification proves a compatibility issue.
- Do not modify `bbi_os/cockpit/tests/test_cockpit.py` or `tests/test_cockpit.py` for the baseline fix.

## 12. Compatibility Risks

- Constructor compatibility: changing `CockpitService.__init__` must preserve `CockpitService()` because `bbi_os/cockpit/router.py` line 6 instantiates it with no arguments.
- Response compatibility: adding `CockpitApiHandler` must not change existing FastAPI `/cockpit/*` response dictionaries documented in `README.md`.
- Read-only behavior: rich dashboard methods must not mutate `ExecutionStateRepository`, because `test_read_only_views_do_not_change_persisted_execution_state` asserts byte-for-byte stability.
- Observability behavior: new service methods must emit `cockpit_view_rendered` with current request context, as asserted by `test_observability_records_request_trace_for_cockpit_action`.
- Error handling: adding a handler should follow existing internal handler patterns without swallowing unexpected errors in a way that masks failures.
- Architectural ambiguity: preserving both `/cockpit/*` and `/v1/cockpit/*` style handlers maintains coexistence temporarily; a future decision should choose the canonical HTTP boundary.

## 13. Validation Plan

Required baseline validation after the future correction:

- Run `python3 -m unittest discover tests`.
- Expected result: 80 tests run, 0 failures, 0 errors, 0 skipped, unless additional hidden drift appears after the import error is removed.

Recommended focused checks:

- Run `python3 -m unittest bbi_os.cockpit.tests.test_cockpit`.
- Verify `uvicorn bbi_os.cockpit.api:app --reload` still starts.
- Verify existing FastAPI prototype endpoints still import and route through `bbi_os/cockpit/router.py`.
- Verify no PostgreSQL, SQLAlchemy, Alembic, auth, Docker, CI/CD, or unrelated features are introduced.

Current required test result recorded during this task:

- Command: `python3 -m unittest discover tests`
- Result: `FAILED (errors=1)`
- Total: 80 tests run
- Passed: 79
- Failures: 0
- Errors: 1
- Skipped: 0
- Error: `ImportError: cannot import name 'CockpitApiHandler' from 'bbi_os.cockpit.api' (bbi_os/cockpit/api.py)`

## 14. Rollback Plan

For the future implementation:

- Revert only the changes to `bbi_os/cockpit/api.py` and `bbi_os/cockpit/service.py` if compatibility regressions occur.
- Because the recommended change should not alter storage formats, rollback should not require data migration.
- If existing `/cockpit/*` behavior changes, restore the original zero-argument prototype path first.
- If rich cockpit handler behavior is wrong, remove the new handler export while keeping existing FastAPI app intact.

## 15. Acceptance Criteria

Baseline stabilization is accepted when:

- `python3 -m unittest discover tests` passes with 0 failures and 0 errors.
- `bbi_os.cockpit.api.CockpitApiHandler` exists and satisfies `test_required_api_surfaces_return_standardized_contracts`.
- `CockpitService()` still supports the current FastAPI router endpoints.
- Dependency-injected `CockpitService(...)` supports the rich methods expected by `bbi_os/cockpit/tests/test_cockpit.py`.
- Read-only cockpit methods do not mutate persisted execution state.
- No application architecture beyond cockpit baseline stabilization is changed.
- No PostgreSQL, SQLAlchemy, Alembic, authentication, Docker, CI/CD, or unrelated features are introduced.

## 16. Final Recommendation

Proceed with a small, production-code-only baseline stabilization in a separate approved implementation task:

1. Add the missing `CockpitApiHandler` adapter to `bbi_os/cockpit/api.py`.
2. Extend `CockpitService` as a backward-compatible facade over existing cockpit dashboards and controls.
3. Preserve the existing FastAPI prototype routes and README-documented startup path.
4. Do not change tests unless a specific assertion is proven invalid after the production contract is restored.

This resolves the import blocker and aligns the cockpit module with the most mature existing BBIOS architecture while keeping the change small and reversible.
