"""
Project Aegis — Minimum Survival Buffer Calculator
===================================================
Calculates the minimum amount a user needs ring-fenced to cover
essential living expenses, with a safety margin.

Usage:
    from simulation.survival_buffer import calculate_survival_buffer
    result = calculate_survival_buffer("USR0001")
"""

import pandas as pd
import numpy as np
import sqlite3
import os
import sys
from pathlib import Path
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = str(Path(BASE_DIR).resolve().parents[2])
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from ledger import get_db_path

DB_PATH = get_db_path()

# Safety margin percentage (15-20%)
SAFETY_MARGIN = 0.18

# Essential categories that must be protected
ESSENTIAL_CATEGORIES = [
    "rent", "groceries", "utilities", "transport",
    "insurance", "medical", "education",
]


def _get_db_path():
    return get_db_path()


def calculate_survival_buffer(user_id):
    """
    Calculate the minimum survival buffer for a user.

    The survival buffer = (average monthly essential expenses) × (1 + safety_margin)

    This is the amount that should be ring-fenced and NOT used for
    EMI payments or debt repayment.

    Returns:
        {
            "user_id": "USR0001",
            "monthly_essential_breakdown": {
                "rent": 15000,
                "groceries": 8000,
                ...
            },
            "total_monthly_essential": 38000,
            "safety_margin_pct": 18,
            "buffer_amount": 44840,
            "ring_fenced": true,
            "current_balance": 65000,
            "buffer_coverage_months": 1.5,
            "buffer_status": "adequate"
        }
    """
    conn = sqlite3.connect(_get_db_path())
    txns = pd.read_sql(
        "SELECT * FROM transactions WHERE user_id = ? ORDER BY date",
        conn, params=(user_id,)
    )
    user = pd.read_sql(
        "SELECT * FROM users WHERE user_id = ?",
        conn, params=(user_id,)
    )
    conn.close()

    if len(txns) == 0 or len(user) == 0:
        return {"user_id": user_id, "error": "No data found"}

    txns["date"] = pd.to_datetime(txns["date"])
    txns["month"] = txns["date"].dt.to_period("M")

    # Get current balance
    current_balance = int(txns.iloc[-1]["balance_after"])

    # ── Calculate average monthly spend per essential category ──
    essential_txns = txns[
        (txns["type"] == "debit") &
        (txns["category"].isin(ESSENTIAL_CATEGORIES))
    ]

    # Use last 3 months for accurate estimation
    ref_date = txns["date"].max()
    recent_essential = essential_txns[essential_txns["date"] >= ref_date - timedelta(days=90)]

    # Monthly average per category
    monthly_by_cat = recent_essential.groupby(["month", "category"])["amount"].sum().reset_index()
    avg_by_cat = monthly_by_cat.groupby("category")["amount"].mean()

    # Build breakdown
    breakdown = {}
    for cat in ESSENTIAL_CATEGORIES:
        if cat in avg_by_cat.index:
            breakdown[cat] = round(avg_by_cat[cat])
        else:
            breakdown[cat] = 0

    total_monthly_essential = sum(breakdown.values())

    # ── Apply safety margin ──
    buffer_amount = round(total_monthly_essential * (1 + SAFETY_MARGIN))

    # ── Determine buffer status ──
    if current_balance <= 0:
        buffer_coverage_months = 0
        buffer_status = "depleted"
    elif buffer_amount > 0:
        buffer_coverage_months = round(current_balance / buffer_amount, 1)
        if buffer_coverage_months >= 3:
            buffer_status = "strong"
        elif buffer_coverage_months >= 1.5:
            buffer_status = "adequate"
        elif buffer_coverage_months >= 1:
            buffer_status = "thin"
        else:
            buffer_status = "critical"
    else:
        buffer_coverage_months = 999
        buffer_status = "unknown"

    # Should we ring-fence?
    ring_fenced = buffer_status in ("thin", "critical", "depleted")

    return {
        "user_id": user_id,
        "monthly_essential_breakdown": breakdown,
        "total_monthly_essential": total_monthly_essential,
        "safety_margin_pct": int(SAFETY_MARGIN * 100),
        "buffer_amount": buffer_amount,
        "ring_fenced": ring_fenced,
        "current_balance": current_balance,
        "buffer_coverage_months": buffer_coverage_months,
        "buffer_status": buffer_status,
    }


if __name__ == "__main__":
    print("🛡️ Survival Buffer Calculator — Test Run")
    print("=" * 60)

    for uid in ["USR0001", "USR0050", "USR0100", "USR0250"]:
        result = calculate_survival_buffer(uid)
        if "error" in result:
            print(f"\n{uid}: {result['error']}")
            continue
        print(f"\n{'─'*40}")
        print(f"User: {result['user_id']}")
        print(f"  Current Balance:    ₹{result['current_balance']:,}")
        print(f"  Monthly Essentials: ₹{result['total_monthly_essential']:,}")
        print(f"  Buffer (with {result['safety_margin_pct']}% margin): ₹{result['buffer_amount']:,}")
        print(f"  Coverage: {result['buffer_coverage_months']} months")
        print(f"  Status: {result['buffer_status'].upper()}")
        print(f"  Ring-fenced: {'Yes' if result['ring_fenced'] else 'No'}")
        print(f"  Breakdown:")
        for cat, amt in result['monthly_essential_breakdown'].items():
            if amt > 0:
                print(f"    {cat:15s}: ₹{amt:,}")
