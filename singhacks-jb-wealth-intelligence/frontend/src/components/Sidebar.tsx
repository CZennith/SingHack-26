import React from 'react';
import { currentRM } from '../data/placeholderData';

interface SidebarProps {
  currentView: 'overview' | 'clients' | 'client-detail';
  onNavigate: (view: 'overview' | 'clients') => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  clientCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentView,
  onNavigate,
  mobileOpen,
  onCloseMobile,
  clientCount,
}) => {
  return (
    <>
      {/* Mobile backdrop */}
      {mobileOpen && (
        <div
          id="sidebar-backdrop"
          onClick={onCloseMobile}
          className="fixed inset-0 bg-black/40 z-40 lg:hidden backdrop-blur-xs"
        />
      )}

      <aside
        id="aurelius-sidebar"
        className={`fixed top-0 left-0 h-screen w-60 border-r border-[#e8e5e0] bg-[#faf9f6] z-40 flex flex-col justify-between p-6 select-none transition-transform duration-200 ease-in-out ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Brand & Navigation */}
        <div className="space-y-10">
          {/* Brand Wordmark */}
          <div className="pt-1">
            <button
              id="brand-link"
              onClick={() => {
                onNavigate('overview');
                onCloseMobile();
              }}
              className="text-left group block w-full focus:outline-hidden"
            >
              <span className="font-serif text-[22px] tracking-tight text-[#121212] block group-hover:opacity-80 transition-opacity">
                Aurelius
              </span>
              <span className="text-[9.5px] uppercase tracking-[0.16em] text-[#888888] font-medium block mt-1">
                Private Wealth
              </span>
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-2">
            {/* Overview */}
            <button
              id="nav-overview"
              onClick={() => {
                onNavigate('overview');
                onCloseMobile();
              }}
              className={`w-full flex items-center justify-between text-[13px] py-1.5 px-2 rounded-sm transition-colors text-left ${
                currentView === 'overview'
                  ? 'font-medium text-[#121212] bg-[#ffffff] border border-[#e8e5e0] shadow-xs'
                  : 'text-[#767676] hover:text-[#121212] hover:bg-[#f4f3f0]'
              }`}
            >
              <span>Overview</span>
              {currentView === 'overview' && (
                <span className="w-1.5 h-1.5 rounded-full bg-[#121212]" />
              )}
            </button>

            {/* Clients */}
            <button
              id="nav-clients"
              onClick={() => {
                onNavigate('clients');
                onCloseMobile();
              }}
              className={`w-full flex items-center justify-between text-[13px] py-1.5 px-2 rounded-sm transition-colors text-left ${
                currentView === 'clients'
                  ? 'font-medium text-[#121212] bg-[#ffffff] border border-[#e8e5e0] shadow-xs'
                  : 'text-[#767676] hover:text-[#121212] hover:bg-[#f4f3f0]'
              }`}
            >
              <span>Clients</span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 bg-[#f4f3f0] text-[#767676] border border-[#e8e5e0]">
                {clientCount}
              </span>
            </button>
          </nav>
        </div>

        {/* Desk & User Profile Footer */}
        <div className="space-y-5">
          {/* Zurich Booking Desk Indicator */}
          <div className="p-3 bg-[#ffffff] border border-[#e8e5e0] shadow-2xs">
            <div className="flex items-center justify-between text-[#767676] mb-1.5">
              <span className="text-[9.5px] uppercase tracking-[0.08em] font-medium">
                {currentRM.bookingDesk.name}
              </span>
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#121212]" />
            </div>
            <div className="font-mono text-[11px] text-[#121212] flex justify-between items-center">
              <span className="text-[#767676]">{currentRM.bookingDesk.metricLabel}</span>
              <span className="font-medium">{currentRM.bookingDesk.metricValue}</span>
            </div>
          </div>

          {/* Relationship Manager Footer */}
          <div className="pt-4 border-t border-[#e8e5e0] flex items-center justify-between">
            <div>
              <div className="text-[13px] font-medium text-[#121212] leading-snug">
                {currentRM.name}
              </div>
              <div className="text-[11px] text-[#767676]">{currentRM.title}</div>
            </div>
            <span
              className="inline-block w-2 h-2 rounded-full bg-emerald-600 ring-2 ring-emerald-100"
              title="Session Active"
            />
          </div>
        </div>
      </aside>
    </>
  );
};
