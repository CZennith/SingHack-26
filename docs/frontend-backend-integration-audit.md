# Frontend/backend integration audit

## Scope and method

This audit reflects the repository as inspected on 5 September 2026. The code is the source of
truth. The audit covers the React/Vite frontend, its fixture data and connector types, the deployed
API, backend configuration and protocols, DuckDB ingestion and tables, snapshot and calculator
modules, evidence packets, result contracts, interpreter, tests, and the documented local/deployment
workflows.

The words `backend source` below include a local Python service or file-producing library even when
there is no HTTP route. `Can connect now?` is stricter: a browser cannot import Python modules or
open the local DuckDB, so a real frontend connection also needs a server transport or a deliberate
static-file deployment decision.

## 1. Executive summary

The frontend is not currently connected to the backend. `src/App.tsx` imports `currentRM`,
`executiveBriefing`, `macroIndicators`, `marketImpactPillars`, and `placeholderClients` directly
from `src/data/placeholderData.ts`. There is no `fetch`, Axios client, query hook, state store, or
connector implementation in the React application. `src/services/connectorContracts.ts` defines
future provider-neutral interfaces only, and `src/services/connectorConfig.ts` is not consumed by
the UI.

The only API route is `GET /api/health` in `api/health.py`. It returns `{ "status": "ok" }` and
does not open DuckDB or expose wealth data. The backend therefore has no browser-accessible route
for clients, portfolios, holdings, dates, exposure, evidence, or interpretation.

There is nevertheless substantial reusable backend functionality:

- DuckDB contains 20 clients, 24 portfolios, 1,015 holdings snapshots, transactions, mandates,
  market context, events, RM notes, planned cash needs, commitments, credit facilities, and
  normalized valuation/price/facility snapshot tables.
- `src/client_snapshot.py` can read the database read-only and produce a validated, client-scoped
  snapshot for one client or all clients. It accepts an exact `client_id`, `as_of_date`,
  `period_start`, and `period_end`.
- `src/calculators/exposure_base.py` produces direct USD exposure totals and groupings from one
  validated snapshot. `src/calculators/exposure_changes.py` compares two exposure bases and returns
  a validated, evidence-backed calculator result.
- `src/pipeline/evidence_packet.py` assembles a versioned, reviewable exposure-change packet from
  a snapshot and calculator result. `src/interpreter/` can post-process that packet through an
  injected client or the server-side OpenAI adapter, with strict evidence and recommendation
  boundaries.

The first practical integration is a read-only server adapter that returns a client snapshot and
its metadata. It can then feed existing exposure and packet outputs without duplicating arithmetic
in TypeScript. Client list/detail raw fields, holdings, portfolio totals, facility snapshots,
transactions, notes, events, planned cash needs, and commitments are data-supported. A thin
transport and response adapter are still required because no API route currently exists.

The current priority ranking, market-impact pillars, liquidity narrative, trajectory, synthesized
analysis, strategic opportunities, recommendations, emergency freeze, and order flow are not
backend capabilities. They should remain clearly labelled placeholders. Raw source data alone must
not be presented as a risk calculation, causal event explanation, suitability assessment, or advice.

Snapshot-date selection is supported by the local snapshot builder and DuckDB: the current database
has `2025-12-31`, `2026-02-27`, `2026-03-31`, `2026-06-30`, and `2026-08-26`. It is not supported
by the frontend or an API. The eventual API must expose valid dates, accept `as_of_date`, distinguish
comparison and period parameters, and return the selected metadata on every response.

The largest gaps are transport, identity mapping, date selection, the mismatch between the UI's
`ClientDossier` shape and the snapshot/result contracts, and the absence of domain calculators for
risk, performance, liquidity, event relevance, suitability, and recommendations.

## 2. Frontend inventory

