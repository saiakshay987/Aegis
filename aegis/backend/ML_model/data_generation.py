"""
Project Aegis — Synthetic Banking Data Generator
=================================================
Generates realistic Indian banking transaction data with embedded
financial shock scenarios. Outputs to SQLite database at data/aegis.db

Run: python data_generation.py
"""

import pandas as pd
import numpy as np
import sqlite3
import os
from datetime import datetime, timedelta
import random

# ─── Configuration ────────────────────────────────────────────────────────────

NUM_USERS = 500
START_DATE = datetime(2026, 1, 1)
END_DATE = datetime(2026, 9, 1)
MONTHS = 9

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "aegis.db")

np.random.seed(42)
random.seed(42)

# ─── Indian Reference Data ───────────────────────────────────────────────────

FIRST_NAMES_MALE = [
    "Aarav", "Vivaan", "Aditya", "Arjun", "Sai", "Rahul", "Rohan", "Karthik",
    "Vikram", "Pranav", "Harsh", "Nikhil", "Amit", "Suresh", "Rajesh", "Deepak",
    "Manish", "Ankur", "Gaurav", "Varun", "Sachin", "Mohit", "Ravi", "Ajay",
    "Vijay", "Anand", "Kunal", "Siddharth", "Akash", "Neeraj", "Abhishek",
    "Prateek", "Hemant", "Tushar", "Sandeep", "Vishal", "Ashish", "Sumit",
    "Pankaj", "Tarun", "Dhruv", "Ishaan", "Kabir", "Lakshay", "Mayank",
]

FIRST_NAMES_FEMALE = [
    "Priya", "Ananya", "Ishita", "Sneha", "Neha", "Pooja", "Divya", "Shreya",
    "Kavya", "Riya", "Aisha", "Meera", "Sakshi", "Tanvi", "Nisha", "Kriti",
    "Swati", "Anjali", "Preeti", "Suman", "Aarti", "Rekha", "Sunita", "Deepa",
    "Shweta", "Rashmi", "Sapna", "Komal", "Nandini", "Pallavi", "Jyoti", "Tara",
    "Bhavna", "Chitra", "Disha", "Esha", "Gauri", "Isha", "Juhi", "Kiara",
]

LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Singh", "Kumar", "Patel", "Joshi", "Reddy",
    "Nair", "Menon", "Iyer", "Rao", "Das", "Chatterjee", "Banerjee", "Mukherjee",
    "Bose", "Sen", "Ghosh", "Pillai", "Hegde", "Shetty", "Kamath", "Kulkarni",
    "Deshmukh", "Patil", "Jadhav", "Pawar", "Thakur", "Mishra", "Pandey",
    "Tiwari", "Srivastava", "Saxena", "Agarwal", "Mittal", "Khanna", "Kapoor",
    "Malhotra", "Mehra", "Bhatia", "Arora", "Sethi", "Bajaj", "Dhawan",
    "Chauhan", "Yadav", "Mahajan", "Rathore", "Chowdhury",
]

CITIES = [
    ("Mumbai", "Maharashtra"), ("Delhi", "Delhi"), ("Bangalore", "Karnataka"),
    ("Hyderabad", "Telangana"), ("Chennai", "Tamil Nadu"), ("Kolkata", "West Bengal"),
    ("Pune", "Maharashtra"), ("Ahmedabad", "Gujarat"), ("Jaipur", "Rajasthan"),
    ("Lucknow", "Uttar Pradesh"), ("Chandigarh", "Punjab"), ("Kochi", "Kerala"),
    ("Indore", "Madhya Pradesh"), ("Coimbatore", "Tamil Nadu"), ("Nagpur", "Maharashtra"),
    ("Bhopal", "Madhya Pradesh"), ("Visakhapatnam", "Andhra Pradesh"),
    ("Thiruvananthapuram", "Kerala"), ("Noida", "Uttar Pradesh"), ("Gurgaon", "Haryana"),
]

