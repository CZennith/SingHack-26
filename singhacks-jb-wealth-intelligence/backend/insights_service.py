"""Generate or retrieve source-grounded advisory insights for a client."""

from data_repository import (
    get_client,
    get_client_cash_needs,
    get_client_commitments,
    get_client_transactions,
)


def build_client_insights(client_id: str) -> dict:
    """Return the payload for GET /clients/{client_id}/insights.

    TODO: derive deterministic mandate/liquidity/concentration flags, obtain RM
    notes, then retrieve or generate validated LLM output. Never let the model
    invent financial values; pass it calculated source facts and return JSON
    matching ClientInsightsResponse in main.py.
    """
    client = get_client(client_id)
    if client is None:
        raise LookupError(f"Unknown client: {client_id}")

    cash_needs = get_client_cash_needs(client_id)
    commitments = get_client_commitments(client_id)
    transactions = get_client_transactions(client_id)
    _ = (cash_needs, commitments, transactions)
    raise NotImplementedError