| Frontend location | File/component | Current content | Current data source | Integration status | Recommended action |
|---|---|---|---|---|---|
| Application shell and view routing | `src/App.tsx` | Overview, clients directory, client detail, modal state, search, risk filtering, selection, toasts | Local React state and `placeholderData` imports | `PARTIALLY_SUPPORTED` | Keep the shell, replace the fixture repository with a query/cache adapter after a read-only API exists. Preserve `client_id` as the canonical identity. |
| RM/desk header | `src/App.tsx`, `src/data/placeholderData.ts` (`currentRM`) | RM name, desk, synthetic book label, alert count, fixed dataset date | Static fixture strings and number | `PARTIALLY_SUPPORTED` | Map RM/desk fields from `clients`; calculate book totals server-side if required. Do not expose a fabricated alert count. |
| Executive briefing strip | `src/App.tsx`, `executiveBriefing` | “Automated Portfolio Synthesis & Mandate Scan”, sync time, four-client summary | Static prose | `PLACEHOLDER_REQUIRED` | Replace only with a versioned backend result or evidence-bound interpretation. There is no current book-wide findings service. |
| Market macro ticker row | `src/components/MarketImpactSection.tsx`, `macroIndicators` | SNB, Fed, VXN, gold, Brent values and changes | Static fixture data | `READY_TO_CONNECT` for raw market context only; `PARTIALLY_SUPPORTED` overall | A server adapter can map `market_context` series/value/unit/date. It cannot infer the displayed changes or freshness unless the response includes them. |
| Market-impact pillar cards | `src/components/MarketImpactSection.tsx`, `marketImpactPillars` | Three narrative pillars, affected client counts/names, portfolio impact, desk context | Static fixture data | `PLACEHOLDER_REQUIRED` | Keep as placeholder. `event_log` and market context exist, but no event-to-holding/client impact calculator or findings contract exists. |
| Affected-account navigation pills | `MarketImpactSection.tsx`, `App.tsx` | Clicks fixture names and fuzzy-matches names/initials to fixture clients | `affectedClientNames` plus `placeholderClients` | `PARTIALLY_SUPPORTED` | Use exact `client_id` values from a future response. Remove name-based matching; it is unsafe for identity and duplicate names. |
| Priority client section | `src/App.tsx` | “Priority Clients”, pending-review count, expand/collapse controls | Static `placeholderClients`, local state | `PARTIALLY_SUPPORTED` | Client records and raw facility/holding inputs exist, but priority/risk magnitude is not calculated. Use backend findings only after a defined calculator contract. |
| Priority client card | `src/components/PriorityClientCard.tsx` | Risk badge, issue, AUM, tags, summary, cash, borrowing/LTV, suggested next step | `ClientDossier` fixture | `PARTIALLY_SUPPORTED` for facts; `PLACEHOLDER_REQUIRED` for conclusions/actions | Map raw facts from snapshot/result. Do not map fixture risk labels, summaries, tags, or suggested actions as if they were computed. |
| Coverage book/list | `src/components/ClientsListView.tsx` | Five fixture clients, search by name/ref/mandate/issue, risk filters, AUM and LTV | `placeholderClients`, local filter state | `PARTIALLY_SUPPORTED` | A future client-list/snapshot endpoint can provide the raw list. The current database has 20 clients and no computed risk severity or `ref` field. |
| Client detail header and identity | `src/components/ClientDetailPage.tsx` | Name, UHNW/HNW tier, mandate, AUM, reference, previous/next navigation | `ClientDossier` fixture | `PARTIALLY_SUPPORTED` | Use snapshot `client_id`, `client_name`, `wealth_band`, `total_aum_usd`, and portfolio mandate fields. `ref` is not in the database; do not invent it. |
| Intelligence overview / about | `ClientDetailPage.tsx` section 01 | Bio, age, occupation, client-since year | Fixture `about` object | `PARTIALLY_SUPPORTED` | Age and `client_since` exist in `clients`; bio and occupation do not. Show only available fields and label missing fields, or define a future profile contract. |
| Custody and liquidity metrics | `ClientDetailPage.tsx` section 02 | Total portfolio value, cash/liquidity, borrowing utilisation, LTV status and progress bar | Fixture `portfolio` object | `PARTIALLY_SUPPORTED` | Portfolio AUM and facility snapshots can supply raw values. Cash liquidity, utilization status, and a combined client metric require explicit aggregation and currency semantics. |
| Asset allocation bar | `ClientDetailPage.tsx` section 02 | Segmented allocation percentages and “Target vs Realised” label | Fixture `portfolio.allocation` | `PARTIALLY_SUPPORTED` | Use `exposure_base` groupings for realized direct USD exposure. Mandate targets exist in `mandate_rules`, but target-vs-realized comparison is not implemented. |
| 12-month trajectory chart | `ClientDetailPage.tsx` section 02 | Delta labels and a hard-coded SVG curve/trough/end marker | Fixture labels; SVG path is hard-coded and does not use `trajectory.points` | `PLACEHOLDER_REQUIRED` | Do not imply performance. `portfolio_valuations` and `instrument_prices` exist, but no performance/trajectory calculator or time-series API exists. |
| Top portfolio holdings | `ClientDetailPage.tsx` section 02 | Four fixture holdings, ticker, value, percentage, “77.9% of Total” | Fixture `topHoldings` | `READY_TO_CONNECT` for a raw holdings table; `PARTIALLY_SUPPORTED` for ranking/percentage | Snapshot `holdings` includes instrument, portfolio, market value, weight, currency, sector, region and liquidity metadata. Server-side ordering/selection should define “top”. |
| Synthesized analysis card | `ClientDetailPage.tsx` section 03 | Headline, narrative, why-it-matters, monitor text | Fixture `synthesisedAnalysis` | `PLACEHOLDER_REQUIRED` | The interpreter can explain a validated evidence packet, but no API route exists and its output shape differs. Do not treat fixture prose as generated analysis. |
| Strategic matrix | `ClientDetailPage.tsx` section 04 | Risks and opportunities lists | Fixture `strategicMatrix` | `PLACEHOLDER_REQUIRED` | No risk/opportunity or recommendation calculator exists. Result v1 explicitly excludes recommendations. |
| Prepare client brief modal | `src/components/Modals.tsx` (`BriefModal`) | Formats fixture facts, risks, opportunities, and a “Recommended Advisory Action”; copy/print actions | Local fixture object and browser APIs | `PLACEHOLDER_REQUIRED` | A future brief must use a validated packet/interpretation and RM review status. Remove “recommended” output until an approved contract and workflow exist. |
| View source data modal | `Modals.tsx` (`SourceDataModal`) | Static “planned” Core Banking, Market Data, and Audit Gateway labels | Static text describing connector interfaces | `PLACEHOLDER_REQUIRED` | Keep as a capability disclosure. It is not a source-data viewer; no connector implementation or route exists. |
| Emergency freeze modal | `Modals.tsx` (`EmergencyFreezeModal`) | Local “Record Prototype State” state transition; explicitly changes no facilities | Local `useState` only | `PLACEHOLDER_REQUIRED` | Do not connect to a financial action. A future audited control would require authorization, immutable audit persistence, and an approved execution contract. |
| New order modal | `Modals.tsx` (`NewOrderModal`) | Client/order type/amount form, local success message, no order sent | Local state and toast callback | `PLACEHOLDER_REQUIRED` | Keep disabled/prototype-labelled. `AuditConnector` is only a protocol; there is no order or audit route and no suitability/approval workflow. |
| Search and risk filters | `src/components/TopHeader.tsx`, `App.tsx`, `ClientsListView.tsx` | Fixture-only text filtering and local risk filtering | Local state over `placeholderClients` | `PARTIALLY_SUPPORTED` | Search can filter a fetched client list locally for small datasets. Risk filters require a backend-defined severity field; search must include exact IDs and instrument identifiers if supported. |
| Notification menu | `TopHeader.tsx` | Two hard-coded alerts, fixed “12m ago”/“45m ago”, badge count 4 | Static JSX | `PLACEHOLDER_REQUIRED` | No notification, findings, or audit API exists. Future notifications need IDs, severity, event time, client ID, evidence, and read state. |
| Sidebar navigation and client count | `src/components/Sidebar.tsx` | Overview/Clients navigation, count, fixed RM/booking desk card | Local props and `currentRM` fixture | `PARTIALLY_SUPPORTED` | Count should come from the client-list response. RM/desk data can be sourced from clients or a session profile, but no session endpoint exists. |

