import React from 'react';
import { macroIndicators, marketImpactPillars } from '../data/placeholderData';

interface MarketImpactSectionProps {
  onSelectClientByName?: (clientName: string) => void;
  marketContext?: Array<Record<string, unknown>>;
  live?: boolean;
  asOfDate?: string;
}

export const MarketImpactSection: React.FC<MarketImpactSectionProps> = ({
  onSelectClientByName,
  marketContext = [],
  live = false,
  asOfDate,
}) => {
  const indicators = live
    ? marketContext.slice(0, 6).map((item, index) => ({
        id: String(item.series_id ?? index),
        label: String(item.series_name ?? item.series_id ?? 'Market context'),
        value: item.value == null ? 'Not available' : String(item.value),
        subtext: item.unit ? String(item.unit) : undefined,
      }))
    : macroIndicators;
  const pillars = live ? [] : marketImpactPillars;
  return (
    <section id="section-market-impact" className="space-y-4">
      {/* Section Header */}
      <div className="flex items-center justify-between border-b border-[#e8e5e0] pb-3">
        <div className="flex items-center gap-2.5">
          <span className="text-[10px] uppercase tracking-[0.14em] font-medium text-[#767676]">
            SECTION 01 · Market &amp; Portfolio Impact
          </span>
        </div>
        <div className="flex items-center gap-2 font-mono text-[11px] text-[#767676]">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse" />
          <span>{live ? `Raw market context · ${asOfDate || 'loading'}` : 'Fixture snapshot · 26 Aug 2026'}</span>
        </div>
      </div>

      {/* Main Container */}
      <div className="bg-[#ffffff] border border-[#e8e5e0] p-6 space-y-6 shadow-2xs">
        {/* Top Macro Tickers Bar */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between pb-5 border-b border-[#f0eee9] gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <h2 className="font-serif text-[20px] text-[#121212]">
                Market &amp; Portfolio Impact
              </h2>
              <span className="px-2 py-0.5 text-[9px] uppercase tracking-[0.08em] font-medium bg-[#faf9f6] border border-[#e8e5e0] text-[#666666]">
                Book-Wide Scan
              </span>
            </div>
            <p className="text-[12.5px] text-[#666666] mt-1">
              {live
                ? 'Dated market-context records returned by the backend. Portfolio impact narratives are not calculated.'
                : 'Synthetic market and event snapshots mapped to affected accounts and collateral lines.'}
            </p>
          </div>

          {/* Quick Macro Tickers */}
          <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono">
            {indicators.map((item) => {
              if (item.highlightColor === 'red') {
                return (
                  <div
                    key={item.id}
                    className="px-2.5 py-1 bg-[#fcf5f5] border border-[#eed6d9] text-[#7A1C28]"
                  >
                    <span className="text-[9.5px] uppercase mr-1.5">{item.label}</span>
                    <span className="font-medium">{item.value}</span>
                    {item.change && <span className="ml-1 text-[10px]">({item.change})</span>}
                  </div>
                );
              }
              if (item.highlightColor === 'amber') {
                return (
                  <div
                    key={item.id}
                    className="px-2.5 py-1 bg-[#fdf8f0] border border-[#f4e4cc] text-[#9E6B20]"
                  >
                    <span className="text-[9.5px] uppercase mr-1.5">{item.label}</span>
                    <span className="font-medium">{item.value}</span>
                    {item.change && <span className="ml-1 text-[10px]">{item.change}</span>}
                  </div>
                );
              }
              return (
                <div
                  key={item.id}
                  className="px-2.5 py-1 bg-[#faf9f6] border border-[#e8e5e0] text-[#121212]"
                >
                  <span className="text-[#767676] text-[9.5px] uppercase mr-1.5">
                    {item.label}
                  </span>
                  <span className="font-medium">{item.value}</span>
                  {item.subtext && (
                    <span className="text-[#888888] text-[10px] ml-1">{item.subtext}</span>
                  )}
                  {item.change && (
                    <span className="text-[#7A1C28] text-[10px] ml-1">{item.change}</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* 3 Structured Intelligence Pillars */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {pillars.map((pillar) => {
            const isRed = pillar.badgeStyle === 'red';
            const isAmber = pillar.badgeStyle === 'amber';

            return (
              <article
                key={pillar.id}
                className="bg-[#faf9f6] border border-[#e8e5e0] p-4 flex flex-col justify-between hover:border-[#121212] transition-colors"
              >
                <div>
                  {/* Category Header */}
                  <div className="flex items-center justify-between gap-2 mb-2.5">
                    <div className="flex items-center gap-1.5">
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${
                          isRed
                            ? 'bg-[#7A1C28]'
                            : isAmber
                            ? 'bg-[#9E6B20]'
                            : 'bg-[#121212]'
                        }`}
                      />
                      <span className="text-[9.5px] uppercase tracking-[0.14em] text-[#767676] font-medium">
                        {pillar.category}
                      </span>
                    </div>

                    <span
                      className={`px-2 py-0.5 text-[9.5px] font-mono font-medium border ${
                        isRed
                          ? 'bg-[#fcf5f5] text-[#7A1C28] border-[#eed6d9]'
                          : isAmber
                          ? 'bg-[#fdf8f0] text-[#9E6B20] border-[#f4e4cc]'
                          : 'bg-[#f4f3f0] text-[#121212] border-[#dedbd5]'
                      }`}
                    >
                      {pillar.affectedCount} {pillar.affectedCount === 1 ? 'Client' : 'Clients'} Affected
                    </span>
                  </div>

                  {/* Title */}
                  <h3 className="font-serif text-[15px] font-semibold text-[#121212] leading-snug mb-2">
                    {pillar.title}
                  </h3>

                  {/* Narrative Body */}
                  <div className="space-y-2.5 mb-3 text-[12px] text-[#555555] leading-relaxed">
                    <p>
                      <strong className="text-[#121212] font-medium">Portfolio Impact: </strong>
                      {pillar.portfolioImpact}
                    </p>
                    <div className="p-2.5 bg-[#ffffff] border border-[#e8e5e0] text-[11px] font-mono text-[#666666]">
                      <span className="font-medium text-[#121212]">Desk Context: </span>
                      {pillar.deskContext}
                    </div>
                  </div>
                </div>

                {/* Affected Accounts Footer */}
                <div className="pt-3 border-t border-[#e8e5e0]">
                  <div className="text-[9px] uppercase tracking-[0.14em] text-[#888888] font-medium mb-1.5">
                    Affected Coverage Accounts
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {pillar.affectedClientNames.map((clientName, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => onSelectClientByName && onSelectClientByName(clientName)}
                        className="px-2 py-0.5 bg-[#ffffff] hover:bg-[#121212] hover:text-[#faf9f6] text-[#121212] text-[11px] border border-[#dedbd5] transition-colors cursor-pointer"
                        title={`View dossier for ${clientName}`}
                      >
                        {clientName}
                      </button>
                    ))}
                  </div>
                </div>
              </article>
            );
          })}
          {live && (
            <article className="lg:col-span-3 bg-[#faf9f6] border border-[#e8e5e0] p-4">
              <h3 className="font-serif text-[15px] font-semibold text-[#121212] mb-2">
                Portfolio impact analysis unavailable
              </h3>
              <p className="text-[12px] text-[#666666] leading-relaxed">
                The backend currently exposes dated market context only; no affected-account narrative or recommendation is fabricated here.
              </p>
            </article>
          )}
        </div>
      </div>
    </section>
  );
};
