/**
 * CallScriptModal — generates a client-friendly call script from a stress result
 * and displays it in a modal with copy-to-clipboard support.
 *
 * Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { X, Copy, Check } from 'lucide-react';
import type { StressRunResult, AuditEntry } from '../types/stressWorkbench';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface CallScriptModalProps {
  isOpen: boolean;
  onClose: () => void;
  stressResult: StressRunResult;
  clientName: string;
  /** e.g. "Conservative", "Balanced", "Growth", or a RiskSeverity like "HIGH" */
  riskProfile: string;
  /** Called when the modal opens — parent appends AuditEntry */
  onAuditEntry: (entry: AuditEntry) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Format a date string (ISO-8601 or YYYY-MM-DD) as "26 Aug 2026".
 */
function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return dateStr;
    return date.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

/**
 * Format a number as "USD 4,200,000.00"
 */
function formatUSD(value: number): string {
  return (
    'USD ' +
    Math.abs(value).toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  );
}

/**
 * Derive closing reassurance based on riskProfile string (case-insensitive).
 * Covers the ClientDossier.riskLevel variants (CRITICAL/HIGH/MEDIUM/LOW)
 * as well as plain-language labels (Conservative, Balanced, Growth, etc.).
 */
function getClosingReassurance(riskProfile: string): string {
  const lower = riskProfile.toLowerCase();
  if (
    lower.includes('conservative') ||
    lower.includes('capital preservation') ||
    lower === 'low'
  ) {
    return 'Our priority remains capital preservation and protecting your portfolio from downside scenarios.';
  }
  if (lower.includes('balanced') || lower === 'medium') {
    return 'We remain focused on balancing growth opportunities with prudent risk management.';
  }
  if (
    lower.includes('growth') ||
    lower.includes('aggressive') ||
    lower === 'high' ||
    lower === 'critical'
  ) {
    return 'We are monitoring the situation closely and are positioned to act opportunistically as conditions evolve.';
  }
  return 'We will continue to monitor your portfolio and update you on any material developments.';
}

/**
 * Derive the call script text from a StressRunResult.
 * Returns a multi-line string with bullets using the • character.
 */