## 3. Backend capability inventory

| Backend route/service | File | Method/type | Data provided | Required parameters | Frontend sections it can support | Notes |
|---|---|---|---|---|---|---|
| Health endpoint | `api/health.py` | HTTP `GET /api/health` | `{status: "ok"}` | None | Deployment/status indicator only | The only implemented API route. It has no database, credential, or external-service dependency. |
| Runtime configuration | `backend/config.py`, `.env.example` | Python configuration service | `DEMO_MODE`, optional `WEALTH_DB_PATH` | Environment values | Future transport composition | `DEMO_MODE` defaults true. Private mode requires an explicit DB path. This module does not create a route or open the database. |
| Connector protocols | `backend/connectors/contracts.py` | Python `Protocol` interfaces | Planned wealth, market, event, insight, and audit seams | `ConnectorContext`: date, correlation ID, requester ID, optional client/portfolio | None directly; future adapter boundary | Interfaces have no concrete implementation, dependency injection, authentication, or transport. |
| Data ingestion/build | `src/build_database.py` and `sql/*.sql` | Local Python CLI/library | Raw CSV/JSON to a fresh DuckDB; normalized tables and ingestion metadata | `data_dir`, `db_path` | Supplies every data-backed feature indirectly | Build is a write operation and is not a request-time service. Raw source files are local/ignored. |
| Curated client data | DuckDB `clients` | Database table | Identity, RM, currency, wealth band, AUM, objectives, risk profile, horizon, liquidity needs, dates, KYC and source-of-wealth fields | `client_id` | Client list, profile, context, future filters | `occupation`, UI `ref`, UI bio, and a UI-ready tier label are absent. `total_aum_usd` is stored but has a date/current-value meaning that must be documented. |
| Portfolios and mandates | DuckDB `portfolios`, `mandate_rules` | Database tables | Portfolio IDs, client IDs, mandates, service model, base currency, inception, benchmark, AUM, allocation bands and notes | `client_id`; optionally `portfolio_id`, `mandate_code` | Portfolio header, allocation context, mandate display | Mandate rules are constraints, not a calculated breach/finding. |
| Holdings and instruments | DuckDB `holdings_snapshots`, `instruments` | Database tables | Dated positions, quantities, prices, local/base/USD values, weights, P&L fields, portfolio/client/instrument dimensions, liquidity and underlying metadata | `client_id`, exact `snapshot_date`; optionally `portfolio_id`, `instrument_id` | Holdings, exposure, instrument detail | Snapshot builder joins instrument metadata and preserves portfolio scope. Direct exposure is USD only; no look-through. |
| Valuations/prices/facilities by date | DuckDB `portfolio_valuations`, `instrument_prices`, `facility_snapshots` | Database tables | Five dated AUM/price/facility snapshots | `snapshot_date` plus client/portfolio/facility/instrument filters | Dated values, facility cards, future charts | Historical values exist, but no performance/return calculator or API response exists. |
| Transactions | DuckDB `transactions` | Database table | Trade/settlement dates, client/portfolio/instrument, type, quantity, price, currency, amount, narrative | `client_id`, inclusive `period_start`, `period_end`; optionally portfolio | Activity/history and future cash-flow context | Snapshot output includes period transactions; no frontend route or transaction view exists. |
| Planned cash needs | DuckDB `planned_cash_needs` | Database table | Need description, currency, amount, due window, recurrence and certainty | `client_id`, optionally due-period filters | Future liquidity panel | Data exists, but no available-cash versus need calculator or liquidity-pressure result exists. |
| Commitments | DuckDB `commitments` | Database table | Fund, currency, committed/called/uncalled amounts and expected call window | `client_id`, optionally `portfolio_id` | Future commitments/liquidity panel | No commitment aggregation or warning calculator exists. |
| Credit facilities | DuckDB `credit_facilities`, `facility_snapshots` | Database tables | Facility limit, currency, rates, margin threshold, current utilization and dated drawn/LTV/headroom | `client_id`, exact `snapshot_date`; optionally facility/portfolio | Borrowing/LTV raw metrics | Facility LTV and UI borrowing utilization are not interchangeable. No breach/priority calculator exists. |
| Market context | DuckDB `market_context` | Database table | Dated named series, category, unit and value | `snapshot_date`; optionally `series_id` | Raw macro indicators | No provider route or change/formatting contract. The UI fixture has values and changes that are not a direct response shape. |
| Event log | DuckDB `event_log` | Database table | Dated event type, region, description, transmission and severity | Inclusive `period_start`, `period_end`; optionally region/type | Event timeline and future evidence context | `event_log.csv` is authoritative for the demo, but no relevance or portfolio-impact matching exists. |
| RM notes | DuckDB `rm_notes` | Database table | Dated note text, RM identity, channel and client | `client_id`, inclusive period | Source/context panel and future review context | Notes are subjective and may conflict with structured data. No conflict detector or safe text endpoint exists. |
| Client snapshot builder | `src/client_snapshot.py` | Read-only Python library and CLI | Validated envelope: metadata, client, portfolios/mandates, exact-date holdings/summaries/facilities, period transactions/needs/commitments/notes/events, quality flags and source references | `client_id` or `--all-clients`, `as_of_date`, optional `period_start`, `period_end`, DB path | Client detail, holdings, raw supporting panels | Opens DuckDB with `read_only=True`. CLI writes canonical JSON only when an output destination is supplied; no HTTP service. |
| Exposure base | `src/calculators/exposure_base.py` | Pure Python function | Client total and direct USD groupings by portfolio, asset class, sub-asset class, sector, region, currency and instrument, with warnings/references | One validated snapshot | Allocation and exposure panels | Uses only `holdings[].market_value_usd`; does not convert currencies, calculate performance, or look through structures. |
| Exposure changes | `src/calculators/exposure_changes.py` | Pure Python function and CLI | Versioned result v1 with changed/added/exited/unchanged facts and current/previous evidence | Current and previous validated exposure bases/snapshots; CLI paths | Exposure-change review | Requires same client, different dates, direct USD exposure bases. CLI writes `outputs/exposure_changes/{client}/{comparison}_to_{as_of}.json`. |
| Evidence packet | `src/pipeline/evidence_packet.py` | Pure Python function and CLI | `exposure_change_review` packet with client context, facts/findings/evidence/warnings/assumptions and governance | Current snapshot plus calculator result(s) | Evidence-bound analysis input | Packet v1 requires RM review, prohibits recommendations, and permits LLM interpretation. It is not an HTTP service. |
| Result contract | `src/contracts/validation.py`, `serialization.py`, `result_models.py`, `docs/contracts/*` | Validator, typed models, JSON schema | Strict result metadata, facts, findings, evidence, warnings, assumptions and review flag | JSON payload | Client-side rendering only after an API exposes it | Result schema version is separate from snapshot and packet versions. v1 has no recommendation field. |
| Interpreter | `src/interpreter/*.py` | Local function, CLI, OpenAI adapter | Evidence-bound observations/questions/limitations/warnings with fact/evidence references | Validated packet, injected interpreter client or server-side OpenAI config | Future synthesized analysis/read-only review panel | No API route. It rejects unsupported numbers, causal claims and recommendation/trade language; output always requires RM review. |
| Protected output writer | `src/output_files.py`, `src/output_paths.py` | Local filesystem utility | Canonical JSON paths and atomic, validated writes | Output root/path, artifact metadata, explicit `overwrite` for replacement | Development artifact workflow only | It is intentionally not a frontend data service. Existing files are protected from accidental replacement. |

