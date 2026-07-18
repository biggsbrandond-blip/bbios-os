# BBIOS OS PostgreSQL Persistence Readiness Assessment

## 1. Document Control

- Document: PostgreSQL Persistence Readiness Assessment
- Repository: `biggsbrandond-blip/bbios-os`
- Repository root assessed: current BBIOS OS repository
- Assessment date: 2026-07-18
- Assessor: Codex engineering analysis agent
- Authorized change: creation of this document only
- Application code changed: No

## 2. Executive Summary

Confirmed: BBIOS OS is a Python backend repository with a documented FastAPI cockpit prototype, additional internal HTTP-style API handlers, JSON-file repositories, dataclass-based domain models, in-memory registries, process-local observability, and a Vite React cockpit UI. The README describes the primary request path as `Client Request -> Router Layer -> Service Layer -> In-Memory Data Store -> Response`, and the current repository has both that early in-memory cockpit path and later JSON-backed domains.

Final readiness classification: **Ready with prerequisites**.

The codebase has useful boundaries for a PostgreSQL migration: services receive repository-like collaborators in many newer domains, JSON persistence is isolated in repository classes, and tests already use temporary storage paths. However, the repository is not ready for direct database modernization without prerequisite cleanup because the current test suite has an import-time failure, there is no declared Python dependency manifest, there is no centralized application composition for all available API handlers, and no transaction/session/unit-of-work boundary exists.

## 3. Assessment Scope

Confirmed scope inspected:

- Root documentation: `README.md`
- Backend package: `bbi_os/`
- Generated template/sample system: `generated_system/`
- Frontend cockpit UI: `cockpit-ui/`
- Tests: root `tests/` and package-local tests under `bbi_os/*/tests/`
- Dependency metadata present in repository: `cockpit-ui/package.json`, `cockpit-ui/package-lock.json`, `cockpit-ui/.env.example`

Not performed:

- No application code changes
- No dependency installs or upgrades
- No PostgreSQL, SQLAlchemy, Alembic, auth, Docker, CI, or feature implementation
- No commit and no pull request

## 4. Repository Structure

Confirmed top-level structure:

- `README.md`: backend architecture overview and documented run command.
- `bbi_os/`: main Python package.
- `generated_system/`: generated FastAPI sample with `api.py`, `router.py`, and `service.py`.
- `tests/`: root test modules, many of which mirror package-local tests by importing them.
- `cockpit-ui/`: React/Vite frontend with source files, package metadata, lockfile, `.env.example`, and installed `node_modules/`.
- `docs/`: created for this assessment document.

Confirmed backend subpackages:

- `bbi_os/cockpit/`: FastAPI prototype router/service plus cockpit dashboards, controls, analytics, client management, and tests.
- `bbi_os/task_management/`: HTTP handler, JSON task repository, task service, and errors.
- `bbi_os/workflows/`: workflow models, engine, repository, API handler, action handlers, and template system.
- `bbi_os/client_pipeline/`: request routing, service, workflow-backed pipeline engine, models, API handler, and template registry.
- `bbi_os/client_onboarding/`: onboarding routing, service, engine, models, registry, API handler, and tests.
- `bbi_os/client_execution/`: execution routing, engine, state machine/repository, service, models, API handler, and tests.
- `bbi_os/client_monetization/`: plan registry, usage tracker, pricing, billing, metering, service, models, API handler, and tests.
- `bbi_os/integrations/`: connector/webhook models, registry, outbound HTTP, webhook service, workflow integration, validation, and API handlers.
- `bbi_os/generator/` and `bbi_os/templates/`: generator utilities and a YAML FastAPI system template.

## 5. Current Application Architecture

Confirmed: The documented architecture in `README.md` is a layered FastAPI prototype with router and service layers. The active FastAPI cockpit implementation in `bbi_os/cockpit/api.py` creates `app = FastAPI(...)` and includes `bbi_os.cockpit.router.router` under `/cockpit`. `bbi_os/__main__.py` also defines `create_app()` and exposes a FastAPI app with `/`, `/health`, and the same cockpit router under `/cockpit`.

