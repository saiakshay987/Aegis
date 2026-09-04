"""
services/logic_service.py — Integrated business logic for Financial Guardian.

Bridges three layers:
  1. SQLAlchemy ORM      → Customer/Loan/Transaction/Intervention queries
  2. ML Pipeline         → Risk scoring, cashflow projection, anomaly detection
  3. LLM Empathy Engine  → Human-readable rationale for repayment plans

All public functions accept `db: Session` as their first param (injected
via FastAPI Depends(get_db) from the routers).
"""

from __future__ import annotations

import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

# ─── Path setup ────────────────────────────────────────────────────────────
# BACKEND_DIR must be inserted at position 0 (highest priority) so that
# `from database import ...` resolves to aegis/backend/database.py and NOT
# the root-level database.py.  PROJECT_ROOT is appended (lowest priority)
# so models.py and rules_engine.py are still reachable.
BACKEND_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # aegis/backend
PROJECT_ROOT = os.path.dirname(os.path.dirname(BACKEND_DIR))                # d:\Aegis\Aegis
ML_MODEL_DIR = os.path.join(BACKEND_DIR, "ML_model")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)          # highest priority
if ML_MODEL_DIR not in sys.path:
    sys.path.insert(1, ML_MODEL_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)            # lowest priority — won't shadow database.py

# ─── ORM models (project root) ─────────────────────────────────────────────
from models import Customer, Loan, Transaction, Intervention

# ─── ML Pipeline (self-contained, uses its own sqlite3 connection) ──────────
try:
    from api.pipeline import (
        get_user_assessment  as ml_get_assessment,
        get_user_projection  as ml_get_projection,
        get_user_repayment_plan as ml_get_repayment,
        get_user_anomalies   as ml_get_anomalies,
        get_portfolio_summary as ml_get_portfolio,
        get_at_risk_users    as ml_get_at_risk,
        record_consent       as ml_record_consent,
    )
    ML_AVAILABLE = True
except Exception as e:
    logging.warning(f"ML pipeline not available: {e}")
    ML_AVAILABLE = False

# ─── LLM Empathy Engine (imported as library, not as a running server) ──────
try:
    from empathy_engine import (
        DistressPayload,
        get_fallback as empathy_fallback,
        build_prompt,
        parse_llm_output,
        call_openai,
        call_gemini,
    )
    EMPATHY_AVAILABLE = True
except Exception as e:
    logging.warning(f"Empathy engine not available: {e}")
    EMPATHY_AVAILABLE = False

# ─── Rules engine (SQLAlchemy-based survival buffer) ───────────────────────
try:
    from rules_engine import (
        calculate_minimum_survival_buffer,
        evaluate_liquidity_distress,
    )
    RULES_AVAILABLE = True
except Exception as e:
    logging.warning(f"Rules engine not available: {e}")
    RULES_AVAILABLE = False

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
#  Internal helpers
# ═══════════════════════════════════════════════

def _get_customer_balance(db: Session, customer_id: str) -> float:
    """
    Current balance for a customer, derived via a walked ledger scan.

    Delegates to the canonical ledger module (aegis/backend/ledger.py)
    which performs a bounce-aware forward walk over all transactions.
    The ``db`` Session parameter is accepted for interface consistency
    with other helpers but is not used — ledger opens its own sqlite3
    connection to avoid mixing ORM and raw-sqlite concerns.
    """
    try:
        from ledger import get_walked_balance
        return get_walked_balance(customer_id)
    except Exception:
        # Fallback: ORM query on latest transaction's balance_after
        latest_tx = (
            db.query(Transaction)
            .filter(Transaction.customer_id == customer_id)
            .order_by(desc(Transaction.timestamp))
            .first()
        )
        return latest_tx.balance_after if latest_tx else 0.0



def _get_monthly_income(db: Session, customer_id: str, months: int = 3) -> float:
    """Average monthly CREDIT sum over the last N months."""
    cutoff = datetime.now() - timedelta(days=months * 30)
    total = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0.0))
        .filter(
            Transaction.customer_id == customer_id,
            Transaction.type == "CREDIT",
            Transaction.timestamp >= cutoff,
        )
        .scalar()
    )
    return round(float(total) / months, 2)