### Database contents and frontend readiness

The curated DuckDB tables are a useful source of facts but are not browser-ready contracts. The
snapshot builder is the current normalization boundary: it scopes every query by client and date,
joins instrument metadata, preserves nulls, and attaches source references. A future route should
prefer returning a validated snapshot or a purpose-built read model instead of exposing arbitrary
SQL rows to the browser.

The five valid holdings/valuation/price/facility dates are defined both by the built data and by
`SNAPSHOT_DATES` in `src/build_database.py`. The source file includes 20 clients and 24 portfolios;
the UI fixture includes only five clients and uses UI-only slug IDs such as
`ravi-chandrasekaran`, not database IDs such as `CL-0001`.

## 4. Frontend-to-backend mapping

| Frontend section | Existing backend source | Required request parameters | Relevant response fields | Can connect now? | Reason |
|---|---|---|---|---|---|
| Client directory | `clients`, or a snapshot-derived client list | `as_of_date` if showing dated AUM; optional search/risk filters | `client_id`, `client_name`, `wealth_band`, `total_aum_usd`, `risk_profile`, `rm_name`, `rm_desk` | Not directly; yes after a thin read API | Raw client data exists, but no route and no UI mapping for 20 records. |
| Client identity/profile | Snapshot `client` plus `portfolios` | `client_id`, `as_of_date` | `client_id`, name, age, client dates, objectives, life stage, source of wealth, risk/horizon/liquidity fields, portfolio mandates | Partially | Bio, occupation and UI reference are missing; portfolio mandate may be multiple. |
| Portfolio list | Snapshot `portfolios` and `portfolio_summaries` | `client_id`, `as_of_date` | Portfolio ID/name, mandate, currency, benchmark, holding count, `market_value_usd_total` | Yes after adapter | The snapshot already preserves portfolio scope and summary values. |
| Holdings table | Snapshot `holdings` | `client_id`, exact `as_of_date` and optional `portfolio_id` | Portfolio/instrument IDs, name, asset class, sector, region, currency, quantities, USD/base/local values, weight, liquidity, underlying metadata | Yes after adapter | All raw fields needed for a factual table exist. Define whether the table is direct-only and how nulls render. |
| Total portfolio value | Snapshot summaries or exposure base | `client_id`, `as_of_date` | Portfolio and client USD totals, holding/portfolio counts | Yes after adapter | Exposure base gives direct USD total; avoid summing base-currency values across portfolios. |
| Asset allocation | Exposure base | `client_id`, `as_of_date` | `client_total`, `by_asset_class`, `by_sub_asset_class`, `by_currency`, weights and warnings | Yes after adapter | Existing calculator supplies realized direct USD exposure. The current target comparison does not exist. |
| Top holdings | Snapshot holdings or exposure base `by_instrument` | `client_id`, `as_of_date`, optional `portfolio_id`, limit/order | Instrument ID/name, market value USD, weight, portfolio ID, underlying reference | Yes after adapter | Existing data supports ranking. The server should define top-N and preserve portfolio identity. |
| Borrowing/facilities | Snapshot `credit_facilities` | `client_id`, exact `as_of_date`, optional facility/portfolio | Facility ID, limit, currency, rate, threshold, drawn, LTV, headroom | Yes after adapter for raw facts | No risk-status or collateral-resilience finding is calculated. Do not equate LTV with facility utilization. |
| Transactions/activity | Snapshot `transactions` | `client_id`, `as_of_date`, `period_start`, `period_end`, optional portfolio | Transaction IDs, dates, type, instrument, quantity, price, currency, amount, narrative | Yes after adapter | Snapshot builder defines inclusive period semantics. No activity component currently exists. |
| Planned cash needs/commitments | Snapshot `planned_cash_needs`, `commitments` | `client_id`, period/date window | Amounts, currencies, due windows, called/uncalled, call window | Partially | Facts can be displayed, but liquidity pressure needs available cash, currency policy, and a calculator. |
| Market ticker | `market_context` or snapshot `market_events` only for events | `snapshot_date`, series IDs | Series ID/name, category, unit, value, snapshot date/label | Partially | Raw series exists in DuckDB, but no route and no current/change response. |
| Event panel | Snapshot `market_events` | `client_id`, `period_start`, `period_end` | Event date/type/region/description/transmission/severity | Partially | Event rows are available, but affected-client matching and causality are not implemented. |
| RM notes/source context | Snapshot `rm_notes`, `source_references` | `client_id`, period | Note text/date/channel; table/key provenance | Partially | Source facts exist, but note-vs-data conflict analysis and access controls are missing. |
| Exposure-change panel | Exposure-change result | `client_id`, current/previous `as_of_date`, both snapshots | Result metadata, facts, scopes, current/previous values, changes, statuses, evidence IDs and warnings | Yes after adapter | Existing contract is suitable for factual change display. The result period fields are nullable, so dates must come from result metadata and input snapshots. |
| Evidence/review panel | Evidence packet | `client_id`, current/previous dates, packet type | Packet metadata, client context, facts/findings/evidence/warnings/assumptions/governance | Yes after adapter | Packet is intentionally limited to exposure-change evidence and RM review; it is not a full dashboard model. |
| Synthesized analysis | Interpreter output from evidence packet | `client_id`, current/previous dates, packet | Summary, observations, questions, limitations, warnings, evidence/fact references, review flag | Not yet | Local interpreter exists, but no route, UI adapter, authorization, or output-to-UI mapping exists. |
| Risk/opportunity matrix | No existing calculator/result | Future `client_id`, `as_of_date`, policy/version | Future findings with facts/evidence and review state | No | Current result/packet contracts intentionally exclude recommendations and unsupported findings. |
| Brief/order/freeze actions | No existing execution/audit route | Future authenticated client/action/context | Future decision ID, authorization, audit record, status | No | Current controls only update local prototype state and explicitly send nothing. |

