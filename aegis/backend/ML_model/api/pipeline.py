"""
Project Aegis — Data Pipeline Orchestrator
===========================================
Ties together all components (features, models, simulation) into a
unified pipeline. Supports both batch processing and single-user queries.

The FastAPI layer imports functions from this module.

Usage:
    from api.pipeline import get_user_assessment, get_portfolio_summary
"""

import pandas as pd
import numpy as np
import sqlite3
import os
import sys
import json
from datetime import datetime

# Add parent directory to path for imports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ML_MODEL_DIR = os.path.dirname(BASE_DIR)
BACKEND_DIR = os.path.dirname(ML_MODEL_DIR)
for _p in [ML_MODEL_DIR, BACKEND_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ledger import get_db_path

from features.feature_engineering import get_user_features, compute_all_features
from simulation.cashflow_projector import project_cashflow, project_cashflow_simple
from simulation.survival_buffer import calculate_survival_buffer
from simulation.adaptive_repayment import generate_repayment_plan
from simulation.risk_scorer import compute_risk_score, compute_all_risk_scores

DB_PATH = get_db_path()


def _get_db_path():
    return get_db_path()


# ─── Single-User API Functions ───────────────────────────────────────────────

def get_user_assessment(user_id: str) -> dict:
    """
    Complete risk assessment for a single user.
    This is the primary API endpoint function.

    Returns everything the frontend needs:
    - Risk score & tier
    - 30/60/90 day projection
    - Survival buffer
    - Recommended repayment plan (if at-risk/critical)
    - Top risk factors
    - Transaction anomalies
    """
    # 1. Risk score
    risk = compute_risk_score(user_id)
    if "error" in risk:
        return {"user_id": user_id, "error": risk["error"]}

    # 2. Cashflow projection (deterministic for API consistency)
    projection = project_cashflow_simple(user_id)

    # 3. Survival buffer
    buffer = calculate_survival_buffer(user_id)

    # 4. Repayment plan (only for at-risk/critical)
    repayment = None
    if risk["risk_tier"] in ("at_risk", "critical"):
        repayment = generate_repayment_plan(user_id)

    # 5. Anomalies
    anomalies = get_user_anomalies(user_id)

    # 6. User profile
    conn = sqlite3.connect(_get_db_path())
    user = pd.read_sql("SELECT * FROM users WHERE user_id = ?", conn, params=(user_id,))
    conn.close()

    profile = {}
    if len(user) > 0:
        u = user.iloc[0]
        profile = {
            "name": u["name"],
            "age": int(u["age"]),
            "city": u["city"],
            "occupation": u["occupation"],
            "monthly_income": int(u["monthly_income"]),
        }

    # Assemble response
    result = {
        "user_id": user_id,
        "timestamp": datetime.now().isoformat(),
        "profile": profile,
        "risk_score": risk["risk_score"],
        "risk_tier": risk["risk_tier"],
        "component_scores": risk["component_scores"],
        "top_risk_factors": risk["top_risk_factors"],
        "projection": {
            "current_balance": projection.get("current_balance", 0),
            "day_30": projection.get("day_30", 0),
            "day_60": projection.get("day_60", 0),
            "day_90": projection.get("day_90", 0),
            "estimated_default_day": projection.get("estimated_default_day"),
            "net_daily_flow": projection.get("net_daily_flow", 0),
        },
        "survival_buffer": {
            "monthly_essential": buffer.get("total_monthly_essential", 0),
            "buffer_amount": buffer.get("buffer_amount", 0),
            "buffer_status": buffer.get("buffer_status", "unknown"),
            "coverage_months": buffer.get("buffer_coverage_months", 0),
            "ring_fenced": buffer.get("ring_fenced", False),
        },
        "recommended_plan": None,
        "anomalies": anomalies,
    }

    # Add repayment plan if applicable
    if repayment and repayment.get("eligibility"):
        result["recommended_plan"] = {
            "eligibility": True,
            "current_emi_total": repayment.get("current_emi_total", 0),
            "recommended_plan": repayment.get("recommended_plan"),
            "alternative_plans": repayment.get("alternative_plans", []),
            "hardship_reasons": repayment.get("hardship_reasons", []),
            "gap_amount": repayment.get("gap_amount", 0),
        }

    return result


def get_user_projection(user_id: str) -> dict:
    """Get 30/60/90 day cashflow projection for a user."""
    return project_cashflow(user_id)


def get_user_repayment_plan(user_id: str) -> dict:
    """Get adaptive repayment plan recommendation."""
    return generate_repayment_plan(user_id)


def get_user_anomalies(user_id: str) -> list:
    """Get recent transaction anomalies for a user."""
    try:
        conn = sqlite3.connect(_get_db_path())
        anomalies = pd.read_sql(
            "SELECT * FROM anomalies WHERE user_id = ? ORDER BY anomaly_score DESC LIMIT 10",
            conn, params=(user_id,)
        )
        conn.close()

        if len(anomalies) == 0:
            return []

        return anomalies.to_dict(orient="records")

    except Exception:
        return []


def get_user_survival_buffer(user_id: str) -> dict:
    """Get survival buffer calculation for a user."""
    return calculate_survival_buffer(user_id)


# ─── Portfolio-Level API Functions ────────────────────────────────────────────

def get_portfolio_summary() -> dict:
    """
    Aggregate risk stats across all users.
    Used by the Bank Ops Command Center.
    """
    conn = sqlite3.connect(_get_db_path())

    # Get all users with their features and risk scores
    try:
        users = pd.read_sql("SELECT * FROM users", conn)
        features = pd.read_sql("SELECT * FROM features", conn)
        risk_scores = pd.read_sql("SELECT * FROM risk_scores", conn)
    except Exception:
        # Risk scores table might not exist yet
        conn.close()
        return {"error": "Run the full pipeline first (batch mode)"}

    # Loan stats
    loans = pd.read_sql("SELECT * FROM loans", conn)

    # Anomaly count
    try:
        anomaly_count = pd.read_sql("SELECT COUNT(*) as cnt FROM anomalies", conn).iloc[0]["cnt"]
    except Exception:
        anomaly_count = 0

    # Consented interventions (defaults averted)
    try:
        consents_count = pd.read_sql("SELECT COUNT(*) as cnt FROM consents WHERE status = 'active'", conn).iloc[0]["cnt"]
    except Exception:
        consents_count = 0

    conn.close()

    # Merge data
    merged = users.merge(risk_scores, on="user_id", how="left")
    merged = merged.merge(features, on="user_id", how="left", suffixes=("", "_feat"))

    # ── Portfolio stats ──
    total_users = len(users)
    tier_dist = merged["risk_tier"].value_counts().to_dict() if "risk_tier" in merged.columns else {}

    # Risk score stats
    if "risk_score" in merged.columns:
        avg_risk = float(merged["risk_score"].mean())
        median_risk = float(merged["risk_score"].median())
        p90_risk = float(merged["risk_score"].quantile(0.9))
    else:
        avg_risk = median_risk = p90_risk = 0

    # Loan portfolio
    total_loan_exposure = int(loans["principal"].sum())
    total_monthly_emi = int(loans["emi_amount"].sum())
    avg_emi_to_income = float(merged["emi_to_income_ratio"].mean()) if "emi_to_income_ratio" in merged.columns else 0

    # Missed EMIs
    total_missed = int(merged["missed_emi_count"].sum()) if "missed_emi_count" in merged.columns else 0

    # At-risk exposure (total loan principal of at-risk + critical users)
    at_risk_users = merged[merged["risk_tier"].isin(["at_risk", "critical"])]["user_id"].tolist() if "risk_tier" in merged.columns else []
    at_risk_loans = loans[loans["user_id"].isin(at_risk_users)]
    at_risk_exposure = int(at_risk_loans["principal"].sum()) if len(at_risk_loans) > 0 else 0

    return {
        "timestamp": datetime.now().isoformat(),
        "total_users": total_users,
        "risk_distribution": {
            "healthy": tier_dist.get("healthy", 0),
            "at_risk": tier_dist.get("at_risk", 0),
            "critical": tier_dist.get("critical", 0),
        },
        "risk_percentages": {
            "healthy_pct": round(tier_dist.get("healthy", 0) / total_users * 100, 1),
            "at_risk_pct": round(tier_dist.get("at_risk", 0) / total_users * 100, 1),
            "critical_pct": round(tier_dist.get("critical", 0) / total_users * 100, 1),
        },
        "risk_scores": {
            "average": round(avg_risk, 1),
            "median": round(median_risk, 1),
            "p90": round(p90_risk, 1),
        },
        "loan_portfolio": {
            "total_exposure": total_loan_exposure,
            "total_monthly_emi_collection": total_monthly_emi,
            "at_risk_exposure": at_risk_exposure,
            "at_risk_exposure_pct": round(at_risk_exposure / max(total_loan_exposure, 1) * 100, 1),
            "avg_emi_to_income_ratio": round(avg_emi_to_income, 4),
        },
        "alerts": {
            "total_missed_emis": total_missed,
            "anomalous_transactions": int(anomaly_count),
            "users_needing_intervention": len(at_risk_users),
            "defaults_averted": int(consents_count),
        },
    }


def get_at_risk_users() -> list:
    """Get list of all at-risk and critical users with summary info."""
    conn = sqlite3.connect(_get_db_path())

    try:
        query = """
            SELECT u.user_id, u.name, u.city, u.occupation, u.monthly_income,
                   rs.risk_score, rs.risk_tier,
                   f.emi_to_income_ratio, f.missed_emi_count, f.days_until_zero,
                   f.income_drop_flag, f.balance_trend
            FROM users u
            JOIN risk_scores rs ON u.user_id = rs.user_id
            LEFT JOIN features f ON u.user_id = f.user_id
            WHERE rs.risk_tier IN ('at_risk', 'critical')
            ORDER BY rs.risk_score DESC
        """
        result = pd.read_sql(query, conn)
    except Exception:
        conn.close()
        return []

    conn.close()

    users_list = []
    for _, row in result.iterrows():
        users_list.append({
            "user_id": row["user_id"],
            "name": row["name"],
            "city": row["city"],
            "occupation": row["occupation"],
            "monthly_income": int(row["monthly_income"]),
            "risk_score": int(row["risk_score"]),
            "risk_tier": row["risk_tier"],
            "emi_to_income_ratio": round(float(row.get("emi_to_income_ratio", 0)), 4),
            "missed_emis": int(row.get("missed_emi_count", 0)),
            "days_until_zero": int(row.get("days_until_zero", 999)),
            "income_dropped": bool(row.get("income_drop_flag", 0)),
        })

    return users_list


def record_consent(user_id: str, plan_id: str) -> dict:
    """Record user's consent to a repayment plan and update risk score to reflect intervention."""
    conn = sqlite3.connect(_get_db_path())

    # Create consent table if not exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS consents (
            consent_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            plan_id TEXT NOT NULL,
            consented_at TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    consent_id = f"CONSENT_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    conn.execute(
        "INSERT INTO consents (consent_id, user_id, plan_id, consented_at, status) VALUES (?, ?, ?, ?, ?)",
        (consent_id, user_id, plan_id, datetime.now().isoformat(), "active")
    )

    # Update risk_scores so admin dashboard reflects "default averted"
    # Mark the user as having an active intervention — lower risk tier to "at_risk"
    # so they no longer show as "critical" but remain on the watchlist
    try:
        existing = pd.read_sql(
            "SELECT risk_score FROM risk_scores WHERE user_id = ?", conn, params=(user_id,)
        )
        if len(existing) > 0:
            current_score = existing.iloc[0]["risk_score"]
            # Cap score at 60 (top of at_risk band) to reflect intervention accepted
            new_score = min(int(current_score), 60)
            conn.execute(
                "UPDATE risk_scores SET risk_score = ?, risk_tier = 'at_risk' WHERE user_id = ?",
                (new_score, user_id)
            )
    except Exception:
        pass  # risk_scores table may not exist yet; non-fatal

    conn.commit()
    conn.close()

    return {
        "consent_id": consent_id,
        "user_id": user_id,
        "plan_id": plan_id,
        "status": "recorded",
        "timestamp": datetime.now().isoformat(),
    }


