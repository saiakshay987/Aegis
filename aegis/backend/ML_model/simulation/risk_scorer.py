"""
Project Aegis — Composite Risk Scorer
=======================================
Computes a unified 0-100 risk score for each user by combining:
  - ML distress probability (40%)
  - EMI-to-income ratio (20%)
  - Balance trend (15%)
  - Days until zero (15%)
  - Shock detection score (10%)

Usage:
    from simulation.risk_scorer import compute_risk_score
    result = compute_risk_score("USR0001")
"""

import pandas as pd
import numpy as np
import sqlite3
import os
import json
import joblib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(os.path.dirname(BASE_DIR), "data", "aegis.db")
MODELS_DIR = os.path.join(os.path.dirname(BASE_DIR), "models")


def _get_db_path():
    if os.path.exists(DB_PATH):
        return DB_PATH
    alt = os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), "data", "aegis.db")
    if os.path.exists(alt):
        return alt
    raise FileNotFoundError(f"Database not found at {DB_PATH}")


def _load_user_features(user_id):
    """Load pre-computed features for a user."""
    conn = sqlite3.connect(_get_db_path())
    features = pd.read_sql(
        "SELECT * FROM features WHERE user_id = ?",
        conn, params=(user_id,)
    )
    conn.close()
    return features.iloc[0] if len(features) > 0 else None


def _get_ml_probability(features_row):
    """Get distress probability from the trained classifier."""
    try:
        model_path = os.path.join(MODELS_DIR, "distress_classifier.pkl")
        feature_order_path = os.path.join(MODELS_DIR, "feature_order.json")
        le_path = os.path.join(MODELS_DIR, "label_encoder.pkl")

        if not all(os.path.exists(p) for p in [model_path, feature_order_path, le_path]):
            return None, None

        model = joblib.load(model_path)
        le = joblib.load(le_path)
        with open(feature_order_path) as f:
            feature_order = json.load(f)

        # Build feature vector in correct order
        feature_values = []
        for feat in feature_order:
            val = features_row.get(feat, 0)
            feature_values.append(0 if pd.isna(val) else val)

        X = np.array(feature_values).reshape(1, -1)
        probas = model.predict_proba(X)[0]
        predicted_class = le.inverse_transform(model.predict(X))[0]

        # Get probability of distress (at_risk + critical)
        class_names = le.classes_.tolist()
        distress_prob = 0
        for i, cls in enumerate(class_names):
            if cls in ("at_risk", "critical"):
                distress_prob += probas[i]

        return distress_prob, predicted_class

    except Exception as e:
        print(f"  ⚠ ML model not available: {e}")
        return None, None


