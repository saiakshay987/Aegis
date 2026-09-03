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
#  Path configuration
#
#  We only add BACKEND_DIR and ML_MODEL_DIR here.
#
#  • BACKEND_DIR   → database.py, schemas.py, empathy_engine.py,
#                    routers/, services/
#  • ML_MODEL_DIR  → api.pipeline, simulation.*, features.*
#
#  PROJECT_ROOT (d:\Aegis\Aegis) is intentionally NOT added here.
#  Adding it would put the root-level database.py on sys.path and
#  shadow the backend-local database.py that correctly resolves the
#  ML database path.  Services that need models.py / rules_engine.py
#  from the root add PROJECT_ROOT in their own module (logic_service.py
#  already does this).
# ─────────────────────────────────────────────────────────────

BACKEND_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BACKEND_DIR))   # d:\Aegis\Aegis
ML_MODEL_DIR = os.path.join(BACKEND_DIR, "ML_model")

for p in [ML_MODEL_DIR, BACKEND_DIR]:   # BACKEND_DIR inserted last → highest priority
    if p not in sys.path:
        sys.path.insert(0, p)

# ─────────────────────────────────────────────────────────────
#  Imports — paths are set, safe to import now
# ─────────────────────────────────────────────────────────────

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Resolves to aegis/backend/database.py → ML_model/data/aegis.db
from database import engine

# ORM-backed routers (SQLAlchemy session injected via Depends(get_db))
from routers.user_router      import router as user_router
from routers.portfolio_router import router as portfolio_router

# ML pipeline router — pure pipeline functions, no SQLAlchemy dependency.
# Mounted under /api so its paths become /api/health,
# /api/user/{id}/assessment, etc.
from ML_model.api.endpoints import router as ml_router


# ─────────────────────────────────────────────────────────────
#  Lifespan
#
#  We do NOT call Base.metadata.create_all() here.
#  aegis.db is already fully populated by the ML data-generation
#  pipeline (users, loans, transactions, features, risk_scores,
#  anomalies, consents tables).  Running create_all would try to
#  add the ORM schema (customers, interventions …) on top of that,
#  corrupting the existing ML table layout.
#
#  To rebuild from scratch: run seed_data.py or data_generation.py
#  from the project root.
# ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Verify the DB is reachable on startup; nothing to tear down."""
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))   # smoke-test the connection
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
#
#  Route ownership:
#    /api/user/…       — ORM-backed customer portal   (user_router)
#    /api/portfolio/…  — ORM-backed bank dashboard    (portfolio_router)
#    /api/…            — ML pipeline direct routes    (ml_router)
#
#  The ORM routers are registered first so they win on any shared
#  paths (FastAPI resolves the first matching route).
# ─────────────────────────────────────────────────────────────

app.include_router(user_router)                  # prefix: /api/user
app.include_router(portfolio_router)             # prefix: /api/portfolio
app.include_router(ml_router, prefix="/api")     # ML pipeline under /api


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
