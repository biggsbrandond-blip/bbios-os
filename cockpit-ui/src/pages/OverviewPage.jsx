import MetricCard from "../components/MetricCard";
import { LoadingState, StatusBadge } from "../components/States";
import { formatMoney } from "../lib/format";

const quickStartSteps = [
  {
    number: "01",
    title: "Create a client",
    description: "Establish the client record and operating context.",
  },
  {
    number: "02",
    title: "Run an execution",
    description: "Launch a structured workflow for the client.",
  },
  {
    number: "03",
    title: "Review results",
    description: "Confirm outcomes, usage, and execution history.",
  },
];

export default function OverviewPage({ data, loading, onNavigate }) {
  if (loading) return <LoadingState />;

  const overview = data.overview;
  const totalClients = Array.isArray(data.clients)
    ? data.clients.length
    : (overview?.active_clients ?? 0);
  const hasActivity = Boolean(
    totalClients > 0
      || (overview?.running_workflows ?? 0) > 0
      || (data.billing?.total_usage_units ?? 0) > 0,
  );
  const status = overview?.system_health?.status === "healthy" ? "OK" : "No activity";

  return (
    <div className="overview-entry">
      <section className="overview-hero">
        <div className="hero-copy">
          <p className="eyebrow">Operational control center</p>
          <h1>Welcome to BBIOS Cockpit</h1>
          <p>
            Your operational control center for clients, executions, and business clarity.
          </p>
          <button className="primary-button" type="button" onClick={() => onNavigate("Clients")}>
            Start with clarity
          </button>
        </div>
        <div className="hero-system-mark" aria-hidden="true">
          <span>BB</span>
          <div><i /><i /><i /></div>
        </div>
      </section>

      <section className="quick-start-section" aria-labelledby="quick-start-title">
        <div className="overview-section-heading">
          <p className="eyebrow">Quick start</p>
          <h2 id="quick-start-title">A clear path from setup to result</h2>
        </div>
        <div className="quick-start-flow">
          {quickStartSteps.map((step, index) => (
            <article className="quick-start-step" key={step.number}>
              <div className="step-topline">
                <span>{step.number}</span>
                {index < quickStartSteps.length - 1 ? <i aria-hidden="true" /> : null}
              </div>
              <h3>{step.title}</h3>
              <p>{step.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="system-status-section" aria-labelledby="system-status-title">
        <div className="overview-section-heading status-heading">
          <div>
            <p className="eyebrow">Current position</p>
            <h2 id="system-status-title">System status</h2>
          </div>
          {hasActivity ? <StatusBadge value={status} /> : null}
        </div>
        {hasActivity ? (
          <div className="metric-grid overview-metrics">
            <MetricCard label="Total Clients" value={totalClients} detail="Persisted client records" />
            <MetricCard label="Active Executions" value={overview?.running_workflows ?? 0} detail="Running or waiting" tone="blue" />
            <MetricCard label="Revenue" value={formatMoney(data.billing?.estimated_cost)} detail="Logical estimated revenue" tone="gold" />
            <MetricCard label="System Status" value={status} detail="Current platform condition" tone="green" />
          </div>
        ) : (
          <div className="overview-empty-state">
            <span className="empty-state-mark" aria-hidden="true" />
            <p>No activity yet — start with your first client</p>
          </div>
        )}
      </section>

      <section className="recommended-action">
        <div>
          <p className="eyebrow">Recommended next step</p>
          <h2>Build the foundation for your first execution</h2>
          <p>Create your first client to begin generating system activity.</p>
        </div>
        <button className="secondary-action-button" type="button" onClick={() => onNavigate("Clients")}>
          Go to Clients
        </button>
      </section>

      <footer className="overview-insight">
        BBIOS operates as a clarity-first execution system. Every action begins with structure.
      </footer>
    </div>
  );
}
