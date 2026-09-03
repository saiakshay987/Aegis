"""
Synthetic Data Generator for Aegis Database
Populates SQLite database with 3 realistic borrower archetypes:
  1. Healthy Salaried Borrower (Priya Sharma)
  2. Exogenous Medical Shock Borrower (Arun Kumar)
  3. High Income Volatility / Freelancer (Rohan Verma)

Run from the project root:
    python seed_data.py
"""

import os
import sys
from datetime import datetime, timedelta

# ── Ensure the backend package (database.py, models.py etc.) is on
#    the path regardless of where this script is invoked from. ───
_THIS_DIR     = os.path.dirname(os.path.abspath(__file__))          # d:\Aegis\Aegis
_BACKEND_DIR  = os.path.join(_THIS_DIR, "aegis", "backend")

# Insert BACKEND_DIR first so 'import database' resolves to
# aegis/backend/database.py (which points to ML_model/data/aegis.db).
# Append _THIS_DIR last so models.py is reachable as a fallback.
for _p in [_THIS_DIR, _BACKEND_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from sqlalchemy.orm import Session
from database import engine, SessionLocal
from models import Base, Customer, Loan, Transaction, Intervention


def init_db_for_seed():
    """Drop and recreate all ORM tables (clean slate for seeding)."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def seed_synthetic_data():
    print("[1/3] Resetting and creating tables...")
    init_db_for_seed()

    db: Session = SessionLocal()
    try:
        print("[2/3] Seeding 3 Borrower Archetypes & Credit Facilities...")
        now = datetime.now()

        # ────────────────────────────────────────────────────────
        # Archetype 1: Healthy Salaried Borrower (Priya Sharma)
        # ────────────────────────────────────────────────────────
        cust1 = Customer(
            id="CUST-001",
            first_name="Priya",
            last_name="Sharma",
            email="priya.sharma@example.com",
            phone="+919876543210",
            archetype="HEALTHY",
            monthly_income_avg=150000.00,
            credit_score=790,
        )
        loan1 = Loan(
            id="LOAN-001",
            customer_id="CUST-001",
            loan_type="VEHICLE",
            principal_amount=800000.00,
            interest_rate_apr=8.75,
            tenure_months=48,
            monthly_emi=18500.00,
            next_due_date=(now + timedelta(days=2)).date(),
            status="ACTIVE",
            nach_mandate_active=True,
        )

        # ────────────────────────────────────────────────────────
        # Archetype 2: Sudden Medical Shock (Arun Kumar)
        # ────────────────────────────────────────────────────────
        cust2 = Customer(
            id="CUST-002",
            first_name="Arun",
            last_name="Kumar",
            email="arun.kumar@example.com",
            phone="+919812345678",
            archetype="MEDICAL_SHOCK",
            monthly_income_avg=48000.00,
            credit_score=735,
        )
        loan2 = Loan(
            id="LOAN-002",
            customer_id="CUST-002",
            loan_type="PERSONAL",
            principal_amount=250000.00,
            interest_rate_apr=13.50,
            tenure_months=24,
            monthly_emi=11800.00,
            next_due_date=(now + timedelta(days=2)).date(),
            status="ACTIVE",
            nach_mandate_active=True,
        )

        # ────────────────────────────────────────────────────────
        # Archetype 3: High Income Volatility (Rohan Verma)
        # ────────────────────────────────────────────────────────
        cust3 = Customer(
            id="CUST-003",
            first_name="Rohan",
            last_name="Verma",
            email="rohan.verma@example.com",
            phone="+919988776655",
            archetype="VOLATILE_INCOME",
            monthly_income_avg=75000.00,
            credit_score=710,
        )
        loan3 = Loan(
            id="LOAN-003",
            customer_id="CUST-003",
            loan_type="EQUIPMENT",
            principal_amount=350000.00,
            interest_rate_apr=11.25,
            tenure_months=36,
            monthly_emi=14500.00,
            next_due_date=(now + timedelta(days=2)).date(),
            status="ACTIVE",
            nach_mandate_active=True,
        )

        db.add_all([cust1, cust2, cust3, loan1, loan2, loan3])
        db.flush()

        print("[3/3] Generating realistic transaction ledgers over last 45 days...")
        transactions = []
        tx_id_counter = 1

        def add_tx(cust_id, dt, amount, tx_type, category, is_essential, desc, bal):
            nonlocal tx_id_counter
            tx = Transaction(
                id=f"TXN-{tx_id_counter:04d}",
                customer_id=cust_id,
                timestamp=dt,
                amount=amount,
                type=tx_type,
                category=category,
                is_essential=is_essential,
                description=desc,
                balance_after=bal,
            )
            tx_id_counter += 1
            transactions.append(tx)

        # ── Customer 1 (Healthy): starting balance ₹1,20,000 ──────
        # 30-day Essential Spend: Rent(30k) + Groceries(11.5k) + Utilities(4.8k) = 46,300
        # Survival Buffer: 46,300 × 1.10 = 50,930
        bal1 = 120000.00
        bal1 -= 12000.00
        add_tx("CUST-001", now - timedelta(days=35), -12000.00, "DEBIT", "GROCERIES",  True,  "Hypermarket Monthly Essentials",          bal1)
        bal1 += 150000.00
        add_tx("CUST-001", now - timedelta(days=30), 150000.00, "CREDIT", "SALARY",    False, "MNC Technologies Monthly Payroll",        bal1)
        bal1 -= 30000.00
        add_tx("CUST-001", now - timedelta(days=28), -30000.00, "DEBIT", "RENT",       True,  "Apartment Monthly Rent Transfer",         bal1)
        bal1 -= 18500.00
        add_tx("CUST-001", now - timedelta(days=25), -18500.00, "DEBIT", "LOAN_EMI",  False, "Auto Debit - Vehicle Loan",               bal1)
        bal1 -= 11500.00
        add_tx("CUST-001", now - timedelta(days=20), -11500.00, "DEBIT", "GROCERIES",  True,  "Supermarket Essentials & Organic Pantry", bal1)
        bal1 -= 4800.00
        add_tx("CUST-001", now - timedelta(days=15),  -4800.00, "DEBIT", "UTILITIES",  True,  "State Electricity & Broadband Bill",      bal1)
        bal1 -= 7200.00
        add_tx("CUST-001", now - timedelta(days=10),  -7200.00, "DEBIT", "ENTERTAINMENT", False, "Fine Dining & Weekend Outing",         bal1)
        bal1 -= 9000.00
        add_tx("CUST-001", now - timedelta(days=5),   -9000.00, "DEBIT", "SHOPPING",  False, "Apparel & Online Retail Store",            bal1)

        # ── Customer 2 (Medical Shock): starting balance ₹40,000 ──
        # Post-shock balance ≈ ₹4,200; upcoming EMI ₹11,800 → DISTRESSED
        bal2 = 40000.00
        bal2 += 48000.00
        add_tx("CUST-002", now - timedelta(days=29),  48000.00, "CREDIT", "SALARY",    False, "Logistics Corp Monthly Payroll",          bal2)
        bal2 -= 14000.00
        add_tx("CUST-002", now - timedelta(days=27), -14000.00, "DEBIT", "RENT",       True,  "Residential House Rent Payment",          bal2)
        bal2 -= 11800.00
        add_tx("CUST-002", now - timedelta(days=25), -11800.00, "DEBIT", "LOAN_EMI",  False, "Auto Debit - Personal Loan",              bal2)
        bal2 -= 7800.00
        add_tx("CUST-002", now - timedelta(days=18),  -7800.00, "DEBIT", "GROCERIES",  True,  "Local Grocery Store Provisions",          bal2)
        bal2 -= 3200.00
        add_tx("CUST-002", now - timedelta(days=12),  -3200.00, "DEBIT", "UTILITIES",  True,  "Electricity & Cooking Gas Cylinder",      bal2)
        bal2 -= 34000.00
        add_tx("CUST-002", now - timedelta(days=3),  -34000.00, "DEBIT", "HEALTHCARE", True,  "Apollo City Hospital - Emergency Surgery",bal2)
        bal2 -= 13000.00
        add_tx("CUST-002", now - timedelta(days=2),  -13000.00, "DEBIT", "HEALTHCARE", True,  "Apollo Pharmacy - Urgent Medication",     bal2)

        # ── Customer 3 (Volatile Income): starting balance ₹38,000 ──
        # Expected ₹85,000 invoice delayed; balance ≈ ₹8,200; EMI ₹14,500 → DISTRESSED
        bal3 = 38000.00
        bal3 -= 18000.00
        add_tx("CUST-003", now - timedelta(days=28), -18000.00, "DEBIT", "RENT",       True,  "Studio Apartment Rent",                   bal3)
        bal3 -= 14500.00
        add_tx("CUST-003", now - timedelta(days=25), -14500.00, "DEBIT", "LOAN_EMI",  False, "Auto Debit - Equipment Loan",             bal3)
        bal3 += 15000.00
        add_tx("CUST-003", now - timedelta(days=24),  15000.00, "CREDIT", "INVOICE",  False, "Client Retainer Advance",                 bal3)
        bal3 -= 7500.00
        add_tx("CUST-003", now - timedelta(days=18),  -7500.00, "DEBIT", "GROCERIES",  True,  "Organic Mart Food Provisions",            bal3)
        bal3 -= 4800.00
        add_tx("CUST-003", now - timedelta(days=12),  -4800.00, "DEBIT", "UTILITIES",  True,  "Cloud Hosting & Fiber Broadband",         bal3)

        db.add_all(transactions)
        db.commit()
        print(
            f"Successfully committed {len(transactions)} transactions "
            f"across 3 customer archetypes."
        )

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_synthetic_data()
