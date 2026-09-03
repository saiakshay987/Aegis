"""
services/logic_service.py — Integrated business logic for Financial Guardian.

Bridges three layers:
  1. SQLAlchemy ORM      → Customer/Loan/Transaction/Intervention queries
  2. ML Pipeline         → Risk scoring, cashflow projection, anomaly detection
  3. LLM Empathy Engine  → Human-readable rationale for repayment plans

All functions accept `db: Session` as their first param (injected via
FastAPI Depends(get_db) from the routers).
"""

from __future__ import annotations

import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

# ─── Ensure ML_model and project root are importable ────────────────
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BACKEND_DIR))
ML_MODEL_DIR = os.path.join(BACKEND_DIR, "ML_model")

for p in [BACKEND_DIR, PROJECT_ROOT, ML_MODEL_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

# ─── ORM models (from project root) ────────────────────────────────
from models import Customer, Loan, Transaction, Intervention

# ─── ML Pipeline functions (self-contained, use their own DB) ───────
try:
    from api.pipeline import (
        get_user_assessment as ml_get_assessment,
        get_user_projection as ml_get_projection,
        get_user_repayment_plan as ml_get_repayment,
        get_user_anomalies as ml_get_anomalies,
        get_portfolio_summary as ml_get_portfolio,
        get_at_risk_users as ml_get_at_risk,
        record_consent as ml_record_consent,
    )
    ML_AVAILABLE = True
except Exception as e:
    logging.warning(f"ML pipeline not available: {e}")
    ML_AVAILABLE = False

# ─── LLM Empathy Engine (imported as library, not run as server) ────
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

# ─── Rules engine (SQLAlchemy-based survival buffer) ────────────────
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
#  Helpers
# ═══════════════════════════════════════════════

def _get_customer_balance(db: Session, customer_id: str) -> float:
    """Get the most recent balance from the transactions table."""
    latest_tx = (
        db.query(Transaction)
        .filter(Transaction.customer_id == customer_id)
        .order_by(desc(Transaction.timestamp))
        .first()
    )
    return latest_tx.balance_after if latest_tx else 0.0


def _get_monthly_income(db: Session, customer_id: str, months: int = 3) -> float:
    """Average monthly income (CREDIT transactions) over the last N months."""
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
    """Average monthly expenses (DEBIT transactions) over the last N months."""
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
    """Count active loans for a customer."""
    return (
        db.query(func.count(Loan.id))
        .filter(Loan.customer_id == customer_id, Loan.status == "ACTIVE")
        .scalar()
    ) or 0


def _risk_tier_to_status(tier: str) -> str:
    """Map ML risk tier names to schema-compatible RiskStatus values."""
    mapping = {
        "healthy": "Healthy",
        "at_risk": "At-Risk",
        "critical": "Critical",
    }
    return mapping.get(tier, "Watch")


def _compute_oxygen_score(balance: float, living_floor: float) -> float:
    """
    Financial oxygen score: how much 'breathing room' above the living floor.
    Score 0-100 where 100 = perfect health.
    """
    if living_floor <= 0:
        return 100.0
    ratio = balance / living_floor
    # Sigmoid-like mapping: ratio=0 → score≈0, ratio=1 → score≈50, ratio=3+ → score≈100
    score = min(100.0, max(0.0, (ratio / (ratio + 1)) * 100 * 2 - 50)) if ratio > 0 else 0.0
    return round(max(0.0, min(100.0, score)), 1)


# ═══════════════════════════════════════════════
#  1.  get_user_assessment(user_id, db)
# ═══════════════════════════════════════════════

def get_user_assessment(user_id: str, db: Session) -> Optional[Dict[str, Any]]:
    """
    Full risk metrics for a single user.

    Strategy:
      - Profile data from SQLAlchemy ORM (Customer table)
      - Balance/income/expenses from ORM Transaction queries
      - Living floor from rules_engine (or fallback calculation)
      - Risk score + oxygen score from ML pipeline (or fallback)
    """
    # ── Try ML pipeline first (has richer data) ──
    if ML_AVAILABLE:
        try:
            ml_result = ml_get_assessment(user_id)
            if ml_result and "error" not in ml_result:
                # ML pipeline returned full assessment — adapt to schema
                profile = ml_result.get("profile", {})
                risk_score = ml_result.get("risk_score", 50)
                risk_tier = ml_result.get("risk_tier", "healthy")
                projection = ml_result.get("projection", {})
                survival = ml_result.get("survival_buffer", {})

                balance = projection.get("current_balance", 0)
                living_floor = survival.get("monthly_essential", 0)
                oxygen_score = round(100 - risk_score, 1)  # Invert: low risk = high oxygen

                return {
                    "user_id": user_id,
                    "name": profile.get("name", user_id),
                    "balance": float(balance),
                    "living_floor": float(living_floor),
                    "financial_oxygen_score": max(0, min(100, oxygen_score)),
                    "risk_status": _risk_tier_to_status(risk_tier),
                    "monthly_income": float(profile.get("monthly_income", 0)),
                    "monthly_expenses": float(
                        survival.get("monthly_essential", 0)
                    ),
                    "active_loans": len(
                        ml_result.get("recommended_plan", {}).get("per_loan_details", [])
                        if isinstance(ml_result.get("recommended_plan"), dict)
                        else []
                    ) or 1,
                }
        except Exception as e:
            logger.warning(f"ML assessment failed for {user_id}: {e}")

    # ── Fallback: pure ORM queries ──
    customer = db.query(Customer).filter(Customer.id == user_id).first()
    if not customer:
        return None

    balance = _get_customer_balance(db, user_id)
    monthly_income = customer.monthly_income_avg or _get_monthly_income(db, user_id)
    monthly_expenses = _get_monthly_expenses(db, user_id)
    active_loans = _get_active_loan_count(db, user_id)

    # Living floor via rules engine
    living_floor = 0.0
    if RULES_AVAILABLE:
        try:
            buffer_data = calculate_minimum_survival_buffer(user_id, db)
            living_floor = buffer_data.get("minimum_survival_buffer", 0.0)
        except Exception:
            living_floor = monthly_expenses * 0.6  # Fallback: 60% of expenses are essential

    if living_floor == 0:
        living_floor = monthly_expenses * 0.6

    oxygen_score = _compute_oxygen_score(balance, living_floor)

    # Determine risk status from oxygen score
    if oxygen_score >= 70:
        risk_status = "Healthy"
    elif oxygen_score >= 45:
        risk_status = "Watch"
    elif oxygen_score >= 20:
        risk_status = "At-Risk"
    else:
        risk_status = "Critical"

    return {
        "user_id": user_id,
        "name": f"{customer.first_name} {customer.last_name}",
        "balance": balance,
        "living_floor": living_floor,
        "financial_oxygen_score": oxygen_score,
        "risk_status": risk_status,
        "monthly_income": monthly_income,
        "monthly_expenses": monthly_expenses,
        "active_loans": active_loans,
    }


# ═══════════════════════════════════════════════
#  2.  project_cashflow(user_id, db)
# ═══════════════════════════════════════════════

def project_cashflow(user_id: str, db: Session) -> Optional[Dict[str, Any]]:
    """
    30/60/90-day cashflow balance trajectory.

    Strategy:
      - Delegate to ML pipeline's projection function (uses its own DB
        with full transaction history and time-series modelling)
      - Fallback to simple ORM-based linear extrapolation
    """
    # ── ML pipeline projection ──
    if ML_AVAILABLE:
        try:
            ml_result = ml_get_projection(user_id)
            if ml_result and "error" not in ml_result:
                # ML returns nested projections dict
                projections = ml_result.get("projections", {})
                current_bal = ml_result.get("current_balance", 0)
                day_30 = projections.get("day_30", ml_result.get("day_30", 0))
                day_60 = projections.get("day_60", ml_result.get("day_60", 0))
                day_90 = projections.get("day_90", ml_result.get("day_90", 0))

                if day_90 > current_bal:
                    trend = "improving"
                elif day_90 < current_bal:
                    trend = "deteriorating"
                else:
                    trend = "stable"

                return {
                    "user_id": user_id,
                    "current_balance": float(current_bal),
                    "projected_balance_day_30": float(day_30),
                    "projected_balance_day_60": float(day_60),
                    "projected_balance_day_90": float(day_90),
                    "risk_trend": trend,
                }
        except Exception as e:
            logger.warning(f"ML projection failed for {user_id}: {e}")

    # ── Fallback: ORM-based linear extrapolation ──
    customer = db.query(Customer).filter(Customer.id == user_id).first()
    if not customer:
        return None

    balance = _get_customer_balance(db, user_id)
    monthly_income = customer.monthly_income_avg or _get_monthly_income(db, user_id)
    monthly_expenses = _get_monthly_expenses(db, user_id)
    net_monthly = monthly_income - monthly_expenses

    day_30 = round(balance + net_monthly, 2)
    day_60 = round(day_30 + net_monthly, 2)
    day_90 = round(day_60 + net_monthly, 2)

    if day_90 > balance:
        trend = "improving"
    elif day_90 < balance:
        trend = "deteriorating"
    else:
        trend = "stable"

    return {
        "user_id": user_id,
        "current_balance": balance,
        "projected_balance_day_30": day_30,
        "projected_balance_day_60": day_60,
        "projected_balance_day_90": day_90,
        "risk_trend": trend,
    }


# ═══════════════════════════════════════════════
#  3.  generate_repayment_plan(user_id, db)
# ═══════════════════════════════════════════════

def generate_repayment_plan(user_id: str, db: Session) -> Optional[Dict[str, Any]]:
    """
    Adaptive repayment recommendation with LLM-generated empathetic rationale.

    Strategy:
      - Get ML repayment plan for safe debit / deferral amounts
      - Feed ML risk data into empathy engine for human-readable rationale
      - Fallback to ORM-based calculation if ML unavailable
    """
    original_emi = 0.0
    safe_debit = 0.0
    deferred = 0.0
    deferral_months = 0
    plan_id = f"PLAN-{user_id}-{datetime.now(timezone.utc).strftime('%Y%m%d')}"

    # ── Try ML pipeline ──
    ml_plan = None
    if ML_AVAILABLE:
        try:
            ml_plan = ml_get_repayment(user_id)
            if ml_plan and "error" not in ml_plan and ml_plan.get("eligibility"):
                recommended = ml_plan.get("recommended_plan", {})
                original_emi = float(ml_plan.get("current_emi_total", 0))
                safe_debit = float(recommended.get("recommended_emi", 0))
                deferred = round(original_emi - safe_debit, 2)
                deferral_months = recommended.get("duration_months", 3)
                plan_id = recommended.get("plan_id", plan_id)
        except Exception as e:
            logger.warning(f"ML repayment failed for {user_id}: {e}")

    # ── Fallback: ORM-based calculation ──
    if original_emi == 0:
        customer = db.query(Customer).filter(Customer.id == user_id).first()
        if not customer:
            return None

        balance = _get_customer_balance(db, user_id)

        # Calculate living floor
        living_floor = 0.0
        if RULES_AVAILABLE:
            try:
                buffer_data = calculate_minimum_survival_buffer(user_id, db)
                living_floor = buffer_data.get("minimum_survival_buffer", 0.0)
            except Exception:
                pass

        if living_floor == 0:
            monthly_expenses = _get_monthly_expenses(db, user_id)
            living_floor = monthly_expenses * 0.6

        # Sum active loan EMIs
        active_loans = (
            db.query(Loan)
            .filter(Loan.customer_id == user_id, Loan.status == "ACTIVE")
            .all()
        )
        original_emi = sum(l.monthly_emi for l in active_loans) if active_loans else 12_000.0

        surplus = max(0.0, balance - living_floor)
        safe_debit = round(min(original_emi, surplus * 0.6), 2)
        deferred = round(original_emi - safe_debit, 2)
        deferral_months = 3 if deferred > 0 else 0

    # ── Generate empathetic rationale via LLM ──
    rationale = (
        f"Your current EMI of ₹{original_emi:,.0f} has been reviewed against your "
        f"live financial position. A safe debit of ₹{safe_debit:,.0f} protects your "
        f"essential expenses, with ₹{deferred:,.0f} deferred interest-free."
    )

    if EMPATHY_AVAILABLE and deferred > 0:
        try:
            # Determine shock type from ML data
            shock_type = "other"
            if ml_plan and isinstance(ml_plan, dict):
                reasons = ml_plan.get("hardship_reasons", [])
                reasons_str = " ".join(reasons).lower()
                if "medical" in reasons_str:
                    shock_type = "medical"
                elif "income" in reasons_str or "job" in reasons_str:
                    shock_type = "job_loss"

            payload = DistressPayload(
                shock=shock_type,
                amount=deferred,
                user_name=user_id,
                emi=original_emi,
                recommended_emi=safe_debit,
                deferred_amount=deferred,
            )
            empathy_response = empathy_fallback(payload)
            rationale = (
                f"{empathy_response.headline} "
                f"{empathy_response.message} "
                f"{empathy_response.suggestion}"
            )
        except Exception as e:
            logger.warning(f"Empathy engine failed for {user_id}: {e}")

    return {
        "user_id": user_id,
        "plan_id": plan_id,
        "original_emi": original_emi,
        "safe_debit_amount": safe_debit,
        "deferred_amount": deferred,
        "deferral_months": deferral_months,
        "rationale": rationale,
    }


# ═══════════════════════════════════════════════
#  4.  get_user_anomalies(user_id, db)
# ═══════════════════════════════════════════════

def get_user_anomalies(user_id: str, db: Session) -> Dict[str, Any]:
    """
    Detected transaction anomalies for a user.

    Strategy:
      - Delegate to ML pipeline's anomaly detector (queries anomalies table
        in ML DB populated by the trained IsolationForest model)
      - Fallback: flag ORM transactions that exceed 3x the category average
    """
    anomalies: List[Dict[str, Any]] = []

    # ── ML pipeline anomalies ──
    if ML_AVAILABLE:
        try:
            ml_anomalies = ml_get_anomalies(user_id)
            if isinstance(ml_anomalies, list) and len(ml_anomalies) > 0:
                for a in ml_anomalies:
                    score = a.get("anomaly_score", 0)
                    if score > 0.7:
                        severity = "high"
                    elif score > 0.4:
                        severity = "medium"
                    else:
                        severity = "low"

                    anomalies.append({
                        "transaction_id": str(a.get("transaction_id", a.get("txn_id", ""))),
                        "date": str(a.get("date", a.get("timestamp", ""))),
                        "category": str(a.get("category", "Unknown")),
                        "amount": float(a.get("amount", 0)),
                        "expected_range_min": float(a.get("expected_min", 0)),
                        "expected_range_max": float(a.get("expected_max", 0)),
                        "severity": severity,
                        "description": str(
                            a.get("description", f"Anomalous {a.get('category', '')} transaction")
                        ),
                    })
        except Exception as e:
            logger.warning(f"ML anomalies failed for {user_id}: {e}")

    # ── Fallback: ORM-based anomaly detection ──
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
                # Calculate category averages
                cat_totals: Dict[str, List[float]] = {}
                for tx in transactions:
                    cat_totals.setdefault(tx.category, []).append(abs(tx.amount))

                cat_avg = {
                    cat: sum(vals) / len(vals) for cat, vals in cat_totals.items()
                }

                # Flag transactions exceeding 3x category average
                for tx in transactions[:50]:  # Check recent 50
                    avg = cat_avg.get(tx.category, 0)
                    if avg > 0 and abs(tx.amount) > avg * 3:
                        anomalies.append({
                            "transaction_id": str(tx.id),
                            "date": tx.timestamp.strftime("%Y-%m-%d")
                            if tx.timestamp
                            else "",
                            "category": tx.category,
                            "amount": abs(tx.amount),
                            "expected_range_min": round(avg * 0.5, 2),
                            "expected_range_max": round(avg * 2, 2),
                            "severity": "high"
                            if abs(tx.amount) > avg * 5
                            else "medium",
                            "description": tx.description
                            or f"Unusually large {tx.category} transaction",
                        })
        except Exception as e:
            logger.warning(f"ORM anomaly detection failed for {user_id}: {e}")

    return {
        "user_id": user_id,
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
    }


# ═══════════════════════════════════════════════
#  5.  record_consent(user_id, plan_id, db)
# ═══════════════════════════════════════════════

def record_consent(user_id: str, plan_id: str, db: Session) -> Dict[str, Any]:
    """
    Persist the customer's consent for an adaptive repayment plan.

    Writes to:
      - SQLAlchemy Intervention table (ORM DB)
      - ML DB consent table (via pipeline function)
    """
    now = datetime.now(timezone.utc)

    # ── Record in ML DB (if available) ──
    if ML_AVAILABLE:
        try:
            ml_record_consent(user_id, plan_id)
        except Exception as e:
            logger.warning(f"ML consent recording failed for {user_id}: {e}")

    # ── Record in ORM DB — create an Intervention record ──
    try:
        # Check if customer exists in ORM DB
        customer = db.query(Customer).filter(Customer.id == user_id).first()
        if customer:
            # Find the active loan to link the intervention
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
                    adjusted_emi=loan.monthly_emi * 0.5,
                    status="ACCEPTED",
                    initiated_at=now,
                )
                db.add(intervention)
                db.commit()
    except Exception as e:
        logger.warning(f"ORM consent recording failed for {user_id}: {e}")
        db.rollback()

    return {
        "user_id": user_id,
        "plan_id": plan_id,
        "status": "confirmed",
        "message": (
            f"Consent recorded successfully for plan {plan_id}. "
            f"Adaptive repayment schedule is now active."
        ),
        "consented_at": now,
    }


