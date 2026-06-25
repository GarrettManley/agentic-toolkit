import { motion } from "motion/react";
import { useApi } from "../hooks/useApi";
import type {
  MachineProfile,
  RecommendationData,
  AnalyticsTile,
} from "../types/api";
import { LoadingPanel } from "../components/LoadingPanel";
import { ErrorPanel } from "../components/ErrorPanel";
import { SignalBadge } from "../components/SignalBadge";
import { ConfidenceBar } from "../components/ConfidenceBar";
import { usd, ratio } from "../format";

const staggerChild = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0 },
};

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07 } },
};

export function Overview() {
  const profile = useApi<MachineProfile>("/api/profile");
  const reco = useApi<RecommendationData>("/api/recommendation");
  const analytics = useApi<AnalyticsTile[]>("/api/analytics");

  return (
    <motion.div
      className="stack-lg"
      variants={container}
      initial="hidden"
      animate="show"
      aria-live="polite"
      aria-label="Overview panel loading"
    >
      {/* ── HERO: VRAM Ceiling ─────────────────────────────────────────── */}
      <motion.div variants={staggerChild}>
        <div
          className="vram-alert"
          role="region"
          aria-label="VRAM constraint alert"
        >
          <p className="vram-alert-label">
            <span aria-hidden="true">⚠ </span>Active constraint · GPU VRAM
            ceiling
          </p>
          <div
            className="row"
            style={{ alignItems: "flex-end", gap: "0.75rem" }}
          >
            <span className="vram-alert-value" aria-label="8 gigabytes VRAM">
              8<span style={{ fontSize: "1.5rem" }}>GB</span>
            </span>
            <div className="stack-sm" style={{ paddingBottom: "0.25rem" }}>
              {profile.status === "ok" && (
                <p className="vram-alert-sub">
                  {profile.data.gpu.model} — limits 1440p fidelity and local LLM
                  inference batch size
                </p>
              )}
              <p
                className="vram-alert-sub"
                style={{ color: "var(--text-muted)" }}
              >
                Primary upgrade target: more VRAM unblocks both goals
                simultaneously
              </p>
            </div>
          </div>
        </div>
      </motion.div>

      {/* ── MACHINE PROFILE ────────────────────────────────────────────── */}
      <motion.div variants={staggerChild}>
        {profile.status === "loading" && (
          <LoadingPanel label="Loading machine profile" rows={5} />
        )}
        {profile.status === "error" && (
          <ErrorPanel message={profile.message} title="Profile unavailable" />
        )}
        {profile.status === "ok" && (
          <div
            className="panel"
            role="region"
            aria-labelledby="profile-heading"
          >
            <div className="panel-header">
              <span
                className="status-led active"
                role="img"
                aria-label="System online"
              />
              <span className="panel-label">System identity</span>
              <h2 className="panel-title" id="profile-heading">
                Machine Profile
              </h2>
            </div>
            <div className="panel-body">
              <div className="grid-4" style={{ gap: "1.5rem" }}>
                <SpecGroup
                  label="CPU"
                  specs={[
                    { field: "Model", value: profile.data.cpu.model },
                    { field: "Socket", value: profile.data.cpu.socket },
                    {
                      field: "Cores / Threads",
                      value: `${profile.data.cpu.cores}c / ${profile.data.cpu.threads}t`,
                    },
                  ]}
                />
                <SpecGroup
                  label="Motherboard"
                  specs={[
                    {
                      field: "Board",
                      value: `${profile.data.motherboard.manufacturer} ${profile.data.motherboard.model}`,
                    },
                    {
                      field: "Chipset",
                      value: profile.data.motherboard.chipset,
                    },
                    {
                      field: "RAM type",
                      value: `${profile.data.motherboard.ram_type} · ${profile.data.motherboard.ram_slots} slots`,
                    },
                  ]}
                />
                <SpecGroup
                  label="RAM"
                  specs={[
                    {
                      field: "Total",
                      value: `${profile.data.ram.total_gb} GB`,
                    },
                    { field: "Type", value: profile.data.ram.type },
                    {
                      field: "Speed",
                      value: `${profile.data.ram.speed_mts} MT/s`,
                    },
                    { field: "Modules", value: `${profile.data.ram.modules}x` },
                  ]}
                />
                <SpecGroup
                  label="GPU"
                  specs={[
                    { field: "Model", value: profile.data.gpu.model },
                    {
                      field: "VRAM",
                      value: `${profile.data.gpu.vram_gb} GB`,
                      highlight: true,
                    },
                  ]}
                />
              </div>
              <hr className="rule" style={{ margin: "1rem 0 0.75rem" }} />
              <div className="row-between">
                <div className="stack-sm">
                  <span className="panel-label">Primary goal</span>
                  <span
                    style={{
                      fontFamily: "var(--font-body)",
                      fontSize: "0.875rem",
                      color: "var(--text-primary)",
                    }}
                  >
                    {profile.data.goals.primary}
                  </span>
                </div>
                <div
                  className="row"
                  style={{
                    gap: "0.4rem",
                    flexWrap: "wrap",
                    justifyContent: "flex-end",
                  }}
                >
                  {profile.data.goals.priorities.map((p) => (
                    <span key={p} className="chip">
                      {p.replace(/_/g, " ")}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </motion.div>

      {/* ── TOP UPGRADE PATHS ──────────────────────────────────────────── */}
      <motion.div variants={staggerChild}>
        {reco.status === "loading" && (
          <LoadingPanel label="Loading upgrade recommendations" rows={6} />
        )}
        {reco.status === "error" && (
          <ErrorPanel
            message={reco.message}
            title="Recommendations unavailable"
          />
        )}
        {reco.status === "ok" && (
          <div className="panel" role="region" aria-labelledby="reco-heading">
            <div className="panel-header">
              <span
                className="status-led amber"
                role="img"
                aria-label="Active"
              />
              <span className="panel-label">Ranked upgrade analysis</span>
              <h2 className="panel-title" id="reco-heading">
                Top Upgrade Paths
              </h2>
            </div>
            <div className="panel-body stack">
              {reco.data.ranked_options.slice(0, 3).map((opt) => (
                <div
                  key={opt.rank}
                  className="highlight-box"
                  role="article"
                  aria-label={`Rank ${opt.rank}: ${opt.component.make} ${opt.component.model}`}
                >
                  <div
                    className="row-between"
                    style={{ marginBottom: "0.5rem" }}
                  >
                    <div className="row">
                      <div className="rank-badge rank-1">#{opt.rank}</div>
                      <div className="stack-sm" style={{ gap: "0.15rem" }}>
                        <span
                          style={{
                            fontFamily: "var(--font-display)",
                            fontSize: "1.1rem",
                            letterSpacing: "0.06em",
                            color: "var(--text-primary)",
                          }}
                        >
                          {opt.component.make} {opt.component.model}
                        </span>
                        <span className="chip">
                          {opt.category.replace(/_/g, " ")}
                        </span>
                      </div>
                    </div>
                    <div className="row">
                      <SignalBadge signal={opt.forecast.recommendation} />
                      <SignalBadge signal={opt.compatibility.verdict} />
                    </div>
                  </div>
                  <div
                    className="row-between"
                    style={{ flexWrap: "wrap", gap: "0.75rem" }}
                  >
                    <p
                      style={{
                        fontFamily: "var(--font-body)",
                        fontSize: "0.8125rem",
                        color: "var(--text-primary)",
                        maxWidth: "60ch",
                      }}
                    >
                      {opt.rationale}
                    </p>
                    <div
                      className="stack-sm"
                      style={{ textAlign: "right", flexShrink: 0 }}
                    >
                      <span
                        style={{
                          fontFamily: "var(--font-display)",
                          fontSize: "1.5rem",
                          color: "var(--amber)",
                        }}
                      >
                        {usd(opt.price.current_usd)}
                      </span>
                      <span className="readout-unit">
                        value/$ {ratio(opt.value_per_dollar)}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </motion.div>

      {/* ── SKU SIGNAL TILES ───────────────────────────────────────────── */}
      <motion.div variants={staggerChild}>
        {analytics.status === "loading" && (
          <LoadingPanel label="Loading price signals" rows={3} />
        )}
        {analytics.status === "error" && (
          <ErrorPanel
            message={analytics.message}
            title="Analytics unavailable"
          />
        )}
        {analytics.status === "ok" && analytics.data.length > 0 && (
          <div role="region" aria-labelledby="signals-heading">
            <h2
              className="panel-label"
              id="signals-heading"
              style={{ marginBottom: "0.75rem", color: "var(--text-muted)" }}
            >
              Price signals
            </h2>
            <div className="grid-2">
              {analytics.data.map((tile) => (
                <SignalTile key={tile.sku_id} tile={tile} />
              ))}
            </div>
          </div>
        )}
      </motion.div>

      {/* ── WHOLE MACHINE PATHS ────────────────────────────────────────── */}
      {reco.status === "ok" && reco.data.whole_machine_paths.length > 0 && (
        <motion.div variants={staggerChild}>
          <div className="panel" role="region" aria-labelledby="bundle-heading">
            <div className="panel-header">
              <span className="panel-label">Bundle options</span>
              <h2 className="panel-title" id="bundle-heading">
                Whole-Machine Paths
              </h2>
            </div>
            <div className="panel-body grid-2">
              {reco.data.whole_machine_paths.map((path) => (
                <div key={path.name} className="path-card">
                  <p
                    style={{
                      fontFamily: "var(--font-display)",
                      fontSize: "1rem",
                      letterSpacing: "0.06em",
                      marginBottom: "0.5rem",
                    }}
                  >
                    {path.name}
                  </p>
                  <div
                    className="row-between"
                    style={{ marginBottom: "0.4rem" }}
                  >
                    <span className="readout-unit">total</span>
                    <span
                      style={{
                        fontFamily: "var(--font-display)",
                        fontSize: "1.25rem",
                        color: "var(--amber)",
                      }}
                    >
                      {usd(path.total_usd)}
                    </span>
                  </div>
                  <div
                    className="row-between"
                    style={{ marginBottom: "0.5rem" }}
                  >
                    <span className="readout-unit">combined value/$</span>
                    <span className="readout" style={{ fontSize: "0.75rem" }}>
                      {ratio(path.combined_value_per_dollar)}
                    </span>
                  </div>
                  <p
                    style={{
                      fontFamily: "var(--font-body)",
                      fontSize: "0.75rem",
                      color: "var(--text-secondary)",
                    }}
                  >
                    {path.notes}
                  </p>
                  <div
                    className="row"
                    style={{
                      flexWrap: "wrap",
                      gap: "0.3rem",
                      marginTop: "0.5rem",
                    }}
                  >
                    {path.components.map((c) => (
                      <span key={c} className="chip">
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      )}

      {/* Verification summary footer */}
      {reco.status === "ok" && (
        <motion.div variants={staggerChild}>
          <VerificationSummaryRow summary={reco.data.verification_summary} />
        </motion.div>
      )}
    </motion.div>
  );
}

/* ── Sub-components ─────────────────────────────────────────────────────── */

function SpecGroup({
  label,
  specs,
}: {
  label: string;
  specs: Array<{ field: string; value: string; highlight?: boolean }>;
}) {
  return (
    <div>
      <p className="panel-label" style={{ marginBottom: "0.4rem" }}>
        {label}
      </p>
      {specs.map(({ field, value, highlight }) => (
        <div key={field} className="spec-row">
          <span className="spec-field">{field}</span>
          <span
            className="spec-value"
            style={
              highlight ? { color: "var(--red)", fontWeight: 700 } : undefined
            }
          >
            {value}
          </span>
        </div>
      ))}
    </div>
  );
}

function SignalTile({ tile }: { tile: AnalyticsTile }) {
  const pct = tile.pct_above_low;

  return (
    <article
      className="panel"
      aria-label={`${tile.sku_id}: ${tile.signal} — $${tile.current_price}`}
      style={{ padding: 0 }}
    >
      <div className="panel-body" style={{ padding: "1rem" }}>
        <div className="row-between" style={{ marginBottom: "0.6rem" }}>
          <p
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "0.6875rem",
              color: "var(--text-secondary)",
              letterSpacing: "0.06em",
            }}
          >
            {tile.sku_id}
          </p>
          <SignalBadge signal={tile.signal} />
        </div>
        <div
          className="row-between"
          style={{ alignItems: "flex-end", marginBottom: "0.6rem" }}
        >
          <span
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "2rem",
              color: "var(--amber)",
              lineHeight: 1,
            }}
          >
            {usd(tile.current_price)}
          </span>
          <div className="stack-sm" style={{ textAlign: "right" }}>
            <span className="readout-unit">confidence</span>
            <span className="readout" style={{ fontSize: "0.75rem" }}>
              {Math.round(tile.confidence * 100)}%
            </span>
          </div>
        </div>
        <ConfidenceBar
          value={tile.confidence}
          label={`Signal confidence: ${Math.round(tile.confidence * 100)}%`}
        />
        <p
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.6875rem",
            color: "var(--text-muted)",
            marginTop: "0.5rem",
          }}
        >
          {pct >= 0
            ? `${pct.toFixed(1)}% above all-time low`
            : `${Math.abs(pct).toFixed(1)}% below all-time low`}
        </p>
      </div>
    </article>
  );
}

function VerificationSummaryRow({
  summary,
}: {
  summary: RecommendationData["verification_summary"];
}) {
  return (
    <div className="panel" role="region" aria-label="Verification summary">
      <div className="panel-body">
        <div className="row-between" style={{ flexWrap: "wrap", gap: "1rem" }}>
          <span className="panel-label">Evidence verification</span>
          <div className="row" style={{ gap: "1.5rem" }}>
            <Stat label="Claims" value={summary.claims_total} />
            <Stat
              label="Passed"
              value={summary.claims_passed}
              color="var(--green)"
            />
            <Stat
              label="Demoted"
              value={summary.claims_demoted}
              color="var(--yellow)"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color?: string;
}) {
  return (
    <div className="stack-sm" style={{ textAlign: "center" }}>
      <span
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "1.5rem",
          color: color ?? "var(--amber)",
        }}
      >
        {value}
      </span>
      <span className="readout-unit">{label}</span>
    </div>
  );
}
