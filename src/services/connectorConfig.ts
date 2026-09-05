import { ConnectorMode } from './connectorContracts';

export interface ConnectorConfig {
  mode: ConnectorMode;
  apiBaseUrl: string;
  dataAsOf: string;
}

export const connectorConfig: ConnectorConfig = {
  mode: import.meta.env.VITE_CONNECTOR_MODE === 'live' ? 'live' : 'mock',
  apiBaseUrl: (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, ''),
  dataAsOf: import.meta.env.VITE_DATA_AS_OF || '2026-08-26',
};