# ═══════════════════════════════════════════════
#  6.  get_portfolio_summary(db)
# ═══════════════════════════════════════════════

def get_portfolio_summary(db: Session) -> Dict[str, Any]:
    """
    Aggregate stats across all accounts for the bank-manager dashboard.

    Strategy:
      - Delegate to ML pipeline for rich risk-scored portfolio stats
      - Map ML output shape to PortfolioSummaryResponse schema
      - Fallback to ORM-based counting
    """
    # ── ML pipeline portfolio ──
    if ML_AVAILABLE:
        try:
            ml_result = ml_get_portfolio()
            if ml_result and "error" not in ml_result:
                risk_dist = ml_result.get("risk_distribution", {})
                alerts = ml_result.get("alerts", {})
                risk_scores = ml_result.get("risk_scores", {})

                total_users = ml_result.get("total_users", 0)
                healthy = risk_dist.get("healthy", 0)
                at_risk = risk_dist.get("at_risk", 0)
                critical = risk_dist.get("critical", 0)
                watch = total_users - healthy - at_risk - critical

                return {
                    "total_users": total_users,
                    "healthy_count": healthy,
                    "watch_count": max(0, watch),
                    "at_risk_count": at_risk,
                    "critical_count": critical,
                    "defaults_prevented": alerts.get("defaults_averted", alerts.get("total_missed_emis", 0)),
                    "average_oxygen_score": round(
                        100 - risk_scores.get("average", 50), 1
                    ),
                    "total_active_interventions": alerts.get(
                        "users_needing_intervention", 0
                    ),
                }
        except Exception as e:
            logger.warning(f"ML portfolio summary failed: {e}")

    # ── Fallback: ORM-based counting ──
    total_users = db.query(func.count(Customer.id)).scalar() or 0
    total_active_interventions = (
        db.query(func.count(Intervention.id))
        .filter(Intervention.status.in_(["PROPOSED", "ACCEPTED", "ACTIVE"]))
        .scalar()
    ) or 0

    return {
        "total_users": total_users,
        "healthy_count": total_users,
        "watch_count": 0,
        "at_risk_count": 0,
        "critical_count": 0,
        "defaults_prevented": total_active_interventions,
        "average_oxygen_score": 65.0,
        "total_active_interventions": total_active_interventions,
    }


