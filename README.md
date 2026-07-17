# BBIOS OS — Sprint 007

Minimal persistent task-management HTTP API implemented with the Python standard library.

## Requirements

- Python 3.9 or newer

## Run

```bash
python3 -m bbi_os
```

The API listens on `http://127.0.0.1:8000` and stores tasks in `data/tasks.json`.
Set `BBIOS_HOST`, `BBIOS_PORT`, or `BBIOS_DATA_FILE` to override those defaults.

## API

Create a task:

```bash
curl -X POST http://127.0.0.1:8000/v1/tasks \
  -H 'Content-Type: application/json' \
  -d '{"title":"First task","description":"Validate Sprint 000","status":"pending"}'
```

List tasks:

```bash
curl http://127.0.0.1:8000/v1/tasks
```

Retrieve, update, or delete a task by replacing `<id>` with its UUID:

```bash
curl http://127.0.0.1:8000/v1/tasks/<id>
curl -X PATCH http://127.0.0.1:8000/v1/tasks/<id> \
  -H 'Content-Type: application/json' \
  -d '{"status":"complete"}'
curl -X DELETE http://127.0.0.1:8000/v1/tasks/<id>
```

Updates accept any combination of `title`, `description`, and `status`.

Successful responses use this envelope:

```json
{
  "request_id": "8f86b90e-608f-44c8-aee8-3243a74c11ef",
  "status": "success",
  "data": {},
  "execution_summary": {
    "workflow_instance_id": "",
    "duration_ms": 0.42,
    "steps_completed": [],
    "external_calls": [],
    "errors": []
  }
}
```

Errors use this envelope with a stable, machine-readable code:

```json
{
  "request_id": "8f86b90e-608f-44c8-aee8-3243a74c11ef",
  "status": "failure",
  "data": {
    "error": {"code": "VALIDATION_ERROR", "message": "Missing field(s): status"}
  },
  "execution_summary": {
    "workflow_instance_id": "",
    "duration_ms": 0.31,
    "steps_completed": [],
    "external_calls": [],
    "errors": [
      {"code": "VALIDATION_ERROR", "message": "Missing field(s): status"}
    ]
  }
}
```

## Observability

Every request receives an internal UUID request ID. Structured JSON logs correlate the
API lifecycle, service events, repository operations, errors, and request timing without
changing the API response contract.

Example log:

```json
{"timestamp":"2026-07-02T17:00:00Z","level":"INFO","event":"task_created","request_id":"60fde467-41cc-46d7-a30f-292abda060df","message":"Task created","metadata":{"event_type":"task_created","entity_id":"49ea7575-f549-464f-90ac-cd438af93528"}}
```

Request completion logs include start/end timestamps, duration, endpoint average,
request count, and slow-request status. Requests over 500 ms also emit a `WARNING` log.

## Authentication and roles

The API accepts opaque internal tokens using `Authorization: Bearer <token>`. Configure
tokens through `BBIOS_AUTH_TOKENS`; credentials are not stored in the task data file.

```bash
export BBIOS_AUTH_TOKENS='{
  "admin-local-token":{"user_id":"admin-1","username":"admin","role":"admin"},
  "user-local-token":{"user_id":"user-1","username":"operator","role":"user"},
  "readonly-local-token":{"user_id":"viewer-1","username":"viewer","role":"readonly"}
}'
python3 -m bbi_os
```

Role examples:

```bash
# Admin: full CRUD
curl -H 'Authorization: Bearer admin-local-token' http://127.0.0.1:8000/v1/tasks

# User: create, read, and update
curl -X POST -H 'Authorization: Bearer user-local-token' \
  -H 'Content-Type: application/json' \
  -d '{"title":"Task","description":"Owned work","status":"pending"}' \
  http://127.0.0.1:8000/v1/tasks

# Readonly: read only
curl -H 'Authorization: Bearer readonly-local-token' http://127.0.0.1:8000/v1/tasks
```

Requests without a token use an anonymous readonly identity. Reads are allowed; writes
return `UNAUTHORIZED`. Invalid tokens return `INVALID_TOKEN`, while authenticated users
without permission receive `FORBIDDEN`.

