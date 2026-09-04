# Editing the Wealth Intelligence project

This repository is the shared SingHacks workspace for the Julius Baer wealth
intelligence concept. The current Aurelius UI is a prototype presentation
layer. It uses synthetic fixture data so the team can work on journeys and
visuals while backend integrations are designed.

## Repository layout

```text
data/                  Synthetic challenge data; do not replace or enrich it with real data
docs/                  Data dictionary, prototype notes, and this contributor guide
starter/               Read-only dataset orientation script
backend/connectors/    Python protocols only; no running backend or provider adapters
frontend/              React/Vite/Tailwind prototype and frontend connector contracts
```

The original prototype README is preserved at
[`docs/PROTOTYPE_README.md`](PROTOTYPE_README.md). The challenge README remains
the product and data source of truth.

## Local setup

From the repository root:

```bash
# Python orientation dependency
python3 -m pip install --user --break-system-packages -r requirements.txt
python3 starter/quickstart.py

# Frontend
cd frontend
npm install
cp .env.example .env.local       # optional; defaults to fixture mode
npm run typecheck
npm run build
npm run dev
```

The frontend runs on `http://localhost:3000`. Do not commit `.env.local` or
any credentials. The `.env.example` file contains only public, non-secret
settings.

## Current frontend boundary

The UI currently imports `src/data/placeholderData.ts`. That file is a
presentation fixture, not a data access layer. The typed replacement boundary
is in `src/services/connectorContracts.ts` and `src/services/connectorConfig.ts`.
When a live adapter is ready, replace the fixture repository at a composition
boundary (for example, a React data hook or page-level loader), rather than
adding `fetch` calls inside visual components.

`VITE_CONNECTOR_MODE=mock` is the safe default. `live` is reserved for a future
environment with an approved backend. The browser must never receive provider
secrets or direct credentials.

## Connector responsibilities

Implementations should remain behind the provider-neutral contracts in
`backend/connectors/contracts.py` and mirror them in the frontend contracts:

| Contract | Responsibility | Challenge source / future provider |
|---|---|---|
| `WealthDataConnector` | Clients, portfolios, holdings, instruments, mandates, transactions, credit, commitments, cash needs | `data/*.csv`; future core-banking or portfolio service |
| `MarketDataConnector` | Dated market series aligned to portfolio snapshots | `market_context.csv`; future market-data provider |
| `EventLogConnector` | Controlled 2026 events and transmission channels | `event_log.csv` is authoritative |
| `InsightConnector` | Grounded explanations, alerts, recommendations, and evidence | Future analytics/AI service |
| `AuditConnector` | RM review, decision, rationale, and traceability | Future audit/compliance service |

Every point-in-time read must carry an `as_of` date and correlation/requester
metadata. An insight must include inspectable evidence references. Generated
recommendations are suggestions for RM review, never automatic orders or
client communications.

## Data rules that feature work must preserve

- Use all five holding snapshots when explaining change; do not collapse the
  dataset to only today’s positions.
- Join across `client_id`, `portfolio_id`, and `instrument_id` carefully.
  Aggregate across a client’s portfolios before assessing book-level risk.
- Look through structured products using
  `instruments.underlying_reference`, not only the displayed asset class.
- Use `event_log.csv` for 2026 events. Do not let an AI model invent or replace
  the controlled event record.
- Keep tax domicile separate from country of residence.
- Treat custody portfolios as part of total wealth but not as bank-managed
  mandate portfolios.
- Surface uncertainty, lagging private-market valuations, and source conflicts
  to the RM rather than silently smoothing them away.
- The data is synthetic, but it should be handled as confidential client data.

## How to add a feature

1. Start with a narrow user outcome, ideally for two or three clients rather
   than a shallow feature across all twenty.
2. Read the relevant rows and the RM notes before choosing calculations or
   copy. Record the source fields and snapshot date in the feature notes.
3. Add or extend a provider-neutral type in `frontend/src/services/` and/or
   `backend/connectors/` before adding a provider-specific implementation.
4. Keep UI components focused on rendering and user actions. Put data loading,
   transformation, and error states in a hook/service boundary.
5. For insights, display the reason, source evidence, assumptions, and the
   RM-controlled next step. Never present a generated recommendation as an
   executed trade.
6. Add fixture coverage for loading, empty, stale, conflicting, and error
   states. Keep new fixtures synthetic and clearly labelled.
7. Run `npm run typecheck`, `npm run build`, and `python3 starter/quickstart.py`
   before opening a pull request.

## Team handoff checklist

- One feature per branch or pull request; avoid editing another feature’s
  connector or component without coordinating.
- Keep commits small enough to review and describe the user outcome in the PR.
- Do not commit `.env*` files except the provided `.env.example`, secrets,
  real client data, generated build output, or `node_modules/`.
- If a connector needs a new endpoint, document the request/response shape,
  authentication ownership, timeout/retry policy, evidence fields, and audit
  event before implementation.
- If the data contradicts a note or another source, preserve both values and
  label the conflict; do not overwrite the authoritative source.
