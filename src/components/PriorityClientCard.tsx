import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ChevronDown, ChevronUp, ArrowRight, ExternalLink } from 'lucide-react';
import { ClientDossier } from '../types';

interface PriorityClientCardProps {
  client: ClientDossier;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onSelectClient: (clientId: string) => void;
}

export const PriorityClientCard: React.FC<PriorityClientCardProps> = ({
  client,
  isExpanded,
  onToggleExpand,
  onSelectClient,
}) => {
  const isCritical = client.riskLevel === 'CRITICAL';
  const isHigh = client.riskLevel === 'HIGH';

  // Card border highlight based on risk & expanded state
  const borderHoverClass = isCritical
    ? 'hover:border-[#7A1C28]'
    : isHigh
    ? 'hover:border-[#9E6B20]'
    : 'hover:border-[#121212]';

  const activeBorderClass = isExpanded
    ? isCritical
      ? 'border-[#7A1C28] ring-1 ring-[#7A1C28]/20'
      : isHigh
      ? 'border-[#9E6B20] ring-1 ring-[#9E6B20]/20'
      : 'border-[#121212]'
    : 'border-[#e8e5e0]';

  return (
    <article
      id={`client-card-${client.id}`}
      className={`bg-[#ffffff] border transition-all duration-200 shadow-2xs group ${activeBorderClass} ${borderHoverClass}`}
    >
      {/* Top Header Row (Always visible) */}
      <div className="p-5 sm:p-6 pb-4">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          {/* Avatar & Core Identity */}
          <div className="flex items-start gap-3.5">
            <button
              type="button"
              onClick={() => onSelectClient(client.id)}
              className={`w-10 h-10 font-mono text-[13px] font-medium flex items-center justify-center shrink-0 border transition-transform group-hover:scale-105 cursor-pointer ${
                isCritical
                  ? 'bg-[#fcf5f5] text-[#7A1C28] border-[#eed6d9]'
                  : isHigh
                  ? 'bg-[#fdf8f0] text-[#9E6B20] border-[#f4e4cc]'
                  : 'bg-[#faf9f6] text-[#121212] border-[#e8e5e0]'
              }`}
              title="Click to view client dossier"
            >
              {client.initials}
            </button>

            <div>
              <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1">
                <button
                  type="button"
                  onClick={() => onSelectClient(client.id)}
                  className={`font-serif text-[18px] text-[#121212] font-medium text-left hover:underline underline-offset-4 cursor-pointer ${
                    isCritical ? 'group-hover:text-[#7A1C28]' : 'group-hover:text-black'
                  }`}
                >
                  {client.name}
                </button>
                <span className="text-[#dedbd5] hidden sm:inline">•</span>
                <span className="text-[12px] text-[#767676]">
                  {client.tier} · {client.mandate} ·{' '}
                  <span className="font-mono text-[#121212] font-medium">{client.aum} AUM</span>
                </span>
              </div>

              {/* Headline Issue */}
              <p
                className={`text-[13px] font-medium mt-1 ${
                  isCritical ? 'text-[#7A1C28]' : 'text-[#121212]'
                }`}
              >
                {client.headlineIssue}
              </p>
            </div>
          </div>

          {/* Right Risk Badges & Expand Control */}
          <div className="flex items-center gap-2.5 self-end sm:self-start shrink-0">
            <span
              className={`px-2 py-0.5 text-[9.5px] font-mono uppercase tracking-[0.08em] font-medium border ${
                isCritical
                  ? 'bg-[#fcf5f5] text-[#7A1C28] border-[#eed6d9]'
                  : isHigh
                  ? 'bg-[#fdf8f0] text-[#9E6B20] border-[#f4e4cc]'
                  : 'bg-[#faf9f6] text-[#666666] border-[#dedbd5]'
              }`}
            >
              {client.riskLevel}
            </span>

            <span className="text-[9.5px] uppercase tracking-[0.14em] text-[#888888] font-medium hidden md:inline">
              REF: {client.ref}
            </span>

            {/* Toggle Collapse Button */}
            <button
              type="button"
              id={`toggle-expand-${client.id}`}
              onClick={(e) => {
                e.stopPropagation();
                onToggleExpand();
              }}
              className="p-1 text-[#666666] hover:text-[#121212] hover:bg-[#faf9f6] border border-[#e8e5e0] transition-colors ml-1"
              aria-label={isExpanded ? 'Collapse section' : 'Expand section'}
              title={isExpanded ? 'Collapse detail' : 'Expand detail'}
            >
              {isExpanded ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>

        {/* Collapsed view preview tags */}
        {!isExpanded && (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-[#f4f3f0]">
            <div className="flex flex-wrap items-center gap-1.5">
              {client.tags.slice(0, 2).map((tag, idx) => (
                <span
                  key={idx}
                  className="px-2 py-0.5 bg-[#faf9f6] text-[#666666] font-mono text-[10.5px] border border-[#e8e5e0]"
                >
                  {tag}
                </span>
              ))}
              {client.tags.length > 2 && (
                <span className="text-[10.5px] text-[#888888] font-mono">
                  +{client.tags.length - 2} more
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onToggleExpand}
                className="text-[11.5px] text-[#767676] hover:text-[#121212] underline underline-offset-4"
              >
                Show details
              </button>
              <button
                type="button"
                onClick={() => onSelectClient(client.id)}
                className="inline-flex items-center gap-1 text-[11.5px] font-medium text-[#121212] hover:underline underline-offset-4"
              >
                <span>Dossier</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Collapsible Section (Detailed view when active) */}
      <AnimatePresence initial={false}>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: 'easeInOut' }}
            className="overflow-hidden border-t border-[#e8e5e0] bg-[#faf9f6]/40"
          >
            <div className="p-5 sm:p-6 pt-4 space-y-4">
              {/* Detailed Summary Narrative */}
              <p className="text-[13px] text-[#555555] leading-relaxed">
                {client.summary}
              </p>

              {/* Full Tags List */}
              <div className="flex flex-wrap items-center gap-1.5">
                {client.tags.map((tag, idx) => {
                  const isRiskTag = tag.includes('+') || tag.includes('breach');
                  return (
                    <span
                      key={idx}
                      className={`px-2 py-0.5 font-mono text-[11px] border ${
                        isRiskTag
                          ? 'bg-[#fcf5f5] text-[#7A1C28] border-[#eed6d9]'
                          : 'bg-[#faf9f6] text-[#121212] border-[#e8e5e0]'
                      }`}
                    >
                      {tag}
                    </span>
                  );
                })}
              </div>

              {/* Collateral & Key Metrics Quick Strip */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 p-3 bg-white border border-[#e8e5e0] text-[11.5px]">
                <div>
                  <span className="text-[#888888] text-[10px] uppercase font-mono block">
                    Cash Liquidity
                  </span>
                  <span className="font-serif text-[14px] text-[#121212]">
                    {client.portfolio.cashLiquidity}
                  </span>
                  <span className="text-[10px] text-[#666666] ml-1 font-mono">
                    ({client.portfolio.cashLiquidityPercent})
                  </span>
                </div>

                <div>
                  <span className="text-[#888888] text-[10px] uppercase font-mono block">
                    Lombard / Borrowing
                  </span>
                  <span className="font-serif text-[14px] text-[#121212]">
                    {client.portfolio.borrowingUtilisation}
                  </span>
                  <span className="text-[10px] text-[#666666] ml-1 font-mono">
                    ({client.portfolio.borrowingLtvPercent}% LTV)
                  </span>
                </div>

                <div className="col-span-2 sm:col-span-1 flex flex-col justify-center">
                  <div className="flex items-center justify-between text-[10px] text-[#888888] font-mono mb-1">
                    <span>LTV Utilization</span>
                    <span>{client.portfolio.borrowingLtvPercent}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-[#f4f3f0] overflow-hidden">
                    <div
                      className={`h-full ${
                        client.portfolio.borrowingLtvPercent > 60
                          ? 'bg-[#7A1C28]'
                          : 'bg-[#121212]'
                      }`}
                      style={{ width: `${Math.min(client.portfolio.borrowingLtvPercent, 100)}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Suggested Next Step Action Ribbon */}
              <div
                onClick={() => onSelectClient(client.id)}
                className={`border px-4 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 cursor-pointer transition-colors ${
                  isCritical
                    ? 'bg-[#fcf5f5] border-[#eed6d9] hover:bg-[#faeded]'
                    : 'bg-[#faf9f6] border-[#e8e5e0] hover:bg-[#f0eee9]'
                }`}
              >
                <div className="flex items-start sm:items-center gap-2 text-[12.5px] text-[#121212]">
                  <span
                    className={`font-semibold shrink-0 ${
                      isCritical ? 'text-[#7A1C28]' : 'text-[#121212]'
                    }`}
                  >
                    Suggested next step:
                  </span>
                  <span className="text-[#555555]">{client.suggestedNextStep}</span>
                </div>

                <div className="flex items-center gap-1.5 text-[11px] font-medium text-[#121212] shrink-0 self-end sm:self-center">
                  <span className="uppercase tracking-[0.08em]">Open Dossier</span>
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                </div>
              </div>

              {/* Primary Direct Navigation Button */}
              <div className="flex justify-end pt-1">
                <button
                  type="button"
                  id={`view-dossier-btn-${client.id}`}
                  onClick={() => onSelectClient(client.id)}
                  className="px-4 py-1.5 bg-[#121212] hover:bg-neutral-800 text-[#faf9f6] text-[11px] font-medium uppercase tracking-[0.12em] flex items-center gap-2 transition-colors cursor-pointer"
                >
                  <span>View Full Client Page</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </article>
  );
};
