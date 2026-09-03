"""
Aegis Rules Engine & Minimum Survival Buffer Calculator
Role: Database Architect / Rules Engine Engineer

Features:
  1. Minimum Survival Buffer Calculation: (30-day Essential Living Debits) * 1.10
  2. Feature 1: Real-Time Risk View (v_customer_risk_status)
  3. Feature 2: Exogenous Shock MCC Guardrail (verifies legitimate shock MCC codes)
  4. Feature 3: Daily Interest Accrual Calculator for Deferred Loan Principal
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy import select, func, desc, text
from sqlalchemy.orm import Session
from models import Customer, Loan, Transaction, Intervention, MCCCode


# ============================================================================
# 1. Feature 1: Real-Time Risk View Queries
# ============================================================================
SQL_SELECT_CUSTOMER_RISK_VIEW = """
-- Selects from Feature 1: Real-Time SQL View
SELECT 
    customer_id,
    customer_name,
    archetype,
    credit_score,
    current_liquid_balance,
    upcoming_emi,
    next_due_date,
    essential_spend_30d,
    minimum_survival_buffer,
    projected_balance_post_emi,
    runway_days_remaining,
    is_distressed,
    projected_deficit,
    recommended_intervention
FROM v_customer_risk_status
ORDER BY is_distressed DESC, projected_deficit DESC;
"""

SQL_CALCULATE_SURVIVAL_BUFFER = """
-- Calculates 30-day Essential Expenses + 10% Emergency Margin for a Customer
SELECT 
    c.id AS customer_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    c.archetype,
    COALESCE(SUM(ABS(t.amount)), 0.0) AS essential_expenses_30d,
    ROUND(COALESCE(SUM(ABS(t.amount)), 0.0) * 0.10, 2) AS emergency_margin_10pct,
    ROUND(COALESCE(SUM(ABS(t.amount)), 0.0) * 1.10, 2) AS minimum_survival_buffer
FROM customers c
LEFT JOIN transactions t 
    ON c.id = t.customer_id 
    AND t.is_essential = 1 
    AND t.type = 'DEBIT'
    AND t.timestamp >= DATETIME(:as_of_date, '-30 days')
    AND t.timestamp <= DATETIME(:as_of_date)
