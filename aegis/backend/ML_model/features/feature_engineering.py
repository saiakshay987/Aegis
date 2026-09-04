"""
Project Aegis — Feature Engineering Pipeline
=============================================
Reads raw transaction/user/loan data from SQLite and computes 25+
ML-ready features per user. Stores results back in SQLite + CSV.

Run: python feature_engineering.py
"""

import pandas as pd
import numpy as np
import sqlite3
import os
import json
from datetime import datetime, timedelta

from datetime import datetime, timedelta
import sys
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = str(Path(BASE_DIR).resolve().parents[1])
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from ledger import get_db_path, get_walked_balance

DB_PATH = get_db_path()
OUTPUT_DIR = BASE_DIR


def load_data():
    """Load all tables from SQLite using canonical database path."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    users = pd.read_sql("SELECT * FROM users", conn)
    loans = pd.read_sql("SELECT * FROM loans", conn)
    txns = pd.read_sql("SELECT * FROM transactions", conn)
    conn.close()

    txns["date"] = pd.to_datetime(txns["date"])
    txns["month"] = txns["date"].dt.to_period("M")
    return users, loans, txns


# ─── Income & Stability Features ─────────────────────────────────────────────

def compute_income_features(txns, user_id):
    """Compute income-related features for a user."""
    user_txns = txns[txns["user_id"] == user_id]
    income_cats = ["salary", "freelance_income", "upi_received"]
    income_txns = user_txns[user_txns["category"].isin(income_cats)]

    # Monthly income aggregation
    monthly_income = income_txns.groupby("month")["amount"].sum()

    # Last 3 months
    last_3m = monthly_income.tail(3)
    # Last 6 months
    last_6m = monthly_income.tail(6)

    avg_monthly_income = last_3m.mean() if len(last_3m) > 0 else 0

    # Income volatility (coefficient of variation)
    if len(last_6m) > 1 and last_6m.mean() > 0:
        income_volatility = last_6m.std() / last_6m.mean()
    else:
        income_volatility = 0.0

    # Income trend (slope over last 6 months)
    if len(last_6m) >= 3:
        x = np.arange(len(last_6m))
        slope = np.polyfit(x, last_6m.values, 1)[0]
        income_trend = slope / (last_6m.mean() + 1)  # Normalized slope
    else:
        income_trend = 0.0

    # Months since last income
    if len(income_txns) > 0:
        last_income_date = income_txns["date"].max()
        ref_date = txns["date"].max()
        months_since_last_income = (ref_date - last_income_date).days / 30
    else:
        months_since_last_income = 12  # Max flag

    return {
        "avg_monthly_income": round(avg_monthly_income),
        "income_volatility": round(income_volatility, 4),
        "income_trend": round(income_trend, 4),
        "months_since_last_income": round(months_since_last_income, 1),
    }


# ─── Spending & Burn Rate Features ───────────────────────────────────────────

def compute_spending_features(txns, user_id):
    """Compute spending-related features for a user."""
    user_txns = txns[txns["user_id"] == user_id]
    debit_txns = user_txns[user_txns["type"] == "debit"]

    essential_cats = ["rent", "groceries", "utilities", "transport", "insurance",
                      "medical", "education", "emi_payment"]
    discretionary_cats = ["dining", "shopping", "entertainment", "travel",
                          "subscriptions", "personal_care"]

    essential_txns = debit_txns[debit_txns["category"].isin(essential_cats)]
    discretionary_txns = debit_txns[debit_txns["category"].isin(discretionary_cats)]

    # Monthly aggregations
    monthly_essential = essential_txns.groupby("month")["amount"].sum()
    monthly_discretionary = discretionary_txns.groupby("month")["amount"].sum()
    monthly_total_debit = debit_txns.groupby("month")["amount"].sum()

    avg_essential = monthly_essential.tail(3).mean() if len(monthly_essential) > 0 else 0
    avg_discretionary = monthly_discretionary.tail(3).mean() if len(monthly_discretionary) > 0 else 0

    # Income for ratios
    income_cats = ["salary", "freelance_income", "upi_received"]
    income_txns = user_txns[user_txns["category"].isin(income_cats)]
    monthly_income = income_txns.groupby("month")["amount"].sum()
    avg_income = monthly_income.tail(3).mean() if len(monthly_income) > 0 else 1

    # Ratios
    essential_to_income = avg_essential / max(avg_income, 1)
    discretionary_to_income = avg_discretionary / max(avg_income, 1)

    # Burn rate trend (slope of monthly total spending)
    if len(monthly_total_debit) >= 3:
        x = np.arange(len(monthly_total_debit.tail(6)))
        slope = np.polyfit(x, monthly_total_debit.tail(6).values, 1)[0]
        burn_rate_trend = slope / (monthly_total_debit.tail(6).mean() + 1)
    else:
        burn_rate_trend = 0.0

    # Spending spikes
    if len(monthly_total_debit) >= 3:
        rolling_avg = monthly_total_debit.rolling(3, min_periods=1).mean()
        spike_count = int((monthly_total_debit > rolling_avg * 1.5).sum())
    else:
        spike_count = 0

    return {
        "avg_monthly_essential_spend": round(avg_essential),
        "avg_monthly_discretionary_spend": round(avg_discretionary),
        "essential_to_income_ratio": round(essential_to_income, 4),
        "discretionary_to_income_ratio": round(discretionary_to_income, 4),
        "burn_rate_trend": round(burn_rate_trend, 4),
        "spending_spike_count": spike_count,
    }


# ─── Balance & Liquidity Features ────────────────────────────────────────────

def compute_balance_features(txns, user_id):
    """Compute balance and liquidity features."""
    user_txns = txns[txns["user_id"] == user_id].sort_values("date")

    if len(user_txns) == 0:
        return {
            "current_balance": 0, "avg_balance_30d": 0, "min_balance_30d": 0,
            "balance_trend": 0.0, "days_until_zero": 999,
        }

    # Current balance derived by walking the transaction ledger forward
    current_balance = int(get_walked_balance(user_id))

    # Last 30 days
    ref_date = user_txns["date"].max()
    last_30d = user_txns[user_txns["date"] >= ref_date - timedelta(days=30)]

    avg_balance_30d = int(last_30d["balance_after"].mean()) if len(last_30d) > 0 else current_balance
    min_balance_30d = int(last_30d["balance_after"].min()) if len(last_30d) > 0 else current_balance

    # Balance trend (slope of daily balance over last 90 days)
    last_90d = user_txns[user_txns["date"] >= ref_date - timedelta(days=90)]
    if len(last_90d) >= 5:
        days_from_start = (last_90d["date"] - last_90d["date"].min()).dt.days.values
        balances = last_90d["balance_after"].values
        slope = np.polyfit(days_from_start, balances, 1)[0]
        balance_trend = round(slope, 2)  # ₹ change per day
    else:
        balance_trend = 0.0

    # Days until zero (at current burn rate)
    if balance_trend < 0 and current_balance > 0:
        days_until_zero = int(current_balance / abs(balance_trend))
        days_until_zero = min(days_until_zero, 999)  # Cap
    else:
        days_until_zero = 999  # No danger

    return {
        "current_balance": current_balance,
        "avg_balance_30d": avg_balance_30d,
        "min_balance_30d": min_balance_30d,
        "balance_trend": balance_trend,
        "days_until_zero": days_until_zero,
    }


# ─── EMI & Debt Features ─────────────────────────────────────────────────────

def compute_emi_features(txns, loans, user_id):
    """Compute EMI and debt-related features."""
    user_loans = loans[loans["user_id"] == user_id]
    user_txns = txns[txns["user_id"] == user_id]

    total_emi_burden = int(user_loans["emi_amount"].sum()) if len(user_loans) > 0 else 0

    # EMI to income ratio
    income_cats = ["salary", "freelance_income", "upi_received"]
    income_txns = user_txns[user_txns["category"].isin(income_cats)]
    monthly_income = income_txns.groupby("month")["amount"].sum()
    avg_income = monthly_income.tail(3).mean() if len(monthly_income) > 0 else 1

    emi_to_income_ratio = total_emi_burden / max(avg_income, 1)

    # Missed EMIs
    emi_missed_txns = user_txns[user_txns["category"] == "emi_missed"]
    missed_emi_count = len(emi_missed_txns)

    # EMI payment consistency
    emi_txns = user_txns[user_txns["category"].isin(["emi_payment", "emi_missed"])]
    if len(emi_txns) > 0:
        paid = len(emi_txns[emi_txns["category"] == "emi_payment"])
        emi_payment_consistency = paid / len(emi_txns)
    else:
        emi_payment_consistency = 1.0  # No loans = no missed payments

    return {
        "total_emi_burden": total_emi_burden,
        "emi_to_income_ratio": round(emi_to_income_ratio, 4),
        "missed_emi_count": missed_emi_count,
        "emi_payment_consistency": round(emi_payment_consistency, 4),
    }


# ─── Shock Detection Features ────────────────────────────────────────────────

def compute_shock_features(txns, user_id):
    """Compute financial shock detection features."""
    user_txns = txns[txns["user_id"] == user_id]
    debit_txns = user_txns[user_txns["type"] == "debit"]

    # Medical shock detection
    medical_txns = debit_txns[debit_txns["category"] == "medical"]
    max_single_medical = int(medical_txns["amount"].max()) if len(medical_txns) > 0 else 0

    # Medical spend spike (current month vs 3-month avg)
    monthly_medical = medical_txns.groupby("month")["amount"].sum()
    if len(monthly_medical) >= 2:
        avg_medical = monthly_medical.iloc[:-1].mean()
        current_medical = monthly_medical.iloc[-1]
        medical_spend_spike = current_medical / max(avg_medical, 1)
    else:
        medical_spend_spike = 1.0

    # Income drop flag
    income_cats = ["salary", "freelance_income", "upi_received"]
    income_txns = user_txns[user_txns["category"].isin(income_cats)]
    monthly_income = income_txns.groupby("month")["amount"].sum()
    if len(monthly_income) >= 2:
        prev_income = monthly_income.iloc[-2]
        curr_income = monthly_income.iloc[-1]
        income_drop_pct = (prev_income - curr_income) / max(prev_income, 1)
        income_drop_flag = 1 if income_drop_pct > 0.40 else 0
    else:
        income_drop_flag = 0
        income_drop_pct = 0.0

    # Large unexpected debit
    monthly_debit = debit_txns.groupby("month")["amount"].mean()
    avg_debit = monthly_debit.mean() if len(monthly_debit) > 0 else 0
    large_debits = debit_txns[debit_txns["amount"] > avg_debit * 3]
    large_unexpected_debit = len(large_debits)

    return {
        "max_single_medical_txn": max_single_medical,
        "medical_spend_spike": round(medical_spend_spike, 4),
        "income_drop_flag": income_drop_flag,
        "income_drop_pct": round(income_drop_pct, 4),
        "large_unexpected_debit": large_unexpected_debit,
    }


# ─── Label Generator ─────────────────────────────────────────────────────────

def derive_labels(features_row, user_row):
    """Derive the target label (healthy/at_risk/critical) from features.
    
    This uses rule-based logic on the computed features to create training labels.
    In production, these would come from actual default/delinquency records.
    """
    score = 0

    # EMI problems
    if features_row.get("missed_emi_count", 0) >= 3:
        score += 35
    elif features_row.get("missed_emi_count", 0) >= 1:
        score += 15

    # EMI burden
    if features_row.get("emi_to_income_ratio", 0) > 0.6:
        score += 20
    elif features_row.get("emi_to_income_ratio", 0) > 0.45:
        score += 10

    # Balance danger
    if features_row.get("days_until_zero", 999) < 30:
        score += 25
    elif features_row.get("days_until_zero", 999) < 60:
        score += 15
    elif features_row.get("days_until_zero", 999) < 90:
        score += 8

    # Income instability
    if features_row.get("income_drop_flag", 0) == 1:
        score += 15
    if features_row.get("income_volatility", 0) > 0.3:
        score += 10

    # Medical shock
    if features_row.get("max_single_medical_txn", 0) > 50000:
        score += 12

    # Spending out of control
    if features_row.get("essential_to_income_ratio", 0) > 0.7:
        score += 10
    if features_row.get("burn_rate_trend", 0) > 0.1:
        score += 8

    # Balance trend
    if features_row.get("balance_trend", 0) < -500:
        score += 10
    elif features_row.get("balance_trend", 0) < -200:
        score += 5

    # Classify
    if score >= 50:
        return "critical"
    elif score >= 25:
        return "at_risk"
    else:
        return "healthy"


# ─── Main Pipeline ───────────────────────────────────────────────────────────

def compute_all_features():
    """Compute features for all users and save to SQLite + CSV."""
    print("🔧 Project Aegis — Feature Engineering Pipeline")
    print("=" * 60)

    print("\n[1/3] Loading data from SQLite...")
    users, loans, txns = load_data()
    print(f"  ✓ {len(users)} users, {len(loans)} loans, {len(txns):,} transactions")

    print("\n[2/3] Computing features per user...")
    feature_rows = []

    for idx, user in users.iterrows():
        uid = user["user_id"]

        features = {"user_id": uid}
        features.update(compute_income_features(txns, uid))
        features.update(compute_spending_features(txns, uid))
        features.update(compute_balance_features(txns, uid))
        features.update(compute_emi_features(txns, loans, uid))
        features.update(compute_shock_features(txns, uid))

        # Derive label
        features["risk_label"] = derive_labels(features, user)

        feature_rows.append(features)

        if (idx + 1) % 50 == 0:
            print(f"  ... processed {idx + 1}/{len(users)} users")

    features_df = pd.DataFrame(feature_rows)

    print(f"\n  ✓ {len(features_df)} feature vectors computed")
    print(f"  ✓ {len(features_df.columns) - 2} features per user")  # minus user_id and label

    print(f"\n📊 Label Distribution:")
    for label, count in features_df["risk_label"].value_counts().items():
        pct = count / len(features_df) * 100
        print(f"  {label:12s} → {count:4d} users ({pct:.1f}%)")

    print("\n[3/3] Saving to SQLite and CSV...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Save to CSV
    csv_path = os.path.join(OUTPUT_DIR, "features.csv")
    features_df.to_csv(csv_path, index=False)
    print(f"  ✓ CSV saved: {csv_path}")

    # Save to SQLite
    conn = sqlite3.connect(DB_PATH)
    features_df.to_sql("features", conn, if_exists="replace", index=False)
    conn.close()
    print(f"  ✓ SQLite table 'features' updated")

    # Save feature metadata
    feature_cols = [c for c in features_df.columns if c not in ("user_id", "risk_label")]
    metadata = {}
    for col in feature_cols:
        metadata[col] = {
            "type": str(features_df[col].dtype),
            "min": float(features_df[col].min()),
            "max": float(features_df[col].max()),
            "mean": float(features_df[col].mean()),
            "description": _get_feature_description(col),
        }
    meta_path = os.path.join(OUTPUT_DIR, "feature_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"  ✓ Metadata saved: {meta_path}")

    print("\n✅ Feature engineering complete!")
    return features_df


def _get_feature_description(name):
    """Return human-readable description for a feature."""
    descriptions = {
        "avg_monthly_income": "Average monthly income over last 3 months (₹)",
        "income_volatility": "Coefficient of variation of monthly income (0=stable, >0.3=volatile)",
        "income_trend": "Normalized slope of income over last 6 months (negative=declining)",
        "months_since_last_income": "Months since the last income credit was received",
        "avg_monthly_essential_spend": "Average monthly essential expenses over last 3 months (₹)",
        "avg_monthly_discretionary_spend": "Average monthly discretionary spending over last 3 months (₹)",
        "essential_to_income_ratio": "Essential spending / income ratio (>0.7 = budget very tight)",
        "discretionary_to_income_ratio": "Discretionary spending / income ratio",
        "burn_rate_trend": "Normalized slope of total monthly spending (positive = increasing)",
        "spending_spike_count": "Number of months where spending exceeded 1.5x the 3-month average",
        "current_balance": "Current account balance (₹)",
        "avg_balance_30d": "Average balance over the last 30 days (₹)",
        "min_balance_30d": "Minimum balance hit in the last 30 days (₹)",
        "balance_trend": "Daily balance change rate (₹/day, negative = declining)",
        "days_until_zero": "Projected days until balance reaches zero at current burn rate",
        "total_emi_burden": "Total monthly EMI obligation across all loans (₹)",
        "emi_to_income_ratio": "Total EMI / monthly income (>0.5 is a red flag)",
        "missed_emi_count": "Number of EMIs missed in the dataset timeframe",
        "emi_payment_consistency": "Percentage of EMIs paid on time (1.0 = perfect)",
        "max_single_medical_txn": "Largest single medical transaction (₹)",
        "medical_spend_spike": "Current month medical spend / historical average (>3 = spike)",
        "income_drop_flag": "Binary flag: 1 if income dropped >40% month-over-month",
        "income_drop_pct": "Percentage drop in income month-over-month",
        "large_unexpected_debit": "Count of individual debits exceeding 3x average monthly debit",
    }
    return descriptions.get(name, name)


# Allow importing individual feature functions
def get_user_features(user_id):
    """Compute features for a single user (for real-time API use)."""
    conn = sqlite3.connect(DB_PATH)
    # Use parameterized queries to prevent SQL injection
    txns  = pd.read_sql("SELECT * FROM transactions WHERE user_id = ?", conn, params=(user_id,))
    loans = pd.read_sql("SELECT * FROM loans WHERE user_id = ?",        conn, params=(user_id,))
    users = pd.read_sql("SELECT * FROM users WHERE user_id = ?",        conn, params=(user_id,))
    conn.close()

    if len(users) == 0:
        return None

    txns["date"] = pd.to_datetime(txns["date"])
    txns["month"] = txns["date"].dt.to_period("M")

    features = {"user_id": user_id}
    features.update(compute_income_features(txns, user_id))
    features.update(compute_spending_features(txns, user_id))
    features.update(compute_balance_features(txns, user_id))
    features.update(compute_emi_features(txns, loans, user_id))
    features.update(compute_shock_features(txns, user_id))

    return features


if __name__ == "__main__":
    compute_all_features()
