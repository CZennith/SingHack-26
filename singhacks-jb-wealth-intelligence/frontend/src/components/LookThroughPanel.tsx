/**
 * LookThroughPanel — Look-Through Concentration results panel.
 *
 * Renders a concentration heatmap table with Pre / Post look-through
 * percentages, mandate limit, and a status badge (BREACH / ELEVATED / OK /
 * NO_LIMIT). When `hidden_concentration_discoveries` is non-empty, a callout
 * card is rendered below the table calling out each hidden concentration.
 *
 * Requirements: 5.5, 5.6, 5.7, 5.8, 14.3
 */

import React from 'react';
import { AlertTriangle, RefreshCw, Eye } from 'lucide-react';
import type {
  LookThroughResult,
  ConcentrationRow,
  HiddenConcentration,
} from '../types/stressWorkbench';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface LookThroughPanelProps {
  result: LookThroughResult | null;
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
  /** Whether a full stress run (or background fetch) has already been attempted. */
  hasRun: boolean;
}

// ---------------------------------------------------------------------------
// Badge tokens per status (Requirements 14.3)
// ---------------------------------------------------------------------------

type ConcentrationStatus = ConcentrationRow['status'];

const STATUS_BADGE: Record<
  ConcentrationStatus,
  { label: string; className: string }
