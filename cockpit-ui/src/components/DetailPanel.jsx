export default function DetailPanel({ title, subtitle, onClose, children }) {
  return (
    <div className="panel-backdrop" role="presentation" onMouseDown={onClose}>
      <aside className="detail-panel" role="dialog" aria-modal="true" aria-label={title} onMouseDown={(event) => event.stopPropagation()}>
        <header>
          <div>
            <p className="eyebrow">Record detail</p>
            <h2>{title}</h2>
            {subtitle ? <p>{subtitle}</p> : null}
          </div>
          <button className="close-button" type="button" onClick={onClose} aria-label="Close detail panel">×</button>
        </header>
        <div className="detail-content">{children}</div>
      </aside>
    </div>
  );
}
