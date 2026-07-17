export function asArray(value) {
  return Array.isArray(value) ? value : [];
}

export function formatMoney(value) {
  const amount = Number(value);
  return Number.isFinite(amount)
    ? new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(amount)
    : "$0.00";
}

export function formatTimestamp(value) {
  if (!value) return "Not available";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}

export function progressFor(state) {
  return {
    PENDING: 0,
    RUNNING: 50,
    WAITING_EXTERNAL: 65,
    COMPENSATING: 80,
    COMPLETED: 100,
    FAILED: 100,
  }[String(state || "").toUpperCase()] ?? 0;
}

export function latestTimestamp(client) {
  const values = [
    ...asArray(client?.executions).map((item) => item.updated_at),
    ...asArray(client?.logs).map((item) => item.timestamp),
  ].filter(Boolean);
  return values.sort().at(-1) || client?.client?.updated_at || "";
}

export function clientName(detail, clientId) {
  const metadata = detail?.client?.metadata || {};
  return metadata.client_name || metadata.name || clientId || "Unnamed client";
}

export function clientStatus(detail) {
  const states = asArray(detail?.executions).map((item) => item.state);
  if (states.includes("FAILED")) return "failed";
  if (states.some((state) => ["PENDING", "RUNNING", "WAITING_EXTERNAL"].includes(state))) {
    return "pending";
  }
  return detail?.status || "active";
}

export function eventStatus(event) {
  if (event?.level === "ERROR" || event?.metadata?.status === "failure") return "ERROR";
  return event?.metadata?.status || "OK";
}
