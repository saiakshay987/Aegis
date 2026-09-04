"""
Project Aegis — Adaptive Repayment Plan Generator
==================================================
Generates bank-approved, consented repayment plan recommendations
when a user is detected as at-risk or critical.

Plans adjust EMI to match user's actual recovery cashflow while
protecting the survival buffer.

Usage:
    from simulation.adaptive_repayment import generate_repayment_plan
    result = generate_repayment_plan("USR0001")
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

from ledger import get_db_path, get_walked_balance

DB_PATH = get_db_path()


def _get_db_path():
    return get_db_path()


def _load_user_financials(user_id):
    """Load all financial data for a user."""
    conn = sqlite3.connect(_get_db_path())
    user = pd.read_sql("SELECT * FROM users WHERE user_id = ?", conn, params=(user_id,))
    loans = pd.read_sql("SELECT * FROM loans WHERE user_id = ?", conn, params=(user_id,))
    txns = pd.read_sql("SELECT * FROM transactions WHERE user_id = ? ORDER BY date", conn, params=(user_id,))

    # Try to load features if available
    try:
        features = pd.read_sql("SELECT * FROM features WHERE user_id = ?", conn, params=(user_id,))
    except Exception:
        features = pd.DataFrame()

    conn.close()

    txns["date"] = pd.to_datetime(txns["date"])
    return user, loans, txns, features


def generate_repayment_plan(user_id):
    """
    Generate an adaptive repayment plan for a distressed user.

    Logic:
        1. Calculate available-for-EMI = Projected Monthly Income − Survival Buffer
        2. If available < current EMI burden → recommend restructuring
        3. Generate plan options: EMI holiday, reduced EMI, or tenure extension

    Returns:
        {
            "user_id": "USR0001",
            "eligibility": true,
            "hardship_reason": "Income dropped 55% in last 2 months",
            "current_emi_total": 25000,
            "projected_monthly_income": 45000,
            "survival_buffer": 28000,
            "available_for_emi": 17000,
            "gap_amount": 8000,
            "recommended_plan": {
                "plan_id": "PLAN_USR0001_001",
                "plan_type": "reduced_emi",
                "recommended_emi": 17000,
                "reduction_pct": 32,
                "duration_months": 6,
                "review_date": "2027-03-01",
                "total_interest_impact": 12500
            },
            "alternative_plans": [...],
            "consent_required": true
        }
    """
    user, loans, txns, features = _load_user_financials(user_id)

    if len(user) == 0 or len(txns) == 0:
        return {"user_id": user_id, "error": "No data found"}

    if len(loans) == 0:
        return {
            "user_id": user_id,
            "eligibility": False,
            "reason": "No active loans found",
        }

    # ── Current financial state ──
    current_balance = int(get_walked_balance(user_id))
    ref_date = txns["date"].max()

    # Monthly income (last 3 months average)
    last_90d = txns[txns["date"] >= ref_date - timedelta(days=90)]
    income_cats = ["salary", "freelance_income", "upi_received"]
    income_txns = last_90d[last_90d["category"].isin(income_cats)]
    monthly_income = round(income_txns["amount"].sum() / 3)

    # Total current EMI burden
    total_emi = int(loans["emi_amount"].sum())

    # Essential monthly spend (survival buffer base)
    essential_cats = ["rent", "groceries", "utilities", "transport", "insurance", "medical", "education"]
    essential_txns = last_90d[(last_90d["type"] == "debit") & (last_90d["category"].isin(essential_cats))]
    monthly_essential = round(essential_txns["amount"].sum() / 3)
    survival_buffer = round(monthly_essential * 1.18)  # 18% margin

    # Available for EMI
    available_for_emi = max(0, monthly_income - survival_buffer)

    # ── Determine hardship reason ──
    hardship_reasons = []
    if not features.empty:
        f = features.iloc[0]
        if f.get("income_drop_flag", 0) == 1:
            drop_pct = abs(f.get("income_drop_pct", 0)) * 100
            hardship_reasons.append(f"Income dropped {drop_pct:.0f}% recently")
        if f.get("max_single_medical_txn", 0) > 50000:
            hardship_reasons.append(f"Major medical expense of ₹{int(f['max_single_medical_txn']):,}")
        if f.get("missed_emi_count", 0) > 0:
            hardship_reasons.append(f"{int(f['missed_emi_count'])} EMI payment(s) missed")
        if f.get("balance_trend", 0) < -300:
            hardship_reasons.append(f"Balance declining at ₹{abs(f['balance_trend']):.0f}/day")

    if not hardship_reasons:
        # Fallback detection
        if available_for_emi < total_emi:
            hardship_reasons.append("Insufficient income to cover EMI obligations")
        if current_balance < survival_buffer:
            hardship_reasons.append("Balance below survival buffer threshold")

    # ── Eligibility check ──
    gap = total_emi - available_for_emi
    eligible = gap > 0 or len(hardship_reasons) > 0

    if not eligible:
        return {
            "user_id": user_id,
            "eligibility": False,
            "reason": "User can comfortably service current EMIs",
            "current_emi_total": total_emi,
            "projected_monthly_income": monthly_income,
            "survival_buffer": survival_buffer,
            "available_for_emi": available_for_emi,
            "surplus": available_for_emi - total_emi,
        }

    # ── Generate repayment plans ──
    plans = []

    # Plan 1: Reduced EMI
    if available_for_emi > 0:
        reduction_pct = round((1 - available_for_emi / total_emi) * 100)
        reduced_emi = max(int(available_for_emi * 0.9), int(total_emi * 0.3))  # Floor at 30% of original

        # Estimate interest impact (simplified)
        avg_rate = loans["interest_rate"].mean() / 100 / 12
        interest_impact = round(gap * 6 * avg_rate)  # 6 months of gap × rate

        plans.append({
            "plan_id": f"PLAN_{user_id}_REDUCED",
            "plan_type": "reduced_emi",
            "recommended_emi": reduced_emi,
            "reduction_pct": min(reduction_pct, 70),
            "duration_months": 6,
            "review_date": (ref_date + timedelta(days=180)).strftime("%Y-%m-%d"),
            "total_interest_impact": interest_impact,
            "description": f"Reduce EMI to ₹{reduced_emi:,}/month for 6 months, then review",
        })

    # Plan 2: EMI Holiday (moratorium)
    if gap > total_emi * 0.5:  # Severe case
        moratorium_interest = round(total_emi * 3 * (loans["interest_rate"].mean() / 100 / 12))
        plans.append({
            "plan_id": f"PLAN_{user_id}_HOLIDAY",
            "plan_type": "emi_holiday",
            "recommended_emi": 0,
            "reduction_pct": 100,
            "duration_months": 3,
            "review_date": (ref_date + timedelta(days=90)).strftime("%Y-%m-%d"),
            "total_interest_impact": moratorium_interest,
            "description": "3-month EMI moratorium to allow financial recovery",
        })

    # Plan 3: Tenure Extension
    # Recalculate EMI with extended tenure
    for loan_idx, loan in loans.iterrows():
        extended_tenure = loan["months_remaining"] + 24  # Add 24 months
        r = loan["interest_rate"] / (12 * 100)
        remaining_principal = loan["principal"] * (
            (1 + r) ** loan["tenure_months"] - (1 + r) ** loan["months_paid"]
        ) / ((1 + r) ** loan["tenure_months"] - 1)
        remaining_principal = max(remaining_principal, loan["emi_amount"] * loan["months_remaining"] * 0.8)

        if r > 0:
            new_emi = remaining_principal * r * (1 + r) ** extended_tenure / ((1 + r) ** extended_tenure - 1)
        else:
            new_emi = remaining_principal / extended_tenure

        new_emi = round(new_emi)

    total_new_emi = round(total_emi * 0.65)  # Approximate 35% reduction via extension
    plans.append({
        "plan_id": f"PLAN_{user_id}_EXTEND",
        "plan_type": "tenure_extension",
        "recommended_emi": total_new_emi,
        "reduction_pct": 35,
        "duration_months": 24,
        "review_date": (ref_date + timedelta(days=365)).strftime("%Y-%m-%d"),
        "total_interest_impact": round(total_emi * 24 * 0.15),  # Rough estimate
        "description": f"Extend loan tenure by 24 months, reducing EMI to ₹{total_new_emi:,}/month",
    })

    # Sort plans by interest impact (recommend lowest cost first)
    plans.sort(key=lambda p: p["total_interest_impact"])

    # ── Build result ──
    recommended = plans[0] if plans else None

    result = {
        "user_id": user_id,
        "eligibility": True,
        "hardship_reasons": hardship_reasons,
        "current_emi_total": total_emi,
        "projected_monthly_income": monthly_income,
        "survival_buffer": survival_buffer,
        "available_for_emi": available_for_emi,
        "gap_amount": max(0, gap),
        "recommended_plan": recommended,
        "alternative_plans": plans[1:] if len(plans) > 1 else [],
        "consent_required": True,
        "per_loan_details": [],
    }

    # Add per-loan breakdown
    for _, loan in loans.iterrows():
        result["per_loan_details"].append({
            "loan_id": loan["loan_id"],
            "loan_type": loan["loan_type"],
            "current_emi": int(loan["emi_amount"]),
            "remaining_months": int(loan["months_remaining"]),
            "interest_rate": float(loan["interest_rate"]),
        })

    return result


if __name__ == "__main__":
    print("📋 Adaptive Repayment Plan — Test Run")
    print("=" * 60)

    for uid in ["USR0001", "USR0050", "USR0100", "USR0250"]:
        result = generate_repayment_plan(uid)
        if "error" in result:
            print(f"\n{uid}: {result['error']}")
            continue
        print(f"\n{'─'*50}")
        print(f"User: {result['user_id']}")
        print(f"  Eligible: {result['eligibility']}")
        if not result['eligibility']:
            print(f"  Reason: {result.get('reason', 'N/A')}")
            continue
        print(f"  Monthly Income:  ₹{result['projected_monthly_income']:,}")
        print(f"  Survival Buffer: ₹{result['survival_buffer']:,}")
        print(f"  Current EMI:     ₹{result['current_emi_total']:,}")
        print(f"  Available:       ₹{result['available_for_emi']:,}")
        print(f"  Gap:             ₹{result['gap_amount']:,}")
        if result.get("hardship_reasons"):
            print(f"  Hardship Reasons:")
            for r in result["hardship_reasons"]:
                print(f"    • {r}")
        if result.get("recommended_plan"):
            plan = result["recommended_plan"]
            print(f"  📌 Recommended: {plan['plan_type']}")
            print(f"     New EMI: ₹{plan['recommended_emi']:,} (↓{plan['reduction_pct']}%)")
            print(f"     Duration: {plan['duration_months']} months")
            print(f"     Interest Impact: ₹{plan['total_interest_impact']:,}")