CITY_COL = {
    "Mumbai": 1.0, "Delhi": 0.92, "Bangalore": 0.90, "Gurgaon": 0.88,
    "Pune": 0.82, "Noida": 0.80, "Hyderabad": 0.78, "Chennai": 0.78,
    "Chandigarh": 0.75, "Kolkata": 0.72, "Kochi": 0.72, "Ahmedabad": 0.70,
    "Thiruvananthapuram": 0.68, "Jaipur": 0.65, "Coimbatore": 0.62,
    "Visakhapatnam": 0.60, "Lucknow": 0.60, "Nagpur": 0.58,
    "Bhopal": 0.55, "Indore": 0.55,
}

OCCUPATIONS = {
    "Software Engineer":     (55000, 180000),
    "Data Analyst":          (35000, 110000),
    "Doctor":                (70000, 250000),
    "Teacher":               (22000, 55000),
    "Bank Manager":          (50000, 120000),
    "Sales Executive":       (22000, 75000),
    "Freelancer":            (15000, 140000),
    "Small Business Owner":  (25000, 200000),
    "Government Employee":   (30000, 85000),
    "Accountant":            (28000, 75000),
    "Marketing Manager":     (40000, 130000),
    "Civil Engineer":        (32000, 95000),
    "Pharmacist":            (28000, 65000),
    "HR Manager":            (38000, 105000),
    "Delivery Executive":    (12000, 30000),
}

LOAN_CONFIGS = {
    "home_loan":       {"principal": (2000000, 8000000), "tenure": (120, 300), "rate": (7.5, 9.5)},
    "personal_loan":   {"principal": (100000, 800000),   "tenure": (12, 60),   "rate": (10.5, 16.0)},
    "vehicle_loan":    {"principal": (200000, 1200000),   "tenure": (36, 84),   "rate": (8.0, 12.0)},
    "education_loan":  {"principal": (400000, 2000000),   "tenure": (60, 120),  "rate": (8.0, 11.0)},
    "credit_card_debt":{"principal": (20000, 250000),     "tenure": (6, 36),    "rate": (24.0, 42.0)},
}

# Scenario distribution for 500 users
SCENARIOS = {
    "healthy":              0.50,
    "medical_shock":        0.10,
    "income_drop":          0.12,
    "debt_spiral":          0.08,
    "lifestyle_inflation":  0.10,
    "mixed_stress":         0.10,
}

# Essential spending categories with monthly ranges as fraction of income
ESSENTIAL_CATEGORIES = {
    "rent":        (0.15, 0.30),
    "groceries":   (0.08, 0.15),
    "utilities":   (0.03, 0.06),
    "transport":   (0.03, 0.08),
    "insurance":   (0.02, 0.05),
    "medical":     (0.01, 0.03),
    "education":   (0.00, 0.05),
}

DISCRETIONARY_CATEGORIES = {
    "dining":         (0.02, 0.08),
    "shopping":       (0.02, 0.10),
    "entertainment":  (0.01, 0.05),
    "travel":         (0.00, 0.06),
    "subscriptions":  (0.005, 0.02),
    "personal_care":  (0.01, 0.03),
}


# ─── Helper Functions ─────────────────────────────────────────────────────────

def calculate_emi(principal, annual_rate, tenure_months):
    """Standard EMI calculation using reducing balance method."""
    r = annual_rate / (12 * 100)  # Monthly interest rate
    if r == 0:
        return principal / tenure_months
    emi = principal * r * (1 + r) ** tenure_months / ((1 + r) ** tenure_months - 1)
    return round(emi)


def assign_scenarios(n):
    """Assign financial scenario to each user."""
    assignments = []
    for scenario, frac in SCENARIOS.items():
        assignments.extend([scenario] * int(n * frac))
    while len(assignments) < n:
        assignments.append("healthy")
    random.shuffle(assignments)
    return assignments


def random_day_in_month(year, month, day_range=(1, 28)):
    """Return a random date within a given month."""
    day = random.randint(day_range[0], min(day_range[1], 28))
    return datetime(year, month, day)


# ─── User Generation ─────────────────────────────────────────────────────────

