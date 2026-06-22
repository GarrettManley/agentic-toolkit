import { useState } from "react";
import { motion } from "motion/react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { useApi } from "../hooks/useApi";
import type { AnalyticsTile, SkuDetail, PricePoint } from "../types/api";
import { LoadingPanel } from "../components/LoadingPanel";
import { ErrorPanel } from "../components/ErrorPanel";
import { SignalBadge } from "../components/SignalBadge";
import { ConfidenceBar } from "../components/ConfidenceBar";

const KNOWN_SKUS = ["rtx-4060-ti-16gb-asus", "ddr5-64gb-6000-cl30-gskill"];

export function PriceForecast() {
  const analytics = useApi<AnalyticsTile[]>("/api/analytics");
  const [activeSku, setActiveSku] = useState<string>(KNOWN_SKUS[0]);

  const skus =
    analytics.status === "ok"
      ? analytics.data.map((t) => t.sku_id)
      : KNOWN_SKUS;

  return (
    <div className="stack-lg" role="region" aria-label="Price and forecast">
      <h2
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "1.5rem",
          letterSpacing: "0.08em",
        }}
      >
        Price &amp; Forecast
      </h2>

      {/* SKU selector tabs */}
      <div
        role="tablist"
        aria-label="Select SKU"
        style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}
      >
        {skus.map((sku) => (
          <button
            key={sku}
            role="tab"
            aria-selected={activeSku === sku}
            aria-controls={`panel-${sku}`}
            id={`tab-${sku}`}
            className={`filter-btn ${activeSku === sku ? "active" : ""}`}
            onClick={() => setActiveSku(sku)}
          >
            {sku}
          </button>
        ))}
      </div>

      <motion.div
        key={activeSku}
        id={`panel-${activeSku}`}
        role="tabpanel"
        aria-labelledby={`tab-${activeSku}`}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
      >
        <SkuPanel skuId={activeSku} />
      </motion.div>
    </div>
  );
}

/* ─── Per-SKU panel ──────────────────────────────────────────────────────── */

