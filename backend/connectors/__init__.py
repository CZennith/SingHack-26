"""Provider-neutral connector protocols; implementations belong in team feature branches."""

from .contracts import (
    AuditConnector,
    ConnectorContext,
    CoreBankingConnector,
    EventLogConnector,
    InsightConnector,
    MarketDataConnector,
    WealthDataConnector,
)

__all__ = [
    "AuditConnector",
    "ConnectorContext",
    "CoreBankingConnector",
    "EventLogConnector",
    "InsightConnector",
    "MarketDataConnector",
    "WealthDataConnector",
]
