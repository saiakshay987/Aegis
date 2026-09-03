"""
routers/user_router.py — Customer-facing API endpoints.

5 endpoints matching the ML engineer's contract:
  1. GET  /api/user/{user_id}/assessment
  2. GET  /api/user/{user_id}/projection
  3. GET  /api/user/{user_id}/repayment-plan
  4. GET  /api/user/{user_id}/anomalies
  5. POST /api/user/{user_id}/consent

╔═══════════════════════════════════════════════════════════════╗
║  DB INTEGRATION: Once bank.db is ready, inject the session   ║
║  via FastAPI's Depends() and pass it to each service call.   ║
╚═══════════════════════════════════════════════════════════════╝
"""

from fastapi import APIRouter, HTTPException

# ─── When the DB layer is ready, uncomment: ──────────────────
# from fastapi import Depends
# from database import get_db
# from sqlalchemy.orm import Session
# ──────────────────────────────────────────────────────────────

from schemas import (
    UserAssessmentResponse,
    CashflowProjectionResponse,
    RepaymentPlanResponse,
    UserAnomaliesResponse,
    AnomalyEntry,
    ConsentRequest,
    ConsentResponse,
)
from services.logic_service import (
    get_user_assessment,
    project_cashflow,
    generate_repayment_plan,
    get_user_anomalies,
    record_consent,
)

router = APIRouter(prefix="/api/user", tags=["Customer Portal"])


# ──────────────────────────────────────────────
#  GET  /api/user/{user_id}/assessment
# ──────────────────────────────────────────────

@router.get(
    "/{user_id}/assessment",
    response_model=UserAssessmentResponse,
    summary="Full risk assessment for a user",
)
async def user_assessment(user_id: int):
    """
    Returns the user's balance, living floor, financial oxygen score,
    risk status, income/expense breakdown, and active loan count.
    """
    data = get_user_assessment(user_id)
    return UserAssessmentResponse(**data)


# ──────────────────────────────────────────────
#  GET  /api/user/{user_id}/projection
# ──────────────────────────────────────────────

@router.get(
    "/{user_id}/projection",
    response_model=CashflowProjectionResponse,
    summary="30/60/90-day cashflow projection",
)
async def user_projection(user_id: int):
    """
    Returns the projected balance trajectory at Day 30, Day 60,
    and Day 90, along with the overall risk trend.
    """
    data = project_cashflow(user_id)
    return CashflowProjectionResponse(**data)


# ──────────────────────────────────────────────
#  GET  /api/user/{user_id}/repayment-plan
# ──────────────────────────────────────────────

@router.get(
    "/{user_id}/repayment-plan",
    response_model=RepaymentPlanResponse,
    summary="Adaptive repayment recommendation",
)
async def user_repayment_plan(user_id: int):
    """
    Returns the ML-recommended adaptive repayment plan: safe debit
    amount, deferred amount, deferral duration, and rationale.
    """
    data = generate_repayment_plan(user_id)
    return RepaymentPlanResponse(**data)


# ──────────────────────────────────────────────
#  GET  /api/user/{user_id}/anomalies
# ──────────────────────────────────────────────

@router.get(
    "/{user_id}/anomalies",
    response_model=UserAnomaliesResponse,
    summary="Detected transaction anomalies",
)
async def user_anomalies(user_id: int):
    """
    Returns transaction anomalies flagged by the ML anomaly detector,
    including category, severity, and expected spending range.
    """
    data = get_user_anomalies(user_id)
    anomalies = [AnomalyEntry(**a) for a in data["anomalies"]]
    return UserAnomaliesResponse(
        user_id=data["user_id"],
        anomaly_count=data["anomaly_count"],
        anomalies=anomalies,
    )


# ──────────────────────────────────────────────
#  POST  /api/user/{user_id}/consent
# ──────────────────────────────────────────────

@router.post(
    "/{user_id}/consent",
    response_model=ConsentResponse,
    summary="Record consent for adaptive repayment",
)
async def user_consent(user_id: int, body: ConsentRequest):
    """
    Accepts the customer's consent for an adaptive repayment plan
    and returns a confirmation with timestamp.
    """
    data = record_consent(user_id, body.plan_id)
    return ConsentResponse(**data)