def compute_risk_score(user_id):
    """
    Compute composite risk score (0-100) for a user.

    Components:
        - ML Distress Probability: 40% weight
        - EMI-to-Income Ratio:     20% weight
        - Balance Trend:           15% weight
        - Days Until Zero:         15% weight
        - Shock Detection:         10% weight

    Returns:
        {
            "user_id": "USR0001",
            "risk_score": 72,
            "risk_tier": "critical",
            "component_scores": {
                "ml_distress": {"raw": 0.85, "weighted": 34.0},
                "emi_burden": {"raw": 0.65, "weighted": 13.0},
                ...
            },
            "top_risk_factors": [
                "Income dropped 55% in last 2 months",
                "Balance declining at ₹8,000/week",
                ...
            ],
            "ml_predicted_class": "critical"
        }
    """
    features = _load_user_features(user_id)

    if features is None:
        return {"user_id": user_id, "error": "No features found. Run feature engineering first."}

    scores = {}

    # ── Component 1: ML Distress Probability (40%) ──
    ml_prob, ml_class = _get_ml_probability(features)
    if ml_prob is not None:
        ml_score = ml_prob * 100  # 0-100
    else:
        # Fallback: use rule-based estimate from features
        ml_score = 0
        if features.get("missed_emi_count", 0) >= 2:
            ml_score += 40
        if features.get("income_drop_flag", 0) == 1:
            ml_score += 30
        if features.get("emi_to_income_ratio", 0) > 0.5:
            ml_score += 20
        if features.get("balance_trend", 0) < -300:
            ml_score += 10
        ml_score = min(ml_score, 100)
        ml_class = None

    scores["ml_distress"] = {"raw": round(ml_score / 100, 4), "weighted": round(ml_score * 0.40, 2)}

    # ── Component 2: EMI-to-Income Ratio (20%) ──
    emi_ratio = features.get("emi_to_income_ratio", 0)
    # Map ratio to 0-100: 0-30% → safe, 30-50% → warning, 50%+ → danger
    if emi_ratio <= 0.30:
        emi_score = emi_ratio / 0.30 * 30  # 0-30
    elif emi_ratio <= 0.50:
        emi_score = 30 + (emi_ratio - 0.30) / 0.20 * 40  # 30-70
    else:
        emi_score = 70 + min((emi_ratio - 0.50) / 0.30, 1.0) * 30  # 70-100
    emi_score = min(emi_score, 100)

    scores["emi_burden"] = {"raw": round(emi_ratio, 4), "weighted": round(emi_score * 0.20, 2)}

    # ── Component 3: Balance Trend (15%) ──
    balance_trend = features.get("balance_trend", 0)
    # Negative trend = danger (₹/day)
    if balance_trend >= 0:
        trend_score = 0
    elif balance_trend >= -100:
        trend_score = abs(balance_trend) / 100 * 30
    elif balance_trend >= -500:
        trend_score = 30 + (abs(balance_trend) - 100) / 400 * 40
    else:
        trend_score = 70 + min((abs(balance_trend) - 500) / 500, 1.0) * 30
    trend_score = min(trend_score, 100)

    scores["balance_trend"] = {"raw": round(balance_trend, 2), "weighted": round(trend_score * 0.15, 2)}

    # ── Component 4: Days Until Zero (15%) ──
    days_to_zero = features.get("days_until_zero", 999)
    if days_to_zero >= 180:
        dtz_score = 0
    elif days_to_zero >= 90:
        dtz_score = (180 - days_to_zero) / 90 * 30
    elif days_to_zero >= 30:
        dtz_score = 30 + (90 - days_to_zero) / 60 * 40
    else:
        dtz_score = 70 + (30 - days_to_zero) / 30 * 30
    dtz_score = min(dtz_score, 100)

    scores["days_to_zero"] = {"raw": days_to_zero, "weighted": round(dtz_score * 0.15, 2)}

    # ── Component 5: Shock Detection (10%) ──
    shock_score = 0
    if features.get("max_single_medical_txn", 0) > 50000:
        shock_score += 40
    if features.get("medical_spend_spike", 1) > 3:
        shock_score += 25
    if features.get("income_drop_flag", 0) == 1:
        shock_score += 25
    if features.get("large_unexpected_debit", 0) > 2:
        shock_score += 10
    shock_score = min(shock_score, 100)

    scores["shock_detection"] = {"raw": round(shock_score / 100, 4), "weighted": round(shock_score * 0.10, 2)}

    # ── Composite Score ──
    total_score = sum(s["weighted"] for s in scores.values())
    total_score = round(min(max(total_score, 0), 100))

    # Map to tier
    if total_score <= 30:
        risk_tier = "healthy"
    elif total_score <= 60:
        risk_tier = "at_risk"
    else:
        risk_tier = "critical"

    # ── Top risk factors (human-readable explanations) ──
    risk_factors = []

    if features.get("income_drop_flag", 0) == 1:
        drop_pct = abs(features.get("income_drop_pct", 0)) * 100
        risk_factors.append(f"Income dropped {drop_pct:.0f}% month-over-month")

    if features.get("missed_emi_count", 0) > 0:
        risk_factors.append(f"{int(features['missed_emi_count'])} EMI payment(s) missed")

    if features.get("max_single_medical_txn", 0) > 30000:
        risk_factors.append(f"Medical expense spike of ₹{int(features['max_single_medical_txn']):,}")

    if balance_trend < -200:
        weekly_decline = abs(balance_trend) * 7
        risk_factors.append(f"Balance declining at ₹{weekly_decline:,.0f}/week")

    if emi_ratio > 0.50:
        risk_factors.append(f"EMI burden at {emi_ratio*100:.0f}% of income (danger zone)")

    if days_to_zero < 90:
        risk_factors.append(f"Projected to hit zero balance in {days_to_zero} days")

    if features.get("burn_rate_trend", 0) > 0.1:
        risk_factors.append("Monthly spending is accelerating")

    if features.get("income_volatility", 0) > 0.3:
        risk_factors.append(f"High income volatility (CV: {features['income_volatility']:.2f})")

    # Take top 5
    risk_factors = risk_factors[:5]

    return {
        "user_id": user_id,
        "risk_score": total_score,
        "risk_tier": risk_tier,
        "component_scores": scores,
        "top_risk_factors": risk_factors,
        "ml_predicted_class": ml_class,
    }


def compute_all_risk_scores():
    """Compute risk scores for all users and save to SQLite."""
    conn = sqlite3.connect(_get_db_path())
    users = pd.read_sql("SELECT user_id FROM users", conn)
    conn.close()

    results = []
    for _, row in users.iterrows():
        result = compute_risk_score(row["user_id"])
        if "error" not in result:
            results.append({
                "user_id": result["user_id"],
                "risk_score": result["risk_score"],
                "risk_tier": result["risk_tier"],
            })

    if results:
        scores_df = pd.DataFrame(results)
        conn = sqlite3.connect(_get_db_path())
        scores_df.to_sql("risk_scores", conn, if_exists="replace", index=False)
        conn.close()
        print(f"  ✓ Risk scores saved for {len(scores_df)} users")

        # Distribution
        print(f"\n📊 Risk Tier Distribution:")
        for tier, count in scores_df["risk_tier"].value_counts().items():
            print(f"  {tier:12s} → {count} ({count/len(scores_df)*100:.1f}%)")

    return results


if __name__ == "__main__":
    print("📊 Composite Risk Scorer — Test Run")
    print("=" * 60)

    for uid in ["USR0001", "USR0050", "USR0100", "USR0250"]:
        result = compute_risk_score(uid)
        if "error" in result:
            print(f"\n{uid}: {result['error']}")
            continue
        print(f"\n{'─'*50}")
        print(f"User: {result['user_id']}")
        emoji = {"healthy": "🟢", "at_risk": "🟡", "critical": "🔴"}.get(result["risk_tier"], "⚪")
        print(f"  Risk Score: {result['risk_score']}/100 {emoji} {result['risk_tier'].upper()}")
        print(f"  Components:")
        for name, data in result["component_scores"].items():
            bar = "█" * int(data["weighted"])
            print(f"    {name:20s} raw={data['raw']:>8}  weighted={data['weighted']:>5} {bar}")
        if result["top_risk_factors"]:
            print(f"  Risk Factors:")
            for rf in result["top_risk_factors"]:
                print(f"    ⚠ {rf}")
