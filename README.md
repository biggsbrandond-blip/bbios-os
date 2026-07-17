# BBIOS OS — Backend System Architecture

## Overview

BBIOS OS is a modular backend system built with FastAPI that demonstrates structured API design, service-layer architecture, and scalable backend engineering principles.

This project simulates a lightweight client management system with routing, validation, search, and execution logging.

---

## Core Features

- Create client with timestamp tracking
- Unique client ID generation (UUID-based)
- Retrieve client by ID
- Search clients by parameters
- Execution logging system
- Test pipeline endpoint for system verification
- Clean separation of Router and Service layers

---

## Architecture

Client Request → Router Layer → Service Layer → In-Memory Data Store → Response

### System Layers

**Router Layer**
- Handles HTTP requests
- Routes data to services
- No business logic

**Service Layer**
- Core business logic
- Client creation & retrieval
- Search + system operations

**Data Layer**
- In-memory storage (prototype persistence)

---

## API Endpoints

### Create Client
POST /cockpit/create-client

### Get Client
GET /cockpit/client/{client_id}

### Search Clients
GET /cockpit/clients/search

### Test System
POST /cockpit/test-pipeline

---

## Example Client Object

{
  "client_id": "uuid",
  "client_name": "John Doe",
  "plan": "premium",
  "created_at": "timestamp"
}

---

## Tech Stack

- Python 3
- FastAPI
- Pydantic
- Uvicorn
- Git / GitHub

---

## How to Run

uvicorn bbi_os.cockpit.api:app --reload

Open:
http://127.0.0.1:8000/docs

---

## Purpose

This project demonstrates:

- Backend API design
- Service-layer architecture
- Clean code separation
- RESTful API structure
- GitHub portfolio readiness

---

## Author

Brandon Biggs  
BBIOS OS — Biggs Bold Ink Engineering System
