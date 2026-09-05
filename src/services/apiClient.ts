import { connectorConfig } from './connectorConfig';

export interface SnapshotDateOption {
  as_of_date: string;
  holdings: boolean;
  valuations: boolean;
  facilities: boolean;
  market_context: boolean;
}

export interface ApiClientSummary {
  client_id: string;
  client_name: string;
  age: number | null;
  base_currency: string | null;
  wealth_band: string | null;
  risk_profile: string | null;
  risk_tolerance_score: number | null;
  investment_horizon_years: number | null;
  liquidity_needs: string | null;
  client_since: string | null;
  rm_id: string | null;
  rm_name: string | null;
  rm_desk: string | null;
  life_stage: string | null;
  objectives: string | null;
  aum_usd_at_as_of: number;
  portfolio_count: number;
  facility_count: number;
  max_ltv_pct_at_as_of: number | null;
}

export interface ApiEnvelope<T> {
  response_metadata: {
    result_type: string;
    schema_version: string;
    client_id: string | null;
    as_of_date: string | null;
    comparison_date: string | null;
    period_start: string | null;
    period_end: string | null;
  };
  [key: string]: unknown;
}

export interface SnapshotEnvelope extends ApiEnvelope<Record<string, unknown>> {
  snapshot: ClientSnapshot;
}

export interface ClientSnapshot {
  snapshot_metadata: {
    client_id: string;
    as_of_date: string;
    period_start: string;
    period_end: string;
    calculation_version: string;
  };
  client: Record<string, unknown>;
  portfolios: Array<Record<string, unknown>>;
  portfolio_summaries: Array<Record<string, unknown>>;
  holdings: Array<Record<string, unknown>>;
  transactions: Array<Record<string, unknown>>;
  planned_cash_needs: Array<Record<string, unknown>>;
  commitments: Array<Record<string, unknown>>;
  credit_facilities: Array<Record<string, unknown>>;
  rm_notes: Array<Record<string, unknown>>;
  market_events: Array<Record<string, unknown>>;
  data_quality_flags: Array<Record<string, unknown>>;
  source_references: Array<Record<string, unknown>>;
}

export interface ExposureEnvelope extends ApiEnvelope<Record<string, unknown>> {
  result: Record<string, unknown>;
}

export interface ExposureBaseEnvelope extends ApiEnvelope<Record<string, unknown>> {
  exposure: Record<string, unknown>;
}

export interface MarketContextEnvelope extends ApiEnvelope<Record<string, unknown>> {
  records: Array<Record<string, unknown>>;
}

export class ApiClientError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = 'ApiClientError';
  }
}

function endpoint(): string {
  return `${connectorConfig.apiBaseUrl}/api/wealth`;
}

function assertIsoDate(value: unknown, field: string): asserts value is string {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    throw new ApiClientError(502, `${field} must be an ISO date in YYYY-MM-DD format`);
  }
}

async function request<T extends ApiEnvelope<unknown>>(
  resource: string,
  params: Record<string, string | undefined> = {},
  signal?: AbortSignal,
): Promise<T> {
  const origin = typeof window === 'undefined' ? 'http://localhost' : window.location.origin;
  const url = new URL(endpoint(), origin);
  url.searchParams.set('resource', resource);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') url.searchParams.set(key, value);
  });
  const response = await fetch(url.toString(), { headers: { Accept: 'application/json' }, signal });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const message = body?.error?.message || `wealth API request failed (${response.status})`;
    throw new ApiClientError(response.status, message);
  }
  if (!body || typeof body !== 'object' || !body.response_metadata) {
    throw new ApiClientError(502, 'wealth API returned an invalid response envelope');
  }
  return body as T;
}

function validateMetadata(
  body: ApiEnvelope<unknown>,
  expected: { clientId?: string; asOfDate?: string; comparisonDate?: string; resultType?: string },
): void {
  const metadata = body.response_metadata;
  if (expected.clientId !== undefined && metadata.client_id !== expected.clientId) {
    throw new ApiClientError(502, 'wealth API response client_id does not match the request');
  }
  if (expected.asOfDate !== undefined && metadata.as_of_date !== expected.asOfDate) {
    throw new ApiClientError(502, 'wealth API response as_of_date does not match the request');
  }
  if (expected.comparisonDate !== undefined && metadata.comparison_date !== expected.comparisonDate) {
    throw new ApiClientError(502, 'wealth API response comparison_date does not match the request');
  }
  if (expected.resultType !== undefined && metadata.result_type !== expected.resultType) {
    throw new ApiClientError(502, 'wealth API response type does not match the request');
  }
}

