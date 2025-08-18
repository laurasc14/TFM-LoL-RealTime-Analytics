# src/api/backfill_api.py
from fastapi import FastAPI, APIRouter
from pydantic import BaseModel

app = FastAPI(
    title="Backfill API",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",  # también activamos Redoc
)

router = APIRouter()

@router.get("/health", summary="Health")
def health():
    return {"status": "ok"}

class BackfillIn(BaseModel):
    summoner: str
    region: str = "europe"
    count: int = 20

@router.post("/backfill", summary="Backfill")
def backfill(payload: BackfillIn):
    # TODO: tu lógica real de backfill, ahora devuelve algo visible
    return {"ok": True, "received": payload.model_dump()}

# MUY IMPORTANTE: registrar el router
app.include_router(router)
