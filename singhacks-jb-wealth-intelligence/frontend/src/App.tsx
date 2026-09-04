import React, { useState, useMemo } from 'react';
import {
  Sidebar,
} from './components/Sidebar';
import { TopHeader } from './components/TopHeader';
import { MarketImpactSection } from './components/MarketImpactSection';
import { PriorityClientCard } from './components/PriorityClientCard';
import { ClientDetailPage } from './components/ClientDetailPage';
import { ClientsListView } from './components/ClientsListView';
import {
  BriefModal,
  SourceDataModal,
  EmergencyFreezeModal,
  NewOrderModal,
} from './components/Modals';
import {
  currentRM,
  executiveBriefing,
  placeholderClients,
} from './data/placeholderData';
import { ClientDossier, RiskSeverity } from './types';
import { FileText, SlidersHorizontal, Sparkles } from 'lucide-react';

export default function App() {
  // Navigation & View State
  const [currentView, setCurrentView] = useState<'overview' | 'clients' | 'client-detail'>(
    'overview'
  );
  const [selectedClientId, setSelectedClientId] = useState<string>('ravi-chandrasekaran');
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRiskFilter, setSelectedRiskFilter] = useState<RiskSeverity | 'ALL'>('ALL');

  // Collapsible Cards State: image 1 requirement: sections for client cards are collapsable
  // We can default the first card to open or allow any combination of toggled cards
  const [expandedCardIds, setExpandedCardIds] = useState<Set<string>>(
    new Set(['ravi-chandrasekaran'])
  );

  // Modal States
  const [isBriefModalOpen, setIsBriefModalOpen] = useState(false);
  const [activeBriefClient, setActiveBriefClient] = useState<ClientDossier | null>(null);
  const [isSourceDataModalOpen, setIsSourceDataModalOpen] = useState(false);
  const [isEmergencyFreezeOpen, setIsEmergencyFreezeOpen] = useState(false);
  const [isNewOrderOpen, setIsNewOrderOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Toggle card expansion
  const toggleCardExpansion = (id: string) => {
    setExpandedCardIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // Select client to navigate to their dedicated page (Image 3)
  const handleSelectClient = (clientId: string) => {
    setSelectedClientId(clientId);
    setCurrentView('client-detail');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Select client by name (e.g. from affected accounts pills)
  const handleSelectClientByName = (name: string) => {
    const found = placeholderClients.find(
      (c) =>
        c.name.toLowerCase().includes(name.toLowerCase()) ||
        name.toLowerCase().includes(c.name.toLowerCase()) ||
        name.toLowerCase().includes(c.initials.toLowerCase())
    );
    if (found) {
      handleSelectClient(found.id);
    } else {
      // If not strictly matching, navigate to clients list with search query
      setSearchQuery(name);
      setCurrentView('clients');
    }
  };

  // Current client for detail view
  const currentClient = useMemo(() => {
    return (
      placeholderClients.find((c) => c.id === selectedClientId) ||
      placeholderClients[0]
    );
  }, [selectedClientId]);

  // Filtered priority clients for Section 02
  const filteredPriorityClients = useMemo(() => {
    return placeholderClients.filter((c) => {
      const matchesSearch =
        searchQuery === '' ||
        c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.ref.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.mandate.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.headlineIssue.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesRisk =
        selectedRiskFilter === 'ALL' || c.riskLevel === selectedRiskFilter;

      return matchesSearch && matchesRisk;
    });
  }, [searchQuery, selectedRiskFilter]);

  return (
    <div className="min-h-screen bg-[#faf9f6] text-[#121212] font-sans antialiased flex flex-col selection:bg-neutral-900 selection:text-[#faf9f6]">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#121212] text-white px-4 py-2.5 text-[12px] font-mono shadow-xl border border-[#333333] flex items-center gap-2">
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* 1. Left Navigation Sidebar */}
      <Sidebar
        currentView={currentView}
        onNavigate={(view) => {
          setCurrentView(view);
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }}
        mobileOpen={mobileSidebarOpen}
        onCloseMobile={() => setMobileSidebarOpen(false)}
        clientCount={placeholderClients.length}
      />

      {/* 2. Docked Top Header */}
      <TopHeader
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        selectedRiskFilter={selectedRiskFilter}
        onSelectRiskFilter={setSelectedRiskFilter}
        onOpenEmergencyFreeze={() => setIsEmergencyFreezeOpen(true)}
        onOpenNewOrder={() => setIsNewOrderOpen(true)}
        onToggleMobileMenu={() => setMobileSidebarOpen(true)}
        unreadNotifications={4}
      />

      {/* 3. Main Stage Content */}
      <main className="lg:pl-60 pt-14 w-full min-h-screen flex flex-col">
        {/* VIEW 1: OVERVIEW / DASHBOARD (Image 1) */}
        {currentView === 'overview' && (
          <div className="w-full flex-1">
            {/* Morning Header Area */}
            <div className="px-6 sm:px-10 pt-10 pb-8 border-b border-[#e8e5e0] bg-[#faf9f6]">
              <div className="max-w-6xl mx-auto flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.14em] font-medium text-[#767676] mb-2">
                    <span>Dataset as-of 26 August 2026</span>
                    <span className="text-[#dedbd5]">•</span>
                    <span>{currentRM.desk}</span>
                  </div>
                  <h1 className="font-serif text-[32px] sm:text-[36px] leading-tight text-[#121212] tracking-tight">
                    Good morning, {currentRM.name.split(' ')[0]}
                  </h1>
                </div>

                <div className="flex flex-wrap items-center gap-3 sm:gap-4 text-[12px] text-[#666666] font-mono">
                  <span>
                    Desk Book AUM:{' '}
                    <strong className="text-[#121212] font-semibold">
                      {currentRM.totalDeskAUM}
                    </strong>
                  </span>
                  <span className="text-[#dedbd5]">•</span>
                  <span>
                    Active Alerts:{' '}
                    <strong className="text-[#7A1C28] font-semibold">
                      {currentRM.activeAlertsCount} Urgent
                    </strong>
                  </span>
                </div>
              </div>

              {/* AI Executive Briefing Strip */}
              <div className="max-w-6xl mx-auto mt-7 bg-[#ffffff] border border-[#e8e5e0] p-4 flex items-start gap-3.5 shadow-2xs">
                <div className="w-6 h-6 border border-[#e8e5e0] bg-[#faf9f6] flex items-center justify-center shrink-0 mt-0.5 text-[#121212]">
                  <span className="font-mono text-[12px] font-semibold">✦</span>
                </div>
                <div className="flex-1">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-1 gap-1">
                    <span className="text-[9.5px] uppercase tracking-[0.14em] font-medium text-[#767676]">
                      {executiveBriefing.title}
                    </span>
                    <span className="font-mono text-[11px] text-[#888888]">
                      {executiveBriefing.syncTime}
                    </span>
                  </div>
                  <p className="text-[13px] text-[#1e1e1e] leading-relaxed">
                    {executiveBriefing.summary}
                  </p>
                </div>
              </div>
            </div>

            {/* Operational Workspace Content Stage */}
            <div className="px-6 sm:px-10 py-10 flex-1 max-w-6xl mx-auto w-full space-y-12">
              {/* SECTION 01: Market & Portfolio Impact */}
              <MarketImpactSection
                onSelectClientByName={handleSelectClientByName}
              />

              {/* SECTION 02: Priority Client Dossiers */}
              <section id="section-priority-clients" className="space-y-5">
                <div className="flex flex-col sm:flex-row sm:items-baseline justify-between border-b border-[#e8e5e0] pb-3 gap-2">
                  <div>
                    <span className="text-[10px] uppercase tracking-[0.14em] font-medium text-[#767676] block mb-1">
                      SECTION 02 · Priority Client Dossiers
                    </span>
                    <h2 className="font-serif text-[22px] text-[#121212]">Priority Clients</h2>
                    <p className="text-[12.5px] text-[#666666] mt-0.5">
                      Ranked by mandate risk magnitude, collateral strain, and required advisory intervention.
                    </p>
                  </div>

                  <div className="flex items-center gap-3 text-[11px] font-mono text-[#767676]">
                    <span>SORT: RISK MAGNITUDE</span>
                    <span className="text-[#dedbd5]">•</span>
                    <span>{filteredPriorityClients.length} ACCOUNTS PENDING REVIEW</span>
                  </div>
                </div>

                {/* Collapsible toggle quick control */}
                <div className="flex items-center justify-between text-[11.5px] text-[#767676] px-1">
                  <span>
                    Click any client card to inspect dossier or toggle details:
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() =>
                        setExpandedCardIds(new Set(placeholderClients.map((c) => c.id)))
                      }
                      className="hover:text-[#121212] underline underline-offset-4"
                    >
                      Expand all
                    </button>
                    <span>·</span>
                    <button
                      onClick={() => setExpandedCardIds(new Set())}
                      className="hover:text-[#121212] underline underline-offset-4"
                    >
                      Collapse all
                    </button>
                  </div>
                </div>

                {/* Vertical Stack of Client Dossiers */}
                <div className="space-y-4">
                  {filteredPriorityClients.map((client) => (
                    <PriorityClientCard
                      key={client.id}
                      client={client}
                      isExpanded={expandedCardIds.has(client.id)}
                      onToggleExpand={() => toggleCardExpansion(client.id)}
                      onSelectClient={handleSelectClient}
                    />
                  ))}

                  {filteredPriorityClients.length === 0 && (
                    <div className="bg-white border border-[#e8e5e0] p-10 text-center text-[#767676] space-y-2">
                      <p className="font-serif text-[18px] text-[#121212]">
                        No client dossiers match current filter.
                      </p>
                      <button
                        onClick={() => {
                          setSearchQuery('');
                          setSelectedRiskFilter('ALL');
                        }}
                        className="text-[12px] underline text-[#121212]"
                      >
                        Reset filters
                      </button>
                    </div>
                  )}
                </div>
              </section>

              {/* Editorial Footer Memo */}
              <div className="pt-6 pb-12 border-t border-[#e8e5e0] flex flex-col sm:flex-row items-center justify-between text-[11px] text-[#888888] gap-4">
                <div className="flex items-center gap-4">
                  <button
                    type="button"
                    onClick={() => {
                      setActiveBriefClient(placeholderClients[0]);
                      setIsBriefModalOpen(true);
                    }}
                    className="px-4 py-2 bg-[#121212] text-[#faf9f6] hover:bg-neutral-800 text-[10px] font-medium uppercase tracking-[0.14em] transition-colors flex items-center gap-2 cursor-pointer"
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>Prepare client brief</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setIsSourceDataModalOpen(true)}
                    className="text-[#666666] hover:text-[#121212] underline underline-offset-4 text-[11px] transition-colors cursor-pointer"
                  >
                    View source data
                  </button>
                </div>

                <div className="text-right">
                  <span>Confidential Memorandum · Aurelius Wealth Partners</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* VIEW 2: CLIENT DETAIL SCREEN (Image 3) */}
        {currentView === 'client-detail' && (
          <ClientDetailPage
            client={currentClient}
            onBack={() => {
              setCurrentView('overview');
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
            onPrepareBrief={(client) => {
              setActiveBriefClient(client);
              setIsBriefModalOpen(true);
            }}
            onViewSourceData={() => setIsSourceDataModalOpen(true)}
            onSelectAnotherClient={handleSelectClient}
            allClients={placeholderClients}
          />
        )}

        {/* VIEW 3: FULL CLIENTS LIST DIRECTORY */}
        {currentView === 'clients' && (
          <div className="px-6 sm:px-10 py-10 max-w-6xl mx-auto w-full">
            <ClientsListView
              clients={placeholderClients}
              onSelectClient={handleSelectClient}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
            />
          </div>
        )}
      </main>

      {/* Interactive Dialogs & Modals */}
      <BriefModal
        client={activeBriefClient}
        onClose={() => {
          setIsBriefModalOpen(false);
          setActiveBriefClient(null);
        }}
      />

      <SourceDataModal
        isOpen={isSourceDataModalOpen}
        onClose={() => setIsSourceDataModalOpen(false)}
      />

      <EmergencyFreezeModal
        isOpen={isEmergencyFreezeOpen}
        onClose={() => setIsEmergencyFreezeOpen(false)}
      />

      <NewOrderModal
        isOpen={isNewOrderOpen}
        onClose={() => setIsNewOrderOpen(false)}
        clients={placeholderClients}
        onOrderPlaced={(name, type) => {
            showToast(`Prototype action recorded for ${name} (${type})`);
        }}
      />
    </div>
  );
}
