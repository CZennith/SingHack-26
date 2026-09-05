import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Backend is running"}


class ClientProfile(BaseModel):
    id: str
    name: str
    risk_score: int


# These response models intentionally mirror the frontend's ClientDossier
# contract. Keep computed monetary values and display strings consistent with
# the frontend until it is migrated to a raw-number presentation model.
class RelationshipManager(BaseModel):
    name: str
    title: str | None = None


class AllocationItem(BaseModel):
    label: str
    percentage: float
    color: str


class TrajectoryPoint(BaseModel):
    date: str
    value: float
    label: str | None = None


class PortfolioHolding(BaseModel):
    id: str
    name: str
    ticker: str
    sector: str
    value: str
    percentage: float


class PortfolioTrajectory(BaseModel):
    deltaPercent: str
    deltaPeriod: str
    startLabel: str
    troughLabel: str
    endLabel: str
    points: list[TrajectoryPoint]


class ClientPortfolio(BaseModel):
    totalValue: str
    totalValueSubtext: str
    cashLiquidity: str
    cashLiquidityPercent: str
    cashLiquiditySubtext: str
    borrowingUtilisation: str
    borrowingLtvPercent: float
    borrowingStatus: str
    allocation: list[AllocationItem]
    trajectory: PortfolioTrajectory
    topHoldings: list[PortfolioHolding]
    remainingHoldingsNote: str


class ClientAbout(BaseModel):
    bio: str
    age: int
    occupation: str
    clientSince: int


class StrategicPoint(BaseModel):
    title: str
    description: str


class AiProfileSummary(BaseModel):
    generatedAt: str
    title: str
    summary: str


class PortfolioExplanation(BaseModel):
    generatedAt: str
    title: str
    overview: str
    whatMovedAndWhy: list[StrategicPoint]
    whatToWatch: list[StrategicPoint]


class StrategicMatrix(BaseModel):
    generatedAt: str
    risks: list[StrategicPoint]
    opportunities: list[StrategicPoint]


class ClientDossierResponse(BaseModel):
    id: str
    ref: str
    name: str
    initials: str
    tier: str
    mandate: str
    aum: str
    riskLevel: str
    headlineIssue: str
    summary: str
    tags: list[str]
    suggestedNextStep: str
    asOf: str | None = None
    valuationAsOf: str | None = None
    relationshipManager: RelationshipManager | None = None
    about: ClientAbout
    portfolio: ClientPortfolio
    # Generated fields are supplied by the separate advisory request.
    profileSummary: AiProfileSummary | None = None
    portfolioExplanation: PortfolioExplanation | None = None
    advisory: StrategicMatrix | None = None


class ClientInsightsResponse(BaseModel):
    profileSummary: AiProfileSummary | None = None
    portfolioExplanation: PortfolioExplanation
    advisory: StrategicMatrix


if __package__:
    # Package mode: ``uvicorn backend.main:app`` from the project root.
    from .data_repository import get_clients as get_csv_clients
else:
    # Module mode: ``uvicorn main:app`` from inside ``backend``.
    from data_repository import get_clients as get_csv_clients

def fetch_client_profiles() -> list[ClientProfile]:
    clients = get_csv_clients()
    return [
        ClientProfile(
            id=row.client_id,
            name=row.client_name,
            risk_score=int(row.risk_tolerance_score * 10),
        )
        for row in clients.itertuples()
    ]


@app.get("/clients", response_model=list[ClientProfile])
def get_clients() -> list[ClientProfile]:
    return fetch_client_profiles()


def fetch_client_dossier(client_id: str) -> ClientDossierResponse:
    """Return deterministic client facts from clients, portfolios and facilities.

    TODO: resolve ``client_id`` from clients.csv, calculate the portfolio values
    and allocation, retrieve the historical trajectory, and return a populated
    ClientDossierResponse. Raise a 404 when the client does not exist.
    """
    if __package__:
        from .client_data_service import build_client_dossier
    else:
        from client_data_service import build_client_dossier

    return ClientDossierResponse.model_validate(build_client_dossier(client_id))


def fetch_client_insights(client_id: str) -> ClientInsightsResponse:
    """Return LLM-generated advisory content grounded in deterministic facts.

    The generated payload may include a client profile summary as well as
    insights. Raise a 404 when the client does not exist.
    """
    if __package__:
        from .llm_service import build_client_insights
    else:
        from llm_service import build_client_insights

    return ClientInsightsResponse.model_validate(build_client_insights(client_id))


@app.get("/clients/{client_id}/dossier", response_model=ClientDossierResponse)
def get_client_dossier(client_id: str) -> ClientDossierResponse:
    """Dossier route consumed when the user opens a client detail page."""
    try:
        return fetch_client_dossier(client_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except NotImplementedError as error:
        raise HTTPException(
            status_code=501,
            detail="Client dossier aggregation has not been implemented yet.",
        ) from error


@app.get("/clients/{client_id}/insights", response_model=ClientInsightsResponse)
def get_client_insights(client_id: str) -> ClientInsightsResponse:
    """Insight route consumed in parallel with the dossier request."""
    try:
        return fetch_client_insights(client_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except NotImplementedError as error:
        raise HTTPException(
            status_code=501,
            detail="Client insight generation has not been implemented yet.",
        ) from error


@app.get("/clients/{client_id}/insights/stream")
def stream_client_insights(client_id: str) -> StreamingResponse:
    """Send each AI insight section to the browser as it completes."""
    if __package__:
        from .llm_service import stream_client_insight_sections
    else:
        from llm_service import stream_client_insight_sections

    def events():
        try:
            yield "event: started\ndata: {}\n\n"
            for section, payload in stream_client_insight_sections(client_id):
                if section == "heartbeat":
                    yield ": keep-alive\n\n"
                    continue
                message = json.dumps({"section": section, "payload": payload})
                yield f"event: insight\ndata: {message}\n\n"
            yield "event: complete\ndata: {}\n\n"
        except LookupError as error:
            yield f"event: error\ndata: {json.dumps({'message': str(error)})}\n\n"
        except Exception:
            # Do not expose model/provider internals to the browser. Server
            # logging retains the original exception through FastAPI/Uvicorn.
            yield "event: error\ndata: {\"message\": \"Unable to generate AI insights.\"}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
