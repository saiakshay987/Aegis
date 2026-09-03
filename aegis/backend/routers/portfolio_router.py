"""
routers/portfolio_router.py — Bank-manager portfolio endpoints.

2 endpoints matching the ML engineer's contract:
  1. GET /api/portfolio/summary
  2. GET /api/portfolio/at-risk
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas import (
    PortfolioSummaryResponse,
    AtRiskUsersResponse,
    AtRiskUser,
)
from services.logic_service import (
    get_portfolio_summary,
    get_at_risk_users,
)

router = APIRouter(prefix="/api/portfolio", tags=["Portfolio Dashboard"])


# ──────────────────────────────────────────────
#  GET  /api/portfolio/summary
# ──────────────────────────────────────────────

@router.get(
    "/summary",
    response_model=PortfolioSummaryResponse,
    summary="Aggregate portfolio statistics",
)
async def portfolio_summary(db: Session = Depends(get_db)):
    """
    Returns aggregate stats across all accounts: total users,
    risk-tier counts, defaults prevented, average oxygen score,
    and total active interventions.
    """
    data = get_portfolio_summary(db)
    return PortfolioSummaryResponse(**data)


# ──────────────────────────────────────────────
#  GET  /api/portfolio/at-risk
# ──────────────────────────────────────────────

@router.get(
    "/at-risk",
    response_model=AtRiskUsersResponse,
    summary="At-risk and critical user list",
)
async def at_risk_users(db: Session = Depends(get_db)):
    """
    Returns all users currently flagged as At-Risk or Critical,
    along with their primary trigger event and days in risk zone.
    """
    users_data = get_at_risk_users(db)
    users = [AtRiskUser(**u) for u in users_data]
    return AtRiskUsersResponse(count=len(users), users=users)