Confirmed: The broader repository contains a second, non-FastAPI API pattern centered on `bbi_os.task_management.api.TaskRequestHandler`, `bbi_os.entity_routing.EntityRouteRegistry`, and internal handler classes such as `WorkflowApiHandler`, `WorkflowTemplateApiHandler`, `ClientPipelineApiHandler`, `OnboardingApiHandler`, `ClientExecutionApiHandler`, `ClientMonetizationApiHandler`, `ConnectorApiHandler`, and `WebhookApiHandler`. These handlers expect a request-like object with `_body()`, `_respond()`, `_log_error()`, `_route_not_found()`, headers, and path.

Confirmed: Newer service classes usually accept repositories, routers, engines, or registries through constructors. The original FastAPI cockpit path uses a module-level singleton `service = CockpitService()` in `bbi_os/cockpit/router.py`.

## 6. Application Entry Points and Startup Flow

Confirmed entry points:

- `README.md` documents `uvicorn bbi_os.cockpit.api:app --reload`.
- `bbi_os/cockpit/api.py` defines a FastAPI app and includes the cockpit router under `/cockpit`.
- `bbi_os/__main__.py` defines `create_app()`, includes the same cockpit router under `/cockpit`, and adds `GET /` and `GET /health`.
- `generated_system/api.py` defines a generated sample FastAPI app under `/cockpit`.
- `bbi_os/task_management/api.py` contains `run_server()` and a `BaseHTTPRequestHandler`-based HTTP server path, but this is not documented in `README.md` as the primary startup command.

Startup concern: There is no confirmed central composition root that wires all JSON-backed services and internal API handlers into a single production application. Tests assemble many objects manually.

## 7. Router and Endpoint Inventory

Confirmed FastAPI endpoints in `bbi_os/__main__.py`:

- `GET /` -> `root()`
- `GET /health` -> `health()`
- Includes `bbi_os.cockpit.router.router` at `/cockpit`

Confirmed FastAPI endpoints in `bbi_os/cockpit/router.py` through `bbi_os/cockpit/api.py`:

- `POST /cockpit/create-client` -> `create_client(payload: ClientRequest)`
- `GET /cockpit/client/{client_id}` -> `get_client(client_id: str)`
- `GET /cockpit/clients/search` -> `search_clients(name: str = "", plan: str = "")`
- `POST /cockpit/test-pipeline` -> `test_pipeline()`

Confirmed generated sample endpoints in `generated_system/router.py`:

- `GET /`
- `GET /health`
- `POST /create-client`
- `POST /test-pipeline`

Confirmed internal handler route surfaces:

- `TaskRequestHandler` in `bbi_os/task_management/api.py`: versioned task CRUD for `/v1/tasks` and `/v1/tasks/{task_id}`.
- `EntityRouteRegistry` in `bbi_os/entity_routing.py`: resolves `/v1/{resource}` style paths.
- `WorkflowApiHandler` in `bbi_os/workflows/api.py`: workflow definitions, executions, execution status, and workflow history.
- `WorkflowTemplateApiHandler` in `bbi_os/workflows/template_api.py`: workflow template create/list/get/execute.
- `ClientPipelineApiHandler` in `bbi_os/client_pipeline/api.py`: `POST /v1/client/request` style client request processing.
- `OnboardingApiHandler` in `bbi_os/client_onboarding/api.py`: `POST /v1/client/onboarding` style onboarding.
- `ClientExecutionApiHandler` in `bbi_os/client_execution/api.py`: execute, schedule-execution, and execution-status routes.
- `ClientMonetizationApiHandler` in `bbi_os/client_monetization/api.py`: plan, usage-event, usage, and billing-summary routes.
- `ConnectorApiHandler` and `WebhookApiHandler` in `bbi_os/integrations/api.py`: connector create/list/test and webhook register/invoke routes.
- `ClientManagementApiHandler` in `bbi_os/cockpit/client_management.py`: create/list clients on a versioned route.