No frontend section is `ALREADY_CONNECTED` today. The raw factual sections are domain-ready but
still require a transport adapter because the only HTTP endpoint is health.

## 5. Snapshot-date integration audit

### Existing date behavior

The database contains five exact snapshot dates. `src/client_snapshot.py` discovers available
dates from `holdings_snapshots`, requires `as_of_date` to be one of those dates, and opens DuckDB
read-only in its CLI. `period_start` and `period_end` are ordinary ISO dates; period records are
filtered inclusively. When omitted, `period_end` defaults to `as_of_date` and `period_start` defaults
to the previous available holdings date.

The local APIs accept:

- Snapshot: `client_id`, `as_of_date`, optional `period_start`, `period_end`.
- Exposure base: one snapshot; its date comes from `snapshot_metadata.as_of_date`.
- Exposure changes: current and previous exposure bases; dates must differ and client IDs must
  match.
- Evidence packet: one current snapshot and result(s); result dates must be compatible.
- Interpreter: one validated evidence packet; metadata must match the packet.

The frontend has no date selector. `src/data/placeholderData.ts` hard-codes 26 August 2026 in
several labels, while `src/services/connectorConfig.ts` contains an unused `VITE_DATA_AS_OF`
default. The fixture client values do not change when a date changes.

| Frontend section | Uses snapshot date? | Existing date source | Existing backend parameter | Can support date selection now? | Missing requirement |
|---|---|---|---|---|---|
| Overview dataset label/RM header | Yes, as a displayed freshness value | Hard-coded fixture text | Snapshot `as_of_date` | No | Date-aware API response and global selected-date state. |
| Market tickers/events | Yes | Fixture date; DB `market_context`/`event_log` | `snapshot_date` or inclusive period | No | Dates endpoint, series response, event-period response and freshness metadata. |
| Priority list/cards | Yes for AUM, holdings and facility facts | Fixture “26 Aug 2026” | Snapshot `client_id`, `as_of_date`; optional period | No | Date-scoped client read model and a defined risk/finding calculation if risk labels remain. |
| Client profile | Partly | Fixture snapshot label; static profile fields | `client_id`, `as_of_date` | No | Distinguish static identity fields from date-sensitive AUM/risk fields. |
| Portfolio value/allocation/holdings | Yes | Fixture values | Exact `client_id`, `as_of_date` | No | Snapshot route and selected-date cache/invalidation. |
| Facility/LTV | Yes | Fixture values and fixed valuation label | `client_id`, exact `as_of_date` | No | Facility response must include snapshot date, units/currency, threshold and headroom. |
| Transactions/RM notes/events/cash needs | Period-dependent | None in UI | `client_id`, `period_start`, `period_end` | No | Period control separate from valuation-date control and inclusive-range metadata. |
| Trajectory/performance | Yes across multiple dates | Hard-coded SVG and labels | Future date range or date series | No | Performance/trajectory calculator and explicit methodology; historical raw tables alone are not a return result. |
| Exposure base | Yes | Snapshot metadata | One snapshot `as_of_date` | No | Snapshot transport; direct USD and no-look-through semantics must be shown. |
| Exposure changes | Yes, current plus comparison | No UI control | Current and previous snapshot dates | No | Comparison-date control, date compatibility checks and result metadata in the API response. |
| Evidence packet/interpreter | Yes, current/comparison/period | No UI control | Packet and interpreter inputs carry all dates | No | Packet endpoint, selected-date state, review/status handling and strict UI response adapter. |
| Brief/source modals | Inherited from client/analysis | Fixture date only | Future snapshot/packet context | No | Preserve provenance and selected dates in the document; do not print fixture claims. |

