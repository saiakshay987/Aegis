"""
Project Aegis — Distress Classifier (Random Forest)
====================================================
Trains a multi-class classifier to predict user risk tier:
healthy / at_risk / critical

Run: python train_distress_classifier.py
"""

import pandas as pd
import numpy as np
import sqlite3
import os
import json
import joblib
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    classification_report, confusion_matrix, f1_score, accuracy_score
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(os.path.dirname(BASE_DIR), "data", "aegis.db")
MODEL_DIR = os.path.join(BASE_DIR)
os.makedirs(MODEL_DIR, exist_ok=True)


def load_features():
    """Load feature table from SQLite."""
    # Try multiple paths for DB
    db_path = DB_PATH
    if not os.path.exists(db_path):
        db_path = os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), "data", "aegis.db")
    if not os.path.exists(db_path):
        # Try relative to ML_model
        db_path = os.path.join(os.path.dirname(BASE_DIR), "data", "aegis.db")

    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT * FROM features", conn)
    conn.close()
    return df


def train_model():
    """Train the distress classifier."""
    print("🧠 Project Aegis — Distress Classifier Training")
    print("=" * 60)

    # Load data
    print("\n[1/5] Loading features...")
    df = load_features()
    print(f"  ✓ {len(df)} samples loaded")

    # Prepare features and labels
    feature_cols = [c for c in df.columns if c not in ("user_id", "risk_label")]
    X = df[feature_cols].fillna(0)
    y = df["risk_label"]

    print(f"  ✓ {len(feature_cols)} features")
    print(f"\n📊 Class Distribution:")
    for label, count in y.value_counts().items():
        print(f"  {label:12s} → {count} ({count/len(y)*100:.1f}%)")

    # Encode labels
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    class_names = le.classes_

    # Split data
    print("\n[2/5] Splitting data (80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
    )
    print(f"  ✓ Train: {len(X_train)}, Test: {len(X_test)}")

    # Train Random Forest
    print("\n[3/5] Training Random Forest...")
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    rf.fit(X_train, y_train)

    # Evaluate
    print("\n[4/5] Evaluating model...")
    y_pred = rf.predict(X_test)
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

    # Cross-validation
    print("\n  Cross-Validation (5-fold):")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(rf, X, y_encoded, cv=cv, scoring="f1_weighted")
    print(f"  CV F1 Scores: {cv_scores.round(4)}")
    print(f"  Mean CV F1:   {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # Feature importance
    importances = rf.feature_importances_
    importance_df = pd.DataFrame({
        "feature": feature_cols,
        "importance": importances
    }).sort_values("importance", ascending=False)

    print(f"\n🔑 Top 10 Features:")
    for _, row in importance_df.head(10).iterrows():
        bar = "█" * int(row["importance"] * 100)
        print(f"  {row['feature']:35s} {row['importance']:.4f} {bar}")

    # Save model
    print("\n[5/5] Saving model and artifacts...")
    model_path = os.path.join(MODEL_DIR, "distress_classifier.pkl")
    joblib.dump(rf, model_path)
    print(f"  ✓ Model saved: {model_path}")

    # Save label encoder
    le_path = os.path.join(MODEL_DIR, "label_encoder.pkl")
    joblib.dump(le, le_path)
    print(f"  ✓ Label encoder saved: {le_path}")

    # Save feature order (critical for inference)
    feature_order_path = os.path.join(MODEL_DIR, "feature_order.json")
    with open(feature_order_path, "w") as f:
        json.dump(feature_cols, f)
    print(f"  ✓ Feature order saved: {feature_order_path}")

    # Save evaluation report
    eval_report = {
        "model_type": "RandomForestClassifier",
        "n_estimators": 200,
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
    }

    report_path = os.path.join(MODEL_DIR, "evaluation_report.json")
    with open(report_path, "w") as f:
        json.dump(eval_report, f, indent=2)
    print(f"  ✓ Evaluation report saved: {report_path}")

    print("\n✅ Distress classifier training complete!")
    return rf, le


if __name__ == "__main__":
    train_model()
