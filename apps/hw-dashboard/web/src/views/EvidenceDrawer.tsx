import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { useApi } from "../hooks/useApi";
import type {
  RecommendationData,
  Spec,
  CompatibilityCheck,
  Citation,
} from "../types/api";
import { LoadingPanel } from "../components/LoadingPanel";
import { ErrorPanel } from "../components/ErrorPanel";
import { DisclosureSection } from "../components/DisclosureSection";

export function EvidenceDrawer() {
  const reco = useApi<RecommendationData>("/api/recommendation");
  const [selected, setSelected] = useState<number | null>(null);

  if (reco.status === "loading")
    return <LoadingPanel label="Loading evidence" rows={6} />;
  if (reco.status === "error")
    return <ErrorPanel message={reco.message} title="Evidence unavailable" />;
  if (reco.status !== "ok") return null;

  const { ranked_options, verification_summary } = reco.data;

  const activeOpt =
    selected !== null
      ? (ranked_options.find((o) => o.rank === selected) ?? null)
      : null;

  return (
    <div className="stack-lg" role="region" aria-label="Evidence and citations">
      <div className="row-between" style={{ flexWrap: "wrap", gap: "0.75rem" }}>
        <div>
          <h2
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "1.5rem",
              letterSpacing: "0.08em",
            }}
          >
            Evidence Drawer
          </h2>
          <p
            style={{
              fontFamily: "var(--font-body)",
              fontSize: "0.8125rem",
              color: "var(--text-secondary)",
              marginTop: "0.2rem",
            }}
          >
            Every spec, price, and compatibility claim with its cited source and
            verification tier.
          </p>
        </div>
        <VerificationSummaryPanel summary={verification_summary} />
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "280px 1fr",
          gap: "1rem",
          alignItems: "start",
        }}
      >
        {/* Component list sidebar */}
        <nav aria-label="Select component for evidence">
          <ul className="stack-sm" style={{ listStyle: "none" }}>
            {ranked_options.map((opt) => (
              <li key={opt.rank}>
                <button
                  className={`panel ${selected === opt.rank ? "active-evidence-item" : ""}`}
                  onClick={() =>
                    setSelected(selected === opt.rank ? null : opt.rank)
                  }
                  aria-pressed={selected === opt.rank}
                  aria-label={`View evidence for rank ${opt.rank}: ${opt.component.make} ${opt.component.model}`}
                  style={{
                    width: "100%",
                    textAlign: "left",
                    cursor: "pointer",
                    padding: "0.75rem",
                    background:
                      selected === opt.rank
                        ? "var(--amber-glow)"
                        : "var(--bg-panel)",
                    borderColor:
                      selected === opt.rank
                        ? "var(--border-amber)"
                        : "var(--border)",
                    transition: "background 0.12s, border-color 0.12s",
                  }}
                >
                  <div className="row" style={{ gap: "0.5rem" }}>
                    <span
                      style={{
                        fontFamily: "var(--font-display)",
                        fontSize: "1rem",
                        color:
                          selected === opt.rank
                            ? "var(--amber)"
                            : "var(--text-muted)",
                      }}
                    >
                      #{opt.rank}
                    </span>
                    <div>
                      <p
                        style={{
                          fontFamily: "var(--font-body)",
                          fontSize: "0.8125rem",
                          color: "var(--text-primary)",
                          lineHeight: 1.3,
                        }}
                      >
                        {opt.component.make} {opt.component.model}
                      </p>
                      <p className="readout-unit">
                        {opt.category.replace(/_/g, " ")}
                      </p>
                    </div>
                  </div>
                  <p
                    className="readout-unit"
                    style={{ marginTop: "0.35rem", color: "var(--text-muted)" }}
                  >
                    {opt.evidence.length} evidence items · {opt.specs.length}{" "}
                    specs
                  </p>
                </button>
              </li>
            ))}
          </ul>
        </nav>

        {/* Evidence detail panel */}
        <AnimatePresence mode="wait">
          {activeOpt ? (
            <motion.div
              key={activeOpt.rank}
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -12 }}
              transition={{ duration: 0.18 }}
              className="stack"
              role="region"
              aria-label={`Evidence for ${activeOpt.component.model}`}
            >
              <div className="panel">
                <div className="panel-header">
                  <span className="panel-label">Citations for</span>
                  <h3 className="panel-title">
                    {activeOpt.component.make} {activeOpt.component.model}
                  </h3>
                </div>
                <div className="panel-body stack">
                  {/* Spec citations */}
                  <DisclosureSection
                    trigger={`Spec claims (${activeOpt.specs.length})`}
                    defaultOpen
                  >
                    <div className="stack-sm">
                      {activeOpt.specs.map((spec) => (
                        <SpecCitationRow key={spec.field} spec={spec} />
                      ))}
                    </div>
                  </DisclosureSection>

                  <hr className="rule" />

                  {/* Price citation */}
                  <DisclosureSection trigger="Price citation" defaultOpen>
                    <CitationBlock citation={activeOpt.price.citation} />
                  </DisclosureSection>

                  <hr className="rule" />

                  {/* Compatibility citations */}
                  {activeOpt.compatibility.checks.some((c) => c.citation) && (
                    <DisclosureSection trigger={`Compatibility citations`}>
                      <div className="stack-sm">
                        {activeOpt.compatibility.checks
                          .filter((c) => c.citation)
                          .map((check, i) => (
                            <CompatibilityCitationRow key={i} check={check} />
                          ))}
                      </div>
                    </DisclosureSection>
                  )}

                  {/* Evidence list */}
                  {activeOpt.evidence.length > 0 && (
                    <>
                      <hr className="rule" />
                      <DisclosureSection
                        trigger={`Evidence sources (${activeOpt.evidence.length})`}
                      >
                        <ul className="stack-sm" style={{ listStyle: "none" }}>
                          {activeOpt.evidence.map((ev, i) => (
                            <li key={i} className="citation-block">
                              {ev}
                            </li>
                          ))}
                        </ul>
                      </DisclosureSection>
                    </>
                  )}
                </div>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
            >
              <div className="panel">
                <div className="state-container">
                  <span className="state-icon" aria-hidden="true">
                    ◎
                  </span>
                  <p className="state-title">Select a component</p>
                  <p className="state-detail">
                    Choose a ranked option from the list to inspect its
                    citations and verification chain.
                  </p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

