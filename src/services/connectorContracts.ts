/**
 * Provider-neutral frontend contracts.
 *
 * These types describe provider-neutral integration boundaries. Fixture mode
 * remains available, while live mode is backed by the read-only wealth API.
 */

export type ConnectorMode = 'mock' | 'live';

export interface ConnectorRequestContext {
  asOf: string;
  correlationId: string;
  requesterId: string;
  clientId?: string;
  portfolioId?: string;
}

export interface EvidenceReference {
  source: string;
  recordId: string;
  asOf: string;
  fields: string[];
}

export interface IntelligenceInsight {
  id: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  title: string;
  explanation: string;
  whyItMatters: string;
  suggestedActions: string[];
  evidence: EvidenceReference[];
  requiresRmReview: true;
}

export interface WealthDataConnector {
  getClients(context: ConnectorRequestContext): Promise<unknown[]>;
  getPortfolios(context: ConnectorRequestContext): Promise<unknown[]>;
  getHoldings(context: ConnectorRequestContext): Promise<unknown[]>;
  getInstruments(context: ConnectorRequestContext): Promise<unknown[]>;
  getMandates(context: ConnectorRequestContext): Promise<unknown[]>;
  getTransactions(context: ConnectorRequestContext): Promise<unknown[]>;
  getCreditFacilities(context: ConnectorRequestContext): Promise<unknown[]>;
  getCommitments(context: ConnectorRequestContext): Promise<unknown[]>;
  getPlannedCashNeeds(context: ConnectorRequestContext): Promise<unknown[]>;
}

export interface MarketDataConnector {
  getMarketContext(context: ConnectorRequestContext): Promise<unknown[]>;
}

export interface EventLogConnector {
  getEvents(context: ConnectorRequestContext): Promise<unknown[]>;
}

export interface InsightConnector {
  generateInsight(
    context: ConnectorRequestContext,
    inputs: unknown[],
  ): Promise<IntelligenceInsight>;
  explainInsight(
    context: ConnectorRequestContext,
    insightId: string,
  ): Promise<EvidenceReference[]>;
}

export interface AuditConnector {
  recordReview(
    context: ConnectorRequestContext,
    insightId: string,
    decision: 'accepted' | 'rejected' | 'modified' | 'deferred',
    rationale?: string,
  ): Promise<void>;
}

export interface BackendConnectors {
  wealth: WealthDataConnector;
  market: MarketDataConnector;
  events: EventLogConnector;
  insights: InsightConnector;
  audit: AuditConnector;
}