```json
{"request_id":"...","status":"failure","data":{"error":{"code":"FORBIDDEN","message":"Insufficient permissions"}},"execution_summary":{"workflow_instance_id":"","duration_ms":0,"steps_completed":[],"external_calls":[],"errors":[{"code":"FORBIDDEN","message":"Insufficient permissions"}]}}
```

## Domain extension model

Sprint 004 adds shared `BaseEntity`, `TaskEntity`, and `UserEntity` representations.
The adapters leave the existing task JSON schema and authentication identities unchanged.
Future domains can register an isolated repository and versioned route handler without
modifying task logic.

```text
HTTP /v1/{entity}
        |
        v
EntityRouteRegistry --> registered domain handler
        |
        +--> tasks ------> existing TaskService --> existing tasks.json
        |
        +--> future type -> domain service ------> isolated entity repository

BaseEntity
  +-- TaskEntity adapter <--> existing task record
  +-- UserEntity adapter <--> existing UserIdentity
  +-- future domain entity
```

`EntityRepositoryRouter` maps each entity type to exactly one repository. Generic JSON
repositories validate entity types and use separate files, preventing cross-domain data
leakage. Registered API domains inherit the existing authentication, RBAC, response,
and observability boundary.

## Workflow orchestration

Workflow definitions contain ordered entity-operation or function-call steps. Inputs can
reference trigger data (`$input.name`) or prior results (`$steps.step_id.field`), while
output mappings collect final workflow output. State is atomically persisted after every
transition.

```text
POST /v1/workflows
        |
        v
WorkflowDefinition --> WorkflowEngine --> ActionRegistry
                            |                  |-- tasks
                            |                  |-- users
                            |                  `-- future entities/functions
                            v
                    WorkflowInstance
                    + step history
                    + persisted state
                    + structured events
```

Create a definition:

```bash
curl -X POST http://127.0.0.1:8000/v1/workflows \
  -H 'Authorization: Bearer admin-local-token' \
  -H 'Content-Type: application/json' \
  -d '{
    "workflow_id":"onboard-task",
    "name":"Create assigned task",
    "description":"Read the current user and create a task",
    "trigger_type":"manual",
    "steps":[
      {"step_id":"current_user","step_name":"Read current user",
       "action_type":"entity_operation","target_entity":"users",
       "input_mapping":{"operation":"current"},
       "output_mapping":{"user_id":"$result.user_id"}},
      {"step_id":"create_task","step_name":"Create task",
       "action_type":"entity_operation","target_entity":"tasks",
       "input_mapping":{"operation":"create","title":"$input.title",
         "description":"$steps.current_user.user_id","status":"pending"},
       "output_mapping":{"task_id":"$result.id"}}
    ]
  }'
```

Trigger and inspect it:

```bash
curl -X POST http://127.0.0.1:8000/v1/workflow-executions \
  -H 'Authorization: Bearer user-local-token' \
  -H 'Content-Type: application/json' \
  -d '{"workflow_id":"onboard-task","input":{"title":"Review intake"}}'

curl -H 'Authorization: Bearer readonly-local-token' \
  http://127.0.0.1:8000/v1/workflow-executions/<instance-id>

curl -H 'Authorization: Bearer readonly-local-token' \
  http://127.0.0.1:8000/v1/workflow-history/<instance-id>
```

Execution is synchronous and deterministic. A failed step halts the workflow; completed
steps with compensation data are rolled back in reverse order. Failed instances can be
retried internally from a clean state. Workflow events preserve workflow, instance, step,
request, user, role, event type, and execution-status correlation.

## Workflow templates

Templates are immutable, reusable step blueprints stored by `template_id:version`.
Runtime parameters are validated, substituted into a deep copy of the blueprint, and used
to create a uniquely identified Sprint 005 workflow definition. The existing engine then
executes that resolved definition unchanged.

```text
Versioned Template
       |
       | validate and bind ${parameters}
       v
Resolved Workflow Definition (unique ID)
       |
       v
Sprint 005 Workflow Engine
       |
       +--> Workflow Instance
       `--> Persisted template lineage
```

Create and list templates:

