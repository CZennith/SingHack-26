/**
 * TypeScript interfaces for the Stress Test & RM Intelligence Workbench.
 * All types mirror the backend Pydantic models in stress_router.py.
 */

// ---------------------------------------------------------------------------
// Scenario configuration
// ---------------------------------------------------------------------------

export type NamedScenarioId =
  | 'hormuz-escalation'
  | 'hormuz-de-escalation'
  | 'tech-selloff'
  | 'rate-shock'
  | 'gold-consolidation';

export type AssetClass =
  | 'Equity'
  | 'Fixed Income'
  | 'Cash and Equivalents'
  | 'Alternatives'
  | 'Commodities'
  | 'Structured Products';

export interface ScenarioConfig {
  id: NamedScenarioId | 'custom';
  label: string;
  shocks: Partial<Record<AssetClass, number>>;
  sector_overrides?: Record<string, number>;
}

export const NAMED_SCENARIOS: Record<NamedScenarioId, ScenarioConfig> = {
  'hormuz-escalation': {
    id: 'hormuz-escalation',
    label: 'Strait of Hormuz Escalation',
    shocks: { Commodities: 40, Equity: -8, 'Fixed Income': 3, Alternatives: 15 },
    sector_overrides: { Airlines: -20, 'Information Technology': 0, Energy: 40 },
  },
  'hormuz-de-escalation': {
    id: 'hormuz-de-escalation',
    label: 'Hormuz Reopens / De-escalation',
    shocks: { Commodities: -25, Equity: 5, Alternatives: -8 },
    sector_overrides: { Airlines: 12, Energy: -25 },
  },
  'tech-selloff': {
    id: 'tech-selloff',
    label: 'Tech Sector Selloff',
    shocks: { Equity: -8 },
    sector_overrides: { 'Information Technology': -20 },
  },
  'rate-shock': {
    id: 'rate-shock',
    label: 'Rate Shock — Fed Hikes',
    shocks: { 'Fixed Income': -12, Equity: -8 },
    sector_overrides: {},
  },
  'gold-consolidation': {
    id: 'gold-consolidation',
    label: 'Gold Consolidation',
    shocks: { Alternatives: -15, Commodities: -15 },
    sector_overrides: {},
  },
};

// ---------------------------------------------------------------------------
// Macro shock results
// ---------------------------------------------------------------------------

export interface HoldingImpact {
  instrument_id: string;
  instrument_name: string;
  asset_class: string;
  look_through_applied: boolean;
  current_value_usd: number;
  shocked_value_usd: number;
  dollar_change_usd: number;
  advance_rate_pct: number;
  shocked_lending_value_usd: number;
}

export interface MacroShockResult {
  client_id: string;
  scenario_id: string;
  as_of: string;
  total_current_value_usd: number;
  total_shocked_value_usd: number;
  net_dollar_impact_usd: number;
  net_pct_change: number;
  top_impacted_holdings: HoldingImpact[];
}

// ---------------------------------------------------------------------------
// LTV stress results
// ---------------------------------------------------------------------------

export interface LTVFacilityRow {
  facility_id: string;
  facility_type: string;
  drawn_usd: number;
  current_ltv_pct: number;
  margin_call_ltv_pct: number;
  ltv_at_minus_10_pct: number | null;
  ltv_at_minus_20_pct: number | null;
  ltv_at_minus_30_pct: number | null;
  scenario_ltv_pct: number | null;
  headroom_at_minus_10_usd: number;
  headroom_at_minus_20_usd: number;
  headroom_at_minus_30_usd: number;
  scenario_headroom_usd: number | null;
}

export interface LTVStressResult {
  client_id: string;
  facilities: LTVFacilityRow[];
}

// ---------------------------------------------------------------------------
// Look-through concentration results
// ---------------------------------------------------------------------------

