/**
 * BookScenarioLeaderboard — ranked table of all book clients for a completed
 * book-wide scenario run.
 *
 * Rows are sorted by scenario_rank (LTV breach clients first, then by absolute
 * dollar impact descending). Clicking a row calls onDrillDown(clientId) to
 * open the Workbench in client mode with the same scenario pre-loaded.
 *
 * Requirements: 12.3, 12.5
 */

import React from 'react';
import type { BookScenarioResponse, BookScenarioClientRow } from '../types/stressWorkbench';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface BookScenarioLeaderboardProps {
  result: BookScenarioResponse;
  onDrillDown: (clientId: string) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatUSD(value: number): string {
  return (
    'USD ' +
    Math.abs(value).toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  );
}

function formatPct(value: number): string {
  return (value >= 0 ? '+' : '') + value.toFixed(2) + '%';
}

// Sort: LTV breach rows first, then by ascending scenario_rank (already
// computed by the backend as absolute impact desc with breach-first tie-break).
function sortedRows(clients: BookScenarioClientRow[]): BookScenarioClientRow[] {
  return [...clients].sort((a, b) => a.scenario_rank - b.scenario_rank);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const BookScenarioLeaderboard: React.FC<BookScenarioLeaderboardProps> = ({
  result,
  onDrillDown,
}) => {
  const rows = sortedRows(result.clients);

  return (
    <div className="bg-white border border-[#e8e5e0] shadow-2xs">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#e8e5e0]">
        <div className="flex items-baseline gap-3">
          <span className="text-[10px] uppercase tracking-[0.14em] font-medium text-[#767676] font-mono">
            SECTION 02 · SCENARIO IMPACT LEADERBOARD
          </span>
          <span className="px-2 py-0.5 text-[9px] uppercase tracking-[0.08em] font-medium bg-[#faf9f6] border border-[#e8e5e0] text-[#666666]">
            {result.scenario.label}
          </span>
        </div>
        <span className="font-mono text-[11px] text-[#888888]">
          as of {result.as_of}
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-[12px]">
          <thead>
            <tr className="border-b border-[#e8e5e0] bg-[#faf9f6]">
              <th className="px-4 py-2.5 text-left text-[9.5px] uppercase tracking-[0.14em] font-medium text-[#767676] font-mono w-12">
                Rank
              </th>
              <th className="px-4 py-2.5 text-left text-[9.5px] uppercase tracking-[0.14em] font-medium text-[#767676] font-mono">
                Client Name
              </th>
              <th className="px-4 py-2.5 text-right text-[9.5px] uppercase tracking-[0.14em] font-medium text-[#767676] font-mono">
                Net Dollar Impact
              </th>
              <th className="px-4 py-2.5 text-right text-[9.5px] uppercase tracking-[0.14em] font-medium text-[#767676] font-mono">
                Net % Change
              </th>
              <th className="px-4 py-2.5 text-center text-[9.5px] uppercase tracking-[0.14em] font-medium text-[#767676] font-mono">
                LTV Status
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.client_id}
                onClick={() => onDrillDown(row.client_id)}
                className="border-b border-[#f0eee9] last:border-b-0 hover:bg-[#faf9f6] cursor-pointer transition-colors"
              >
                {/* Rank */}
                <td className="px-4 py-3 font-mono text-[11px] text-[#767676]">
                  {row.scenario_rank}
                </td>

                {/* Client Name */}
                <td className="px-4 py-3">
                  <span className="text-[12.5px] font-medium text-[#121212]">
                    {row.client_name}
                  </span>
                </td>

                {/* Net Dollar Impact */}
                <td className="px-4 py-3 text-right font-mono text-[11.5px]">
                  <span
                    className={
                      row.net_dollar_impact_usd < 0
                        ? 'text-[#7A1C28]'
                        : 'text-emerald-700'
                    }
                  >
                    {row.net_dollar_impact_usd < 0 ? '−' : '+'}
                    {formatUSD(row.net_dollar_impact_usd)}
                  </span>
                </td>

                {/* Net % Change */}
                <td className="px-4 py-3 text-right font-mono text-[11.5px]">
                  <span
                    className={
                      row.net_pct_change < 0 ? 'text-[#7A1C28]' : 'text-emerald-700'
                    }
                  >
                    {formatPct(row.net_pct_change)}
                  </span>
                </td>

                {/* LTV Breach Badge */}
                <td className="px-4 py-3 text-center">
                  {row.ltv_breach ? (
                    <span className="px-2 py-0.5 bg-[#fcf5f5] text-[#7A1C28] border border-[#eed6d9] text-[9.5px] font-mono font-medium">
                      LTV BREACH
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 bg-[#f4f3f0] text-[#555555] border border-[#dedbd5] text-[9.5px] font-mono">
                      OK
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer summary */}
      <div className="px-5 py-3 border-t border-[#e8e5e0] bg-[#faf9f6] flex items-center justify-between">
        <span className="text-[11px] text-[#767676] font-mono">
          {rows.length} clients ranked · click a row to drill down
        </span>
        <span className="text-[11px] text-[#767676] font-mono">
          {rows.filter((r) => r.ltv_breach).length} LTV breach
          {rows.filter((r) => r.ltv_breach).length !== 1 ? 'es' : ''}
        </span>
      </div>
    </div>
  );
};