def generate_users(n=NUM_USERS):
    """Generate n synthetic Indian banking users."""
    scenarios = assign_scenarios(n)
    users = []

    for i in range(n):
        user_id = f"USR{i:04d}"
        gender = random.choice(["M", "F"])
        first = random.choice(FIRST_NAMES_MALE if gender == "M" else FIRST_NAMES_FEMALE)
        last = random.choice(LAST_NAMES)
        age = int(np.random.normal(35, 8))
        age = max(22, min(58, age))
        city, state = random.choice(CITIES)
        occupation = random.choice(list(OCCUPATIONS.keys()))
        low, high = OCCUPATIONS[occupation]

        # Age-adjusted income (older = more experienced, up to a cap)
        age_factor = min(1.0, 0.55 + (age - 22) * 0.0125)
        monthly_income = int(np.random.uniform(low, high) * age_factor)
        monthly_income = round(monthly_income / 500) * 500  # Round to ₹500

        # Freelancers and business owners have volatile income
        income_type = "variable" if occupation in ("Freelancer", "Small Business Owner") else "salaried"

        users.append({
            "user_id": user_id,
            "name": f"{first} {last}",
            "age": age,
            "gender": gender,
            "city": city,
            "state": state,
            "occupation": occupation,
            "income_type": income_type,
            "monthly_income": monthly_income,
            "col_multiplier": CITY_COL[city],
            "scenario": scenarios[i],
            "account_opened": (START_DATE - timedelta(days=random.randint(365, 1825))).strftime("%Y-%m-%d"),
        })

    return pd.DataFrame(users)


# ─── Loan Generation ─────────────────────────────────────────────────────────

def generate_loans(users_df):
    """Generate 0-3 loans per user based on income and occupation."""
    loans = []
    loan_counter = 0

    for _, user in users_df.iterrows():
        income = user["monthly_income"]
        # Number of loans: higher income → more likely to have loans
        if income < 25000:
            n_loans = np.random.choice([0, 1], p=[0.3, 0.7])
        elif income < 60000:
            n_loans = np.random.choice([1, 2], p=[0.6, 0.4])
        else:
            n_loans = np.random.choice([1, 2, 3], p=[0.4, 0.4, 0.2])

        # Debt spiral users always have 2-3 loans
        if user["scenario"] == "debt_spiral":
            n_loans = random.choice([2, 3])

        available_types = list(LOAN_CONFIGS.keys())

        # Lower income users less likely to have home loans
        if income < 40000:
            available_types = [t for t in available_types if t != "home_loan"]

        chosen_types = random.sample(available_types, min(n_loans, len(available_types)))

        for loan_type in chosen_types:
            cfg = LOAN_CONFIGS[loan_type]
            principal = int(np.random.uniform(*cfg["principal"]))
            principal = round(principal / 10000) * 10000  # Round to ₹10,000
            tenure = random.randint(*cfg["tenure"])
            rate = round(np.random.uniform(*cfg["rate"]), 2)
            emi = calculate_emi(principal, rate, tenure)

            # Ensure total EMI doesn't exceed 60% of income for healthy users
            max_months = max(1, min(tenure - 1, 60))
            months_paid = random.randint(1, max_months)
            emi_day = random.randint(1, 10)
            next_due_date = datetime(2026, 9, min(emi_day, 28)).strftime("%Y-%m-%d")

            loans.append({
                "loan_id": f"LN{loan_counter:05d}",
                "id": f"LN{loan_counter:05d}",
                "user_id": user["user_id"],
                "customer_id": user["user_id"],
                "loan_type": loan_type.upper(),
                "principal": principal,
                "principal_amount": float(principal),
                "tenure_months": tenure,
                "interest_rate": rate,
                "interest_rate_apr": float(rate),
                "emi_amount": emi,
                "monthly_emi": float(emi),
                "months_paid": months_paid,
                "months_remaining": tenure - months_paid,
                "emi_day": emi_day,
                "next_due_date": next_due_date,
                "status": "ACTIVE",
                "nach_mandate_active": 1,
                "created_at": f"{user['account_opened']} 00:00:00",
            })
            loan_counter += 1

    return pd.DataFrame(loans)


# ─── Transaction Generation ──────────────────────────────────────────────────

