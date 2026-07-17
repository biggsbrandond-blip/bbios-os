const pages = ["Overview", "Clients", "Executions", "Monetization", "Logs"];

export default function Layout({ page, onNavigate, children }) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">B</span>
          <div>
            <strong>BBIOS</strong>
            <small>Operations cockpit</small>
          </div>
        </div>
        <nav aria-label="Cockpit navigation">
          {pages.map((item) => (
            <button
              className={page === item ? "nav-item active" : "nav-item"}
              key={item}
              onClick={() => onNavigate(item)}
              type="button"
            >
              <span className="nav-dot" />
              {item}
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="status-light" />
          Cockpit UI v1.0
        </div>
      </aside>
      <main className="main-panel">{children}</main>
    </div>
  );
}
