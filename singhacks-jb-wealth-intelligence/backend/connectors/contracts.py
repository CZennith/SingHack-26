"""Typed seams for future wealth-intelligence integrations.

Only protocols and transport-neutral value objects live here. A concrete
connector must be implemented behind one of these interfaces and injected by
the future application composition layer.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Mapping, Protocol, Sequence


Record = Mapping[str, Any]


@dataclass(frozen=True)
class ConnectorContext:
    """Request metadata required for traceability and point-in-time reads."""

    as_of: date
    correlation_id: str
    requester_id: str
    client_id: str | None = None
    portfolio_id: str | None = None


@dataclass(frozen=True)
class EvidenceRef:
    """A source reference an insight must expose to the RM."""

    source: str
    record_id: str
    as_of: date
    fields: tuple[str, ...] = field(default_factory=tuple)


class WealthDataConnector(Protocol):
    """Read client, portfolio and suitability data from a controlled source."""

    def get_clients(self, context: ConnectorContext) -> Sequence[Record]: ...

    def get_portfolios(self, context: ConnectorContext) -> Sequence[Record]: ...

    def get_holdings(self, context: ConnectorContext) -> Sequence[Record]: ...

    def get_instruments(self, context: ConnectorContext) -> Sequence[Record]: ...

    def get_mandates(self, context: ConnectorContext) -> Sequence[Record]: ...

    def get_transactions(self, context: ConnectorContext) -> Sequence[Record]: ...

    def get_credit_facilities(self, context: ConnectorContext) -> Sequence[Record]: ...

    def get_commitments(self, context: ConnectorContext) -> Sequence[Record]: ...

    def get_planned_cash_needs(self, context: ConnectorContext) -> Sequence[Record]: ...


class MarketDataConnector(Protocol):
    """Read market series at the same dated snapshots as portfolio positions."""

    def get_market_context(self, context: ConnectorContext) -> Sequence[Record]: ...


class EventLogConnector(Protocol):
    """Read the controlled event source; event_log.csv is authoritative in the demo."""

    def get_events(self, context: ConnectorContext) -> Sequence[Record]: ...


class InsightConnector(Protocol):
    """Generate or retrieve grounded intelligence, never unsupported assertions."""

    def generate_insight(
        self,
        context: ConnectorContext,
        inputs: Sequence[Record],
    ) -> Mapping[str, Any]: ...

    def explain_insight(
        self,
        context: ConnectorContext,
        insight_id: str,
    ) -> Sequence[EvidenceRef]: ...


class AuditConnector(Protocol):
    """Persist RM review and decision events in an immutable audit trail."""

    def record_review(
        self,
        context: ConnectorContext,
        insight_id: str,
        decision: str,
        rationale: str | None = None,
    ) -> None: ...
