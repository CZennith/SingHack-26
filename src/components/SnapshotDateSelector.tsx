import React from 'react';
import { useWealthData } from '../services/WealthDataContext';

export const SnapshotDateSelector: React.FC = () => {
  const { mode, dates, datesLoading, asOfDate, comparisonDate, dateError, setAsOfDate, setComparisonDate } = useWealthData();

  if (mode === 'mock') {
    return <span className="text-[10px] font-mono text-[#888888]">Fixture mode · no live date selection</span>;
  }
  if (datesLoading) return <span className="text-[11px] font-mono text-[#767676]">Loading snapshot dates…</span>;
  if (dateError) return <span className="text-[11px] font-mono text-[#7A1C28]">Date error: {dateError}</span>;
  if (!dates.length) return <span className="text-[11px] font-mono text-[#767676]">No snapshot dates available</span>;

  return (
    <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono">
      <label className="flex items-center gap-1.5">
        <span className="text-[#767676] uppercase tracking-[0.08em]">As of</span>
        <select value={asOfDate} onChange={(event) => setAsOfDate(event.target.value)} className="bg-white border border-[#dedbd5] px-2 py-1 text-[#121212]">
          {dates.map((item) => <option key={item.as_of_date} value={item.as_of_date}>{item.as_of_date}</option>)}
        </select>
      </label>
      <label className="flex items-center gap-1.5">
        <span className="text-[#767676] uppercase tracking-[0.08em]">Compare</span>
        <select value={comparisonDate} onChange={(event) => setComparisonDate(event.target.value)} className="bg-white border border-[#dedbd5] px-2 py-1 text-[#121212]">
          {dates.filter((item) => item.as_of_date !== asOfDate).map((item) => <option key={item.as_of_date} value={item.as_of_date}>{item.as_of_date}</option>)}
        </select>
      </label>
    </div>
  );
};