The eventual date workflow should be:

1. Fetch valid dates and labels from a backend endpoint backed by `holdings_snapshots` (and confirm
   that valuations/facilities/market data have the same coverage).
2. Store a selected `as_of_date` and a separate optional `comparison_date` in application state.
3. Fetch or build a snapshot with the selected client/date/period and return metadata including
   snapshot schema and calculation versions.
4. Derive exposure and evidence results from that snapshot, never from a second frontend
   calculation.
5. Invalidate date-sensitive cards when the selected date changes and visibly display the returned
   dates on every section.

## 6. Placeholder decisions

These sections should remain placeholders until the stated backend capability exists:

| Frontend area | Why it cannot be connected now | Limitation type | Future capability | Safe placeholder message |
|---|---|---|---|---|
| Executive briefing and priority ranking | No book-wide priority/finding service; fixture count and ranking are static | Missing calculator, route and contract | Versioned book-scan result containing client IDs, facts, evidence, severity policy and generated-at/as-of metadata | “Priority scan is a prototype view; no live findings are connected.” |
| Market-impact pillars | Events and market series exist but no deterministic client/holding impact match exists | Missing calculator and route | Event-impact result with event ID, affected client/portfolio/instrument IDs, matching rationale and evidence | “Market context is available; portfolio impact analysis is not yet implemented.” |
| Liquidity-pressure panel | Cash needs and commitments exist, but cash holdings, currencies, timing, facilities and offsets are not reconciled | Missing calculator, currency policy and contract | Liquidity result with as-of/period metadata, need windows, available liquidity basis, currency treatment, warnings and evidence | “Planned needs are sourced data; liquidity pressure has not been calculated.” |
| Suitability/mandate risks | Mandate bands and client risk fields exist, but no breach/drift/waiver logic exists | Missing calculator and policy contract | Mandate-observation result with portfolio, rule version, realized allocation, breach status, waiver evidence and RM review | “Mandate rules are available; compliance observations are not calculated.” |
| Note-versus-data conflicts | RM notes are available, but no controlled comparison or conflict classification exists | Missing analysis service and contract | Conflict result linking a note field/quote to structured facts, confidence, status and source references | “RM notes are contextual and require review; conflicts are not automatically classified.” |
| Event relevance/causality | `event_log` has transmission descriptions, but no causal attribution is supported | Missing calculator/policy | Event-link result that states matching evidence and uncertainty without claiming causation | “Events are shown as source context; causal impact is not asserted.” |
| Performance/trajectory | Historical valuation/price tables are raw inputs, not returns; current SVG is hard-coded | Missing calculator and methodology | Performance result with return method, valuation dates, currency policy, missing-data handling and evidence | “Historical trajectory is a visual placeholder; performance is not calculated.” |
| Synthesized analysis/LLM | Interpreter is local and packet-bound; no API or UI adapter; it cannot fill missing data | Missing route, authorization and response adapter | Packet endpoint plus interpretation endpoint returning strict observations, questions, limitations, warnings and references | “Evidence-bound interpretation is not available in this preview.” |
| Recommendations/opportunities | Result v1, packet v1 and interpreter prohibit recommendations/trade language | Missing business logic, governance and contract | Separate approved recommendation contract with suitability, authorization, rationale, evidence and audit trail | “No recommendation is generated; RM review and approved workflow are required.” |
| Emergency freeze/order controls | UI only changes local state and explicitly sends no order/freeze | Missing execution/audit route and controls | Authenticated action API, idempotency, authorization, immutable audit event, approval state and downstream status | “Prototype control only; no facilities or orders are changed.” |

Mock financial data must not be silently retained when any of these sections is connected. A raw
fact should be shown with source/date/units; a finding or recommendation should only be shown with
the corresponding validated contract and evidence.

## 7. Recommended implementation order

### Can connect immediately at the domain layer

These require existing functionality only and no new financial calculation. They still need a
server transport because a browser cannot call the current Python functions directly.

1. Client directory and profile facts from `clients`, `portfolios`, and the snapshot builder:
   `src/client_snapshot.py`, `src/App.tsx`, `src/components/ClientsListView.tsx`, and
   `src/components/ClientDetailPage.tsx`.
2. Dated holdings, portfolio summaries, instrument metadata and top holdings from the validated
   snapshot: `src/client_snapshot.py` and `ClientDetailPage.tsx`.
3. Direct realized allocation and exposure totals from `src/calculators/exposure_base.py`, mapped
   to `ClientDetailPage.tsx` without re-aggregating in TypeScript.
4. Raw facility facts, transactions, planned cash needs, commitments, RM notes and events from
   snapshot sections, shown as source data rather than risk conclusions.
5. Exposure changes from the validated result emitted by `src/calculators/exposure_changes.py`,
   rendered as facts/statuses with evidence IDs.

### Requires a small integration adapter

1. Add a read-only API composition layer around `build_client_snapshot` with strict request
   validation for `client_id`, `as_of_date`, `period_start`, and `period_end`; return the validated
   snapshot or a stable read model. Relevant files: `backend/config.py`, `src/client_snapshot.py`,
   `src/snapshot_models.py`, `src/contracts/serialization.py`, and the future API module.
2. Add an available-dates response backed by `holdings_snapshots`, including coverage/validation
   for valuations, facilities and market context. Connect it to the future date control rather than
   hard-coding `VITE_DATA_AS_OF`.
