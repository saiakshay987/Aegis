"""
main.py — FastAPI application entry-point for Financial Guardian.

Mounts all routers, configures CORS (allow all origins for React dev),
and provides a health-check endpoint.

Run with:
    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.user_router import router as user_router
from routers.portfolio_router import router as portfolio_router

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
    version="0.2.0",
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
        "version": "0.2.0",
    }


# ─────────────────────────────────────────────────────────────
#  DB startup hook (placeholder)
# ─────────────────────────────────────────────────────────────
#
#  When your teammate's database module is ready, add:
#
#  from database import engine, Base
#
#  @app.on_event("startup")
#  async def on_startup():
#      Base.metadata.create_all(bind=engine)
#
# ─────────────────────────────────────────────────────────────