```bash
curl -X POST http://127.0.0.1:8000/v1/workflow-templates \
  -H 'Authorization: Bearer admin-local-token' \
  -H 'Content-Type: application/json' \
  -d '{
    "template_id":"task-intake",
    "name":"Task intake",
    "description":"Create a parameterized intake task",
    "version":"v1",
    "parameter_schema":{
      "required":["title","owner_id"],
      "properties":{"title":{"type":"string"},"owner_id":{"type":"string"}}
    },
    "step_blueprint":[{
      "step_id":"create_task",
      "step_name":"Create task",
      "action_type":"entity_operation",
      "target_entity":"tasks",
      "input_mapping":{
        "operation":"create","title":"${title}",
        "description":"Owner: ${owner_id}","status":"pending"
      },
      "output_mapping":{"task_id":"$result.id"}
    }]
  }'

curl http://127.0.0.1:8000/v1/workflow-templates
curl 'http://127.0.0.1:8000/v1/workflow-templates/task-intake?version=v1'
```

Execute a specific version:

```bash
curl -X POST http://127.0.0.1:8000/v1/workflow-templates/task-intake/execute \
  -H 'Authorization: Bearer user-local-token' \
  -H 'Content-Type: application/json' \
  -d '{
    "version":"v1",
    "parameters":{"title":"Review contract","owner_id":"user-1"}
  }'
```

Omitting `version` selects the latest natural version. Publishing `v2` never overwrites
`v1`; older templates and their resolved workflow definitions remain executable. Lineage
records and structured events capture template ID, selected version, workflow instance,
parameter bindings, request ID, and user context.

## External integrations

Connectors are immutable, versioned definitions. They contain schemas and the name of an
environment variable—not its secret value. The outbound engine restricts calls to the
connector's HTTP(S) base URL, validates payloads, caps request/response sizes, applies a
fixed timeout, retries transient failures at most twice, and returns normalized data.

```text
Workflow connector step --------> OutboundRequestEngine --------> External API
        |                                  |
        |                                  +-- environment credential
        |                                  +-- schema validation
        |                                  +-- timeout / bounded retry
        |                                  `-- structured trace log
        v
Normalized response --> next workflow step

External system --> signed webhook --> sanitized payload --> mapped workflow
```

Register and test a connector:

```bash
export WEATHER_API_TOKEN='replace-with-local-secret'

curl -X POST http://127.0.0.1:8000/v1/connectors \
  -H 'Authorization: Bearer admin-local-token' \
  -H 'Content-Type: application/json' \
  -d '{
    "connector_id":"weather",
    "name":"Weather API",
    "type":"http_api",
    "base_url":"https://weather.example.com/v1",
    "auth_method":"bearer_token",
    "credential_env":"WEATHER_API_TOKEN",
    "version":"v1",
    "request_schema":{"type":"object"},
    "response_schema":{"type":"object"}
  }'

curl -H 'Authorization: Bearer readonly-local-token' \
  http://127.0.0.1:8000/v1/connectors

curl -X POST http://127.0.0.1:8000/v1/connectors/weather/test \
  -H 'Authorization: Bearer admin-local-token' \
  -H 'Content-Type: application/json' \
  -d '{"version":"v1","method":"GET","path":"current","query":{"city":"Boston"}}'
```

Workflow connector steps use `action_type: "function_call"`,
`target_entity: "connector"`, and an input mapping containing `connector_id`, `method`,
`path`, `query`, and/or `body`. Their normalized output can be referenced as
`$steps.<step_id>.data.<field>` by later steps.

Register and invoke a webhook:

```bash
export INTAKE_WEBHOOK_SECRET='replace-with-local-secret'

curl -X POST http://127.0.0.1:8000/v1/webhooks/register \
  -H 'Authorization: Bearer admin-local-token' \
  -H 'Content-Type: application/json' \
  -d '{
    "webhook_id":"intake",
    "workflow_id":"onboard-task",
    "secret_env":"INTAKE_WEBHOOK_SECRET",
    "payload_schema":{"type":"object","required":["title"]}
  }'

curl -X POST http://127.0.0.1:8000/v1/webhooks/invoke \
  -H 'Authorization: Bearer admin-local-token' \
  -H 'X-Webhook-Signature: sha256=<hex-hmac>' \
  -H 'Content-Type: application/json' \
  -d '{"webhook_id":"intake","payload":{"title":"External request"}}'
