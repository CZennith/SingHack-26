/**
 * StressWorkbenchPage — main container for the Stress Test & RM Intelligence Workbench.
 *
 * Two modes:
 *  - "client"    : stress tests for a single selected client
 *  - "book-wide" : scenario run across all 20 clients (leaderboard)
 *
 * On mount in client mode, background fetches for look-through and liquidity
 * are fired automatically so those panels are ready before the RM runs a scenario.
 *
 * Requirements: 1.1, 1.2, 1.4, 1.5, 1.6, 1.7, 9.6
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeft, Activity, ChevronDown, AlertTriangle, RefreshCw } from 'lucide-react';
import type { ClientDossier } from '../types';
import {
  NAMED_SCENARIOS,
  type ScenarioConfig,
  type StressRunResult,
  type LookThroughResult,
  type LiquidityResult,
  type BookScenarioResponse,
  type AuditEntry,
  type NamedScenarioId,
} from '../types/stressWorkbench';
import {
  runStressTest,
  getLookThrough,
  getLiquidity,
  runBookScenario,
} from '../services/stressTest';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface StressWorkbenchPageProps {
  mode: 'client' | 'book-wide';
  clientId: string | null;
  allClients: ClientDossier[];
  onBack: () => void;
  onSelectClient: (clientId: string) => void;
}

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

const usd = (value: number) =>
  `USD ${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const pct = (value: number, decimals = 2) =>
  `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`;

// ---------------------------------------------------------------------------
// Default scenario (tech-selloff as sensible first pick)
// ---------------------------------------------------------------------------

const DEFAULT_SCENARIO: ScenarioConfig = NAMED_SCENARIOS['tech-selloff'];

// ---------------------------------------------------------------------------
// Status badge helpers (design token tokens from Requirements 14.3)
// ---------------------------------------------------------------------------

const badgeClass = (level: 'critical' | 'elevated' | 'ok') => {
  if (level === 'critical') return 'bg-[#fcf5f5] text-[#7A1C28] border border-[#eed6d9]';
  if (level === 'elevated') return 'bg-[#fdf8f0] text-[#9E6B20] border border-[#f4e4cc]';
  return 'bg-[#faf9f6] text-[#666666] border border-[#dedbd5]';
};

// ---------------------------------------------------------------------------
// Skeleton placeholder
// ---------------------------------------------------------------------------

const Skeleton: React.FC<{ lines?: number }> = ({ lines = 3 }) => (
  <div className="space-y-2 animate-pulse">
    {Array.from({ length: lines }).map((_, i) => (
      <div key={i} className={`h-4 bg-[#f4f3f0] rounded ${i === lines - 1 ? 'w-3/4' : 'w-full'}`} />
    ))}
  </div>
);

// ---------------------------------------------------------------------------
// Section header
// ---------------------------------------------------------------------------

const SectionHeader: React.FC<{ index: string; title: string }> = ({ index, title }) => (
  <div className="flex items-baseline gap-3 border-b border-[#e8e5e0] pb-3 mb-5">
    <span className="text-[10px] uppercase tracking-[0.14em] font-medium text-[#767676] font-mono">
      SECTION {index} · {title}
    </span>
  </div>
);

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export const StressWorkbenchPage: React.FC<StressWorkbenchPageProps> = ({
  mode,
  clientId,
  allClients,
  onBack,
  onSelectClient,
}) => {
  const activeClient = useMemo(
    () => allClients.find((c) => c.id === clientId) ?? null,
    [allClients, clientId],
  );

  // --- Scenario config state (persisted across client switches) ---
  const [scenarioConfig, setScenarioConfig] = useState<ScenarioConfig>(DEFAULT_SCENARIO);
  const [customShocks, setCustomShocks] = useState<Record<string, number>>({});

  // --- Result states ---
  const [stressResult, setStressResult] = useState<StressRunResult | null>(null);
  const [lookThroughResult, setLookThroughResult] = useState<LookThroughResult | null>(null);
  const [liquidityResult, setLiquidityResult] = useState<LiquidityResult | null>(null);
  const [bookScenarioResult, setBookScenarioResult] = useState<BookScenarioResponse | null>(null);

  // --- Loading / error states ---
  const [isRunning, setIsRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [isLoadingLookThrough, setIsLoadingLookThrough] = useState(false);
  const [lookThroughError, setLookThroughError] = useState<string | null>(null);
  const [isLoadingLiquidity, setIsLoadingLiquidity] = useState(false);
  const [liquidityError, setLiquidityError] = useState<string | null>(null);
  const [isRunningBookScenario, setIsRunningBookScenario] = useState(false);
  const [bookScenarioError, setBookScenarioError] = useState<string | null>(null);

  // --- Audit trail ---
  const [auditEntries, setAuditEntries] = useState<AuditEntry[]>([]);
  const [hasUnreviewedResult, setHasUnreviewedResult] = useState(false);
  const [auditNote, setAuditNote] = useState('');
  const [showAuditInput, setShowAuditInput] = useState<'reviewed' | 'actioned' | null>(null);
  const [auditLogOpen, setAuditLogOpen] = useState(false);

  // --- Navigation guard ref ---
  const hasUnreviewedRef = useRef(false);
  hasUnreviewedRef.current = hasUnreviewedResult;

  // --- Validation ---
  const shocksForRun = scenarioConfig.id === 'custom' ? customShocks : (scenarioConfig.shocks as Record<string, number>);
  const invalidShocks = Object.entries(shocksForRun).filter(([, v]) => v < -100 || v > 100);
  const canRun = invalidShocks.length === 0 && !!clientId;

  // ---------------------------------------------------------------------------
  // Background data fetches on mount (client mode)
  // ---------------------------------------------------------------------------

  useEffect(() => {
    if (mode !== 'client' || !clientId) return;
    const controller = new AbortController();

    // Look-through
    setIsLoadingLookThrough(true);
    setLookThroughError(null);
    getLookThrough(clientId, controller.signal)
      .then(setLookThroughResult)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setLookThroughError(err instanceof Error ? err.message : 'Failed to load concentration data.');
      })
      .finally(() => setIsLoadingLookThrough(false));

    // Liquidity
    setIsLoadingLiquidity(true);
    setLiquidityError(null);
    getLiquidity(clientId, controller.signal)
      .then(setLiquidityResult)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setLiquidityError(err instanceof Error ? err.message : 'Failed to load liquidity data.');
      })
      .finally(() => setIsLoadingLiquidity(false));

    return () => controller.abort();
  }, [mode, clientId]);

  // ---------------------------------------------------------------------------
  // Run stress test
  // ---------------------------------------------------------------------------

  const handleRun = useCallback(async () => {
    if (!clientId || !canRun) return;
    setIsRunning(true);
    setRunError(null);
    setStressResult(null);
    setHasUnreviewedResult(false);

    try {
      const result = await runStressTest({
        client_id: clientId,
        scenario: {
          scenario_id: scenarioConfig.id,
          shocks: shocksForRun as Record<string, number>,
          sector_overrides: (scenarioConfig.sector_overrides ?? {}) as Record<string, number>,
        },
      });
      setStressResult(result);
      setHasUnreviewedResult(true);
    } catch (err: unknown) {
      setRunError(err instanceof Error ? err.message : 'Stress test failed.');
    } finally {
      setIsRunning(false);
    }
  }, [clientId, canRun, scenarioConfig, shocksForRun]);

  // ---------------------------------------------------------------------------
  // Run book-wide scenario
  // ---------------------------------------------------------------------------

  const handleRunBookScenario = useCallback(async () => {
    setIsRunningBookScenario(true);
    setBookScenarioError(null);
    try {
      const result = await runBookScenario({
        scenario: {
          scenario_id: scenarioConfig.id,
          shocks: shocksForRun as Record<string, number>,
          sector_overrides: (scenarioConfig.sector_overrides ?? {}) as Record<string, number>,
        },
      });
      setBookScenarioResult(result);
    } catch (err: unknown) {
      setBookScenarioError(err instanceof Error ? err.message : 'Book scenario failed.');
    } finally {
      setIsRunningBookScenario(false);
    }
  }, [scenarioConfig, shocksForRun]);

  // ---------------------------------------------------------------------------
  // Audit trail helpers
  // ---------------------------------------------------------------------------

  const addAuditEntry = useCallback(
    (decision: AuditEntry['decision'], note = '') => {
      if (!stressResult) return;
      setAuditEntries((prev) => [
        ...prev,
        {
          result_id: stressResult.result_id,
          timestamp: new Date().toISOString(),
          client_id: stressResult.client_id,
          scenario_name: stressResult.scenario.label,
          decision,
          note: note.slice(0, 160),
        },
      ]);
      setHasUnreviewedResult(false);
    },
    [stressResult],
  );

  const handleMarkDecision = (decision: 'reviewed' | 'actioned') => {
    addAuditEntry(decision, auditNote);
    setAuditNote('');
    setShowAuditInput(null);
  };

  // ---------------------------------------------------------------------------
  // Navigate-away guard (Req 9.6)
  // ---------------------------------------------------------------------------

  const handleBack = useCallback(() => {
    if (
      hasUnreviewedRef.current &&
      !window.confirm('This stress result has not been reviewed. Leave anyway?')
    ) {
      return;
    }
    onBack();
  }, [onBack]);

  // ---------------------------------------------------------------------------
  // Scenario change handler
  // ---------------------------------------------------------------------------

  const handleScenarioChange = (id: NamedScenarioId | 'custom') => {
    if (id === 'custom') {
      setScenarioConfig({ id: 'custom', label: 'Custom', shocks: {} });
    } else {
      setScenarioConfig(NAMED_SCENARIOS[id]);
    }
    // Changing scenario clears previous result
    setStressResult(null);
    setHasUnreviewedResult(false);
    setRunError(null);
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  const currentClient = activeClient;

  return (
    <div className="w-full min-h-screen bg-[#faf9f6]">
      <div className="max-w-6xl mx-auto px-6 sm:px-10 pt-8 pb-24 space-y-10">

        {/* ------------------------------------------------------------------ */}
        {/* Breadcrumb & header                                                 */}
        {/* ------------------------------------------------------------------ */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={handleBack}
              className="inline-flex items-center gap-1.5 text-[12px] text-[#767676] hover:text-[#121212] transition-colors cursor-pointer group"
            >
              <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform" />
              <span>
                {mode === 'client' && currentClient
                  ? `Back to ${currentClient.name}`
                  : 'Back to Overview'}
              </span>
            </button>

            {/* Client switcher (client mode only) */}
            {mode === 'client' && allClients.length > 0 && (
              <div className="flex items-center gap-2 text-[11px] font-mono text-[#767676]">
                <span className="text-[10px] uppercase tracking-[0.1em]">Client:</span>
                <div className="relative">
                  <select
                    value={clientId ?? ''}
                    onChange={(e) => onSelectClient(e.target.value)}
                    className="appearance-none bg-white border border-[#e8e5e0] text-[#121212] text-[12px] px-3 py-1 pr-7 focus:outline-none focus:border-[#121212] cursor-pointer"
                  >
                    {allClients.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-[#767676] pointer-events-none" />
                </div>
              </div>
            )}
          </div>

          {/* Page title */}
          <div className="border-b border-[#e8e5e0] pb-6">
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.14em] font-medium text-[#767676] mb-2">
              <Activity className="w-3.5 h-3.5" />
              <span>Stress Test & RM Intelligence Workbench</span>
              {mode === 'book-wide' && (
                <span className="ml-2 px-2 py-0.5 bg-[#fdf8f0] text-[#9E6B20] border border-[#f4e4cc] text-[9px] uppercase tracking-widest">
                  Book-Wide Mode
                </span>
              )}
            </div>
            <h1 className="font-serif text-[30px] sm:text-[34px] leading-tight text-[#121212] tracking-tight">
              {mode === 'client' && currentClient
                ? `${currentClient.name} — Stress Analysis`
                : 'Book-Wide Scenario Analysis'}
            </h1>
            {mode === 'client' && currentClient && (
              <p className="text-[12.5px] text-[#666666] mt-1">
                {currentClient.tier} · {currentClient.mandate} · AUM {currentClient.aum}
              </p>
            )}
          </div>
        </div>

        {/* ------------------------------------------------------------------ */}
        {/* Scenario picker                                                      */}
        {/* ------------------------------------------------------------------ */}
        <section className="bg-white border border-[#e8e5e0] p-6 shadow-2xs space-y-5">
          <SectionHeader index="01" title="SCENARIO CONFIGURATION" />

          <div className="flex flex-col sm:flex-row sm:items-end gap-4">
            <div className="flex-1 space-y-1.5">
              <label className="text-[10px] uppercase tracking-[0.12em] font-medium text-[#767676]">
                Scenario
              </label>
              <div className="relative">
                <select
                  value={scenarioConfig.id}
                  onChange={(e) => handleScenarioChange(e.target.value as NamedScenarioId | 'custom')}
                  className="w-full appearance-none bg-[#faf9f6] border border-[#e8e5e0] text-[#121212] text-[13px] px-3 py-2.5 pr-8 focus:outline-none focus:border-[#121212] cursor-pointer"
                >
                  {(Object.keys(NAMED_SCENARIOS) as NamedScenarioId[]).map((id) => (
                    <option key={id} value={id}>
                      {NAMED_SCENARIOS[id].label}
                    </option>
                  ))}
                  <option value="custom">Custom</option>
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#767676] pointer-events-none" />
              </div>
            </div>

            {/* Named scenario — show shock summary */}
            {scenarioConfig.id !== 'custom' && (
              <div className="flex flex-wrap gap-2 text-[11px] font-mono">
                {Object.entries(scenarioConfig.shocks).map(([ac, pct]) => (
                  <span
                    key={ac}
                    className={`px-2 py-1 border text-[10px] ${
                      (pct as number) < 0 ? badgeClass('critical') : badgeClass('ok')
                    }`}
                  >
                    {ac}: {(pct as number) >= 0 ? '+' : ''}{pct}%
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Custom scenario shock table */}
          {scenarioConfig.id === 'custom' && (
            <div className="space-y-3">
              <p className="text-[12px] text-[#666666]">
                Enter shock percentages per asset class (−100 to +100):
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {(['Equity', 'Fixed Income', 'Cash and Equivalents', 'Alternatives', 'Commodities', 'Structured Products'] as const).map(
                  (ac) => {
                    const val = customShocks[ac] ?? 0;
                    const isInvalid = val < -100 || val > 100;
                    return (
                      <div key={ac} className="space-y-1">
                        <label className="text-[10px] text-[#767676] uppercase tracking-[0.1em]">
                          {ac}
                        </label>
                        <input
                          type="number"
                          value={val}
                          min={-100}
                          max={100}
                          step={0.5}
                          onChange={(e) =>
                            setCustomShocks((prev) => ({
                              ...prev,
                              [ac]: parseFloat(e.target.value) || 0,
                            }))
                          }
                          className={`w-full border text-[13px] px-3 py-2 bg-[#faf9f6] focus:outline-none ${
                            isInvalid
                              ? 'border-[#7A1C28] text-[#7A1C28]'
                              : 'border-[#e8e5e0] text-[#121212] focus:border-[#121212]'
                          }`}
                        />
                        {isInvalid && (
                          <p className="text-[10px] text-[#7A1C28]">Must be −100 to +100</p>
                        )}
                      </div>
                    );
                  },
                )}
              </div>
            </div>
          )}

          {/* Validation summary */}
          {invalidShocks.length > 0 && (
            <div className="flex items-center gap-2 text-[12px] text-[#7A1C28] bg-[#fcf5f5] border border-[#eed6d9] px-3 py-2">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
              <span>Fix invalid shock values before running.</span>
            </div>
          )}

          {/* Run button */}
          <div className="flex items-center gap-3 pt-2">
            {mode === 'client' ? (
              <button
                type="button"
                onClick={handleRun}
                disabled={!canRun || isRunning}
                className="bg-[#121212] text-white text-[10px] font-medium uppercase tracking-[0.14em] px-5 py-2.5 flex items-center gap-2 transition-colors cursor-pointer hover:bg-neutral-800 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isRunning ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Running…</span>
                  </>
                ) : (
                  <>
                    <Activity className="w-3.5 h-3.5" />
                    <span>Run Stress Tests</span>
                  </>
                )}
              </button>
            ) : (
              <button
                type="button"
                onClick={handleRunBookScenario}
                disabled={isRunningBookScenario}
                className="bg-[#121212] text-white text-[10px] font-medium uppercase tracking-[0.14em] px-5 py-2.5 flex items-center gap-2 transition-colors cursor-pointer hover:bg-neutral-800 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isRunningBookScenario ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Running book scenario…</span>
                  </>
                ) : (
                  <>
                    <Activity className="w-3.5 h-3.5" />
                    <span>Run Book Scenario</span>
                  </>
                )}
              </button>
            )}
          </div>

          {runError && (
            <div className="flex items-center gap-2 text-[12px] text-[#7A1C28] bg-[#fcf5f5] border border-[#eed6d9] px-3 py-2">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
              <span>{runError}</span>
              <button
                type="button"
                onClick={handleRun}
                className="ml-auto underline underline-offset-4 cursor-pointer"
              >
                Retry
              </button>
            </div>
          )}
        </section>

        {/* ------------------------------------------------------------------ */}
        {/* Scenario narrative card (shown after run)                           */}
        {/* ------------------------------------------------------------------ */}
        {stressResult?.narrative && (
          <section className="bg-white border border-[#e8e5e0] p-6 shadow-2xs">
            <div className="flex items-start gap-3.5">
              <div className="w-6 h-6 border border-[#e8e5e0] bg-[#faf9f6] flex items-center justify-center shrink-0 mt-0.5">
                <span className="font-mono text-[12px] font-semibold text-[#121212]">✦</span>
              </div>
              <div>
                <div className="text-[9.5px] uppercase tracking-[0.14em] font-medium text-[#767676] mb-2">
                  Scenario Narrative · {stressResult.scenario.label}
                </div>
                <p className="text-[13.5px] text-[#1e1e1e] leading-relaxed font-serif">
                  {stressResult.narrative}
                </p>
              </div>
            </div>
          </section>
        )}

        {/* ------------------------------------------------------------------ */}
        {/* CLIENT MODE: stress result panels                                   */}
        {/* ------------------------------------------------------------------ */}
        {mode === 'client' && (
          <>
            {/* SECTION 02 — Macro Shock */}
            <section className="bg-white border border-[#e8e5e0] p-6 shadow-2xs space-y-4">
              <SectionHeader index="02" title="MACRO SHOCK SIMULATOR" />
              {isRunning && <Skeleton lines={4} />}
              {!isRunning && stressResult && (
                <>
                  {/* Summary metrics */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
                    {[
                      { label: 'Current Portfolio', value: usd(stressResult.macro_shock.total_current_value_usd) },
                      { label: 'Shocked Portfolio', value: usd(stressResult.macro_shock.total_shocked_value_usd) },
                      {
                        label: 'Net Dollar Impact',
                        value: usd(stressResult.macro_shock.net_dollar_impact_usd),
                        negative: stressResult.macro_shock.net_dollar_impact_usd < 0,
                      },
                      {
                        label: 'Net % Change',
                        value: pct(stressResult.macro_shock.net_pct_change),
                        negative: stressResult.macro_shock.net_pct_change < 0,
                      },
                    ].map(({ label, value, negative }) => (
                      <div key={label} className="bg-[#faf9f6] border border-[#e8e5e0] p-4">
                        <div className="text-[9.5px] uppercase tracking-[0.1em] text-[#767676] mb-1.5">{label}</div>
                        <div className={`font-mono text-[13px] font-semibold ${negative ? 'text-[#7A1C28]' : 'text-[#121212]'}`}>
                          {value}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Top-10 holdings table */}
                  {stressResult.macro_shock.top_impacted_holdings.length > 0 && (
                    <div className="overflow-x-auto">
                      <table className="w-full text-[12px]">
                        <thead>
                          <tr className="border-b border-[#e8e5e0] text-[10px] uppercase tracking-[0.1em] text-[#767676]">
                            <th className="text-left py-2 pr-4 font-medium">Holding</th>
                            <th className="text-left py-2 pr-4 font-medium">Asset Class</th>
                            <th className="text-right py-2 pr-4 font-medium">Current</th>
                            <th className="text-right py-2 pr-4 font-medium">Shocked</th>
                            <th className="text-right py-2 font-medium">Change</th>
                          </tr>
                        </thead>
                        <tbody>
                          {stressResult.macro_shock.top_impacted_holdings.map((h) => (
                            <tr key={h.instrument_id} className="border-b border-[#f4f3f0] hover:bg-[#faf9f6]">
                              <td className="py-2.5 pr-4">
                                <span className="text-[#121212]">{h.instrument_name}</span>
                                {h.look_through_applied && (
                                  <span className="ml-1.5 text-[9px] px-1 py-0.5 bg-[#fdf8f0] text-[#9E6B20] border border-[#f4e4cc]">
                                    LT
                                  </span>
                                )}
                              </td>
                              <td className="py-2.5 pr-4 text-[#666666]">{h.asset_class}</td>
                              <td className="py-2.5 pr-4 text-right font-mono">{usd(h.current_value_usd)}</td>
                              <td className="py-2.5 pr-4 text-right font-mono">{usd(h.shocked_value_usd)}</td>
                              <td className={`py-2.5 text-right font-mono font-semibold ${h.dollar_change_usd < 0 ? 'text-[#7A1C28]' : 'text-[#2d6a2d]'}`}>
                                {usd(h.dollar_change_usd)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <p className="text-[10px] text-[#888888] mt-2">
                        LT = Look-through applied — shock uses underlying asset class.
                      </p>
                    </div>
                  )}
                </>
              )}
              {!isRunning && !stressResult && (
                <p className="text-[12.5px] text-[#888888]">Run a scenario above to see macro shock results.</p>
              )}
            </section>

            {/* SECTION 03 — Lombard LTV */}
            <section className="bg-white border border-[#e8e5e0] p-6 shadow-2xs space-y-4">
              <SectionHeader index="03" title="LOMBARD LTV STRESS TEST" />
              {isRunning && <Skeleton lines={3} />}
              {!isRunning && stressResult && (() => {
                const facilities = stressResult.ltv_stress.facilities;
                if (facilities.length === 0) {
                  return <p className="text-[12.5px] text-[#888888]">No Lombard facility on record for this client.</p>;
                }
                return (
                  <div className="space-y-6">
                    {facilities.map((f) => {
                      const cols = [
                        { label: 'Current LTV', val: f.current_ltv_pct, isLtv: true, scenario: false },
                        { label: 'LTV at −10%', val: f.ltv_at_minus_10_pct, isLtv: true, scenario: false },
                        { label: 'LTV at −20%', val: f.ltv_at_minus_20_pct, isLtv: true, scenario: false },
                        { label: 'LTV at −30%', val: f.ltv_at_minus_30_pct, isLtv: true, scenario: false },
                        { label: 'Scenario LTV', val: f.scenario_ltv_pct, isLtv: true, scenario: true },
                      ];
                      return (
                        <div key={f.facility_id} className="space-y-3">
                          <div className="flex items-center gap-3 text-[11px] font-mono text-[#767676]">
                            <span className="font-semibold text-[#121212]">{f.facility_id}</span>
                            <span>Drawn: {usd(f.drawn_usd)}</span>
                            <span>Margin call threshold: <strong className="text-[#121212]">{f.margin_call_ltv_pct.toFixed(1)}%</strong></span>
                          </div>
                          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                            {cols.map(({ label, val, scenario }) => {
                              if (scenario && val === null) return (
                                <div key={label} className="bg-[#faf9f6] border border-[#e8e5e0] p-3">
                                  <div className="text-[9.5px] uppercase tracking-[0.1em] text-[#767676] mb-1">{label}</div>
                                  <div className="font-mono text-[12px] text-[#888888]">N/A</div>
                                </div>
                              );
                              const ltvVal = val as number;
                              const isBreached = ltvVal >= f.margin_call_ltv_pct;
                              return (
                                <div key={label} className={`p-3 border ${isBreached ? 'bg-[#fcf5f5] border-[#eed6d9]' : 'bg-[#faf9f6] border-[#e8e5e0]'}`}>
                                  <div className="text-[9.5px] uppercase tracking-[0.1em] text-[#767676] mb-1">{label}</div>
                                  <div className={`font-mono text-[12px] font-semibold ${isBreached ? 'text-[#7A1C28]' : 'text-[#121212]'}`}>
                                    {ltvVal.toFixed(1)}%
                                  </div>
                                  {isBreached && (
                                    <div className={`mt-1 text-[9px] uppercase tracking-wider px-1.5 py-0.5 inline-block ${badgeClass('critical')}`}>
                                      Margin Call
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                          {/* Headroom row */}
                          <div className="text-[11px] font-mono text-[#666666] flex flex-wrap gap-4">
                            {[
                              ['−10%', f.headroom_at_minus_10_usd],
                              ['−20%', f.headroom_at_minus_20_usd],
                              ['−30%', f.headroom_at_minus_30_usd],
                            ].map(([label, val]) => (
                              <span key={label as string}>
                                Headroom at {label}: <strong className={(val as number) < 0 ? 'text-[#7A1C28]' : 'text-[#121212]'}>{usd(val as number)}</strong>
                              </span>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                );
              })()}
              {!isRunning && !stressResult && (
                <p className="text-[12.5px] text-[#888888]">Run a scenario to see LTV stress results.</p>
              )}
            </section>

            {/* SECTION 04 — Look-Through Concentration */}
            <section className="bg-white border border-[#e8e5e0] p-6 shadow-2xs space-y-4">
              <SectionHeader index="04" title="LOOK-THROUGH CONCENTRATION" />
              {isLoadingLookThrough && <Skeleton lines={5} />}
              {lookThroughError && (
                <div className={`flex items-center gap-2 text-[12px] px-3 py-2 ${badgeClass('critical')}`}>
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                  <span>{lookThroughError}</span>
                </div>
              )}
              {!isLoadingLookThrough && lookThroughResult && (
                <>
                  {lookThroughResult.hidden_concentration_discoveries.length > 0 && (
                    <div className={`p-4 ${badgeClass('elevated')} space-y-1`}>
                      <div className="text-[10px] uppercase tracking-widest font-medium">
                        Hidden Concentration Discovered
                      </div>
                      {lookThroughResult.hidden_concentration_discoveries.map((h) => (
                        <p key={h.exposure_name} className="text-[12px]">
                          <strong>{h.exposure_name}</strong>: {h.pre_pct.toFixed(2)}% → {h.post_pct.toFixed(2)}% after look-through (+{h.gap_pct.toFixed(2)} pp). {h.explanation}
                        </p>
                      ))}
                    </div>
                  )}
                  <div className="overflow-x-auto">
                    <table className="w-full text-[12px]">
                      <thead>
                        <tr className="border-b border-[#e8e5e0] text-[10px] uppercase tracking-[0.1em] text-[#767676]">
                          <th className="text-left py-2 pr-4 font-medium">Exposure</th>
                          <th className="text-right py-2 pr-3 font-medium">Pre-LT %</th>
                          <th className="text-right py-2 pr-3 font-medium">Post-LT %</th>
                          <th className="text-right py-2 pr-3 font-medium">Limit %</th>
                          <th className="text-right py-2 font-medium">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {lookThroughResult.concentrations.map((row, i) => {
                          const statusLevel =
                            row.status === 'BREACH' ? 'critical' :
                            row.status === 'ELEVATED' ? 'elevated' : 'ok';
                          return (
                            <tr key={i} className="border-b border-[#f4f3f0] hover:bg-[#faf9f6]">
                              <td className="py-2.5 pr-4 text-[#121212]">{row.exposure_name}</td>
                              <td className="py-2.5 pr-3 text-right font-mono text-[#666666]">{row.pre_look_through_pct.toFixed(2)}%</td>
                              <td className="py-2.5 pr-3 text-right font-mono font-semibold text-[#121212]">{row.post_look_through_pct.toFixed(2)}%</td>
                              <td className="py-2.5 pr-3 text-right font-mono text-[#666666]">
                                {row.mandate_limit_pct !== null ? `${row.mandate_limit_pct.toFixed(1)}%` : '—'}
                              </td>
                              <td className="py-2.5 text-right">
                                {row.status !== 'NO_LIMIT' ? (
                                  <span className={`text-[9px] uppercase tracking-wider px-1.5 py-0.5 ${badgeClass(statusLevel)}`}>
                                    {row.status}
                                  </span>
                                ) : (
                                  <span className="text-[11px] text-[#888888]">—</span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
              {!isLoadingLookThrough && !lookThroughResult && !lookThroughError && (
                <p className="text-[12.5px] text-[#888888]">Loading concentration data…</p>
              )}
            </section>

            {/* SECTION 05 — Liquidity Coverage */}
            <section className="bg-white border border-[#e8e5e0] p-6 shadow-2xs space-y-4">
              <SectionHeader index="05" title="LIQUIDITY COVERAGE TEST" />
              {isLoadingLiquidity && <Skeleton lines={4} />}
              {liquidityError && (
                <div className={`flex items-center gap-2 text-[12px] px-3 py-2 ${badgeClass('critical')}`}>
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                  <span>{liquidityError}</span>
                </div>
              )}
              {!isLoadingLiquidity && liquidityResult && (
                <>
                  {/* LCR summary */}
                  <div className={`p-4 border ${liquidityResult.status === 'SHORTFALL' ? 'bg-[#fcf5f5] border-[#eed6d9]' : 'bg-[#faf9f6] border-[#e8e5e0]'}`}>
                    <div className="flex flex-wrap items-center gap-6 text-[12px] font-mono">
                      <div>
                        <span className="text-[10px] uppercase tracking-[0.1em] text-[#767676] block mb-0.5">LCR</span>
                        <span className={`text-[22px] font-semibold ${liquidityResult.status === 'SHORTFALL' ? 'text-[#7A1C28]' : 'text-[#121212]'}`}>
                          {liquidityResult.lcr !== null ? liquidityResult.lcr.toFixed(2) : 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] uppercase tracking-[0.1em] text-[#767676] block mb-0.5">Status</span>
                        <span className={`px-2 py-1 text-[10px] uppercase tracking-wider font-medium ${badgeClass(liquidityResult.status === 'SHORTFALL' ? 'critical' : 'ok')}`}>
                          {liquidityResult.status}
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] uppercase tracking-[0.1em] text-[#767676] block mb-0.5">Tier-1 Liquid</span>
                        <span className="text-[#121212]">{usd(liquidityResult.tier1_liquid_value_usd)}</span>
                      </div>
                      <div>
                        <span className="text-[10px] uppercase tracking-[0.1em] text-[#767676] block mb-0.5">60-Day Obligations</span>
                        <span className="text-[#121212]">{usd(liquidityResult.total_60d_obligations_usd)}</span>
                      </div>
                      <div>
                        <span className="text-[10px] uppercase tracking-[0.1em] text-[#767676] block mb-0.5">
                          {liquidityResult.surplus_or_gap_usd >= 0 ? 'Surplus' : 'Gap'}
                        </span>
                        <span className={liquidityResult.surplus_or_gap_usd < 0 ? 'text-[#7A1C28] font-semibold' : 'text-[#121212]'}>
                          {usd(Math.abs(liquidityResult.surplus_or_gap_usd))}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Sell-to-cover list */}
                  {liquidityResult.sell_to_cover.length > 0 && (
                    <div className="space-y-2">
                      <div className="text-[10px] uppercase tracking-[0.12em] text-[#767676] font-medium">Sell-to-Cover (ranked)</div>
                      {liquidityResult.sell_to_cover.map((item) => (
                        <div key={item.rank} className="flex items-center justify-between text-[12px] bg-[#faf9f6] border border-[#e8e5e0] px-4 py-2.5">
                          <div className="flex items-center gap-3">
                            <span className="font-mono text-[10px] text-[#888888]">#{item.rank}</span>
                            <span className="text-[#121212]">{item.instrument_name}</span>
                          </div>
                          <div className="flex items-center gap-4 font-mono text-[11px]">
                            <span>{usd(item.current_value_usd)}</span>
                            <span className={item.unrealised_pnl_usd < 0 ? 'text-[#7A1C28]' : 'text-[#2d6a2d]'}>
                              P&L: {usd(item.unrealised_pnl_usd)}
                            </span>
                            <span className="text-[#888888]">T+{item.estimated_settle_days}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Life-event flags */}
                  {liquidityResult.life_event_flags.length > 0 && (
                    <div className="space-y-2">
                      <div className="text-[10px] uppercase tracking-[0.12em] text-[#767676] font-medium">Life-Event Planning Flags</div>
                      {liquidityResult.life_event_flags.map((flag, i) => (
                        <div key={i} className={`p-4 ${badgeClass('elevated')} space-y-1`}>
                          <div className="text-[11px] font-semibold">{flag.description} — Due {flag.due_date}</div>
                          <div className="text-[11px]">{flag.life_stage_note}</div>
                          <div className="text-[11px] font-mono">Amount: {usd(flag.amount_usd)} · Coverage ratio: {flag.coverage_ratio.toFixed(2)}x</div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
              {!isLoadingLiquidity && !liquidityResult && !liquidityError && (
                <p className="text-[12.5px] text-[#888888]">Loading liquidity data…</p>
              )}
            </section>

            {/* SECTION 06 — RM Recommendations */}
            <section className="bg-white border border-[#e8e5e0] p-6 shadow-2xs space-y-4">
              <SectionHeader index="06" title="RM RECOMMENDATIONS" />
              {isRunning && <Skeleton lines={3} />}
              {!isRunning && stressResult && (
                <div className="space-y-3">
                  {stressResult.recommendations.map((rec, i) => (
                    <div key={i} className={`p-4 border ${rec.mandate_breach ? 'bg-[#fcf5f5] border-[#eed6d9]' : 'bg-[#faf9f6] border-[#e8e5e0]'}`}>
                      <div className="flex items-start justify-between gap-4">
                        <div className="space-y-1.5 flex-1">
                          <div className="text-[13px] font-medium text-[#121212]">
                            {rec.action_verb} {rec.holding_name ?? rec.asset_class}
                          </div>
                          <div className="text-[12px] text-[#666666]">{rec.plain_language_summary}</div>
                          {rec.mandate_breach && rec.breach_detail && (
                            <div className={`text-[11px] px-2 py-1.5 ${badgeClass('critical')}`}>
                              <span className="font-medium">Mandate breach: </span>{rec.breach_detail}
                            </div>
                          )}
                          {rec.mandate_breach && rec.alternative_action && (
                            <div className={`text-[11px] px-2 py-1.5 ${badgeClass('elevated')}`}>
                              <span className="font-medium">Alternative: </span>{rec.alternative_action}
                            </div>
                          )}
                        </div>
                        <span className={`shrink-0 text-[9px] uppercase tracking-wider px-2 py-1 ${badgeClass('ok')}`}>
                          {rec.approval_label}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              {!isRunning && !stressResult && (
                <p className="text-[12.5px] text-[#888888]">Run a scenario to see RM recommendations.</p>
              )}
            </section>

            {/* SECTION 07 — Audit Trail */}
            {stressResult && (
              <section className="bg-white border border-[#e8e5e0] p-6 shadow-2xs space-y-4">
                <SectionHeader index="07" title="AUDIT TRAIL" />

                {/* Has this result been marked? */}
                {auditEntries.filter((e) => e.result_id === stressResult.result_id).length > 0 ? (
                  <div className="flex items-center gap-2 text-[12px] text-[#2d6a2d] bg-[#f0faf0] border border-[#c8e6c9] px-3 py-2">
                    <span>✓</span>
                    <span>
                      Result marked as{' '}
                      <strong>
                        {auditEntries.find((e) => e.result_id === stressResult.result_id)?.decision}
                      </strong>{' '}
                      at {new Date(auditEntries.find((e) => e.result_id === stressResult.result_id)!.timestamp).toLocaleTimeString()}
                      {auditEntries.find((e) => e.result_id === stressResult.result_id)?.note && (
                        <> — "{auditEntries.find((e) => e.result_id === stressResult.result_id)?.note}"</>
                      )}
                    </span>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <p className="text-[12px] text-[#666666]">
                      Mark this stress result to create a defensible advisory record.
                    </p>
                    {showAuditInput && (
                      <div className="space-y-2">
                        <input
                          type="text"
                          value={auditNote}
                          onChange={(e) => setAuditNote(e.target.value.slice(0, 160))}
                          placeholder="Optional note (max 160 characters)…"
                          className="w-full border border-[#e8e5e0] bg-[#faf9f6] text-[13px] px-3 py-2 focus:outline-none focus:border-[#121212]"
                        />
                        <div className="text-[10px] text-[#888888] text-right">{auditNote.length}/160</div>
                      </div>
                    )}
                    <div className="flex items-center gap-3">
                      {showAuditInput === null && (
                        <>
                          <button
                            type="button"
                            onClick={() => setShowAuditInput('reviewed')}
                            className="bg-[#121212] text-white text-[10px] font-medium uppercase tracking-[0.14em] px-4 py-2 cursor-pointer hover:bg-neutral-800"
                          >
                            Mark as Reviewed
                          </button>
                          <button
                            type="button"
                            onClick={() => setShowAuditInput('actioned')}
                            className="border border-[#121212] text-[#121212] text-[10px] font-medium uppercase tracking-[0.14em] px-4 py-2 cursor-pointer hover:bg-[#f4f3f0]"
                          >
                            Mark as Actioned
                          </button>
                        </>
                      )}
                      {showAuditInput && (
                        <>
                          <button
                            type="button"
                            onClick={() => handleMarkDecision(showAuditInput)}
                            className="bg-[#121212] text-white text-[10px] font-medium uppercase tracking-[0.14em] px-4 py-2 cursor-pointer hover:bg-neutral-800"
                          >
                            Confirm {showAuditInput === 'reviewed' ? 'Review' : 'Action'}
                          </button>
                          <button
                            type="button"
                            onClick={() => { setShowAuditInput(null); setAuditNote(''); }}
                            className="text-[#767676] text-[11px] underline cursor-pointer"
                          >
                            Cancel
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                )}

                {/* Collapsible audit log */}
                {auditEntries.length > 0 && (
                  <div className="pt-2 border-t border-[#e8e5e0]">
                    <button
                      type="button"
                      onClick={() => setAuditLogOpen((o) => !o)}
                      className="flex items-center gap-2 text-[11px] text-[#767676] hover:text-[#121212] transition-colors cursor-pointer"
                    >
                      <ChevronDown className={`w-3 h-3 transition-transform ${auditLogOpen ? 'rotate-180' : ''}`} />
                      <span>Audit log ({auditEntries.filter((e) => e.client_id === clientId).length} entries)</span>
                    </button>
                    {auditLogOpen && (
                      <div className="mt-3 space-y-2">
                        {[...auditEntries]
                          .filter((e) => e.client_id === clientId)
                          .reverse()
                          .map((entry, i) => (
                            <div key={i} className="text-[11px] text-[#666666] bg-[#faf9f6] border border-[#e8e5e0] px-3 py-2">
                              <span className="font-mono text-[10px] text-[#888888]">{new Date(entry.timestamp).toLocaleString()}</span>
                              {' · '}
                              <span className="font-medium text-[#121212]">{entry.decision}</span>
                              {' · '}
                              <span>{entry.scenario_name}</span>
                              {entry.note && <span> — "{entry.note}"</span>}
                            </div>
                          ))}
                      </div>
                    )}
                  </div>
                )}
              </section>
            )}
          </>
        )}

        {/* ------------------------------------------------------------------ */}
        {/* BOOK-WIDE MODE: leaderboard                                         */}
        {/* ------------------------------------------------------------------ */}
        {mode === 'book-wide' && (
          <section className="bg-white border border-[#e8e5e0] p-6 shadow-2xs space-y-4">
            <SectionHeader index="02" title="SCENARIO IMPACT LEADERBOARD" />
            {isRunningBookScenario && <Skeleton lines={6} />}
            {bookScenarioError && (
              <div className={`flex items-center gap-2 text-[12px] px-3 py-2 ${badgeClass('critical')}`}>
                <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                <span>{bookScenarioError}</span>
              </div>
            )}
            {!isRunningBookScenario && bookScenarioResult && (
              <>
                <div className={`px-4 py-2 text-[11px] ${badgeClass('elevated')}`}>
                  <strong>{bookScenarioResult.scenario.label}</strong> — Leaderboard sorted by scenario impact. LTV breach clients rank first.
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-[12px]">
                    <thead>
                      <tr className="border-b border-[#e8e5e0] text-[10px] uppercase tracking-[0.1em] text-[#767676]">
                        <th className="text-left py-2 pr-3 font-medium w-8">Rank</th>
                        <th className="text-left py-2 pr-4 font-medium">Client</th>
                        <th className="text-right py-2 pr-4 font-medium">Net $ Impact</th>
                        <th className="text-right py-2 pr-4 font-medium">% Change</th>
                        <th className="text-right py-2 font-medium">LTV Breach</th>
                      </tr>
                    </thead>
                    <tbody>
                      {bookScenarioResult.clients.map((row) => (
                        <tr
                          key={row.client_id}
                          className="border-b border-[#f4f3f0] hover:bg-[#faf9f6] cursor-pointer"
                          onClick={() => onSelectClient(row.client_id)}
                        >
                          <td className="py-2.5 pr-3 font-mono text-[#888888]">{row.scenario_rank}</td>
                          <td className="py-2.5 pr-4 text-[#121212] font-medium">{row.client_name}</td>
                          <td className={`py-2.5 pr-4 text-right font-mono font-semibold ${row.net_dollar_impact_usd < 0 ? 'text-[#7A1C28]' : 'text-[#2d6a2d]'}`}>
                            {usd(row.net_dollar_impact_usd)}
                          </td>
                          <td className={`py-2.5 pr-4 text-right font-mono ${row.net_pct_change < 0 ? 'text-[#7A1C28]' : 'text-[#2d6a2d]'}`}>
                            {pct(row.net_pct_change)}
                          </td>
                          <td className="py-2.5 text-right">
                            {row.ltv_breach ? (
                              <span className={`text-[9px] uppercase tracking-wider px-1.5 py-0.5 ${badgeClass('critical')}`}>
                                Breach
                              </span>
                            ) : (
                              <span className="text-[11px] text-[#888888]">—</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <p className="text-[10px] text-[#888888] mt-2">Click a client row to open their individual stress workbench.</p>
                </div>
              </>
            )}
            {!isRunningBookScenario && !bookScenarioResult && !bookScenarioError && (
              <p className="text-[12.5px] text-[#888888]">Select a scenario and click "Run Book Scenario" to see the impact leaderboard.</p>
            )}
          </section>
        )}
      </div>
    </div>
  );
};