/* ─── Sub-components ─────────────────────────────────────────────────────── */

function SpecCitationRow({ spec }: { spec: Spec }) {
  return (
    <div
      style={{
        borderBottom: "1px solid rgba(255,255,255,0.04)",
        paddingBottom: "0.5rem",
      }}
    >
      <div className="row-between" style={{ marginBottom: "0.25rem" }}>
        <span className="spec-field">{spec.field}</span>
        <span className="spec-value">
          {String(spec.value)}
          {spec.unit ? ` ${spec.unit}` : ""}
        </span>
      </div>
      <CitationBlock citation={spec.citation} compact />
    </div>
  );
}

function CompatibilityCitationRow({ check }: { check: CompatibilityCheck }) {
  if (!check.citation) return null;
  return (
    <div
      style={{
        borderBottom: "1px solid rgba(255,255,255,0.04)",
        paddingBottom: "0.5rem",
      }}
    >
      <p className="spec-field" style={{ marginBottom: "0.25rem" }}>
        {check.dimension}: {check.detail}
      </p>
      <CitationBlock citation={check.citation} compact />
    </div>
  );
}

function CitationBlock({
  citation,
  compact = false,
}: {
  citation: Citation;
  compact?: boolean;
}) {
  return (
    <div className="citation-block">
      <div
        className="row"
        style={{ gap: "0.4rem", marginBottom: compact ? "0.15rem" : "0.3rem" }}
      >
        <span className="tier-badge">T{citation.tier}</span>
        <span style={{ color: "var(--text-secondary)", fontSize: "0.625rem" }}>
          {citation.claim}
        </span>
      </div>
      <a
        href={citation.url}
        target="_blank"
        rel="noopener noreferrer"
        aria-label={`Open source: ${citation.url}`}
        style={{ fontSize: "0.6rem" }}
      >
        {citation.url}
      </a>
    </div>
  );
}

function VerificationSummaryPanel({
  summary,
}: {
  summary: RecommendationData["verification_summary"];
}) {
  const passRate =
    summary.claims_total > 0
      ? ((summary.claims_passed / summary.claims_total) * 100).toFixed(0)
      : "—";

  return (
    <div
      className="panel"
      style={{ padding: 0 }}
      role="region"
      aria-label="Verification summary"
    >
      <div
        className="panel-body row"
        style={{ gap: "1.5rem", padding: "0.75rem 1rem" }}
      >
        <VerStat label="Total claims" value={summary.claims_total} />
        <VerStat
          label="Passed"
          value={summary.claims_passed}
          color="var(--green)"
        />
        <VerStat
          label="Demoted"
          value={summary.claims_demoted}
          color="var(--yellow)"
        />
        <VerStat label="Pass rate" value={`${passRate}%`} accent />
      </div>
    </div>
  );
}

function VerStat({
  label,
  value,
  color,
  accent,
}: {
  label: string;
  value: string | number;
  color?: string;
  accent?: boolean;
}) {
  return (
    <div className="stack-sm" style={{ textAlign: "center", gap: "0.1rem" }}>
      <span
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "1.25rem",
          color: color ?? (accent ? "var(--amber)" : "var(--text-primary)"),
        }}
      >
        {value}
      </span>
      <span className="readout-unit">{label}</span>
    </div>
  );
}