Assessment: Only the cockpit prototype endpoints are true FastAPI routes in the current source. The richer `/v1/*` handlers are test-driven/internal and not included in the documented FastAPI app.

## 8. Service Layer Inventory

Confirmed services and engines:

- `bbi_os.cockpit.service.CockpitService`: in-memory client and execution list management for the FastAPI prototype.
- `bbi_os.cockpit.client_management.ClientManagementService`: JSON-backed client creation/listing through `EntityRepository` and `ClientPlanRegistry`.
- `bbi_os.task_management.service.TaskService`: task CRUD and validation over `JsonTaskRepository`.
- `bbi_os.workflows.engine.WorkflowEngine`: workflow definitions, execution, retry, status, history, mapping resolution, and rollback.
- `bbi_os.workflows.templates.WorkflowTemplateService`: immutable template creation, version lookup, template execution, and lineage persistence.
- `bbi_os.client_pipeline.service.ClientPipelineService`: authenticated request validation, template route resolution, and pipeline execution.
- `bbi_os.client_onboarding.service.OnboardingService`: authenticated onboarding request orchestration.
- `bbi_os.client_execution.service.ClientExecutionService`: client validation, routing, execution scheduling/start, and latest status.
- `bbi_os.client_monetization.service.ClientMonetizationService`: plan lookup, usage tracking, automatic usage recording, metrics, and billing.
- `bbi_os.integrations.webhooks.WebhookService`: webhook registration and invocation.
- `bbi_os.integrations.outbound.OutboundRequestEngine`: connector execution and external HTTP dispatch.
- Cockpit dashboard/control/analytics classes under `bbi_os/cockpit/{controls,dashboards,analytics}` provide read/control surfaces over services and repositories.

## 9. Repository and Storage Inventory

Confirmed persistent JSON/file repositories:

- `JsonTaskRepository` in `bbi_os/task_management/repository.py`: task records keyed by task `id`.
- `JsonEntityRepository` in `bbi_os/entity_repository.py`: generic entity records keyed by `entity_id`.
- `WorkflowRepository` in `bbi_os/workflows/repository.py`: workflow definitions and workflow instances in separate JSON files.
- `WorkflowTemplateRepository` in `bbi_os/workflows/templates.py`: workflow templates and lineage in separate JSON files.
- `ExecutionStateRepository` in `bbi_os/client_execution/state.py`: client execution state records.
- `ClientPlanRegistry` in `bbi_os/client_monetization/registry.py`: client-to-plan assignments, with immutable plan definitions in `bbi_os/client_monetization/plans.py`.
- `UsageTracker` in `bbi_os/client_monetization/usage_tracker.py`: usage event records.
- `IntegrationRegistry` in `bbi_os/integrations/registry.py`: versioned connectors, webhooks, and workflow mappings.

Confirmed implementation pattern: JSON repositories use `threading.RLock`, read whole files into dictionaries, write to temporary files with `tempfile.mkstemp`, flush/fsync, and atomically replace with `os.replace`.

Confirmed in-memory/process-local data:

- `CockpitService.clients` and `CockpitService.executions` in `bbi_os/cockpit/service.py`.
- `EntityRouteRegistry._handlers` in `bbi_os/entity_routing.py`.
- `WorkflowActionRegistry._handlers` in `bbi_os/workflows/engine.py`.
- `ClientTemplateRegistry._routes` in `bbi_os/client_pipeline/templates/registry.py`.
- `OnboardingRegistry._routes` in `bbi_os/client_onboarding/registry.py`.
- `ExecutionTypeRegistry._modes` in `bbi_os/client_execution/registry.py`.
- `ExecutionStateMachine` persists transitions through `ExecutionStateRepository`, but transition logic is process-local.
- `CockpitEventStore` in `bbi_os/cockpit/models.py`: bounded `deque` of observability events.
- `Observability.metrics` in `bbi_os/observability.py`: process-local request timing counters.
- `UsageSignalMeter` in `bbi_os/client_monetization/metering_observer.py`: process-local request metering cache.