```

The signature is an HMAC-SHA256 of canonical compact JSON (sorted keys). Webhook callers
also cross the existing BBIOS authentication boundary. Failures use the standard API
envelope with `EXTERNAL_REQUEST_FAILED`, `WEBHOOK_VALIDATION_FAILED`,
`CONNECTOR_NOT_FOUND`, or `TIMEOUT_ERROR`.

## Client automation pipeline

The client pipeline is the business-facing composition layer. It does not implement new
workflow, template, connector, auth, or logging behavior; it routes authenticated client
requests through those existing systems.

```text
POST /v1/client/request
        |
        +--> Sprint 003 authentication + user match
        +--> request-type router
        +--> Sprint 006 template selection / parameter binding
        +--> Sprint 005 workflow execution
        +--> Sprint 007 connector actions (when present)
        `--> Sprint 002 correlated result event
```

Configured request mappings:

```text
onboarding      -> onboarding_template_v1
task_flow       -> task_execution_template_v1
external_action -> connector_workflow_template_v1
```

The referenced templates must exist in the workflow template library before those request
types are invoked. Additional mappings can be registered without changing pipeline logic.

```bash
curl -X POST http://127.0.0.1:8000/v1/client/request \
  -H 'Authorization: Bearer user-local-token' \
  -H 'Content-Type: application/json' \
  -d '{
    "type":"onboarding",
    "payload":{"title":"Onboard Acme"},
    "user_id":"user-1"
  }'
```

The body `user_id` must match the authenticated user. Successful responses return template
and workflow lineage plus final workflow output. Pipeline events include request ID, user,
template ID, workflow instance ID, status, and total execution time. Errors use
`INVALID_REQUEST_TYPE`, `WORKFLOW_NOT_FOUND`, or `PIPELINE_EXECUTION_FAILED` in the
standard response envelope.

## COS-001 client onboarding

COS-001 is the first concrete workflow product built on the client application boundary.
It installs three onboarding template mappings and executes the selected immutable template
through the existing workflow engine.

```text
POST /v1/client/onboarding
        |
        +--> authenticate and verify user_id
        +--> select basic / premium / enterprise template
        +--> validate client
        +--> create client entity
        +--> verify and persist authenticated role assignment
        +--> create onboarding task
        +--> optionally call external setup connector
        +--> create linked onboarding record
        `--> return result + emit end-to-end trace
```

Mappings:

```text
basic_onboarding      -> onboarding_template_v1
premium_onboarding    -> onboarding_template_v2
enterprise_onboarding -> onboarding_template_v3
```

The templates are installed idempotently at startup. All currently share the six-step
COS-001 foundation and remain independently versionable. Because Sprint 003 identities are
environment-backed and immutable, the role step verifies the authenticated role and records
it on the client entity; it does not modify credentials or elevate access.

```bash
curl -X POST http://127.0.0.1:8000/v1/client/onboarding \
  -H 'Authorization: Bearer user-local-token' \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id":"user-1",
    "client_name":"Acme Corporation",
    "request_type":"basic_onboarding",
    "payload":{}
  }'
```

To enable optional external setup, first register a connector and include its ID:

```json
{
  "user_id": "user-1",
  "client_name": "Acme Corporation",
  "request_type": "enterprise_onboarding",
  "payload": {"external_connector_id": "crm"}
}
```

Example execution trace:

```text
validate_client       completed
create_client         completed  -> client entity ID
assign_role           completed  -> authenticated user/role persisted
create_task           completed  -> task ID
external_setup        completed or skipped
complete              completed  -> onboarding entity + workflow link
```

Connector failure halts the workflow and compensates reversible client/task changes. The
final observability event includes onboarding request ID, request/user correlation, template,
workflow instance, client entity, duration, and status.

## COS-002 client execution runtime

COS-002 executes existing templates for clients created by COS-001. It does not define
workflows or business rules. Immediate executions run synchronously; scheduled and recurring
requests are persisted as `PENDING` records for a future authorized scheduler to claim.

```text
COS-001 client entity
        |
        v
COS-002 request validation
        |
        +--> PENDING --> RUNNING --> COMPLETED
        |                 |
        |                 +--> WAITING_EXTERNAL --> RUNNING
        |                 `--> COMPENSATING --> FAILED
        v
Sprint 006 template --> Sprint 005 engine --> tasks/connectors
```

Start an immediate execution:

```bash
curl -X POST http://127.0.0.1:8000/v1/client/execute \
  -H 'Authorization: Bearer user-local-token' \
  -H 'Content-Type: application/json' \
  -d '{
    "client_id":"<cos-001-client-id>",
    "execution_type":"one_time",
    "workflow_id":"<existing-template-id>",
    "input":{}
  }'
```

