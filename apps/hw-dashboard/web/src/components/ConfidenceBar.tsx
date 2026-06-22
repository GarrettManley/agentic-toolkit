interface Props {
  value: number; // 0..1
  label?: string;
}

export function ConfidenceBar({ value, label }: Props) {
  const pct = Math.round(value * 100);
  const desc = label ?? `Confidence: ${pct}%`;

  return (
    <div style={{ width: "100%" }}>
      <div
        className="confidence-bar-track"
        role="meter"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={desc}
        title={desc}
      >
        <div className="confidence-bar-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