Confirmed generated/static/test data:

- `generated_system/` is generated sample code and not wired as the main app.
- `bbi_os/templates/cockpit_template_v0_1.yaml` is a generator template; it explicitly marks `state_layer.type: in_memory` and `database is forbidden until explicitly enabled`.
- Tests create temporary JSON files under `tempfile.TemporaryDirectory()`.
- `cockpit-ui/src/fixtures/pilotData.js` is static frontend pilot fixture data.

Confirmed absent storage mechanisms:

- No PostgreSQL code found.
- No SQLAlchemy code found.
- No Alembic configuration found.
- No SQLite database file found.

## 10. Domain Model and Schema Inventory

Confirmed Pydantic schemas:

- `bbi_os.cockpit.router.ClientRequest` extends `pydantic.BaseModel` with `client_name` and `plan`.

Confirmed dataclass/domain schemas:

- `bbi_os.auth.UserIdentity`
- `bbi_os.domain.BaseEntity`, `TaskEntity`, `UserEntity`
- `bbi_os.workflows.models.WorkflowStep`, `WorkflowDefinition`, `StepExecution`, `WorkflowInstance`
- `bbi_os.workflows.templates.WorkflowTemplate`
- `bbi_os.client_pipeline.models.ClientRequest`, `ClientPipelineResult`
- `bbi_os.client_onboarding.models.OnboardingRequest`, `OnboardingResult`
- `bbi_os.client_execution.models.ClientExecutionRequest`, `StateTransition`, `ClientExecutionRecord`
- `bbi_os.client_monetization.models.ClientPlan`, `UsageEventRequest`, `UsageEvent`, `BillingSummary`
- `bbi_os.integrations.models.ConnectorDefinition`, `WebhookRegistration`
- `bbi_os.cockpit.models.WorkflowControlRequest`

Confirmed config-like schemas and environment handling:

- `Authenticator.from_environment()` parses `BBIOS_AUTH_TOKENS` JSON from the environment.
- `ConnectorDefinition.credential_env` stores the name of an environment variable used for connector credentials.
- `WebhookRegistration.secret_env` stores the name of an environment variable used for webhook signing secrets.
- `cockpit-ui/.env.example` documents `VITE_API_BASE_URL` and `VITE_PILOT_MODE`.

Assessment: Most backend request/response/domain objects are dataclasses with manual `from_dict` validation, not Pydantic models. This is workable but requires explicit mapping decisions before SQLAlchemy models are introduced.

## 11. Current Data Flow

Confirmed FastAPI cockpit prototype flow:

1. HTTP request enters `bbi_os.cockpit.api.app`.
2. `APIRouter` endpoint in `bbi_os/cockpit/router.py` receives the request.
3. `ClientRequest` Pydantic model validates create-client bodies.
4. Module-level `CockpitService` handles validation and business logic.
5. `CockpitService` writes client records to `self.clients` in memory and execution events to `self.executions`.
6. Endpoint returns dictionaries directly.

Confirmed versioned task/internal handler flow:

1. `TaskRequestHandler` receives HTTP methods.
2. `_observe_request()` starts request context, authentication, authorization, observability, and execution summary.
3. `_dispatch_entity()` delegates non-task resources through `EntityRouteRegistry`.
4. For tasks, `_body()` parses JSON and `TaskService` validates input.
5. `JsonTaskRepository` reads/writes the JSON file.
6. Responses are wrapped with `success_response()` or `error_response()` from `bbi_os.task_management.api`.

Confirmed workflow/template flow:

1. API handler receives a request object.
2. Service/model `from_dict()` validation constructs definitions/templates.
3. `WorkflowRepository` or `WorkflowTemplateRepository` persists JSON records.
4. `WorkflowEngine` creates instances, executes registered action handlers, records step history, and saves after state changes.
5. On failures, `_rollback()` calls action rollbacks for completed steps where rollback data exists.

