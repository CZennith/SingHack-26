/**
 * ScenarioNarrativeCard — displays the AI-generated scenario narrative.
 *
 * Placed above the stress module panels. Shows a skeleton while loading,
 * renders nothing when `narrative` is null, and displays the narrative text
 * with serif styling when available.
 *
 * Requirements: 2.3, 8.2
 */

import React from 'react';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface ScenarioNarrativeCardProps {
  narrative: string | null;
  isLoading: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const ScenarioNarrativeCard: React.FC<ScenarioNarrativeCardProps> = ({
  narrative,
  isLoading,
}) => {
  // Loading state: show animated skeleton placeholder
  if (isLoading) {
    return (
      <div
        data-testid="scenario-narrative-card-skeleton"
        className="bg-white border border-[#e8e5e0] p-6 shadow-2xs space-y-4"
        aria-busy="true"
        aria-label="Loading scenario narrative"
      >
        <div className="border-b border-[#e8e5e0] pb-3">
          <span className="text-[10px] uppercase tracking-[0.14em] font-medium text-[#767676] font-mono">
            SCENARIO NARRATIVE
          </span>
        </div>
        <div className="space-y-3 animate-pulse" role="presentation">
          <div className="h-4 bg-[#f4f3f0] rounded w-full" />
          <div className="h-4 bg-[#f4f3f0] rounded w-5/6" />
          <div className="h-4 bg-[#f4f3f0] rounded w-4/5" />
        </div>
      </div>
    );
  }

  // No narrative yet: render nothing
  if (narrative === null) {
    return null;
  }

  // Narrative available: render card
  return (
    <div
      data-testid="scenario-narrative-card"
      className="bg-white border border-[#e8e5e0] p-6 shadow-2xs space-y-3"
    >
      <div className="border-b border-[#e8e5e0] pb-3">
        <span className="text-[10px] uppercase tracking-[0.14em] font-medium text-[#767676] font-mono">
          SCENARIO NARRATIVE
        </span>
      </div>
      <p className="font-serif text-[14px] leading-relaxed text-[#2a2520]">
        {narrative}
      </p>
    </div>
  );
};

export default ScenarioNarrativeCard;
