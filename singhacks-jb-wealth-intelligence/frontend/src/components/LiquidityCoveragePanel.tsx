/**
 * LiquidityCoveragePanel — Liquidity Coverage Test results panel.
 *
 * Displays the LCR ratio, total 60-day obligations, Tier-1 liquid value,
 * a SHORTFALL/COVERED status banner, a ranked sell-to-cover recommendation
 * list, and life-event flag cards when present.
 *
 * Requirements: 6.3, 6.4, 6.5, 6.6, 6.7, 13.4
 */

import React from 'react';
import { AlertTriangle, RefreshCw, Shield, Droplets } from 'lucide-react';
import type { LiquidityResult, SellToCoverItem, LifeEventFlag } from '../types/stressWorkbench';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface LiquidityCoveragePanelProps {
  result: LiquidityResult | null;
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
  /** Whether a stress run or background fetch has been attempted. */
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

/** Format an LCR value to 2 decimal places, or "N/A" when null. */
function formatLCR(lcr: number | null): string {
  if (lcr === null) return 'N/A';
  return lcr.toFixed(2);
}

/** Format a date string for display. */
function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

// ---------------------------------------------------------------------------
// SummaryMetrics — 3-col strip
// ---------------------------------------------------------------------------

const SummaryMetrics: React.FC<{ result: LiquidityResult }> = ({ result }) => {
  const metrics = [
    {
      label: 'LCR Ratio',
      value: formatLCR(result.lcr),
      colorClass: result.lcr === null
        ? 'text-[#aaaaaa]'
        : result.lcr >= 1
        ? 'text-[#2c6e6a]'
        : 'text-[#7A1C28]',
    },
    {
      label: 'Total 60d Obligations',
      value: formatUSD(result.total_60d_obligations_usd),
      colorClass: 'text-[#2a2520]',
    },
    {
      label: 'Tier-1 Liquid Value',
      value: formatUSD(result.tier1_liquid_value_usd),
      colorClass: 'text-[#2a2520]',
    },
  ];

  return (
    <div
      data-testid="liquidity-summary-metrics"
      className="grid grid-cols-1 sm:grid-cols-3 gap-4"
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

// ---------------------------------------------------------------------------
// StatusBanner — SHORTFALL or COVERED
// ---------------------------------------------------------------------------

const StatusBanner: React.FC<{ result: LiquidityResult }> = ({ result }) => {
  const isShortfall = result.status === 'SHORTFALL';

  if (isShortfall) {
    return (
      <div
        data-testid="liquidity-status-banner-shortfall"
        className="flex items-center gap-3 bg-[#fcf5f5] border border-[#eed6d9] px-4 py-3"
        role="alert"
        aria-label="Liquidity shortfall detected"
      >
        <AlertTriangle className="w-4 h-4 text-[#7A1C28] flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-baseline gap-3">
            <span className="text-[12px] uppercase tracking-[0.14em] font-mono font-semibold text-[#7A1C28]">
              SHORTFALL
            </span>
            <span className="text-[12.5px] font-mono text-[#7A1C28]">
              Gap: {formatUSD(Math.abs(result.surplus_or_gap_usd))}
            </span>
          </div>
          <p className="text-[11.5px] text-[#9e3a47] mt-0.5">
            Tier-1 liquid assets are insufficient to cover 60-day obligations.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="liquidity-status-banner-covered"
      className="flex items-center gap-3 bg-[#f0faf9] border border-[#c0e8e4] px-4 py-3"
      role="status"
      aria-label="Liquidity covered"
    >
      <Shield className="w-4 h-4 text-[#2c6e6a] flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-baseline gap-3">
          <span className="text-[12px] uppercase tracking-[0.14em] font-mono font-semibold text-[#2c6e6a]">
            COVERED
          </span>
          <span className="text-[12.5px] font-mono text-[#2c6e6a]">
            Surplus: {formatUSD(result.surplus_or_gap_usd)}
          </span>
        </div>
        <p className="text-[11.5px] text-[#3a8a84] mt-0.5">
          Tier-1 liquid assets are sufficient to cover 60-day obligations.
        </p>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// SellToCoverList
// ---------------------------------------------------------------------------

const SellToCoverRow: React.FC<{ item: SellToCoverItem; index: number }> = ({
  item,
  index,
}) => {
  const pnlIsNegative = item.unrealised_pnl_usd < 0;
  const pnlIsPositive = item.unrealised_pnl_usd > 0;
  const pnlColorClass = pnlIsNegative
    ? 'text-[#7A1C28]'
    : pnlIsPositive
    ? 'text-[#2c6e6a]'
    : 'text-[#555555]';

  return (
    <tr
      data-testid={`sell-to-cover-row-${index}`}
      className="border-t border-[#f0ede8]"
    >
      {/* Rank */}
      <td className="py-2.5 pr-3 text-left w-8">
        <span className="text-[11.5px] font-mono text-[#aaaaaa] tabular-nums">
          {item.rank}
        </span>
      </td>

      {/* Holding name */}
      <td className="py-2.5 pr-4 text-left">
        <span className="text-[12.5px] text-[#2a2520] font-medium leading-tight">
          {item.instrument_name}
        </span>
      </td>

      {/* Current value */}
      <td className="py-2.5 pr-4 text-right">
        <span className="text-[12px] font-mono tabular-nums text-[#2a2520]">
          {formatUSD(item.current_value_usd)}
        </span>
      </td>

      {/* Unrealised P&L */}
      <td className="py-2.5 pr-4 text-right">
        <span className={`text-[12px] font-mono tabular-nums font-medium ${pnlColorClass}`}>
          {pnlIsPositive ? '+' : ''}
          {formatUSD(item.unrealised_pnl_usd)}
        </span>
      </td>

      {/* Estimated settle days */}
      <td className="py-2.5 text-right">
        <span className="text-[12px] font-mono tabular-nums text-[#555555]">
          {item.estimated_settle_days}d
        </span>
      </td>
    </tr>
  );
};

const SellToCoverList: React.FC<{ items: SellToCoverItem[] }> = ({ items }) => {
  const top5 = items.slice(0, 5);

  return (
    <div data-testid="sell-to-cover-list" className="space-y-3">
      {/* Sub-header */}
      <span className="text-[10px] uppercase tracking-[0.14em] font-medium text-[#767676] font-mono">
        Sell-to-Cover Recommendations
      </span>

      {top5.length === 0 ? (
        <p className="text-[12.5px] text-[#888888] py-2">
          No sell-to-cover recommendations.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[580px] border-collapse">
            <thead>
              <tr>
                {[
                  { label: '#', align: 'text-left pr-3 w-8' },
                  { label: 'Holding', align: 'text-left pr-4' },
                  { label: 'Current Value', align: 'text-right pr-4' },
                  { label: 'Unrealised P&L', align: 'text-right pr-4' },
                  { label: 'Settle', align: 'text-right' },
                ].map(({ label, align }) => (
                  <th
                    key={label}
                    className={`pb-2 text-[10px] uppercase tracking-[0.12em] font-medium text-[#767676] font-mono border-b border-[#e8e5e0] ${align}`}
                  >
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {top5.map((item, i) => (
                <SellToCoverRow key={item.rank} item={item} index={i} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// LifeEventFlagCard
// ---------------------------------------------------------------------------

const LifeEventFlagCard: React.FC<{ flag: LifeEventFlag; index: number }> = ({
  flag,
  index,
}) => {
  const isCovered = flag.coverage_ratio >= 1;

  return (
    <div
      data-testid={`life-event-flag-card-${index}`}
      className="bg-[#fdf8f0] border border-[#f4e4cc] p-3 space-y-1.5"
    >
      {/* Header row */}
      <div className="flex flex-wrap items-start justify-between gap-2">
        <span className="text-[12.5px] font-semibold text-[#2a2520] leading-snug">
          {flag.description}
        </span>
        <span
          className={`inline-flex items-center px-2 py-0.5 text-[9.5px] uppercase tracking-widest font-mono font-semibold leading-none whitespace-nowrap ${
            isCovered
              ? 'bg-[#f0faf9] text-[#2c6e6a] border border-[#c0e8e4]'
              : 'bg-[#fcf5f5] text-[#7A1C28] border border-[#eed6d9]'
          }`}
          aria-label={`Coverage status: ${isCovered ? 'covered' : 'shortfall'}`}
        >
          {isCovered ? 'COVERED' : 'SHORTFALL'}
        </span>
      </div>

      {/* Metrics row */}
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        <span className="text-[11px] font-mono text-[#767676]">
          Due:{' '}
          <span className="text-[#2a2520] font-medium">{formatDate(flag.due_date)}</span>
        </span>
        <span className="text-[11px] font-mono text-[#767676]">
          Amount:{' '}
          <span className="text-[#2a2520] font-medium">{formatUSD(flag.amount_usd)}</span>
        </span>
        <span className="text-[11px] font-mono text-[#767676]">
          Coverage:{' '}
          <span
            className={`font-medium ${isCovered ? 'text-[#2c6e6a]' : 'text-[#7A1C28]'}`}
          >
            {flag.coverage_ratio.toFixed(2)}×
          </span>
        </span>
      </div>

      {/* Life-stage note */}
      {flag.life_stage_note && (
        <p className="text-[11.5px] text-[#5a4a35] leading-relaxed">
          {flag.life_stage_note}
        </p>
      )}
    </div>
  );
};

const LifeEventFlags: React.FC<{ flags: LifeEventFlag[] }> = ({ flags }) => (
  <div data-testid="life-event-flags" className="space-y-3">
    {/* Sub-header */}
    <div className="flex items-center gap-2">
      <Droplets className="w-3.5 h-3.5 text-[#9E6B20] flex-shrink-0" />
      <span className="text-[10px] uppercase tracking-[0.14em] font-medium text-[#9E6B20] font-mono">
        Life Event Flags
      </span>
      <span className="text-[10px] font-mono text-[#9E6B20] opacity-70">
        · {flags.length} flag{flags.length !== 1 ? 's' : ''}
      </span>
    </div>

    {/* Cards */}
    <div className="space-y-2">
      {flags.map((flag, i) => (
        <LifeEventFlagCard key={i} flag={flag} index={i} />
      ))}
    </div>
  </div>
);

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

const LiquiditySkeleton: React.FC = () => (
  <div
    data-testid="liquidity-coverage-skeleton"
    className="space-y-5"
    aria-busy="true"
    aria-label="Loading liquidity coverage results"
  >
    {/* Summary metrics skeleton */}
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 animate-pulse" role="presentation">
      {[...Array(3)].map((_, i) => (
        <div key={i} className="flex flex-col gap-2">
          <div className="h-2.5 bg-[#f4f3f0] rounded w-3/4" />
          <div className="h-4 bg-[#f4f3f0] rounded w-full" />
        </div>
      ))}
    </div>

    {/* Status banner skeleton */}
    <div className="animate-pulse" role="presentation">
      <div className="h-14 bg-[#f4f3f0] rounded w-full" />
    </div>

    {/* Sell-to-cover list skeleton */}
    <div className="space-y-2 animate-pulse" role="presentation">
      <div className="h-2.5 bg-[#f4f3f0] rounded w-40" />
      <div className="h-3 bg-[#f4f3f0] rounded w-full" />
      {[...Array(4)].map((_, i) => (
        <div key={i} className={`h-9 bg-[#f4f3f0] rounded ${i === 3 ? 'w-3/4' : 'w-full'}`} />
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
    data-testid="liquidity-coverage-error-banner"
    className="flex items-start gap-3 bg-amber-50 border border-amber-200 text-amber-900 px-4 py-3"
    role="alert"
  >
    <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0 text-amber-600" />
    <div className="flex-1 min-w-0">
      <p className="text-[12.5px] font-medium">Failed to load liquidity coverage results</p>
      <p className="text-[11.5px] mt-0.5 text-amber-800 break-words">{message}</p>
    </div>
    <button
      onClick={onRetry}
      className="flex items-center gap-1.5 text-[11.5px] font-medium text-amber-800 hover:text-amber-900 underline underline-offset-2 flex-shrink-0"
      aria-label="Retry loading liquidity coverage results"
    >
      <RefreshCw className="w-3 h-3" />
      Retry
    </button>
  </div>
);

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export const LiquidityCoveragePanel: React.FC<LiquidityCoveragePanelProps> = ({
  result,
  isLoading,
  error,
  onRetry,
  hasRun,
}) => {
  return (
    <div
      data-testid="liquidity-coverage-panel"
      className="bg-white border border-[#e8e5e0] p-6 shadow-2xs space-y-5"
    >
      {/* Section header */}
      <div className="flex items-baseline gap-3 border-b border-[#e8e5e0] pb-3">
        <span className="text-[10px] uppercase tracking-[0.14em] font-medium text-[#767676] font-mono">
          SECTION 04 · LIQUIDITY COVERAGE TEST
        </span>
      </div>

      {/* Error banner */}
      {error && !isLoading && <ErrorBanner message={error} onRetry={onRetry} />}

      {/* Loading skeleton */}
      {isLoading && <LiquiditySkeleton />}

      {/* Empty / pre-run state */}
      {!isLoading && !error && !result && (
        <p className="text-[12.5px] text-[#888888]">
          {hasRun
            ? 'Run a scenario above to see liquidity coverage results.'
            : 'Liquidity coverage data will load automatically when a client is selected.'}
        </p>
      )}

      {/* Results */}
      {!isLoading && result && (
        <div className="space-y-6">
          {/* Summary metrics strip */}
          <SummaryMetrics result={result} />

          {/* Status banner */}
          <StatusBanner result={result} />

          {/* Sell-to-cover list */}
          <SellToCoverList items={result.sell_to_cover} />

          {/* Life-event flag cards — only when non-empty */}
          {result.life_event_flags.length > 0 && (
            <LifeEventFlags flags={result.life_event_flags} />
          )}
        </div>
      )}
    </div>
  );
};

export default LiquidityCoveragePanel;