Confirmed client lifecycle flow across later modules:

1. `ClientManagementService.create()` creates a `BaseEntity` with `entity_type="client"`.
2. It saves via `JsonEntityRepository`, then assigns a plan through `ClientPlanRegistry`.
3. Client pipeline/onboarding/execution services authenticate through current request context and call route registries.
4. Template services and workflow engines create workflow definitions/instances and persist them to JSON.
5. Monetization records usage through `UsageTracker` and uses static plan definitions from `DEFAULT_PLANS`.

## 12. Configuration and Dependency Assessment

Confirmed backend dependency state:

- No `requirements.txt`, `pyproject.toml`, `setup.py`, `setup.cfg`, `Pipfile`, or `poetry.lock` was found.
- Runtime imports available in the current environment: FastAPI `0.128.8`, Pydantic `2.13.4`, Uvicorn `0.39.0`.
- These Python versions are environment observations, not repository-pinned package versions.

Confirmed frontend dependency state:

- `cockpit-ui/package.json`: React `18.3.1`, React DOM `18.3.1`, Vite `5.4.14`, `@vitejs/plugin-react` `4.3.4`.
- `cockpit-ui/package-lock.json`: lockfileVersion `3`.

Configuration gaps:

- No backend environment example for `BBIOS_AUTH_TOKENS`.
- No central settings module or typed configuration object.
- No database URL or persistence backend selection mechanism.
- No Alembic config or migration directory.

## 13. Test Environment and Test Results

Confirmed test structure:

- Root test files: `tests/test_auth.py`, `tests/test_client_management.py`, `tests/test_client_pipeline.py`, `tests/test_cockpit.py`, `tests/test_domain.py`, `tests/test_execution.py`, `tests/test_integrations.py`, `tests/test_monetization.py`, `tests/test_observability.py`, `tests/test_onboarding.py`, `tests/test_task_api.py`, `tests/test_task_service.py`, `tests/test_workflow_templates.py`, `tests/test_workflows.py`.
- Package-local tests exist under `bbi_os/client_pipeline/tests/`, `bbi_os/client_onboarding/tests/`, `bbi_os/client_execution/tests/`, `bbi_os/client_monetization/tests/`, and `bbi_os/cockpit/tests/`.
- Tests use `tempfile.TemporaryDirectory()` and JSON files such as `tasks.json`, `clients.json`, `executions.json`, `workflows.json`, `instances.json`, `templates.json`, `lineage.json`, `integrations.json`, `plans.json`, and `usage.json`.
- Tests include fake request objects, fake transports, capture actions, and stub services/templates.

Commands run:

- `python3 -m unittest discover`
  - Result: failed
  - Total: 34 tests run
  - Passed: 33
  - Errors: 1
  - Failures: 0
  - Skipped: 0
  - Error: `ImportError: cannot import name 'CockpitApiHandler' from 'bbi_os.cockpit.api'`

- `python3 -m unittest discover tests`
  - Result: failed
  - Total: 80 tests run
  - Passed: 79
  - Errors: 1
  - Failures: 0
  - Skipped: 0
  - Error: `tests/test_cockpit.py` imports `bbi_os.cockpit.tests.test_cockpit`, which imports missing `CockpitApiHandler` from `bbi_os.cockpit.api`

- `python3 -m pytest`
  - Result: blocked by environment
  - Reason: active Python environment reports `No module named pytest`

Assessment: Existing failures appear to be repository/interface drift, not a database or environment limitation. The pytest command is blocked because pytest is not installed and the repository does not declare it as a dependency.

## 14. Security and Data-Protection Observations

Confirmed:

