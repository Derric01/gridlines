"""Gridline FastAPI application and static React frontend entrypoint."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.analysis import build_analysis

ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"
FRONTEND_DIST = ROOT / "frontend" / "dist"

app = FastAPI(
    title="Gridline Wind Forecast Review",
    description="A point-in-time January 2026 wind forecast replay using Elexon FUELHH and WINDFOR data.",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


@lru_cache(maxsize=2)
def get_analysis(auction_id: str = "gb_30m") -> dict:
    return build_analysis(DATA_ROOT, auction_id)


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "gridline"}


@app.get("/api/analysis", tags=["analysis"])
def analysis(auction: Literal["gb_60m", "gb_30m"] = Query(default="gb_30m")) -> JSONResponse:
    try:
        return JSONResponse(get_analysis(auction))
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=503, detail=f"Analysis data unavailable: {error}") from error


if FRONTEND_DIST.is_dir():
    # Mount last so /api routes take precedence; Vercel can promote these files to its CDN.
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
