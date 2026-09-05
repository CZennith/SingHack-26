"""Build deterministic client dossier data from repository records."""

from data_repository import (
    get_client,
    get_client_facilities,
    get_client_holdings,
    get_client_portfolios,
)


def build_client_dossier(client_id: str) -> dict:
    """Return the payload for GET /clients/{client_id}/dossier.

    TODO: validate the client, aggregate holdings, calculate liquidity/allocation
    and facility metrics, build trajectory points, and map results to the
    ClientDossierResponse contract declared in main.py.
    """
    client = get_client(client_id)
    if client is None:
        raise LookupError(f"Unknown client: {client_id}")

    portfolios = get_client_portfolios(client_id)
    holdings = get_client_holdings(client_id)
    facilities = get_client_facilities(client_id)
    _ = (portfolios, holdings, facilities)  # Inputs reserved for implementation.
    raise NotImplementedError
