import { ClientDossier, RiskSeverity } from '../types';
import { ApiClientSummary, ClientSnapshot } from './apiClient';

const ALLOCATION_COLORS = ['#2c6e6a', '#9e6b20', '#7a1c28', '#55534e', '#8c887f', '#b7a98d'];

function money(value: unknown): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) return 'Not available';
  return `USD ${value.toLocaleString('en-US', { maximumFractionDigits: 2 })}`;
}

function initials(name: string): string {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join('').toUpperCase();
}

function severity(profile: string | null): RiskSeverity | null {
  const value = profile?.toUpperCase();
  return value === 'CRITICAL' || value === 'HIGH' || value === 'MEDIUM' || value === 'LOW' ? value : null;
}

function valueNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

export function toClientDossier(summary: ApiClientSummary, snapshot?: ClientSnapshot, exposure?: Record<string, unknown>): ClientDossier {
  const firstPortfolio = snapshot?.portfolios?.[0];
  const portfolioSummaries = snapshot?.portfolio_summaries || [];
  const total = valueNumber((exposure?.client_total as Record<string, unknown> | undefined)?.market_value_usd) ?? summary.aum_usd_at_as_of;
  const allocationGroups = (exposure?.by_asset_class as Array<Record<string, unknown>> | undefined) || [];
  const allocation = allocationGroups.map((group, index) => ({
    label: String(group.key ?? 'Unclassified'),
    percentage: valueNumber(group.weight_pct) ?? 0,
    color: ALLOCATION_COLORS[index % ALLOCATION_COLORS.length],
  }));
  const holdings = [...(snapshot?.holdings || [])]
    .sort((a, b) => (valueNumber(b.market_value_usd) ?? 0) - (valueNumber(a.market_value_usd) ?? 0));
  const topHoldings = holdings.slice(0, 4).map((holding, index) => ({
    id: String(holding.instrument_id ?? `holding-${index}`),
    name: String(holding.instrument_name ?? holding.instrument_id ?? 'Unnamed instrument'),
    ticker: String(holding.instrument_id ?? '—'),
    sector: String(holding.sector ?? 'Unclassified'),
    value: money(valueNumber(holding.market_value_usd)),
    percentage: valueNumber(holding.weight_pct) ?? 0,
  }));
  const mandateNames = [...new Set(portfolioSummaries.map((item) => item.mandate_name).filter(Boolean).map(String))];
  const mandate = mandateNames.length === 1 ? mandateNames[0] : mandateNames.length > 1 ? 'Multiple mandates' : String(firstPortfolio?.mandate_name ?? 'Portfolio coverage');
  const asOf = snapshot?.snapshot_metadata.as_of_date || '';
  const ltv = summary.max_ltv_pct_at_as_of;
  return {
    id: summary.client_id,
    ref: summary.client_id,
    name: summary.client_name,
    initials: initials(summary.client_name),
    tier: summary.wealth_band || 'Not classified',
    mandate,
    aum: money(total),
    riskLevel: severity(summary.risk_profile),
    riskProfile: summary.risk_profile,
    headlineIssue: '',
    summary: '',
    tags: [],
    suggestedNextStep: '',
    about: {
      bio: '',
      age: summary.age ?? 0,
      occupation: '',
      clientSince: summary.client_since ? Number(summary.client_since.slice(0, 4)) : 0,
    },
    portfolio: {
      totalValue: money(total),
      totalValueSubtext: asOf ? `Direct USD holdings as of ${asOf}` : 'Selected snapshot',
      cashLiquidity: 'Not calculated',
      cashLiquidityPercent: '—',
      cashLiquiditySubtext: 'Liquidity analysis is not implemented',
      borrowingUtilisation: ltv === null ? 'Not calculated' : `${ltv}% LTV`,
      borrowingLtvPercent: ltv,
      borrowingStatus: ltv === null ? 'NOT_CALCULATED' : 'AVAILABLE',
      allocation,
      trajectory: {
        deltaPercent: 'Not calculated', deltaPeriod: 'Performance calculator unavailable',
        startLabel: 'Not available', troughLabel: 'Not available', endLabel: asOf || 'Not available', points: [],
      },
      topHoldings,
      remainingHoldingsNote: holdings.length > 4 ? `${holdings.length - 4} additional holdings available in the snapshot.` : 'All holdings shown from the selected snapshot.',
    },
    synthesisedAnalysis: {
      syncTime: 'Not connected', headline: '', narrative: '', whyItMatters: '', monitor: '',
    },
    strategicMatrix: { risks: [], opportunities: [] },
  };
}
