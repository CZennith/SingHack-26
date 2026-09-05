"""Generate validated advisory language from deterministic client facts.

The functions in this module are intentionally skeletons. A future provider
implementation must receive only the sourced context from ``client_data_service``
and return validated structured output; it must never calculate or invent
financial values.
"""

from typing import Any, Mapping

from client_data_service import build_client_llm_context


def generate_client_profile_summary(client_facts: Mapping[str, Any]) -> dict:
    """Generate the client-facing profile summary from deterministic facts.

    TODO: return validated summary/bio content with evidence and uncertainty
    markers. This function must not alter numeric values from ``client_facts``.
    """
    client = client_facts["client"]
    return {
        "summary": f"Placeholder AI profile for {client['client_name']}. Stated objective: {client['objectives']}",
        "disclaimer": "Placeholder generated content; relationship-manager review required.",
    }


def generate_client_advisory(client_facts: Mapping[str, Any]) -> dict:
    """Generate the full advisory payload, including insights and next steps.

    TODO: return ``synthesisedAnalysis`` and ``strategicMatrix``, plus future
    generated fields such as headline issue, tags and suggested next step.
    Suggestions remain subject to relationship-manager review.
    """
    profile = generate_client_profile_summary(client_facts)
    return {
        "synthesisedAnalysis": {
            "syncTime": "Placeholder advisory output",
            "headline": "Advisory review ready",
            "narrative": profile["summary"],
            "whyItMatters": "This temporary copy is based on deterministic client context.",
            "monitor": "Validate cash needs, mandate suitability, and facility headroom before action.",
        },
        "strategicMatrix": {
            "risks": [{"title": "Review required", "description": "Confirm portfolio exposures and planned commitments with the RM."}],
            "opportunities": [{"title": "Planning discussion", "description": "Prepare an RM-reviewed proposal aligned to stated objectives."}],
        },
    }


def build_client_insights(client_id: str) -> dict:
    """Return generated advisory content for ``GET /clients/{id}/insights``."""
    client_facts = build_client_llm_context(client_id)
    return generate_client_advisory(client_facts)
