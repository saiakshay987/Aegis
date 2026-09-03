"""
Aegis Rules Engine & Minimum Survival Buffer Calculator
Role: Database Architect / Rules Engine Engineer

Formula:
  Minimum Survival Buffer = (30-day Average Essential Expenses) + (10% Emergency Margin)
                          = Total Essential Debits in last 30 days * 1.10

Distress Threshold:
  Projected Buffer Post-EMI = (Current Liquid Balance - Scheduled Monthly EMI)
  If (Projected Buffer Post-EMI < Minimum Survival Buffer):
      TRIGGER DYNAMIC LIQUIDITY FORBEARANCE INTERVENTION
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy import select, func, desc, text
from sqlalchemy.orm import Session
from models import Customer, Loan, Transaction, Intervention


# ============================================================================
# 1. Pure SQL Implementation (Can be executed directly on SQLite / Any RDBMS)
# ============================================================================
SQL_CALCULATE_SURVIVAL_BUFFER = """
-- Calculates 30-day Essential Expenses + 10% Emergency Margin for a Customer
SELECT 
    c.id AS customer_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    c.archetype,
    COALESCE(SUM(ABS(t.amount)), 0.0) AS essential_expenses_30d,
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

SQL_EVALUATE_ALL_CUSTOMERS_DISTRESS = """
-- Evaluates Liquidity Distress across all borrowers with upcoming active EMIs
WITH EssentialSpend AS (
    SELECT 
        customer_id,
        COALESCE(SUM(ABS(amount)), 0.0) AS essential_30d,
        ROUND(COALESCE(SUM(ABS(amount)), 0.0) * 1.10, 2) AS survival_buffer
    FROM transactions
    WHERE is_essential = 1 
      AND type = 'DEBIT'
      AND timestamp >= DATETIME(:as_of_date, '-30 days')
      AND timestamp <= DATETIME(:as_of_date)
    GROUP BY customer_id
),
LatestBalance AS (
    SELECT 
        customer_id,
        balance_after AS current_liquid_balance
    FROM transactions t1
    WHERE timestamp = (
        SELECT MAX(t2.timestamp) 
        FROM transactions t2 
        WHERE t2.customer_id = t1.customer_id
          AND t2.timestamp <= DATETIME(:as_of_date)
    )
)
SELECT 
    c.id AS customer_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    c.archetype,
    c.credit_score,
    lb.current_liquid_balance,
    l.id AS loan_id,
    l.monthly_emi AS upcoming_emi,
    l.next_due_date,
    COALESCE(es.survival_buffer, 0.0) AS survival_buffer,
    ROUND(lb.current_liquid_balance - l.monthly_emi, 2) AS projected_balance_post_emi,
    CASE 
        WHEN (lb.current_liquid_balance - l.monthly_emi) < COALESCE(es.survival_buffer, 0.0) THEN 1 
        ELSE 0 
    END AS is_distressed,
    CASE 
        WHEN (lb.current_liquid_balance - l.monthly_emi) < COALESCE(es.survival_buffer, 0.0) 
        THEN ROUND(COALESCE(es.survival_buffer, 0.0) - (lb.current_liquid_balance - l.monthly_emi), 2)
        ELSE 0.0 
    END AS projected_deficit
FROM customers c
JOIN loans l ON c.id = l.customer_id AND l.status = 'ACTIVE'
LEFT JOIN LatestBalance lb ON c.id = lb.customer_id
LEFT JOIN EssentialSpend es ON c.id = es.customer_id
ORDER BY is_distressed DESC, projected_deficit DESC;
"""


# ============================================================================
# 2. Python / SQLAlchemy Implementation
# ============================================================================

