/**
 * ScenarioPicker — standalone scenario selector with shock table editor.
 *
 * Renders the five named scenarios plus a "Custom" option. When a named
 * scenario is selected the shock values are pre-populated (read-only chips).
 * When "Custom" is selected the user can edit each asset-class shock value
 * directly. Inline validation disables the Run button when any value is
 * outside ±100.
 *
 * Requirements: 2.1, 2.2, 2.4, 2.5, 2.6
 */

import React, { useState } from 'react';
import { Activity } from 'lucide-react';
import {
  NAMED_SCENARIOS,
  type ScenarioConfig,
  type AssetClass,
  type NamedScenarioId,
} from '../types/stressWorkbench';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ALL_ASSET_CLASSES: AssetClass[] = [
  'Equity',
  'Fixed Income',
  'Cash and Equivalents',
  'Alternatives',
  'Commodities',
  'Structured Products',
];

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface ScenarioPickerProps {
  selectedScenario: ScenarioConfig;
  onScenarioChange: (config: ScenarioConfig) => void;
  onRun: () => void;
  isLoading: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function namedToConfig(id: NamedScenarioId): ScenarioConfig {
  const def = NAMED_SCENARIOS[id];
  return {
    id,
    label: def.label,
    shocks: { ...def.shocks },
    sector_overrides: { ...def.sector_overrides },
  };
}

function isValidShock(value: number): boolean {
  return value >= -100 && value <= 100;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const ScenarioPicker: React.FC<ScenarioPickerProps> = ({
  selectedScenario,
  onScenarioChange,
  onRun,
  isLoading,
}) => {
  // Track raw string values for the custom shock inputs so users can type
  // freely (e.g. "-" before completing "-20") without losing intermediate state.
  const [rawCustomShocks, setRawCustomShocks] = useState<Partial<Record<AssetClass, string>>>(() => {
    if (selectedScenario.id === 'custom') {
      const raw: Partial<Record<AssetClass, string>> = {};
      for (const ac of ALL_ASSET_CLASSES) {
        raw[ac] = String(selectedScenario.shocks[ac] ?? 0);
      }
      return raw;
    }
    const raw: Partial<Record<AssetClass, string>> = {};
    for (const ac of ALL_ASSET_CLASSES) {
      raw[ac] = '0';
    }
    return raw;
  });

  // ---------------------------------------------------------------------------
  // Derived validation state (Custom mode only)
  // ---------------------------------------------------------------------------

  const customShockValues: Partial<Record<AssetClass, number>> = {};
  const invalidClasses: AssetClass[] = [];

  if (selectedScenario.id === 'custom') {
    for (const ac of ALL_ASSET_CLASSES) {
      const raw = rawCustomShocks[ac] ?? '0';
      const parsed = parseFloat(raw);
      const numericValue = isNaN(parsed) ? 0 : parsed;
      customShockValues[ac] = numericValue;
      // Treat incomplete entry (e.g. "-") as invalid
      if (isNaN(parsed) || !isValidShock(numericValue)) {
        invalidClasses.push(ac);
      }
    }
  }

  const hasValidationError = selectedScenario.id === 'custom' && invalidClasses.length > 0;
  const canRun = !isLoading && !hasValidationError;

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  const handleScenarioSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const id = e.target.value as ScenarioConfig['id'];
    if (id === 'custom') {
      // Initialise raw strings from current custom values (or zero)
      const raw: Partial<Record<AssetClass, string>> = {};
      for (const ac of ALL_ASSET_CLASSES) {
        raw[ac] = String(selectedScenario.id === 'custom' ? (selectedScenario.shocks[ac] ?? 0) : 0);
      }
      setRawCustomShocks(raw);
      const shocks: Partial<Record<AssetClass, number>> = {};
      for (const ac of ALL_ASSET_CLASSES) {
        shocks[ac] = 0;
      }
      onScenarioChange({ id: 'custom', label: 'Custom', shocks });
    } else {
      onScenarioChange(namedToConfig(id as NamedScenarioId));
    }
  };

  const handleCustomShockChange = (ac: AssetClass, value: string) => {
    // Update raw string immediately for responsive input
    const newRaw = { ...rawCustomShocks, [ac]: value };
    setRawCustomShocks(newRaw);

    // Sync numeric values back to parent state
    const newShocks: Partial<Record<AssetClass, number>> = {};
    for (const cls of ALL_ASSET_CLASSES) {
      const raw = cls === ac ? value : (newRaw[cls] ?? '0');
      const parsed = parseFloat(raw);
      newShocks[cls] = isNaN(parsed) ? 0 : parsed;
    }
    onScenarioChange({
      ...selectedScenario,
      id: 'custom',
      label: 'Custom',
      shocks: newShocks,
    });
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div
      data-testid="scenario-picker-standalone"
      className="bg-white border border-[#e8e5e0] p-6 shadow-2xs space-y-4"
    >
      {/* Header */}
      <div className="flex items-baseline gap-3 border-b border-[#e8e5e0] pb-3">
        <span className="text-[10px] uppercase tracking-[0.14em] font-medium text-[#767676] font-mono">
          SCENARIO CONFIGURATION
        </span>
      </div>

      {/* Dropdown row */}
      <div className="flex flex-col sm:flex-row sm:items-end gap-4">
        <div className="flex-1 space-y-1.5">
          <label
            htmlFor="scenario-select"
            className="text-[10px] uppercase tracking-[0.12em] font-medium text-[#767676] font-mono"
          >
            Scenario
          </label>
          <select
            id="scenario-select"
            value={selectedScenario.id}
            onChange={handleScenarioSelect}
            disabled={isLoading}
            className="w-full appearance-none bg-[#faf9f6] border border-[#e8e5e0] text-[#121212] text-[13px] px-3 py-2.5 focus:outline-none focus:border-[#121212] cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {(Object.keys(NAMED_SCENARIOS) as NamedScenarioId[]).map((id) => (
              <option key={id} value={id}>
                {NAMED_SCENARIOS[id].label}
              </option>
            ))}
            <option value="custom">Custom</option>
          </select>
        </div>

        {/* Named scenario: read-only shock chips */}
        {selectedScenario.id !== 'custom' && (
          <div className="flex flex-wrap gap-2">
            {Object.entries(selectedScenario.shocks).map(([ac, shock]) => (
              <span
                key={ac}
                className={`px-2 py-1 border text-[10px] font-mono ${
                  (shock as number) < 0
                    ? 'bg-[#fcf5f5] text-[#7A1C28] border-[#eed6d9]'
                    : 'bg-[#faf9f6] text-[#666666] border-[#dedbd5]'
                }`}
              >
                {ac}: {(shock as number) >= 0 ? '+' : ''}
                {shock}%
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Custom scenario: editable shock table */}
      {selectedScenario.id === 'custom' && (
        <div className="space-y-2">
          <span className="text-[10px] uppercase tracking-[0.12em] font-medium text-[#767676] font-mono">
            Shock Values (%)
          </span>
          <div className="border border-[#e8e5e0] divide-y divide-[#e8e5e0]">
            {ALL_ASSET_CLASSES.map((ac) => {
              const rawVal = rawCustomShocks[ac] ?? '0';
              const parsed = parseFloat(rawVal);
              const isInvalid = isNaN(parsed) || !isValidShock(parsed);
              return (
                <div
                  key={ac}
                  className={`flex items-center justify-between px-4 py-2.5 ${
                    isInvalid ? 'bg-[#fcf5f5]' : 'bg-white'
                  }`}
                >
                  <span className="text-[12px] text-[#121212] font-medium">{ac}</span>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min={-100}
                      max={100}
                      step={1}
                      value={rawVal}
                      onChange={(e) => handleCustomShockChange(ac, e.target.value)}
                      disabled={isLoading}
                      aria-label={`${ac} shock percentage`}
                      className={`w-24 text-right bg-[#faf9f6] border text-[13px] px-2 py-1 focus:outline-none font-mono disabled:opacity-50 disabled:cursor-not-allowed ${
                        isInvalid
                          ? 'border-[#eed6d9] text-[#7A1C28] focus:border-[#7A1C28]'
                          : 'border-[#e8e5e0] text-[#121212] focus:border-[#121212]'
                      }`}
                    />
                    <span className="text-[12px] text-[#767676] font-mono w-4">%</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Inline validation message */}
          {hasValidationError && (
            <p
              role="alert"
              className="text-[11px] text-[#7A1C28] bg-[#fcf5f5] border border-[#eed6d9] px-3 py-2"
            >
              Shock values must be between −100% and +100%. Please correct:{' '}
              {invalidClasses.join(', ')}.
            </p>
          )}
        </div>
      )}

      {/* Run button */}
      <div className="flex items-center gap-3 pt-2">
        <button
          type="button"
          onClick={onRun}
          disabled={!canRun}
          aria-disabled={!canRun}
          className="bg-[#121212] text-white text-[10px] font-medium uppercase tracking-[0.14em] px-5 py-2.5 flex items-center gap-2 transition-colors cursor-pointer hover:bg-neutral-800 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Activity className="w-3.5 h-3.5" aria-hidden="true" />
          <span>{isLoading ? 'Running…' : 'Run Stress Tests'}</span>
        </button>

        {hasValidationError && (
          <span className="text-[11px] text-[#7A1C28] font-mono">
            Fix shock values to enable run
          </span>
        )}
      </div>
    </div>
  );
};

export default ScenarioPicker;
