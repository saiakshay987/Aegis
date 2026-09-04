"""
Project Aegis — Anomaly Detector (Isolation Forest)
====================================================
Unsupervised anomaly detection on transaction-level data to flag
unusual financial activity (shocks, sudden large debits, etc.)

Run: python train_anomaly_detector.py
"""

import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np
import sqlite3
import os
import os
import sys
from pathlib import Path
import json
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = str(Path(BASE_DIR).resolve().parents[1])
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from ledger import get_db_path

DB_PATH = get_db_path()
MODEL_DIR = os.path.join(BASE_DIR)
os.makedirs(MODEL_DIR, exist_ok=True)


def load_transactions():
    """Load transaction data from SQLite using canonical path."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    txns = pd.read_sql("SELECT * FROM transactions", conn)
    conn.close()

    txns["date"] = pd.to_datetime(txns["date"])
    return txns


def engineer_txn_features(txns):
    """Create transaction-level features for anomaly detection."""
    print("  Computing transaction-level features...")

    # Sort by user and date
    txns = txns.sort_values(["user_id", "date"]).reset_index(drop=True)

    # Basic amount features
    txns["is_debit"] = (txns["type"] == "debit").astype(int)
    txns["log_amount"] = np.log1p(txns["amount"])

    # Per-user statistics for relative comparison
    user_stats = txns.groupby("user_id").agg(
        mean_amount=("amount", "mean"),
        std_amount=("amount", "std"),
        median_amount=("amount", "median"),
    ).reset_index()
    user_stats["std_amount"] = user_stats["std_amount"].fillna(1)

    txns = txns.merge(user_stats, on="user_id", how="left")

    # Amount relative to user's norm
    txns["amount_zscore"] = (txns["amount"] - txns["mean_amount"]) / (txns["std_amount"] + 1)
    txns["amount_to_median_ratio"] = txns["amount"] / (txns["median_amount"] + 1)

    # Category encoding (high-risk categories get higher values)
    category_risk = {
        "salary": 0, "freelance_income": 0, "upi_received": 0,
        "rent": 1, "groceries": 1, "utilities": 1, "transport": 1,
        "insurance": 1, "education": 1, "subscriptions": 1,
        "dining": 2, "shopping": 2, "entertainment": 2,
        "personal_care": 2, "travel": 3,
        "medical": 4, "emi_payment": 3, "emi_missed": 5,
        "debt_repayment": 5, "cash_advance": 5, "emergency": 5,
    }
    txns["category_risk_level"] = txns["category"].map(category_risk).fillna(3)

    # Day of month (late-month transactions might signal cash crunch)
    txns["day_of_month"] = txns["date"].dt.day
    txns["is_month_end"] = (txns["day_of_month"] >= 25).astype(int)

    # Balance ratio (how much of balance this txn represents)
    txns["txn_to_balance_ratio"] = txns["amount"] / (txns["balance_after"] + txns["amount"] + 1)

    return txns


def train_anomaly_model():
    """Train Isolation Forest for anomaly detection."""
    print("🔍 Project Aegis — Anomaly Detector Training")
    print("=" * 60)

    print("\n[1/4] Loading transactions...")
    txns = load_transactions()
    print(f"  ✓ {len(txns):,} transactions loaded")

    # Only analyze debit transactions (anomalies are about spending)
    debit_txns = txns[txns["type"] == "debit"].copy()
    print(f"  ✓ {len(debit_txns):,} debit transactions for analysis")

    print("\n[2/4] Engineering transaction features...")
    debit_txns = engineer_txn_features(debit_txns)

    # Select features for anomaly detection
    anomaly_features = [
        "log_amount",
        "amount_zscore",
        "amount_to_median_ratio",
        "category_risk_level",
        "is_month_end",
        "txn_to_balance_ratio",
    ]

    X = debit_txns[anomaly_features].fillna(0)

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    print(f"  ✓ {len(anomaly_features)} features prepared")

    print("\n[3/4] Training Isolation Forest...")
    iso_forest = IsolationForest(
        n_estimators=200,
        contamination=0.08,  # Expect ~8% of transactions to be anomalous
        max_features=0.8,
        random_state=42,
        n_jobs=-1,
    )
    iso_forest.fit(X_scaled)

    # Score all transactions
    scores = iso_forest.decision_function(X_scaled)
    predictions = iso_forest.predict(X_scaled)

    # Anomalies are labeled as -1
    n_anomalies = (predictions == -1).sum()
    print(f"\n  Anomalies detected: {n_anomalies:,} / {len(debit_txns):,} ({n_anomalies/len(debit_txns)*100:.1f}%)")

    # Convert scores to 0-1 range (higher = more anomalous)
    anomaly_scores = 1 - (scores - scores.min()) / (scores.max() - scores.min() + 1e-8)
    debit_txns["anomaly_score"] = anomaly_scores
    debit_txns["is_anomaly"] = (predictions == -1).astype(int)

    # Show top anomalies
    print(f"\n🚨 Sample Anomalous Transactions:")
    top_anomalies = debit_txns.nlargest(10, "anomaly_score")
    for _, row in top_anomalies.iterrows():
        print(f"  [{row['user_id']}] ₹{row['amount']:>10,} | {row['category']:20s} | "
              f"Score: {row['anomaly_score']:.3f} | {row['description']}")

    # Category distribution of anomalies
    anomalous_txns = debit_txns[debit_txns["is_anomaly"] == 1]
    print(f"\n📊 Anomaly Category Distribution:")
    for cat, count in anomalous_txns["category"].value_counts().head(8).items():
        print(f"  {cat:25s} → {count:,}")

    print("\n[4/4] Saving model and artifacts...")

    # Save model
    model_path = os.path.join(MODEL_DIR, "anomaly_detector.pkl")
    joblib.dump(iso_forest, model_path)
    print(f"  ✓ Model saved: {model_path}")

    # Save scaler
    scaler_path = os.path.join(MODEL_DIR, "anomaly_scaler.pkl")
    joblib.dump(scaler, scaler_path)
    print(f"  ✓ Scaler saved: {scaler_path}")

    # Save feature order
    feature_path = os.path.join(MODEL_DIR, "anomaly_features.json")
    with open(feature_path, "w") as f:
        json.dump(anomaly_features, f)
    print(f"  ✓ Feature order saved: {feature_path}")

    # Save anomaly scores back to SQLite
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    # Create anomalies table with key transaction info
    anomaly_records = debit_txns[debit_txns["is_anomaly"] == 1][[
        "txn_id", "user_id", "date", "amount", "category", "description",
        "anomaly_score", "balance_after"
    ]].copy()
    anomaly_records["date"] = anomaly_records["date"].astype(str)
    anomaly_records.to_sql("anomalies", conn, if_exists="replace", index=False)
    conn.close()
    print(f"  ✓ Anomalies table saved to SQLite ({len(anomaly_records)} records)")

    # Evaluation summary
    eval_report = {
        "model_type": "IsolationForest",
        "n_estimators": 200,
        "contamination": 0.08,
        "total_transactions_analyzed": len(debit_txns),
        "anomalies_detected": int(n_anomalies),
        "anomaly_rate": float(n_anomalies / len(debit_txns)),
        "features_used": anomaly_features,
        "top_anomaly_categories": anomalous_txns["category"].value_counts().head(8).to_dict(),
        "score_distribution": {
            "min": float(anomaly_scores.min()),
            "max": float(anomaly_scores.max()),
            "mean": float(anomaly_scores.mean()),
            "p95": float(np.percentile(anomaly_scores, 95)),
        },
    }

    report_path = os.path.join(MODEL_DIR, "anomaly_evaluation.json")
    with open(report_path, "w") as f:
        json.dump(eval_report, f, indent=2)
    print(f"  ✓ Evaluation report saved: {report_path}")

    print("\n✅ Anomaly detector training complete!")
    return iso_forest, scaler


if __name__ == "__main__":
    train_anomaly_model()
