import type { BuySignal, CompatibilityVerdict } from "../types/api";

type SignalValue = BuySignal | CompatibilityVerdict | "buy" | "hold";

const SIGNAL_META: Record<string, { icon: string; label: string }> = {
  buy_now: { icon: "▲", label: "BUY NOW" },
  buy: { icon: "▲", label: "BUY" },
  watch: { icon: "◉", label: "WATCH" },
  hold: { icon: "◉", label: "HOLD" },
  wait: { icon: "▽", label: "WAIT" },
  compatible: { icon: "✓", label: "COMPATIBLE" },
  conditional: { icon: "⚠", label: "CONDITIONAL" },
  incompatible: { icon: "✗", label: "INCOMPATIBLE" },
};

interface Props {
  signal: SignalValue;
  compact?: boolean;
}

export function SignalBadge({ signal, compact = false }: Props) {
  const meta = SIGNAL_META[signal] ?? {
    icon: "?",
    label: signal.toUpperCase(),
  };

  return (
    <span className={`signal-badge ${signal}`} aria-label={meta.label}>
      <span aria-hidden="true">{meta.icon}</span>
      {!compact && <span>{meta.label}</span>}
    </span>
  );
}
