# Cockpit UI v1.0

Standalone React frontend for the existing BBIOS OS Cockpit APIs.

## Pages

- Overview
- Clients and client detail
- Executions and execution detail
- Monetization
- Logs and log detail

Execution data is polled every seven seconds. Failed or empty API responses render safe empty states.

## External frontend environment

This source tree assumes Node.js is provided by the deployment environment.

```bash
npm install
npm run dev
```

The Vite development server proxies `/v1` to `http://127.0.0.1:8000`.
For a separately hosted backend, set:

```bash
VITE_API_BASE_URL=https://your-bbios-api.example.com
```

The application performs read-only `GET` requests against existing `/v1/cockpit/*` endpoints. It does not create or extend backend APIs.

## Pilot validation mode

The frontend includes one static, read-only lifecycle fixture for pilot review:

- Client: `Alpha Test Client`
- Plan: `pro`
- Linked completed execution with two timeline steps
- Four aggregated workflow usage units
- Correlated execution and monetization logs under one request ID

Enable it in the external frontend environment:

```bash
VITE_PILOT_MODE=true
```

Pilot mode performs no API writes and does not modify backend state. Setting it to `false`
restores normal read-only API consumption.
