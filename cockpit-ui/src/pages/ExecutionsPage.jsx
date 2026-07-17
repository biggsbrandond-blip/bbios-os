import { useMemo, useState } from "react";
import DetailPanel from "../components/DetailPanel";
import PageHeader from "../components/PageHeader";
import { EmptyState, LoadingState, StatusBadge } from "../components/States";
import { asArray, eventStatus, formatTimestamp, progressFor } from "../lib/format";

export default function ExecutionsPage({ data, loading }) {
  const [selectedId, setSelectedId] = useState(null);
  const executions = asArray(data.executions?.executions);
  const selected = executions.find((item) => item.execution_id === selectedId);
  const detailLogs = useMemo(() => {
    if (!selected) return [];
    const clientLogs = asArray(data.clientDetails[selected.client_id]?.logs);
    return clientLogs.filter((event) => {
      const metadata = event?.metadata || {};
      return metadata.execution_id === selected.execution_id
        || (selected.workflow_instance_id && metadata.workflow_instance_id === selected.workflow_instance_id);
    });
  }, [data.clientDetails, selected]);
  if (loading) return <LoadingState />;

  return (
    <>
      <PageHeader eyebrow="COS-002" title="Executions" description="Execution state and workflow progress, refreshed every seven seconds." />
      <section className="content-card table-card">
        {executions.length ? (
          <div className="table-scroll"><table><thead><tr><th>Execution ID</th><th>Client ID</th><th>State</th><th>Progress</th></tr></thead>
          <tbody>{executions.slice().reverse().map((execution) => {
            const progress = progressFor(execution.state);
            return <tr key={execution.execution_id} onClick={() => setSelectedId(execution.execution_id)} tabIndex="0">
              <td><strong className="mono">{execution.execution_id}</strong></td><td className="mono">{execution.client_id || "Not available"}</td>
              <td><StatusBadge value={execution.state} /></td><td><div className="progress-label"><span>{progress}%</span><div className="progress-track"><span style={{ width: `${progress}%` }} /></div></div></td>
            </tr>;
          })}</tbody></table></div>
        ) : <EmptyState />}
      </section>
      {selected ? (
        <DetailPanel title="Execution detail" subtitle={selected.execution_id} onClose={() => setSelectedId(null)}>
          <div className="correlation-box"><span>Request ID correlation</span><strong className="mono">{detailLogs[0]?.request_id || selected.connector_calls?.[0]?.request_id || "Not available"}</strong></div>
          <h3>Execution timeline</h3>
          {asArray(selected.step_history).length ? <ol className="timeline">{asArray(selected.step_history).map((step, index) => <li key={step.step_id || index}><span className={`timeline-marker ${step.status || "pending"}`}>{index + 1}</span><div><strong>{step.step_name || step.step_id || `Step ${index + 1}`}</strong><small>{formatTimestamp(step.started_at)} · {step.status || "Unknown"}</small>{step.error ? <p className="error-text">{step.error}</p> : null}</div></li>)}</ol> : <EmptyState message="No step data available" />}
          <h3>Logs</h3>
          {detailLogs.length ? <ul className="plain-logs">{detailLogs.map((event, index) => <li key={`${event.request_id}-${index}`}><time>{formatTimestamp(event.timestamp)}</time><span>{event.event || "event"}</span><StatusBadge value={eventStatus(event)} /></li>)}</ul> : <EmptyState message="No correlated logs available" />}
        </DetailPanel>
      ) : null}
    </>
  );
}
