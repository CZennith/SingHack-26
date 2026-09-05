/**
 * WorkbenchBreadcrumb — back navigation and client switcher for the Stress Workbench.
 *
 * Requirements: 1.6, 1.7
 *
 * - In client mode: shows "← Back to [Client Name]" and a client switcher <select>
 * - In book-wide mode: shows "← Overview" only
 */

import React from 'react';
import type { ClientDossier } from '../types';

export interface WorkbenchBreadcrumbProps {
  mode: 'client' | 'book-wide';
  activeClient: ClientDossier | null;
  allClients: ClientDossier[];
  clientId: string | null;
  onBack: () => void;
  onSelectClient: (clientId: string) => void;
}

export const WorkbenchBreadcrumb: React.FC<WorkbenchBreadcrumbProps> = ({
  mode,
  activeClient,
  allClients,
  clientId,
  onBack,
  onSelectClient,
}) => {
  const backLabel =
    mode === 'client' && activeClient
      ? `← Back to ${activeClient.name}`
      : '← Overview';

  return (
    <div className="flex flex-wrap items-center gap-4 py-2">
      {/* Back navigation */}
      <button
        type="button"
        onClick={onBack}
        className="text-[12px] text-[#767676] hover:text-[#121212] hover:underline transition-colors focus:outline-none"
      >
        {backLabel}
      </button>

      {/* Client switcher — client mode only */}
      {mode === 'client' && allClients.length > 0 && (
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-[0.14em] text-[#767676]">
            Switch client:
          </span>
          <select
            value={clientId ?? ''}
            onChange={(e) => onSelectClient(e.target.value)}
            className="text-[12px] font-mono border border-[#e8e5e0] bg-[#faf9f6] px-2 py-1 text-[#121212] focus:outline-none"
          >
            {allClients.map((client) => (
              <option key={client.id} value={client.id}>
                {client.ref} · {client.name}
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
};