Schedule and inspect execution state:

```bash
curl -X POST http://127.0.0.1:8000/v1/client/schedule-execution \
  -H 'Authorization: Bearer user-local-token' \
  -H 'Content-Type: application/json' \
  -d '{
    "client_id":"<cos-001-client-id>",
    "execution_type":"scheduled",
    "workflow_id":"<existing-template-id>",
    "input":{}
  }'

curl -H 'Authorization: Bearer user-local-token' \
  http://127.0.0.1:8000/v1/client/execution-status/<client-id>
```

The governance response envelope remains authoritative. COS-002 fields (`client_id`,
execution status, workflow instance, rollback actions, and state history) are returned under
`data`; trace-derived steps, external calls, duration, and errors remain under
`execution_summary`. Only one immediate execution may run per client at a time.

## COS-003 client monetization

COS-003 observes COS-001/COS-002 completion signals and records isolated, persistent usage
events. It never executes workflows or changes execution outcomes. Listener failures are
contained by the observability boundary, so metering and billing failures cannot interrupt
client execution.

```text
COS-001 / COS-002 observability events
                |
                v
        Usage signal meter
                |
                +--> per-client usage ledger
                +--> plan policy checks
                `--> logical billing summary
```

The default `basic` plan is assigned when a client has no explicit plan record. Plan
definitions are immutable and include usage limits, connector access, workflow-complexity
limits, and rate limits. Billing uses deterministic decimal rates and does not process
payments.

```bash
curl -H 'Authorization: Bearer user-local-token' \
  http://127.0.0.1:8000/v1/client/plan/<client-id>

curl -X POST http://127.0.0.1:8000/v1/client/usage-event \
  -H 'Authorization: Bearer user-local-token' \
  -H 'Content-Type: application/json' \
  -d '{"client_id":"<client-id>","event_type":"workflow_execution","usage_units":1,"metadata":{}}'

curl -H 'Authorization: Bearer user-local-token' \
  http://127.0.0.1:8000/v1/client/usage/<client-id>

curl -X POST http://127.0.0.1:8000/v1/client/billing-summary \
  -H 'Authorization: Bearer user-local-token' \
  -H 'Content-Type: application/json' \
  -d '{"client_id":"<client-id>"}'
```

Automatic execution metering records one base unit plus one unit per completed workflow
step, and records connector calls separately. Manual usage ingestion enforces plan policy;
automatic observation remains non-blocking by design.

## Cockpit control plane

The Cockpit Layer is a logical, human-facing control plane over COS-001 through COS-003.
It provides dashboard contracts, operational analytics, and guarded command adapters without
implementing workflow, onboarding, connector, or pricing logic.

```text
Human operator
      |
      v
Cockpit API and dashboards
      |-- read models --> COS repositories + Sprint 002 events
      `-- commands ----> COS-002 public execution service
```

Read views aggregate client identity, execution state and history, workflow steps,
compensation details, connector activity, usage, billing summaries, system health, and
performance metrics. The bounded event view receives existing structured observability
records and preserves request ID and user traceability.

```text
GET  /v1/cockpit/system-overview
GET  /v1/cockpit/client/{client_id}
GET  /v1/cockpit/executions
GET  /v1/cockpit/usage
GET  /v1/cockpit/billing-summary
POST /v1/cockpit/workflow/execute
POST /v1/cockpit/workflow/retry
POST /v1/cockpit/workflow/cancel
```

Workflow starts and retries delegate to COS-002. The cockpit never writes workflow or
execution repositories directly. Pause and cancel commands are safe-rejected because the
current COS-002 state machine does not define those transitions; the cockpit does not invent
engine behavior or bypass the execution boundary. Template deployment is similarly rejected
because template definition is outside the cockpit's authority.

### Client creation

The Cockpit client boundary supports persistent client creation and listing without changing
COS-002 execution or COS-003 metering behavior.

```text
GET  /clients
POST /clients  {"name":"Acme","plan":"Pro"}
```

Clients use the existing isolated client entity store, while plan assignments use the existing
plan registry. Responses follow the shared request ID and execution-summary envelope.

## Test

```bash
python3 -m unittest discover -s tests -v
```
