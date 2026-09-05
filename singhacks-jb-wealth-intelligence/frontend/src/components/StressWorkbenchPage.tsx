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
 * Requirements: 1.6, 1.7, 9.6
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Activity } from 'lucide-react';
import type { ClientDossier } from '../types';
import {
  NAMED_SCENARIOS,
  type ScenarioConfig,
  type StressRunResult,
  type LookThroughResult,
  type LiquidityResult,
  type BookScenarioResponse,
  type AuditEntry,
} from '../types/stressWorkbench';
import {
  getLookThrough,
  getLiquidity,
} from '../services/stressTest';
import { WorkbenchBreadcrumb } from './WorkbenchBreadcrumb';
import { UrgencyScoreBanner } from './UrgencyScoreBanner';
import { ScenarioNarrativeCard } from './ScenarioNarrativeCard';
import { ScenarioPicker } from './ScenarioPicker';
import { MacroShockPanel } from './MacroShockPanel';
import { LombardLTVPanel } from './LombardLTVPanel';
import { LookThroughPanel } from './LookThroughPanel';
import { LiquidityCoveragePanel } from './LiquidityCoveragePanel';
import { RMActionPanel } from './RMActionPanel';
import { AuditTrailPanel } from './AuditTrailPanel';
import { BookScenarioLeaderboard } from './BookScenarioLeaderboard';
import { CallScriptModal } from './CallScriptModal';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface StressWorkbenchPageProps {
  mode: 'client' | 'book-wide';
  /** null only in book-wide mode before client drill-down */
  clientId: string | null;
  allClients: ClientDossier[];
  onBack: () => void;
  onSelectClient: (clientId: string) => void;
  /** Called after a book-wide scenario completes successfully (Req 12.4, 12.7) */
  onBookScenarioRun?: (scenarioName: string) => void;
}

// ---------------------------------------------------------------------------
// WorkbenchState — full session state shape (design.md § State Management)
// ---------------------------------------------------------------------------

interface WorkbenchState {
  // Navigation
  mode: 'client' | 'book-wide';
  activeClientId: string | null;

  // Scenario configuration (persisted across client switches)
  scenarioConfig: ScenarioConfig;

  // Results (cleared when scenario changes or client switches)
  stressResult: StressRunResult | null;
  lookThroughResult: LookThroughResult | null;
  liquidityResult: LiquidityResult | null;
  bookScenarioResult: BookScenarioResponse | null;

  // Loading states
  isRunning: boolean;
  isLoadingLookThrough: boolean;
  isLoadingLiquidity: boolean;
  isRunningBookScenario: boolean;

  // Audit trail (append-only, persisted for session)
  auditEntries: AuditEntry[];

  // Call script
  callScript: string | null;
  isCallScriptModalOpen: boolean;

  // Unreviewed navigation guard (Req 9.6)
  hasUnreviewedResult: boolean;
}

// ---------------------------------------------------------------------------
// Helper: convert a NamedScenarioDefinition + its id key to a ScenarioConfig
// ---------------------------------------------------------------------------

function namedToConfig(id: keyof typeof NAMED_SCENARIOS): ScenarioConfig {
  const def = NAMED_SCENARIOS[id];
  return {
    id,
    label: def.label,
    shocks: def.shocks,
    sector_overrides: def.sector_overrides,
  };
}

// ---------------------------------------------------------------------------
// Default scenario (tech-selloff as sensible first pick)
// ---------------------------------------------------------------------------

const DEFAULT_SCENARIO: ScenarioConfig = namedToConfig('tech-selloff');



// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export const StressWorkbenchPage: React.FC<StressWorkbenchPageProps> = ({
  mode,
  clientId,
  allClients,
  onBack,
  onSelectClient,
  onBookScenarioRun,
}) => {
  const activeClient = allClients.find((c) => c.id === clientId) ?? null;

  // -------------------------------------------------------------------------
  // WorkbenchState — decomposed into individual useState calls for ergonomics,
  // but collectively they represent the WorkbenchState shape from design.md.
  // -------------------------------------------------------------------------

  // Navigation (mirrors WorkbenchState.mode / .activeClientId)
  // Derived from props — no separate state needed.

  // Scenario configuration
  const [scenarioConfig, setScenarioConfig] = useState<ScenarioConfig>(DEFAULT_SCENARIO);

  // Results
  const [stressResult, setStressResult] = useState<StressRunResult | null>(null);
  const [lookThroughResult, setLookThroughResult] = useState<LookThroughResult | null>(null);
  const [liquidityResult, setLiquidityResult] = useState<LiquidityResult | null>(null);
  const [bookScenarioResult, setBookScenarioResult] = useState<BookScenarioResponse | null>(null);

  // Loading states
  const [isRunning, setIsRunning] = useState(false);
  const [isLoadingLookThrough, setIsLoadingLookThrough] = useState(false);
  const [isLoadingLiquidity, setIsLoadingLiquidity] = useState(false);
  const [isRunningBookScenario, setIsRunningBookScenario] = useState(false);

  // Audit trail
  const [auditEntries, setAuditEntries] = useState<AuditEntry[]>([]);

  // Macro shock error
  const [macroShockError, setMacroShockError] = useState<string | null>(null);

  // Call script
  const [callScript, setCallScript] = useState<string | null>(null);
  const [isCallScriptModalOpen, setIsCallScriptModalOpen] = useState(false);

  // Unreviewed navigation guard (Req 9.6)
  const [hasUnreviewedResult, setHasUnreviewedResult] = useState(false);

  // Ref for synchronous access in the navigation guard callback
  const hasUnreviewedRef = useRef(false);
  hasUnreviewedRef.current = hasUnreviewedResult;

  // Expose the full WorkbenchState shape as a computed object for consumers /
  // tests that need to inspect it as a single unit.
  const workbenchState: WorkbenchState = {
    mode,
    activeClientId: clientId,
    scenarioConfig,
    stressResult,
    lookThroughResult,
    liquidityResult,
    bookScenarioResult,
    isRunning,
    isLoadingLookThrough,
    isLoadingLiquidity,
    isRunningBookScenario,
    auditEntries,
    callScript,
    isCallScriptModalOpen,
    hasUnreviewedResult,
  };

  // -------------------------------------------------------------------------
  // Background data fetches on mount — client mode only (Req 1.6, design §State)
  // Fires GET /api/stress-test/look-through and GET /api/stress-test/liquidity
  // -------------------------------------------------------------------------

  useEffect(() => {
    if (mode !== 'client' || !clientId) return;

    const controller = new AbortController();

    // Look-through fetch
    setIsLoadingLookThrough(true);
    getLookThrough(clientId, controller.signal)
      .then(setLookThroughResult)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        console.error('Look-through fetch failed:', err);
      })
      .finally(() => setIsLoadingLookThrough(false));

    // Liquidity fetch
    setIsLoadingLiquidity(true);
    getLiquidity(clientId, controller.signal)
      .then(setLiquidityResult)
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        console.error('Liquidity fetch failed:', err);
      })
      .finally(() => setIsLoadingLiquidity(false));

    return () => controller.abort();
  }, [mode, clientId]);

  // -------------------------------------------------------------------------
  // State-transition: scenario change clears results (design.md §State transitions)
  // -------------------------------------------------------------------------

  const handleScenarioChange = useCallback((config: ScenarioConfig) => {
    setScenarioConfig(config);
    // Changing scenario clears previous stress result and resets unreviewed guard
    setStressResult(null);
    setHasUnreviewedResult(false);
  }, []);

  // -------------------------------------------------------------------------
  // Navigate-away guard (Req 9.6)
  // -------------------------------------------------------------------------

  const handleBack = useCallback(() => {
    if (
      hasUnreviewedRef.current &&
      !window.confirm('This stress result has not been reviewed. Leave anyway?')
    ) {
      return;
    }
    onBack();
  }, [onBack]);

  // -------------------------------------------------------------------------
  // Stub run handlers (full implementation in later tasks)
  // -------------------------------------------------------------------------

  const handleRun = useCallback(async () => {
    if (!clientId) return;
    setIsRunning(true);
    setStressResult(null);
    setHasUnreviewedResult(false);
    setMacroShockError(null);
    try {
      // Full implementation via RunStressTests task
      const { runStressTest } = await import('../services/stressTest');
      const result = await runStressTest({
        client_id: clientId,
        scenario: {
          scenario_id: scenarioConfig.id,
          shocks: scenarioConfig.shocks as Record<string, number>,
          sector_overrides: (scenarioConfig.sector_overrides ?? {}) as Record<string, number>,
        },
      });
      setStressResult(result);
      setHasUnreviewedResult(true);
    } catch (err: unknown) {
      console.error('Stress test failed:', err);
      setMacroShockError(err instanceof Error ? err.message : 'Stress test failed');
    } finally {
      setIsRunning(false);
    }
  }, [clientId, scenarioConfig]);

  const handleRunBookScenario = useCallback(async () => {
    setIsRunningBookScenario(true);
    try {
      const { runBookScenario } = await import('../services/stressTest');
      const result = await runBookScenario({
        scenario: {
          scenario_id: scenarioConfig.id,
          shocks: scenarioConfig.shocks as Record<string, number>,
          sector_overrides: (scenarioConfig.sector_overrides ?? {}) as Record<string, number>,
        },
      });
      setBookScenarioResult(result);
      // Notify parent that a book scenario completed (Req 12.4, 12.7)
      onBookScenarioRun?.(result.scenario.label);
    } catch (err: unknown) {
      console.error('Book scenario failed:', err);
    } finally {
      setIsRunningBookScenario(false);
    }
  }, [scenarioConfig, onBookScenarioRun]);

  // -------------------------------------------------------------------------
  // Audit trail handlers — append entries returned from AuditTrailPanel (Req 9)
  // -------------------------------------------------------------------------

  const handleMarkReviewed = useCallback((entry: AuditEntry) => {
    setAuditEntries((prev) => [...prev, entry]);
    // Marking as reviewed clears the unreviewed guard (Req 9.6)
    setHasUnreviewedResult(false);
  }, []);

  const handleMarkActioned = useCallback((entry: AuditEntry) => {
    setAuditEntries((prev) => [...prev, entry]);
    // Marking as actioned also clears the unreviewed guard (Req 9.6)
    setHasUnreviewedResult(false);
  }, []);

  // -------------------------------------------------------------------------
  // Call script handlers (Req 10)
  // -------------------------------------------------------------------------

  const handleOpenCallScript = useCallback(() => {
    setIsCallScriptModalOpen(true);
  }, []);

  const handleCloseCallScript = useCallback(() => {
    setIsCallScriptModalOpen(false);
  }, []);

  const handleCallScriptAudit = useCallback((entry: AuditEntry) => {
    setAuditEntries((prev) => [...prev, entry]);
  }, []);

  // Prevent unused variable warning — workbenchState is used for type-checking
  // and will be passed to sub-panels in later tasks.
  void workbenchState;

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div className="w-full min-h-screen bg-[#faf9f6]">
      <div className="max-w-6xl mx-auto px-6 sm:px-10 pt-8 pb-24 space-y-6">

        {/* ------------------------------------------------------------------
            WorkbenchBreadcrumb — back navigation + client switcher (Req 1.6, 1.7)
        ------------------------------------------------------------------ */}
        <WorkbenchBreadcrumb
          mode={mode}
          activeClient={activeClient}
          allClients={allClients}
          clientId={clientId}
          onBack={handleBack}
          onSelectClient={onSelectClient}
        />

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
            {mode === 'client' && activeClient
              ? `${activeClient.name} — Stress Analysis`
              : 'Book-Wide Scenario Analysis'}
          </h1>
          {mode === 'client' && activeClient && (
            <p className="text-[12.5px] text-[#666666] mt-1">
              {activeClient.tier} · {activeClient.mandate} · AUM {activeClient.aum}
            </p>
          )}
        </div>

        {/* ------------------------------------------------------------------
            UrgencyScoreBanner — urgency score + projected delta (Req 11)
        ------------------------------------------------------------------ */}
        {mode === 'client' && (
          <UrgencyScoreBanner
            clientId={clientId ?? ''}
            currentScore={activeClient?.urgencyScore ?? 0}
            riskLevel={activeClient?.riskLevel ?? 'LOW'}
            triggers={
              activeClient?.prioritizationTriggers
                ? activeClient.prioritizationTriggers.map((t, i) => {
                    // Triggers are stored as "Label (+pts)" strings, e.g. "LTV Pressure (+25)"
                    const match = t.match(/^(.*?)\s*\(\+(\d+)\)$/);
                    const label = match ? match[1].trim() : t;
                    const points = match ? parseInt(match[2], 10) : 0;
                    return {
                      code: `trigger-${i}`,
                      label,
                      points,
                      evidence_summary: label,
                      module_anchor: '',
                    };
                  })
                : []
            }
            projectedScore={
              stressResult !== null && activeClient?.urgencyScore !== undefined
                ? activeClient.urgencyScore + (stressResult.ltv_stress?.facilities?.some(
                    (f) => f.scenario_ltv_pct !== null && f.scenario_ltv_pct >= f.margin_call_ltv_pct
                  ) ? 20 : 0)
                : null
            }
            projectedDelta={
              stressResult !== null && activeClient?.urgencyScore !== undefined
                ? (stressResult.ltv_stress?.facilities?.some(
                    (f) => f.scenario_ltv_pct !== null && f.scenario_ltv_pct >= f.margin_call_ltv_pct
                  ) ? 20 : 0)
                : null
            }
            onScrollTo={(anchor) => {
              if (!anchor) return;
              const el = document.getElementById(anchor);
              if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }}
          />
        )}

        {/* ------------------------------------------------------------------
            ScenarioPicker — named scenario dropdown + shock table editor (Req 2)
        ------------------------------------------------------------------ */}
        <ScenarioPicker
          selectedScenario={scenarioConfig}
          onScenarioChange={handleScenarioChange}
          onRun={mode === 'client' ? handleRun : handleRunBookScenario}
          isLoading={mode === 'client' ? isRunning : isRunningBookScenario}
        />

        {/* ------------------------------------------------------------------
            ScenarioNarrativeCard — AI narrative above stress panels (Req 2.3, 8.2)
        ------------------------------------------------------------------ */}
        {mode === 'client' && (
          <ScenarioNarrativeCard
            narrative={stressResult?.narrative ?? null}
            isLoading={isRunning}
          />
        )}

        {/* ------------------------------------------------------------------
            CLIENT MODE: five stress panels
            These are placeholder divs; full panel components are created in
            later tasks (MacroShockPanel, LombardLTVPanel, LookThroughPanel,
            LiquidityCoveragePanel, RMActionPanel).
        ------------------------------------------------------------------ */}
        {mode === 'client' && (
          <>
            {/* Panel 1 — Macro Shock Simulator (Req 3) */}
            <MacroShockPanel
              result={stressResult?.macro_shock ?? null}
              isLoading={isRunning}
              error={macroShockError}
              onRetry={handleRun}
            />

            {/* Panel 2 — Lombard LTV Stress Test (Req 4) */}
            <LombardLTVPanel
              result={stressResult?.ltv_stress ?? null}
              isLoading={isRunning}
              error={macroShockError}
              onRetry={handleRun}
              hasRun={stressResult !== null}
            />

            {/* Panel 3 — Look-Through Concentration (Req 5) */}
            <LookThroughPanel
              result={lookThroughResult}
              isLoading={isLoadingLookThrough}
              error={null}
              onRetry={() => {
                if (!clientId) return;
                setIsLoadingLookThrough(true);
                getLookThrough(clientId)
                  .then(setLookThroughResult)
                  .catch((err: unknown) => console.error('Look-through retry failed:', err))
                  .finally(() => setIsLoadingLookThrough(false));
              }}
              hasRun={lookThroughResult !== null}
            />

            {/* Panel 4 — Liquidity Coverage Test (Req 6) */}
            <LiquidityCoveragePanel
              result={liquidityResult}
              isLoading={isLoadingLiquidity}
              error={null}
              onRetry={() => {
                if (!clientId) return;
                setIsLoadingLiquidity(true);
                getLiquidity(clientId)
                  .then(setLiquidityResult)
                  .catch((err: unknown) => console.error('Liquidity retry failed:', err))
                  .finally(() => setIsLoadingLiquidity(false));
              }}
              hasRun={liquidityResult !== null}
            />

            {/* Panel 5 — RM Recommendations (Req 7) */}
            <RMActionPanel
              recommendations={stressResult?.recommendations ?? null}
              isLoading={isRunning}
              error={macroShockError}
              onRetry={handleRun}
              hasRun={stressResult !== null}
            />

            {/* Generate Call Script button — visible only after a stress run (Req 10.1) */}
            {stressResult !== null && (
              <div className="flex justify-end">
                <button
                  onClick={handleOpenCallScript}
                  className="px-4 py-2 text-[11.5px] font-medium text-[#faf9f6] bg-[#2a2520] hover:bg-[#121212] transition-colors"
                  aria-label="Generate call script for this stress result"
                >
                  Generate Call Script
                </button>
              </div>
            )}

            {/* Panel 6 — Audit Trail (Req 9) */}
            <AuditTrailPanel
              resultId={stressResult?.result_id ?? null}
              clientId={clientId ?? ''}
              scenarioName={stressResult?.scenario?.label ?? scenarioConfig.label}
              auditEntries={auditEntries}
              onMarkReviewed={handleMarkReviewed}
              onMarkActioned={handleMarkActioned}
            />
          </>
        )}

        {/* ------------------------------------------------------------------
            BOOK-WIDE MODE: leaderboard (Req 12)
        ------------------------------------------------------------------ */}
        {mode === 'book-wide' && (
          <>
            {isRunningBookScenario && (
              <div
                data-testid="book-scenario-leaderboard"
                className="bg-white border border-[#e8e5e0] p-6 shadow-2xs space-y-3"
              >
                <div className="flex items-baseline gap-3 border-b border-[#e8e5e0] pb-3">
                  <span className="text-[10px] uppercase tracking-[0.14em] font-medium text-[#767676] font-mono">
                    SECTION 02 · SCENARIO IMPACT LEADERBOARD
                  </span>
                </div>
                <div className="space-y-2 animate-pulse">
                  {[...Array(6)].map((_, i) => (
                    <div key={i} className={`h-4 bg-[#f4f3f0] rounded ${i === 5 ? 'w-3/4' : 'w-full'}`} />
                  ))}
                </div>
              </div>
            )}

            {!isRunningBookScenario && !bookScenarioResult && (
              <div
                data-testid="book-scenario-leaderboard"
                className="bg-white border border-[#e8e5e0] p-6 shadow-2xs space-y-3"
              >
                <div className="flex items-baseline gap-3 border-b border-[#e8e5e0] pb-3">
                  <span className="text-[10px] uppercase tracking-[0.14em] font-medium text-[#767676] font-mono">
                    SECTION 02 · SCENARIO IMPACT LEADERBOARD
                  </span>
                </div>
                <p className="text-[12.5px] text-[#888888]">
                  Select a scenario and click &ldquo;Run Book Scenario&rdquo; to see the impact leaderboard.
                </p>
              </div>
            )}

            {!isRunningBookScenario && bookScenarioResult && (
              <div data-testid="book-scenario-leaderboard">
                <BookScenarioLeaderboard
                  result={bookScenarioResult}
                  onDrillDown={(clientId) => onSelectClient(clientId)}
                />
              </div>
            )}
          </>
        )}
      </div>

      {/* ── CallScriptModal — rendered at root outside the max-w-6xl container (Req 10) */}
      {isCallScriptModalOpen && stressResult !== null && (
        <CallScriptModal
          isOpen={isCallScriptModalOpen}
          onClose={handleCloseCallScript}
          stressResult={stressResult}
          clientName={activeClient?.name ?? clientId ?? 'Client'}
          riskProfile={activeClient?.riskLevel ?? 'MEDIUM'}
          onAuditEntry={handleCallScriptAudit}
        />
      )}
    </div>
  );
};
