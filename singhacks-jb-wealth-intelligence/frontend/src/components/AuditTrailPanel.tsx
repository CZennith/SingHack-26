/**
 * AuditTrailPanel — Audit Trail component (Section 06).
 *
 * Renders the "Mark as Reviewed" / "Mark as Actioned" action buttons below
 * the stress results. Once a decision is recorded, a stamped confirmation
 * footer appears on the result panel. A collapsible Audit Log section lists
 * all Audit_Entries for the active client in reverse-chronological order.
 *
 * Note-entry is handled via a lightweight inline prompt (max 160 chars) that
 * appears when either action button is clicked.
 *
 * Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
 */

import React, { useState } from 'react';
import { ChevronDown, ChevronUp, ClipboardCheck, Zap, Clock } from 'lucide-react';
import type { AuditEntry } from '../types/stressWorkbench';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface AuditTrailPanelProps {
  /** The result_id from the most-recently run StressRunResult. */
  resultId: string | null;
  /** Client ID of the active stress session. */
  clientId: string;
  /** Scenario name (label) of the last run. */
  scenarioName: string;
  /** Full session-scoped audit log for this client (passed in from parent state). */
  auditEntries: AuditEntry[];
  /** Called when RM marks as reviewed or actioned; parent appends entry to state. */
  onMarkReviewed: (entry: AuditEntry) => void;
  onMarkActioned: (entry: AuditEntry) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Format ISO timestamp to a human-readable short form. */
function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  } catch {
    return iso;
  }
}

/** Truncate a note to a short excerpt for the footer stamp. */
function noteExcerpt(note: string, maxLen = 80): string {
  if (!note) return '';
  return note.length > maxLen ? note.slice(0, maxLen) + '…' : note;
}

/** Decision badge tokens (matches app badge colour system). */
function decisionBadgeTokens(decision: AuditEntry['decision']) {
  switch (decision) {
    case 'actioned':
      return {
        bg: 'bg-[#fcf5f5]',
        text: 'text-[#7A1C28]',
        border: 'border-[#eed6d9]',
        label: 'ACTIONED',
      };
    case 'call_script_generated':
      return {
        bg: 'bg-[#fdf8f0]',
        text: 'text-[#9E6B20]',
        border: 'border-[#f4e4cc]',
        label: 'CALL SCRIPT',
      };
    case 'reviewed':
    default:
      return {
        bg: 'bg-[#faf9f6]',
        text: 'text-[#555555]',
        border: 'border-[#dedbd5]',
        label: 'REVIEWED',
      };
  }
}

// ---------------------------------------------------------------------------
// NotePrompt — inline textarea + confirm / cancel for optional note entry
// ---------------------------------------------------------------------------

interface NotePromptProps {
  decision: 'reviewed' | 'actioned';
  onConfirm: (note: string) => void;
  onCancel: () => void;
}

