const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok || !body || body.status === "failure") {
    const message = body?.data?.error?.message || `Request failed (${response.status})`;
    throw new Error(message);
  }
  return body.data ?? {};
}

export const cockpitApi = {
  overview: () => request("/v1/cockpit/system-overview"),
  usage: () => request("/v1/cockpit/usage"),
  billing: () => request("/v1/cockpit/billing-summary"),
  executions: () => request("/v1/cockpit/executions"),
  client: (clientId) => request(`/v1/cockpit/client/${encodeURIComponent(clientId)}`),
  clients: () => request("/clients"),
  createClient: (client) => request("/clients", {
    method: "POST",
    body: JSON.stringify(client),
  }),
};
