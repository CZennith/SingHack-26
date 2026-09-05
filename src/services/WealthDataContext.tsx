import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { connectorConfig } from './connectorConfig';
import {
  ApiClientError, ApiClientSummary, ClientSnapshot, SnapshotDateOption,
  fetchClients, fetchExposure, fetchExposureChanges, fetchMarketContext, fetchSnapshot, fetchSnapshotDates,
} from './apiClient';

interface WealthDataState {
  mode: 'mock' | 'live';
  dates: SnapshotDateOption[];
  datesLoading: boolean;
  asOfDate: string;
  comparisonDate: string;
  periodStart: string;
  periodEnd: string;
  clients: ApiClientSummary[];
  selectedClientId: string;
  snapshot: ClientSnapshot | null;
  exposure: Record<string, unknown> | null;
  exposureChanges: Record<string, unknown> | null;
  marketContext: Array<Record<string, unknown>>;
  loading: boolean;
  error: string | null;
  dateError: string | null;
  setAsOfDate: (value: string) => void;
  setComparisonDate: (value: string) => void;
  setSelectedClientId: (value: string) => void;
}

const WealthDataContext = createContext<WealthDataState | null>(null);

function queryValue(key: string): string {
  if (typeof window === 'undefined') return '';
  return new URLSearchParams(window.location.search).get(key) || '';
}

function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}

function message(error: unknown): string {
  return error instanceof ApiClientError || error instanceof Error ? error.message : 'wealth API request failed';
}

export function resolveDateSelection(
  available: SnapshotDateOption[],
  requestedAsOf = '',
  requestedComparison = '',
  requestedPeriodStart = '',
  requestedPeriodEnd = '',
): { asOfDate: string; comparisonDate: string; periodStart: string; periodEnd: string } {
  if (!available.length) throw new Error('wealth API returned no supported snapshot dates');
  const sorted = [...available].sort((a, b) => a.as_of_date.localeCompare(b.as_of_date));
  const latest = sorted[sorted.length - 1].as_of_date;
  const asOfDate = requestedAsOf || latest;
  if (!sorted.some((item) => item.as_of_date === asOfDate)) throw new Error(`Unsupported snapshot date in URL: ${asOfDate}`);
  const prior = sorted.filter((item) => item.as_of_date < asOfDate).at(-1)?.as_of_date || '';
  const comparisonDate = requestedComparison || prior;
  if (!comparisonDate || !sorted.some((item) => item.as_of_date === comparisonDate) || comparisonDate === asOfDate) {
    throw new Error(`Unsupported comparison date: ${comparisonDate || 'none'}`);
  }
  return {
    asOfDate,
    comparisonDate,
    periodStart: requestedPeriodStart || comparisonDate,
    periodEnd: requestedPeriodEnd || asOfDate,
  };
}