def calculate_minimum_survival_buffer(
    customer_id: str,
    db: Session,
    as_of_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Calculates the 30-day essential expenses and Minimum Survival Buffer
    for a given customer using SQLAlchemy ORM.
    
    Formula:
        Buffer = (30-day Total Essential Living Debits) * 1.10
    """
    if as_of_date is None:
        as_of_date = datetime.now()
    
    start_date = as_of_date - timedelta(days=30)

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise ValueError(f"Customer with ID {customer_id} not found.")

    # Sum essential debits in the 30-day window
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
    Evaluates whether an upcoming loan EMI will breach the customer's
    Minimum Survival Buffer, creating transient financial distress.
    """
    if as_of_date is None:
        as_of_date = datetime.utcnow()

    buffer_data = calculate_minimum_survival_buffer(customer_id, db, as_of_date)
    survival_buffer = buffer_data["minimum_survival_buffer"]

    # Retrieve customer's latest active loan
    loan = db.query(Loan).filter(
        Loan.customer_id == customer_id,
        Loan.status == "ACTIVE"
    ).first()

    # Retrieve current liquid balance from most recent transaction
    latest_tx = db.query(Transaction).filter(
        Transaction.customer_id == customer_id,
        Transaction.timestamp <= as_of_date
    ).order_by(desc(Transaction.timestamp)).first()

    current_balance = latest_tx.balance_after if latest_tx else 0.0
    upcoming_emi = loan.monthly_emi if loan else 0.0

    projected_balance_post_emi = round(current_balance - upcoming_emi, 2)
    is_distressed = projected_balance_post_emi < survival_buffer
    deficit = round(survival_buffer - projected_balance_post_emi, 2) if is_distressed else 0.0

    recommendation = None
    if is_distressed and loan:
        recommendation = recommend_intervention_strategy(
            customer_archetype=buffer_data["archetype"],
            loan=loan,
            current_balance=current_balance,
            survival_buffer=survival_buffer,
            deficit=deficit
        )

    return {
        **buffer_data,
        "current_balance": current_balance,
        "upcoming_emi": upcoming_emi,
        "next_due_date": str(loan.next_due_date) if loan else None,
        "projected_balance_post_emi": projected_balance_post_emi,
        "is_distressed": is_distressed,
        "projected_deficit": deficit,
        "recommendation": recommendation
    }


def recommend_intervention_strategy(
    customer_archetype: str,
    loan: Loan,
    current_balance: float,
    survival_buffer: float,
    deficit: float
) -> Dict[str, Any]:
    """
    Synthesizes proactive, personalized forbearance actions instead of 
    allowing rigid NACH bounce.
    """
    if customer_archetype == "MEDICAL_SHOCK":
        # Shock scenario: Patient experienced a sudden spike in healthcare costs.
        # Action: Streaming Micro-Amortization (Spread EMI into 4 weekly micro-chunks of 25%)
        # or Interest-only freeze for 30 days to protect survival floor.
        adjusted_emi = round(loan.monthly_emi * 0.25, 2)
        return {
            "action_type": "STREAMING_MICRO_AMORTIZATION",
            "trigger_reason": "EXOGENOUS_MEDICAL_SHOCK",
            "original_emi": loan.monthly_emi,
            "adjusted_emi": adjusted_emi,
            "rationale": (
                f"Customer suffered exogenous medical shock. Monthly debit of INR {loan.monthly_emi:,.2f} "
                f"would breach survival floor (INR {survival_buffer:,.2f}) by INR {deficit:,.2f}. "
                f"De-escalating to weekly micro-installments of INR {adjusted_emi:,.2f} over 30 days."
            )
        }
    elif customer_archetype == "VOLATILE_INCOME":
        # Volatile scenario: Freelancer/gig worker awaiting invoice settlement.
        # Action: Grace Period Extension / Split EMI matching delayed invoice receivables.
        return {
            "action_type": "GRACE_PERIOD_EXTENSION",
            "trigger_reason": "INVOICE_DELAY",
            "original_emi": loan.monthly_emi,
            "adjusted_emi": loan.monthly_emi,
            "rationale": (
                f"Contractor payment cycle lag detected. Projected deficit is INR {deficit:,.2f}. "
                f"Shifting NACH debit date by 14 days without late penalty or CIBIL score degradation."
            )
        }
    else:
        return {
            "action_type": "SPLIT_EMI",
            "trigger_reason": "LIQUIDITY_BUFFER_BREACH",
            "original_emi": loan.monthly_emi,
            "adjusted_emi": round(loan.monthly_emi / 2, 2),
            "rationale": "Liquidity buffer breach detected. Proposing bi-weekly split installment."
        }
