import { ConnectorMode } from './connectorContracts';

export interface ConnectorConfig {
  mode: ConnectorMode;
  apiBaseUrl: string;
  dataAsOf: string;
}

const publicEnv: Record<string, string | undefined> =
  (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env ?? {};

export const connectorConfig: ConnectorConfig = {
  mode: publicEnv.VITE_CONNECTOR_MODE === 'live' ? 'live' : 'mock',
  apiBaseUrl: (publicEnv.VITE_API_BASE_URL || '').replace(/\/$/, ''),
  dataAsOf: publicEnv.VITE_DATA_AS_OF || '2026-08-26',
};