> = {
  BREACH: {
    label: 'BREACH',
    className:
      'bg-[#fcf5f5] text-[#7A1C28] border border-[#eed6d9]',
  },
  ELEVATED: {
    label: 'ELEVATED',
    className:
      'bg-[#fdf8f0] text-[#9E6B20] border border-[#f4e4cc]',
  },
  OK: {
    label: 'OK',
    className:
      'bg-[#f0faf9] text-[#2c6e6a] border border-[#c0e8e4]',
  },
  NO_LIMIT: {
    label: 'NO LIMIT',
    className:
      'bg-[#f4f3f0] text-[#767676] border border-[#e8e5e0]',
  },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Format a raw percentage number to two decimal places with a "%" suffix. */
function fmtPct(value: number): string {
  return value.toFixed(2) + '%';
}

/** Row background hint based on status — subtle tint for breaches/elevated. */
function rowBgClass(status: ConcentrationStatus): string {
  if (status === 'BREACH') return 'bg-[#fefcfc]';
  if (status === 'ELEVATED') return 'bg-[#fffdf9]';
  return '';
}

// ---------------------------------------------------------------------------
// StatusBadge
// ---------------------------------------------------------------------------

const StatusBadge: React.FC<{ status: ConcentrationStatus }> = ({ status }) => {
  const { label, className } = STATUS_BADGE[status];
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-[9.5px] uppercase tracking-widest font-mono font-semibold leading-none whitespace-nowrap ${className}`}
      aria-label={`Concentration status: ${label}`}
    >
      {label}
    </span>
  );
};

// ---------------------------------------------------------------------------
// ConcentrationTableRow
// ---------------------------------------------------------------------------

const ConcentrationTableRow: React.FC<{
  row: ConcentrationRow;
  index: number;
}> = ({ row, index }) => {
  const bg = rowBgClass(row.status);
  return (
    <tr
      data-testid={`concentration-row-${index}`}
      className={`border-t border-[#f0ede8] ${bg}`}
    >
      {/* Exposure name */}
      <td className="py-2.5 pr-4 text-left">
        <div className="flex flex-col gap-0.5">
          <span className="text-[12.5px] text-[#2a2520] font-medium leading-snug">
            {row.exposure_name}
          </span>
          <span className="text-[10.5px] text-[#888888] font-mono">
            {row.asset_class}
            {row.sector && row.sector !== row.asset_class ? ` · ${row.sector}` : ''}
          </span>
        </div>
      </td>

      {/* Pre look-through % */}
      <td className="py-2.5 pr-4 text-right">
        <span className="text-[12px] font-mono tabular-nums text-[#555555]">
          {fmtPct(row.pre_look_through_pct)}
        </span>
      </td>

      {/* Post look-through % */}
      <td className="py-2.5 pr-4 text-right">
        <span
          className={`text-[12px] font-mono tabular-nums font-medium ${
            row.status === 'BREACH'
              ? 'text-[#7A1C28]'
              : row.status === 'ELEVATED'
              ? 'text-[#9E6B20]'
              : 'text-[#2a2520]'
          }`}
        >
          {fmtPct(row.post_look_through_pct)}
        </span>
      </td>

      {/* Mandate limit % */}
      <td className="py-2.5 pr-4 text-right">
        <span className="text-[12px] font-mono tabular-nums text-[#555555]">
          {row.mandate_limit_pct !== null ? fmtPct(row.mandate_limit_pct) : '—'}
        </span>
      </td>

      {/* Status badge */}
      <td className="py-2.5 text-right">
        <StatusBadge status={row.status} />
      </td>
    </tr>
  );
};

// ---------------------------------------------------------------------------
// ConcentrationTable
// ---------------------------------------------------------------------------

const ConcentrationTable: React.FC<{ rows: ConcentrationRow[] }> = ({ rows }) => (
  <div data-testid="look-through-table" className="overflow-x-auto">
    <table className="w-full min-w-[640px] border-collapse">
      <thead>
        <tr>
          {[
            { label: 'Exposure', align: 'text-left pr-4' },
            { label: 'Pre Look-Through %', align: 'text-right pr-4' },
            { label: 'Post Look-Through %', align: 'text-right pr-4' },
            { label: 'Mandate Limit %', align: 'text-right pr-4' },
            { label: 'Status', align: 'text-right' },
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
        {rows.map((row, i) => (
          <ConcentrationTableRow key={`${row.exposure_name}-${i}`} row={row} index={i} />
        ))}
      </tbody>
    </table>
    {rows.length === 0 && (
      <p className="text-[12.5px] text-[#888888] py-4 text-center">
        No concentration data available.
      </p>
    )}
  </div>
);

// ---------------------------------------------------------------------------
// HiddenConcentrationCallout
// ---------------------------------------------------------------------------

const HiddenConcentrationCallout: React.FC<{
  discoveries: HiddenConcentration[];
}> = ({ discoveries }) => (
  <div
    data-testid="hidden-concentration-callout"
    className="bg-[#fdf8f0] border border-[#f4e4cc] p-4 space-y-3"
    role="alert"
    aria-label="Hidden concentration discoveries"
  >
    {/* Header */}
    <div className="flex items-center gap-2">
      <Eye className="w-3.5 h-3.5 text-[#9E6B20] flex-shrink-0" />
      <span className="text-[10px] uppercase tracking-[0.14em] font-medium text-[#9E6B20] font-mono">
        Hidden Concentration Discovered
      </span>
      <span className="text-[10px] font-mono text-[#9E6B20] opacity-70">
        · {discoveries.length} finding{discoveries.length !== 1 ? 's' : ''}
      </span>
    </div>

    {/* Individual findings */}
    <div className="space-y-2.5">
      {discoveries.map((d, i) => (
        <div
          key={i}
          className="border-t border-[#f4e4cc] pt-2.5 first:border-t-0 first:pt-0"
        >
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 mb-0.5">
            <span className="text-[12.5px] font-semibold text-[#2a2520]">
              {d.exposure_name}
            </span>
            <span className="text-[11px] font-mono text-[#9E6B20]">
              {fmtPct(d.pre_pct)} → {fmtPct(d.post_pct)}
              <span className="ml-2 text-[10.5px] opacity-80">
                (gap: +{fmtPct(d.gap_pct)} AUM)
              </span>
            </span>
          </div>
          <p className="text-[12px] text-[#5a4a35] leading-relaxed">{d.explanation}</p>
        </div>
      ))}
    </div>
  </div>
);

// ---------------------------------------------------------------------------
// AUM Summary strip
// ---------------------------------------------------------------------------

const AUMStrip: React.FC<{ result: LookThroughResult }> = ({ result }) => (
  <div className="flex flex-wrap items-center gap-6 text-[11px] font-mono text-[#767676]">
    <span>
      Client:{' '}
      <span className="text-[#2a2520] font-medium">{result.client_id}</span>
    </span>
    <span className="text-[#dedbd5]">·</span>
    <span>
      Total AUM:{' '}
      <span className="text-[#2a2520] font-medium">
        {'USD ' +
          result.total_aum_usd.toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}
      </span>
    </span>
    <span className="text-[#dedbd5]">·</span>
    <span>
      As of:{' '}
      <span className="text-[#2a2520] font-medium">{result.as_of}</span>
    </span>
    <span className="text-[#dedbd5]">·</span>
    <span>
      Exposures:{' '}
      <span className="text-[#2a2520] font-medium">{result.concentrations.length}</span>
    </span>
  </div>
);

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

const LookThroughSkeleton: React.FC = () => (
  <div
    data-testid="look-through-skeleton"
    className="space-y-4"
    aria-busy="true"
    aria-label="Loading look-through concentration results"
  >
    {/* Meta strip placeholder */}
    <div className="animate-pulse flex gap-4" role="presentation">
      <div className="h-3 bg-[#f4f3f0] rounded w-24" />
      <div className="h-3 bg-[#f4f3f0] rounded w-32" />
      <div className="h-3 bg-[#f4f3f0] rounded w-20" />
    </div>
    {/* Table rows placeholder */}
    <div className="animate-pulse space-y-2" role="presentation">
      <div className="h-3 bg-[#f4f3f0] rounded w-full" />
      {[...Array(6)].map((_, i) => (
        <div
          key={i}
          className={`h-9 bg-[#f4f3f0] rounded ${i === 5 ? 'w-3/4' : 'w-full'}`}
        />
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
    data-testid="look-through-error-banner"
    className="flex items-start gap-3 bg-amber-50 border border-amber-200 text-amber-900 px-4 py-3"
    role="alert"
  >
    <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0 text-amber-600" />
    <div className="flex-1 min-w-0">
      <p className="text-[12.5px] font-medium">Failed to load look-through results</p>
      <p className="text-[11.5px] mt-0.5 text-amber-800 break-words">{message}</p>
    </div>
    <button
      onClick={onRetry}
      className="flex items-center gap-1.5 text-[11.5px] font-medium text-amber-800 hover:text-amber-900 underline underline-offset-2 flex-shrink-0"
      aria-label="Retry loading look-through results"
    >
      <RefreshCw className="w-3 h-3" />
      Retry
    </button>
  </div>
);

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export const LookThroughPanel: React.FC<LookThroughPanelProps> = ({
  result,
  isLoading,
  error,
  onRetry,
  hasRun,
}) => {
  return (
    <div
      data-testid="look-through-panel"
      className="bg-white border border-[#e8e5e0] p-6 shadow-2xs space-y-5"
    >
      {/* Section header */}
      <div className="flex items-baseline gap-3 border-b border-[#e8e5e0] pb-3">
        <span className="text-[10px] uppercase tracking-[0.14em] font-medium text-[#767676] font-mono">
          SECTION 03 · LOOK-THROUGH CONCENTRATION
        </span>
      </div>

      {/* Error banner */}
      {error && !isLoading && <ErrorBanner message={error} onRetry={onRetry} />}

      {/* Loading skeleton */}
      {isLoading && <LookThroughSkeleton />}

      {/* Empty / pre-fetch state */}
      {!isLoading && !error && !result && (
        <p className="text-[12.5px] text-[#888888]">
          {hasRun
            ? 'No look-through data returned for this client.'
            : 'Look-through concentration data will load automatically when a client is selected.'}
        </p>
      )}

      {/* Results */}
      {!isLoading && result && (
        <div className="space-y-6">
          {/* AUM summary meta strip */}
          <AUMStrip result={result} />

          {/* Concentration heatmap table */}
          <ConcentrationTable rows={result.concentrations} />

          {/* Hidden concentration callout — only when discoveries exist */}
          {result.hidden_concentration_discoveries.length > 0 && (
            <HiddenConcentrationCallout
              discoveries={result.hidden_concentration_discoveries}
            />
          )}
        </div>
      )}
    </div>
  );
};

export default LookThroughPanel;
