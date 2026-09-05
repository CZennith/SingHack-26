import { ConnectorMode } from './connectorContracts';

export interface ConnectorConfig {
  mode: ConnectorMode;
  apiBaseUrl: string;
  dataAsOf: string;
}

export const connectorConfig: ConnectorConfig = {
  mode: 'live',
  // In development Vite proxies /api to the local FastAPI server. Deployments
  // can set VITE_API_BASE_URL to their backend origin instead.
  apiBaseUrl: (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, ''),
  dataAsOf: import.meta.env.VITE_DATA_AS_OF || '2026-08-26',
};
