"""LLM-owned copy for the client detail page.

Each generator represents one independently configurable LLM call. The
deterministic client-data service is the only permitted source of model input;
the FastAPI response models validate the returned dictionaries before they are
sent to the frontend.
"""

import json
from typing import Any
import datetime 

from client_data_service import build_client_llm_context

from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv(Path(__file__).with_name(".env"))

openai_client = OpenAI()  


def generate_profile_summary(context: dict[str, Any]) -> dict | None:
    """Call the profile-summary LLM with factual client context only.

    This optional section summarises the client's stated objectives and current
    situation. It must not infer personal facts missing from ``context``.
    """
    client = context["client"]

    #print(f"Profile summary: {context["profile_summary"]}")

    instructions = (
        """
        You are an assistant for a private-banking Relationship Manager.

Write a concise, factual client context summary based only on the supplied JSON.

Requirements:
- Use only information explicitly present in the JSON.
- Summarize the RM notes.
- Highlight any key points for the RM to take note. Flag any contradictions or tensions between stated objectives and current situation or behavior.
- Do not calculate figures or introduce recommendations, market views, products, securities, or events.
- Do not mention missing fields or describe your process.
- Use professional, neutral language suitable for an internal RM briefing.
- Write one short paragraph. 
- Be concise. Keep the response below 75 words.
        """
    )
    output = openai_client.responses.create(
        model="gpt-5.6-terra",
        instructions=instructions,
        input=json.dumps(context["profile_summary"], ensure_ascii=False, separators=(",", ":")),
    )

    print("**---**")
    print(f"Ran LLM for profile summary for {client['client_name']}. Tokens used: {output.usage.total_tokens}")
    print(f"LLM output: {output.output_text}")
    print("**---**")

    return {
        "generatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M SGT"),
        "title": "Client context summary",
        "summary": (
            output.output_text
            if output.output_text
            else "No summary generated. Please check the model response."
        ),
    }


def generate_portfolio_explanation(context: dict[str, Any]) -> dict:
    """Call the portfolio-explanation LLM with sourced, dated facts.

    This is retrospective attribution only: explain portfolio movement and its
    supported causes, without recommending trades.
    """
    _ = context

    class ExplanationPoint(BaseModel):
        title: str
        description: str

    class PortfolioExplanation(BaseModel):
        overview: str
        whatMovedAndWhy: list[ExplanationPoint]
        whatToWatch: list[ExplanationPoint]

    response = openai_client.responses.parse(
        model="gpt-5.6-terra",
        #reasoning={"effort": "medium"},
        instructions="""
    Explain the portfolio in clear, client-friendly language.

    Use only the supplied input. For events in 2026, event_log_2026 is
    authoritative and overrides your prior knowledge. Connect an event to a
    holding only when the event transmission channel and the holding's exposure
    metadata support that link.

    Do not present correlation as certainty. If quantity_changed is true, do not
    attribute the full value change to market performance. Do not recommend trades.

    Return 1–3 titled points for whatMovedAndWhy and 1–3 titled points for
    whatToWatch. Each point must have a short 1-4 word title and a client-friendly
    description. Each section should be no more than 100 words.
    """,
        input=json.dumps(
            context["portfolio_explanation"],
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        text_format=PortfolioExplanation,
    )
    print("**---**")
    print(f"Ran LLM for portfolio explanation for {context['client']['client_name']}. Tokens used: {response.usage.total_tokens}")
    print(f"LLM output: {response.output_text}")
    print("**---**")
    
    output = response.output_parsed
    return {
        "generatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M SGT"),
        "title": "Intelligent Portfolio Explanation",
        "overview": (
            output.overview
            if output.overview
            else "No overview generated. Please check the model response."
        ),
        # ``ExplanationPoint`` is local to this OpenAI parse schema. Convert
        # it to plain dictionaries so FastAPI can validate it as its public
        # ``StrategicPoint`` response model.
        "whatMovedAndWhy": [point.model_dump() for point in output.whatMovedAndWhy],
        "whatToWatch": [point.model_dump() for point in output.whatToWatch],
    }


def generate_proactive_advice(context: dict[str, Any]) -> dict:
    """Call the advisory LLM for RM-reviewed risks and opportunities.

    Advice must be traceable to deterministic inputs and framed as a
    discussion item for Relationship Manager review.
    """
    class AdvicePoint(BaseModel):
        title: str
        description: str

    class ProactiveAdvice(BaseModel):
        risks: list[AdvicePoint]
        opportunities: list[AdvicePoint]

    def records(frame) -> list[dict]:
        """Convert repository data frames to JSON-safe source records."""
        return json.loads(frame.to_json(orient="records", date_format="iso"))

    advisory_context = {
        "client_description": context["profile_summary"]["client_description"],
        "rm_notes": context["profile_summary"]["rm_notes"],
        "portfolio_snapshot": context["dossier"],
        "portfolio_evidence": context["portfolio_explanation"],
        "facilities": records(context["facilities"]),
        "planned_cash_needs": records(context["cash_needs"]),
        "outstanding_commitments": records(context["commitments"]),
        "transactions": records(context["transactions"]),
    }

    response = openai_client.responses.parse(
        model="gpt-5.6-terra",
        instructions="""
You are an assistant for a private-banking Relationship Manager. Identify the
most material client-specific discussion points from the supplied JSON.

Use only supplied facts. RM notes are dated observations, not independently
verified facts. For events occurring in 2026, portfolio_evidence.event_log_2026
is authoritative and overrides your prior knowledge. Do not invent facts,
prices, events, exposures, or client preferences.

Return 1–3 risks and 1–3 opportunities. Each item needs a concise 1–4 word
title and a client-specific description of no more than 55 words. Risks should
describe a supported exposure, constraint, or unresolved issue. Opportunities
must be framed as an RM-reviewed planning discussion, never an instruction or
a promise of outcome. Do not recommend named securities or products.
        """,
        input=json.dumps(advisory_context, ensure_ascii=False, separators=(",", ":")),
        text_format=ProactiveAdvice,
    )

    output = response.output_parsed
    print("**---**")
    print(
        f"Ran LLM for proactive advice for {context['client']['client_name']}. "
        f"Tokens used: {response.usage.total_tokens}"
    )
    print(f"LLM output: {response.output_text}")
    print("**---**")

    return {
        "generatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M SGT"),
        "risks": [point.model_dump() for point in output.risks],
        "opportunities": [point.model_dump() for point in output.opportunities],
    }


def build_client_insights(client_id: str) -> dict:
    """Build context once, then make the three section calls sequentially."""
    context = build_client_llm_context(client_id)

    return {
        "profileSummary": generate_profile_summary(context),
        "portfolioExplanation": generate_portfolio_explanation(context),
        "advisory": generate_proactive_advice(context),
    }



if __name__ == "__main__":
    client_id = "CL-0001"
    insights = build_client_insights(client_id)
    print(json.dumps(insights, indent=2))
