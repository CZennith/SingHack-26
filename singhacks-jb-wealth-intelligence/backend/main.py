from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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


class SynthesisedAnalysis(BaseModel):
    syncTime: str
    headline: str
    narrative: str
    whyItMatters: str
    monitor: str


class StrategicMatrix(BaseModel):
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
    # The dossier endpoint may omit generated text; insights are requested separately.
    synthesisedAnalysis: SynthesisedAnalysis | None = None
    strategicMatrix: StrategicMatrix | None = None


class ClientInsightsResponse(BaseModel):
    synthesisedAnalysis: SynthesisedAnalysis
    strategicMatrix: StrategicMatrix


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
    """Build one client dossier from clients, portfolios, holdings and facilities.

    TODO: resolve ``client_id`` from clients.csv, calculate the portfolio values
    and allocation, retrieve the historical trajectory, and return a populated
    ClientDossierResponse. Raise a 404 when the client does not exist.
    """
    from dossier_service import build_client_dossier

    return ClientDossierResponse.model_validate(build_client_dossier(client_id))


def fetch_client_insights(client_id: str) -> ClientInsightsResponse:
    """Return the cached/rules-and-LLM-generated advisory insights for a client.

    TODO: construct a source-grounded input from the computed dossier, RM notes,
    mandate checks, events, cash needs and commitments; then retrieve or create
    validated structured insight output. Raise a 404 when the client does not exist.
    """
    from insights_service import build_client_insights

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