def _generate_income_transactions(user, month_dt, scenario, month_index):
    """Generate income (credit) transactions for a month."""
    txns = []
    income = user["monthly_income"]
    income_type = user["income_type"]

    # ── Apply scenario-based income modifications ──
    if scenario == "income_drop" and month_index >= 5:
        # Income drops 40-65% starting from month 6
        drop_factor = np.random.uniform(0.35, 0.60)
        income = int(income * drop_factor)
    elif scenario == "income_drop" and month_index == 4:
        # Slight dip the month before
        income = int(income * np.random.uniform(0.80, 0.95))

    if income_type == "salaried":
        # Salary credit on 1st-5th of month
        salary_day = random.randint(1, 5)
        salary_date = datetime(month_dt.year, month_dt.month, salary_day)
        # Add ±5% natural variation
        actual_salary = int(income * np.random.uniform(0.95, 1.05))
        txns.append({
            "date": salary_date.strftime("%Y-%m-%d"),
            "amount": actual_salary,
            "type": "credit",
            "category": "salary",
            "description": "Monthly salary credit",
        })
    else:
        # Variable income: 2-4 irregular payments
        n_payments = random.randint(2, 4)
        for _ in range(n_payments):
            pay_day = random.randint(1, 28)
            pay_date = datetime(month_dt.year, month_dt.month, pay_day)
            payment = int((income / n_payments) * np.random.uniform(0.5, 1.5))
            txns.append({
                "date": pay_date.strftime("%Y-%m-%d"),
                "amount": payment,
                "type": "credit",
                "category": "freelance_income",
                "description": random.choice([
                    "Client payment received", "Project milestone payment",
                    "Consulting fee", "Contract payment",
                ]),
            })

    # Occasional UPI received / refunds (10% chance per month)
    if random.random() < 0.10:
        txns.append({
            "date": datetime(month_dt.year, month_dt.month, random.randint(1, 28)).strftime("%Y-%m-%d"),
            "amount": int(np.random.uniform(500, 5000)),
            "type": "credit",
            "category": "upi_received",
            "description": random.choice(["UPI transfer received", "Settlement received", "Refund"]),
        })

    return txns


def _generate_essential_transactions(user, month_dt, scenario, month_index):
    """Generate essential expense transactions for a month."""
    txns = []
    income = user["monthly_income"]
    col = user["col_multiplier"]

    for category, (low_frac, high_frac) in ESSENTIAL_CATEGORIES.items():
        # Skip education for users without education-related context
        if category == "education" and random.random() < 0.6:
            continue

        base_amount = int(income * np.random.uniform(low_frac, high_frac) * col)

        if category == "rent":
            # Rent is a single payment, usually 1st-5th
            rent_day = random.randint(1, 5)
            txns.append({
                "date": datetime(month_dt.year, month_dt.month, rent_day).strftime("%Y-%m-%d"),
                "amount": round(base_amount / 100) * 100,
                "type": "debit",
                "category": "rent",
                "description": "Monthly rent payment",
            })
        elif category == "groceries":
            # 3-6 grocery trips per month
            n_trips = random.randint(3, 6)
            for _ in range(n_trips):
                txns.append({
                    "date": datetime(month_dt.year, month_dt.month, random.randint(1, 28)).strftime("%Y-%m-%d"),
                    "amount": int(base_amount / n_trips * np.random.uniform(0.6, 1.4)),
                    "type": "debit",
                    "category": "groceries",
                    "description": random.choice([
                        "BigBasket order", "Zepto delivery", "DMart purchase",
                        "Local kirana store", "Blinkit order", "JioMart",
                    ]),
                })
        elif category == "utilities":
            # 2-3 utility bills
            for desc in random.sample(["Electricity bill", "Water bill", "Gas bill", "Internet bill", "Mobile recharge"], k=random.randint(2, 3)):
                txns.append({
                    "date": datetime(month_dt.year, month_dt.month, random.randint(5, 20)).strftime("%Y-%m-%d"),
                    "amount": int(base_amount / 3 * np.random.uniform(0.7, 1.3)),
                    "type": "debit",
                    "category": "utilities",
                    "description": desc,
                })
        elif category == "medical":
            # Normal medical: small regular expenses
            if random.random() < 0.4:  # Not every month
                txns.append({
                    "date": datetime(month_dt.year, month_dt.month, random.randint(1, 28)).strftime("%Y-%m-%d"),
                    "amount": int(base_amount * np.random.uniform(0.5, 1.5)),
                    "type": "debit",
                    "category": "medical",
                    "description": random.choice([
                        "Pharmacy purchase", "Doctor consultation",
                        "Lab test", "Medicine order - PharmEasy",
                    ]),
                })
        else:
            # Other essentials: 1-2 transactions
            for _ in range(random.randint(1, 2)):
                txns.append({
                    "date": datetime(month_dt.year, month_dt.month, random.randint(1, 28)).strftime("%Y-%m-%d"),
                    "amount": int(base_amount / 2 * np.random.uniform(0.6, 1.4)),
                    "type": "debit",
                    "category": category,
                    "description": f"{category.replace('_', ' ').title()} payment",
                })

    return txns


