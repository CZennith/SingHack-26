import assert from 'node:assert/strict';
import test from 'node:test';

import {
  ApiClientError,
  fetchClients,
  fetchExposure,
  fetchExposureChanges,
  fetchSnapshot,
  fetchSnapshotDates,
} from '../../src/services/apiClient';
import { resolveDateSelection } from '../../src/services/WealthDataContext';
import { toClientDossier } from '../../src/services/viewModels';

const dates = [
  { as_of_date: '2026-06-30', holdings: true, valuations: true, facilities: true, market_context: true },
  { as_of_date: '2026-08-26', holdings: true, valuations: true, facilities: true, market_context: true },
];

function response(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), { status, headers: { 'Content-Type': 'application/json' } });
}

function metadata(overrides: Record<string, unknown> = {}) {
  return {
    result_type: 'client_snapshot', schema_version: '1.0.0', client_id: 'CL-0001',
    as_of_date: '2026-08-26', comparison_date: null, period_start: '2026-06-30', period_end: '2026-08-26',
    ...overrides,
  };
}

test('date selection defaults to latest and prior comparison, while preserving explicit URL dates', () => {
  assert.deepEqual(resolveDateSelection(dates), {
    asOfDate: '2026-08-26', comparisonDate: '2026-06-30', periodStart: '2026-06-30', periodEnd: '2026-08-26',
  });
  assert.deepEqual(resolveDateSelection(dates, '2026-06-30', '2026-08-26', '2026-01-01', '2026-06-30'), {
    asOfDate: '2026-06-30', comparisonDate: '2026-08-26', periodStart: '2026-01-01', periodEnd: '2026-06-30',
  });
  assert.throws(() => resolveDateSelection(dates, '2026-08-27'), /Unsupported snapshot date/);
});

test('browser API client passes dates and rejects metadata mismatches', async () => {
  const requests: URL[] = [];
  const previousFetch = globalThis.fetch;
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    const url = new URL(String(input));
    requests.push(url);
    const resource = url.searchParams.get('resource');
    if (resource === 'dates') return response({ response_metadata: metadata({ result_type: 'snapshot_dates', client_id: null, as_of_date: null }), dates });
    if (resource === 'clients') return response({ response_metadata: metadata({ result_type: 'client_list', client_id: null, as_of_date: url.searchParams.get('as_of_date') }), clients: [] });
    if (resource === 'snapshot') {
      return response({ response_metadata: metadata(), snapshot: { snapshot_metadata: { client_id: 'CL-0001', as_of_date: '2026-08-26', period_start: '2026-06-30', period_end: '2026-08-26', calculation_version: '1.0.0' } } });
    }
    if (resource === 'exposure') return response({ response_metadata: metadata({ result_type: 'exposure_base', period_start: '2026-06-30', period_end: '2026-08-26' }), exposure: {} });
    return response({ response_metadata: metadata({ result_type: 'exposure_changes', comparison_date: '2026-06-30' }), result: { result_metadata: { client_id: 'CL-0001', as_of_date: '2026-08-26', comparison_date: '2026-06-30' } } });
  }) as typeof fetch;
  try {
    assert.deepEqual((await fetchSnapshotDates()).map((item) => item.as_of_date), ['2026-06-30', '2026-08-26']);
    await fetchClients('2026-08-26');
    await fetchSnapshot('CL-0001', '2026-08-26', '2026-06-30', '2026-08-26');
    await fetchExposure('CL-0001', '2026-08-26', '2026-06-30', '2026-08-26');
    await fetchExposureChanges('CL-0001', '2026-08-26', '2026-06-30', '2026-06-30', '2026-08-26');
    const snapshotRequest = requests.find((url) => url.searchParams.get('resource') === 'snapshot');
    assert.equal(snapshotRequest?.searchParams.get('period_start'), '2026-06-30');
    assert.equal(snapshotRequest?.searchParams.get('period_end'), '2026-08-26');
    const changesRequest = requests.find((url) => url.searchParams.get('resource') === 'exposure_changes');
    assert.equal(changesRequest?.searchParams.get('comparison_date'), '2026-06-30');
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test('browser API client refuses a response for the wrong client', async () => {
  const previousFetch = globalThis.fetch;
  globalThis.fetch = (async () => response({
    response_metadata: metadata({ client_id: 'CL-0002' }),
    snapshot: { snapshot_metadata: { client_id: 'CL-0002', as_of_date: '2026-08-26', period_start: '2026-06-30', period_end: '2026-08-26', calculation_version: '1.0.0' } },
  })) as typeof fetch;
  try {
    await assert.rejects(
      fetchSnapshot('CL-0001', '2026-08-26', '2026-06-30', '2026-08-26'),
      (error: unknown) => error instanceof ApiClientError && /client_id/.test(error.message),
    );
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test('browser API client rejects malformed calculator metadata and missing client metadata', async () => {
  const previousFetch = globalThis.fetch;
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    const url = new URL(String(input));
    if (url.searchParams.get('resource') === 'exposure_changes') {
      return response({
        response_metadata: metadata({ result_type: 'exposure_changes', comparison_date: '2026-06-30' }),
        result: { result_metadata: { client_id: 'CL-0001', as_of_date: 'not-a-date', comparison_date: '2026-06-30' } },
      });
    }
    return response({ response_metadata: metadata({ client_id: null }) });
  }) as typeof fetch;
  try {
    await assert.rejects(
      fetchExposureChanges('CL-0001', '2026-08-26', '2026-06-30', '2026-06-30', '2026-08-26'),
      (error: unknown) => error instanceof ApiClientError && /dates/.test(error.message),
    );
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test('live view model keeps unsupported analysis as explicit placeholders', () => {
  const dossier = toClientDossier({
    client_id: 'CL-0001', client_name: 'Example Client', age: 40, base_currency: 'USD', wealth_band: 'UHNW',
    risk_profile: 'Balanced Growth', risk_tolerance_score: null, investment_horizon_years: 10, liquidity_needs: null,
    client_since: '2010-01-01', rm_id: null, rm_name: null, rm_desk: null, life_stage: null, objectives: null,
    aum_usd_at_as_of: 100, portfolio_count: 1, facility_count: 0, max_ltv_pct_at_as_of: null,
  });
  assert.equal(dossier.id, 'CL-0001');
  assert.equal(dossier.riskLevel, null);
  assert.equal(dossier.headlineIssue, '');
  assert.equal(dossier.portfolio.cashLiquidity, 'Not calculated');
});
