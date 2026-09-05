/**
 * RMActionPanel — RM Recommendations panel (Section 05).
 *
 * Renders the list of guarded RM recommendations returned by the backend's
 * mandate_guard engine. For each recommendation the panel shows:
 *  - Action text (verb + asset class / holding name)
 *  - Plain-language summary
 *  - Approval label badge (Discretionary / Client Approval Required / Custody)
 *  - MANDATE BREACH warning + alternative action text when applicable
 *
 * When the recommendations array is empty a "No immediate action required"
 * state is rendered with contextual rationale.
 *
 * Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
 */

import React from 'react';
import { AlertTriangle, CheckCircle2, RefreshCw, ShieldCheck } from 'lucide-react';
import type { RMRecommendation } from '../types/stressWorkbench';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface RMActionPanelProps {
  recommendations: RMRecommendation[] | null;
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
  /** Whether a full stress run has already been executed (used for empty-state copy). */
  hasRun: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Build a short action title from a recommendation, e.g.
 * "Reduce · Fixed Income — Global Bonds Fund"
 * "Increase · Equity"
 */
function buildActionTitle(rec: RMRecommendation): string {
  const parts: string[] = [rec.action_verb];
  if (rec.asset_class) parts.push(rec.asset_class);
  if (rec.holding_name) parts.push(`— ${rec.holding_name}`);
  return parts.join(' · ');
}

/**
 * Derive badge styling tokens from the approval label string.
 * Covers the three service-model variants expected from the backend.
 */
function approvalBadgeTokens(label: string): { bg: string; text: string; border: string } {
  const upper = label.toUpperCase();
  if (upper.includes('CUSTODY')) {
    return {
      bg: 'bg-[#f4f3f0]',
      text: 'text-[#555555]',
      border: 'border-[#dddbd7]',
    };
  }
  if (upper.includes('CLIENT APPROVAL') || upper.includes('ADVISORY')) {
    return {
      bg: 'bg-[#fdf8f0]',
      text: 'text-[#9E6B20]',
      border: 'border-[#f4e4cc]',
    };
  }
  // Discretionary — RM may act without explicit client approval
  return {
    bg: 'bg-[#f0faf9]',
    text: 'text-[#2c6e6a]',
    border: 'border-[#c0e8e4]',
  };
}

// ---------------------------------------------------------------------------
// ApprovalBadge
// ---------------------------------------------------------------------------

const ApprovalBadge: React.FC<{ label: string }> = ({ label }) => {
  const { bg, text, border } = approvalBadgeTokens(label);
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-[9.5px] uppercase tracking-widest font-mono font-semibold leading-none whitespace-nowrap border ${bg} ${text} ${border}`}
      aria-label={`Approval requirement: ${label}`}
    >
      {label}
    </span>
  );
};

// ---------------------------------------------------------------------------
// MandateBreachCallout
// ---------------------------------------------------------------------------

const MandateBreachCallout: React.FC<{
  breachDetail: string | null;
  alternativeAction: string | null;
}> = ({ breachDetail, alternativeAction }) => (
  <div
    data-testid="mandate-breach-callout"
    className="bg-[#fcf5f5] border border-[#eed6d9] p-3 space-y-1.5"
    role="alert"
    aria-label="Mandate breach warning"
  >
    {/* Warning header */}
    <div className="flex items-center gap-2">
      <AlertTriangle className="w-3.5 h-3.5 text-[#7A1C28] flex-shrink-0" />
      <span className="text-[10px] uppercase tracking-[0.14em] font-mono font-semibold text-[#7A1C28]">
        MANDATE BREACH
      </span>
    </div>

    {/* Breach detail */}
    {breachDetail && (
      <p className="text-[11.5px] text-[#9e3a47] leading-relaxed">{breachDetail}</p>
    )}

    {/* Alternative action */}
    {alternativeAction && (
      <div className="pt-1 border-t border-[#eed6d9]">
        <p className="text-[10px] uppercase tracking-[0.12em] font-mono text-[#7A1C28] mb-0.5">
          Alternative Action
        </p>
        <p className="text-[11.5px] text-[#7A1C28] font-medium leading-relaxed">
          {alternativeAction}
        </p>
      </div>
    )}
  </div>
);

// ---------------------------------------------------------------------------
// RecommendationCard — renders a single RM recommendation
// ---------------------------------------------------------------------------

const RecommendationCard: React.FC<{
  rec: RMRecommendation;
  index: number;
}> = ({ rec, index }) => {
  const weightChangeSign = rec.weight_change > 0 ? '+' : '';
  const weightChangeColor =
    rec.weight_change < 0
      ? 'text-[#7A1C28]'
      : rec.weight_change > 0
      ? 'text-[#2c6e6a]'
      : 'text-[#555555]';

  return (
    <div
      data-testid={`recommendation-card-${index}`}
      className={`space-y-3 ${
        index > 0 ? 'border-t border-[#e8e5e0] pt-5 mt-5' : ''
      }`}
    >
      {/* Action title + badge row */}
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex flex-col gap-1 min-w-0">
          <span className="text-[13px] font-semibold text-[#2a2520] leading-snug break-words">
            {buildActionTitle(rec)}
          </span>
          {rec.weight_change !== 0 && (
            <span className={`text-[11px] font-mono tabular-nums ${weightChangeColor}`}>
              Weight change: {weightChangeSign}
              {rec.weight_change.toFixed(1)}%
              {rec.projected_weight !== null && (
                <span className="text-[#767676]">
                  {' '}→ {rec.projected_weight.toFixed(1)}% projected
                </span>
              )}
            </span>
          )}
        </div>
        <ApprovalBadge label={rec.approval_label} />
      </div>

      {/* Mandate breach callout — shown before plain-language summary */}
      {rec.mandate_breach && (
        <MandateBreachCallout
          breachDetail={rec.breach_detail}
          alternativeAction={rec.alternative_action}
        />
      )}

      {/* Plain-language summary */}
      <p className="text-[12.5px] text-[#444444] leading-relaxed">
        {rec.plain_language_summary}
      </p>

      {/* Rationale */}
      {rec.rationale && (
        <p className="text-[11.5px] text-[#767676] leading-relaxed border-l-2 border-[#e8e5e0] pl-3">
          {rec.rationale}
        </p>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// NoActionRequired — empty state when backend returns no recommendations
// ---------------------------------------------------------------------------

const NoActionRequired: React.FC = () => (
  <div
    data-testid="rm-no-action-required"
    className="flex items-start gap-3 bg-[#f0faf9] border border-[#c0e8e4] px-4 py-4"
    role="status"
    aria-label="No immediate action required"
  >
    <CheckCircle2 className="w-4 h-4 text-[#2c6e6a] flex-shrink-0 mt-0.5" />
    <div className="space-y-1">
      <p className="text-[12.5px] font-semibold text-[#2a2520]">
        No immediate action required
      </p>
      <p className="text-[11.5px] text-[#3a8a84] leading-relaxed">
        All portfolio positions are within mandate limits under the current scenario.
        No trades or client communications are required at this time.
      </p>
    </div>
  </div>
);

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

const RMActionSkeleton: React.FC = () => (
  <div
    data-testid="rm-action-skeleton"
    className="space-y-5"
    aria-busy="true"
    aria-label="Loading RM recommendations"
  >
    <div className="animate-pulse space-y-4" role="presentation">
      {[...Array(3)].map((_, i) => (
        <div key={i} className={`space-y-2 ${i > 0 ? 'border-t border-[#f0ede8] pt-4' : ''}`}>
          <div className="flex justify-between gap-4">
            <div className="h-3.5 bg-[#f4f3f0] rounded w-2/3" />
            <div className="h-5 bg-[#f4f3f0] rounded w-28 flex-shrink-0" />
          </div>
          <div className="h-2.5 bg-[#f4f3f0] rounded w-full" />
          <div className="h-2.5 bg-[#f4f3f0] rounded w-4/5" />
        </div>
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
    data-testid="rm-action-error-banner"
    className="flex items-start gap-3 bg-amber-50 border border-amber-200 text-amber-900 px-4 py-3"
    role="alert"
  >
    <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0 text-amber-600" />
    <div className="flex-1 min-w-0">
      <p className="text-[12.5px] font-medium">Failed to load RM recommendations</p>
      <p className="text-[11.5px] mt-0.5 text-amber-800 break-words">{message}</p>
    </div>
    <button
      onClick={onRetry}
      className="flex items-center gap-1.5 text-[11.5px] font-medium text-amber-800 hover:text-amber-900 underline underline-offset-2 flex-shrink-0"
      aria-label="Retry loading RM recommendations"
    >
      <RefreshCw className="w-3 h-3" />
      Retry
    </button>
  </div>
);

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export const RMActionPanel: React.FC<RMActionPanelProps> = ({
  recommendations,
  isLoading,
  error,
  onRetry,
  hasRun,
}) => {
  return (
    <div
      data-testid="rm-action-panel"
      className="bg-white border border-[#e8e5e0] p-6 shadow-2xs space-y-5"
    >
      {/* Section header */}
      <div className="flex items-center gap-3 border-b border-[#e8e5e0] pb-3">
        <ShieldCheck className="w-3.5 h-3.5 text-[#767676] flex-shrink-0" />
        <span className="text-[10px] uppercase tracking-[0.14em] font-medium text-[#767676] font-mono">
          SECTION 05 · RM RECOMMENDATIONS
        </span>
      </div>

      {/* Error banner */}
      {error && !isLoading && <ErrorBanner message={error} onRetry={onRetry} />}

      {/* Loading skeleton */}
      {isLoading && <RMActionSkeleton />}

      {/* Pre-run / empty state */}
      {!isLoading && !error && recommendations === null && (
        <p className="text-[12.5px] text-[#888888]">
          {hasRun
            ? 'No recommendation data returned for this scenario.'
            : 'Run a scenario above to see RM recommendations.'}
        </p>
      )}

      {/* Empty recommendations — "No immediate action" */}
      {!isLoading && !error && recommendations !== null && recommendations.length === 0 && (
        <NoActionRequired />
      )}

      {/* Recommendation cards */}
      {!isLoading && recommendations !== null && recommendations.length > 0 && (
        <div
          data-testid="recommendation-list"
          className="space-y-0"
        >
          {/* Summary count */}
          <p className="text-[11px] font-mono text-[#767676] pb-4">
            {recommendations.length} recommendation{recommendations.length !== 1 ? 's' : ''}
            {recommendations.some((r) => r.mandate_breach) && (
              <span className="ml-2 text-[#7A1C28] font-semibold">
                · {recommendations.filter((r) => r.mandate_breach).length} mandate breach
                {recommendations.filter((r) => r.mandate_breach).length !== 1 ? 'es' : ''}
              </span>
            )}
          </p>

          {recommendations.map((rec, i) => (
            <RecommendationCard key={i} rec={rec} index={i} />
          ))}
        </div>
      )}
    </div>
  );
};

export default RMActionPanel;