def _generate_discretionary_transactions(user, month_dt, scenario, month_index):
    """Generate discretionary spending transactions."""
    txns = []
    income = user["monthly_income"]

    for category, (low_frac, high_frac) in DISCRETIONARY_CATEGORIES.items():
        # Skip some categories randomly for variety
        if random.random() < 0.25:
            continue

        base_amount = int(income * np.random.uniform(low_frac, high_frac))

        # Lifestyle inflation: discretionary spending grows 5-8% per month from month 3
        if scenario == "lifestyle_inflation" and month_index >= 3:
            inflation_factor = 1.0 + 0.07 * (month_index - 2)
            base_amount = int(base_amount * inflation_factor)

        if category == "dining":
            n_outings = random.randint(2, 6)
            for _ in range(n_outings):
                txns.append({
                    "date": datetime(month_dt.year, month_dt.month, random.randint(1, 28)).strftime("%Y-%m-%d"),
                    "amount": int(base_amount / n_outings * np.random.uniform(0.4, 1.8)),
                    "type": "debit",
                    "category": "dining",
                    "description": random.choice([
                        "Swiggy order", "Zomato order", "Restaurant bill",
                        "Cafe Coffee Day", "Starbucks", "Local restaurant",
                    ]),
                })
        elif category == "shopping":
            n_purchases = random.randint(1, 4)
            for _ in range(n_purchases):
                txns.append({
                    "date": datetime(month_dt.year, month_dt.month, random.randint(1, 28)).strftime("%Y-%m-%d"),
                    "amount": int(base_amount / n_purchases * np.random.uniform(0.3, 2.0)),
                    "type": "debit",
                    "category": "shopping",
                    "description": random.choice([
                        "Amazon purchase", "Flipkart order", "Myntra order",
                        "Reliance Digital", "Croma", "Mall purchase",
                    ]),
                })
        elif category == "subscriptions":
            txns.append({
                "date": datetime(month_dt.year, month_dt.month, random.randint(1, 10)).strftime("%Y-%m-%d"),
                "amount": random.choice([149, 199, 299, 499, 599, 799, 999, 1499]),
                "type": "debit",
                "category": "subscriptions",
                "description": random.choice([
                    "Netflix subscription", "Spotify Premium", "Hotstar subscription",
                    "Amazon Prime", "YouTube Premium", "Gym membership",
                ]),
            })
        else:
            for _ in range(random.randint(1, 3)):
                txns.append({
                    "date": datetime(month_dt.year, month_dt.month, random.randint(1, 28)).strftime("%Y-%m-%d"),
                    "amount": int(base_amount / 2 * np.random.uniform(0.5, 2.0)),
                    "type": "debit",
                    "category": category,
                    "description": f"{category.replace('_', ' ').title()} expense",
                })

    return txns


