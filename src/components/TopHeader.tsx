import React, { useState } from 'react';
import { Search, Bell, SlidersHorizontal, Menu, X, CheckCircle2, ShieldAlert } from 'lucide-react';
import { RiskSeverity } from '../types';

interface TopHeaderProps {
  searchQuery: string;
  onSearchChange: (val: string) => void;
  selectedRiskFilter: RiskSeverity | 'ALL';
  onSelectRiskFilter: (risk: RiskSeverity | 'ALL') => void;
  onOpenEmergencyFreeze: () => void;
  onOpenNewOrder: () => void;
  onToggleMobileMenu: () => void;
  unreadNotifications: number;
}

export const TopHeader: React.FC<TopHeaderProps> = ({
  searchQuery,
  onSearchChange,
  selectedRiskFilter,
  onSelectRiskFilter,
  onOpenEmergencyFreeze,
  onOpenNewOrder,
  onToggleMobileMenu,
  unreadNotifications,
}) => {
  const [showFilterMenu, setShowFilterMenu] = useState(false);
  const [showNotificationMenu, setShowNotificationMenu] = useState(false);

  return (
    <header
      id="top-docked-header"
      className="fixed top-0 left-0 w-full h-14 lg:pl-60 border-b border-[#e8e5e0] bg-[#faf9f6]/95 backdrop-blur-md z-30 flex items-center justify-between px-4 sm:px-8 transition-all"
    >
      {/* Left: Mobile Menu + Search */}
      <div className="flex items-center gap-3 w-full max-w-xs sm:max-w-sm md:max-w-md">
        <button
          id="mobile-menu-toggle"
          onClick={onToggleMobileMenu}
          className="lg:hidden p-1.5 text-[#666666] hover:text-[#121212] focus:outline-hidden"
          aria-label="Toggle navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2.5 w-full bg-white/50 border border-[#e8e5e0] px-3 py-1.5 focus-within:bg-white focus-within:border-[#121212] transition-all">
          <Search className="w-4 h-4 text-[#888888] shrink-0" />
          <input
            id="global-search-input"
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search mandates, clients, ISIN or ticker..."
            className="w-full bg-transparent border-0 text-[13px] text-[#121212] placeholder:text-[#999999] focus:ring-0 p-0 focus:outline-hidden"
          />
          {searchQuery && (
            <button
              onClick={() => onSearchChange('')}
              className="text-[#999999] hover:text-[#121212]"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Right Actions Cluster */}
      <div className="flex items-center gap-3 sm:gap-4 shrink-0">
        <div className="relative flex items-center gap-1.5 sm:gap-2 border-r border-[#e8e5e0] pr-3 sm:pr-4">
          {/* Notifications Button */}
          <div className="relative">
            <button
              id="notifications-button"
              type="button"
              aria-label="Notifications"
              onClick={() => {
                setShowNotificationMenu(!showNotificationMenu);
                setShowFilterMenu(false);
              }}
              className="p-1.5 text-[#666666] hover:text-[#121212] hover:bg-[#f4f3f0] transition-colors relative"
            >
              <Bell className="w-4 h-4" />
              {unreadNotifications > 0 && (
                <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-[#7A1C28]" />
              )}
            </button>

            {/* Notification Menu Dropdown */}
            {showNotificationMenu && (
              <div className="absolute right-0 mt-2 w-72 sm:w-80 bg-white border border-[#dedbd5] shadow-lg py-2 z-50">
                <div className="px-4 py-2 border-b border-[#e8e5e0] flex items-center justify-between">
                  <span className="text-[11px] font-mono uppercase tracking-[0.08em] font-semibold text-[#121212]">
                    Prototype Desk Alerts
                  </span>
                  <span className="text-[10px] text-[#767676]">Fixture data</span>
                </div>
                <div className="divide-y divide-[#f0eee9] max-h-64 overflow-y-auto text-[12px]">
                  <div className="p-3 hover:bg-[#faf9f6]">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] font-semibold uppercase text-[#7A1C28] bg-[#fcf5f5] px-1.5 py-0.5 border border-[#eed6d9]">
                        Critical Alert
                      </span>
                      <span className="text-[10px] text-[#888888]">12m ago</span>
                    </div>
                    <p className="text-[#121212] font-medium">Margarethe Voss-Brenner</p>
                    <p className="text-[#666666] text-[11px]">Duration ceiling drift exceeds 7.4y threshold.</p>
                  </div>
                  <div className="p-3 hover:bg-[#faf9f6]">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] font-semibold uppercase text-[#9E6B20] bg-[#fdf8f0] px-1.5 py-0.5 border border-[#f4e4cc]">
                        High Alert
                      </span>
                      <span className="text-[10px] text-[#888888]">45m ago</span>
                    </div>
                    <p className="text-[#121212] font-medium">David Lim</p>
                    <p className="text-[#666666] text-[11px]">USD 3.5m capital call due 16 Sep with cash gap.</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Filter / Tune Button */}
          <div className="relative">
            <button
              id="filter-toggle-button"
              type="button"
              aria-label="System Filter"
              onClick={() => {
                setShowFilterMenu(!showFilterMenu);
                setShowNotificationMenu(false);
              }}
              className={`p-1.5 hover:bg-[#f4f3f0] transition-colors relative ${
                selectedRiskFilter !== 'ALL'
                  ? 'text-[#121212] bg-[#f4f3f0]'
                  : 'text-[#666666] hover:text-[#121212]'
              }`}
            >
              <SlidersHorizontal className="w-4 h-4" />
              {selectedRiskFilter !== 'ALL' && (
                <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-[#121212]" />
              )}
            </button>

            {/* Filter Dropdown */}
            {showFilterMenu && (
              <div className="absolute right-0 mt-2 w-56 bg-white border border-[#dedbd5] shadow-lg p-2 z-50">
                <div className="px-2 py-1 text-[10px] uppercase tracking-[0.14em] text-[#767676] font-medium mb-1">
                  Filter by Risk Priority
                </div>
                {(['ALL', 'CRITICAL', 'HIGH', 'MEDIUM'] as const).map((filter) => (
                  <button
                    key={filter}
                    onClick={() => {
                      onSelectRiskFilter(filter);
                      setShowFilterMenu(false);
                    }}
                    className={`w-full flex items-center justify-between px-2 py-1.5 text-[12px] text-left hover:bg-[#faf9f6] transition-colors ${
                      selectedRiskFilter === filter ? 'font-medium text-[#121212] bg-[#f4f3f0]' : 'text-[#666666]'
                    }`}
                  >
                    <span>{filter === 'ALL' ? 'Show All Risk Levels' : `${filter} Priority`}</span>
                    {selectedRiskFilter === filter && <CheckCircle2 className="w-3.5 h-3.5 text-[#121212]" />}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <button
          id="btn-emergency-freeze"
          type="button"
          onClick={onOpenEmergencyFreeze}
          className="h-8 px-2.5 sm:px-3 border border-[#dedbd5] hover:border-[#7A1C28] text-[#7A1C28] text-[10px] font-medium uppercase tracking-[0.14em] transition-colors whitespace-nowrap flex items-center gap-1.5"
        >
          <ShieldAlert className="w-3.5 h-3.5 shrink-0 hidden sm:inline" />
          <span>Emergency Freeze</span>
        </button>

        <button
          id="btn-new-order"
          type="button"
          onClick={onOpenNewOrder}
          className="h-8 px-3 sm:px-4 bg-[#121212] text-[#faf9f6] hover:bg-neutral-800 text-[10px] font-medium uppercase tracking-[0.14em] transition-colors whitespace-nowrap"
        >
          New Order
        </button>
      </div>
    </header>
  );
};
