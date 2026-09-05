from fastapi import FastAPI
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


def fetch_client_profiles() -> list[ClientProfile]:
    """
    Replace this body with your database/API query.

    Example SQL:
      SELECT client_id, client_name, risk_score
      FROM clients
      ORDER BY client_name;
    """
    rows = [
        {"client_id": "CL-0001", "client_name": "Hartono Wijaya Kusuma", "risk_score": 60},
        {"client_id": "CL-0002", "client_name": "Ravi Chandrasekaran", "risk_score": 80},
    ]

    return [
        ClientProfile(
            id=row["client_id"],
            name=row["client_name"],
            risk_score=row["risk_score"],
        )
        for row in rows
    ]


@app.get("/clients", response_model=list[ClientProfile])
def get_clients() -> list[ClientProfile]:
    return fetch_client_profiles()