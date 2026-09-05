import React, { useState } from 'react';
import {
  ArrowLeft,
  User,
  Briefcase,
  ShieldCheck,
  FileText,
  Database,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { ClientDossier } from '../types';

interface ClientDetailPageProps {
  client: ClientDossier;
  onBack: () => void;
  onPrepareBrief: (client: ClientDossier) => void;
  onViewSourceData: () => void;
  onSelectAnotherClient: (clientId: string) => void;
  allClients: ClientDossier[];
}

export const ClientDetailPage: React.FC<ClientDetailPageProps> = ({
  client,
  onBack,
  onPrepareBrief,
  onViewSourceData,
  onSelectAnotherClient,
  allClients,
}) => {
  const currentIndex = allClients.findIndex((c) => c.id === client.id);
  const prevClient = currentIndex > 0 ? allClients[currentIndex - 1] : null;
  const nextClient = currentIndex < allClients.length - 1 ? allClients[currentIndex + 1] : null;
  const points = client.portfolio.trajectory.points;
  const trajectoryPath = points.length > 1
    ? points.map((point, index) => {
        const values = points.map((item) => item.value);
        const min = Math.min(...values);
        const max = Math.max(...values);
        const x = 10 + (480 * index) / (points.length - 1);
        const y = max === min ? 60 : 18 + ((max - point.value) / (max - min)) * 77;
        return `${index === 0 ? 'M' : 'L'} ${x} ${y}`;
      }).join(' ')
    : '';
  const topHoldingsPercent = client.portfolio.topHoldings.reduce((total, holding) => total + holding.percentage, 0);

  return (
    <div id="client-detail-view" className="w-full min-h-screen bg-[#faf9f6]">
      {/* Top Floating RM Profile Tag (as in Image 3 top right) */}
      <div className="hidden md:flex fixed top-4 right-8 z-20 items-center gap-3 bg-[#faf9f6]/90 backdrop-blur-xs py-1 px-2 border border-[#e8e5e0]">
        <div className="text-right">
          <div className="text-[12px] font-medium text-[#121212] leading-none">{client.relationshipManager?.name ?? 'Relationship manager pending'}</div>
          <div className="text-[10px] text-[#767676] mt-0.5 leading-none">Relationship Manager</div>
        </div>
        <div className="w-7 h-7 rounded-full border border-[#dedbd5] bg-white flex items-center justify-center text-[#121212] shadow-2xs">
          <span className="font-serif text-[11px] italic font-semibold">A</span>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 sm:px-10 pt-8 pb-24 space-y-10">
        {/* Navigation Bar & Header */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <button
              id="back-to-dashboard-btn"
              type="button"
              onClick={onBack}
              className="inline-flex items-center gap-1.5 text-[12px] text-[#767676] hover:text-[#121212] transition-colors cursor-pointer group"
            >
              <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform" />
              <span>Back to Dashboard</span>
            </button>

            {/* Client switcher quick navigation */}
            <div className="flex items-center gap-2 text-[11px] font-mono text-[#767676]">
              {prevClient && (
                <button
                  onClick={() => onSelectAnotherClient(prevClient.id)}
                  className="hover:text-[#121212] hover:underline flex items-center gap-0.5"
                >
                  <ChevronLeft className="w-3 h-3" />
                  <span>Prev</span>
                </button>
              )}
              {prevClient && nextClient && <span>|</span>}
              {nextClient && (
                <button
                  onClick={() => onSelectAnotherClient(nextClient.id)}
                  className="hover:text-[#121212] hover:underline flex items-center gap-0.5"
                >
                  <span>Next</span>
                  <ChevronRight className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>

          <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 pt-1">
            <div>
              <h1 className="font-serif text-[34px] sm:text-[38px] leading-tight text-[#121212] font-normal tracking-tight">
                {client.name}
              </h1>
              <p className="text-[12.5px] text-[#666666] mt-1.5 tracking-wide font-normal">
                {client.tier} &nbsp;·&nbsp; {client.mandate} &nbsp;·&nbsp;{' '}
                <span className="font-mono text-[#121212] font-medium">{client.aum} AUM</span>
              </p>
            </div>

            <div className="pt-2 shrink-0">
              <span className="text-[10px] tracking-[0.14em] uppercase font-semibold text-[#55534e] border border-[#dedbd5] bg-white px-2.5 py-1">
                ADVISORY INTELLIGENCE &nbsp;·&nbsp; Ref: {client.ref}
              </span>
            </div>
          </div>
        </div>

        {/* SECTION 01 · INTELLIGENCE OVERVIEW */}
        <section className="space-y-3">
          <div className="flex items-center justify-between border-b border-[#e8e5e0] pb-2">
            <span className="text-[10px] tracking-[0.16em] uppercase font-semibold text-[#8c887f]">
              SECTION 01 · INTELLIGENCE OVERVIEW
            </span>
            <span className="text-[11px] text-[#55534e] flex items-center gap-1.5 font-mono">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse" />
              Snapshot · {client.asOf ?? 'pending'}
            </span>
          </div>

          <div className="bg-white border border-[#e8e5e0] p-6 sm:p-7 shadow-2xs">
            <h2 className="font-serif text-[21px] text-[#121212] font-normal mb-3">
              About {client.name.split(' ')[0]}
            </h2>
            <p className="text-[14px] leading-[23px] text-[#55534e] font-normal max-w-4xl">
              {client.about.bio}
            </p>

            {client.profileSummary && (
              <div className="mt-5 border-l-2 border-[#2c6e6a] bg-[#f9f8f5] px-4 py-3">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-[12.5px] font-medium text-[#121212]">{client.profileSummary.title}</span>
                  <span className="text-[10px] text-[#8c887f] font-mono">AI-generated · {client.profileSummary.generatedAt}</span>
                </div>
                <p className="mt-1 text-[12.5px] leading-relaxed text-[#55534e]">{client.profileSummary.summary}</p>
              </div>
            )}

            <div className="flex flex-wrap items-center gap-4 mt-6 pt-5 border-t border-[#e8e5e0] text-[12px] text-[#666666]">
              <span className="inline-flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-[#8c887f]" />
                {client.about.age} years old
              </span>
              <span className="text-[#dedbd5]">·</span>
              <span className="inline-flex items-center gap-1.5">
                <Briefcase className="w-3.5 h-3.5 text-[#8c887f]" />
                {client.about.occupation}
              </span>
              <span className="text-[#dedbd5]">·</span>
              <span className="inline-flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-[#8c887f]" />
                Client since {client.about.clientSince}
              </span>
            </div>
          </div>
        </section>

        {/* SECTION 02 · CUSTODY & LIQUIDITY */}
        <section className="space-y-4">
          <div className="flex items-center justify-between border-b border-[#e8e5e0] pb-2">
            <span className="text-[10px] tracking-[0.16em] uppercase font-semibold text-[#8c887f]">
              SECTION 02 · CUSTODY &amp; LIQUIDITY
            </span>
            <span className="text-[11px] text-[#666666] font-mono">
              Valuation as of {client.valuationAsOf ?? client.asOf ?? 'pending'}
            </span>
          </div>

          <h2 className="font-serif text-[21px] text-[#121212] font-normal">Portfolio</h2>

          {/* Top 3 Metrics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Metric 1 */}
            <div className="bg-white border border-[#e8e5e0] p-5 shadow-2xs">
              <div className="text-[10px] tracking-[0.12em] uppercase font-medium text-[#8c887f] mb-2 font-mono">
                TOTAL PORTFOLIO VALUE
              </div>
              <div className="font-serif text-[28px] leading-tight text-[#121212] font-normal">
                {client.portfolio.totalValue}
              </div>
              <div className="text-[11.5px] text-[#8c887f] mt-2">
                {client.portfolio.totalValueSubtext}
              </div>
            </div>

            {/* Metric 2 */}
            <div className="bg-white border border-[#e8e5e0] p-5 shadow-2xs">
              <div className="text-[10px] tracking-[0.12em] uppercase font-medium text-[#8c887f] mb-2 font-mono">
                CASH &amp; LIQUIDITY
              </div>
              <div className="font-serif text-[28px] leading-tight text-[#121212] font-normal">
                {client.portfolio.cashLiquidity}{' '}
                <span className="text-[14px] font-sans text-[#8c887f] ml-1 font-normal">
                  ({client.portfolio.cashLiquidityPercent})
                </span>
              </div>
              <div className="text-[11.5px] text-[#8c887f] mt-2">
                {client.portfolio.cashLiquiditySubtext}
              </div>
            </div>

            {/* Metric 3 */}
            <div className="bg-white border border-[#e8e5e0] p-5 shadow-2xs">
              <div className="flex items-start justify-between">
                <div className="text-[10px] tracking-[0.12em] uppercase font-medium text-[#8c887f] mb-2 font-mono">
                  BORROWING / FACILITY UTILISATION
                </div>
                <span
                  className={`text-[9.5px] tracking-wider uppercase px-2 py-0.5 rounded-full font-medium font-mono ${
                    client.portfolio.borrowingStatus === 'CRITICAL'
                      ? 'bg-[#fcf5f5] text-[#7A1C28] border border-[#eed6d9]'
                      : client.portfolio.borrowingStatus === 'ELEVATED'
                      ? 'bg-[#fdf8f0] text-[#9E6B20] border border-[#f4e4cc]'
                      : 'bg-[#faf9f6] text-[#666666] border border-[#dedbd5]'
                  }`}
                >
                  {client.portfolio.borrowingStatus}
                </span>
              </div>
              <div className="font-serif text-[28px] leading-tight text-[#121212] font-normal">
                {client.portfolio.borrowingUtilisation}{' '}
                <span className="text-[13px] font-sans text-[#8c887f] ml-1 font-normal">
                  ({client.portfolio.borrowingLtvPercent}% of LTV)
                </span>
              </div>

              {/* Progress Bar */}
              <div className="w-full h-1.5 bg-[#f4f3f0] rounded-full mt-3 overflow-hidden">
                <div
                  className={`h-full ${
                    client.portfolio.borrowingLtvPercent > 60
                      ? 'bg-[#121212]'
                      : 'bg-[#55534e]'
                  }`}
                  style={{ width: `${Math.min(client.portfolio.borrowingLtvPercent, 100)}%` }}
                />
              </div>
            </div>
          </div>

          {/* Allocation & Top Holdings Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 pt-1">
            {/* Left: Asset Allocation & Trajectory (7 cols) */}
            <div className="lg:col-span-7 space-y-5">
              {/* Asset Allocation Card */}
              <div className="bg-white border border-[#e8e5e0] p-5 shadow-2xs">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[10px] tracking-[0.12em] uppercase font-semibold text-[#55534e] font-mono">
                    ASSET ALLOCATION
                  </span>
                  <span className="text-[11px] text-[#8c887f]">Target vs Realised</span>
                </div>

                {/* Allocation Segmented Bar */}
                <div className="w-full h-2.5 rounded-full overflow-hidden flex bg-[#f4f3f0]">
                  {client.portfolio.allocation.map((item, idx) => (
                    <div
                      key={idx}
                      style={{ width: `${item.percentage}%`, backgroundColor: item.color }}
                      title={`${item.label} ${item.percentage}%`}
                    />
                  ))}
                </div>

                {/* Allocation Legend */}
                <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-[11.5px] text-[#55534e] mt-3.5">
                  {client.portfolio.allocation.map((item, idx) => (
                    <span key={idx} className="flex items-center gap-1.5">
                      <span
                        className="w-2 h-2 rounded-full inline-block"
                        style={{ backgroundColor: item.color }}
                      />
                      {item.label} {item.percentage}%
                    </span>
                  ))}
                </div>
              </div>

              {/* 12-Month Trajectory Card */}
              <div className="bg-white border border-[#e8e5e0] p-5 shadow-2xs">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="text-[10px] tracking-[0.12em] uppercase font-semibold text-[#55534e] font-mono">
                      12-MONTH TRAJECTORY
                    </div>
                    <div className="text-[11px] text-[#8c887f] mt-0.5">
                      Includes recent drawdown trough and swift leverage recovery
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-[11.5px] font-semibold text-[#121212] font-mono">
                      {client.portfolio.trajectory.deltaPercent}
                    </span>
                    <div className="text-[10.5px] text-[#8c887f]">
                      {client.portfolio.trajectory.deltaPeriod}
                    </div>
                  </div>
                </div>

                {/* SVG Chart */}
                <div className="relative w-full pt-2 pb-1">
                  <svg
                    className="w-full h-28 overflow-visible"
                    preserveAspectRatio="none"
                    viewBox="0 0 500 120"
                  >
                    <defs>
                      <linearGradient id={`curveGrad-${client.id}`} x1="0" x2="0" y1="0" y2="1">
                        <stop offset="0%" stopColor="#2a2824" stopOpacity="0.14" />
                        <stop offset="100%" stopColor="#2a2824" stopOpacity="0.0" />
                      </linearGradient>
                    </defs>

                    {/* Area fill */}
                    {trajectoryPath && <path
                      d={`${trajectoryPath} L 490 115 L 10 115 Z`}
                      fill={`url(#curveGrad-${client.id})`}
                    />}

                    {/* Curve stroke */}
                    {trajectoryPath && <path
                      d={trajectoryPath}
                      fill="none"
                      stroke="#1f1d1a"
                      strokeLinecap="round"
                      strokeWidth="1.75"
                    />}

                    {/* Trough Marker */}
                    {trajectoryPath && <circle
                      cx="250"
                      cy="95"
                      fill="#ffffff"
                      r="3.5"
                      stroke="#b33939"
                      strokeWidth="1.5"
                    />}

                    {/* Endpoint Marker */}
                    {trajectoryPath && <circle cx="490" cy="18" fill="#1f1d1a" r="3" />}
                  </svg>

                  {/* Chart labels beneath */}
                  <div className="flex items-center justify-between text-[11px] pt-3 border-t border-[#e8e5e0] text-[#8c887f]">
                    <span>{client.portfolio.trajectory.startLabel}</span>
                    <span className="text-[#b33939] font-medium">
                      {client.portfolio.trajectory.troughLabel}
                    </span>
                    <span className="text-[#121212] font-medium">
                      {client.portfolio.trajectory.endLabel}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Right: Top Portfolio Holdings Table (5 cols) */}
            <div className="lg:col-span-5 bg-white border border-[#e8e5e0] p-5 flex flex-col justify-between shadow-2xs">
              <div>
                <div className="flex items-center justify-between border-b border-[#e8e5e0] pb-3 mb-2">
                  <span className="text-[10px] tracking-[0.12em] uppercase font-semibold text-[#55534e] font-mono">
                    TOP PORTFOLIO HOLDINGS
                  </span>
                  <span className="text-[11px] text-[#8c887f] font-mono">{topHoldingsPercent.toFixed(1)}% of Total</span>
                </div>

                <div className="divide-y divide-[#f0eee9]">
                  {client.portfolio.topHoldings.map((h) => (
                    <div key={h.id} className="py-3 flex items-start justify-between">
                      <div>
                        <div className="text-[13px] font-medium text-[#121212]">{h.name}</div>
                        <div className="text-[11px] text-[#8c887f]">{h.ticker}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-[12.5px] font-medium text-[#121212] font-mono">
                          {h.value}
                        </div>
                        <div className="text-[11px] text-[#8c887f] font-mono">
                          {h.percentage}%
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="pt-4 border-t border-[#e8e5e0] text-[11px] text-[#8c887f] leading-snug">
                {client.portfolio.remainingHoldingsNote}
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 03 · INTELLIGENT PORTFOLIO EXPLANATION */}
        <section className="space-y-3">
          <div className="border-b border-[#e8e5e0] pb-2">
            <span className="text-[10px] tracking-[0.16em] uppercase font-semibold text-[#8c887f]">
              SECTION 03 · PORTFOLIO EXPLANATION
            </span>
          </div>

          {/* Accent Border Synthesis Card */}
          <div className="bg-white border border-[#e8e5e0] border-l-[3px] border-l-[#121212] p-6 sm:p-7 space-y-5 shadow-2xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-[#121212] text-[15px]">✦</span>
                <h3 className="font-serif text-[20px] text-[#121212] font-normal">
                  {client.portfolioExplanation.title}
                </h3>
              </div>
              <span className="text-[11px] text-[#8c887f] font-mono">
                AI-generated · {client.portfolioExplanation.generatedAt}
              </span>
            </div>

            <p className="text-[14px] leading-[23px] text-[#121212] font-normal max-w-4xl">
              {client.portfolioExplanation.overview}
            </p>

            {/* Sub-cards: Why it Matters & Monitor */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
              <div className="bg-[#f9f8f5] border border-[#e8e5e0] p-4">
                <div className="text-[10px] tracking-[0.12em] uppercase font-semibold text-[#55534e] mb-1.5 font-mono">
                  WHAT MOVED & WHY
                </div>
                <p className="text-[12.5px] leading-relaxed text-[#55534e]">
                  {client.portfolioExplanation.whatMovedAndWhy}
                </p>
              </div>

              <div className="bg-[#f9f8f5] border border-[#e8e5e0] p-4">
                <div className="text-[10px] tracking-[0.12em] uppercase font-semibold text-[#55534e] mb-1.5 font-mono">
                  EVENTS TO MONITOR
                </div>
                <p className="text-[12.5px] leading-relaxed text-[#55534e]">
                  {client.portfolioExplanation.whatToWatch}
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 04 · PROACTIVE ADVICE (Risks & Opportunities) */}
        <section className="space-y-4">
          <div className="border-b border-[#e8e5e0] pb-2">
            <span className="text-[10px] tracking-[0.16em] uppercase font-semibold text-[#8c887f]">
              SECTION 04 · PROACTIVE ADVICE
            </span>
          </div>

          <div className="bg-white border border-[#e8e5e0] border-l-[3px] border-l-[#121212] p-6 sm:p-7 space-y-5 shadow-2xs">
            <div className="flex items-center justify-between gap-4">
              <h2 className="font-serif text-[21px] text-[#121212] font-normal">
                Risks, Opportunities &amp; Next Steps
              </h2>
              <span className="text-[10px] text-[#8c887f] font-mono shrink-0">
                AI-generated · {client.advisory.generatedAt}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
            {/* Risks Column */}
            <div className="bg-[#f9f8f5] border border-[#e8e5e0] p-4 space-y-4">
              <div className="flex items-center gap-2 pb-2 border-b border-[#e8e5e0]">
                <span className="w-1.5 h-1.5 rounded-full bg-[#b33939] inline-block" />
                <h3 className="font-serif text-[17px] text-[#121212] font-normal">Risks</h3>
              </div>

              <ul className="space-y-3.5 text-[12.5px] leading-relaxed text-[#55534e]">
                {client.advisory.risks.map((risk, idx) => (
                  <li key={idx} className="flex items-start gap-2.5">
                    <span className="text-[#b33939] text-xs mt-0.5 font-bold">•</span>
                    <span>
                      <strong className="font-medium text-[#121212]">{risk.title}: </strong>
                      {risk.description}
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Opportunities Column */}
            <div className="bg-[#f9f8f5] border border-[#e8e5e0] p-4 space-y-4">
              <div className="flex items-center gap-2 pb-2 border-b border-[#e8e5e0]">
                <span className="w-1.5 h-1.5 rounded-full bg-[#2c6e6a] inline-block" />
                <h3 className="font-serif text-[17px] text-[#121212] font-normal">
                  Opportunities
                </h3>
              </div>

              <ul className="space-y-3.5 text-[12.5px] leading-relaxed text-[#55534e]">
                {client.advisory.opportunities.map((opp, idx) => (
                  <li key={idx} className="flex items-start gap-2.5">
                    <span className="text-[#2c6e6a] text-xs mt-0.5 font-bold">•</span>
                    <span>
                      <strong className="font-medium text-[#121212]">{opp.title}: </strong>
                      {opp.description}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
            </div>
          </div>
        </section>

        {/* Bottom Action Ribbon / Document Footer */}
        <div className="pt-6 border-t border-[#e8e5e0] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-[11px] text-[#8c887f]">
          <div className="flex items-center gap-4">
            <button
              id="prepare-client-brief-btn"
              type="button"
              onClick={() => onPrepareBrief(client)}
              className="bg-[#121212] hover:bg-neutral-800 text-white text-[10px] font-medium uppercase tracking-[0.14em] px-4 py-2 flex items-center gap-2 transition-colors cursor-pointer"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Prepare client brief</span>
            </button>

            <button
              id="view-source-data-btn"
              type="button"
              onClick={onViewSourceData}
              className="text-[#666666] hover:text-[#121212] underline underline-offset-4 text-[11px] transition-colors flex items-center gap-1.5 cursor-pointer"
            >
              <Database className="w-3 h-3 text-[#8c887f]" />
              <span>View source data</span>
            </button>
          </div>

          <div className="text-right">
            <span>Confidential Memorandum · Aurelius Wealth Partners</span>
          </div>
        </div>
      </div>
    </div>
  );
};