- `bbi_os/auth.py` uses opaque bearer tokens mapped through `BBIOS_AUTH_TOKENS`; no token values were exposed in this report.
- `TaskRequestHandler` applies authentication/authorization for versioned routes using roles `admin`, `user`, and `readonly`.
- `ConnectorDefinition` rejects connector URLs containing credentials or fragments and stores `credential_env` rather than credential values.
- `OutboundRequestEngine` reads connector credentials from environment variables and injects authorization headers.
- `WebhookRegistration` stores `secret_env`, and `WebhookService` reads the signing secret from the environment.
- `Observability.log()` writes structured records including `user_id`, `role`, event metadata, and request IDs.

Risks:

- Environment secret names are persisted in JSON connector/webhook registrations; values are not persisted by design, but names can still reveal integration intent.
- No centralized secret management abstraction exists.
- No backend configuration schema validates required environment variables at startup.
- Structured logs can include arbitrary metadata from services and external integrations; logging redaction policy is not centralized.
- The FastAPI cockpit prototype route uses no auth middleware or dependencies.

## 15. Technical Debt and Duplication

Confirmed debt:

- Two cockpit concepts coexist: the FastAPI prototype in `bbi_os/cockpit/router.py`/`service.py`, and richer dashboard/control tests expecting `CockpitApiHandler` plus a constructor-injected `CockpitService`.
- `bbi_os/cockpit/tests/test_cockpit.py` imports `CockpitApiHandler`, but `bbi_os/cockpit/api.py` only defines a FastAPI `app`.
- `bbi_os/cockpit/tests/test_cockpit.py` constructs `CockpitService` with many dependencies, but `bbi_os/cockpit/service.py` currently defines `CockpitService.__init__(self)` with no injected dependencies.
- API handling is split between FastAPI routers and custom `BaseHTTPRequestHandler`/handler classes.
- Response shape differs between the original FastAPI cockpit service dictionaries and standardized `response_envelope()` responses used by internal handlers.
- JSON repository read/write code is duplicated across multiple repositories.
- Validation is split across Pydantic only for the simple cockpit request and manual dataclass `from_dict()` methods elsewhere.
- IDs and timestamps are generated directly in services/engines instead of through injectable clock/ID providers.

## 16. PostgreSQL Readiness Assessment

Readiness strengths:

- Several service classes already accept repository collaborators, which supports replacing JSON repositories with database-backed repositories.
- JSON repositories isolate persistence details for tasks, entities, workflows, templates, executions, plan assignments, usage events, and integrations.
- Tests use temporary storage paths, demonstrating a useful pattern for future isolated database tests.
- Domain objects have explicit serialization methods such as `to_dict()`, `from_dict()`, and `to_record()`.

Prerequisites before PostgreSQL implementation:

- Fix the cockpit API/service drift causing the current test import error.
- Establish one supported backend application composition path.
- Declare backend dependencies and Python version.
- Decide whether FastAPI will be the only production HTTP boundary or whether `TaskRequestHandler` remains supported.
- Define database schema ownership for entities currently stored as generic JSON metadata versus strongly typed tables.
- Introduce transaction boundaries for multi-write operations.
- Add database-backed test isolation strategy.

Assessment: PostgreSQL can be introduced safely after these prerequisites. Direct replacement of JSON writes with database writes would be risky because workflows, templates, onboarding, client creation, monetization, and execution state perform related writes without a shared transaction boundary.

## 17. SQLAlchemy 2.x Readiness Assessment

Confirmed: No SQLAlchemy code exists. No ORM models, sessions, engines, metadata, or repositories are present.

Recommended SQLAlchemy 2.x direction:

- Use SQLAlchemy 2.x typed declarative models separate from current dataclass domain/request objects.
- Start with repository implementations behind existing repository/service seams.
- Add explicit session management and transaction scopes at service/application boundaries.
- Preserve domain-level validation in services/dataclasses initially, then decide whether Pydantic/dataclass/ORM validation responsibilities should be consolidated.
- Avoid leaking SQLAlchemy session objects into routers or domain models.

Main readiness gap: Existing repositories expose simple CRUD methods but no unit-of-work protocol, no transaction propagation, no optimistic locking/version columns, and no relationship-loading strategy.

## 18. Alembic Migration Readiness Assessment

