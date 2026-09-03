"""
main.py — FastAPI application entry-point for Financial Guardian.

Mounts all routers, configures CORS (allow all origins for React dev),
and provides a health-check endpoint.

Run with:
    uvicorn main:app --reload --port 8000
"""

import sys
import os

# ─────────────────────────────────────────────────────────────
#  Path configuration — allow imports from:
#    1. Root project dir (database.py, models.py, rules_engine.py)
#    2. ML_model dir (api.pipeline, simulation.*, features.*)
# ─────────────────────────────────────────────────────────────

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BACKEND_DIR))  # d:\Projects\Aegis
ML_MODEL_DIR = os.path.join(BACKEND_DIR, "ML_model")

for p in [PROJECT_ROOT, ML_MODEL_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import engine, Base
from routers.user_router import router as user_router
from routers.portfolio_router import router as portfolio_router


# ─────────────────────────────────────────────────────────────
#  Lifespan — initialise DB tables on startup
# ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all ORM tables if they don't already exist."""
    Base.metadata.create_all(bind=engine)
    yield


# ─────────────────────────────────────────────────────────────
#  App initialisation
# ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="Financial Guardian API",
    description=(
        "Backend API for the Financial Guardian hackathon project. "
        "Provides financial health assessments, cashflow projections, "
        "anomaly detection, adaptive repayment plans, and portfolio analytics."
    ),
    version="0.3.0",
    lifespan=lifespan,
)


# ─────────────────────────────────────────────────────────────
#  CORS — allow the React frontend (any origin during dev)
# ─────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # TODO: lock down to your frontend URL in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────
#  Register routers
# ─────────────────────────────────────────────────────────────

app.include_router(user_router)
app.include_router(portfolio_router)


# ─────────────────────────────────────────────────────────────
#  Health-check
# ─────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def health_check():
    """Simple liveness probe — returns 200 when the server is up."""
    return {
        "status": "healthy",
        "service": "Financial Guardian API",
        "version": "0.3.0",
    }
