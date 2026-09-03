"""
main.py — FastAPI application entry-point for Financial Guardian.

Starts the server, mounts all routers, configures CORS for the React
frontend, and exposes a health-check endpoint.

Run with:
    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.admin_router import router as admin_router
from routers.user_router import router as user_router

# ─────────────────────────────────────────────────────────────
#  App initialisation
# ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="Financial Guardian API",
    description=(
        "Backend API for the Financial Guardian hackathon project. "
        "Provides financial health monitoring, stress-test simulations, "
        "and adaptive repayment consent flows."
    ),
    version="0.1.0",
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

app.include_router(admin_router)
app.include_router(user_router)


# ─────────────────────────────────────────────────────────────
#  Health-check
# ─────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def health_check():
    """Simple liveness probe — returns 200 when the server is up."""
    return {
        "status": "healthy",
        "service": "Financial Guardian API",
        "version": "0.1.0",
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
