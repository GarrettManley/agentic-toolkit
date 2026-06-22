interface Props {
  rows?: number;
  label?: string;
}

export function LoadingPanel({ rows = 4, label = "Loading data…" }: Props) {
  return (
    <div className="panel" role="status" aria-label={label} aria-live="polite">
      <div className="panel-body stack-sm">
        {Array.from({ length: rows }).map((_, i) => (
          <div
            key={i}
            className="skeleton"
            style={{ height: "1.25rem", width: `${70 + (i % 3) * 10}%` }}
            aria-hidden="true"
          />
        ))}
      </div>
    </div>
  );
}