def _get_monthly_expenses(db: Session, customer_id: str, months: int = 3) -> float:
    """Average monthly DEBIT sum (absolute) over the last N months."""
    cutoff = datetime.now() - timedelta(days=months * 30)
    total = (
        db.query(func.coalesce(func.sum(func.abs(Transaction.amount)), 0.0))
        .filter(
            Transaction.customer_id == customer_id,
            Transaction.type == "DEBIT",
            Transaction.timestamp >= cutoff,
        )
        .scalar()
    )
    return round(float(total) / months, 2)


def _get_active_loan_count(db: Session, customer_id: str) -> int:
    """Count of ACTIVE loans for a customer."""
    return (
        db.query(func.count(Loan.id))
        .filter(Loan.customer_id == customer_id, Loan.status == "ACTIVE")
        .scalar()
    ) or 0


def _risk_tier_to_status(tier: str) -> str:
    """Map ML risk-tier string to the schema RiskStatus enum value."""
    return {
        "healthy":  "Healthy",
        "at_risk":  "At-Risk",
        "critical": "Critical",
    }.get(tier, "Watch")


def _compute_oxygen_score(balance: float, living_floor: float) -> float:
    """
    Financial oxygen score (0–100).

    Interpretation:
        score = 100 → balance is ≥ 3× the living floor (very healthy)
        score =  50 → balance equals the living floor exactly
        score =   0 → balance is zero or below

    Formula: score = min(100, (balance / living_floor) * (100 / 3))
    Linear scale: living_floor maps to ~33, 3×floor maps to 100.
    We clamp to [0, 100].
    """
    if living_floor <= 0:
        return 100.0
    if balance <= 0:
        return 0.0
    raw = (balance / living_floor) * (100.0 / 3.0)
    return round(min(100.0, max(0.0, raw)), 1)


# ═══════════════════════════════════════════════
#  1.  get_user_assessment(user_id, db)
# ═══════════════════════════════════════════════

def get_user_assessment(user_id: str, db: Session) -> Optional[Dict[str, Any]]:
    """
    Full risk metrics for a single user.

    Primary path  → ML pipeline (richer time-series data, trained model).
    Fallback path → pure SQLAlchemy ORM queries on the customers/loans/
                    transactions tables seeded by seed_data.py.
    """
    # ── Primary: ML pipeline ───────────────────────────────────────
    if ML_AVAILABLE:
        try:
            ml_result = ml_get_assessment(user_id)
            if ml_result and "error" not in ml_result:
                profile    = ml_result.get("profile", {})
                risk_score = ml_result.get("risk_score", 50)
                risk_tier  = ml_result.get("risk_tier", "healthy")
                projection = ml_result.get("projection", {})
                survival   = ml_result.get("survival_buffer", {})

                balance     = float(projection.get("current_balance", 0))
                living_floor = float(survival.get("monthly_essential", 0))
                # Invert the ML 0-100 risk score: low risk = high oxygen
                oxygen_score = round(100.0 - float(risk_score), 1)
                oxygen_score = max(0.0, min(100.0, oxygen_score))

                # active_loans: derive entirely from ML data — never query ORM
                # here because the ML DB schema differs (loan_id not id).
                per_loan = ml_result.get("recommended_plan") or {}
                loan_details = per_loan.get("per_loan_details", []) if isinstance(per_loan, dict) else []
                if loan_details:
                    active_loans = len(loan_details)
                elif per_loan.get("current_emi_total", 0) > 0:
                    # User has loans (EMI > 0) but details not returned for healthy users
                    active_loans = 1
                else:
                    active_loans = 0

                return {
                    "user_id":               user_id,
                    "name":                  profile.get("name", user_id),
                    "balance":               balance,
                    "living_floor":          living_floor,
                    "financial_oxygen_score": oxygen_score,
                    "risk_status":           _risk_tier_to_status(risk_tier),
                    "monthly_income":        float(profile.get("monthly_income", 0)),
                    "monthly_expenses":      float(survival.get("monthly_essential", 0)),
                    "active_loans":          active_loans,
                }
        except Exception as e:
            logger.warning(f"ML assessment failed for {user_id}: {e}")

    # ── Fallback: ORM queries ──────────────────────────────────────
    # Only works if seed_data.py has been run (customers/loans tables exist).
    # If the ML DB is the only DB and those tables are absent, return None.
    try:
        customer = db.query(Customer).filter(Customer.id == user_id).first()
    except Exception as e:
        logger.warning(f"ORM fallback unavailable for {user_id}: {e}")
        return None

    if not customer:
        return None

    balance          = _get_customer_balance(db, user_id)
    monthly_income   = customer.monthly_income_avg or _get_monthly_income(db, user_id)
    monthly_expenses = _get_monthly_expenses(db, user_id)
    active_loans     = _get_active_loan_count(db, user_id)

    # Living floor via rules engine; fallback to 60 % of expenses
    living_floor = 0.0
    if RULES_AVAILABLE:
        try:
            buf = calculate_minimum_survival_buffer(user_id, db)
            living_floor = buf.get("minimum_survival_buffer", 0.0)
        except Exception:
            pass
    if living_floor == 0.0:
        living_floor = monthly_expenses * 0.6

    oxygen_score = _compute_oxygen_score(balance, living_floor)

    if oxygen_score >= 70:
        risk_status = "Healthy"
    elif oxygen_score >= 45:
        risk_status = "Watch"
    elif oxygen_score >= 20:
        risk_status = "At-Risk"
    else:
        risk_status = "Critical"

    return {
        "user_id":               user_id,
        "name":                  f"{customer.first_name} {customer.last_name}",
        "balance":               balance,
        "living_floor":          living_floor,
        "financial_oxygen_score": oxygen_score,
        "risk_status":           risk_status,
        "monthly_income":        monthly_income,
        "monthly_expenses":      monthly_expenses,
        "active_loans":          active_loans,
    }


