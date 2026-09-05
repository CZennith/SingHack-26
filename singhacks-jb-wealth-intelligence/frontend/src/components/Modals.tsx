import React, { useState } from 'react';
import { X, Check, ShieldAlert, FileText, Database, Printer, Copy, ArrowRight } from 'lucide-react';
import { ClientDossier } from '../types';

interface BriefModalProps {
  client: ClientDossier | null;
  onClose: () => void;
}

export const BriefModal: React.FC<BriefModalProps> = ({ client, onClose }) => {
  const [copied, setCopied] = useState(false);

  if (!client) return null;

  const handleCopy = () => {
    const text = `AURELIUS PRIVATE WEALTH - EXECUTIVE CLIENT BRIEF
Client: ${client.name} (Ref: ${client.ref})
Tier: ${client.tier} | Mandate: ${client.mandate} | AUM: ${client.aum}
Risk Status: ${client.riskLevel}

HEADLINE ISSUE:
${client.headlineIssue}

SUMMARY:
${client.summary}

SUGGESTED NEXT STEP:
${client.suggestedNextStep}

KEY RISKS:
${client.advisory.risks.map((r) => `- ${r.title}: ${r.description}`).join('\n')}

OPPORTUNITIES:
${client.advisory.opportunities.map((o) => `- ${o.title}: ${o.description}`).join('\n')}
`;
    navigator.clipboard?.writeText?.(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs">
      <div className="bg-white border border-[#dedbd5] max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl flex flex-col">
        {/* Header */}
        <div className="p-5 border-b border-[#e8e5e0] flex items-center justify-between bg-[#faf9f6]">
          <div>
            <div className="text-[10px] uppercase font-mono tracking-[0.14em] text-[#767676]">
              Executive Advisory Memorandum
            </div>
            <h3 className="font-serif text-[20px] text-[#121212] mt-0.5">
              Client Brief: {client.name}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-[#767676] hover:text-[#121212] hover:bg-[#f0eee9]"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Document Body */}
        <div className="p-6 space-y-5 text-[13px] leading-relaxed text-[#1e1e1e]">
          <div className="flex items-center justify-between border-b border-[#f0eee9] pb-3 text-[12px] font-mono text-[#666666]">
            <span>Ref: {client.ref}</span>
            <span>Mandate: {client.mandate}</span>
            <span className="font-medium text-[#121212]">{client.aum} AUM</span>
          </div>

          <div className="space-y-1">
            <h4 className="text-[11px] font-mono uppercase tracking-[0.1em] text-[#7A1C28] font-semibold">
              Current Mandate Strain &amp; Objective
            </h4>
            <p className="text-[#121212] font-medium">{client.headlineIssue}</p>
            <p className="text-[#555555]">{client.summary}</p>
          </div>

          <div className="p-3.5 bg-[#fdf8f0] border border-[#f4e4cc] text-[12px]">
            <span className="font-medium text-[#9E6B20] block mb-0.5 uppercase tracking-micro text-[10px]">
              Recommended Advisory Action
            </span>
            <p className="text-[#121212]">{client.suggestedNextStep}</p>
          </div>

          <div className="space-y-2 pt-2 border-t border-[#f0eee9]">
            <h4 className="text-[11px] font-mono uppercase tracking-[0.1em] text-[#767676] font-semibold">
              Strategic Matrix Synopsis
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[12px]">
              <div className="p-3 bg-[#faf9f6] border border-[#e8e5e0]">
                <div className="font-medium text-[#7A1C28] mb-1">Key Vulnerabilities</div>
                <ul className="space-y-1 text-[#555555]">
                  {client.advisory.risks.slice(0, 2).map((r, i) => (
                    <li key={i} className="list-disc ml-3 text-[11.5px]">
                      {r.title}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="p-3 bg-[#faf9f6] border border-[#e8e5e0]">
                <div className="font-medium text-[#2c6e6a] mb-1">Target Solutions</div>
                <ul className="space-y-1 text-[#555555]">
                  {client.advisory.opportunities.slice(0, 2).map((o, i) => (
                    <li key={i} className="list-disc ml-3 text-[11.5px]">
                      {o.title}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-[#e8e5e0] bg-[#faf9f6] flex items-center justify-between">
          <div className="text-[11px] text-[#888888] font-mono">
            Aurelius Private Wealth · Strictly Confidential
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="px-3 py-1.5 border border-[#dedbd5] bg-white hover:bg-[#f4f3f0] text-[#121212] text-[11px] font-medium flex items-center gap-1.5 transition-colors"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy Text'}</span>
            </button>
            <button
              onClick={() => window.print()}
              className="px-3.5 py-1.5 bg-[#121212] text-white hover:bg-neutral-800 text-[11px] font-medium uppercase tracking-[0.1em] flex items-center gap-1.5 transition-colors"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print Brief</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

interface SourceDataModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SourceDataModal: React.FC<SourceDataModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs">
      <div className="bg-white border border-[#dedbd5] max-w-lg w-full shadow-2xl p-6 space-y-5">
        <div className="flex items-center justify-between border-b border-[#e8e5e0] pb-3">
          <div>
            <span className="text-[10px] uppercase font-mono tracking-[0.14em] text-[#767676]">
              Connector Contracts
            </span>
            <h3 className="font-serif text-[20px] text-[#121212]">Planned Data Sources</h3>
          </div>
          <button onClick={onClose} className="p-1 text-[#767676] hover:text-[#121212]">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-3 font-mono text-[11.5px] text-[#555555]">
          <div className="p-3 bg-[#faf9f6] border border-[#e8e5e0] flex items-center justify-between">
            <div>
              <div className="font-medium text-[#121212]">Core Banking / Wealth Data</div>
              <div className="text-[10px] text-[#888888]">Maps to WealthDataConnector · not connected</div>
            </div>
            <span className="text-[#767676] bg-[#f4f3f0] border border-[#dedbd5] px-2 py-0.5 text-[10px]">
              PLANNED
            </span>
          </div>

          <div className="p-3 bg-[#faf9f6] border border-[#e8e5e0] flex items-center justify-between">
            <div>
              <div className="font-medium text-[#121212]">Market Data Provider</div>
              <div className="text-[10px] text-[#888888]">Maps to MarketDataConnector · not connected</div>
            </div>
            <span className="text-[#767676] bg-[#f4f3f0] border border-[#dedbd5] px-2 py-0.5 text-[10px]">
              PLANNED
            </span>
          </div>

          <div className="p-3 bg-[#faf9f6] border border-[#e8e5e0] flex items-center justify-between">
            <div>
              <div className="font-medium text-[#121212]">Audit &amp; Execution Gateway</div>
              <div className="text-[10px] text-[#888888]">Maps to AuditConnector · review only</div>
            </div>
            <span className="text-[#767676] bg-[#f4f3f0] border border-[#dedbd5] px-2 py-0.5 text-[10px]">
              PLANNED
            </span>
          </div>
        </div>

        <div className="pt-2 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-[#121212] text-white text-[11px] font-medium uppercase tracking-[0.1em]"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

interface EmergencyFreezeModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const EmergencyFreezeModal: React.FC<EmergencyFreezeModalProps> = ({ isOpen, onClose }) => {
  const [frozen, setFrozen] = useState(false);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
      <div className="bg-white border border-[#7A1C28] max-w-md w-full shadow-2xl p-6 space-y-4">
        <div className="flex items-center gap-3 text-[#7A1C28] border-b border-[#eed6d9] pb-3">
          <ShieldAlert className="w-6 h-6 shrink-0" />
          <h3 className="font-serif text-[20px] text-[#121212]">Simulate Desk Freeze</h3>
        </div>

        {frozen ? (
          <div className="p-4 bg-[#fcf5f5] border border-[#eed6d9] text-[13px] text-[#7A1C28] space-y-2">
            <p className="font-semibold">Prototype state recorded.</p>
            <p className="text-[12px] text-[#555555]">
              No facilities or execution channels were changed. A future AuditConnector will record
              and route this RM-controlled decision.
            </p>
            <div className="pt-3">
              <button
                onClick={() => {
                  setFrozen(false);
                  onClose();
                }}
                className="w-full py-2 bg-[#121212] text-white text-[11px] uppercase tracking-[0.1em]"
              >
                Return to Workspace
              </button>
            </div>
          </div>
        ) : (
          <>
            <p className="text-[13px] text-[#555555] leading-relaxed">
              This prototype demonstrates the RM review flow only. It does not halt transactions or
              change Lombard facilities.
            </p>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#e8e5e0]">
              <button
                onClick={onClose}
                className="px-3.5 py-1.5 border border-[#dedbd5] text-[#121212] text-[11px] hover:bg-[#faf9f6]"
              >
                Cancel
              </button>
              <button
                onClick={() => setFrozen(true)}
                className="px-4 py-1.5 bg-[#7A1C28] hover:bg-[#5f1620] text-white text-[11px] font-medium uppercase tracking-[0.1em]"
              >
                Record Prototype State
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

interface NewOrderModalProps {
  isOpen: boolean;
  onClose: () => void;
  clients: ClientDossier[];
  onOrderPlaced: (clientName: string, orderType: string) => void;
}

export const NewOrderModal: React.FC<NewOrderModalProps> = ({
  isOpen,
  onClose,
  clients,
  onOrderPlaced,
}) => {
  const [selectedClientId, setSelectedClientId] = useState(clients[0]?.id || '');
  const [orderType, setOrderType] = useState('REBALANCE_SOVEREIGN');
  const [amount, setAmount] = useState('1,000,000');
  const [submitted, setSubmitted] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const c = clients.find((x) => x.id === selectedClientId);
    onOrderPlaced(c ? c.name : 'Client', orderType);
    setSubmitted(true);
    setTimeout(() => {
      setSubmitted(false);
      onClose();
    }, 1500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs">
      <div className="bg-white border border-[#dedbd5] max-w-lg w-full shadow-2xl p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-[#e8e5e0] pb-3">
          <div>
            <span className="text-[10px] uppercase font-mono tracking-[0.14em] text-[#767676]">
              Advisory Workflow Prototype
            </span>
            <h3 className="font-serif text-[20px] text-[#121212]">Draft Advisory Action</h3>
          </div>
          <button onClick={onClose} className="p-1 text-[#767676] hover:text-[#121212]">
            <X className="w-5 h-5" />
          </button>
        </div>

        {submitted ? (
          <div className="p-6 text-center space-y-2">
            <Check className="w-8 h-8 text-emerald-600 mx-auto" />
            <p className="font-serif text-[18px] text-[#121212]">Prototype action recorded</p>
            <p className="text-[12px] text-[#666666]">
              No order was sent. Implement AuditConnector and an approved execution workflow before
              enabling live actions.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4 text-[13px]">
            <div>
              <label className="block text-[11px] uppercase font-mono tracking-[0.08em] text-[#767676] mb-1">
                Target Client Account
              </label>
              <select
                value={selectedClientId}
                onChange={(e) => setSelectedClientId(e.target.value)}
                className="w-full bg-[#faf9f6] border border-[#e8e5e0] p-2 text-[13px] text-[#121212] focus:outline-hidden focus:border-[#121212]"
              >
                {clients.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.ref} · {c.mandate})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[11px] uppercase font-mono tracking-[0.08em] text-[#767676] mb-1">
                Order Type &amp; Strategy
              </label>
              <select
                value={orderType}
                onChange={(e) => setOrderType(e.target.value)}
                className="w-full bg-[#faf9f6] border border-[#e8e5e0] p-2 text-[13px] text-[#121212] focus:outline-hidden focus:border-[#121212]"
              >
                <option value="REBALANCE_SOVEREIGN">Rebalance into Sovereign Short Duration</option>
                <option value="LOMBARD_LIQUIDITY">Short-term Lombard Liquidity Bridge</option>
                <option value="EQUITY_COLLAR">Implement Phased Hedging Collar</option>
                <option value="GOLD_TRIM">Trim Bullion Over-Allocation (Capital Harvest)</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] uppercase font-mono tracking-[0.08em] text-[#767676] mb-1">
                Notional Value (USD / EUR)
              </label>
              <input
                type="text"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="w-full bg-[#faf9f6] border border-[#e8e5e0] p-2 text-[13px] font-mono text-[#121212] focus:outline-hidden focus:border-[#121212]"
              />
            </div>

            <div className="pt-3 border-t border-[#e8e5e0] flex justify-end gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1.5 border border-[#dedbd5] text-[#767676] text-[11px] hover:bg-[#faf9f6]"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 bg-[#121212] text-white text-[11px] font-medium uppercase tracking-[0.1em] hover:bg-neutral-800"
              >
                Route Order
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