function deriveCallScript(
  result: StressRunResult,
  clientName: string,
  riskProfile: string
): string {
  const lines: string[] = [];

  // ── Context setter ──────────────────────────────────────────────────────
  lines.push(
    `This analysis was prepared on ${formatDate(result.as_of)} for ${clientName} based on the ${result.scenario.label} scenario.`
  );
  lines.push('');

  // ── Key findings ────────────────────────────────────────────────────────
  lines.push('KEY FINDINGS');

  // 1. Net dollar impact
  const macro_shock = result.macro_shock;
  if (macro_shock) {
    const sign = (macro_shock.net_dollar_impact_usd ?? 0) < 0 ? '−' : '+';
    const absPct = Math.abs(macro_shock.net_pct_change ?? 0).toFixed(1);
    const topHolding = macro_shock.top_impacted_holdings?.[0];
    const topHoldingName = topHolding?.instrument_name ?? 'the largest impacted position';
    lines.push(
      `• Portfolio impact of ${sign}${formatUSD(macro_shock.net_dollar_impact_usd ?? 0)} (${sign}${absPct}%), driven primarily by ${topHoldingName}.`
    );
  }

  // 2. LTV status
  const ltv_stress = result.ltv_stress;
  const facilities = ltv_stress?.facilities ?? [];
  if (facilities.length > 0) {
    const facility = facilities[0];
    if (facility.scenario_ltv_pct != null && facility.margin_call_ltv_pct != null) {
      const threshold = facility.margin_call_ltv_pct;
      const scenarioLtv = facility.scenario_ltv_pct;
      const proximityPct = threshold > 0 ? (scenarioLtv / threshold) * 100 : 0;
      if (scenarioLtv >= threshold) {
        lines.push(
          `• Your Lombard facility (${facility.facility_id}) would breach the margin call threshold under this scenario — scenario LTV of ${scenarioLtv.toFixed(1)}% exceeds the ${threshold.toFixed(1)}% limit.`
        );
      } else if (proximityPct >= 80) {
        lines.push(
          `• Your Lombard facility is approaching its margin call threshold — scenario LTV of ${scenarioLtv.toFixed(1)}% versus a ${threshold.toFixed(1)}% limit (${(threshold - scenarioLtv).toFixed(1)} points of headroom).`
        );
      } else {
        lines.push(
          `• Your Lombard facility remains within comfortable limits under this scenario — scenario LTV of ${scenarioLtv.toFixed(1)}% versus a ${threshold.toFixed(1)}% threshold.`
        );
      }
    }
  }

  // 3. Liquidity
  const liquidity = result.liquidity;
  if (liquidity?.lcr != null) {
    if (liquidity.lcr < 1.0) {
      lines.push(
        `• A liquidity shortfall exists — your liquid assets cover ${(liquidity.lcr * 100).toFixed(0)}% of 60-day obligations, leaving a gap of ${formatUSD(Math.abs(liquidity.surplus_or_gap_usd ?? 0))}.`
      );
    } else {
      lines.push(
        `• Liquidity is well-covered — liquid assets exceed 60-day obligations by ${formatUSD(liquidity.surplus_or_gap_usd ?? 0)} (coverage ratio: ${liquidity.lcr.toFixed(2)}×).`
      );
    }
  }

  // 4. Concentration breach (if any)
  const look_through = result.look_through;
  const breaches = look_through?.concentrations?.filter((c) => c.status === 'BREACH') ?? [];
  if (breaches.length > 0) {
    const breach = breaches[0];
    lines.push(
      `• A concentration limit has been breached: ${breach.exposure_name} represents ${breach.post_look_through_pct.toFixed(1)}% of your portfolio against a mandate limit of ${breach.mandate_limit_pct?.toFixed(1) ?? 'N/A'}%.`
    );
  }

  lines.push('');

  // ── Recommended actions ─────────────────────────────────────────────────
  lines.push('RECOMMENDED ACTIONS');
  const { recommendations } = result;
  if (!recommendations || recommendations.length === 0) {
    lines.push('• No immediate rebalancing action is required at this time.');
  } else {
    lines.push(`• ${recommendations[0].plain_language_summary}`);
    if (recommendations[1]) {
      lines.push(`• ${recommendations[1].plain_language_summary}`);
    }
  }

  lines.push('');

  // ── Closing reassurance ─────────────────────────────────────────────────
  lines.push(getClosingReassurance(riskProfile));

  return lines.join('\n');
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export const CallScriptModal: React.FC<CallScriptModalProps> = ({
  isOpen,
  onClose,
  stressResult,
  clientName,
  riskProfile,
  onAuditEntry,
}) => {
  const [copyState, setCopyState] = useState<'idle' | 'copied' | 'fallback'>('idle');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const auditFiredRef = useRef(false);

  // Derive the script text once
  const scriptText = deriveCallScript(stressResult, clientName, riskProfile);

  // ── Audit entry on open (Req 10.5) ──────────────────────────────────────
  useEffect(() => {
    if (!isOpen) return;
    if (auditFiredRef.current) return;
    auditFiredRef.current = true;

    onAuditEntry({
      result_id: stressResult.result_id,
      timestamp: new Date().toISOString(),
      client_id: stressResult.client_id,
      scenario_name: stressResult.scenario.label,
      decision: 'call_script_generated',
      note: '',
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  // Reset audit ref if modal is closed and re-opened for a different result
  useEffect(() => {
    if (!isOpen) {
      auditFiredRef.current = false;
      setCopyState('idle');
    }
  }, [isOpen, stressResult.result_id]);

  // ── Copy to clipboard ────────────────────────────────────────────────────
  const handleCopy = useCallback(async () => {
    if (navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(scriptText);
        setCopyState('copied');
        setTimeout(() => setCopyState('idle'), 2000);
      } catch {
        setCopyState('fallback');
      }
    } else {
      setCopyState('fallback');
    }
  }, [scriptText]);

  // Auto-select the textarea when falling back to manual copy
  useEffect(() => {
    if (copyState === 'fallback' && textareaRef.current) {
      textareaRef.current.select();
    }
  }, [copyState]);

  // ── Keyboard close ───────────────────────────────────────────────────────
  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const formattedDate = formatDate(stressResult.as_of);

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 backdrop-blur-sm pt-12 pb-12 px-4 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-label="Call Script"
      onClick={(e) => {
        // Close on overlay click
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-[#faf9f6] border border-[#e8e5e0] shadow-2xs max-w-xl w-full">

        {/* ── Confidential memo header ─────────────────────────────────── */}
        <div className="border-b border-[#e8e5e0] px-6 py-4">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1.5 min-w-0">
              <p className="text-[10px] uppercase tracking-[0.14em] font-medium text-[#767676] font-mono">
                CONFIDENTIAL · INTERNAL USE ONLY
              </p>
              <div className="flex flex-wrap gap-x-5 gap-y-1 text-[10.5px] font-mono text-[#555555]">
                <span>
                  <span className="text-[#767676] uppercase tracking-[0.12em] text-[9.5px]">Client </span>
                  {clientName}
                </span>
                <span>
                  <span className="text-[#767676] uppercase tracking-[0.12em] text-[9.5px]">Scenario </span>
                  {stressResult.scenario.label}
                </span>
                <span>
                  <span className="text-[#767676] uppercase tracking-[0.12em] text-[9.5px]">Date </span>
                  {formattedDate}
                </span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="flex-shrink-0 p-1.5 text-[#767676] hover:text-[#121212] hover:bg-[#f0ede8] transition-colors"
              aria-label="Close call script modal"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* ── Script body ──────────────────────────────────────────────── */}
        <div className="px-6 py-5 space-y-4">
          <p className="text-[10px] uppercase tracking-[0.14em] font-medium text-[#767676] font-mono">
            CALL SCRIPT · RM TALKING POINTS
          </p>

          <div className="space-y-3 text-[12.5px] text-[#2a2520] leading-relaxed">
            {scriptText.split('\n').map((line, idx) => {
              if (line === '') return <div key={idx} className="h-1" />;

              // Section headers
              if (line === 'KEY FINDINGS' || line === 'RECOMMENDED ACTIONS') {
                return (
                  <p
                    key={idx}
                    className="text-[10px] uppercase tracking-[0.14em] font-medium text-[#767676] font-mono pt-1"
                  >
                    {line}
                  </p>
                );
              }

              // Bullet points
              if (line.startsWith('• ')) {
                return (
                  <p key={idx} className="flex gap-2">
                    <span className="flex-shrink-0 text-[#767676]">•</span>
                    <span>{line.slice(2)}</span>
                  </p>
                );
              }

              // Context setter / closing reassurance
              return (
                <p key={idx} className="text-[12.5px] text-[#2a2520] leading-relaxed italic">
                  {line}
                </p>
              );
            })}
          </div>
        </div>

        {/* ── Footer — copy action ─────────────────────────────────────── */}
        <div className="border-t border-[#e8e5e0] px-6 py-4 space-y-3">
          {copyState !== 'fallback' && (
            <button
              onClick={handleCopy}
              className="flex items-center gap-2 px-4 py-2 text-[11.5px] font-medium text-[#faf9f6] bg-[#2a2520] hover:bg-[#121212] transition-colors"
              aria-label="Copy call script to clipboard"
            >
              {copyState === 'copied' ? (
                <>
                  <Check className="w-3.5 h-3.5" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  Copy to Clipboard
                </>
              )}
            </button>
          )}

          {/* Clipboard API fallback — pre-selected textarea */}
          {copyState === 'fallback' && (
            <div className="space-y-2">
              <p className="text-[11px] text-[#767676] font-mono uppercase tracking-[0.12em]">
                Clipboard unavailable — select all and copy manually (Ctrl+C / ⌘C)
              </p>
              <textarea
                ref={textareaRef}
                readOnly
                value={scriptText}
                rows={10}
                className="w-full text-[11.5px] font-mono text-[#2a2520] bg-[#f4f3f0] border border-[#e8e5e0] p-3 resize-none focus:outline-none"
                aria-label="Call script text for manual copy"
              />
              <button
                onClick={() => setCopyState('idle')}
                className="text-[11px] text-[#767676] hover:text-[#121212] underline underline-offset-2"
              >
                Try clipboard again
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CallScriptModal;
