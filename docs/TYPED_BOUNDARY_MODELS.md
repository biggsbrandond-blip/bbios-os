# BBIOS OS Typed Boundary Models

## 1. Document Control

- Document: Typed Boundary Models
- Phase: 2F Typed Service Boundary Models
- Branch: `phase-2/repository-contract-cleanup`
- Baseline before Phase 2F: commit `e7c53bc`, 117 tests passing
- Scope: narrow typed-model boundary for stable internal service operations
- Out of scope: PostgreSQL, SQLAlchemy, Alembic, Pydantic migration, API redesign, response redesign, repository schema changes, authentication, deployment, Docker, CI/CD, unit-of-work implementation, and broad DTO migration

## 2. Executive Summary

Phase 2F introduced typed task service input models while preserving all external contracts. The selected boundary is task creation and update inside `TaskService`, because task payload validation is stable, task routes already have handler and FastAPI adapter coverage, and task persistence remains JSON-backed dictionaries.

Confirmed implementation: `TaskCreateRequest` and `TaskUpdateRequest` in `bbi_os/task_management/models.py` provide `from_dict()` translation for legacy callers and `to_dict()` compatibility where the service must update existing task records.

No HTTP body, route, response envelope, status code, repository return type, JSON file layout, exception message, or application behavior changed.

## 3. Complete Typed-Boundary Inventory

| Boundary | Source | Consumer | Current Type | Keys or Fields | Translation | Status | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Task create | `TaskRequestHandler._post()`, `bbi_os/api/v1.py` | `TaskService.create()` | Dict request payload | `title`, `description`, `status` | `TaskCreateRequest.from_dict()` in service | Implemented in Phase 2F | Low |
| Task update | `TaskRequestHandler._patch()`, `bbi_os/api/v1.py` | `TaskService.update()` | Dict request payload | Optional `title`, `description`, `status`; at least one required | `TaskUpdateRequest.from_dict()` in service | Implemented in Phase 2F | Low |
| Task record | `TaskService`, `JsonTaskRepository` | Handlers, adapters, repository | Dict record | `id`, `title`, `description`, `status`, `created_at`, `updated_at` | None; preserved as repository/output dict | Deferred | Medium |
| Client creation | `/clients`, `/v1/clients` adapter and `ClientManagementApiHandler` | `ClientManagementService.create()` | Dict request payload | `name`, `plan` | Inline service validation | Deferred | Low |
| Client record | `ClientManagementService` | API handlers and frontend-compatible adapter | Dict response over `BaseEntity` | `id`, `name`, `plan`, `created_at` | `BaseEntity` plus plan registry lookup | Deferred | Medium |
| Prototype cockpit client | `bbi_os/cockpit/router.py` | `CockpitService.create_client()` | Separate string parameters and dict result | `client_name`, `plan`, `created_at` | Inline prototype facade | Deferred compatibility | Medium |
| Client execution request | Execution handlers and cockpit controls | `ClientExecutionService.start()`, `schedule()` | Dict accepted, typed internally | `client_id`, `execution_type`, `workflow_id`, `input` | `ClientExecutionRequest.from_dict()` | Existing typed model | Low |
| Client execution record | Engine, state repository, cockpit dashboards | Services and dashboards | `ClientExecutionRecord` dataclass | execution id, client id, workflow id, state, transitions, timestamps, output | `to_dict()` and `from_dict()` | Existing typed model | Low |
| Workflow control request | Cockpit controls | `ExecutionControls.start()` | Dict accepted, typed internally | `client_id`, `workflow_id`, `input`, optional `execution_type` | `WorkflowControlRequest.from_dict()` | Existing typed model | Low |
| Usage event request | Monetization API/service and automatic metering | `ClientMonetizationService.track()`, `record_automatic()` | Dict accepted for API, typed internally | `client_id`, `event_type`, `usage_units`, `metadata` | `UsageEventRequest.from_dict()` or constructor | Existing typed model | Low |
| Usage event record | Usage tracker and monetization service | Billing and metrics | `UsageEvent` dataclass | usage id, client id, event type, units, cost, metadata, timestamp, source | `to_dict()` and `from_dict()` | Existing typed model | Low |
| Billing summary | Billing generator | Monetization service/API | `BillingSummary` dataclass | client id, total units, cost, breakdown | `to_dict()` | Existing typed model | Low |
| Client pipeline request | Pipeline API/service | `ClientPipelineService.process()` | Dict accepted, typed internally | `type`, `payload`, `user_id` | `ClientRequest.from_dict()` | Existing typed model | Low |
| Client pipeline result | Pipeline engine/service | API handler | `ClientPipelineResult` dataclass | request type, template id/version, workflow instance id, status, output | `to_dict()` | Existing typed model | Low |
| Onboarding request | Onboarding API/service | `OnboardingService.onboard()` | Dict accepted, typed internally | `user_id`, `client_name`, `request_type`, `payload` | `OnboardingRequest.from_dict()` | Existing typed model | Low |
| Onboarding result | Onboarding engine/service | API handler | `OnboardingResult` dataclass | onboarding ids, workflow ids, task id, status, output | `to_dict()` | Existing typed model | Low |
| Workflow definition | Workflow API/templates | `WorkflowEngine.create_definition()` | Dict accepted, typed internally | workflow id, name, description, steps, trigger type, schemas | `WorkflowDefinition.from_dict()` | Existing typed model | Medium |
| Workflow instance | Workflow repository/engine | Status, history, execution monitor | `WorkflowInstance` dataclass | instance id, workflow id, step index, status, history, timestamps, input/output | `to_dict()` and `from_dict()` | Existing typed model | Medium |
| Base entity record | Entity repository | Client management, onboarding actions | `BaseEntity` dataclass | entity id, type, timestamps, metadata | `to_record()` and `from_record()` | Existing typed model | Low |
| Cockpit dashboards | Cockpit service | FastAPI prototype/internal handler tests | Dict view models | Overview, client, execution, usage, billing, workflow-control aggregates | Dashboard render methods | Deferred | Medium |
| Integration/webhook records | Integration handlers/services | Registry and workflow engine | Dataclasses plus dict payloads | Connector, webhook, request/response metadata | Existing model conversions where defined | Deferred | Medium |

