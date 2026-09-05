import React, { useState } from 'react';
import { ArrowRight, Search, ShieldAlert, SlidersHorizontal, CheckCircle2 } from 'lucide-react';
import { ClientDossier, RiskSeverity } from '../types';

interface ClientsListViewProps {
  clients: ClientDossier[];
  onSelectClient: (clientId: string) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  riskFilteringAvailable?: boolean;
}

export const ClientsListView: React.FC<ClientsListViewProps> = ({
  clients,
  onSelectClient,
  searchQuery,
  onSearchChange,
  riskFilteringAvailable = true,
}) => {
  const [selectedRisk, setSelectedRisk] = useState<RiskSeverity | 'ALL'>('ALL');

  const filteredClients = clients.filter((c) => {
    const matchesSearch =
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.ref.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.mandate.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.headlineIssue.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesRisk = !riskFilteringAvailable || selectedRisk === 'ALL' || c.riskLevel === selectedRisk;
    return matchesSearch && matchesRisk;
  });

  return (
    <div id="clients-list-view" className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-baseline justify-between border-b border-[#e8e5e0] pb-4 gap-2">
        <div>
          <span className="text-[10px] uppercase tracking-[0.14em] font-medium text-[#767676] block mb-1">
            MANDATE DIRECTORY &amp; COVERAGE BOOK
          </span>
          <h2 className="font-serif text-[26px] text-[#121212]">Coverage Book</h2>
          <p className="text-[12.5px] text-[#666666] mt-0.5">
            Active relationship manager accounts, risk tolerances, and custody valuations.
          </p>
        </div>

        {/* Filter Controls */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {riskFilteringAvailable ? (['ALL', 'CRITICAL', 'HIGH', 'MEDIUM'] as const).map((r) => (
            <button
              key={r}
              onClick={() => setSelectedRisk(r)}
              className={`px-2.5 py-1 text-[11px] font-mono border transition-colors ${
                selectedRisk === r
                  ? 'bg-[#121212] text-white border-[#121212]'
                  : 'bg-white text-[#666666] border-[#e8e5e0] hover:border-[#121212]'
              }`}
            >
              {r}
            </button>
          )) : <span className="text-[11px] font-mono text-[#888888]">Risk filtering unavailable</span>}
        </div>
      </div>

      {/* Client Table / Card Grid */}
      <div className="bg-white border border-[#e8e5e0] divide-y divide-[#f0eee9] shadow-2xs">
        {filteredClients.map((client) => {
          const isCritical = client.riskLevel === 'CRITICAL';
          const isHigh = client.riskLevel === 'HIGH';

          return (
            <div
              key={client.id}
              onClick={() => onSelectClient(client.id)}
              className="p-5 sm:p-6 hover:bg-[#faf9f6] transition-colors cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-4 group"
            >
              {/* Identity & Issue */}
              <div className="flex items-start gap-3.5">
                <div
                  className={`w-10 h-10 font-mono text-[13px] font-medium flex items-center justify-center shrink-0 border ${
                    isCritical
                      ? 'bg-[#fcf5f5] text-[#7A1C28] border-[#eed6d9]'
                      : isHigh
                      ? 'bg-[#fdf8f0] text-[#9E6B20] border-[#f4e4cc]'
                      : 'bg-[#faf9f6] text-[#121212] border-[#e8e5e0]'
                  }`}
                >
                  {client.initials}
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-serif text-[17px] text-[#121212] group-hover:underline underline-offset-4">
                      {client.name}
                    </h3>
                    <span className="text-[#dedbd5]">•</span>
                    <span className="text-[12px] text-[#767676]">{client.mandate}</span>
                  </div>

                  <p
                    className={`text-[12.5px] mt-1 ${
                      isCritical ? 'text-[#7A1C28] font-medium' : 'text-[#555555]'
                    }`}
                  >
                    {client.headlineIssue || 'No priority finding calculated'}
                  </p>
                </div>
              </div>

              {/* Financial Summary & Actions */}
              <div className="flex items-center justify-between md:justify-end gap-6 shrink-0 pt-2 md:pt-0 border-t md:border-t-0 border-[#f4f3f0]">
                <div className="text-left md:text-right">
                  <div className="font-mono text-[13px] font-medium text-[#121212]">
                    {client.aum}
                  </div>
                  <div className="text-[11px] text-[#888888] font-mono">
                    LTV: {client.portfolio.borrowingLtvPercent === null ? 'Not calculated' : `${client.portfolio.borrowingLtvPercent}%`}
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span
                    className={`px-2 py-0.5 text-[9.5px] font-mono uppercase tracking-[0.08em] font-medium border ${
                      isCritical
                        ? 'bg-[#fcf5f5] text-[#7A1C28] border-[#eed6d9]'
                        : isHigh
                        ? 'bg-[#fdf8f0] text-[#9E6B20] border-[#f4e4cc]'
                        : 'bg-[#faf9f6] text-[#666666] border-[#dedbd5]'
                    }`}
                  >
                    {client.riskLevel || 'NOT CALCULATED'}
                  </span>

                  <ArrowRight className="w-4 h-4 text-[#888888] group-hover:text-[#121212] group-hover:translate-x-1 transition-all" />
                </div>
              </div>
            </div>
          );
        })}

        {filteredClients.length === 0 && (
          <div className="p-12 text-center text-[#888888]">
            <p className="text-[14px]">No clients found matching the search criteria.</p>
          </div>
        )}
      </div>
    </div>
  );
};
