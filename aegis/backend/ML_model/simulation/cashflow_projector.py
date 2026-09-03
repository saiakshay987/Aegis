"""
Project Aegis — 30/60/90 Day Cashflow Projector
================================================
Projects a user's account balance trajectory based on recent
income and spending patterns. Identifies estimated default day.

Usage:
    from simulation.cashflow_projector import project_cashflow
    result = project_cashflow("USR0001")
"""

import pandas as pd
import numpy as np
import sqlite3
import os
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(os.path.dirname(BASE_DIR), "data", "aegis.db")


def _get_db_path():
    if os.path.exists(DB_PATH):
        return DB_PATH
    alt = os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), "data", "aegis.db")
    if os.path.exists(alt):
        return alt
    raise FileNotFoundError(f"Database not found at {DB_PATH}")


def _load_user_data(user_id):
    """Load user's transaction and loan data from SQLite."""
    conn = sqlite3.connect(_get_db_path())
    txns = pd.read_sql(
        f"SELECT * FROM transactions WHERE user_id = ? ORDER BY date",
        conn, params=(user_id,)
    )
    loans = pd.read_sql(
        f"SELECT * FROM loans WHERE user_id = ?",
        conn, params=(user_id,)
    )
    user = pd.read_sql(
        f"SELECT * FROM users WHERE user_id = ?",
        conn, params=(user_id,)
    )
    conn.close()

    txns["date"] = pd.to_datetime(txns["date"])
    return txns, loans, user


def project_cashflow(user_id, days=(30, 60, 90)):
    """
    Project a user's cashflow trajectory.

    Args:
        user_id: The user ID to project for
        days: Tuple of projection horizons in days

    Returns:
        Dictionary with projection data:
        {
            "user_id": "USR0001",
            "current_balance": 45000,
            "projections": {
                "day_30": 12000,
                "day_60": -8000,
                "day_90": -35000
            },
            "daily_trajectory": [...],  # Day-by-day balance
            "estimated_default_day": 47 or null,
            "avg_daily_income": 2500,
            "avg_daily_burn": 3100,
            "net_daily_flow": -600,
            "projection_confidence": "medium"
        }
    """
    txns, loans, user = _load_user_data(user_id)

    if len(txns) == 0 or len(user) == 0:
        return {"user_id": user_id, "error": "No data found"}

    # ── Current state ──
    current_balance = int(txns.iloc[-1]["balance_after"])
    ref_date = txns["date"].max()

    # ── Calculate average daily income (from last 3 months) ──
    last_90d = txns[txns["date"] >= ref_date - timedelta(days=90)]

    income_cats = ["salary", "freelance_income", "upi_received"]
    income_txns = last_90d[last_90d["category"].isin(income_cats)]
    total_income_90d = income_txns["amount"].sum()
    avg_daily_income = total_income_90d / 90

    # ── Calculate average daily burn (from last 3 months) ──
    debit_txns = last_90d[last_90d["type"] == "debit"]
    # Exclude emi_missed (those are zero-amount markers)
    debit_txns = debit_txns[debit_txns["category"] != "emi_missed"]
    total_burn_90d = debit_txns["amount"].sum()
    avg_daily_burn = total_burn_90d / 90

    # ── Net daily cashflow ──
    net_daily_flow = avg_daily_income - avg_daily_burn

    # ── Monthly EMI obligations (known fixed costs) ──
    total_monthly_emi = int(loans["emi_amount"].sum()) if len(loans) > 0 else 0
    daily_emi_allocation = total_monthly_emi / 30

    # ── Project day-by-day balance ──
    max_days = max(days) + 1
    trajectory = []
    balance = current_balance
    default_day = None

    # Add some randomness to simulate real-world variability
    rng = np.random.RandomState(hash(user_id) % 2**31)

    for day in range(1, max_days + 1):
        # Daily income (with variability)
        day_income = avg_daily_income * rng.uniform(0.0, 2.0)

        # Salary spike on day 1-5 of each month cycle
        if day % 30 <= 5:
            day_income += avg_daily_income * 8  # Monthly salary concentrated

        # Daily expenses (with variability)
        day_expense = avg_daily_burn * rng.uniform(0.5, 1.5)

        # EMI payment on EMI days (roughly monthly)
        if day % 30 in [1, 2, 3, 4, 5] and len(loans) > 0:
            day_expense += total_monthly_emi / 5  # Spread EMIs over 5 days

        balance = balance + day_income - day_expense
        trajectory.append(round(balance))

        # Track when balance first goes negative
        if balance <= 0 and default_day is None:
            default_day = day

    # ── Determine projection confidence ──
    data_months = (ref_date - txns["date"].min()).days / 30
    if data_months >= 6 and len(txns) > 100:
        confidence = "high"
    elif data_months >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    # ── Build result ──
    projections = {}
    for d in days:
        projected_val = trajectory[d - 1] if d <= len(trajectory) else trajectory[-1]
        projections[f"day_{d}"] = round(projected_val)

    result = {
        "user_id": user_id,
        "current_balance": current_balance,
        "projections": projections,
        "daily_trajectory": trajectory[:max(days)],
        "estimated_default_day": default_day,
        "avg_daily_income": round(avg_daily_income, 2),
        "avg_daily_burn": round(avg_daily_burn, 2),
        "net_daily_flow": round(net_daily_flow, 2),
        "total_monthly_emi": total_monthly_emi,
        "projection_confidence": confidence,
        "data_months_available": round(data_months, 1),
    }

    return result


