import { ClientDossier, RiskSeverity } from '../types';
import { connectorConfig } from './connectorConfig';
import { placeholderClients } from '../data/placeholderData';

/** The personal-information fields currently returned by GET /clients. */
export interface BackendClient {
  id: string | number;
  name: string;
  risk_score: number;
}

const riskLevelFor = (score: number): RiskSeverity => {
  if (score >= 75) return 'CRITICAL';
  if (score >= 50) return 'HIGH';
  if (score >= 25) return 'MEDIUM';
  return 'LOW';
};

const initialsFor = (name: string) =>
  name
    .trim()
    .split(/\s+/)
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

/**
 * Adapts the small profile response to the current dossier UI. Portfolio and
 * insight panels retain visual fixture data until the backend exposes them.
 */
const toDossier = (client: BackendClient, index: number): ClientDossier => {
  const presentationFixture = placeholderClients[index % placeholderClients.length];
  const riskLevel = riskLevelFor(client.risk_score);

  return {
    ...presentationFixture,
    id: String(client.id),
    ref: `CLIENT-${client.id}`,
    name: client.name,
    initials: initialsFor(client.name),
    riskLevel,
    headlineIssue: `Risk score: ${client.risk_score}`,
    summary: 'Personal profile loaded from the client service.',
    tags: [`Risk score ${client.risk_score}`, 'Profile source: backend'],
    about: {
      ...presentationFixture.about,
      bio: 'Personal profile loaded from the client service. Portfolio and advisory details will appear when supplied by the backend.',
    },
  };
};

export async function fetchClientDossiers(signal?: AbortSignal): Promise<ClientDossier[]> {
  const response = await fetch(`${connectorConfig.apiBaseUrl}/clients`, {
    headers: { Accept: 'application/json' },
    signal,
  });

  if (!response.ok) {
    throw new Error(`Client service returned ${response.status}.`);
  }

  const payload: unknown = await response.json();
  if (!Array.isArray(payload)) {
    throw new Error('Client service returned an invalid response.');
  }

  const clients = payload.filter(
    (item): item is BackendClient =>
      typeof item === 'object' &&
      item !== null &&
      typeof (item as BackendClient).id !== 'undefined' &&
      typeof (item as BackendClient).name === 'string' &&
      typeof (item as BackendClient).risk_score === 'number',
  );

  if (clients.length !== payload.length) {
    throw new Error('One or more client profiles from the service are invalid.');
  }

  return clients.map(toDossier);
}
