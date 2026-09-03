"""
Automated Test Suite for Aegis Database & Rules Engine
Verifies:
  1. Relational schema integrity & foreign key constraints
  2. Data ingestion across the 3 user archetypes
  3. Minimum Survival Buffer mathematical calculation (Essential Spend * 1.10)
  4. Distress evaluation logic & intervention proposals
  5. Pure SQL query execution match with ORM results
"""

import unittest
from datetime import datetime
from sqlalchemy import text
from database import engine, SessionLocal, init_db
from models import Customer, Loan, Transaction, Intervention
from rules_engine import (
    calculate_minimum_survival_buffer,
    evaluate_liquidity_distress,
    SQL_EVALUATE_ALL_CUSTOMERS_DISTRESS,
    SQL_CALCULATE_SURVIVAL_BUFFER
)
from seed_data import seed_synthetic_data


class TestAegisDatabaseAndRulesEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Seed fresh database
        seed_synthetic_data()
        cls.now = datetime.now()

    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_01_schema_and_customers_exist(self):
        """Verify that 3 customer archetypes and active loans exist in the database."""
        customers = self.db.query(Customer).all()
        self.assertEqual(len(customers), 3, "Expected exactly 3 customer archetypes")

        archetypes = {c.archetype for c in customers}
        self.assertSetEqual(archetypes, {"HEALTHY", "MEDICAL_SHOCK", "VOLATILE_INCOME"})

        loans = self.db.query(Loan).filter(Loan.status == "ACTIVE").all()
        self.assertEqual(len(loans), 3, "Expected 3 active loans matching the customers")

    def test_02_healthy_archetype_no_distress(self):
        """Verify Archetype 1 (Healthy) has ample liquidity and triggers NO distress."""
        eval_healthy = evaluate_liquidity_distress("CUST-001", self.db, as_of_date=self.now)
        
        self.assertFalse(eval_healthy["is_distressed"])
        self.assertEqual(eval_healthy["projected_deficit"], 0.0)
        self.assertIsNone(eval_healthy["recommendation"])
        self.assertGreater(
            eval_healthy["projected_balance_post_emi"], 
            eval_healthy["minimum_survival_buffer"],
            "Healthy user post-EMI balance must exceed survival buffer"
        )

    def test_03_medical_shock_archetype_triggers_micro_amortization(self):
        """Verify Archetype 2 (Medical Shock) triggers distress and recommends STREAMING_MICRO_AMORTIZATION."""
        eval_shock = evaluate_liquidity_distress("CUST-002", self.db, as_of_date=self.now)
        
        self.assertTrue(eval_shock["is_distressed"], "Medical shock must trigger distress")
        self.assertGreater(eval_shock["projected_deficit"], 0.0)
        self.assertIsNotNone(eval_shock["recommendation"])
        
        rec = eval_shock["recommendation"]
        self.assertEqual(rec["action_type"], "STREAMING_MICRO_AMORTIZATION")
        self.assertEqual(rec["trigger_reason"], "EXOGENOUS_MEDICAL_SHOCK")
        self.assertLess(rec["adjusted_emi"], rec["original_emi"])

    def test_04_volatile_income_archetype_triggers_grace_period(self):
        """Verify Archetype 3 (Volatile Income) triggers distress and recommends GRACE_PERIOD_EXTENSION."""
        eval_volatile = evaluate_liquidity_distress("CUST-003", self.db, as_of_date=self.now)
        
        self.assertTrue(eval_volatile["is_distressed"], "Volatile income delay must trigger distress")
        self.assertGreater(eval_volatile["projected_deficit"], 0.0)
        self.assertIsNotNone(eval_volatile["recommendation"])
        
        rec = eval_volatile["recommendation"]
        self.assertEqual(rec["action_type"], "GRACE_PERIOD_EXTENSION")
        self.assertEqual(rec["trigger_reason"], "INVOICE_DELAY")

    def test_05_survival_buffer_math(self):
        """Verify Minimum Survival Buffer = 30-day essential debits * 1.10."""
        res = calculate_minimum_survival_buffer("CUST-001", self.db, as_of_date=self.now)
        essential = res["30_day_essential_expenses"]
        margin = res["emergency_margin_10_pct"]
        buffer_val = res["minimum_survival_buffer"]

        self.assertAlmostEqual(margin, round(essential * 0.10, 2), places=2)
        self.assertAlmostEqual(buffer_val, round(essential * 1.10, 2), places=2)

    def test_06_pure_sql_query_matches_orm(self):
        """Verify that pure SQL execution yields identical results to SQLAlchemy ORM."""
        with engine.connect() as conn:
            result = conn.execute(
                text(SQL_CALCULATE_SURVIVAL_BUFFER),
                {"customer_id": "CUST-002", "as_of_date": self.now.strftime("%Y-%m-%d %H:%M:%S")}
            ).mappings().first()

        orm_res = calculate_minimum_survival_buffer("CUST-002", self.db, as_of_date=self.now)

        self.assertAlmostEqual(result["essential_expenses_30d"], orm_res["30_day_essential_expenses"], places=2)
        self.assertAlmostEqual(result["minimum_survival_buffer"], orm_res["minimum_survival_buffer"], places=2)


if __name__ == "__main__":
    unittest.main()
