from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

from .prioritization import DEFAULT_AS_OF, calculate_prioritization


app = FastAPI(title="RM Intelligence Workbench API")
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/prioritization")
def prioritization(
    as_of: date | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    effective_as_of = as_of if isinstance(as_of, date) else DEFAULT_AS_OF
    effective_limit = limit if isinstance(limit, int) else 20
    try:
        result = calculate_prioritization(DATA_DIR, effective_as_of)
    except (FileNotFoundError, KeyError, ValueError) as error:
        raise HTTPException(status_code=500, detail=f"Unable to calculate prioritization: {error}") from error

    result["clients"] = result["clients"][:effective_limit]
    return result