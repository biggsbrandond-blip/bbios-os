export default function MetricCard({ label, value, detail, tone = "default" }) {
  return (
    <article className={`metric-card tone-${tone}`}>
      <p>{label}</p>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}