def _generate_shock_transactions(user, month_dt, scenario, month_index):
    """Generate shock-specific transactions based on user scenario."""
    txns = []
    income = user["monthly_income"]

    if scenario == "medical_shock" and month_index in (5, 6):
        # Large medical expense in months 6-7
        if month_index == 5:
            shock_amount = int(np.random.uniform(50000, 200000))
            txns.append({
                "date": datetime(month_dt.year, month_dt.month, random.randint(8, 20)).strftime("%Y-%m-%d"),
                "amount": shock_amount,
                "type": "debit",
                "category": "medical",
                "description": random.choice([
                    "Hospital admission - emergency", "Surgery charges",
                    "ICU charges", "Major medical procedure",
                ]),
            })
        if month_index == 6:
            followup = int(np.random.uniform(10000, 60000))
            txns.append({
                "date": datetime(month_dt.year, month_dt.month, random.randint(5, 25)).strftime("%Y-%m-%d"),
                "amount": followup,
                "type": "debit",
                "category": "medical",
                "description": random.choice([
                    "Follow-up treatment", "Rehabilitation charges",
                    "Post-surgery medication", "Specialist consultation",
                ]),
            })

    elif scenario == "debt_spiral" and month_index >= 4:
        # Cash advances and payday-style borrowing
        if random.random() < 0.5:
            txns.append({
                "date": datetime(month_dt.year, month_dt.month, random.randint(15, 25)).strftime("%Y-%m-%d"),
                "amount": int(np.random.uniform(5000, 30000)),
                "type": "credit",
                "category": "cash_advance",
                "description": "Cash advance / personal borrowing",
            })
        # High-interest repayments
        txns.append({
            "date": datetime(month_dt.year, month_dt.month, random.randint(1, 28)).strftime("%Y-%m-%d"),
            "amount": int(np.random.uniform(3000, 15000)),
            "type": "debit",
            "category": "debt_repayment",
            "description": "Informal loan repayment / interest charges",
        })

    elif scenario == "mixed_stress":
        # Multiple mild stressors
        if month_index == 4 and random.random() < 0.7:
            txns.append({
                "date": datetime(month_dt.year, month_dt.month, random.randint(1, 28)).strftime("%Y-%m-%d"),
                "amount": int(np.random.uniform(15000, 50000)),
                "type": "debit",
                "category": "medical",
                "description": "Unexpected medical expense",
            })
        if month_index >= 6 and random.random() < 0.4:
            txns.append({
                "date": datetime(month_dt.year, month_dt.month, random.randint(1, 28)).strftime("%Y-%m-%d"),
                "amount": int(np.random.uniform(10000, 40000)),
                "type": "debit",
                "category": "emergency",
                "description": random.choice([
                    "Vehicle repair", "Home repair emergency",
                    "Legal fees", "Family emergency transfer",
                ]),
            })

    return txns


def _generate_emi_transactions(user, user_loans, month_dt, scenario, month_index):
    """Generate EMI payment transactions."""
    txns = []

    for _, loan in user_loans.iterrows():
        emi_day = loan["emi_day"]
        emi_date = datetime(month_dt.year, month_dt.month, min(emi_day, 28))

        # Determine if EMI is missed
        missed = False
        if scenario in ("income_drop", "medical_shock", "debt_spiral") and month_index >= 6:
            miss_prob = 0.3 if scenario == "income_drop" else 0.2
            missed = random.random() < miss_prob
        if scenario == "debt_spiral" and month_index >= 7:
            missed = random.random() < 0.45

        if not missed:
            txns.append({
                "date": emi_date.strftime("%Y-%m-%d"),
                "amount": loan["emi_amount"],
                "type": "debit",
                "category": "emi_payment",
                "description": f"EMI - {loan['loan_type'].replace('_', ' ').title()} ({loan['loan_id']})",
            })
        else:
            txns.append({
                "date": emi_date.strftime("%Y-%m-%d"),
                "amount": 0,
                "type": "debit",
                "category": "emi_missed",
                "description": f"EMI MISSED - {loan['loan_type'].replace('_', ' ').title()} ({loan['loan_id']})",
            })

    return txns


