interface Props {
  message?: string;
  title?: string;
}

export function ErrorPanel({ message, title = "API Unavailable" }: Props) {
  return (
    <div className="panel" role="alert" aria-live="assertive">
      <div className="state-container">
        <span className="state-icon" aria-hidden="true">
          ⚠
        </span>
        <p className="state-title">{title}</p>
        {message && <p className="state-detail">{message}</p>}
        <p className="state-detail" style={{ color: "var(--text-muted)" }}>
          Start the API server:{" "}
          <code>uvicorn api.server:app --host 127.0.0.1 --port 8077</code>
        </p>
      </div>
    </div>
  );
}