## 4. Selected Boundary

The selected boundary is task service input:

- `TaskService.create()` now accepts either a legacy dictionary or `TaskCreateRequest`.
- `TaskService.update()` now accepts either a legacy dictionary or `TaskUpdateRequest`.
- `TaskService.create_task()` and `TaskService.update_task()` are typed internal service operations.

This boundary was selected because task create/update payloads have stable fields, existing validation messages, existing handler tests, existing FastAPI adapter tests, and a simple JSON repository shape. It avoids route, response, repository, and persistence changes.

## 5. Current Dictionary Contract

Task creation currently accepts a JSON object with `title`, `description`, and `status`. Task update accepts a JSON object with one or more of those same fields. The valid status values remain `pending`, `in-progress`, and `complete`.

Validation failures preserve the existing `ValidationError` messages:

- `Request body must be a JSON object`
- `Unknown field(s): ...`
- `Missing field(s): ...`
- `'title' must be a string`
- `'description' must be a string`
- `'status' must be pending, in-progress, or complete`
- `At least one field is required`

## 6. Typed Model Contract

`TaskCreateRequest` is a frozen dataclass with `title`, `description`, and `status` fields. `TaskUpdateRequest` is a frozen dataclass with optional update fields that preserve the distinction between absent fields and fields explicitly provided as invalid values.

Both models expose `from_dict()` to keep HTTP handlers and existing callers dictionary-compatible. Both expose `to_dict()` so service logic can continue persisting the same dictionary record shape.

## 7. Translation Behavior

Dictionary callers enter through `TaskService.create()` and `TaskService.update()`. The service converts dictionaries into typed request models before invoking the typed operations.

Typed callers can use `TaskService.create_task()` and `TaskService.update_task()` directly, or pass typed request models to the legacy method names. The typed path creates the same task dictionaries, logs the same observability events, and persists the same JSON records.

## 8. Compatibility and Isolation

Handler and FastAPI adapter functions still pass dictionaries from request bodies. Response envelopes are still owned by `TaskRequestHandler` and `bbi_os/api/v1.py`. `JsonTaskRepository` still stores and returns dictionaries, and no JSON schema, file path, ordering, locking, or mutation semantics changed.

Phase 2G preserves this typed-boundary decision. `TaskService` now depends on the `TaskRepository` protocol from `bbi_os/persistence.py`, but the protocol still uses the existing dictionary task record shape so typed service inputs do not imply a repository record migration.

## 9. Remaining Typed-Boundary Debt

1. Client management create payloads remain dictionary-based in `ClientManagementService.create()`.
2. Cockpit prototype methods and dashboard view models remain dictionary-heavy compatibility surfaces.
3. Task repository records remain plain dictionaries until a repository record migration is separately approved.
4. Workflow definitions already use dataclasses internally but still accept rich nested dictionaries at API/service boundaries.
5. Integration and webhook payloads retain flexible dictionaries because external metadata and request bodies are intentionally open-ended.

## 10. Validation Expectations

Phase 2F must keep full unittest discovery passing, compileall passing, diff-check passing, and the working tree unstaged for human review. No files should be staged, committed, pushed, merged, or tagged during this task.
