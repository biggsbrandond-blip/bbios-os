import MetricCard from "../components/MetricCard";
import PageHeader from "../components/PageHeader";
import { EmptyState, LoadingState } from "../components/States";
import { asArray, formatMoney } from "../lib/format";

const plans = ["basic", "pro", "enterprise", "custom"];

export default function MonetizationPage({ data, loading }) {
  if (loading) return <LoadingState />;
  const clients = asArray(data.usage?.clients);
  return (
    <>
      <PageHeader eyebrow="COS-003" title="Monetization" description="Logical usage and revenue intelligence by client plan." />
      <section className="metric-grid monetization-metrics">
        <MetricCard label="Total revenue" value={formatMoney(data.billing?.estimated_cost)} detail="Logical estimated revenue" tone="gold" />
        <MetricCard label="Usage units" value={data.billing?.total_usage_units ?? 0} detail="Across all clients" />
        <MetricCard label="Workflow volume" value={data.usage?.execution_volume ?? 0} detail="Metered workflow units" tone="blue" />
        <MetricCard label="Connector usage" value={data.usage?.connector_usage ?? 0} detail="Metered connector units" tone="green" />
      </section>
      <section className="plan-grid">
        {plans.map((plan) => <article className="plan-card" key={plan}><span className={`plan-accent ${plan}`} /><p>{plan}</p><strong>{data.usage?.plan_breakdown?.[plan] ?? 0}</strong><small>clients</small></article>)}
      </section>
      <section className="content-card table-card">
        <div className="section-heading"><div><p className="eyebrow">Account usage</p><h2>Usage per client</h2></div></div>
        {clients.length ? <div className="table-scroll"><table><thead><tr><th>Client ID</th><th>Plan</th><th>Usage units</th><th>Estimated revenue</th></tr></thead><tbody>{clients.map((client) => <tr key={client.client_id}><td className="mono">{client.client_id}</td><td className="capitalize">{client.plan || "basic"}</td><td>{client.total_usage_units ?? 0}</td><td>{formatMoney(client.estimated_cost)}</td></tr>)}</tbody></table></div> : <EmptyState />}
      </section>
    </>
  );
}
