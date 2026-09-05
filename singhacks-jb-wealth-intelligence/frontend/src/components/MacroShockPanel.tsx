/**
 * MacroShockPanel — displays macro shock simulation results.
 *
 * Shows summary metrics (total current value, total shocked value, net dollar
 * impact, net % change) and a top-10 holding breakdown table. Look-through
 * rows are highlighted with a subtle indicator. Skeleton placeholders are
 * shown while loading; an error banner with retry is shown on failure.
 *
 * Requirements: 3.3, 3.4, 14.1, 14.2, 14.5, 14.6
 */

import React from 'react';
import { RefreshCw, AlertTriangle } from 'lucide-react';
import type { MacroShockResult, HoldingImpact } from '../types/stressWorkbench';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface MacroShockPanelProps {
  result: MacroShockResult | null;
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
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

/** Format a percentage change with sign and 2 decimal places. */
function formatPct(value: number): string {
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** Four-metric summary strip. */
const SummaryMetrics: React.FC<{ result: MacroShockResult }> = ({ result }) => {
  const isNegative = result.net_dollar_impact_usd < 0;
  const isPositive = result.net_dollar_impact_usd > 0;

  const impactColorClass = isNegative
    ? 'text-[#7A1C28]'
    : isPositive
    ? 'text-[#2c6e6a]'
    : 'text-[#2a2520]';

  const pctColorClass = isNegative
    ? 'text-[#7A1C28]'
    : isPositive
    ? 'text-[#2c6e6a]'
    : 'text-[#2a2520]';

  const metrics = [
    {
      label: 'Total Current Value',
      value: formatUSD(result.total_current_value_usd),
      colorClass: 'text-[#2a2520]',
    },
    {
      label: 'Total Shocked Value',
      value: formatUSD(result.total_shocked_value_usd),
      colorClass: 'text-[#2a2520]',
    },
    {
      label: 'Net Dollar Impact',
      value: formatUSD(result.net_dollar_impact_usd),
      colorClass: impactColorClass,
    },
    {
      label: 'Net % Change',
      value: formatPct(result.net_pct_change),
      colorClass: pctColorClass,
    },
  ];

  return (
    <div
      data-testid="macro-shock-summary-metrics"
      className="grid grid-cols-2 sm:grid-cols-4 gap-4"
    >
      {metrics.map(({ label, value, colorClass }) => (
        <div key={label} className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-[0.12em] font-medium text-[#767676] font-mono">
            {label}
          </span>
          <span className={`text-[13px] font-mono font-medium tabular-nums ${colorClass}`}>
            {value}
          </span>
        </div>
      ))}
    </div>
  );
};

/** Single row in the holdings table. */
const HoldingRow: React.FC<{ holding: HoldingImpact; index: number }> = ({
  holding,
  index,
}) => {
  const isNegative = holding.dollar_change_usd < 0;
  const isPositive = holding.dollar_change_usd > 0;

  const changeColorClass = isNegative
    ? 'text-[#7A1C28]'
    : isPositive
    ? 'text-[#2c6e6a]'
    : 'text-[#555555]';

  return (
    <tr
      data-testid={`holding-row-${index}`}
      className={`border-t border-[#f0ede8] ${holding.look_through_applied ? 'bg-[#fdfcfb]' : ''}`}
    >
      {/* Name + look-through badge */}
      <td className="py-2.5 pr-4 text-left">
        <div className="flex items-center gap-2">
          <span className="text-[12.5px] text-[#2a2520] font-medium leading-tight">
            {holding.instrument_name}
          </span>
          {holding.look_through_applied && (
            <span
              title="Look-through applied"
              className="inline-flex items-center px-1.5 py-0.5 text-[9px] uppercase tracking-wider font-mono font-medium bg-[#f0faf9] text-[#2c6e6a] border border-[#c0e8e4] rounded-sm leading-none"
            >
              LT
            </span>
          )}
        </div>
      </td>

      {/* Asset class */}
      <td className="py-2.5 pr-4 text-left">
        <span className="text-[11.5px] text-[#767676] font-mono">
          {holding.asset_class}
        </span>
      </td>

      {/* Current value */}
      <td className="py-2.5 pr-4 text-right">
        <span className="text-[12px] text-[#2a2520] font-mono tabular-nums">
          {formatUSD(holding.current_value_usd)}
        </span>
      </td>

      {/* Shocked value */}
      <td className="py-2.5 pr-4 text-right">
        <span className="text-[12px] text-[#2a2520] font-mono tabular-nums">
          {formatUSD(holding.shocked_value_usd)}
        </span>
      </td>

      {/* Dollar change */}
      <td className="py-2.5 text-right">
        <span className={`text-[12px] font-mono tabular-nums font-medium ${changeColorClass}`}>
          {formatUSD(holding.dollar_change_usd)}
        </span>
      </td>
    </tr>
  );
};

/** Top-10 holdings breakdown table. */
const HoldingsTable: React.FC<{ holdings: HoldingImpact[] }> = ({ holdings }) => {
  const top10 = holdings.slice(0, 10);

  return (
    <div data-testid="macro-shock-holdings-table" className="overflow-x-auto">
      <table className="w-full min-w-[640px] border-collapse">
        <thead>
          <tr>
            {['Name', 'Asset Class', 'Current Value', 'Shocked Value', 'Dollar Change'].map(
              (col) => (
                <th
                  key={col}
                  className={`pb-2 text-[10px] uppercase tracking-[0.12em] font-medium text-[#767676] font-mono border-b border-[#e8e5e0] ${
                    col === 'Name' || col === 'Asset Class' ? 'text-left pr-4' : 'text-right'
                  } ${col === 'Name' ? '' : col === 'Asset Class' ? 'pr-4' : col === 'Dollar Change' ? '' : 'pr-4'}`}
                >
                  {col}
                </th>
              )
            )}
          </tr>
        </thead>
        <tbody>
          {top10.map((holding, i) => (
            <HoldingRow key={holding.instrument_id} holding={holding} index={i} />
          ))}
        </tbody>
      </table>
      {holdings.length === 0 && (
        <p className="text-[12.5px] text-[#888888] py-4 text-center">
          No holdings data available.
        </p>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

const MacroShockSkeleton: React.FC = () => (
  <div
    data-testid="macro-shock-skeleton"
    className="space-y-6"
    aria-busy="true"
    aria-label="Loading macro shock results"
  >
    {/* Summary metrics skeleton */}
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 animate-pulse" role="presentation">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="flex flex-col gap-2">
          <div className="h-2.5 bg-[#f4f3f0] rounded w-3/4" />
          <div className="h-4 bg-[#f4f3f0] rounded w-full" />
        </div>
      ))}
    </div>

    {/* Table skeleton */}
    <div className="space-y-2 animate-pulse" role="presentation">
      <div className="h-3 bg-[#f4f3f0] rounded w-full" />
      {[...Array(5)].map((_, i) => (
        <div key={i} className={`h-8 bg-[#f4f3f0] rounded ${i === 4 ? 'w-3/4' : 'w-full'}`} />
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
    data-testid="macro-shock-error-banner"
    className="flex items-start gap-3 bg-amber-50 border border-amber-200 text-amber-900 rounded px-4 py-3"
    role="alert"
  >
    <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0 text-amber-600" />
    <div className="flex-1 min-w-0">
      <p className="text-[12.5px] font-medium">Failed to load macro shock results</p>
      <p className="text-[11.5px] mt-0.5 text-amber-800 break-words">{message}</p>
    </div>
    <button
      onClick={onRetry}
      className="flex items-center gap-1.5 text-[11.5px] font-medium text-amber-800 hover:text-amber-900 underline underline-offset-2 flex-shrink-0"
      aria-label="Retry loading macro shock results"
    >
      <RefreshCw className="w-3 h-3" />
      Retry
    </button>
  </div>
);

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export const MacroShockPanel: React.FC<MacroShockPanelProps> = ({
  result,
  isLoading,
  error,
  onRetry,
}) => {
  return (
    <div
      data-testid="macro-shock-panel"
      className="bg-white border border-[#e8e5e0] p-6 shadow-2xs space-y-5"
    >
      {/* Section header */}
      <div className="flex items-baseline gap-3 border-b border-[#e8e5e0] pb-3">
        <span className="text-[10px] uppercase tracking-[0.14em] font-medium text-[#767676] font-mono">
          SECTION 01 · MACRO SHOCK SIMULATOR
        </span>
      </div>

      {/* Error banner */}
      {error && !isLoading && (
        <ErrorBanner message={error} onRetry={onRetry} />
      )}

      {/* Loading skeleton */}
      {isLoading && <MacroShockSkeleton />}

      {/* Empty / pre-run state */}
      {!isLoading && !error && !result && (
        <p className="text-[12.5px] text-[#888888]">
          Run a scenario above to see macro shock results.
        </p>
      )}

      {/* Results */}
      {!isLoading && result && (
        <div className="space-y-6">
          <SummaryMetrics result={result} />
          <HoldingsTable holdings={result.top_impacted_holdings} />
        </div>
      )}
    </div>
  );
};

export default MacroShockPanel;