Confirmed: No Alembic configuration exists.

Prerequisites:

- Add backend dependency metadata first.
- Define SQLAlchemy metadata and naming conventions.
- Establish initial schema from current JSON shapes.
- Decide which JSON metadata fields remain JSONB and which become normalized columns.
- Create seed/initial-data strategy for immutable plans from `DEFAULT_PLANS`.
- Create data migration tooling from existing JSON files if production JSON data exists outside tests.

Alembic readiness: Not ready until SQLAlchemy metadata and a database URL/settings layer exist.

## 19. Risks and Potential Failure Modes

Highest-risk areas:

- Multi-entity operations without transactions: `ClientManagementService.create()` saves a client and then assigns a plan with manual rollback; workflow/template execution writes definitions, instances, and lineage; onboarding creates linked entities/tasks/workflows.
- Interface drift: tests reference `CockpitApiHandler` and richer cockpit service methods that are not present in the current implementation.
- Generic metadata storage: `BaseEntity.metadata`, workflow inputs/outputs, template schemas, connector schemas, and event metadata are flexible dictionaries that need explicit JSONB/relational modeling decisions.

Additional risks:

- UUID strings are generated in many services; schema constraints must standardize UUID handling.
- Timestamp strings use both `datetime.utcnow().isoformat()` and timezone-aware `timestamp()` with `Z`; database timestamp normalization is required.
- Process-local locks protect only one process and will not protect multi-worker deployments.
- Read-modify-write JSON semantics may hide concurrency assumptions that PostgreSQL will expose.
- Tests rely heavily on temporary files and manual object wiring; database fixtures must replace this without cross-test leakage.
- Observability and cockpit event stores are process-local; persistence expectations must be clarified.
- External connector/webhook behavior needs transaction and retry policies around side effects.

## 20. Recommended Migration Strategy

Phase 0: Stabilize existing baseline.

- Fix or intentionally retire the `CockpitApiHandler`/cockpit service drift.
- Declare backend dependencies and supported Python version.
- Confirm one canonical backend startup path.
- Validation gate: `python3 -m unittest discover tests` passes with 0 failures/errors.
- Rollback: revert only stabilization changes if tests regress.

Phase 1: Add persistence abstraction contracts.

- Define repository protocols for each persisted aggregate where absent.
- Introduce a unit-of-work or transaction boundary abstraction.
- Keep JSON repositories as the active implementation.
- Validation gate: all existing tests pass against JSON implementations.
- Rollback: keep JSON repositories as default and disable DB implementation by configuration.

Phase 2: Add SQLAlchemy 2.x infrastructure behind feature flags.

- Add settings for database URL.
- Add engine/session factory and typed ORM models.
- Add SQLAlchemy repositories without changing API behavior.
- Validation gate: repository contract tests pass against both JSON and PostgreSQL test backends.
- Rollback: switch persistence backend setting back to JSON.

Phase 3: Introduce Alembic migrations.

- Create initial migration from ORM metadata.
- Add migration validation in local/test workflow.
- Seed immutable reference data such as default plans.
- Validation gate: new database can migrate from empty to current schema and run repository tests.
- Rollback: downgrade migration in non-production test database and retain JSON source data.

Phase 4: Controlled data migration.

- Export/transform existing JSON records.
- Load into PostgreSQL with validation counts and referential checks.
- Run dual-read or shadow-read validation where practical.
- Validation gate: record counts, IDs, timestamps, relationships, workflow histories, lineage, usage totals, and billing summaries match.
- Rollback: stop writes to PostgreSQL, restore JSON backend, and preserve migration logs.

Phase 5: Cut over writes.

- Enable PostgreSQL repositories for a controlled environment.
- Monitor errors, latency, transaction rollbacks, and data consistency.
- Validation gate: API tests, workflow tests, execution tests, monetization tests, and cockpit read tests pass against PostgreSQL.
- Rollback: return persistence backend to JSON only if no writes require reverse migration, or run a verified reverse-export if writes occurred.