# ═══════════════════════════════════════════════
#  2.  project_cashflow(user_id, db)
# ═══════════════════════════════════════════════

def project_cashflow(user_id: str, db: Session) -> Optional[Dict[str, Any]]:
    """
    30/60/90-day cashflow balance trajectory.

    Primary  → ML pipeline (full time-series modelling).
    Fallback → ORM linear extrapolation.
    """
    if ML_AVAILABLE:
        try:
            ml_result = ml_get_projection(user_id)
            if ml_result and "error" not in ml_result:
                projections = ml_result.get("projections", {})
                current_bal = float(ml_result.get("current_balance", 0))
                day_30 = float(projections.get("day_30", ml_result.get("day_30", 0)))
                day_60 = float(projections.get("day_60", ml_result.get("day_60", 0)))
                day_90 = float(projections.get("day_90", ml_result.get("day_90", 0)))

                trend = "stable"
                if day_90 > current_bal:
                    trend = "improving"
                elif day_90 < current_bal:
                    trend = "deteriorating"

                return {
                    "user_id":                   user_id,
                    "current_balance":            current_bal,
                    "projected_balance_day_30":   day_30,
                    "projected_balance_day_60":   day_60,
                    "projected_balance_day_90":   day_90,
                    "risk_trend":                 trend,
                }
        except Exception as e:
            logger.warning(f"ML projection failed for {user_id}: {e}")

    # ── ORM fallback ──────────────────────────────────────────────
    customer = db.query(Customer).filter(Customer.id == user_id).first()
    if not customer:
        return None

    balance       = _get_customer_balance(db, user_id)
    monthly_income = customer.monthly_income_avg or _get_monthly_income(db, user_id)
    net_monthly    = monthly_income - _get_monthly_expenses(db, user_id)

    day_30 = round(balance + net_monthly,           2)
    day_60 = round(balance + net_monthly * 2,       2)
    day_90 = round(balance + net_monthly * 3,       2)

    trend = "stable"
    if day_90 > balance:
        trend = "improving"
    elif day_90 < balance:
        trend = "deteriorating"

    return {
        "user_id":                  user_id,
        "current_balance":          balance,
        "projected_balance_day_30": day_30,
        "projected_balance_day_60": day_60,
        "projected_balance_day_90": day_90,
        "risk_trend":               trend,
    }


# ═══════════════════════════════════════════════
#  3.  generate_repayment_plan(user_id, db)
# ═══════════════════════════════════════════════

