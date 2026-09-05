/**
 * LombardLTVPanel — Lombard LTV Stress Test results panel.
 *
 * Displays a per-facility stress table showing current LTV, LTV at
 * −10%/−20%/−30% haircut levels, scenario LTV (when available), and the
 * margin call threshold. A MARGIN CALL WARNING badge is rendered in any
 * cell where the stressed LTV meets or exceeds the margin call threshold.
 * Dollar headroom rows are displayed below each facility's stress table.
 *
 * Edge cases:
 *  - Empty facilities array → "No Lombard facility on record" message.
 *  - `ltv = null` (zero lending value guard) → "N/A" in that cell.
 *
 * Requirements: 4.4, 4.5, 4.6, 4.7, 14.3
 */

import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import type { LTVStressResult, LTVFacilityRow } from '../types/stressWorkbench';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface LombardLTVPanelProps {
  result: LTVStressResult | null;
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
  /** Whether a full stress run has already been executed (used for empty-state copy). */
  hasRun: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Format a number as USD with thousand separators and 2 decimal places. */
function formatUSD(value: number): string {
  return (
    'USD ' +
    value.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  );
}

/** Render an LTV value as a percentage string or "N/A" when null. */
function renderLTV(ltv: number | null): string {
  if (ltv === null) return 'N/A';
  return ltv.toFixed(2) + '%';
}

/** Returns true when a stressed LTV warrants a margin call warning badge. */
function isMarginCallWarning(ltv: number | null, threshold: number): boolean {
  return ltv !== null && ltv >= threshold;
}

// ---------------------------------------------------------------------------
// MarginCallBadge
// ---------------------------------------------------------------------------

const MarginCallBadge: React.FC = () => (
  <span
    className="inline-flex items-center gap-1 px-2 py-0.5 text-[9.5px] uppercase tracking-widest font-mono font-semibold bg-[#fcf5f5] text-[#7A1C28] border border-[#eed6d9] leading-none whitespace-nowrap"
    role="alert"
    aria-label="Margin call warning"
  >
    <AlertTriangle className="w-2.5 h-2.5 flex-shrink-0" />
    MARGIN CALL WARNING
  </span>
);

// ---------------------------------------------------------------------------
// LTVCell — renders a single stress LTV cell, optionally with warning badge
// ---------------------------------------------------------------------------

interface LTVCellProps {
  ltv: number | null;
  threshold: number;
}

const LTVCell: React.FC<LTVCellProps> = ({ ltv, threshold }) => {
  const warn = isMarginCallWarning(ltv, threshold);
  return (
    <td className={`py-2.5 px-3 text-right align-top ${warn ? 'bg-[#fcf5f5]' : ''}`}>
      <div className="flex flex-col items-end gap-1">
        <span
          className={`text-[12px] font-mono tabular-nums font-medium ${
            warn ? 'text-[#7A1C28]' : ltv === null ? 'text-[#aaaaaa]' : 'text-[#2a2520]'
          }`}
        >
          {renderLTV(ltv)}
        </span>
        {warn && <MarginCallBadge />}
      </div>
    </td>
  );
};

// ---------------------------------------------------------------------------
// FacilityTable — stress table + headroom row for a single Lombard facility
// ---------------------------------------------------------------------------

const FacilityTable: React.FC<{ facility: LTVFacilityRow; index: number }> = ({
  facility,
  index,
}) => {
  const columns: Array<{
    label: string;
    ltv: number | null;
    headroom: number;
  }> = [
    {
      label: '−10%',
      ltv: facility.ltv_at_minus_10_pct,
      headroom: facility.headroom_at_minus_10_usd,
    },
    {
      label: '−20%',
      ltv: facility.ltv_at_minus_20_pct,
      headroom: facility.headroom_at_minus_20_usd,
    },
    {
      label: '−30%',
      ltv: facility.ltv_at_minus_30_pct,
      headroom: facility.headroom_at_minus_30_usd,
    },
  ];

  return (
    <div
      data-testid={`facility-table-${facility.facility_id}`}
      className={`space-y-3 ${index > 0 ? 'border-t border-[#e8e5e0] pt-5 mt-5' : ''}`}
    >
      {/* Facility header */}
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-[12px] font-semibold text-[#2a2520]">
          {facility.facility_id}
        </span>
        <span className="text-[11px] text-[#767676] font-mono uppercase tracking-wide">
          {facility.facility_type}
        </span>
        <span className="text-[11.5px] text-[#555555] font-mono">
          Drawn: {formatUSD(facility.drawn_usd)}
        </span>
        <span className="text-[11.5px] text-[#555555] font-mono">
          MC Threshold: {facility.margin_call_ltv_pct.toFixed(2)}%
        </span>
      </div>

      {/* Stress table */}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[600px] border-collapse border border-[#e8e5e0]">
          <thead>
            <tr className="bg-[#f8f6f3]">
              <th className="py-2 px-3 text-left text-[10px] uppercase tracking-[0.12em] font-medium text-[#767676] font-mono border-b border-[#e8e5e0]">
                LTV Metric
              </th>
              <th className="py-2 px-3 text-right text-[10px] uppercase tracking-[0.12em] font-medium text-[#767676] font-mono border-b border-[#e8e5e0]">
                Current
              </th>
              {columns.map((col) => (
                <th
                  key={col.label}
                  className="py-2 px-3 text-right text-[10px] uppercase tracking-[0.12em] font-medium text-[#767676] font-mono border-b border-[#e8e5e0]"
                >
                  Haircut {col.label}
                </th>
              ))}
              {facility.scenario_ltv_pct !== null && (
                <th className="py-2 px-3 text-right text-[10px] uppercase tracking-[0.12em] font-medium text-[#767676] font-mono border-b border-[#e8e5e0]">
                  Scenario
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {/* LTV row */}
            <tr className="border-t border-[#f0ede8]">
              <td className="py-2.5 px-3 text-left text-[11.5px] text-[#767676] font-mono uppercase tracking-wide border-r border-[#f0ede8]">
                LTV Ratio
              </td>

              {/* Current LTV — no warning badge (baseline) */}
              <td className="py-2.5 px-3 text-right">
                <span className="text-[12px] font-mono tabular-nums font-medium text-[#2a2520]">
                  {facility.current_ltv_pct.toFixed(2)}%
                </span>
              </td>

              {/* Haircut LTV columns */}
              {columns.map((col) => (
                <LTVCell
                  key={col.label}
                  ltv={col.ltv}
                  threshold={facility.margin_call_ltv_pct}
                />
              ))}

              {/* Scenario LTV column (conditional) */}
              {facility.scenario_ltv_pct !== null && (
                <LTVCell
                  ltv={facility.scenario_ltv_pct}
                  threshold={facility.margin_call_ltv_pct}
                />
              )}
            </tr>

            {/* Dollar headroom row */}
            <tr className="border-t border-[#f0ede8] bg-[#fdfcfb]">
              <td className="py-2.5 px-3 text-left text-[11.5px] text-[#767676] font-mono uppercase tracking-wide border-r border-[#f0ede8]">
                Headroom (USD)
              </td>

              {/* No headroom for "current" baseline column */}
              <td className="py-2.5 px-3 text-right">
                <span className="text-[12px] text-[#aaaaaa] font-mono">—</span>
              </td>

              {/* Headroom per haircut level */}
              {columns.map((col) => {
                const isNegative = col.headroom < 0;
                return (
                  <td key={col.label} className="py-2.5 px-3 text-right">
                    <span
                      className={`text-[12px] font-mono tabular-nums font-medium ${
                        isNegative ? 'text-[#7A1C28]' : 'text-[#2c6e6a]'
                      }`}
                    >
                      {formatUSD(col.headroom)}
                    </span>
                  </td>
                );
              })}

              {/* Scenario headroom column (conditional) */}
              {facility.scenario_ltv_pct !== null && (
                <td className="py-2.5 px-3 text-right">
                  {facility.scenario_headroom_usd !== null ? (
                    <span
                      className={`text-[12px] font-mono tabular-nums font-medium ${
                        facility.scenario_headroom_usd < 0 ? 'text-[#7A1C28]' : 'text-[#2c6e6a]'
                      }`}
                    >
                      {formatUSD(facility.scenario_headroom_usd)}
                    </span>
                  ) : (
                    <span className="text-[12px] text-[#aaaaaa] font-mono">—</span>
                  )}
                </td>
              )}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

const LombardLTVSkeleton: React.FC = () => (
  <div
    data-testid="lombard-ltv-skeleton"
    className="space-y-4"
    aria-busy="true"
    aria-label="Loading LTV stress results"
  >
    <div className="animate-pulse space-y-3" role="presentation">
      {/* Facility header placeholder */}
      <div className="flex gap-3">
        <div className="h-3.5 bg-[#f4f3f0] rounded w-28" />
        <div className="h-3.5 bg-[#f4f3f0] rounded w-20" />
        <div className="h-3.5 bg-[#f4f3f0] rounded w-32" />
      </div>
      {/* Table rows placeholder */}
      {[...Array(3)].map((_, i) => (
        <div key={i} className={`h-8 bg-[#f4f3f0] rounded ${i === 2 ? 'w-3/4' : 'w-full'}`} />
      ))}
    </div>
  </div>
);

// ---------------------------------------------------------------------------
// Error banner
// ---------------------------------------------------------------------------

const ErrorBanner: React.FC<{ message: string; onRetry: () => void }> = ({
  message,
  onRetry,
}) => (
  <div
    data-testid="lombard-ltv-error-banner"
    className="flex items-start gap-3 bg-amber-50 border border-amber-200 text-amber-900 px-4 py-3"
    role="alert"
  >
    <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0 text-amber-600" />
    <div className="flex-1 min-w-0">
      <p className="text-[12.5px] font-medium">Failed to load LTV stress results</p>
      <p className="text-[11.5px] mt-0.5 text-amber-800 break-words">{message}</p>
    </div>
    <button
      onClick={onRetry}
      className="flex items-center gap-1.5 text-[11.5px] font-medium text-amber-800 hover:text-amber-900 underline underline-offset-2 flex-shrink-0"
      aria-label="Retry loading LTV stress results"
    >
      <RefreshCw className="w-3 h-3" />
      Retry
    </button>
  </div>
);

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export const LombardLTVPanel: React.FC<LombardLTVPanelProps> = ({
  result,
  isLoading,
  error,
  onRetry,
  hasRun,
}) => {
  return (
    <div
      data-testid="lombard-ltv-panel"
      className="bg-white border border-[#e8e5e0] p-6 shadow-2xs space-y-5"
    >
      {/* Section header */}
      <div className="flex items-baseline gap-3 border-b border-[#e8e5e0] pb-3">
        <span className="text-[10px] uppercase tracking-[0.14em] font-medium text-[#767676] font-mono">
          SECTION 02 · LOMBARD LTV STRESS TEST
        </span>
      </div>

      {/* Error banner */}
      {error && !isLoading && <ErrorBanner message={error} onRetry={onRetry} />}

      {/* Loading skeleton */}
      {isLoading && <LombardLTVSkeleton />}

      {/* Empty / pre-run state */}
      {!isLoading && !error && !result && (
        <p className="text-[12.5px] text-[#888888]">
          {hasRun
            ? 'No LTV stress data returned for this client.'
            : 'Run a scenario above to see Lombard LTV stress results.'}
        </p>
      )}

      {/* No Lombard facility */}
      {!isLoading && result && result.facilities.length === 0 && (
        <div
          data-testid="lombard-ltv-empty"
          className="py-6 text-center text-[12.5px] text-[#888888] border border-dashed border-[#e8e5e0] bg-[#fdfcfb]"
        >
          No Lombard facility on record for this client.
        </div>
      )}

      {/* Facility tables */}
      {!isLoading && result && result.facilities.length > 0 && (
        <div className="space-y-0">
          {result.facilities.map((facility, index) => (
            <FacilityTable
              key={facility.facility_id}
              facility={facility}
              index={index}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default LombardLTVPanel;