WHERE c.id = :customer_id
GROUP BY c.id;
"""


# ============================================================================
# 2. Feature 3: Daily Interest Accrual Calculator
# ============================================================================
def calculate_daily_interest_accrual(
    deferred_principal: float,
    annual_interest_rate_apr: float,
    days_deferred: int
) -> Dict[str, Any]:
    """
    Feature 3: Financial tracking function calculating how much interest
    accrues daily on a deferred balance during forbearance.

    Formula:
        Daily Rate = (Annual APR / 365) / 100
        Accrued Interest = Deferred Principal * Daily Rate * Days Deferred
    """
    daily_rate = (annual_interest_rate_apr / 365.0) / 100.0
    accrued_interest = round(deferred_principal * daily_rate * days_deferred, 2)

    return {
        "deferred_principal": deferred_principal,
        "annual_interest_rate_apr": annual_interest_rate_apr,
        "daily_accrual_rate": round(daily_rate, 8),
        "days_deferred": days_deferred,
        "accrued_interest": accrued_interest
    }


# ============================================================================
# 3. Feature 2: Exogenous Shock MCC Guardrail Validator
# ============================================================================
def verify_exogenous_shock_guardrail(
    customer_id: str,
    db: Session,
    lookback_days: int = 14
) -> Dict[str, Any]:
    """
    Feature 2: Validates whether the customer incurred legitimate, verified
    non-discretionary emergency expenditures (e.g. MCC 8062 Hospital, 5912 Pharmacy).
    
    Prevents self-transfers (MCC 6012), gambling (MCC 7995), or unverified
    cash movements from gaming the forbearance engine.
    """
    cutoff = datetime.now() - timedelta(days=lookback_days)

    # Query transactions matching shock-eligible MCC codes
    shock_txs = (
        db.query(Transaction, MCCCode)
        .join(MCCCode, Transaction.mcc_code == MCCCode.code)
        .filter(
            Transaction.customer_id == customer_id,
            Transaction.type == "DEBIT",
            Transaction.timestamp >= cutoff,
            MCCCode.is_shock_eligible == True
        )
        .all()
    )

    total_shock_spend = sum(abs(t.Transaction.amount) for t in shock_txs)
    has_valid_shock = len(shock_txs) > 0 and total_shock_spend > 10000.00

    return {
        "customer_id": customer_id,
        "has_valid_shock": has_valid_shock,
        "shock_transaction_count": len(shock_txs),
        "total_shock_expenditure": total_shock_spend,
        "verified_mcc_records": [
            {
                "tx_id": t.Transaction.id,
                "amount": abs(t.Transaction.amount),
                "mcc_code": t.Transaction.mcc_code,
                "category": t.MCCCode.category_name,
                "description": t.Transaction.description
            }
            for t in shock_txs
        ]
    }


# ============================================================================
# 4. Core Survival Buffer & Distress Evaluation
# ============================================================================
def calculate_minimum_survival_buffer(
    customer_id: str,
    db: Session,
    as_of_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Calculates the 30-day essential expenses and Minimum Survival Buffer.
    Formula: Buffer = (30-day Essential Living Debits) * 1.10
    """
    if as_of_date is None:
        as_of_date = datetime.now()
    
    start_date = as_of_date - timedelta(days=30)

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise ValueError(f"Customer with ID {customer_id} not found.")

    essential_spend = db.query(func.coalesce(func.sum(func.abs(Transaction.amount)), 0.0)).filter(
        Transaction.customer_id == customer_id,
        Transaction.is_essential == True,
        Transaction.type == "DEBIT",
        Transaction.timestamp >= start_date,
        Transaction.timestamp <= as_of_date
    ).scalar()

    essential_spend_total = float(essential_spend)
    emergency_margin = round(essential_spend_total * 0.10, 2)
    minimum_survival_buffer = round(essential_spend_total + emergency_margin, 2)

    return {
        "customer_id": customer.id,
        "customer_name": f"{customer.first_name} {customer.last_name}",
        "archetype": customer.archetype,
        "as_of_date": as_of_date.isoformat(),
        "30_day_essential_expenses": essential_spend_total,
        "emergency_margin_10_pct": emergency_margin,
        "minimum_survival_buffer": minimum_survival_buffer
    }


