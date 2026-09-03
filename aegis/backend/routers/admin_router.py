"""
routers/admin_router.py — Bank-manager dashboard endpoints.

Provides portfolio-level analytics and a watchlist of at-risk accounts.

╔═══════════════════════════════════════════════════════════════╗
║  DB INTEGRATION: Once bank.db is ready, inject the session   ║
║  via FastAPI's Depends() and pass it to the service layer.   ║
╚═══════════════════════════════════════════════════════════════╝
"""

from fastapi import APIRouter

# ─── When the DB layer is ready, uncomment: ──────────────────
# from fastapi import Depends
# from database import get_db
# from sqlalchemy.orm import Session
# ──────────────────────────────────────────────────────────────

from schemas import PortfolioSummaryResponse, WatchlistResponse, WatchlistAccount
from services.logic_service import get_portfolio_summary, get_watchlist

router = APIRouter(prefix="/api/admin", tags=["Admin Dashboard"])


@router.get(
    "/portfolio-summary",
    response_model=PortfolioSummaryResponse,
    summary="Portfolio overview for the bank manager",
)
async def portfolio_summary():
    """
    Returns aggregate stats:
    - Total customers
    - Count of at-risk, watch, and healthy accounts
    - Total defaults averted by early intervention
    - Average financial oxygen score across the book

    TODO: Accept `db: Session = Depends(get_db)` and forward to service.
    """
    data = get_portfolio_summary()
    return PortfolioSummaryResponse(**data)


@router.get(
    "/watchlist",
    response_model=WatchlistResponse,
    summary="At-risk and watch-listed accounts",
)
async def watchlist():
    """
    Returns every account currently in the Watch or At-Risk zone,
    along with the shock event that triggered the classification.

    TODO: Accept `db: Session = Depends(get_db)` and forward to service.
    """
    accounts_data = get_watchlist()
    accounts = [WatchlistAccount(**a) for a in accounts_data]
    return WatchlistResponse(count=len(accounts), accounts=accounts)
