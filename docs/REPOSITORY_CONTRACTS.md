# BBIOS OS Repository Contracts

## 1. Supported Python Version

The supported runtime contract is Python `>=3.12,<3.13`, with Python 3.12.13 validated for development and tests.

## 2. Canonical Application Entry Point

The canonical application factory is `bbi_os.app.create_app()`. The canonical module-level application instance is `bbi_os.app.app`.

Legacy imports from `bbi_os.__main__` and `bbi_os.cockpit.api` remain supported and must reference the same canonical app object.

## 3. Canonical Settings Access

Application metadata, host, port, debug flag, log level, API prefix, and data directory must be read through `bbi_os.settings.get_settings()` or `bbi_os.settings.load_settings()`.

Credential and secret reads currently present in auth and integration modules are legacy configuration debt and must not be expanded without a security/configuration approval.

## 4. Canonical API Structure

The approved target API structure is versioned FastAPI routes delegating to handlers/adapters and then to application services. Full `/v1/*` FastAPI consolidation is not implemented yet, but stable task and client-management handler contracts now have focused FastAPI adapters.

Current supported API surfaces are:

- FastAPI prototype cockpit routes under the configured cockpit prefix, defaulting to `/cockpit`.
- FastAPI adapter routes for `/v1/tasks`, `/v1/tasks/{task_id}`, `/clients`, and `/v1/clients`.
- Internal handler-style `/v1/*` routes through `TaskRequestHandler` and `EntityRouteRegistry`.
- Compatibility `/clients` handling normalized by `TaskRequestHandler`.

Route-registration ownership for the current FastAPI app lives in `bbi_os.app.create_app()`, which includes `bbi_os.cockpit.router.router` under the configured API prefix, includes `bbi_os.api.v1.router` once, and registers `/` and `/health`.

`bbi_os.api.v1` owns the current FastAPI adapter boundary. Adapter functions must translate FastAPI path/body/header inputs into the existing handler request shape, delegate to handlers or handler-backed services, and return the captured status code and response body without response-envelope redesign.

Deferred handler contracts include `/v1/cockpit/*`, workflow, execution, monetization, onboarding, pipeline, integration, webhook, and workflow-template routes whose runtime service composition is not yet approved for the canonical FastAPI app.

## 5. Canonical Handler Boundary

Handlers and adapters translate request/response concerns, route matching, body parsing, status codes, and error mapping. They must delegate business behavior to services and preserve existing response envelopes.

Known handlers include `TaskRequestHandler`, `WorkflowApiHandler`, `WorkflowTemplateApiHandler`, `ClientExecutionApiHandler`, `ClientPipelineApiHandler`, `ClientMonetizationApiHandler`, `ClientManagementApiHandler`, `ConnectorApiHandler`, `WebhookApiHandler`, and `CockpitApiHandler`.

## 6. Canonical Service Boundary

Application services own orchestration and business rules. Services may coordinate repositories, engines, dashboards, controls, and observability, but they must not depend on private repository implementation methods.

Compatibility services may retain optional constructor dependencies only when preserving an existing public contract.

## 7. Canonical Repository Boundary

Repositories expose public methods for supported reads and writes. Current public repository methods include patterns such as `list()`, `get()`, `save()`, `delete()`, `latest_for_client()`, `list_for_client()`, `save_definition()`, `get_definition()`, `save_instance()`, and `get_instance()`.

Private methods such as `_read()` and `_write()` are implementation details. They may remain inside repository implementations while JSON storage is current, but application services must use public methods.

## 8. Canonical Data-Transfer Approach

Domain data should cross stable internal boundaries as dataclasses or typed records where they already exist. Dictionaries are acceptable at HTTP request/response boundaries, prototype compatibility paths, flexible metadata fields, and legacy task data.

Existing JSON file structures must not change without a migration plan.

## 9. Public Import Paths

Supported public imports are the module-level paths currently exercised by the test suite, including:

- `bbi_os.settings`
- `bbi_os.auth`
- `bbi_os.domain`
- `bbi_os.entity_repository`
- `bbi_os.entity_routing`
- `bbi_os.response_contract`
- service, handler, repository, model, engine, dashboard, control, and analytics modules under `bbi_os/*`

Package-level re-export policy remains deferred. Do not remove existing import paths without approval.

## 10. Private Implementation Rules

Names beginning with `_` are private to their defining module or class. Production code outside that owner must not call them. Existing private repository methods may remain as compatibility wrappers or implementation helpers until storage cleanup is approved.

## 11. Exception-Handling Contract

Handlers must map domain exceptions to structured error responses without leaking internal exception details. Internal handler errors should use `error_response()` and preserve the standard envelope.

Unexpected internal errors should return generic failure messages while observability records the error event.

## 12. Logging Boundary

Structured observability is provided by `bbi_os.observability`. Services, repositories, handlers, workflow engines, and external integration paths may emit events through `get_observability()`.

Logging must preserve request context, avoid interrupting business execution through listener failures, and avoid committing secrets or credential values.

## 13. Compatibility Policy

Compatibility layers remain valid until explicit deprecation is approved. Current compatibility layers include legacy app imports from `bbi_os.__main__` and `bbi_os.cockpit.api`, the cockpit prototype routes, richer cockpit handler/facade paths, `/clients` and `/v1/clients` FastAPI adapters, `/clients` normalization, zero-argument `CockpitService()`, and top-level test wrappers.

## 14. Deprecation Policy

Deprecation requires a documented decision, route/import inventory, tests for both old and new behavior during transition, and human approval before removal.

Silent removal of endpoints, imports, response fields, storage fields, or handler methods is not allowed.

## 15. Testing Expectations

The canonical test command is:

```bash
python -m unittest discover tests
```

New cleanup work should add focused unittest coverage when it changes a public contract or protects an existing compatibility behavior. Do not introduce pytest as required tooling without approval.

## 16. Persistence Migration Expectations

PostgreSQL, SQLAlchemy, and Alembic are planned future work, not current implementation. Persistence migration must begin with repository parity tests, transaction ownership, schema decisions, migration rollback planning, and compatibility validation.

## 17. Frontend Integration Expectations

The React cockpit currently expects read-only `/v1/cockpit/*` endpoints and `/clients` list/create behavior. The `/clients` list/create path is now served by the FastAPI adapter. The `/v1/cockpit/*` paths remain deferred until rich cockpit runtime composition is approved. Future FastAPI consolidation must either preserve these paths or update frontend usage under an approved compatibility plan.

## 18. Contract Change Approval Rules

Human approval is required before:

- changing public import paths;
- changing route paths or response envelopes;
- removing compatibility layers;
- changing JSON file formats;
- adding PostgreSQL, SQLAlchemy, Alembic, Docker, CI/CD, deployment, or authentication behavior;
- changing supported Python runtime ranges;
- adding broad package exports or renaming modules.
