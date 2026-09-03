"""
Aegis Demo & Verification Pipeline
Demonstrates:
  1. Standalone SQL calculation of Minimum Survival Buffer
  2. SQLAlchemy Rules Engine calculating buffers and detecting liquidity distress
  3. Automated generation and storage of dynamic forbearance interventions
"""

import json
from datetime import datetime, timezone
from sqlalchemy import text
from database import engine, SessionLocal
from models import Customer, Loan, Intervention
from rules_engine import (
    calculate_minimum_survival_buffer,
    evaluate_liquidity_distress,
    SQL_EVALUATE_ALL_CUSTOMERS_DISTRESS,
    SQL_CALCULATE_SURVIVAL_BUFFER
)
from seed_data import seed_synthetic_data


def run_demo():
    print("=" * 80)
    print("      AEGIS: DYNAMIC LIQUIDITY FORBEARANCE FOR TRANSIENT FINANCIAL SHOCKS")
    print("         Role: Database Architect & Rules Engine Verification")
    print("=" * 80)

    # 1. Seed database
    seed_synthetic_data()

    now = datetime.now()
    db = SessionLocal()

    try:
        # 2. Execute Pure SQL Analysis across all customers
        print("\n" + "-" * 80)
        print(" [STEP 1] EXECUTING PURE SQL DISTRESS AUDIT QUERY")
        print("-" * 80)
        with engine.connect() as conn:
            result = conn.execute(
                text(SQL_EVALUATE_ALL_CUSTOMERS_DISTRESS), 
                {"as_of_date": now.strftime("%Y-%m-%d %H:%M:%S")}
            )
            rows = result.fetchall()
            print(f"{'NAME':<15} | {'ARCHETYPE':<16} | {'BALANCE':<10} | {'EMI':<8} | {'BUFFER':<10} | {'STATUS':<15} | {'DEFICIT':<10}")
            print("-" * 92)
            for row in rows:
                status = "CRITICAL DISTRESS" if row.is_distressed else "HEALTHY"
                print(f"{row.customer_name:<15} | {row.archetype:<16} | INR {row.current_liquid_balance:<9,.0f} | INR {row.upcoming_emi:<7,.0f} | INR {row.survival_buffer:<9,.0f} | {status:<17} | INR {row.projected_deficit:<9,.2f}")

        # 3. Evaluate each archetype with SQLAlchemy Rules Engine
        print("\n" + "-" * 80)
        print(" [STEP 2] RUNNING ORM RULES ENGINE & GENERATING PROACTIVE INTERVENTIONS")
        print("-" * 80)

        customers = db.query(Customer).all()
        interventions_created = []

        for cust in customers:
            evaluation = evaluate_liquidity_distress(cust.id, db, as_of_date=now)
            print(f"\n>> Analyzing Customer: {cust.first_name} {cust.last_name} ({cust.id})")
            print(f"   Archetype:                  {cust.archetype}")
            print(f"   Credit Score:               {cust.credit_score}")
            print(f"   30-Day Essential Expenses:  INR {evaluation['30_day_essential_expenses']:,.2f}")
            print(f"   10% Emergency Margin:       INR {evaluation['emergency_margin_10_pct']:,.2f}")
            print(f"   Minimum Survival Buffer:    INR {evaluation['minimum_survival_buffer']:,.2f}")
            print(f"   Current Liquid Balance:     INR {evaluation['current_balance']:,.2f}")
            print(f"   Upcoming Loan EMI:          INR {evaluation['upcoming_emi']:,.2f}")
            print(f"   Projected Post-EMI Balance: INR {evaluation['projected_balance_post_emi']:,.2f}")

            if evaluation["is_distressed"]:
                rec = evaluation["recommendation"]
                print(f"   [!WARNING] DISTRESS DETECTED!")
                print(f"   Projected Survival Deficit: INR {evaluation['projected_deficit']:,.2f}")
                print(f"   Intervention Action:        {rec['action_type']}")
                print(f"   Trigger Reason:             {rec['trigger_reason']}")
                print(f"   Adjusted Repayment Amount:  INR {rec['adjusted_emi']:,.2f}")
                print(f"   Strategy Rationale:         {rec['rationale']}")

                # Persist intervention record to database
                loan = db.query(Loan).filter(Loan.customer_id == cust.id, Loan.status == "ACTIVE").first()
                if loan:
                    intervention = Intervention(
                        id=f"INT-{cust.id}-{len(interventions_created)+1:02d}",
                        loan_id=loan.id,
                        customer_id=cust.id,
                        trigger_reason=rec["trigger_reason"],
                        projected_deficit=evaluation["projected_deficit"],
                        survival_buffer=evaluation["minimum_survival_buffer"],
                        action_type=rec["action_type"],
                        original_emi=rec["original_emi"],
                        adjusted_emi=rec["adjusted_emi"],
                        status="PROPOSED"
                    )
                    db.add(intervention)
                    interventions_created.append(intervention)
            else:
                print(f"   [OK] Customer liquidity status is HEALTHY. No intervention required.")

        db.commit()

        # 4. Verify Interventions Table
        print("\n" + "-" * 80)
        print(f" [STEP 3] STORED INTERVENTIONS IN DATABASE ({len(interventions_created)} RECORD(S))")
        print("-" * 80)
        for itv in db.query(Intervention).all():
            print(f"   - Intervention ID: {itv.id} | Action: {itv.action_type} | Customer: {itv.customer_id} | Orig EMI: INR {itv.original_emi:,.2f} -> Adj EMI: INR {itv.adjusted_emi:,.2f} | Status: {itv.status}")

        print("\n" + "=" * 80)
        print(" AEGIS RULES ENGINE VERIFICATION COMPLETED SUCCESSFULLY")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    run_demo()
