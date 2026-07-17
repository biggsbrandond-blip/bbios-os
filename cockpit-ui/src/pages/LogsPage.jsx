import { useState } from "react";
import DetailPanel from "../components/DetailPanel";
import PageHeader from "../components/PageHeader";
import { EmptyState, LoadingState, StatusBadge } from "../components/States";
import { eventStatus, formatTimestamp } from "../lib/format";

export default function LogsPage({ logs, loading }) {
  const [selected, setSelected] = useState(null);
  if (loading) return <LoadingState />;
  return (
    <>
      <PageHeader eyebrow="Sprint 002" title="Logs" description="Structured operational events with request-level correlation." />
      <section className="content-card table-card">
        {logs.length ? <div className="table-scroll"><table><thead><tr><th>Timestamp</th><th>Request ID</th><th>Event type</th><th>Status</th></tr></thead><tbody>{logs.map((event, index) => <tr key={`${event.request_id || "log"}-${index}`} onClick={() => setSelected(event)} tabIndex="0"><td>{formatTimestamp(event.timestamp)}</td><td className="mono">{event.request_id || "Not available"}</td><td>{event.event || event.metadata?.event_type || "Unknown event"}</td><td><StatusBadge value={eventStatus(event)} /></td></tr>)}</tbody></table></div> : <EmptyState />}
      </section>
      {selected ? <DetailPanel title={selected.event || "Log detail"} subtitle={formatTimestamp(selected.timestamp)} onClose={() => setSelected(null)}><div className="correlation-box"><span>Request ID</span><strong className="mono">{selected.request_id || "Not available"}</strong></div><dl className="detail-list"><div><dt>Status</dt><dd><StatusBadge value={eventStatus(selected)} /></dd></div><div><dt>Message</dt><dd>{selected.message || "No message available"}</dd></div><div><dt>User</dt><dd>{selected.user_id || "Not available"}</dd></div><div><dt>Role</dt><dd>{selected.role || "Not available"}</dd></div></dl><h3>Metadata</h3><pre>{JSON.stringify(selected.metadata || {}, null, 2)}</pre></DetailPanel> : null}
    </>
  );
}