def generate_transactions(users_df, loans_df):
    """Generate all transactions for all users across all months."""
    all_txns = []
    txn_counter = 0

    for _, user in users_df.iterrows():
        user_id = user["user_id"]
        scenario = user["scenario"]
        user_loans = loans_df[loans_df["user_id"] == user_id]

        # Starting balance: 1-4 months of income
        balance = int(user["monthly_income"] * np.random.uniform(1.0, 4.0))

        for month_idx in range(MONTHS):
            month_dt = START_DATE + timedelta(days=month_idx * 30)
            year = START_DATE.year + (START_DATE.month + month_idx - 1) // 12
            month = (START_DATE.month + month_idx - 1) % 12 + 1
            month_dt = datetime(year, month, 1)

            month_txns = []

            # 1. Income
            month_txns.extend(_generate_income_transactions(user, month_dt, scenario, month_idx))

            # 2. Essential spending
            month_txns.extend(_generate_essential_transactions(user, month_dt, scenario, month_idx))

            # 3. Discretionary spending
            month_txns.extend(_generate_discretionary_transactions(user, month_dt, scenario, month_idx))

            # 4. EMI payments
            month_txns.extend(_generate_emi_transactions(user, user_loans, month_dt, scenario, month_idx))

            # 5. Shock-specific events
            month_txns.extend(_generate_shock_transactions(user, month_dt, scenario, month_idx))

            # Sort by date and compute running balance
            month_txns.sort(key=lambda x: x["date"])

            for txn in month_txns:
                amt = txn["amount"]
                ttype = txn["type"]
                cat = txn["category"]
                status = "success"

                if ttype == "credit":
                    balance += amt
                else:
                    if balance < amt:
                        # Transaction bounces due to insufficient funds (NACH bounce)
                        status = "bounced"
                        balance -= 500  # NACH bounce fee
                        balance = max(balance, 0)
                    else:
                        balance -= amt

                is_essential = 1 if cat in ESSENTIAL_CATEGORIES or cat in ("emi_payment", "emi_missed") else 0

                all_txns.append({
                    "txn_id": f"TXN{txn_counter:07d}",
                    "id": f"TXN{txn_counter:07d}",
                    "user_id": user_id,
                    "customer_id": user_id,
                    "date": txn["date"],
                    "timestamp": f"{txn['date']} {10 + (txn_counter % 10):02d}:{(txn_counter % 60):02d}:{(txn_counter % 59):02d}",
                    "amount": amt,
                    "type": ttype,
                    "category": cat,
                    "description": txn["description"],
                    "balance_after": balance,
                    "status": status,
                    "is_essential": is_essential,
                })
                txn_counter += 1

    return pd.DataFrame(all_txns)


# ─── Database Writer ──────────────────────────────────────────────────────────