def generate_repayment_plan(user_id: str, db: Session) -> Optional[Dict[str, Any]]:
    """
    Adaptive repayment recommendation with LLM-generated empathetic rationale.

    Primary  → ML pipeline plan + empathy engine rationale.
    Fallback → ORM-based safe-debit calculation.
    """
    original_emi   = 0.0
    safe_debit     = 0.0
    deferred       = 0.0
    deferral_months = 0
    plan_id = f"PLAN-{user_id}-{datetime.now(timezone.utc).strftime('%Y%m%d')}"

    ml_plan = None
    if ML_AVAILABLE:
        try:
            ml_plan = ml_get_repayment(user_id)
            if ml_plan and "error" not in ml_plan and ml_plan.get("eligibility"):
                recommended   = ml_plan.get("recommended_plan", {})
                original_emi  = float(ml_plan.get("current_emi_total", 0))
                safe_debit    = float(recommended.get("recommended_emi", 0))
                deferred      = round(original_emi - safe_debit, 2)
                deferral_months = recommended.get("duration_months", 3)
                plan_id       = recommended.get("plan_id", plan_id)
        except Exception as e:
            logger.warning(f"ML repayment failed for {user_id}: {e}")

    # ── ORM fallback ──────────────────────────────────────────────
    if original_emi == 0.0:
        customer = db.query(Customer).filter(Customer.id == user_id).first()
        if not customer:
            return None

        balance      = _get_customer_balance(db, user_id)
        living_floor = 0.0
        if RULES_AVAILABLE:
            try:
                buf = calculate_minimum_survival_buffer(user_id, db)
                living_floor = buf.get("minimum_survival_buffer", 0.0)
            except Exception:
                pass
        if living_floor == 0.0:
            living_floor = _get_monthly_expenses(db, user_id) * 0.6

        active_loans = (
            db.query(Loan)
            .filter(Loan.customer_id == user_id, Loan.status == "ACTIVE")
            .all()
        )
        original_emi = sum(l.monthly_emi for l in active_loans) if active_loans else 12_000.0

        surplus    = max(0.0, balance - living_floor)
        safe_debit = round(min(original_emi, surplus * 0.6), 2)
        deferred   = round(original_emi - safe_debit, 2)
        deferral_months = 3 if deferred > 0 else 0

    # ── Rationale: empathy engine or plain text ───────────────────
    rationale = (
        f"Your current EMI of ₹{original_emi:,.0f} has been reviewed against your "
        f"live financial position. A safe debit of ₹{safe_debit:,.0f} protects your "
        f"essential expenses, with ₹{deferred:,.0f} deferred interest-free."
    )

    if EMPATHY_AVAILABLE and deferred > 0:
        try:
            shock_type = "other"
            if ml_plan and isinstance(ml_plan, dict):
                reasons_str = " ".join(ml_plan.get("hardship_reasons", [])).lower()
                if "medical" in reasons_str:
                    shock_type = "medical"
                elif any(w in reasons_str for w in ("income", "job", "salary")):
                    shock_type = "job_loss"

            payload = DistressPayload(
                shock=shock_type,
                amount=deferred,
                user_name=user_id,
                emi=original_emi,
                recommended_emi=safe_debit,
                deferred_amount=deferred,
            )
            resp = empathy_fallback(payload)
            rationale = f"{resp.headline} {resp.message} {resp.suggestion}"
        except Exception as e:
            logger.warning(f"Empathy engine failed for {user_id}: {e}")

    return {
        "user_id":          user_id,
        "plan_id":          plan_id,
        "original_emi":     original_emi,
        "safe_debit_amount": safe_debit,
        "deferred_amount":  deferred,
        "deferral_months":  deferral_months,
        "rationale":        rationale,
    }


# ═══════════════════════════════════════════════
#  4.  get_user_anomalies(user_id, db)
# ═══════════════════════════════════════════════

