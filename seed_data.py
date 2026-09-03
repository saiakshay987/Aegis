"""
Synthetic Data Generator for Aegis Database
Populates SQLite database with:
  1. Standard Banking Merchant Category Codes (MCC) with Shock Guardrails
  2. 3 Realistic Borrower Archetypes:
     - Healthy Salaried Borrower (Priya Sharma)
     - Exogenous Medical Shock Borrower (Arun Kumar)
     - High Income Volatility / Freelancer (Rohan Verma)
  3. 45-day Ledger Transactions linked to verified MCC codes
  4. Interventions with Daily Accrued Interest Tracking
"""

from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from database import engine, init_db, SessionLocal
from models import Base, Customer, Loan, Transaction, Intervention, MCCCode


def seed_synthetic_data():
    print("[1/4] Resetting and re-initializing database schema...")
    Base.metadata.drop_all(bind=engine)
    init_db(use_schema_sql=True)

    db: Session = SessionLocal()
    try:
        now = datetime.now()

        # --------------------------------------------------------------------
        # 1. Seed Feature 2: Merchant Category Codes (MCC) Reference Table
        # Guardrail: Prevents self-transfers or gaming from qualifying as shocks
        # --------------------------------------------------------------------
        print("[2/4] Seeding MCC Reference Codes & Exogenous Shock Guardrails...")
        mcc_list = [
            MCCCode(code="8062", category_name="Hospitals & Inpatient Care", is_essential=True, is_shock_eligible=True, description="Emergency hospital admission & surgical centers"),
            MCCCode(code="8011", category_name="Physicians & Clinics", is_essential=True, is_shock_eligible=True, description="Specialist doctors, urgent diagnostics & medical clinics"),
            MCCCode(code="5912", category_name="Pharmacies & Prescriptions", is_essential=True, is_shock_eligible=True, description="Prescription pharmaceuticals & emergency medicines"),
            MCCCode(code="5411", category_name="Grocery Stores & Supermarkets", is_essential=True, is_shock_eligible=False, description="Household nutritional necessities and pantry items"),
            MCCCode(code="4900", category_name="Utilities (Electric, Water, Gas)", is_essential=True, is_shock_eligible=False, description="Public utility providers and household energy"),
            MCCCode(code="6513", category_name="Real Estate Agents & Residential Rent", is_essential=True, is_shock_eligible=False, description="Residential house lease and apartment rent"),
            MCCCode(code="5812", category_name="Restaurants & Dining", is_essential=False, is_shock_eligible=False, description="Discretionary cafes, bars, and restaurants"),
            MCCCode(code="5311", category_name="Department Stores & Retail", is_essential=False, is_shock_eligible=False, description="Discretionary retail shopping and electronics"),
            MCCCode(code="6012", category_name="Financial Institutions (P2P / Self-Transfer)", is_essential=False, is_shock_eligible=False, description="Fund transfers, crypto wallets, and self-swaps (UNQUALIFIED FOR SHOCK)"),
            MCCCode(code="7995", category_name="Betting & Gambling", is_essential=False, is_shock_eligible=False, description="Casinos, lotteries, and speculative sports betting"),
        ]
        db.add_all(mcc_list)
        db.flush()

        # --------------------------------------------------------------------
        # 2. Seed 3 Borrower Archetypes & Credit Facilities
        # --------------------------------------------------------------------
        print("[3/4] Seeding Borrower Archetypes & Credit Facilities...")

        # Archetype 1: Healthy Salaried Borrower (Priya Sharma)
        cust1 = Customer(
            id="CUST-001",
            first_name="Priya",
            last_name="Sharma",
            email="priya.sharma@example.com",
            phone="+919876543210",
            archetype="HEALTHY",
            monthly_income_avg=150000.00,
            credit_score=790
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
            nach_mandate_active=True
        )

        # Archetype 2: Sudden Medical Shock (Arun Kumar)
        cust2 = Customer(
            id="CUST-002",
            first_name="Arun",
            last_name="Kumar",
            email="arun.kumar@example.com",
            phone="+919812345678",
            archetype="MEDICAL_SHOCK",
            monthly_income_avg=48000.00,
            credit_score=735
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
            nach_mandate_active=True
        )

        # Archetype 3: High Income Volatility (Rohan Verma)
        cust3 = Customer(
            id="CUST-003",
            first_name="Rohan",
            last_name="Verma",
            email="rohan.verma@example.com",
            phone="+919988776655",
            archetype="VOLATILE_INCOME",
            monthly_income_avg=75000.00,
            credit_score=710
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
            nach_mandate_active=True
        )

        db.add_all([cust1, cust2, cust3, loan1, loan2, loan3])
        db.flush()

        # --------------------------------------------------------------------
        # 3. Seed Realistic 45-day Ledger Transactions with MCC Codes
        # --------------------------------------------------------------------
        print("[4/4] Seeding Transactions & Daily Accrual Interventions...")
        transactions = []
        tx_id_counter = 1

        def add_tx(cust_id, mcc, dt, amount, tx_type, category, is_essential, desc, bal):
            nonlocal tx_id_counter
            tx = Transaction(
                id=f"TXN-{tx_id_counter:04d}",
                customer_id=cust_id,
                mcc_code=mcc,
                timestamp=dt,
                amount=amount,
                type=tx_type,
                category=category,
                is_essential=is_essential,
                description=desc,
                balance_after=bal
            )
            tx_id_counter += 1
            transactions.append(tx)

        # Priya Sharma (Healthy): Starting Balance: 1,20,000
        bal1 = 120000.00
        bal1 -= 12000.00
        add_tx("CUST-001", "5411", now - timedelta(days=35), -12000.00, "DEBIT", "GROCERIES", True, "Hypermarket Monthly Essentials", bal1)
        bal1 += 150000.00
        add_tx("CUST-001", None, now - timedelta(days=30), 150000.00, "CREDIT", "SALARY", False, "MNC Technologies Monthly Payroll", bal1)
        bal1 -= 30000.00
        add_tx("CUST-001", "6513", now - timedelta(days=28), -30000.00, "DEBIT", "RENT", True, "Apartment Monthly Rent Transfer", bal1)
        bal1 -= 18500.00
        add_tx("CUST-001", None, now - timedelta(days=25), -18500.00, "DEBIT", "LOAN_EMI", False, "Auto Debit - Vehicle Loan", bal1)
        bal1 -= 11500.00
        add_tx("CUST-001", "5411", now - timedelta(days=20), -11500.00, "DEBIT", "GROCERIES", True, "Supermarket Essentials & Pantry", bal1)
        bal1 -= 4800.00
        add_tx("CUST-001", "4900", now - timedelta(days=15), -4800.00, "DEBIT", "UTILITIES", True, "State Electricity & Broadband Bill", bal1)
        bal1 -= 7200.00
        add_tx("CUST-001", "5812", now - timedelta(days=10), -7200.00, "DEBIT", "ENTERTAINMENT", False, "Fine Dining & Weekend Bistro", bal1)
        bal1 -= 9000.00
        add_tx("CUST-001", "5311", now - timedelta(days=5), -9000.00, "DEBIT", "SHOPPING", False, "Apparel & Online Retail Store", bal1)

        # Arun Kumar (Medical Shock): Starting Balance: 40,000
        bal2 = 40000.00
        bal2 += 48000.00
        add_tx("CUST-002", None, now - timedelta(days=29), 48000.00, "CREDIT", "SALARY", False, "Logistics Corp Monthly Payroll", bal2)
        bal2 -= 14000.00
        add_tx("CUST-002", "6513", now - timedelta(days=27), -14000.00, "DEBIT", "RENT", True, "Residential House Rent Payment", bal2)
        bal2 -= 11800.00
        add_tx("CUST-002", None, now - timedelta(days=25), -11800.00, "DEBIT", "LOAN_EMI", False, "Auto Debit - Personal Loan", bal2)
        bal2 -= 7800.00
        add_tx("CUST-002", "5411", now - timedelta(days=18), -7800.00, "DEBIT", "GROCERIES", True, "Local Grocery Store Provisions", bal2)
        bal2 -= 3200.00
        add_tx("CUST-002", "4900", now - timedelta(days=12), -3200.00, "DEBIT", "UTILITIES", True, "Electricity & Cooking Gas Cylinder", bal2)
        # MCC 8062: Verified Inpatient Hospitalization Emergency
        bal2 -= 34000.00
        add_tx("CUST-002", "8062", now - timedelta(days=3), -34000.00, "DEBIT", "HEALTHCARE", True, "Apollo Hospital - Emergency Surgery", bal2)
        # MCC 5912: Urgent Post-Op Medications
        bal2 -= 13000.00
        add_tx("CUST-002", "5912", now - timedelta(days=2), -13000.00, "DEBIT", "HEALTHCARE", True, "Apollo Pharmacy - Urgent Medication & Lab", bal2)
        # Remaining balance: 4,200

        # Rohan Verma (Volatile Income): Starting Balance: 38,000
        bal3 = 38000.00
        bal3 -= 18000.00
        add_tx("CUST-003", "6513", now - timedelta(days=28), -18000.00, "DEBIT", "RENT", True, "Studio Apartment Rent", bal3)
        bal3 -= 14500.00
        add_tx("CUST-003", None, now - timedelta(days=25), -14500.00, "DEBIT", "LOAN_EMI", False, "Auto Debit - Equipment Loan", bal3)
        bal3 += 15000.00
        add_tx("CUST-003", None, now - timedelta(days=24), 15000.00, "CREDIT", "INVOICE", False, "Client Retainer Advance", bal3)
        bal3 -= 7500.00
        add_tx("CUST-003", "5411", now - timedelta(days=18), -7500.00, "DEBIT", "GROCERIES", True, "Organic Mart Food Provisions", bal3)
        bal3 -= 4800.00
        add_tx("CUST-003", "4900", now - timedelta(days=12), -4800.00, "DEBIT", "UTILITIES", True, "Cloud Hosting & Fiber Broadband", bal3)
        # Remaining balance: 8,200 (Expected 85,000 invoice delayed)

        db.add_all(transactions)
        db.flush()

        # --------------------------------------------------------------------
        # 4. Seed Feature 3: Enhanced Interventions with Daily Accrual Tracking
        # --------------------------------------------------------------------
        # Intervention 1 for Arun Kumar (Medical Shock)
        # Converts 11,800 monthly EMI into 4 weekly streaming micro-installments of 2,950
        # Tracks daily interest accrual on the temporarily deferred principal
        deferred_p1 = round(11800.00 * 0.75, 2)  # 8,850.00 deferred
        apr1 = loan2.interest_rate_apr           # 13.50%
        daily_rate1 = apr1 / 365.0 / 100.0       # 0.00036986
        days_def1 = 30
        accrued_int1 = round(deferred_p1 * daily_rate1 * days_def1, 2)  # INR 98.20

        itv1 = Intervention(
            id="INT-CUST-002-01",
            loan_id=loan2.id,
            customer_id=cust2.id,
            trigger_reason="EXOGENOUS_MEDICAL_SHOCK",
            projected_deficit=86800.00,
            survival_buffer=79200.00,
            action_type="STREAMING_MICRO_AMORTIZATION",
            original_emi=loan2.monthly_emi,
            adjusted_emi=2950.00,
            deferred_principal=deferred_p1,
            annual_interest_rate=apr1,
            daily_accrual_rate=round(daily_rate1, 8),
            days_deferred=days_def1,
            accrued_interest=accrued_int1,
            forbearance_start_date=now.date(),
            forbearance_end_date=(now + timedelta(days=30)).date(),
            repayment_schedule_type="STREAMING_MICRO",
            status="PROPOSED"
        )

        # Intervention 2 for Rohan Verma (Volatile Income)
        # 14-day grace period extension to align with client invoice settlement
        deferred_p2 = loan3.monthly_emi         # 14,500.00 deferred
        apr2 = loan3.interest_rate_apr           # 11.25%
        daily_rate2 = apr2 / 365.0 / 100.0       # 0.00030822
        days_def2 = 14
        accrued_int2 = round(deferred_p2 * daily_rate2 * days_def2, 2)  # INR 62.57

        itv2 = Intervention(
            id="INT-CUST-003-01",
            loan_id=loan3.id,
            customer_id=cust3.id,
            trigger_reason="INVOICE_DELAY",
            projected_deficit=39630.00,
            survival_buffer=33330.00,
            action_type="GRACE_PERIOD_EXTENSION",
            original_emi=loan3.monthly_emi,
            adjusted_emi=loan3.monthly_emi,
            deferred_principal=deferred_p2,
            annual_interest_rate=apr2,
            daily_accrual_rate=round(daily_rate2, 8),
            days_deferred=days_def2,
            accrued_interest=accrued_int2,
            forbearance_start_date=now.date(),
            forbearance_end_date=(now + timedelta(days=14)).date(),
            repayment_schedule_type="BALLOON_AT_END",
            status="PROPOSED"
        )

        db.add_all([itv1, itv2])
        db.commit()

        print("Seeding completed successfully:")
        print(f" - MCC Codes: {len(mcc_list)}")
        print(f" - Customers: 3")
        print(f" - Loans: 3")
        print(f" - Transactions: {len(transactions)}")
        print(f" - Interventions with Accrual: 2")

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_synthetic_data()
