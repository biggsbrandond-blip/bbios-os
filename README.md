# BBIOS OS

BBIOS OS is a modular FastAPI backend system designed as a backend engineering portfolio project. It models a business operating system for client management, task management, workflow execution, integrations, monetization concepts, observability, and an administrative Cockpit API surface.

The project focuses on production-style backend architecture: clear layers, stable service boundaries, repository contracts, operational readiness, structured error handling, and incremental evolution without broad rewrites.

BBIOS OS is not presented as a production SaaS platform. It is a portfolio-grade backend system that demonstrates disciplined engineering practices and a path from prototype architecture toward production readiness.

## Architecture Diagram

```text
Client / API Consumer
        |
        v
FastAPI Application
        |
        v
Middleware / Operational Layer
request correlation, health, readiness, metrics, error handling
        |
        v
Routers and Versioned API Adapters
        |
        v
Handlers / Request Adapters
        |
        v
Application Services
        |
        v
Repository Protocols
        |
        v
JSON Repository Implementations
        |
        v
JSON Persistence
```

The current runtime uses JSON persistence only. The architecture is intentionally shaped so future persistence implementations can be introduced behind stable repository contracts.

## Core Design Principles

### Layered Architecture

BBIOS OS separates HTTP concerns, middleware, routers, handlers, application services, repository contracts, and persistence. This keeps framework code away from core business behavior and makes the system easier to reason about.

### Service / Repository Separation

Services coordinate application behavior. Repositories own persistence access. Service code depends on stable repository contracts rather than directly managing storage details.

### Protocol-Based Contracts

Repository and service boundaries use narrow contracts to support substitution, testing, and future persistence migration without changing route behavior.

### Observability-First Design

Operational behavior is treated as a first-class backend concern. The system includes request correlation, structured logs, centralized error responses, liveness checks, readiness checks, and metrics.

### Incremental Architecture Evolution

The project evolves through small, compatibility-preserving phases. Existing routes, response envelopes, JSON persistence behavior, and service contracts are protected while the architecture matures.

## Features

### API Features

- Client management through Cockpit and compatibility routes.
- Task management with create, list, retrieve, update, and delete operations.
- Workflow and execution service architecture.
- Versioned `/v1` API adapter layer.
- Handler-backed compatibility endpoints for existing client and task flows.
- Service-layer boundaries for task, execution, monetization, and repository dependencies.
- Protocol-based repository abstraction over JSON-backed storage.

### Operational Features

- `GET /health` for lightweight process liveness.
- `GET /health/ready` for readiness checks.
- `GET /metrics` for JSON operational metrics.
- `X-Request-ID` request correlation.
- Inbound request ID reuse when valid.
- UUID request ID generation when missing or invalid.
- Response header propagation for request IDs.
- Centralized exception handling for structured JSON errors.
- Structured observability logs.

### Current API Surface

Runtime and operational endpoints:

```http
GET /
GET /health
GET /health/ready
GET /metrics
```

Cockpit endpoints:

```http
POST /cockpit/create-client
GET /cockpit/client/{client_id}
GET /cockpit/clients/search
POST /cockpit/test-pipeline
```

Task endpoints:

```http
GET /v1/tasks
POST /v1/tasks
GET /v1/tasks/{task_id}
PATCH /v1/tasks/{task_id}
DELETE /v1/tasks/{task_id}
```

Client compatibility and versioned endpoints:

```http
GET /clients
POST /clients
GET /v1/clients
POST /v1/clients
```

### Structured Error Format

Centralized exception responses use a consistent JSON shape:

```json
{
  "error": true,
  "type": "ValidationError",
  "message": "Example error message",
  "request_id": "request-id",
  "timestamp": "2026-07-20T00:00:00Z"
}
```

## Testing

The project currently has 137+ automated tests passing.

Coverage includes:

- FastAPI runtime construction;
- route contract stability;
- API adapter behavior;
- service contracts;
- repository contracts;
- persistence abstraction;
- typed task boundary models;
- request correlation middleware;
- centralized exception response format;
- readiness and metrics endpoints;
- observability behavior;
- client, task, workflow, integration, execution, monetization, and Cockpit modules.

Run the test suite:

```bash
.venv/bin/python -m unittest discover tests
```

Run a backend compile check:

```bash
.venv/bin/python -m compileall bbi_os
```

## Running the Project

Start the FastAPI backend from the repository root:

```bash
uvicorn bbi_os.app:app --reload
```

The canonical ASGI entry point is:

```text
bbi_os.app:app
```

Open the interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

## Tech Stack

Backend:

- Python 3.12
- FastAPI
- Pydantic
- Uvicorn
- JSON file persistence

Testing and engineering:

- Python `unittest`
- `compileall`
- Git
- Architecture documentation
- Architecture decision records

Frontend prototype:

- React
- Vite

## Repository Structure

```text
bbi_os/
|-- api/
|-- client_execution/
|-- client_monetization/
|-- client_onboarding/
|-- client_pipeline/
|-- cockpit/
|-- core/error_system/
|-- generator/
|-- integrations/
|-- task_management/
|-- workflows/
|-- app.py
|-- observability.py
|-- operational.py
|-- persistence.py
|-- settings.py

tests/
docs/
cockpit-ui/
```

## Roadmap

### Phase 3: Operational Maturity

Phase 3 focuses on making the backend easier to run, inspect, debug, and operate:

- request correlation;
- centralized exception handling;
- readiness checks;
- metrics endpoint;
- operational documentation;
- regression validation around runtime behavior.

### Phase 4: Production Persistence

Phase 4 is planned to introduce production persistence behind the existing repository contracts:

- PostgreSQL integration;
- SQLAlchemy repository implementations;
- Alembic migrations;
- runtime persistence selection;
- JSON-to-database migration strategy.

### Phase 5: Production Hardening

Phase 5 is planned to harden the system for deployment-oriented workflows:

- authentication and authorization;
- deployment configuration;
- Docker support;
- CI/CD workflow;
- expanded monitoring and tracing;
- production readiness review.

## Project Status

BBIOS OS is an actively developed backend engineering portfolio project.

Implemented:

- FastAPI runtime entry point;
- layered route, handler, service, and repository organization;
- versioned API adapter layer;
- service and repository contracts;
- JSON-backed repository implementations;
- request correlation middleware;
- centralized structured error handling;
- health, readiness, and metrics endpoints;
- automated regression coverage.

Planned, not yet implemented:

- PostgreSQL persistence;
- SQLAlchemy;
- Alembic migrations;
- Docker;
- CI/CD;
- deployment configuration;
- production authentication and authorization.

## Engineering Value

BBIOS OS demonstrates backend engineering skills that are directly relevant to production teams:

- designing layered FastAPI systems;
- preserving compatibility while improving architecture;
- separating business logic from framework and persistence concerns;
- defining stable contracts between services and repositories;
- adding operational readiness without rewriting business logic;
- validating architecture with automated tests;
- documenting architectural decisions and future work clearly.