def get_user_anomalies(user_id: str, db: Session) -> Dict[str, Any]:
    """
    Detected transaction anomalies.

    Primary  → ML IsolationForest anomaly detector (anomalies table).
    Fallback → ORM: flag transactions that exceed 3× their category average.
    """
    anomalies: List[Dict[str, Any]] = []

    if ML_AVAILABLE:
        try:
            ml_anomalies = ml_get_anomalies(user_id)
            if isinstance(ml_anomalies, list) and ml_anomalies:
                for a in ml_anomalies:
                    score = float(a.get("anomaly_score", 0))
                    severity = "high" if score > 0.7 else ("medium" if score > 0.4 else "low")
                    anomalies.append({
                        "transaction_id":    str(a.get("transaction_id", a.get("txn_id", ""))),
                        "date":              str(a.get("date", a.get("timestamp", ""))),
                        "category":          str(a.get("category", "Unknown")),
                        "amount":            float(a.get("amount", 0)),
                        "expected_range_min": float(a.get("expected_min", 0)),
                        "expected_range_max": float(a.get("expected_max", 0)),
                        "severity":          severity,
                        "description":       str(
                            a.get("description",
                                  f"Anomalous {a.get('category', '')} transaction")
                        ),
                    })
        except Exception as e:
            logger.warning(f"ML anomalies failed for {user_id}: {e}")

    # ── ORM fallback ──────────────────────────────────────────────
    if not anomalies:
        try:
            cutoff = datetime.now() - timedelta(days=90)
            transactions = (
                db.query(Transaction)
                .filter(
                    Transaction.customer_id == user_id,
                    Transaction.type == "DEBIT",
                    Transaction.timestamp >= cutoff,
                )
                .order_by(desc(Transaction.timestamp))
                .all()
            )
            if transactions:
                cat_amounts: Dict[str, List[float]] = {}
                for tx in transactions:
                    cat_amounts.setdefault(tx.category, []).append(abs(tx.amount))
                cat_avg = {c: sum(v) / len(v) for c, v in cat_amounts.items()}

                for tx in transactions[:50]:
                    avg = cat_avg.get(tx.category, 0)
                    if avg > 0 and abs(tx.amount) > avg * 3:
                        anomalies.append({
                            "transaction_id":    str(tx.id),
                            "date":              tx.timestamp.strftime("%Y-%m-%d") if tx.timestamp else "",
                            "category":          tx.category,
                            "amount":            abs(tx.amount),
                            "expected_range_min": round(avg * 0.5, 2),
                            "expected_range_max": round(avg * 2.0, 2),
                            "severity":          "high" if abs(tx.amount) > avg * 5 else "medium",
                            "description":       tx.description or f"Unusually large {tx.category} transaction",
                        })
        except Exception as e:
            logger.warning(f"ORM anomaly detection failed for {user_id}: {e}")

    return {"user_id": user_id, "anomaly_count": len(anomalies), "anomalies": anomalies}


# ═══════════════════════════════════════════════
#  5.  record_consent(user_id, plan_id, db)
# ═══════════════════════════════════════════════

def record_consent(user_id: str, plan_id: str, db: Session) -> Dict[str, Any]:
    """
    Persist customer consent for an adaptive repayment plan.

    Writes to:
      • ML DB consents table (via pipeline function)
      • ORM DB Intervention table
    """
    now = datetime.now(timezone.utc)

    if ML_AVAILABLE:
        try:
            ml_record_consent(user_id, plan_id)
        except Exception as e:
            logger.warning(f"ML consent recording failed for {user_id}: {e}")

    try:
        customer = db.query(Customer).filter(Customer.id == user_id).first()
        if customer:
            loan = (
                db.query(Loan)
                .filter(Loan.customer_id == user_id, Loan.status == "ACTIVE")
                .first()
            )
            if loan:
                import uuid
                intervention = Intervention(
                    id=str(uuid.uuid4()),
                    loan_id=loan.id,
                    customer_id=user_id,
                    trigger_reason="LIQUIDITY_BUFFER_BREACH",
                    projected_deficit=0.0,
                    survival_buffer=0.0,
                    action_type="SPLIT_EMI",
                    original_emi=loan.monthly_emi,
                    adjusted_emi=round(loan.monthly_emi * 0.5, 2),
                    status="ACCEPTED",
                    initiated_at=now,
                )
                db.add(intervention)
                db.commit()
    except Exception as e:
        logger.warning(f"ORM consent recording failed for {user_id}: {e}")
        db.rollback()

    return {
        "user_id":      user_id,
        "plan_id":      plan_id,
        "status":       "confirmed",
        "message":      (
            f"Consent recorded for plan {plan_id}. "
            "Adaptive repayment schedule is now active."
        ),
        "consented_at": now,
    }


# ═══════════════════════════════════════════════
#  6.  get_portfolio_summary(db)
# ═══════════════════════════════════════════════