# ─── Batch Pipeline ──────────────────────────────────────────────────────────

def run_batch_pipeline():
    """
    Run the full batch pipeline:
    1. Feature engineering for all users
    2. Train/update models
    3. Compute risk scores for all users
    4. Generate portfolio summary
    """
    print("🚀 Project Aegis — Full Batch Pipeline")
    print("=" * 60)

    # Step 1: Feature Engineering
    print("\n[STEP 1/3] Running feature engineering...")
    features_df = compute_all_features()

    # Step 2: Risk Scores
    print("\n[STEP 2/3] Computing risk scores for all users...")
    risk_results = compute_all_risk_scores()

    # Step 3: Portfolio Summary
    print("\n[STEP 3/3] Generating portfolio summary...")
    summary = get_portfolio_summary()

    print(f"\n{'='*60}")
    print("📊 Portfolio Summary:")
    print(f"  Total Users: {summary.get('total_users', 'N/A')}")
    risk_dist = summary.get("risk_distribution", {})
    print(f"  🟢 Healthy:  {risk_dist.get('healthy', 0)}")
    print(f"  🟡 At-Risk:  {risk_dist.get('at_risk', 0)}")
    print(f"  🔴 Critical: {risk_dist.get('critical', 0)}")
    alerts = summary.get("alerts", {})
    print(f"  ⚠ Missed EMIs: {alerts.get('total_missed_emis', 0)}")
    print(f"  🚨 Users needing intervention: {alerts.get('users_needing_intervention', 0)}")

    # Save summary
    summary_path = os.path.join(ML_MODEL_DIR, "data", "portfolio_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  ✓ Portfolio summary saved: {summary_path}")

    print("\n✅ Batch pipeline complete!")
    return summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Project Aegis Pipeline")
    parser.add_argument("--test", action="store_true", help="Test with a single user")
    parser.add_argument("--user", type=str, help="Get assessment for a specific user")
    parser.add_argument("--batch", action="store_true", help="Run full batch pipeline")
    args = parser.parse_args()

    if args.test or args.user:
        uid = args.user or "USR0001"
        print(f"Testing single-user assessment for {uid}...")
        result = get_user_assessment(uid)
        print(json.dumps(result, indent=2, default=str))
    elif args.batch:
        run_batch_pipeline()
    else:
        # Default: run batch
        run_batch_pipeline()
