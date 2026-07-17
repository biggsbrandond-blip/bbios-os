import { useState } from "react";
import DetailPanel from "../components/DetailPanel";
import PageHeader from "../components/PageHeader";
import { EmptyState, LoadingState, StatusBadge } from "../components/States";
import { asArray, clientStatus, formatMoney, formatTimestamp, latestTimestamp } from "../lib/format";

const plans = ["Basic", "Pro", "Enterprise", "Custom"];

export default function ClientsPage({ data, loading, onCreate }) {
  const [selectedId, setSelectedId] = useState(null);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [plan, setPlan] = useState("Basic");
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (loading) return <LoadingState />;
  const clients = asArray(data.clients);
  const detail = selectedId ? data.clientDetails[selectedId] : null;

  const openCreate = () => {
    setName("");
    setPlan("Basic");
    setFormError("");
    setCreating(true);
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!name.trim()) {
      setFormError("Client name is required");
      return;
    }
    setSubmitting(true);
    setFormError("");
    try {
      await onCreate({ name: name.trim(), plan });
      setCreating(false);
    } catch (error) {
      setFormError(error?.message || "Unable to create client");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="COS-001"
        title="Clients"
        description="Client identity, operational status, and plan context."
        action={{ label: "Create Client", onClick: openCreate }}
      />
      <section className="content-card table-card">
        {clients.length ? (
          <div className="table-scroll"><table><thead><tr><th>Client name</th><th>Status</th><th>Plan type</th><th>Last activity</th></tr></thead>
          <tbody>{clients.map((client) => {
            const clientDetail = data.clientDetails[client.id];
            return <tr key={client.id} onClick={() => setSelectedId(client.id)} tabIndex="0">
              <td><strong>{client.name || "Unnamed client"}</strong><small>{client.id}</small></td>
              <td><StatusBadge value={clientStatus(clientDetail)} /></td><td className="capitalize">{client.plan || "Basic"}</td>
              <td>{formatTimestamp(latestTimestamp(clientDetail) || client.created_at)}</td></tr>;
          })}</tbody></table></div>
        ) : <EmptyState />}
      </section>

      {selectedId ? (
        <DetailPanel title={detail?.client?.metadata?.name || detail?.client?.metadata?.client_name || selectedId} subtitle={selectedId} onClose={() => setSelectedId(null)}>
          {detail ? <><div className="detail-stats"><div><span>Status</span><StatusBadge value={clientStatus(detail)} /></div><div><span>Plan</span><strong>{detail.usage?.plan || "basic"}</strong></div><div><span>Usage</span><strong>{detail.usage?.total_usage_units ?? 0} units</strong></div><div><span>Revenue</span><strong>{formatMoney(detail.billing?.estimated_cost)}</strong></div></div>
          <h3>Recent executions</h3>{asArray(detail.executions).length ? <ul className="record-list">{asArray(detail.executions).slice(-6).reverse().map((item) => <li key={item.execution_id}><div><strong>{item.workflow_id || "Workflow"}</strong><small>{formatTimestamp(item.updated_at)}</small></div><StatusBadge value={item.state} /></li>)}</ul> : <EmptyState />}</> : <EmptyState />}
        </DetailPanel>
      ) : null}

      {creating ? (
        <DetailPanel title="Create Client" subtitle="Add a persistent client record" onClose={() => !submitting && setCreating(false)}>
          <form className="client-form" onSubmit={submit} noValidate>
            <label htmlFor="client-name">Client Name</label>
            <input
              id="client-name"
              name="client-name"
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Enter client name"
              autoFocus
              required
            />
            <label htmlFor="client-plan">Plan</label>
            <select id="client-plan" value={plan} onChange={(event) => setPlan(event.target.value)}>
              {plans.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
            {formError ? <p className="form-error" role="alert">{formError}</p> : null}
            <div className="form-actions">
              <button type="button" className="secondary-button" onClick={() => setCreating(false)} disabled={submitting}>Cancel</button>
              <button type="submit" className="primary-page-button" disabled={submitting}>{submitting ? "Creating…" : "Create Client"}</button>
            </div>
          </form>
        </DetailPanel>
      ) : null}
    </>
  );
}