def save_to_sqlite(users_df, loans_df, txns_df):
    """Save all dataframes to SQLite database with dual-key ORM/ML compatibility."""
    os.makedirs(DATA_DIR, exist_ok=True)

    # Remove existing DB
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)

    # Create tables with explicit schemas
    conn.execute("""
        CREATE TABLE users (
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            city TEXT,
            state TEXT,
            occupation TEXT,
            income_type TEXT,
            monthly_income INTEGER,
            col_multiplier REAL,
            scenario TEXT,
            account_opened TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE customers (
            id TEXT PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE,
            phone TEXT UNIQUE,
            archetype TEXT NOT NULL,
            monthly_income_avg REAL NOT NULL,
            credit_score INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE loans (
            id TEXT PRIMARY KEY,
            loan_id TEXT,
            user_id TEXT,
            customer_id TEXT,
            loan_type TEXT,
            principal INTEGER,
            principal_amount REAL,
            tenure_months INTEGER,
            interest_rate REAL,
            interest_rate_apr REAL,
            emi_amount INTEGER,
            monthly_emi REAL,
            months_paid INTEGER,
            months_remaining INTEGER,
            emi_day INTEGER,
            next_due_date TEXT,
            status TEXT,
            nach_mandate_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)

    conn.execute("""
        CREATE TABLE transactions (
            id TEXT PRIMARY KEY,
            txn_id TEXT,
            user_id TEXT,
            customer_id TEXT,
            date TEXT,
            timestamp TIMESTAMP,
            amount REAL,
            type TEXT,
            category TEXT,
            description TEXT,
            balance_after REAL,
            status TEXT,
            is_essential INTEGER DEFAULT 0,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS interventions (
            id TEXT PRIMARY KEY,
            loan_id TEXT NOT NULL,
            customer_id TEXT NOT NULL,
            trigger_reason TEXT NOT NULL,
            projected_deficit REAL NOT NULL,
            survival_buffer REAL NOT NULL,
            action_type TEXT NOT NULL,
            original_emi REAL NOT NULL,
            adjusted_emi REAL NOT NULL,
            status TEXT DEFAULT 'PENDING_CONSENT',
            initiated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (loan_id) REFERENCES loans(id),
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)

    # Create indexes for fast queries
    conn.execute("CREATE INDEX idx_txn_user ON transactions(user_id)")
    conn.execute("CREATE INDEX idx_txn_customer ON transactions(customer_id)")
    conn.execute("CREATE INDEX idx_txn_date ON transactions(date)")
    conn.execute("CREATE INDEX idx_txn_timestamp ON transactions(timestamp)")
    conn.execute("CREATE INDEX idx_txn_user_date ON transactions(user_id, date)")
    conn.execute("CREATE INDEX idx_txn_category ON transactions(category)")
    conn.execute("CREATE INDEX idx_loan_user ON loans(user_id)")
    conn.execute("CREATE INDEX idx_loan_customer ON loans(customer_id)")

    # Build customers DataFrame from users
    customers = []
    for _, u in users_df.iterrows():
        parts = u["name"].split(maxsplit=1)
        first = parts[0]
        last = parts[1] if len(parts) > 1 else "User"
        customers.append({
            "id": u["user_id"],
            "first_name": first,
            "last_name": last,
            "email": f"{u['user_id'].lower()}@aegis-bank.com",
            "phone": f"+9198{random.randint(10000000, 99999999)}",
            "archetype": u["scenario"].upper(),
            "monthly_income_avg": float(u["monthly_income"]),
            "credit_score": random.randint(650, 800),
            "created_at": f"{u['account_opened']} 00:00:00",
            "updated_at": f"{u['account_opened']} 00:00:00",
        })
    customers_df = pd.DataFrame(customers)

    # Insert data
    users_df.to_sql("users", conn, if_exists="append", index=False)
    customers_df.to_sql("customers", conn, if_exists="append", index=False)
    loans_df.to_sql("loans", conn, if_exists="append", index=False)
    txns_df.to_sql("transactions", conn, if_exists="append", index=False)

    conn.commit()

    # Also save CSVs for easy inspection
    users_df.to_csv(os.path.join(DATA_DIR, "users.csv"), index=False)
    loans_df.to_csv(os.path.join(DATA_DIR, "loans.csv"), index=False)
    txns_df.to_csv(os.path.join(DATA_DIR, "transactions.csv"), index=False)

    print(f"\n{'='*60}")
    print(f"  DATABASE SAVED: {DB_PATH}")
    print(f"{'='*60}")

    # Summary stats
    print(f"\n📊 Data Summary:")
    print(f"  Users:        {len(users_df):,}")
    print(f"  Loans:        {len(loans_df):,}")
    print(f"  Transactions: {len(txns_df):,}")
    print(f"\n📋 Scenario Distribution:")
    for scenario, count in users_df["scenario"].value_counts().items():
        print(f"  {scenario:25s} → {count} users ({count/len(users_df)*100:.0f}%)")
    print(f"\n💰 Income Range: ₹{users_df['monthly_income'].min():,} - ₹{users_df['monthly_income'].max():,}")
    print(f"  Median Income: ₹{users_df['monthly_income'].median():,.0f}")
    print(f"\n🏦 Loan Types:")
    for lt, count in loans_df["loan_type"].value_counts().items():
        print(f"  {lt:25s} → {count}")
    print(f"\n📈 Transaction Categories:")
    for cat, count in txns_df["category"].value_counts().head(10).items():
        print(f"  {cat:25s} → {count:,}")

    conn.close()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("🚀 Project Aegis — Synthetic Data Generator")
    print("=" * 60)

    print("\n[1/4] Generating users...")
    users_df = generate_users()
    print(f"  ✓ {len(users_df)} users created")

    print("\n[2/4] Generating loans...")
    loans_df = generate_loans(users_df)
    print(f"  ✓ {len(loans_df)} loans created")

    print("\n[3/4] Generating transactions (this may take a minute)...")
    txns_df = generate_transactions(users_df, loans_df)
    print(f"  ✓ {len(txns_df):,} transactions created")

    print("\n[4/4] Saving to SQLite database...")
    save_to_sqlite(users_df, loans_df, txns_df)

    print("\n✅ Data generation complete!")
    return users_df, loans_df, txns_df


if __name__ == "__main__":
    main()