export function WealthDataProvider({ children }: { children: React.ReactNode }) {
  const mode = connectorConfig.mode;
  const [dates, setDates] = useState<SnapshotDateOption[]>([]);
  const [datesLoading, setDatesLoading] = useState(mode === 'live');
  const [asOfDate, setAsOfDateState] = useState(queryValue('as_of_date'));
  const [comparisonDate, setComparisonDateState] = useState(queryValue('comparison_date'));
  const [periodStart, setPeriodStart] = useState(queryValue('period_start'));
  const [periodEnd, setPeriodEnd] = useState(queryValue('period_end'));
  const [clients, setClients] = useState<ApiClientSummary[]>([]);
  const [selectedClientId, setSelectedClientIdState] = useState(queryValue('client_id'));
  const [snapshot, setSnapshot] = useState<ClientSnapshot | null>(null);
  const [exposure, setExposure] = useState<Record<string, unknown> | null>(null);
  const [exposureChanges, setExposureChanges] = useState<Record<string, unknown> | null>(null);
  const [marketContext, setMarketContext] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dateError, setDateError] = useState<string | null>(null);

  useEffect(() => {
    if (mode !== 'live') return;
    const controller = new AbortController();
    fetchSnapshotDates(controller.signal)
      .then((available) => {
        setDates(available);
        const selection = resolveDateSelection(
          available, asOfDate, comparisonDate, queryValue('period_start'), queryValue('period_end'),
        );
        setAsOfDateState(selection.asOfDate);
        setComparisonDateState(selection.comparisonDate);
        setPeriodStart(selection.periodStart);
        setPeriodEnd(selection.periodEnd);
      })
      .catch((requestError) => { if (!isAbort(requestError)) setDateError(message(requestError)); })
      .finally(() => setDatesLoading(false));
    return () => controller.abort();
    // Initial URL values are intentionally captured on first mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  useEffect(() => {
    if (mode !== 'live' || !asOfDate || dateError) return;
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    fetchClients(asOfDate, controller.signal)
      .then((items) => {
        setClients(items);
        if (selectedClientId && !items.some((item) => item.client_id === selectedClientId)) {
          setError(`Unknown client_id: ${selectedClientId}`);
          setSelectedClientIdState('');
        } else if (!selectedClientId && items[0]) {
          setSelectedClientIdState(items[0].client_id);
        }
      })
      .catch((requestError) => { if (!isAbort(requestError)) setError(message(requestError)); })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [mode, asOfDate, dateError]);

  useEffect(() => {
    if (mode !== 'live' || !asOfDate || !comparisonDate || !periodStart || !periodEnd || !selectedClientId || dateError) return;
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    Promise.all([
      fetchSnapshot(selectedClientId, asOfDate, periodStart, periodEnd, controller.signal),
      fetchExposure(selectedClientId, asOfDate, periodStart, periodEnd, controller.signal),
      fetchExposureChanges(selectedClientId, asOfDate, comparisonDate, periodStart, periodEnd, controller.signal),
    ])
      .then(([nextSnapshot, nextExposure, nextChanges]) => {
        if (nextSnapshot.snapshot_metadata.client_id !== selectedClientId) throw new ApiClientError(502, 'snapshot client mismatch');
        setSnapshot(nextSnapshot);
        setExposure(nextExposure);
        setExposureChanges(nextChanges);
      })
      .catch((requestError) => { if (!isAbort(requestError)) { setSnapshot(null); setExposureChanges(null); setError(message(requestError)); } })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [mode, asOfDate, comparisonDate, periodStart, periodEnd, selectedClientId, dateError]);

  useEffect(() => {
    if (mode !== 'live' || !asOfDate || dateError) return;
    const controller = new AbortController();
    fetchMarketContext(asOfDate, controller.signal)
      .then(setMarketContext)
      .catch((requestError) => { if (!isAbort(requestError)) setError(message(requestError)); });
    return () => controller.abort();
  }, [mode, asOfDate, dateError]);

  useEffect(() => {
    if (mode !== 'live' || !asOfDate || typeof window === 'undefined') return;
    const url = new URL(window.location.href);
    const values: Record<string, string> = {
      as_of_date: asOfDate, comparison_date: comparisonDate, period_start: periodStart,
      period_end: periodEnd, client_id: selectedClientId,
    };
    Object.entries(values).forEach(([key, value]) => value ? url.searchParams.set(key, value) : url.searchParams.delete(key));
    window.history.replaceState({}, '', url);
  }, [mode, asOfDate, comparisonDate, periodStart, periodEnd, selectedClientId]);

  const setAsOfDate = (value: string) => {
    if (!dates.some((item) => item.as_of_date === value)) { setDateError(`Unsupported snapshot date: ${value}`); return; }
    setDateError(null);
    setAsOfDateState(value);
    const prior = dates.filter((item) => item.as_of_date < value).at(-1)?.as_of_date || value;
    if (prior === value) setDateError('A comparison date is required for this snapshot');
    else { setComparisonDateState(prior); setPeriodStart(prior); setPeriodEnd(value); }
    setSnapshot(null); setExposure(null); setExposureChanges(null);
  };

  const setComparisonDate = (value: string) => {
    if (!dates.some((item) => item.as_of_date === value) || value === asOfDate) { setDateError(`Unsupported comparison date: ${value}`); return; }
    setDateError(null); setComparisonDateState(value); setPeriodStart(value); setPeriodEnd(asOfDate);
    setSnapshot(null); setExposure(null); setExposureChanges(null);
  };

  const setSelectedClientId = (value: string) => {
    setSelectedClientIdState(value);
    setSnapshot(null);
    setExposure(null);
    setExposureChanges(null);
  };

  const value = useMemo(() => ({
    mode, dates, datesLoading, asOfDate, comparisonDate, periodStart, periodEnd, clients,
    selectedClientId, snapshot, exposure, exposureChanges, marketContext, loading, error, dateError,
    setAsOfDate, setComparisonDate, setSelectedClientId,
  }), [mode, dates, datesLoading, asOfDate, comparisonDate, periodStart, periodEnd, clients, selectedClientId, snapshot, exposure, exposureChanges, marketContext, loading, error, dateError]);

  return <WealthDataContext.Provider value={value}>{children}</WealthDataContext.Provider>;
}

export function useWealthData(): WealthDataState {
  const value = useContext(WealthDataContext);
  if (!value) throw new Error('useWealthData must be used inside WealthDataProvider');
  return value;
}
