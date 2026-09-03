"""
schemas.py — Pydantic request/response models for Financial Guardian.

These schemas define the API contract. They are decoupled from the database
models so that your teammate's SQLAlchemy/SQLite layer can evolve independently.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
#  Enums
# ──────────────────────────────────────────────

class RiskStatus(str, Enum):
    """Traffic-light risk classification for a user's financial health."""
    HEALTHY = "Healthy"
    WATCH = "Watch"
    AT_RISK = "At-Risk"


class ScenarioType(str, Enum):
    """Types of stress-test scenarios the simulation engine supports."""
    NORMAL = "normal"
    MEDICAL_SHOCK = "medical_shock"
    DELAYED_INCOME = "delayed_income"


# ──────────────────────────────────────────────
#  User Health
# ──────────────────────────────────────────────

class UserHealthResponse(BaseModel):
    """Snapshot of a user's financial vitals — returned by GET /health."""
    user_id: int
    balance: float = Field(..., description="Current account balance (INR)")
    living_floor: float = Field(
        ...,
        description="Minimum balance required to cover essential expenses",
    )
    financial_oxygen_score: float = Field(
        ...,
        ge=0,
        le=100,
        description="0-100 score indicating financial breathing room",
    )
    risk_status: RiskStatus


# ──────────────────────────────────────────────
#  Simulation (Stress-Test)
# ──────────────────────────────────────────────

class SimulationRequest(BaseModel):
    """Input for the what-if simulation engine."""
    user_id: int
    simulated_shock_amount: float = Field(
        ..., ge=0, description="One-time shock amount to inject (INR)"
    )
    scenario_type: ScenarioType = ScenarioType.NORMAL


class SimulationResponse(BaseModel):
    """Projected balance trajectory after applying the shock scenario."""
    user_id: int
    scenario_type: ScenarioType
    projected_balance_day_30: float
    projected_balance_day_60: float
    projected_balance_day_90: float
    risk_status_after_shock: RiskStatus


# ──────────────────────────────────────────────
#  Adaptive Intervention / Consent-Repayment
# ──────────────────────────────────────────────

class LoanScheduleEntry(BaseModel):
    """A single row in the updated repayment schedule."""
    month: int
    original_emi: float
    adjusted_emi: float
    deferred_amount: float


class InterventionRequest(BaseModel):
    """Customer consent payload for an adaptive split-payment plan."""
    user_id: int
    loan_id: int
    proposed_temporary_emi: float = Field(
        ..., description="Reduced EMI the customer can afford right now"
    )
    deferred_amount: float = Field(
        ..., description="Amount to be deferred and redistributed"
    )


class InterventionResponse(BaseModel):
    """Confirmation returned after recording the consent agreement."""
    status: str = Field(..., description="e.g. 'approved', 'pending_review'")
    message: str
    updated_loan_schedule: List[LoanScheduleEntry]


# ──────────────────────────────────────────────
#  Admin / Portfolio-level
# ──────────────────────────────────────────────

class PortfolioSummaryResponse(BaseModel):
    """Aggregate stats for the bank manager dashboard."""
    total_customers: int
    at_risk_count: int
    watch_count: int
    healthy_count: int
    total_defaults_averted: int
    average_oxygen_score: float


class WatchlistAccount(BaseModel):
    """A single at-risk account entry for the watchlist view."""
    user_id: int
    name: str
    balance: float
    financial_oxygen_score: float
    risk_status: RiskStatus
    shock_trigger: Optional[str] = Field(
        None, description="Event that pushed the account into risk zone"
    )


class WatchlistResponse(BaseModel):
    """List wrapper returned by GET /watchlist."""
    count: int
    accounts: List[WatchlistAccount]