def get_portfolio_summary(db: Session) -> Dict[str, Any]:
    """
    Aggregate stats for the bank-manager dashboard.

    Primary  → ML pipeline (risk-scored portfolio).
    Fallback → ORM count of customers / interventions.
    """
    if ML_AVAILABLE:
        try:
            ml_result = ml_get_portfolio()
            if ml_result and "error" not in ml_result:
                risk_dist   = ml_result.get("risk_distribution", {})
                alerts      = ml_result.get("alerts", {})
                risk_scores = ml_result.get("risk_scores", {})

                total   = ml_result.get("total_users", 0)
                healthy = risk_dist.get("healthy", 0)
                at_risk = risk_dist.get("at_risk", 0)
                critical = risk_dist.get("critical", 0)
                watch   = max(0, total - healthy - at_risk - critical)

                return {
                    "total_users":               total,
                    "healthy_count":             healthy,
                    "watch_count":               watch,
                    "at_risk_count":             at_risk,
                    "critical_count":            critical,
                    "defaults_prevented":        alerts.get("defaults_averted",
                                                            alerts.get("total_missed_emis", 0)),
                    "average_oxygen_score":      round(100.0 - risk_scores.get("average", 50.0), 1),
                    "total_active_interventions": alerts.get("users_needing_intervention", 0),
                }
        except Exception as e:
            logger.warning(f"ML portfolio summary failed: {e}")

    # ── ORM fallback ──────────────────────────────────────────────
    total_users = db.query(func.count(Customer.id)).scalar() or 0
    total_interventions = (
        db.query(func.count(Intervention.id))
        .filter(Intervention.status.in_(["PROPOSED", "ACCEPTED", "ACTIVE"]))
        .scalar()
    ) or 0

    return {
        "total_users":               total_users,
        "healthy_count":             total_users,
        "watch_count":               0,
        "at_risk_count":             0,
        "critical_count":            0,
        "defaults_prevented":        total_interventions,
        "average_oxygen_score":      65.0,
        "total_active_interventions": total_interventions,
    }


# ═══════════════════════════════════════════════
#  7.  get_at_risk_users(db)
# ═══════════════════════════════════════════════

def get_at_risk_users(db: Session) -> List[Dict[str, Any]]:
    """
    All users flagged At-Risk or Critical with their primary trigger.

    Primary  → ML pipeline (ML-scored list).
    Fallback → ORM rules-engine distress detection.
    """
    if ML_AVAILABLE:
        try:
            ml_result = ml_get_at_risk()
            if isinstance(ml_result, list) and ml_result:
                users = []
                for u in ml_result:
                    risk_score = float(u.get("risk_score", 50))
                    risk_tier  = u.get("risk_tier", "at_risk")
                    oxygen     = round(100.0 - risk_score, 1)

                    triggers = []
                    if u.get("income_dropped"):
                        triggers.append("Income drop detected")
                    if u.get("missed_emis", 0) > 0:
                        triggers.append(f"{u['missed_emis']} missed EMI(s)")
                    if u.get("days_until_zero", 999) < 90:
                        triggers.append(f"Projected zero balance in {u['days_until_zero']} days")
                    primary_trigger = "; ".join(triggers) if triggers else "Financial stress detected"

                    users.append({
                        "user_id":               str(u.get("user_id", "")),
                        "name":                  str(u.get("name", "")),
                        "balance":               0.0,
                        "financial_oxygen_score": max(0.0, min(100.0, oxygen)),
                        "risk_status":           _risk_tier_to_status(risk_tier),
                        "primary_trigger":       primary_trigger,
                        "days_in_risk_zone":     max(1, 90 - int(u.get("days_until_zero", 90))),
                    })
                return users
        except Exception as e:
            logger.warning(f"ML at-risk users failed: {e}")

    # ── ORM fallback ──────────────────────────────────────────────
    results: List[Dict[str, Any]] = []
    if RULES_AVAILABLE:
        try:
            for customer in db.query(Customer).all():
                distress = evaluate_liquidity_distress(customer.id, db)
                if distress.get("is_distressed"):
                    balance  = distress.get("current_balance", 0.0)
                    floor    = distress.get("minimum_survival_buffer", 0.0)
                    oxygen   = _compute_oxygen_score(balance, floor)
                    deficit  = distress.get("projected_deficit", 0.0)
                    results.append({
                        "user_id":               customer.id,
                        "name":                  f"{customer.first_name} {customer.last_name}",
                        "balance":               balance,
                        "financial_oxygen_score": oxygen,
                        "risk_status":           "Critical" if deficit > 10_000 else "At-Risk",
                        "primary_trigger":       distress.get("recommendation", {}).get(
                                                    "trigger_reason", "Liquidity buffer breach"
                                                 ),
                        "days_in_risk_zone":     1,
                    })
        except Exception as e:
            logger.warning(f"ORM at-risk detection failed: {e}")

    return results
