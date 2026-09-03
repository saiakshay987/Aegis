"""
routers/user_router.py — Customer-facing API endpoints.

Covers financial health checks, what-if simulations, and consent
for adaptive repayment plans.

╔═══════════════════════════════════════════════════════════════╗
║  DB INTEGRATION: Once bank.db is ready, inject the session   ║
║  via FastAPI's Depends() and pass it to the service layer.   ║
╚═══════════════════════════════════════════════════════════════╝
"""

from fastapi import APIRouter, HTTPException

# ─── When the DB layer is ready, uncomment: ──────────────────
# from fastapi import Depends
# from database import get_db
# from sqlalchemy.orm import Session
# ──────────────────────────────────────────────────────────────

from schemas import (
    UserHealthResponse,
    SimulationRequest,
    SimulationResponse,
    InterventionRequest,
    InterventionResponse,
    LoanScheduleEntry,
)
from services.logic_service import (
    get_living_floor,
    get_user_balance,
    calculate_financial_oxygen_score,
    classify_risk,
    forecast_cashflow,
    record_consent_agreement,
)

router = APIRouter(prefix="/api/user", tags=["Customer Portal"])


# ──────────────────────────────────────────────
#  GET  /api/user/{user_id}/health
# ──────────────────────────────────────────────

@router.get(
    "/{user_id}/health",
    response_model=UserHealthResponse,
    summary="Financial health snapshot",
)
async def user_health(user_id: int):
    """
    Returns the user's current balance, living floor, financial oxygen
    score, and risk classification.

    TODO: Accept `db: Session = Depends(get_db)` and forward to service.
    """
    balance = get_user_balance(user_id)
    living_floor = get_living_floor(user_id)
    score = calculate_financial_oxygen_score(balance, living_floor)
    risk = classify_risk(score)

    return UserHealthResponse(
        user_id=user_id,
        balance=balance,
        living_floor=living_floor,
        financial_oxygen_score=score,
        risk_status=risk,
    )


# ──────────────────────────────────────────────
#  POST  /api/user/{user_id}/simulate
# ──────────────────────────────────────────────

@router.post(
    "/{user_id}/simulate",
    response_model=SimulationResponse,
    summary="What-if stress-test simulation",
)
async def simulate(user_id: int, body: SimulationRequest):
    """
    Accepts a shock amount and scenario type, then returns projected
    balances at Day 30, Day 60, and Day 90.

    TODO: Accept `db: Session = Depends(get_db)` and wire to ML forecast.
    """
    if body.user_id != user_id:
        raise HTTPException(
            status_code=400,
            detail="user_id in path and body must match.",
        )

    projections = forecast_cashflow(
        user_id=user_id,
        scenario=body.scenario_type.value,
        shock_amount=body.simulated_shock_amount,
    )

    # Classify risk based on worst-case (Day 30) projected balance
    living_floor = get_living_floor(user_id)
    worst_score = calculate_financial_oxygen_score(
        projections["day_30"], living_floor
    )
    risk_after = classify_risk(worst_score)

    return SimulationResponse(
        user_id=user_id,
        scenario_type=body.scenario_type,
        projected_balance_day_30=projections["day_30"],
        projected_balance_day_60=projections["day_60"],
        projected_balance_day_90=projections["day_90"],
        risk_status_after_shock=risk_after,
    )


# ──────────────────────────────────────────────
#  POST  /api/user/{user_id}/consent-repayment
# ──────────────────────────────────────────────

@router.post(
    "/{user_id}/consent-repayment",
    response_model=InterventionResponse,
    summary="Record adaptive repayment consent",
)
async def consent_repayment(user_id: int, body: InterventionRequest):
    """
    The customer agrees to an adaptive split-payment plan.  This endpoint
    records the agreement and returns the updated loan schedule.

    TODO: Accept `db: Session = Depends(get_db)` and persist to bank.db.
    """
    if body.user_id != user_id:
        raise HTTPException(
            status_code=400,
            detail="user_id in path and body must match.",
        )

    result = record_consent_agreement(
        user_id=body.user_id,
        loan_id=body.loan_id,
        proposed_temporary_emi=body.proposed_temporary_emi,
        deferred_amount=body.deferred_amount,
    )

    schedule = [LoanScheduleEntry(**entry) for entry in result["updated_loan_schedule"]]

    return InterventionResponse(
        status=result["status"],
        message=result["message"],
        updated_loan_schedule=schedule,
    )