function SkuPanel({ skuId }: { skuId: string }) {
  const detail = useApi<SkuDetail>(`/api/analytics/${skuId}`);
  const series = useApi<PricePoint[]>(`/api/skus/${skuId}/series`);

  if (detail.status === "loading" || series.status === "loading") {
    return <LoadingPanel label={`Loading data for ${skuId}`} rows={6} />;
  }
  if (detail.status === "error" || series.status === "error") {
    return (
      <ErrorPanel
        title="SKU data unavailable"
        message={
          detail.status === "error"
            ? detail.message
            : series.status === "error"
              ? series.message
              : undefined
        }
      />
    );
  }
  if (detail.status !== "ok" || series.status !== "ok") return null;

  const det = detail.data;
  const pts = series.data;

  // Prepare chart data — merge series points
  const chartData = pts.map((pt) => ({
    date: pt.capture_date.slice(0, 10),
    price: pt.price,
    source: pt.source,
    retailer: pt.retailer,
    isSeed: pt.source === "seed",
  }));

  const atlDate = det.historical.all_time_low_date?.slice(0, 10) ?? null;
  const atlPrice = det.historical.all_time_low;

  return (
    <div className="stack">
      {/* Summary metrics */}
      <div className="grid-4" style={{ gap: "0.75rem" }}>
        <MetricTile
          label="Current price"
          value={`$${det.current.price.toFixed(0)}`}
          sub={det.current.currency}
          accent
        />
        <MetricTile
          label="All-time low"
          value={`$${atlPrice.toFixed(0)}`}
          sub={atlDate ?? ""}
          color="var(--green)"
        />
        <MetricTile
          label="% above ATL"
          value={`${det.historical.pct_above_low.toFixed(1)}%`}
          sub={`Pctl rank: ${det.historical.percentile_rank.toFixed(0)}`}
        />
        <MetricTile
          label="7-day forecast"
          value={`$${det.trend.holt_forecast_7d.toFixed(0)}`}
          sub={det.trend.direction}
        />
      </div>

      {/* Signal & confidence */}
      <div className="highlight-box">
        <div
          className="row-between"
          style={{ marginBottom: "0.5rem", flexWrap: "wrap", gap: "0.5rem" }}
        >
          <div className="row">
            <SignalBadge signal={det.recommendation.signal} />
            <span
              style={{
                fontFamily: "var(--font-body)",
                fontSize: "0.875rem",
                color: "var(--text-secondary)",
              }}
            >
              {det.recommendation.confidence_label}
            </span>
          </div>
          <span className="readout-unit">
            Confidence: {Math.round(det.recommendation.confidence * 100)}%
          </span>
        </div>
        <ConfidenceBar
          value={det.recommendation.confidence}
          label={`Buy signal confidence: ${Math.round(det.recommendation.confidence * 100)}%`}
        />
        {det.recommendation.rationale.length > 0 && (
          <ul
            style={{ marginTop: "0.5rem", paddingLeft: "1rem" }}
            aria-label="Signal rationale"
          >
            {det.recommendation.rationale.map((r, i) => (
              <li
                key={i}
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.6875rem",
                  color: "var(--text-secondary)",
                  marginBottom: "0.2rem",
                }}
              >
                {r}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Recharts time series */}
      {chartData.length > 0 ? (
        <div className="panel">
          <div className="panel-header">
            <span className="panel-label">Price history</span>
            <h3 className="panel-title">{skuId}</h3>
          </div>
          <div className="panel-body">
            <PriceChart
              data={chartData}
              atlDate={atlDate}
              atlPrice={atlPrice}
              skuId={skuId}
            />
            {/* Accessible data table */}
            <details style={{ marginTop: "1rem" }}>
              <summary
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.625rem",
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                }}
              >
                View data table (screen reader)
              </summary>
              <div style={{ overflowX: "auto", marginTop: "0.5rem" }}>
                <table
                  className="data-table"
                  aria-label={`Price history for ${skuId}`}
                >
                  <thead>
                    <tr>
                      <th scope="col">Date</th>
                      <th scope="col">Price (USD)</th>
                      <th scope="col">Retailer</th>
                      <th scope="col">Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pts.map((pt, i) => (
                      <tr key={i}>
                        <td>{pt.capture_date.slice(0, 10)}</td>
                        <td>${pt.price.toFixed(2)}</td>
                        <td>{pt.retailer}</td>
                        <td>{pt.source}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          </div>
        </div>
      ) : (
        <div className="panel">
          <div className="state-container">
            <span className="state-icon" aria-hidden="true">
              ◎
            </span>
            <p className="state-title">No price history</p>
            <p className="state-detail">
              Run the nightly collector to seed price data.
            </p>
          </div>
        </div>
      )}

      {/* Caveats */}
      {det.caveats.length > 0 && (
        <div className="panel">
          <div className="panel-header">
            <span className="status-led warn" role="img" aria-label="Warning" />
            <span className="panel-label">Caveats</span>
          </div>
          <div className="panel-body stack-sm">
            {det.caveats.map((c, i) => (
              <p
                key={i}
                style={{
                  fontFamily: "var(--font-body)",
                  fontSize: "0.8125rem",
                  color: "var(--text-secondary)",
                }}
              >
                <span
                  aria-hidden="true"
                  style={{ color: "var(--yellow)", marginRight: "0.4em" }}
                >
                  ⚠
                </span>
                {c}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Events */}
      {det.events.nearest_event && (
        <div
          className="panel"
          style={{
            background: "var(--bg-raised)",
            borderColor: "var(--border-amber)",
          }}
        >
          <div className="panel-body row-between">
            <div className="row">
              <span
                className="status-led amber blink"
                role="img"
                aria-label="Upcoming event"
              />
              <div>
                <span className="panel-label">Upcoming price event</span>
                <p
                  style={{
                    fontFamily: "var(--font-body)",
                    fontSize: "0.875rem",
                    color: "var(--text-primary)",
                  }}
                >
                  {det.events.nearest_event}
                </p>
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <span
                style={{
                  fontFamily: "var(--font-display)",
                  fontSize: "2rem",
                  color: "var(--amber)",
                }}
              >
                {det.events.days_until}
              </span>
              <span className="readout-unit" style={{ display: "block" }}>
                days away
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Price Chart ─────────────────────────────────────────────────────────── */

interface ChartPoint {
  date: string;
  price: number;
  source: string;
  retailer: string;
  isSeed: boolean;
}

function PriceChart({
  data,
  atlDate,
  atlPrice,
  skuId,
}: {
  data: ChartPoint[];
  atlDate: string | null;
  atlPrice: number;
  skuId: string;
}) {
  return (
    <div
      role="img"
      aria-label={`Price history chart for ${skuId}. Shows price over time. All-time low: $${atlPrice.toFixed(0)}${atlDate ? ` on ${atlDate}` : ""}.`}
    >
      <ResponsiveContainer width="100%" height={280}>
        <LineChart
          data={data}
          margin={{ top: 12, right: 20, bottom: 8, left: 0 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(255,255,255,0.05)"
            vertical={false}
          />
          <XAxis
            dataKey="date"
            tick={{
              fontFamily: "var(--font-mono)",
              fontSize: 10,
              fill: "var(--text-muted)",
            }}
            tickLine={false}
            axisLine={{ stroke: "var(--border)" }}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{
              fontFamily: "var(--font-mono)",
              fontSize: 10,
              fill: "var(--text-muted)",
            }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => `$${v}`}
            width={52}
          />
          <Tooltip content={<PriceTooltip />} />
          <Legend
            wrapperStyle={{
              fontFamily: "var(--font-mono)",
              fontSize: "0.625rem",
              letterSpacing: "0.1em",
              color: "var(--text-muted)",
            }}
          />

          {/* ATL reference line */}
          {atlPrice > 0 && (
            <ReferenceLine
              y={atlPrice}
              stroke="var(--green)"
              strokeDasharray="4 2"
              strokeOpacity={0.7}
              label={{
                value: `ATL $${atlPrice.toFixed(0)}`,
                position: "insideTopRight",
                fontFamily: "var(--font-mono)",
                fontSize: 10,
                fill: "var(--green)",
              }}
            />
          )}

          {/* Seed points — dimmed */}
          <Line
            name="Seed data"
            dataKey={(d: ChartPoint) => (d.isSeed ? d.price : undefined)}
            type="monotone"
            stroke="var(--text-muted)"
            strokeWidth={1}
            strokeDasharray="3 3"
            dot={{ r: 2, fill: "var(--text-muted)", stroke: "none" }}
            activeDot={false}
            connectNulls={false}
            legendType="plainline"
          />

          {/* First-party live points */}
          <Line
            name="Live price"
            dataKey={(d: ChartPoint) => (!d.isSeed ? d.price : undefined)}
            type="monotone"
            stroke="var(--amber)"
            strokeWidth={2}
            dot={{
              r: 3,
              fill: "var(--amber)",
              stroke: "var(--bg-panel)",
              strokeWidth: 1,
            }}
            activeDot={{
              r: 5,
              fill: "var(--amber)",
              stroke: "var(--bg-panel)",
              strokeWidth: 2,
            }}
            connectNulls={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function PriceTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value: number; payload: ChartPoint }>;
  label?: string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const pt = payload[0];

  return (
    <div className="chart-tooltip" role="tooltip">
      <p className="chart-tooltip-label">{label}</p>
      <p style={{ color: "var(--amber)" }}>${pt.value?.toFixed(2)}</p>
      {pt.payload.retailer && (
        <p style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>
          {pt.payload.retailer}
        </p>
      )}
      <p style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>
        {pt.payload.isSeed ? "seed" : "live"}
      </p>
    </div>
  );
}

/* ─── Metric tile ─────────────────────────────────────────────────────────── */

function MetricTile({
  label,
  value,
  sub,
  accent = false,
  color,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: boolean;
  color?: string;
}) {
  return (
    <div className="panel" style={{ padding: 0 }}>
      <div className="panel-body" style={{ padding: "0.75rem" }}>
        <span
          className="readout-unit"
          style={{ display: "block", marginBottom: "0.2rem" }}
        >
          {label}
        </span>
        <span
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "1.5rem",
            color: color ?? (accent ? "var(--amber)" : "var(--text-primary)"),
            lineHeight: 1,
          }}
        >
          {value}
        </span>
        {sub && (
          <span
            className="readout-unit"
            style={{ display: "block", marginTop: "0.15rem" }}
          >
            {sub}
          </span>
        )}
      </div>
    </div>
  );
}
