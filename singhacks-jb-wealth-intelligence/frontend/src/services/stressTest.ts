/**
 * Typed fetch wrappers for all /stress-test/* API endpoints.
 * All paths are relative to connectorConfig.apiBaseUrl (proxied through Vite).
 */

import { connectorConfig } from './connectorConfig';
import type {
  StressRunRequest,
  StressRunResult,
  LookThroughResult,
  LiquidityResult,
  BookScenarioRequest,
  BookScenarioResponse,
} from '../types/stressWorkbench';

const BASE = `${connectorConfig.apiBaseUrl}/stress-test`;

async function postJson<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(`Stress test API error ${response.status}: ${detail}`);
  }
  return response.json() as Promise<T>;
}

async function getJson<T>(path: string, params: Record<string, string>, signal?: AbortSignal): Promise<T> {
  const query = new URLSearchParams(params).toString();
  const response = await fetch(`${BASE}${path}?${query}`, {
    headers: { Accept: 'application/json' },
    signal,
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(`Stress test API error ${response.status}: ${detail}`);
  }
  return response.json() as Promise<T>;
}

/** Run the full stress suite (macro shock + LTV + mandate guard + narrative) for one client. */
export async function runStressTest(
  req: StressRunRequest,
  signal?: AbortSignal,
): Promise<StressRunResult> {
  return postJson<StressRunResult>('/run', req, signal);
}

/** Look-through concentration analysis for one client. */
export async function getLookThrough(
  clientId: string,
  signal?: AbortSignal,
): Promise<LookThroughResult> {
  return getJson<LookThroughResult>('/look-through', { client_id: clientId }, signal);
}

/** 60-day LCR calculation, sell-to-cover, and life-event flags for one client. */
export async function getLiquidity(
  clientId: string,
  signal?: AbortSignal,
): Promise<LiquidityResult> {
  return getJson<LiquidityResult>('/liquidity', { client_id: clientId }, signal);
}

/** Scenario shock across all 20 clients — ranked leaderboard. */
export async function runBookScenario(
  req: BookScenarioRequest,
  signal?: AbortSignal,
): Promise<BookScenarioResponse> {
  return postJson<BookScenarioResponse>('/book-scenario', req, signal);
}

/** 2–4 sentence scenario narrative for a specific client and scenario. */
export async function getNarrative(
  clientId: string,
  scenarioId: string,
  signal?: AbortSignal,
): Promise<{ narrative: string; top_affected_holdings: string[] }> {
  return getJson('/narrative', { client_id: clientId, scenario_id: scenarioId }, signal);
}
