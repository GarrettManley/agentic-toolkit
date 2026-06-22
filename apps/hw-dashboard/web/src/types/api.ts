// ─── Profile ─────────────────────────────────────────────────────────────────

export interface CpuProfile {
  model: string;
  socket: string;
  cores: number;
  threads: number;
}

export interface MotherboardProfile {
  manufacturer: string;
  model: string;
  chipset: string;
  ram_type: string;
  ram_slots: number;
}

export interface RamProfile {
  total_gb: number;
  type: string;
  speed_mts: number;
  modules: number;
}

export interface GpuProfile {
  model: string;
  vram_gb: number;
}

export interface StorageItem {
  model: string;
  capacity_gb: number;
  media: string;
}

export interface Goals {
  primary: string;
  priorities: string[];
}

export interface MachineProfile {
  profile_id: string;
  os: string;
  cpu: CpuProfile;
  motherboard: MotherboardProfile;
  ram: RamProfile;
  gpu: GpuProfile;
  storage: StorageItem[];
  goals: Goals;
}

// ─── Recommendation ──────────────────────────────────────────────────────────

export interface Citation {
  url: string;
  tier: string;
  claim: string;
}

export interface Spec {
  field: string;
  value: string | number;
  unit?: string;
  status: string;
  citation: Citation;
}

export type CompatibilityVerdict =
  | "compatible"
  | "conditional"
  | "incompatible";

export interface CompatibilityCheck {
  dimension: string;
  pass: boolean | null;
  detail: string;
  citation?: Citation;
}

export interface Compatibility {
  verdict: CompatibilityVerdict;
  checks: CompatibilityCheck[];
}

export interface PriceInfo {
  current_usd: number;
  currency: string;
  citation: Citation;
}

export interface Forecast {
  recommendation: "buy" | "wait" | "hold";
  narrative: string;
  confidence: number;
  target_window: string;
}

export interface Component {
  make: string;
  model: string;
  id: string;
}

export interface RankedOption {
  rank: number;
  category: string;
  component: Component;
  specs: Spec[];
  compatibility: Compatibility;
  price: PriceInfo;
  forecast: Forecast;
  value_per_dollar: number;
  rationale: string;
  evidence: string[];
}

export interface WholeMachinePath {
  name: string;
  components: string[];
  total_usd: number;
  combined_value_per_dollar: number;
  notes: string;
}

export interface ExcludedItem {
  component: string;
  reason: string;
}

export interface VerificationSummary {
  claims_total: number;
  claims_passed: number;
  claims_demoted: number;
  votes_per_claim: Record<string, number>;
}

export interface RecommendationData {
  ranked_options: RankedOption[];
  whole_machine_paths: WholeMachinePath[];
  excluded: ExcludedItem[];
  verification_summary: VerificationSummary;
}

// ─── Analytics ───────────────────────────────────────────────────────────────

export type BuySignal = "buy_now" | "watch" | "wait";

export interface AnalyticsTile {
  sku_id: string;
  component_id: string;
  current_price: number;
  signal: BuySignal;
  confidence: number;
  pct_above_low: number;
}

export interface HistoricalData {
  all_time_low: number;
  all_time_low_date: string;
  all_time_high: number;
  pct_above_low: number;
  percentile_rank: number;
}

export interface RollingData {
  [key: string]: number | string;
}

export interface TrendData {
  usd_per_day: number;
  direction: string;
  holt_forecast_7d: number;
}

export interface EventData {
  nearest_event: string;
  days_until: number;
}

export interface PriceRecommendation {
  signal: BuySignal;
  confidence: number;
  confidence_label: string;
  rationale: string[];
}

export interface SkuDetail {
  sku_id: string;
  history_days: number;
  seed_days: number;
  current: { price: number; currency: string };
  historical: HistoricalData;
  rolling: RollingData;
  trend: TrendData;
  events: EventData;
  recommendation: PriceRecommendation;
  caveats: string[];
}

export interface PricePoint {
  capture_date: string;
  price: number;
  currency: string;
  retailer: string;
  source: string;
}

// ─── Components ──────────────────────────────────────────────────────────────

export interface ComponentRecord {
  id: string;
  make: string;
  model: string;
  category: string;
  [key: string]: unknown;
}