def project_cashflow_simple(user_id):
    """
    Simplified deterministic projection (no randomness).
    Uses straight-line extrapolation for API consistency.
    """
    txns, loans, user = _load_user_data(user_id)

    if len(txns) == 0 or len(user) == 0:
        return {"user_id": user_id, "error": "No data found"}

    current_balance = int(txns.iloc[-1]["balance_after"])
    ref_date = txns["date"].max()

    # Last 90 days stats
    last_90d = txns[txns["date"] >= ref_date - timedelta(days=90)]
    income_cats = ["salary", "freelance_income", "upi_received"]
    income_txns = last_90d[last_90d["category"].isin(income_cats)]
    debit_txns = last_90d[(last_90d["type"] == "debit") & (last_90d["category"] != "emi_missed")]

    avg_daily_income = income_txns["amount"].sum() / 90
    avg_daily_burn = debit_txns["amount"].sum() / 90
    net_daily = avg_daily_income - avg_daily_burn

    # Straight-line projection
    day_30 = round(current_balance + net_daily * 30)
    day_60 = round(current_balance + net_daily * 60)
    day_90 = round(current_balance + net_daily * 90)

    # Default day
    if net_daily < 0 and current_balance > 0:
        default_day = int(current_balance / abs(net_daily))
    else:
        default_day = None

    return {
        "user_id": user_id,
        "current_balance": current_balance,
        "day_30": day_30,
        "day_60": day_60,
        "day_90": day_90,
        "estimated_default_day": default_day,
        "avg_daily_income": round(avg_daily_income, 2),
        "avg_daily_burn": round(avg_daily_burn, 2),
        "net_daily_flow": round(net_daily, 2),
    }


if __name__ == "__main__":
    # Test with a few users
    print("📈 Cashflow Projector — Test Run")
    print("=" * 60)

    for uid in ["USR0001", "USR0050", "USR0100", "USR0250"]:
        result = project_cashflow(uid)
        print(f"\n{'─'*40}")
        print(f"User: {result['user_id']}")
        print(f"  Current Balance: ₹{result['current_balance']:,}")
        for label, val in result['projections'].items():
            marker = "⚠️" if val < 0 else "✓"
            print(f"  {label}: ₹{val:,} {marker}")
        if result['estimated_default_day']:
            print(f"  🚨 Estimated default in {result['estimated_default_day']} days")
        print(f"  Confidence: {result['projection_confidence']}")