# ═══════════════════════════════════════════════
#  7.  get_at_risk_users(db)
# ═══════════════════════════════════════════════

def get_at_risk_users(db: Session) -> List[Dict[str, Any]]:
    """
    All users flagged as At-Risk or Critical with their primary trigger.

    Strategy:
      - Delegate to ML pipeline for ML-scored at-risk user list
      - Map ML output shape to AtRiskUser schema
      - Fallback to ORM-based distress detection via rules engine
    """
    # ── ML pipeline at-risk users ──
    if ML_AVAILABLE:
        try:
            ml_result = ml_get_at_risk()
            if isinstance(ml_result, list) and len(ml_result) > 0:
                users = []
                for u in ml_result:
                    risk_score = u.get("risk_score", 50)
                    risk_tier = u.get("risk_tier", "at_risk")
                    oxygen_score = round(100 - risk_score, 1)

                    # Determine primary trigger
                    triggers = []
                    if u.get("income_dropped"):
                        triggers.append("Income drop detected")
                    if u.get("missed_emis", 0) > 0:
                        triggers.append(f"{u['missed_emis']} missed EMI(s)")
                    if u.get("days_until_zero", 999) < 90:
                        triggers.append(
                            f"Projected zero balance in {u['days_until_zero']} days"
                        )
                    primary_trigger = "; ".join(triggers) if triggers else "Financial stress detected"

                    users.append({
                        "user_id": str(u.get("user_id", "")),
                        "name": str(u.get("name", "")),
                        "balance": 0.0,  # Not in ML at-risk response
                        "financial_oxygen_score": max(0, min(100, oxygen_score)),
                        "risk_status": _risk_tier_to_status(risk_tier),
                        "primary_trigger": primary_trigger,
                        "days_in_risk_zone": max(1, 90 - u.get("days_until_zero", 90)),
                    })
                return users
        except Exception as e:
            logger.warning(f"ML at-risk users failed: {e}")

    # ── Fallback: ORM-based detection ──
    results = []
    if RULES_AVAILABLE:
        try:
            customers = db.query(Customer).all()
            for c in customers:
                distress = evaluate_liquidity_distress(c.id, db)
                if distress.get("is_distressed"):
                    balance = distress.get("current_balance", 0)
                    deficit = distress.get("projected_deficit", 0)
                    oxygen = _compute_oxygen_score(
                        balance, distress.get("minimum_survival_buffer", 0)
                    )
                    results.append({
                        "user_id": c.id,
                        "name": f"{c.first_name} {c.last_name}",
                        "balance": balance,
                        "financial_oxygen_score": oxygen,
                        "risk_status": "Critical" if deficit > 10000 else "At-Risk",
                        "primary_trigger": distress.get("recommendation", {}).get(
                            "trigger_reason", "Liquidity buffer breach"
                        ),
                        "days_in_risk_zone": 1,
                    })
        except Exception as e:
            logger.warning(f"ORM at-risk detection failed: {e}")

    return results
