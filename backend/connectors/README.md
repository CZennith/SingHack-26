# Backend connector contracts

This folder is an integration boundary, not a backend service. It contains
Python `Protocol` definitions and small value objects only. There is no web
server, database client, market-data client, LLM client, or credential handling
here yet.

Implement future providers behind the contracts in `contracts.py`, then wire
them through an application composition layer. Keep the provider-specific
mapping, authentication, retries, and observability in that adapter; keep the
frontend and intelligence layer provider-neutral.

The demo dataset maps naturally to `WealthDataConnector` and
`MarketDataConnector`. `EventLogConnector` must remain the authoritative source
for 2026 events, and every generated insight should return evidence references
that an RM can inspect.
