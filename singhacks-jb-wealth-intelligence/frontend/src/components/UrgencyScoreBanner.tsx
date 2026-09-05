/**
 * UrgencyScoreBanner — displays the client's urgency score, risk level,
 * contributing triggers, and projected score delta from stress test results.
 *
 * Requirements: 11.1, 11.2, 11.3, 11.4
 */

import React from 'react';
import type { UrgencyTrigger } from '../types/stressWorkbench';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface UrgencyScoreBannerProps {
  clientId: string;
  currentScore: number;
  riskLevel: string; // "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
  triggers: UrgencyTrigger[];
  projectedScore: number | null;
  projectedDelta: number | null;
  onScrollTo: (anchor: string) => void;
}

// ---------------------------------------------------------------------------
// Badge colour tokens (Req 14)
// ---------------------------------------------------------------------------

function getBadgeClasses(riskLevel: string): string {
  switch (riskLevel.toUpperCase()) {
    case 'CRITICAL':
      return 'bg-[#fcf5f5] text-[#7A1C28] border border-[#eed6d9]';
    case 'HIGH':
    case 'ELEVATED':
    case 'WARNING':
      return 'bg-[#fdf8f0] text-[#9E6B20] border border-[#f4e4cc]';
    case 'MEDIUM':
    case 'LOW':
    case 'NORMAL':
    case 'OK':
    default:
      return 'bg-[#faf9f6] text-[#666666] border border-[#dedbd5]';
  }
}

// ---------------------------------------------------------------------------
// Delta indicator colour
// ---------------------------------------------------------------------------

function getDeltaClasses(delta: number): string {
  if (delta > 0) return 'text-[#7A1C28]';
  if (delta < 0) return 'text-[#2A6B3A]';
  return 'text-[#666666]';
}

function formatDelta(delta: number): string {
  if (delta > 0) return `+${delta}`;
  return String(delta);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const UrgencyScoreBanner: React.FC<UrgencyScoreBannerProps> = ({
  currentScore,
  riskLevel,
  triggers,
  projectedScore,
  projectedDelta,
  onScrollTo,
}) => {
  const badgeClasses = getBadgeClasses(riskLevel);
  const showProjected =
    projectedScore !== null &&
    projectedDelta !== null &&
    projectedScore !== currentScore;

  return (
    <div
      data-testid="urgency-score-banner"
      className="bg-white border border-[#e8e5e0] p-4 shadow-2xs space-y-3"
    >
      {/* Section header */}
      <div className="flex items-baseline gap-3 border-b border-[#e8e5e0] pb-3">
        <span className="text-[10px] uppercase tracking-[0.14em] font-medium text-[#767676] font-mono">
          URGENCY SCORE DRILLDOWN
        </span>
      </div>

      {/* Score row — Req 11.1 */}
      <div className="flex flex-wrap items-center gap-4">
        {/* Current score */}
        <div className="flex items-center gap-2">
          <span
            className={`font-mono text-[22px] font-semibold leading-none px-3 py-1.5 ${badgeClasses}`}
            data-testid="urgency-score-value"
          >
            {currentScore}
          </span>
          <span
            className={`text-[10px] uppercase tracking-[0.12em] font-medium px-2 py-0.5 ${badgeClasses}`}
            data-testid="urgency-risk-level"
          >
            {riskLevel}
          </span>
        </div>

        {/* Projected score delta — Req 11.3 */}
        {showProjected && projectedScore !== null && projectedDelta !== null && (
          <div
            className="flex items-center gap-2 pl-4 border-l border-[#e8e5e0]"
            data-testid="projected-score-indicator"
          >
            <span className="text-[10px] uppercase tracking-[0.12em] text-[#767676] font-mono">
              Projected
            </span>
            <span className="font-mono text-[18px] font-semibold text-[#121212] leading-none">
              {projectedScore}
            </span>
            <span
              className={`font-mono text-[12px] font-medium ${getDeltaClasses(projectedDelta)}`}
              data-testid="projected-delta"
            >
              {formatDelta(projectedDelta)} pts
            </span>
          </div>
        )}
      </div>

      {/* Trigger list — Req 11.2, 11.4 */}
      {triggers.length === 0 ? (
        <p
          className="text-[12px] text-[#aaaaaa] italic"
          data-testid="no-triggers-message"
        >
          No active triggers
        </p>
      ) : (
        <ul className="space-y-1" data-testid="trigger-list">
          {triggers.map((trigger) => (
            <li key={trigger.code}>
              <button
                type="button"
                onClick={() => onScrollTo(trigger.module_anchor)}
                className="w-full text-left px-3 py-2 hover:bg-[#f4f3f0] transition-colors cursor-pointer group"
                data-testid={`trigger-row-${trigger.code}`}
              >
                <div className="flex items-baseline justify-between gap-3">
                  <span className="text-[12.5px] text-[#121212] font-medium group-hover:underline">
                    {trigger.label}
                  </span>
                  <span className="shrink-0 font-mono text-[11px] text-[#7A1C28] font-semibold">
                    +{trigger.points} pts
                  </span>
                </div>
                <p className="text-[11px] text-[#767676] mt-0.5 leading-snug">
                  {trigger.evidence_summary}
                </p>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
