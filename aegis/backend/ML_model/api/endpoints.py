"""
Project Aegis — FastAPI Endpoint Functions
==========================================
Ready-to-import endpoint functions for the FastAPI server.
Your FastAPI teammate simply imports these and wires them to routes.

Usage in FastAPI app:
    from ML_model.api.endpoints import router
    app.include_router(router, prefix="/api")
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import sys
import os

# Add parent dir to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ML_MODEL_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, ML_MODEL_DIR)

from api.pipeline import (
    get_user_assessment,
    get_user_projection,
    get_user_repayment_plan,
    get_user_anomalies,
    get_user_survival_buffer,
    get_portfolio_summary,
    get_at_risk_users,
    record_consent,
)

# ─── Router ───────────────────────────────────────────────────────────────────

router = APIRouter(tags=["aegis"])


# ─── Pydantic Models (Response Schemas) ───────────────────────────────────────

class ConsentRequest(BaseModel):
    plan_id: str


class HealthResponse(BaseModel):
    status: str
    version: str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0", "service": "Project Aegis"}


@router.get("/user/{user_id}/assessment")
async def api_user_assessment(user_id: str):
    """
    Full risk assessment for a single user.
    Returns risk score, projections, survival buffer, repayment plan, and anomalies.
    """
    try:
        result = get_user_assessment(user_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/projection")
async def api_user_projection(user_id: str):
    """
    30/60/90 day cashflow projection for a user.
    Includes daily trajectory and estimated default day.
    """
    try:
        result = get_user_projection(user_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/repayment-plan")
async def api_user_repayment_plan(user_id: str):
    """
    Adaptive repayment plan recommendation.
    Includes eligibility check, plan options, and per-loan details.
    """
    try:
        result = get_user_repayment_plan(user_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/anomalies")
async def api_user_anomalies(user_id: str):
    """
    Recent transaction anomalies detected for a user.
    Sorted by anomaly score (highest first).
    """
    try:
        result = get_user_anomalies(user_id)
        return {"user_id": user_id, "anomalies": result, "count": len(result)}
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/survival-buffer")
async def api_user_survival_buffer(user_id: str):
    """
    Survival buffer calculation showing essential expense breakdown
    and ring-fence recommendation.
    """
    try:
        result = get_user_survival_buffer(user_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolio/summary")
async def api_portfolio_summary():
    """
    Aggregate risk stats across all users.
    Used by the Bank Ops Command Center.
    """
    try:
        result = get_portfolio_summary()
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolio/at-risk")
async def api_at_risk_users():
    """
    List all at-risk and critical users with summary info.
    Sorted by risk score (highest first).
    """
    try:
        result = get_at_risk_users()
        return {"users": result, "count": len(result)}
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/{user_id}/consent")
async def api_record_consent(user_id: str, body: ConsentRequest):
    """
    Record user's consent to an adaptive repayment plan.
    This is the compliance-critical endpoint — nothing changes without consent.
    """
    try:
        result = record_consent(user_id, body.plan_id)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
