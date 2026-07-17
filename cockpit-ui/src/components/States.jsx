export function LoadingState() {
  return (
    <div className="state-panel" role="status">
      <span className="loader" />
      <p>Loading cockpit data…</p>
    </div>
  );
}

export function EmptyState({ message = "No data available" }) {
  return (
    <div className="state-panel compact">
      <p>{message}</p>
    </div>
  );
}

export function StatusBadge({ value }) {
  const normalized = String(value || "unknown").toLowerCase();
  return <span className={`badge badge-${normalized.replaceAll("_", "-")}`}>{value || "Unknown"}</span>;
}
