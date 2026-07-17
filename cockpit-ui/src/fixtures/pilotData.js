const requestId = "pilot-request-alpha-001";
const executionId = "pilot-execution-alpha-001";
const workflowInstanceId = "pilot-workflow-instance-alpha-001";
const clientId = "alpha-test-client";

const lifecycleLogs = [
  {
    timestamp: "2026-07-03T13:00:00Z",
    level: "INFO",
    event: "client_execution_state_changed",
    request_id: requestId,
    user_id: "pilot-operator",
    role: "admin",
    message: "Client execution entered running state",
    metadata: {
      client_id: clientId,
      execution_id: executionId,
      workflow_instance_id: workflowInstanceId,
      previous_state: "PENDING",
      execution_state: "RUNNING",
      status: "success",
    },
  },
  {
    timestamp: "2026-07-03T13:00:01Z",
    level: "INFO",
    event: "workflow_step_completed",
    request_id: requestId,
    user_id: "pilot-operator",
    role: "admin",
    message: "Client validation completed",
    metadata: {
      client_id: clientId,
      execution_id: executionId,
      workflow_instance_id: workflowInstanceId,
      step_id: "validate-client",
      execution_status: "completed",
      status: "success",
    },
  },
  {
    timestamp: "2026-07-03T13:00:02Z",
    level: "INFO",
    event: "client_execution_completed",
    request_id: requestId,
    user_id: "pilot-operator",
    role: "admin",
    message: "Client execution completed",
    metadata: {
      client_id: clientId,
      execution_id: executionId,
      workflow_instance_id: workflowInstanceId,
      execution_state: "COMPLETED",
      status: "success",
    },
  },
  {
    timestamp: "2026-07-03T13:00:03Z",
    level: "INFO",
    event: "client_usage_recorded",
    request_id: requestId,
    user_id: "pilot-operator",
    role: "admin",
    message: "Client usage recorded",
    metadata: {
      client_id: clientId,
      execution_id: executionId,
      workflow_instance_id: workflowInstanceId,
      usage_event_type: "workflow_execution",
      usage_units: 4,
      status: "success",
    },
  },
];

const execution = {
  execution_id: executionId,
  client_id: clientId,
  execution_type: "one_time",
  workflow_id: "pilot-onboarding-workflow-v1",
  workflow_instance_id: workflowInstanceId,
  state: "COMPLETED",
  created_at: "2026-07-03T13:00:00Z",
  updated_at: "2026-07-03T13:00:02Z",
  transitions: [
    { state: "PENDING", timestamp: "2026-07-03T12:59:59Z" },
    { state: "RUNNING", timestamp: "2026-07-03T13:00:00Z" },
    { state: "COMPLETED", timestamp: "2026-07-03T13:00:02Z" },
  ],
  step_history: [
    {
      step_id: "validate-client",
      step_name: "Validate Alpha Test Client",
      status: "completed",
      started_at: "2026-07-03T13:00:00Z",
      ended_at: "2026-07-03T13:00:01Z",
    },
    {
      step_id: "record-usage",
      step_name: "Record execution usage",
      status: "completed",
      started_at: "2026-07-03T13:00:01Z",
      ended_at: "2026-07-03T13:00:02Z",
    },
  ],
  connector_calls: [],
  rollback_actions: [],
  output: { result: "Pilot lifecycle completed" },
};

const usage = {
  client_id: clientId,
  plan: "pro",
  event_count: 1,
  total_usage_units: 4,
  estimated_cost: 0.32,
  usage_breakdown: { workflows: 4, connectors: 0, onboarding: 0 },
};

export const pilotData = {
  clients: [
    {
      id: clientId,
      name: "Alpha Test Client",
      plan: "Pro",
      created_at: "2026-07-03T12:55:00Z",
    },
  ],
  overview: {
    active_clients: 1,
    running_workflows: 0,
    execution_states: { COMPLETED: 1 },
    system_health: {
      status: "healthy",
      workflow_success_rate: 1,
      connector_failure_rate: 0,
      running_executions: 0,
      queued_executions: 0,
    },
    recent_errors: [],
    connector_activity: [],
  },
  usage: {
    clients: [usage],
    plan_breakdown: { basic: 0, pro: 1, enterprise: 0, custom: 0 },
    execution_volume: 4,
    connector_usage: 0,
  },
  billing: {
    clients: [
      {
        client_id: clientId,
        total_usage_units: 4,
        estimated_cost: 0.32,
        usage_breakdown: { workflows: 4, connectors: 0, onboarding: 0 },
      },
    ],
    total_usage_units: 4,
    estimated_cost: 0.32,
  },
  executions: { executions: [execution] },
  clientDetails: {
    [clientId]: {
      client: {
        entity_id: clientId,
        entity_type: "client",
        created_at: "2026-07-03T12:55:00Z",
        updated_at: "2026-07-03T13:00:03Z",
        metadata: { client_name: "Alpha Test Client" },
      },
      status: "active",
      executions: [execution],
      active_workflows: [],
      usage,
      billing: {
        client_id: clientId,
        total_usage_units: 4,
        estimated_cost: 0.32,
        usage_breakdown: { workflows: 4, connectors: 0, onboarding: 0 },
      },
      logs: lifecycleLogs,
    },
  },
};
