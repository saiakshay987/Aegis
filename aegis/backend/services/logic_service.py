"""
services/logic_service.py — Mock business logic for Financial Guardian.

╔══════════════════════════════════════════════════════════════════════╗
║  INTEGRATION POINT                                                   ║
║  Every function in this file is a stub.  Replace the mock returns    ║
║  with real queries once the SQLite (bank.db) session and ML model    ║
║  are ready.  The function signatures are the contract — keep them.   ║
╚══════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# ─── DB dependency placeholder ───────────────────────────────────────
# When your teammate's DB layer is ready, import and use the session:
#
#   from database import get_db          # SQLAlchemy SessionLocal
#   from sqlalchemy.orm import Session
#
# Then accept `db: Session` as a parameter in each function below.
# ─────────────────────────────────────────────────────────────────────


def get_living_floor(user_id: int) -> float:
    """
    Return the *living floor* for a user — the minimum monthly balance
    required to cover rent, groceries, utilities, and loan EMIs.

    TODO: Replace with a real query:
        SELECT living_floor FROM user_profiles WHERE user_id = :user_id
    """
    # Mock: return a static floor for demo purposes
    mock_floors = {
        1: 15_000.0,
        2: 22_000.0,
        3: 18_500.0,
    }
    return mock_floors.get(user_id, 20_000.0)


def get_user_balance(user_id: int) -> float:
    """
    Fetch the user's current account balance from bank.db.

    TODO: Replace with:
        SELECT balance FROM accounts WHERE user_id = :user_id
    """
    mock_balances = {
        1: 45_000.0,
        2: 12_000.0,
        3: 8_500.0,
    }
    return mock_balances.get(user_id, 30_000.0)


def calculate_financial_oxygen_score(balance: float, living_floor: float) -> float:
    """
    Financial Oxygen Score (0-100).

    A simple heuristic:
        score = min(100, (balance / living_floor) * 50)

    TODO: Replace with the ML model's prediction once integrated:
        from ML_model.predict import predict_oxygen_score
    """
    if living_floor <= 0:
        return 100.0
    score = min(100.0, (balance / living_floor) * 50.0)
    return round(score, 2)


def classify_risk(score: float) -> str:
    """Map an oxygen score to a traffic-light risk label."""
    if score >= 60:
        return "Healthy"
    elif score >= 35:
        return "Watch"
    return "At-Risk"


def calculate_adaptive_split(
    balance: float,
    living_floor: float,
    emi_amount: float,
) -> Dict[str, Any]:
    """
    Determine an adaptive EMI split that keeps the user above their
    living floor after the payment.

    Returns:
        {
            "affordable_emi": float,
            "deferred_amount": float,
            "months_to_recover": int,
        }

    TODO: Wire up to ML-based affordability model.
    """
    surplus = max(0.0, balance - living_floor)
    affordable_emi = min(emi_amount, surplus * 0.6)  # keep 40% buffer
    deferred = emi_amount - affordable_emi

    months_to_recover = 3 if deferred > 0 else 0

    return {
        "affordable_emi": round(affordable_emi, 2),
        "deferred_amount": round(deferred, 2),
        "months_to_recover": months_to_recover,
    }


def forecast_cashflow(
    user_id: int,
    scenario: str,
    shock_amount: float = 0.0,
) -> Dict[str, float]:
    """
    30/60/90-day cash-flow projection under a given scenario.

    Scenario types:
        - "normal"          → baseline trajectory
        - "medical_shock"   → one-time large expense on Day 1
        - "delayed_income"  → salary delayed by 15 days

    Returns:
        {"day_30": float, "day_60": float, "day_90": float}

    TODO: Replace with the ML model's time-series forecast:
        from ML_model.forecast import run_forecast
    """
    balance = get_user_balance(user_id)

    # Rough monthly income / expense assumptions (mock)
    monthly_income = 50_000.0
    monthly_expense = 35_000.0
    net_monthly = monthly_income - monthly_expense

    if scenario == "medical_shock":
        balance -= shock_amount
    elif scenario == "delayed_income":
        # First month has half income
        balance -= monthly_expense * 0.5

    day_30 = balance + net_monthly
    day_60 = day_30 + net_monthly
    day_90 = day_60 + net_monthly

    return {
        "day_30": round(day_30, 2),
        "day_60": round(day_60, 2),
        "day_90": round(day_90, 2),
    }


# ──────────────────────────────────────────────
#  Admin / Portfolio-level helpers
# ──────────────────────────────────────────────

def get_portfolio_summary() -> Dict[str, Any]:
    """
    Aggregate stats across all users for the bank-manager dashboard.

    TODO: Replace with:
        SELECT risk_status, COUNT(*) FROM user_profiles GROUP BY risk_status
    """
    return {
        "total_customers": 1_250,
        "at_risk_count": 87,
        "watch_count": 214,
        "healthy_count": 949,
        "total_defaults_averted": 34,
        "average_oxygen_score": 62.4,
    }


def get_watchlist() -> List[Dict[str, Any]]:
    """
    Return accounts currently flagged as Watch or At-Risk.

    TODO: Replace with:
        SELECT * FROM user_profiles
        WHERE risk_status IN ('Watch', 'At-Risk')
        ORDER BY financial_oxygen_score ASC
    """
    return [
        {
            "user_id": 2,
            "name": "Priya Sharma",
            "balance": 12_000.0,
            "financial_oxygen_score": 27.3,
            "risk_status": "At-Risk",
            "shock_trigger": "Medical emergency — ₹80,000 hospital bill",
        },
        {
            "user_id": 3,
            "name": "Rahul Verma",
            "balance": 8_500.0,
            "financial_oxygen_score": 23.0,
            "risk_status": "At-Risk",
            "shock_trigger": "Delayed salary — employer cash-flow issues",
        },
        {
            "user_id": 7,
            "name": "Ananya Iyer",
            "balance": 19_200.0,
            "financial_oxygen_score": 42.1,
            "risk_status": "Watch",
            "shock_trigger": None,
        },
    ]


def record_consent_agreement(
    user_id: int,
    loan_id: int,
    proposed_temporary_emi: float,
    deferred_amount: float,
) -> Dict[str, Any]:
    """
    Persist the customer's consent to an adaptive repayment plan.

    TODO: INSERT into consent_agreements table in bank.db.

    Returns confirmation payload for the API response.
    """
    # Mock schedule: redistribute deferred amount over 3 months
    per_month_deferred = round(deferred_amount / 3, 2)
    original_emi = proposed_temporary_emi + deferred_amount

    schedule = [
        {
            "month": i,
            "original_emi": original_emi,
            "adjusted_emi": proposed_temporary_emi if i <= 3 else original_emi,
            "deferred_amount": per_month_deferred if i <= 3 else 0.0,
        }
        for i in range(1, 7)
    ]

    return {
        "status": "approved",
        "message": (
            f"Consent recorded for user {user_id}, loan {loan_id}. "
            f"Temporary EMI ₹{proposed_temporary_emi:,.2f} for 3 months."
        ),
        "updated_loan_schedule": schedule,
    }
