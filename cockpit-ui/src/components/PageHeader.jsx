export default function PageHeader({ eyebrow, title, description, onRefresh, action }) {
  return (
    <header className="page-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="page-description">{description}</p>
      </div>
      {action ? (
        <button className="primary-page-button" onClick={action.onClick} type="button">
          {action.label}
        </button>
      ) : onRefresh ? (
        <button className="secondary-button" onClick={onRefresh} type="button">
          Refresh data
        </button>
      ) : null}
    </header>
  );
}
