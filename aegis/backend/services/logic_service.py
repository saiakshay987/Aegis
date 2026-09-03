"""
services/logic_service.py — Mock business logic for Financial Guardian.

╔══════════════════════════════════════════════════════════════════════╗
║  CONTRACT: 7 functions matching the ML engineer's API spec.         ║
║  Each function returns realistic mock data for frontend testing.    ║
║  Replace internals with real DB queries / ML calls when ready.      ║
║                                                                      ║
║  Integration:  Accept `db: Session` as first param when wiring up   ║
║                SQLite (bank.db) via FastAPI Depends().               ║
╚══════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


# ═══════════════════════════════════════════════
#  1.  get_user_assessment(user_id)
# ═══════════════════════════════════════════════

def get_user_assessment(user_id: int) -> Dict[str, Any]:
    """
    Full risk metrics for a single user.

    TODO: Replace with real queries against bank.db:
        SELECT * FROM user_profiles WHERE user_id = ?
        + ML oxygen score from model inference
    """
    mock_users = {
        1: {
            "user_id": 1,
            "name": "Aarav Mehta",
            "balance": 45_000.0,
            "living_floor": 15_000.0,
            "financial_oxygen_score": 82.5,
            "risk_status": "Healthy",
            "monthly_income": 60_000.0,
            "monthly_expenses": 38_000.0,
            "active_loans": 1,
        },
        2: {
            "user_id": 2,
            "name": "Priya Sharma",
            "balance": 12_000.0,
            "living_floor": 22_000.0,
            "financial_oxygen_score": 27.3,
            "risk_status": "At-Risk",
            "monthly_income": 45_000.0,
            "monthly_expenses": 41_000.0,
            "active_loans": 2,
        },
        3: {
            "user_id": 3,
            "name": "Rahul Verma",
            "balance": 8_500.0,
            "living_floor": 18_500.0,
            "financial_oxygen_score": 18.9,
            "risk_status": "Critical",
            "monthly_income": 35_000.0,
            "monthly_expenses": 33_000.0,
            "active_loans": 3,
        },
    }
    return mock_users.get(user_id, {
        "user_id": user_id,
        "name": f"User {user_id}",
        "balance": 30_000.0,
        "living_floor": 20_000.0,
        "financial_oxygen_score": 55.0,
        "risk_status": "Watch",
        "monthly_income": 50_000.0,
        "monthly_expenses": 36_000.0,
        "active_loans": 1,
    })


# ═══════════════════════════════════════════════
#  2.  project_cashflow(user_id)
# ═══════════════════════════════════════════════

def project_cashflow(user_id: int) -> Dict[str, Any]:
    """
    30/60/90-day cashflow balance trajectory.

    TODO: Replace with ML time-series forecast:
        from ML_model.forecast import run_forecast
    """
    assessment = get_user_assessment(user_id)
    balance = assessment["balance"]
    net_monthly = assessment["monthly_income"] - assessment["monthly_expenses"]

    day_30 = round(balance + net_monthly, 2)
    day_60 = round(day_30 + net_monthly, 2)
    day_90 = round(day_60 + net_monthly, 2)

    if day_90 > balance:
        trend = "improving"
    elif day_90 < balance:
        trend = "deteriorating"
    else:
        trend = "stable"

    return {
        "user_id": user_id,
        "current_balance": balance,
        "projected_balance_day_30": day_30,
        "projected_balance_day_60": day_60,
        "projected_balance_day_90": day_90,
        "risk_trend": trend,
    }


# ═══════════════════════════════════════════════
#  3.  generate_repayment_plan(user_id)
# ═══════════════════════════════════════════════

def generate_repayment_plan(user_id: int) -> Dict[str, Any]:
    """
    Adaptive repayment recommendation.

    TODO: Replace with ML affordability model + DB loan data:
        SELECT emi_amount FROM loans WHERE user_id = ? AND status = 'active'
    """
    assessment = get_user_assessment(user_id)
    balance = assessment["balance"]
    living_floor = assessment["living_floor"]

    original_emi = 12_000.0  # mock EMI
    surplus = max(0.0, balance - living_floor)
    safe_debit = round(min(original_emi, surplus * 0.6), 2)
    deferred = round(original_emi - safe_debit, 2)

    return {
        "user_id": user_id,
        "plan_id": f"PLAN-{user_id}-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        "original_emi": original_emi,
        "safe_debit_amount": safe_debit,
        "deferred_amount": deferred,
        "deferral_months": 3 if deferred > 0 else 0,
        "rationale": (
            f"Balance ({balance:,.0f}) minus living floor ({living_floor:,.0f}) "
            f"leaves a surplus of {surplus:,.0f}. Safe debit set at 60% of surplus."
        ),
    }


# ═══════════════════════════════════════════════
#  4.  get_user_anomalies(user_id)
# ═══════════════════════════════════════════════

def get_user_anomalies(user_id: int) -> Dict[str, Any]:
    """
    Detected transaction anomalies for a user.

    TODO: Replace with ML anomaly detection output:
        from ML_model.anomaly import detect_anomalies
    """
    mock_anomalies: Dict[int, List[Dict[str, Any]]] = {
        2: [
            {
                "transaction_id": "TXN-20260815-7821",
                "date": "2026-08-15",
                "category": "Medical",
                "amount": 80_000.0,
                "expected_range_min": 500.0,
                "expected_range_max": 5_000.0,
                "severity": "high",
                "description": "Hospital admission — emergency surgery bill",
            },
            {
                "transaction_id": "TXN-20260820-3345",
                "date": "2026-08-20",
                "category": "Pharmacy",
                "amount": 12_500.0,
                "expected_range_min": 200.0,
                "expected_range_max": 2_000.0,
                "severity": "medium",
                "description": "Post-operative medication bulk purchase",
            },
        ],
        3: [
            {
                "transaction_id": "TXN-20260801-1190",
                "date": "2026-08-01",
                "category": "Cash Withdrawal",
                "amount": 25_000.0,
                "expected_range_min": 2_000.0,
                "expected_range_max": 10_000.0,
                "severity": "high",
                "description": "Unusually large ATM withdrawal — possible distress",
            },
        ],
    }

    anomalies = mock_anomalies.get(user_id, [])
    return {
        "user_id": user_id,
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
    }


# ═══════════════════════════════════════════════
#  5.  record_consent(user_id, plan_id)
# ═══════════════════════════════════════════════

def record_consent(user_id: int, plan_id: str) -> Dict[str, Any]:
    """
    Persist the customer's consent for an adaptive repayment plan.

    TODO: INSERT into consent_agreements table in bank.db:
        INSERT INTO consent_agreements (user_id, plan_id, consented_at)
        VALUES (?, ?, datetime('now'))
    """
    now = datetime.now(timezone.utc)
    return {
        "user_id": user_id,
        "plan_id": plan_id,
        "status": "confirmed",
        "message": (
            f"Consent recorded successfully for plan {plan_id}. "
            f"Adaptive repayment schedule is now active."
        ),
        "consented_at": now.isoformat(),
    }


# ═══════════════════════════════════════════════
#  6.  get_portfolio_summary()
# ═══════════════════════════════════════════════

def get_portfolio_summary() -> Dict[str, Any]:
    """
    Aggregate stats across all accounts for the bank-manager dashboard.

    TODO: Replace with:
        SELECT risk_status, COUNT(*) FROM user_profiles GROUP BY risk_status
    """
    return {
        "total_users": 1_250,
        "healthy_count": 893,
        "watch_count": 214,
        "at_risk_count": 108,
        "critical_count": 35,
        "defaults_prevented": 47,
        "average_oxygen_score": 62.4,
        "total_active_interventions": 72,
    }


# ═══════════════════════════════════════════════
#  7.  get_at_risk_users()
# ═══════════════════════════════════════════════

def get_at_risk_users() -> List[Dict[str, Any]]:
    """
    All users flagged as At-Risk or Critical with their primary trigger.

    TODO: Replace with:
        SELECT * FROM user_profiles
        WHERE risk_status IN ('At-Risk', 'Critical')
        ORDER BY financial_oxygen_score ASC
    """
    return [
        {
            "user_id": 3,
            "name": "Rahul Verma",
            "balance": 8_500.0,
            "financial_oxygen_score": 18.9,
            "risk_status": "Critical",
            "primary_trigger": "Delayed salary — employer cash-flow issues",
            "days_in_risk_zone": 22,
        },
        {
            "user_id": 2,
            "name": "Priya Sharma",
            "balance": 12_000.0,
            "financial_oxygen_score": 27.3,
            "risk_status": "At-Risk",
            "primary_trigger": "Medical emergency — INR 80,000 hospital bill",
            "days_in_risk_zone": 14,
        },
        {
            "user_id": 9,
            "name": "Kavita Reddy",
            "balance": 14_200.0,
            "financial_oxygen_score": 31.5,
            "risk_status": "At-Risk",
            "primary_trigger": "Sudden rent increase — relocated to metro city",
            "days_in_risk_zone": 8,
        },
        {
            "user_id": 14,
            "name": "Suresh Nair",
            "balance": 6_800.0,
            "financial_oxygen_score": 15.2,
            "risk_status": "Critical",
            "primary_trigger": "Job loss — contract terminated",
            "days_in_risk_zone": 31,
        },
    ]
