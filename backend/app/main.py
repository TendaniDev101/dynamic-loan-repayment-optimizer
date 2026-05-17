from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .calculator import PRICING_TIERS, optimize_loan
from .models import LoanRequest, OptimizationResponse

app = FastAPI(title="Loan Optimization Engine API")
REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST_DIR = REPO_ROOT / "frontend" / "dist"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config")
def get_config() -> dict[str, object]:
    return {
        "term_options": [12, 24, 36, 48, 60],
        "pricing_tiers": [
            {
                "tier": tier.tier,
                "score_min": tier.score_min,
                "score_max": tier.score_max,
                "risk_category": tier.risk_category,
                "risk_premium": tier.risk_premium,
            }
            for tier in PRICING_TIERS
        ],
    }


@app.post("/api/optimize", response_model=OptimizationResponse)
def optimize(request: LoanRequest) -> OptimizationResponse:
    return optimize_loan(request)


if FRONTEND_DIST_DIR.exists():
    assets_dir = FRONTEND_DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str) -> FileResponse:
        candidate = FRONTEND_DIST_DIR / full_path
        if full_path and candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST_DIR / "index.html")