const NotePrompt: React.FC<NotePromptProps> = ({ decision, onConfirm, onCancel }) => {
  const [note, setNote] = useState('');
  const MAX = 160;
  const remaining = MAX - note.length;

  return (
    <div
      data-testid="audit-note-prompt"
      className="bg-[#faf9f6] border border-[#e8e5e0] p-4 space-y-3"
      role="dialog"
      aria-label={`Add note for ${decision} decision`}
    >
      <p className="text-[11.5px] text-[#444444] leading-relaxed">
        Add an optional note (max {MAX} characters):
      </p>
      <textarea
        data-testid="audit-note-input"
        value={note}
        onChange={(e) => setNote(e.target.value.slice(0, MAX))}
        rows={3}
        placeholder="e.g. Discussed with client — agreed to reduce Equity by 5%"
        className="w-full text-[12.5px] text-[#121212] bg-white border border-[#e8e5e0] px-3 py-2 leading-relaxed resize-none focus:outline-none focus:border-[#9c9790] placeholder:text-[#aaaaaa]"
        aria-label="Audit note"
        maxLength={MAX}
      />
      <div className="flex items-center justify-between">
        <span
          className={`text-[10px] font-mono tabular-nums ${
            remaining < 20 ? 'text-[#9E6B20]' : 'text-[#9c9790]'
          }`}
        >
          {remaining} characters remaining
        </span>
        <div className="flex items-center gap-2">
          <button
            data-testid="audit-note-cancel"
            onClick={onCancel}
            className="text-[11.5px] text-[#666666] underline underline-offset-2 hover:text-[#333333]"
          >
            Cancel
          </button>
          <button
            data-testid="audit-note-confirm"
            onClick={() => onConfirm(note.trim())}
            className="text-[11.5px] font-semibold text-white bg-[#2a2520] px-4 py-1.5 hover:bg-[#3a3530] transition-colors"
          >
            Save {decision === 'reviewed' ? 'Review' : 'Action'}
          </button>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// StampedFooter — shown on the result panel once an entry exists
// ---------------------------------------------------------------------------

interface StampedFooterProps {
  entry: AuditEntry;
}

const StampedFooter: React.FC<StampedFooterProps> = ({ entry }) => {
  const tokens = decisionBadgeTokens(entry.decision);
  return (
    <div
      data-testid="audit-stamped-footer"
      className="flex flex-wrap items-start gap-3 bg-[#faf9f6] border border-[#e8e5e0] px-4 py-3"
      role="status"
      aria-label={`Result ${entry.decision} at ${entry.timestamp}`}
    >
      <ClipboardCheck className="w-4 h-4 text-[#767676] flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0 space-y-0.5">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`inline-flex items-center px-2 py-0.5 text-[9.5px] uppercase tracking-widest font-mono font-semibold border ${tokens.bg} ${tokens.text} ${tokens.border}`}
          >
            {tokens.label}
          </span>
          <span className="text-[11px] font-mono text-[#767676] tabular-nums">
            {formatTimestamp(entry.timestamp)}
          </span>
        </div>
        {entry.note && (
          <p className="text-[11.5px] text-[#555555] leading-relaxed">
            "{noteExcerpt(entry.note)}"
          </p>
        )}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// AuditLogEntry — a single row in the collapsible audit log
// ---------------------------------------------------------------------------

const AuditLogEntry: React.FC<{ entry: AuditEntry; index: number }> = ({ entry, index }) => {
  const tokens = decisionBadgeTokens(entry.decision);
  return (
    <div
      data-testid={`audit-log-entry-${index}`}
      className={`flex items-start gap-3 py-3 ${index > 0 ? 'border-t border-[#f0ede8]' : ''}`}
    >
      <div className="flex flex-col items-center gap-1 flex-shrink-0 pt-0.5">
        <Clock className="w-3 h-3 text-[#aaaaaa]" />
        {index < 10 && ( // vertical connector line hint
          <div className="w-px h-3 bg-[#e8e5e0]" />
        )}
      </div>
      <div className="flex-1 min-w-0 space-y-1">
        {/* Decision + timestamp */}
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`inline-flex items-center px-1.5 py-0.5 text-[9px] uppercase tracking-widest font-mono font-semibold border ${tokens.bg} ${tokens.text} ${tokens.border}`}
          >
            {tokens.label}
          </span>
          <span className="text-[10.5px] font-mono text-[#767676] tabular-nums">
            {formatTimestamp(entry.timestamp)}
          </span>
        </div>
        {/* Scenario */}
        <p className="text-[11.5px] text-[#444444] leading-snug">
          {entry.scenario_name}
        </p>
        {/* Note excerpt */}
        {entry.note && (
          <p className="text-[11px] text-[#767676] italic leading-snug">
            "{noteExcerpt(entry.note, 120)}"
          </p>
        )}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export const AuditTrailPanel: React.FC<AuditTrailPanelProps> = ({
  resultId,
  clientId,
  scenarioName,
  auditEntries,
  onMarkReviewed,
  onMarkActioned,
}) => {
  // Which note prompt is open: null | 'reviewed' | 'actioned'
  const [promptDecision, setPromptDecision] = useState<'reviewed' | 'actioned' | null>(null);
  // Whether the collapsible audit log section is expanded
  const [isLogExpanded, setIsLogExpanded] = useState(false);

  // The latest entry for the current result (if any)
  const latestEntryForResult = resultId
    ? auditEntries.find(
        (e) =>
          e.result_id === resultId &&
          (e.decision === 'reviewed' || e.decision === 'actioned'),
      )
    : undefined;

  // Entries for the current client, reverse-chronological (most recent first)
  const clientEntries = [...auditEntries]
    .filter((e) => e.client_id === clientId)
    .reverse();

  // -------------------------------------------------------------------------
  // Handlers
  // -------------------------------------------------------------------------

  const handleActionClick = (decision: 'reviewed' | 'actioned') => {
    if (!resultId) return;
    setPromptDecision(decision);
  };

  const handleNoteConfirm = (note: string) => {
    if (!resultId || !promptDecision) return;

    const entry: AuditEntry = {
      result_id: resultId,
      timestamp: new Date().toISOString(),
      client_id: clientId,
      scenario_name: scenarioName,
      decision: promptDecision,
      note,
    };

    if (promptDecision === 'reviewed') {
      onMarkReviewed(entry);
    } else {
      onMarkActioned(entry);
    }

    setPromptDecision(null);
  };

  const handleNoteCancel = () => {
    setPromptDecision(null);
  };

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  const hasResult = resultId !== null;
  const alreadyStamped = latestEntryForResult !== undefined;

  return (
    <div
      data-testid="audit-trail-panel"
      className="bg-white border border-[#e8e5e0] shadow-2xs space-y-0"
    >
      {/* ------------------------------------------------------------------
          Section header
      ------------------------------------------------------------------ */}
      <div className="flex items-center gap-3 border-b border-[#e8e5e0] px-6 py-4">
        <ClipboardCheck className="w-3.5 h-3.5 text-[#767676] flex-shrink-0" />
        <span className="text-[10px] uppercase tracking-[0.14em] font-medium text-[#767676] font-mono">
          SECTION 06 · AUDIT TRAIL
        </span>
      </div>

      <div className="px-6 py-5 space-y-4">

        {/* ------------------------------------------------------------------
            Stamped footer — shown when current result already has an entry
        ------------------------------------------------------------------ */}
        {alreadyStamped && latestEntryForResult && (
          <StampedFooter entry={latestEntryForResult} />
        )}

        {/* ------------------------------------------------------------------
            Action buttons — shown when a result exists and not yet in an
            active note-prompt state
        ------------------------------------------------------------------ */}
        {hasResult && !promptDecision && !alreadyStamped && (
          <div
            data-testid="audit-action-buttons"
            className="flex flex-wrap items-center gap-3"
            role="group"
            aria-label="Audit trail actions"
          >
            <button
              data-testid="mark-reviewed-btn"
              onClick={() => handleActionClick('reviewed')}
              className="inline-flex items-center gap-2 px-4 py-2 text-[11.5px] font-semibold text-[#2a2520] bg-white border border-[#ccc9c3] hover:bg-[#f4f3f0] hover:border-[#9c9790] transition-colors"
              aria-label="Mark this result as reviewed"
            >
              <ClipboardCheck className="w-3.5 h-3.5" />
              Mark as Reviewed
            </button>
            <button
              data-testid="mark-actioned-btn"
              onClick={() => handleActionClick('actioned')}
              className="inline-flex items-center gap-2 px-4 py-2 text-[11.5px] font-semibold text-white bg-[#2a2520] border border-[#2a2520] hover:bg-[#3a3530] transition-colors"
              aria-label="Mark this result as actioned"
            >
              <Zap className="w-3.5 h-3.5" />
              Mark as Actioned
            </button>
          </div>
        )}

        {/* Re-stamp affordance: show button when already stamped to allow adding second decision */}
        {hasResult && !promptDecision && alreadyStamped && (
          <div className="flex flex-wrap gap-3">
            {latestEntryForResult?.decision !== 'actioned' && (
              <button
                data-testid="mark-actioned-btn"
                onClick={() => handleActionClick('actioned')}
                className="inline-flex items-center gap-2 px-4 py-2 text-[11.5px] font-semibold text-white bg-[#2a2520] border border-[#2a2520] hover:bg-[#3a3530] transition-colors"
                aria-label="Mark this result as actioned"
              >
                <Zap className="w-3.5 h-3.5" />
                Mark as Actioned
              </button>
            )}
          </div>
        )}

        {/* ------------------------------------------------------------------
            Note prompt — shown when an action button was clicked
        ------------------------------------------------------------------ */}
        {promptDecision && (
          <NotePrompt
            decision={promptDecision}
            onConfirm={handleNoteConfirm}
            onCancel={handleNoteCancel}
          />
        )}

        {/* ------------------------------------------------------------------
            Pre-run state: no result available yet
        ------------------------------------------------------------------ */}
        {!hasResult && !promptDecision && (
          <p className="text-[12.5px] text-[#888888]">
            Run a scenario above to enable audit trail actions.
          </p>
        )}

      </div>

      {/* ------------------------------------------------------------------
          Collapsible Audit Log — all entries for the active client
      ------------------------------------------------------------------ */}
      <div className="border-t border-[#e8e5e0]">
        {/* Toggle header */}
        <button
          data-testid="audit-log-toggle"
          onClick={() => setIsLogExpanded((prev) => !prev)}
          className="w-full flex items-center justify-between px-6 py-3 text-[11px] uppercase tracking-[0.14em] font-mono text-[#767676] hover:bg-[#faf9f6] transition-colors"
          aria-expanded={isLogExpanded}
          aria-controls="audit-log-body"
        >
          <span>
            Audit Log
            {clientEntries.length > 0 && (
              <span className="ml-2 text-[#aaaaaa]">({clientEntries.length})</span>
            )}
          </span>
          {isLogExpanded ? (
            <ChevronUp className="w-3.5 h-3.5" />
          ) : (
            <ChevronDown className="w-3.5 h-3.5" />
          )}
        </button>

        {/* Log body */}
        {isLogExpanded && (
          <div
            id="audit-log-body"
            data-testid="audit-log-body"
            className="px-6 pb-5"
          >
            {clientEntries.length === 0 ? (
              <p className="text-[12px] text-[#888888] py-2">
                No audit entries recorded this session.
              </p>
            ) : (
              <div>
                {clientEntries.map((entry, i) => (
                  <AuditLogEntry key={`${entry.result_id}-${entry.timestamp}`} entry={entry} index={i} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AuditTrailPanel;