export interface ConcentrationRow {
  exposure_name: string;
  asset_class: string;
  sector: string;
  pre_look_through_pct: number;
  post_look_through_pct: number;
  mandate_limit_pct: number | null;
  status: 'BREACH' | 'ELEVATED' | 'OK' | 'NO_LIMIT';
}

export interface HiddenConcentration {
  exposure_name: string;
  pre_pct: number;
  post_pct: number;
  gap_pct: number;
  explanation: string;
}

export interface LookThroughResult {
  client_id: string;
  as_of: string;
  total_aum_usd: number;
  concentrations: ConcentrationRow[];
  hidden_concentration_discoveries: HiddenConcentration[];
}

// ---------------------------------------------------------------------------
// Liquidity coverage results
// ---------------------------------------------------------------------------

export interface SellToCoverItem {
  rank: number;
  instrument_name: string;
  current_value_usd: number;
  unrealised_pnl_usd: number;
  estimated_settle_days: number;
}

export interface LifeEventFlag {
  description: string;
  due_date: string;
  amount_usd: number;
  coverage_ratio: number;
  life_stage_note: string;
}

export interface LiquidityResult {
  client_id: string;
  as_of: string;
  total_60d_obligations_usd: number;
  tier1_liquid_value_usd: number;
  lcr: number | null;
  status: 'COVERED' | 'SHORTFALL';
  surplus_or_gap_usd: number;
  sell_to_cover: SellToCoverItem[];
  life_event_flags: LifeEventFlag[];
}

// ---------------------------------------------------------------------------
// RM recommendations
// ---------------------------------------------------------------------------

export interface RMRecommendation {
  action_verb: string;
  asset_class: string | null;
  holding_name: string | null;
  rationale: string;
  weight_change: number;
  approval_label: string;
  plain_language_summary: string;
  mandate_breach: boolean;
  breach_detail: string | null;
  alternative_action: string | null;
  projected_weight: number | null;
}

// ---------------------------------------------------------------------------
// Full stress run result
// ---------------------------------------------------------------------------

export interface StressRunResult {
  result_id: string;
  as_of: string;
  client_id: string;
  scenario: { id: string; label: string };
  macro_shock: MacroShockResult;
  ltv_stress: LTVStressResult;
  liquidity: LiquidityResult;
  narrative: string;
  recommendations: RMRecommendation[];
}

// ---------------------------------------------------------------------------
// Book-wide scenario
// ---------------------------------------------------------------------------

export interface BookScenarioClientRow {
  client_id: string;
  client_name: string;
  total_current_value_usd: number;
  total_shocked_value_usd: number;
  net_dollar_impact_usd: number;
  net_pct_change: number;
  ltv_breach: boolean;
  ltv_breach_facility_id: string | null;
  scenario_rank: number;
}

export interface BookScenarioResponse {
  scenario: { id: string; label: string };
  as_of: string;
  clients: BookScenarioClientRow[];
}

// ---------------------------------------------------------------------------
// Urgency / scoring
// ---------------------------------------------------------------------------

export interface UrgencyTrigger {
  code: string;
  points: number;
  label: string;
  evidence_summary: string;
  module_anchor: string;
}

// ---------------------------------------------------------------------------
// Audit trail
// ---------------------------------------------------------------------------

export interface AuditEntry {
  result_id: string;
  timestamp: string; // ISO-8601
  client_id: string;
  scenario_name: string;
  decision: 'reviewed' | 'actioned' | 'call_script_generated';
  note: string; // max 160 chars
}

// ---------------------------------------------------------------------------
// Request shapes for the service layer
// ---------------------------------------------------------------------------

export interface StressRunRequest {
  client_id: string;
  scenario: {
    scenario_id: string;
    shocks: Partial<Record<AssetClass, number>>;
    sector_overrides?: Record<string, number>;
  };
}

export interface BookScenarioRequest {
  scenario: {
    scenario_id: string;
    shocks: Partial<Record<AssetClass, number>>;
    sector_overrides?: Record<string, number>;
  };
}
