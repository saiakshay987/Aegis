"""
Project Aegis — Distress Classifier (Reproducible 15-Feature Random Forest + Calibration)
========================================================================================
Trains a calibrated multi-class classifier to predict borrower risk tier:
healthy / at_risk / critical.

Matches specification:
- 15 core features
- 350 trees, max_depth 12
- Probability calibration via CalibratedClassifierCV
- Repo-relative paths
- Exports train_dataset.csv and test_dataset.csv
"""

import os
import sys
import json
import sqlite3
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, f1_score, accuracy_score

BASE_DIR = Path(__file__).resolve().parent
ML_MODEL_DIR = BASE_DIR.parent
BACKEND_DIR = ML_MODEL_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ledger import get_db_path

DATA_DIR = ML_MODEL_DIR / "data"
MODEL_DIR = BASE_DIR
MODEL_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 15 Core Features matching feature_order.json & model audit
CORE_FEATURES = [
    "avg_monthly_income",
    "income_volatility",
    "income_trend",
    "months_since_last_income",
    "avg_monthly_essential_spend",
    "avg_monthly_discretionary_spend",
    "essential_to_income_ratio",
    "discretionary_to_income_ratio",
    "burn_rate_trend",
    "spending_spike_count",
    "current_balance",
    "avg_balance_30d",
    "min_balance_30d",
    "balance_trend",
    "days_until_zero",
]


def load_features():
    """Load feature table from SQLite using canonical path."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT * FROM features", conn)
    conn.close()
    return df


def train_model():
    """Train the distress classifier with 15 core features, 350 trees, depth 12, and calibration."""
    print("🧠 Project Aegis — Distress Classifier Training")
    print("=" * 60)

    # 1. Load data
    print("\n[1/5] Loading features from SQLite...")
    df = load_features()
    print(f"  ✓ {len(df)} samples loaded")

    # Verify all 15 core features are present
    missing = [c for c in CORE_FEATURES if c not in df.columns]
    if missing:
        raise ValueError(f"Missing core features in dataset: {missing}")

    X = df[CORE_FEATURES].fillna(0)
    y = df["risk_label"]

    print(f"  ✓ Using {len(CORE_FEATURES)} core features")
    print(f"\n📊 Class Distribution:")
    for label, count in y.value_counts().items():
        print(f"  {label:12s} → {count} ({count/len(y)*100:.1f}%)")

    # Encode labels
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    class_names = le.classes_

    # 2. Split data (80/20 train/test split)
    print("\n[2/5] Splitting data (80/20)...")
    X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
        X, y_encoded, df.index, test_size=0.2, random_state=42, stratify=y_encoded
    )
    print(f"  ✓ Train: {len(X_train)}, Test: {len(X_test)}")

    # Save train and test datasets
    train_df = df.loc[idx_train].copy()
    test_df = df.loc[idx_test].copy()
    train_path = DATA_DIR / "train_dataset.csv"
    test_path = DATA_DIR / "test_dataset.csv"
    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)
    print(f"  ✓ Saved train dataset: {train_path}")
    print(f"  ✓ Saved test dataset:  {test_path}")

    # 3. Train Random Forest (350 trees, max_depth 12)
    print("\n[3/5] Training Random Forest (350 trees, max_depth 12)...")
    base_rf = RandomForestClassifier(
        n_estimators=350,
        max_depth=12,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    base_rf.fit(X_train, y_train)

    # 4. Calibrate Classifier
    print("  Applying CalibratedClassifierCV (sigmoid calibration, 5-fold)...")
    calibrated_clf = CalibratedClassifierCV(
        estimator=base_rf,
        method="sigmoid",
        cv=5
    )
    calibrated_clf.fit(X_train, y_train)

    # 5. Evaluate
    print("\n[4/5] Evaluating calibrated model...")
    y_pred = calibrated_clf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average="weighted")

    print(f"\n  Accuracy:    {accuracy:.4f}")
    print(f"  F1 (weighted): {f1:.4f}")
    print(f"\n  Classification Report:")
    report = classification_report(y_test, y_pred, target_names=class_names)
    print(report)

    cm = confusion_matrix(y_test, y_pred)
    print(f"  Confusion Matrix:")
    print(f"  {cm}")

    # Cross-validation on base estimator
    print("\n  Cross-Validation (5-fold):")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(base_rf, X, y_encoded, cv=cv, scoring="f1_weighted")
    print(f"  CV F1 Scores: {cv_scores.round(4)}")
    print(f"  Mean CV F1:   {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # Feature importance from base Random Forest
    importances = base_rf.feature_importances_
    importance_df = pd.DataFrame({
        "feature": CORE_FEATURES,
        "importance": importances
    }).sort_values("importance", ascending=False)

    print(f"\n🔑 Top Features:")
    for _, row in importance_df.iterrows():
        bar = "█" * int(row["importance"] * 100)
        print(f"  {row['feature']:35s} {row['importance']:.4f} {bar}")

    # 6. Save model and artifacts
    print("\n[5/5] Saving model and artifacts...")
    model_path = MODEL_DIR / "distress_classifier.pkl"
    joblib.dump(calibrated_clf, model_path)
    print(f"  ✓ Calibrated Model saved: {model_path}")

    le_path = MODEL_DIR / "label_encoder.pkl"
    joblib.dump(le, le_path)
    print(f"  ✓ Label encoder saved:    {le_path}")

    feature_order_path = MODEL_DIR / "feature_order.json"
    with open(feature_order_path, "w") as f:
        json.dump(CORE_FEATURES, f, indent=2)
    print(f"  ✓ Feature order saved (15 features): {feature_order_path}")

    eval_report = {
        "model_type": "RandomForestClassifier + CalibratedClassifierCV",
        "n_features": len(CORE_FEATURES),
        "n_estimators": 350,
        "max_depth": 12,
        "calibration": "sigmoid",
        "accuracy": float(accuracy),
        "f1_weighted": float(f1),
        "cv_f1_mean": float(cv_scores.mean()),
        "cv_f1_std": float(cv_scores.std()),
        "class_names": class_names.tolist(),
        "confusion_matrix": cm.tolist(),
        "classification_report": classification_report(
            y_test, y_pred, target_names=class_names, output_dict=True
        ),
        "feature_importance": importance_df.to_dict(orient="records"),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "features": CORE_FEATURES,
    }

    report_path = MODEL_DIR / "evaluation_report.json"
    with open(report_path, "w") as f:
        json.dump(eval_report, f, indent=2)
    print(f"  ✓ Evaluation report saved: {report_path}")

    print("\n✅ Distress classifier training complete and fully reproducible!")
    return calibrated_clf, le


if __name__ == "__main__":
    train_model()
