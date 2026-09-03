"""
schemas.py — Pydantic request/response models for Financial Guardian.

Aligned to the ML engineer's contract: 7 endpoints, exact response shapes.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
#  Enums
# ──────────────────────────────────────────────

class RiskStatus(str, Enum):
    HEALTHY = "Healthy"
    WATCH = "Watch"
    AT_RISK = "At-Risk"
    CRITICAL = "Critical"


# ──────────────────────────────────────────────
#  1. GET /api/user/{user_id}/assessment
# ──────────────────────────────────────────────

class UserAssessmentResponse(BaseModel):
    """Full risk metrics returned by get_user_assessment()."""
    user_id: int
    name: str
    balance: float
    living_floor: float = Field(
        ..., description="Minimum balance to cover essential monthly expenses"
    )
    financial_oxygen_score: float = Field(..., ge=0, le=100)
    risk_status: RiskStatus
    monthly_income: float
    monthly_expenses: float
    active_loans: int


# ──────────────────────────────────────────────
#  2. GET /api/user/{user_id}/projection
# ──────────────────────────────────────────────

class CashflowProjectionResponse(BaseModel):
    """30/60/90-day cashflow trajectory returned by project_cashflow()."""
    user_id: int
    current_balance: float
    projected_balance_day_30: float
    projected_balance_day_60: float
    projected_balance_day_90: float
    risk_trend: str = Field(
        ..., description="'improving', 'stable', or 'deteriorating'"
    )


# ──────────────────────────────────────────────
#  3. GET /api/user/{user_id}/repayment-plan
# ──────────────────────────────────────────────

class RepaymentPlanResponse(BaseModel):
    """Adaptive repayment recommendation from generate_repayment_plan()."""
    user_id: int
    plan_id: str
    original_emi: float
    safe_debit_amount: float = Field(
        ..., description="Reduced EMI the user can safely afford now"
    )
    deferred_amount: float = Field(
        ..., description="Amount deferred and redistributed over future months"
    )
    deferral_months: int
    rationale: str


# ──────────────────────────────────────────────
#  4. GET /api/user/{user_id}/anomalies
# ──────────────────────────────────────────────

class AnomalyEntry(BaseModel):
    """A single detected transaction anomaly."""
    transaction_id: str
    date: str
    category: str
    amount: float
    expected_range_min: float
    expected_range_max: float
    severity: str = Field(..., description="'low', 'medium', or 'high'")
    description: str


class UserAnomaliesResponse(BaseModel):
    """Anomalies detected for a user by get_user_anomalies()."""
    user_id: int
    anomaly_count: int
    anomalies: List[AnomalyEntry]


# ──────────────────────────────────────────────
#  5. POST /api/user/{user_id}/consent
# ──────────────────────────────────────────────

class ConsentRequest(BaseModel):
    """Body for the consent endpoint."""
    plan_id: str


class ConsentResponse(BaseModel):
    """Confirmation returned by record_consent()."""
    user_id: int
    plan_id: str
    status: str
    message: str
    consented_at: datetime


# ──────────────────────────────────────────────
#  6. GET /api/portfolio/summary
# ──────────────────────────────────────────────

class PortfolioSummaryResponse(BaseModel):
    """Aggregate stats across all accounts from get_portfolio_summary()."""
    total_users: int
    healthy_count: int
    watch_count: int
    at_risk_count: int
    critical_count: int
    defaults_prevented: int
    average_oxygen_score: float
    total_active_interventions: int


# ──────────────────────────────────────────────
#  7. GET /api/portfolio/at-risk
# ──────────────────────────────────────────────

class AtRiskUser(BaseModel):
    """A single at-risk or critical user entry."""
    user_id: int
    name: str
    balance: float
    financial_oxygen_score: float
    risk_status: RiskStatus
    primary_trigger: Optional[str] = Field(
        None, description="Event that pushed the account into the risk zone"
    )
    days_in_risk_zone: int


class AtRiskUsersResponse(BaseModel):
    """List wrapper returned by get_at_risk_users()."""
    count: int
    users: List[AtRiskUser]
