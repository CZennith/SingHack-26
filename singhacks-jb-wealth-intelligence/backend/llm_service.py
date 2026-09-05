"""LLM-owned language for the client detail page.

The LLM explains deterministic facts; it never calculates values, determines
prices, or invents events. ``client_data_service.build_client_llm_context`` is
the only approved input boundary for a future model provider.
"""

from typing import Any, Mapping, TypedDict

from client_data_service import build_client_llm_context


class ProfileSummaryOutput(TypedDict):
    """Optional Section 01 addition; it does not replace the factual bio."""

    generatedAt: str
    title: str
    summary: str


class PortfolioExplanationOutput(TypedDict):
    """Section 03: retrospective portfolio attribution, not advice."""

    generatedAt: str
    title: str
    overview: str
    whatMovedAndWhy: str
    whatToWatch: str


class StrategicPointOutput(TypedDict):
    title: str
    description: str


class ProactiveAdviceOutput(TypedDict):
    """Section 04: forward-looking, RM-reviewed risks and opportunities."""

    generatedAt: str
    risks: list[StrategicPointOutput]
    opportunities: list[StrategicPointOutput]


class ClientInsightsOutput(TypedDict):
    profileSummary: ProfileSummaryOutput | None
    portfolioExplanation: PortfolioExplanationOutput
    advisory: ProactiveAdviceOutput


# Every prompt must be built only from these sourced context groups. The model
# may describe relationships between them but may not add unsupported facts.
ALLOWED_CONTEXT = (
    "client",       # factual profile, objectives, risk profile
    "dossier",      # calculated valuation, allocation, trajectory, LTV
    "holdings",     # dated position-level values and exposures
    "portfolios",   # mandate and portfolio metadata
    "facilities",   # drawn amount, LTV, headroom
    "cash_needs",   # planned client cash requirements
    "commitments",  # uncalled commitments and expected windows
    "transactions", # known client activity
    "rm_notes",     # relationship-manager context
)


def generate_profile_summary(client_facts: Mapping[str, Any]) -> ProfileSummaryOutput | None:
    """Generate the optional AI addition to Section 01.

    The model should summarise client context, objectives, and the current
    situation. It must not rewrite the factual ``about.bio`` or infer personal
    facts that are absent from the controlled context.
    """
    client = client_facts["client"]
    return {
        "generatedAt": "2026-08-26 09:30 SGT",
        "title": "Client context summary",
        "summary": f"Placeholder AI summary for {client['client_name']}. Stated objective: {client['objectives']}",
    }


def generate_portfolio_explanation(client_facts: Mapping[str, Any]) -> PortfolioExplanationOutput:
    """Generate Section 03: explain what the portfolio did and why.

    Required model content: portfolio return/change, material holdings or
    exposures that contributed, relevant controlled market/geopolitical events,
    and a concise explanation a client can understand. Do not recommend trades
    in this section.
    """
    _ = client_facts
    return {
        "generatedAt": "2026-08-26 09:30 SGT",
        "title": "Portfolio movement explanation pending",
        "overview": "A future model will connect dated portfolio movements to material holdings and controlled market events.",
        "whatMovedAndWhy": "This section attributes what moved, why it moved, and how the move affected this portfolio.",
        "whatToWatch": "Review the next valuation snapshot and new events affecting material holdings.",
    }


def generate_proactive_advice(client_facts: Mapping[str, Any]) -> ProactiveAdviceOutput:
    """Generate Section 04: forward-looking, RM-reviewed advice.

    Required model content: client-specific concentration, liquidity, currency,
    mandate and collateral risks; event-driven opportunities; and scenario or
    stress-test implications when supplied in the context. Each point must be
    traceable to deterministic inputs and framed as an RM-reviewed suggestion.
    """
    _ = client_facts
    return {
        "generatedAt": "2026-08-26 09:30 SGT",
        "risks": [{"title": "Review required", "description": "Confirm exposures, liquidity needs, and facility headroom with the RM."}],
        "opportunities": [{"title": "Planning discussion", "description": "Prepare an RM-reviewed proposal aligned to stated objectives."}],
    }


def generate_client_advisory(client_facts: Mapping[str, Any]) -> ClientInsightsOutput:
    """Compose the three distinct LLM outputs consumed by the frontend."""
    return {
        "profileSummary": generate_profile_summary(client_facts),
        "portfolioExplanation": generate_portfolio_explanation(client_facts),
        "advisory": generate_proactive_advice(client_facts),
    }


def build_client_insights(client_id: str) -> ClientInsightsOutput:
    """Build sourced context, then return validated LLM-owned display content."""
    return generate_client_advisory(build_client_llm_context(client_id))