3. Add result/packet read endpoints or a server-side pipeline endpoint that invokes existing pure
   functions. Return `result_metadata`, packet governance, version fields and evidence references
   unchanged.
4. Add a frontend mapper from snapshot/result contracts to explicitly factual UI view models. Keep
   missing fields nullable and remove fixture-only fields rather than inventing them.
5. Add an authenticated, read-only interpreter endpoint only after the packet endpoint and review
   status are in place. Use `src/interpreter/validation.py` and keep `requires_rm_review=true`.

### Must remain placeholders

Market-impact narratives, risk priority, liquidity pressure, suitability observations, note/data
conflicts, event causality, performance trajectory, recommendations, order routing, and emergency
freeze remain placeholders until their calculators, policy versions, contracts, API routes,
authorization, and evidence behavior are designed and tested. The existing fixture UI should not be
relabelled as live functionality.

## 8. Risks and inconsistencies

### Data and identity

- The UI contains five fixture clients, while DuckDB contains 20. The current selected ID is a
  human-readable slug (`ravi-chandrasekaran`); the database uses IDs such as `CL-0001`.
- Market-impact navigation uses fuzzy name matching through `affectedClientNames`; this can select
  the wrong account and ignores the already-present `affectedClientIds` fixture field.
- UI `ref`, `occupation`, bio, and several tier/profile fields do not exist in the curated client
  table. `wealth_band` can inform a tier mapping, but it is not automatically equivalent.
- Some clients have multiple portfolios. Client-level AUM and portfolio-level values must not be
  confused, and portfolio IDs must remain attached to holdings and exposure groups.

### Date, currency, and freshness

- Multiple components display a fixed “26 Aug 2026” or “16:00 EST” even though no selected-date or
  timezone response exists.
- Transactions, RM notes, and events are inclusive period data; holdings and facility snapshots are
  exact as-of data. One global date should not be applied to all sections without the correct period
  semantics.
- The exposure base is direct `market_value_usd`; it does not perform currency conversion or
  look-through. UI percentages must not silently mix `market_value_base`, local currency, and USD.
- Facility `ltv_pct`, `utilisation_pct_current`, `drawn`, `credit_limit`, and `headroom` are distinct
  fields. The fixture's “borrowing utilisation” and LTV progress bar should not be mapped by name
  alone.
- The UI's allocation label says “Target vs Realised”, but the existing exposure calculator only
  provides realized direct exposure. Mandate targets exist but no comparison result exists.
- The trajectory SVG uses a hard-coded curve rather than `trajectory.points`; it is not a backend
  performance view.

### Response-shape and contract risks

- `ClientDossier` is a presentation model containing prose, tags, risk labels, allocation colors,
  trajectory labels, and suggested actions. It is not a snapshot or result contract.
- Snapshot v1 has `snapshot_metadata`, raw/context arrays, quality flags and source references.
  Calculator result v1 has separate result metadata, facts, findings, evidence, warnings and
  assumptions. Evidence packet v1 adds governance. These envelopes must not be flattened into one
  undocumented frontend shape.
- Result `period_start` and `period_end` are optional/nullable; exposure change uses
  `as_of_date` and `comparison_date`. The UI must not assume a result period exists.
- The snapshot builder uses `calculation_version`; result and packet metadata also carry separate
  schema/calculation/version fields. Preserve these distinctions in UI provenance.
- The packet intentionally carries minimal client context plus calculator evidence; it is not a
  complete replacement for the full snapshot. Raw holdings, transactions, notes and events are not
  automatically available to the interpreter through packet context.

### Safety and governance

- Fixture text contains recommendations, “target solutions”, “suggested next step”, and causal
  market narratives even though current result, packet and interpreter boundaries prohibit those
  outputs.
- Notifications are hard-coded with relative times and a badge count; they could be mistaken for
  live alerts.
- Emergency freeze and New Order controls are explicitly simulations. Connecting them would be a
  materially different execution capability requiring authorization and audit controls.
- The only deployed route is health. The browser must not receive `WEALTH_DB_PATH`, `OPENAI_API_KEY`,
  or raw private data through `VITE_*` variables. Local DuckDB must remain read-only for readers.
- The current Vercel preview configuration deliberately excludes raw data, database, tests, and
  outputs. A preview cannot use the local DuckDB unless a separately approved sanitized service is
  provided.

## 9. Proposed future API contracts

These are proposals only. They are not implemented by this audit.

### `GET /api/metadata/snapshot-dates`

Request parameters: optional `client_id` and `dataset`/coverage selector.

Response:

```json
{
  "data_type": "snapshot_dates",
  "schema_version": "1.0.0",
  "dates": [
    {"as_of_date": "2026-06-30", "holdings": true, "valuations": true, "facilities": true, "market_context": true},
    {"as_of_date": "2026-08-26", "holdings": true, "valuations": true, "facilities": true, "market_context": true}
  ],
  "source": "wealth.duckdb"
}
```

Error cases: invalid client, unavailable/partial date coverage, inaccessible database, malformed
date, and unauthorized requester. The response is metadata derived from DuckDB, not a calculator
result.

### `GET /api/clients`

Request parameters: optional `as_of_date`, search, and pagination/filter parameters. If AUM is
dated, `as_of_date` is required and must be a valid date.

Minimum response fields: `client_id`, `client_name`, `wealth_band`, `total_aum_usd`, `base_currency`,
`risk_profile`, `rm_id`, `rm_name`, `rm_desk`, selected-date metadata, `snapshot_schema_version`, and
`snapshot_calculation_version`. It must not include an invented UI `ref` or risk severity.

Error cases: invalid date, unknown filter, unavailable database, unauthorized requester, and partial
data coverage.

### `GET /api/clients/{client_id}/snapshot`

Request parameters: required `as_of_date`; optional `period_start`, `period_end`, and `portfolio_id`.
The service should call the read-only snapshot builder and enforce client/portfolio ownership.

