import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { useApi } from "../hooks/useApi";
import type {
  RecommendationData,
  RankedOption,
  CompatibilityCheck,
} from "../types/api";
import { LoadingPanel } from "../components/LoadingPanel";
import { ErrorPanel } from "../components/ErrorPanel";
import { SignalBadge } from "../components/SignalBadge";
import { DisclosureSection } from "../components/DisclosureSection";
import { usd, ratio } from "../format";

const ALL = "__all__";

function getCategories(options: RankedOption[]): string[] {
  const cats = Array.from(new Set(options.map((o) => o.category)));
  return cats;
}

export function ComponentExplorer() {
  const reco = useApi<RecommendationData>("/api/recommendation");
  const [activeCategory, setActiveCategory] = useState<string>(ALL);

  if (reco.status === "loading")
    return <LoadingPanel label="Loading component explorer" rows={8} />;
  if (reco.status === "error")
    return <ErrorPanel message={reco.message} title="Components unavailable" />;
  if (reco.status !== "ok") return null;

  const { ranked_options } = reco.data;
  const categories = getCategories(ranked_options);

  const filtered =
    activeCategory === ALL
      ? ranked_options
      : ranked_options.filter((o) => o.category === activeCategory);

  return (
    <div className="stack-lg" role="region" aria-label="Component explorer">
      <div className="row-between" style={{ flexWrap: "wrap", gap: "0.75rem" }}>
        <h2
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "1.5rem",
            letterSpacing: "0.08em",
          }}
        >
          Component Explorer
        </h2>
        <div
          className="filter-bar"
          role="group"
          aria-label="Filter by category"
        >
          <button
            className={`filter-btn ${activeCategory === ALL ? "active" : ""}`}
            onClick={() => setActiveCategory(ALL)}
            aria-pressed={activeCategory === ALL}
          >
            All ({ranked_options.length})
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              className={`filter-btn ${activeCategory === cat ? "active" : ""}`}
              onClick={() => setActiveCategory(cat)}
              aria-pressed={activeCategory === cat}
            >
              {cat.replace(/_/g, " ")}
            </button>
          ))}
        </div>
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={activeCategory}
          className="stack"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.18 }}
        >
          {filtered.map((opt) => (
            <ComponentCard key={opt.rank} opt={opt} />
          ))}
          {filtered.length === 0 && (
            <div className="state-container">
              <span className="state-icon" aria-hidden="true">
                ◎
              </span>
              <p className="state-title">No components</p>
            </div>
          )}
        </motion.div>
      </AnimatePresence>

      {/* Excluded items */}
      {reco.data.excluded.length > 0 && (
        <div className="panel">
          <div className="panel-header">
            <span className="panel-label">Excluded from ranking</span>
          </div>
          <div className="panel-body">
            <table className="data-table" aria-label="Excluded components">
              <thead>
                <tr>
                  <th scope="col">Component</th>
                  <th scope="col">Reason</th>
                </tr>
              </thead>
              <tbody>
                {reco.data.excluded.map((ex, i) => (
                  <tr key={i}>
                    <td>{ex.component}</td>
                    <td style={{ color: "var(--text-muted)" }}>{ex.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Component Card ─────────────────────────────────────────────────────── */

function ComponentCard({ opt }: { opt: RankedOption }) {
  return (
    <article
      className="panel"
      aria-label={`${opt.component.make} ${opt.component.model}, rank ${opt.rank}`}
    >
      <div className="panel-body" style={{ padding: "1rem" }}>
        {/* Header */}
        <div
          className="row-between"
          style={{ marginBottom: "0.75rem", flexWrap: "wrap", gap: "0.5rem" }}
        >
          <div className="row">
            <div className="rank-badge">#{opt.rank}</div>
            <div>
              <p
                style={{
                  fontFamily: "var(--font-display)",
                  fontSize: "1.15rem",
                  letterSpacing: "0.06em",
                }}
              >
                {opt.component.make} {opt.component.model}
              </p>
              <p className="readout-unit">{opt.category.replace(/_/g, " ")}</p>
            </div>
          </div>
          <div className="row" style={{ gap: "0.4rem", flexWrap: "wrap" }}>
            <SignalBadge signal={opt.compatibility.verdict} />
            <SignalBadge signal={opt.forecast.recommendation} />
          </div>
        </div>

        {/* Price + value */}
        <div
          className="row"
          style={{ gap: "2rem", marginBottom: "0.75rem", flexWrap: "wrap" }}
        >
          <div>
            <span className="readout-unit">Current price</span>
            <p
              style={{
                fontFamily: "var(--font-display)",
                fontSize: "1.75rem",
                color: "var(--amber)",
                lineHeight: 1,
              }}
            >
              {usd(opt.price.current_usd)}
              <span className="readout-unit" style={{ marginLeft: "0.3em" }}>
                {opt.price.currency}
              </span>
            </p>
          </div>
          <div>
            <span className="readout-unit">Value / dollar</span>
            <p
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "1.25rem",
                color: "var(--text-primary)",
                lineHeight: 1.2,
              }}
            >
              {ratio(opt.value_per_dollar)}
            </p>
          </div>
          <div style={{ flex: 1, minWidth: "200px" }}>
            <span className="readout-unit">Forecast</span>
            <p
              style={{
                fontFamily: "var(--font-body)",
                fontSize: "0.8125rem",
                color: "var(--text-secondary)",
                marginTop: "0.15rem",
              }}
            >
              {opt.forecast.narrative}
            </p>
            <p className="readout-unit" style={{ marginTop: "0.2rem" }}>
              Target: {opt.forecast.target_window} · Confidence:{" "}
              {Math.round(opt.forecast.confidence * 100)}%
            </p>
          </div>
        </div>

        {/* Specs table */}
        <DisclosureSection trigger="Specs">
          <div className="stack-sm" style={{ marginBottom: "0.75rem" }}>
            {opt.specs.map((spec) => (
              <div key={spec.field} className="spec-row">
                <span className="spec-field">{spec.field}</span>
                <div className="row" style={{ gap: "0.4rem" }}>
                  <span className="spec-value">
                    {String(spec.value)}
                    {spec.unit && (
                      <span className="spec-unit">{spec.unit}</span>
                    )}
                  </span>
                  <span
                    className={`chip ${spec.status === "pass" ? "" : "warn"}`}
                    style={
                      spec.status === "pass"
                        ? {
                            color: "var(--green)",
                            borderColor: "var(--green-dim)",
                          }
                        : {}
                    }
                    aria-label={`Status: ${spec.status}`}
                  >
                    {spec.status === "pass" ? "✓" : spec.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
          {/* Accessible data table for SR */}
          <table
            className="sr-only"
            aria-label={`${opt.component.model} specs`}
          >
            <thead>
              <tr>
                <th>Field</th>
                <th>Value</th>
                <th>Unit</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {opt.specs.map((spec) => (
                <tr key={spec.field}>
                  <td>{spec.field}</td>
                  <td>{String(spec.value)}</td>
                  <td>{spec.unit ?? ""}</td>
                  <td>{spec.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </DisclosureSection>

        <hr className="rule" />

        {/* Compatibility checks */}
        <DisclosureSection trigger="Compatibility checks">
          <div className="stack-sm">
            {opt.compatibility.checks.map((check, i) => (
              <CompatibilityRow key={i} check={check} />
            ))}
          </div>
        </DisclosureSection>

        {/* Rationale */}
        {opt.rationale && (
          <>
            <hr className="rule" />
            <p
              style={{
                fontFamily: "var(--font-body)",
                fontSize: "0.8125rem",
                color: "var(--text-secondary)",
              }}
            >
              {opt.rationale}
            </p>
          </>
        )}
      </div>
    </article>
  );
}

function CompatibilityRow({ check }: { check: CompatibilityCheck }) {
  const icon = check.pass === true ? "✓" : check.pass === false ? "✗" : "?";
  const cls =
    check.pass === true
      ? "compatible"
      : check.pass === false
        ? "incompatible"
        : "watch";

  return (
    <div className="row" style={{ gap: "0.6rem", alignItems: "flex-start" }}>
      <span
        className={`signal-badge ${cls}`}
        aria-label={`${check.dimension}: ${check.pass === true ? "pass" : check.pass === false ? "fail" : "unknown"}`}
      >
        <span aria-hidden="true">{icon}</span>
        <span>{check.dimension}</span>
      </span>
      <p
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "0.6875rem",
          color: "var(--text-muted)",
        }}
      >
        {check.detail}
      </p>
    </div>
  );
}
