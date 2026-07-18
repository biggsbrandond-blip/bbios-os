# BBIOS OS

BBIOS OS is a modular business-operations platform built with Python, FastAPI, and React.

The project explores how backend services, client operations, workflow execution, task management, integrations, monetization, observability, and an administrative Cockpit interface can be organized within a layered software architecture.

BBIOS OS began as an internal operating-system concept for Biggs Bold Ink and now serves as my primary backend engineering portfolio project.

---

## Project Status

BBIOS OS is an actively developed portfolio and learning project.

The current implementation demonstrates modular backend architecture, API routing, service-layer separation, frontend integration, automated testing, and prototype business workflows.

It is not presented as a production-ready commercial platform.

---

## Current Capabilities

- Client onboarding and management
- UUID-based client identification
- Client retrieval and search
- Client pipeline handling
- Workflow and execution services
- Task-management services
- Authentication foundations
- Integration management
- Monetization and usage concepts
- Execution logging and observability
- Template-driven system generation
- Administrative Cockpit interface
- Automated tests across core system modules

---

## Architecture

```text
User or Client
      |
      v
React Cockpit UI
      |
      v
FastAPI API Layer
      |
      v
Router Layer
      |
      v
Service and Domain Layers
      |
      +---- Client Onboarding
      +---- Client Pipeline
      +---- Client Execution
      +---- Client Monetization
      +---- Task Management
      +---- Workflows
      +---- Integrations
      +---- Templates
      +---- Observability
      |
      v
Prototype Repository and Data Layer
```

### Router Layer

The router layer:

- receives HTTP requests;
- validates and routes request data;
- calls the appropriate service;
- returns structured API responses;
- avoids holding core business logic.

### Service and Domain Layers

The service and domain layers:

- contain business rules;
- coordinate client and workflow operations;
- manage execution behavior;
- organize reusable application logic;
- separate business concerns from HTTP handling.

### Repository and Data Layer

The current prototype uses repository and in-memory data concepts while the project continues toward persistent database integration.

---

## Repository Structure

```text
bbios-os/
|
|-- bbi_os/
|   |-- client_execution/
|   |-- client_monetization/
|   |-- client_onboarding/
|   |-- client_pipeline/
|   |-- cockpit/
|   |-- generator/
|   |-- integrations/
|   |-- task_management/
|   |-- templates/
|   |-- workflows/
|   |-- auth.py
|   |-- domain.py
|   |-- entity_repository.py
|   |-- entity_routing.py
|   |-- observability.py
|   |-- response_contract.py
|
|-- cockpit-ui/
|   |-- src/
|   |-- package.json
|   |-- vite.config.js
|   |-- .env.example
|
|-- generated_system/
|
|-- tests/
|
|-- README.md
```

---

## Cockpit UI

The Cockpit UI is a standalone React frontend for the BBIOS OS Cockpit APIs.

Current interface areas include:

- Overview
- Clients
- Client details
- Executions
- Execution details
- Monetization
- Logs
- Log details

The frontend uses read-only API requests and includes safe empty states for unavailable or empty responses.

---

## Example API Endpoints

### Create Client

```http
POST /cockpit/create-client
```

### Retrieve Client

```http
GET /cockpit/client/{client_id}
```

### Search Clients

```http
GET /cockpit/clients/search
```

### Test Pipeline

```http
POST /cockpit/test-pipeline
```

Additional versioned Cockpit endpoints are used by the React frontend.

---

## Example Client Object

```json
{
  "client_id": "uuid",
  "client_name": "Example Client",
  "plan": "premium",
  "created_at": "timestamp"
}
```

---

## Technology Stack

### Backend

- Python
- FastAPI
- Pydantic
- Uvicorn

### Frontend

- JavaScript
- React
- Vite

### Testing and Development

- Pytest
- Git
- GitHub
- REST APIs
- Swagger / OpenAPI documentation

---

## Run the Backend

From the repository root, run:

```bash
uvicorn bbi_os.cockpit.api:app --reload
```

Then open the interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

---

## Run the Cockpit UI

Move into the frontend directory:

```bash
cd cockpit-ui
```

Install the frontend dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

By default, the Vite development server proxies `/v1` requests to:

```text
http://127.0.0.1:8000
```

For a separately hosted backend, configure:

```text
VITE_API_BASE_URL=https://your-bbios-api.example.com
```

---

## Run the Tests

From the repository root, run:

```bash
pytest
```

The test suite includes coverage for areas such as:

- authentication;
- client management;
- client pipelines;
- Cockpit services;
- domain behavior;
- execution services;
- integrations;
- monetization;
- observability;
- onboarding;
- task APIs.

---

## Engineering Concepts Demonstrated

This project demonstrates:

- modular backend design;
- REST API development;
- router and service separation;
- reusable domain organization;
- request and response contracts;
- authentication foundations;
- workflow-oriented system design;
- frontend and backend integration;
- automated testing;
- technical documentation;
- Git-based version control;
- incremental software development.

---

## Development Roadmap

Planned areas of continued development include:

- PostgreSQL database integration;
- persistent data storage;
- expanded authentication and authorization;
- stronger API validation;
- additional automated testing;
- Docker support;
- continuous integration;
- deployment configuration;
- improved frontend interaction;
- production-readiness review.

---

## Purpose

BBIOS OS was created to strengthen practical backend engineering skills through the development of a real, evolving system.

The project combines my background in writing, documentation, education, and structured communication with software engineering.

The central goal is the same across both disciplines:

> Turn complexity into clear, usable systems.

---

## Author

**Biggs**

Founder, Biggs Bold Ink  
U.S. Army Veteran  
Backend Engineering Portfolio

**Write Bold. Leave Legacy.**

**With Honor and Purpose.**