Minimum response: the validated snapshot envelope from `validate_snapshot`, including
`snapshot_metadata` (`client_id`, `as_of_date`, `period_start`, `period_end`,
`calculation_version`, and provenance), `client`, `portfolios`, `portfolio_summaries`, `holdings`,
`transactions`, `planned_cash_needs`, `commitments`, `credit_facilities`, `rm_notes`,
`market_events`, `data_quality_flags`, and `source_references`.

Error cases: missing/unknown client, invalid or unsupported as-of date, invalid period, portfolio
not owned by client, database unavailable, and validation failure. The response is a snapshot, not a
recommendation or interpretation.

### `GET /api/clients/{client_id}/exposure`

Request parameters: required `as_of_date`; optional `period_start`, `period_end` only for input
snapshot provenance.

Minimum response: validated exposure-base object with `exposure_metadata`, `client_total`,
`by_portfolio`, `by_asset_class`, `by_sub_asset_class`, `by_sector`, `by_region`, `by_currency`,
`by_instrument`, warnings, source references, `currency_basis: "USD"`, and
`look_through_included: false`.

Error cases: snapshot failure, missing/non-numeric USD value, unsupported look-through request,
invalid date, client mismatch, and database unavailable. This should call
`build_exposure_base`; the frontend should not duplicate grouping arithmetic.

### `GET /api/clients/{client_id}/exposure-changes`

Request parameters: required `as_of_date` and `comparison_date`; optional period parameters for
the two source snapshots.

Minimum response: validated result v1 from `calculate_exposure_changes`, including separate result
schema, calculator version, input snapshot schema/calculation versions, current/comparison dates,
facts, evidence IDs, warnings, assumptions, and `requires_rm_review`.

Error cases: dates equal/reversed/unavailable, client mismatch, invalid snapshots, unsupported
exposure basis, result validation failure, and database unavailable.

### `GET /api/clients/{client_id}/evidence-packet`

Request parameters: required current and comparison dates and packet type. Optional period bounds
must be passed through and reflected in packet metadata.

Minimum response: validated `exposure_change_review` packet with packet schema/version, client
context, facts/findings/evidence/warnings/assumptions, included calculators, and governance:
`requires_rm_review: true`, `recommendations_allowed: false`,
`llm_interpretation_allowed: true`, `source_data_is_authoritative: true`.

Error cases: incompatible dates/results, client mismatch, unsupported packet type, missing evidence,
contract validation failure, or unavailable source data.

### `POST /api/clients/{client_id}/interpretations`

This is future work and should accept a packet reference or validated packet body, not arbitrary
frontend prose. Request parameters/body should include packet ID or packet, requester/correlation
metadata, and an explicit RM-review context. It should invoke the existing evidence-bound
interpreter only after authorization and packet validation.

Minimum response fields: `interpretation_metadata` matching packet client/current/comparison dates
and packet schema, `executive_summary`, evidence-linked `observations`, `questions_for_rm`,
`limitations`, `warnings`, and `requires_rm_review: true`. No recommendations, trades, causal claims,
unsupported numbers, hidden reasoning, or API key may be returned.

Error cases: invalid packet, unsupported packet version, unauthorized requester, provider timeout or
refusal, invalid model output, unsupported evidence reference, and incomplete/partial packet. The
existing interpreter validation rules should remain authoritative.

### Future analytical contracts

Risk priority, liquidity pressure, mandate observations, event relevance, performance, suitability,
conflict detection, recommendations, audit actions, and execution controls each need a separate
versioned result or action contract. Each should include request dates, client/portfolio scope,
calculation/policy version, explicit currency and missing-data semantics, evidence references,
warnings, and RM-review/governance fields. None should be represented by extending the fixture
`ClientDossier` with unverified strings.

## 10. Audit conclusion

The exact first factual frontend connections should be:

- `src/components/ClientsListView.tsx` and `src/components/Sidebar.tsx` using a future read-only
  clients response from `clients`.
- `src/components/ClientDetailPage.tsx` identity, portfolios, holdings, raw facility metrics and
  portfolio summaries using `src/client_snapshot.py` output.
- The holdings/allocation portions of `ClientDetailPage.tsx` using
  `src/calculators/exposure_base.py` output, preserving direct USD semantics.
- A new exposure-change view using the validated result from
  `src/calculators/exposure_changes.py`, with evidence and date metadata intact.
- A source/evidence view using the validated snapshot `source_references` and evidence packet, not
  the current static “planned” modal.

The existing backend sources for those connections are the read-only snapshot builder, DuckDB
curated tables, exposure base, exposure changes, result validator, and evidence packet builder.
They are local Python/file capabilities today and require a narrow server transport before the
browser can use them.

The following must remain placeholders: fixture executive briefing and priority ranking,
market-impact pillars, liquidity pressure, suitability/mandate findings, note/data conflicts, event
causality, performance trajectory, recommendations, emergency freeze, order routing, and live
notifications. The interpreter may eventually support an evidence-bound review panel, but it is not
currently frontend-connected and cannot supply missing calculations or recommendations.

Snapshot-date selection is technically supported in the database and snapshot builder but not in
the current frontend/API. It needs an available-dates endpoint, selected-date and comparison-date
state, date-aware read models, coverage/error handling, and visible provenance.

The recommended next implementation task is to add a read-only API adapter for
`GET /api/metadata/snapshot-dates`, `GET /api/clients`, and
`GET /api/clients/{client_id}/snapshot`, together with contract tests for identity, date scoping,
read-only database access, and no cross-client data. Once those responses are stable, connect the
client list/detail factual fields and direct exposure; do not start with recommendations or the
fixture narrative sections.

No application code, API route, database, data file, test, configuration, or frontend file was
modified for this audit. The only intended repository change is this document.
