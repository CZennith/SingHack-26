import { ClientDossier, RiskSeverity } from '../types';
import { connectorConfig } from './connectorConfig';

/**
 * Backend contract:
 * GET /clients -> ClientSummary[]
 * GET /clients/{id}/dossier -> ClientDossier
 * GET /clients/{id}/insights -> ClientInsights
 * Financial calculations belong to the backend; this client never overlays a
 * response with another client's presentation fixture.
 */
export interface ClientSummary {
  id: string;
  name: string;
  ref: string;
  tier: 'UHNW' | 'HNW';
  mandate: string;
  aum: string;
  riskLevel: RiskSeverity;
  headlineIssue: string;
  summary: string;
  tags: string[];
  suggestedNextStep: string;
}

export interface ClientInsights {
  synthesisedAnalysis: ClientDossier['synthesisedAnalysis'];
  strategicMatrix: ClientDossier['strategicMatrix'];
}

const initialsFor = (name: string) => name.trim().split(/\s+/).map((part) => part[0]).join('').slice(0, 2).toUpperCase();
const riskLevelFor = (score: number): RiskSeverity => score >= 75 ? 'CRITICAL' : score >= 50 ? 'HIGH' : score >= 25 ? 'MEDIUM' : 'LOW';

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${connectorConfig.apiBaseUrl}${path}`, { headers: { Accept: 'application/json' }, signal });
  if (!response.ok) throw new Error(`Client service returned ${response.status} for ${path}.`);
  return response.json() as Promise<T>;
}

/** Supports the current three-field list response until the summary endpoint is expanded. */
const toSummary = (client: Partial<ClientSummary> & { id: string | number; name: string; risk_score?: number }): ClientSummary => ({
  id: String(client.id), name: client.name, ref: client.ref ?? `CLIENT-${client.id}`,
  tier: client.tier ?? 'HNW', mandate: client.mandate ?? 'Pending mandate data',
  aum: client.aum ?? 'Pending valuation', riskLevel: client.riskLevel ?? riskLevelFor(client.risk_score ?? 0),
  headlineIssue: client.headlineIssue ?? (client.risk_score === undefined ? 'Pending risk assessment' : `Risk score: ${client.risk_score}`),
  summary: client.summary ?? 'Open dossier to load portfolio and advisory data.', tags: client.tags ?? [],
  suggestedNextStep: client.suggestedNextStep ?? 'Review client dossier.',
});

export async function fetchClients(signal?: AbortSignal): Promise<ClientDossier[]> {
  const payload = await getJson<Array<Partial<ClientSummary> & { id: string | number; name: string; risk_score?: number }>>('/clients', signal);
  if (!Array.isArray(payload)) throw new Error('Client service returned an invalid client list.');
  // Detail fields are intentionally absent until the per-client request completes.
  return payload.map((item) => {
    const summary = toSummary(item);
    return {
      ...summary,
      initials: initialsFor(summary.name),
      about: { bio: 'Profile details are loading.', age: 0, occupation: 'Pending profile data', clientSince: 0 },
      portfolio: {
        totalValue: '—', totalValueSubtext: 'Pending valuation', cashLiquidity: '—', cashLiquidityPercent: '—', cashLiquiditySubtext: 'Pending liquidity data',
        borrowingUtilisation: '—', borrowingLtvPercent: 0, borrowingStatus: 'NORMAL', allocation: [],
        trajectory: { deltaPercent: '—', deltaPeriod: '1-Year Delta', startLabel: '—', troughLabel: '—', endLabel: '—', points: [] },
        topHoldings: [], remainingHoldingsNote: 'Holdings load when the dossier is opened.',
      },
      synthesisedAnalysis: { syncTime: 'Pending', headline: 'Analysis loading', narrative: 'Advisory analysis loads with the client dossier.', whyItMatters: '—', monitor: '—' },
      strategicMatrix: { risks: [], opportunities: [] },
    };
  });
}

export async function fetchClientDossier(clientId: string, signal?: AbortSignal): Promise<ClientDossier> {
  const dossier = await getJson<ClientDossier>(`/clients/${encodeURIComponent(clientId)}/dossier`, signal);
  if (!dossier || dossier.id !== clientId) throw new Error('Client service returned an invalid dossier.');
  return { ...dossier, initials: dossier.initials || initialsFor(dossier.name) };
}

export async function fetchClientInsights(clientId: string, signal?: AbortSignal): Promise<ClientInsights> {
  return getJson<ClientInsights>(`/clients/${encodeURIComponent(clientId)}/insights`, signal);
}