## 21. Proposed File Changes

No implementation changes are authorized in this assessment.

Recommended future file additions, pending human approval:

- Backend dependency manifest: `pyproject.toml` or `requirements.txt`
- Settings module: for database URL and auth/secret environment validation
- SQLAlchemy infrastructure package: engine/session/base models
- Repository protocol refinements and SQLAlchemy implementations
- Alembic configuration and migration versions
- Database test fixtures and repository contract tests

## 22. Validation Gates and Acceptance Criteria

Before database work:

- Current canonical test command passes.
- Backend dependency manifest exists and can recreate the environment.
- Canonical app startup is documented and verified.
- All API surfaces intended for production are wired into that app or explicitly marked internal/test-only.

Before PostgreSQL write enablement:

- SQLAlchemy repositories satisfy the same behavioral tests as JSON repositories.
- Every multi-write service has a transaction boundary.
- IDs, timestamp types, indexes, uniqueness rules, foreign keys, nullable fields, and JSONB fields are documented.
- Alembic migrations run from empty database to head.
- Rollback path is tested outside production.

Acceptance criteria for readiness:

- `python3 -m unittest discover tests` reports 0 failures/errors.
- Database-backed test suite passes with isolated test database setup/teardown.
- JSON-to-database migration validation proves record-count and business-summary parity.
- No secrets are written to database tables or logs; only secret environment variable names are stored where still required.

## 23. Rollback and Recovery Considerations

- Keep JSON repositories available until PostgreSQL parity is proven.
- Treat existing JSON files as source-of-truth backups during initial migration.
- Use feature/config switch for persistence backend selection.
- For migrations, test Alembic downgrade only where data-preserving rollback is realistic; otherwise define restore-from-backup.
- For external side effects, do not wrap HTTP calls and database commits in a way that creates ambiguous partial completion without an outbox, compensation, or idempotency strategy.
- For client creation and onboarding, replace manual delete-based rollback with database transactions before enabling PostgreSQL writes.

## 24. Recommended Implementation Order

1. Resolve cockpit API/service/test drift.
2. Add backend dependency manifest and environment documentation.
3. Decide canonical HTTP/application architecture.
4. Define persistence boundaries and transaction/unit-of-work contracts.
5. Add SQLAlchemy models and database repositories behind a disabled-by-default backend setting.
6. Add Alembic migrations and database test fixtures.
7. Build JSON export/import validation.
8. Run dual repository contract tests.
9. Perform controlled migration and monitored cutover.

## 25. Open Questions and Required Decisions

- Should `bbi_os.cockpit.api:app` or `bbi_os.__main__:app` be the canonical backend entry point?
- Are the `/v1/*` internal handler routes intended to become FastAPI endpoints?
- Should generic `BaseEntity.metadata` remain JSONB or be split into typed relational tables for clients, tasks, users, and onboarding records?
- Are workflow definitions/templates immutable after creation in production?
- Should workflow-generated resolved definitions be persisted permanently, or can they be derived from template lineage?
- What production JSON files, if any, need migration?
- What database isolation level and concurrency expectations apply to client execution?
- Should observability events be persisted to PostgreSQL, streamed externally, or remain process-local?
- What is the retention policy for usage events, execution histories, webhook registrations, and connector definitions?
- Should connector/webhook environment variable names be considered sensitive metadata?

## 26. Final Readiness Determination

Final classification: **Ready with prerequisites**.

Confirmed rationale: The repository has enough separation to support a controlled PostgreSQL migration after stabilization. JSON repositories and constructor-injected services provide useful seams. The current blockers are not conceptual; they are operational and architectural readiness issues that should be resolved before introducing PostgreSQL, SQLAlchemy 2.x, or Alembic.

Primary prerequisites:

- Restore the test baseline by resolving the missing `CockpitApiHandler` and cockpit service/API drift.
- Create backend dependency and configuration management.
- Establish transaction-aware repository/session boundaries before replacing JSON persistence.