export async function fetchSnapshotDates(signal?: AbortSignal): Promise<SnapshotDateOption[]> {
  const body = await request<ApiEnvelope<unknown> & { dates: SnapshotDateOption[] }>('dates', {}, signal);
  if (!Array.isArray(body.dates) || body.dates.length === 0) {
    throw new ApiClientError(502, 'wealth API returned no supported snapshot dates');
  }
  body.dates.forEach((item) => assertIsoDate(item?.as_of_date, 'as_of_date'));
  return [...body.dates].sort((a, b) => a.as_of_date.localeCompare(b.as_of_date));
}

export async function fetchClients(asOfDate: string, signal?: AbortSignal): Promise<ApiClientSummary[]> {
  const body = await request<ApiEnvelope<unknown> & { clients: ApiClientSummary[] }>(
    'clients', { as_of_date: asOfDate }, signal,
  );
  assertIsoDate(body.response_metadata.as_of_date, 'response_metadata.as_of_date');
  validateMetadata(body, { asOfDate, resultType: 'client_list' });
  if (!Array.isArray(body.clients)) throw new ApiClientError(502, 'wealth API returned an invalid client list');
  return body.clients;
}

export async function fetchSnapshot(
  clientId: string,
  asOfDate: string,
  periodStart: string,
  periodEnd: string,
  signal?: AbortSignal,
): Promise<ClientSnapshot> {
  const body = await request<SnapshotEnvelope>('snapshot', {
    client_id: clientId, as_of_date: asOfDate, period_start: periodStart, period_end: periodEnd,
  }, signal);
  validateMetadata(body, { clientId, asOfDate, resultType: 'client_snapshot' });
  const metadata = body.snapshot?.snapshot_metadata;
  if (!metadata || metadata.client_id !== clientId || metadata.as_of_date !== asOfDate || metadata.period_start !== periodStart || metadata.period_end !== periodEnd) {
    throw new ApiClientError(502, 'snapshot metadata does not match the requested client or dates');
  }
  return body.snapshot;
}

export async function fetchExposureChanges(
  clientId: string,
  asOfDate: string,
  comparisonDate: string,
  periodStart: string,
  periodEnd: string,
  signal?: AbortSignal,
): Promise<Record<string, unknown>> {
  const body = await request<ExposureEnvelope>('exposure_changes', {
    client_id: clientId, as_of_date: asOfDate, comparison_date: comparisonDate,
    period_start: periodStart, period_end: periodEnd,
  }, signal);
  validateMetadata(body, { clientId, asOfDate, comparisonDate, resultType: 'exposure_changes' });
  const metadata = body.result?.result_metadata as Record<string, unknown> | undefined;
  if (!metadata || metadata.client_id !== clientId || metadata.as_of_date !== asOfDate || metadata.comparison_date !== comparisonDate) {
    throw new ApiClientError(502, 'exposure-change metadata does not match the requested dates');
  }
  return body.result;
}

export async function fetchExposure(
  clientId: string,
  asOfDate: string,
  periodStart: string,
  periodEnd: string,
  signal?: AbortSignal,
): Promise<Record<string, unknown>> {
  const body = await request<ExposureBaseEnvelope>('exposure', {
    client_id: clientId, as_of_date: asOfDate, period_start: periodStart, period_end: periodEnd,
  }, signal);
  validateMetadata(body, { clientId, asOfDate, resultType: 'exposure_base' });
  if (!body.exposure || typeof body.exposure !== 'object') {
    throw new ApiClientError(502, 'wealth API returned an invalid exposure base');
  }
  return body.exposure;
}

export async function fetchMarketContext(asOfDate: string, signal?: AbortSignal): Promise<Array<Record<string, unknown>>> {
  const body = await request<MarketContextEnvelope>('market_context', { as_of_date: asOfDate }, signal);
  validateMetadata(body, { asOfDate, resultType: 'market_context' });
  return body.records;
}