def evaluate_liquidity_distress(
    customer_id: str,
    db: Session,
    as_of_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Evaluates liquidity distress, validates shock guardrails,
    and synthesizes daily interest accrual on proposed interventions.
    """
    if as_of_date is None:
        as_of_date = datetime.now()

    buffer_data = calculate_minimum_survival_buffer(customer_id, db, as_of_date)
    survival_buffer = buffer_data["minimum_survival_buffer"]

    loan = db.query(Loan).filter(
        Loan.customer_id == customer_id,
        Loan.status.in_(["ACTIVE", "FORBEARANCE"])
    ).first()

    latest_tx = db.query(Transaction).filter(
        Transaction.customer_id == customer_id,
        Transaction.timestamp <= as_of_date
    ).order_by(desc(Transaction.timestamp)).first()

    current_balance = latest_tx.balance_after if latest_tx else 0.0
    upcoming_emi = loan.monthly_emi if loan else 0.0

    projected_balance_post_emi = round(current_balance - upcoming_emi, 2)
    is_distressed = projected_balance_post_emi < survival_buffer
    deficit = round(survival_buffer - projected_balance_post_emi, 2) if is_distressed else 0.0

    # Calculate financial runway in days
    essential_spend = buffer_data["30_day_essential_expenses"]
    runway_days = round((current_balance / essential_spend) * 30.0, 1) if essential_spend > 0 else 999.0

    # Validate MCC shock guardrail
    shock_guardrail = verify_exogenous_shock_guardrail(customer_id, db)

    recommendation = None
    if is_distressed and loan:
        recommendation = recommend_intervention_strategy(
            customer_archetype=buffer_data["archetype"],
            loan=loan,
            current_balance=current_balance,
            survival_buffer=survival_buffer,
            deficit=deficit,
            shock_guardrail=shock_guardrail
        )

    return {
        **buffer_data,
        "current_balance": current_balance,
        "upcoming_emi": upcoming_emi,
        "next_due_date": str(loan.next_due_date) if loan else None,
        "projected_balance_post_emi": projected_balance_post_emi,
        "runway_days_remaining": runway_days,
        "is_distressed": is_distressed,
        "projected_deficit": deficit,
        "shock_guardrail": shock_guardrail,
        "recommendation": recommendation
    }


def recommend_intervention_strategy(
    customer_archetype: str,
    loan: Loan,
    current_balance: float,
    survival_buffer: float,
    deficit: float,
    shock_guardrail: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Synthesizes proactive forbearance with daily interest accrual tracking.
    """
    if customer_archetype == "MEDICAL_SHOCK":
        # Enforce Feature 2 Guardrail: Ensure legitimate medical shock MCC exists
        if not shock_guardrail["has_valid_shock"]:
            return {
                "action_type": "REJECTED_UNVERIFIED_SHOCK",
                "trigger_reason": "FAILED_MCC_GUARDRAIL",
                "rationale": "Emergency shock forbearance denied: No qualifying medical/emergency MCC transactions detected."
            }

        # Action: Streaming Micro-Amortization (Weekly micro-debits)
        adjusted_emi = round(loan.monthly_emi * 0.25, 2)
        deferred_principal = round(loan.monthly_emi * 0.75, 2)
        days_deferred = 30
        accrual = calculate_daily_interest_accrual(deferred_principal, loan.interest_rate_apr, days_deferred)

        return {
            "action_type": "STREAMING_MICRO_AMORTIZATION",
            "trigger_reason": "EXOGENOUS_MEDICAL_SHOCK",
            "original_emi": loan.monthly_emi,
            "adjusted_emi": adjusted_emi,
            "repayment_schedule_type": "STREAMING_MICRO",
            "deferred_principal": accrual["deferred_principal"],
            "annual_interest_rate": accrual["annual_interest_rate_apr"],
            "daily_accrual_rate": accrual["daily_accrual_rate"],
            "days_deferred": accrual["days_deferred"],
            "accrued_interest": accrual["accrued_interest"],
            "rationale": (
                f"Verified medical emergency via MCC 8062/5912 (INR {shock_guardrail['total_shock_expenditure']:,.2f}). "
                f"De-escalating to weekly micro-installments of INR {adjusted_emi:,.2f}. "
                f"Daily interest accrues at {accrual['daily_accrual_rate']*100:.4f}%/day (INR {accrual['accrued_interest']:,.2f} over 30 days)."
            )
        }
    elif customer_archetype == "VOLATILE_INCOME":
        # Action: Grace Period Extension
        deferred_principal = loan.monthly_emi
        days_deferred = 14
        accrual = calculate_daily_interest_accrual(deferred_principal, loan.interest_rate_apr, days_deferred)

        return {
            "action_type": "GRACE_PERIOD_EXTENSION",
            "trigger_reason": "INVOICE_DELAY",
            "original_emi": loan.monthly_emi,
            "adjusted_emi": loan.monthly_emi,
            "repayment_schedule_type": "BALLOON_AT_END",
            "deferred_principal": accrual["deferred_principal"],
            "annual_interest_rate": accrual["annual_interest_rate_apr"],
            "daily_accrual_rate": accrual["daily_accrual_rate"],
            "days_deferred": accrual["days_deferred"],
            "accrued_interest": accrual["accrued_interest"],
            "rationale": (
                f"Contractor payment cycle lag detected. Projected deficit is INR {deficit:,.2f}. "
                f"Shifting NACH debit date by 14 days without late fee penalty. "
                f"Daily interest accrues at {accrual['daily_accrual_rate']*100:.4f}%/day (INR {accrual['accrued_interest']:,.2f} over 14 days)."
            )
        }
    else:
        return {
            "action_type": "SPLIT_EMI",
            "trigger_reason": "LIQUIDITY_BUFFER_BREACH",
            "original_emi": loan.monthly_emi,
            "adjusted_emi": round(loan.monthly_emi / 2, 2),
            "repayment_schedule_type": "STREAMING_MICRO",
            "deferred_principal": round(loan.monthly_emi / 2, 2),
            "annual_interest_rate": loan.interest_rate_apr,
            "daily_accrual_rate": round(loan.interest_rate_apr / 365.0 / 100.0, 8),
            "days_deferred": 15,
            "accrued_interest": 0.0,
            "rationale": "Liquidity buffer breach detected. Proposing bi-weekly split installment."
        }
