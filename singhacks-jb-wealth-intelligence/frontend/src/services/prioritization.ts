import { connectorConfig } from './connectorConfig';

export interface PrioritizationTrigger {
  code: string;
  points: number;
  label: string;
  evidence: Record<string, string | number>[];
}

export interface PrioritizedClient {
  client_id: string;
  client_name: string;
  total_aum_usd: number;
  urgency_score: number;
  risk_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  trigger_reasons: PrioritizationTrigger[];
  rank: number;
}

export interface PrioritizationResponse {
  as_of: string;
  rule_weights: Record<string, number>;
  clients: PrioritizedClient[];
}

export async function getPrioritization(): Promise<PrioritizationResponse> {
  const response = await fetch(`${connectorConfig.apiBaseUrl}/api/prioritization`);
  if (!response.ok) {
    throw new Error(`Prioritization request failed (${response.status})`);
  }
  return response.json() as Promise<PrioritizationResponse>;
}