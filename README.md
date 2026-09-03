# Aegis: Dynamic Liquidity Forbearance for Transient Financial Shocks

> **Domain 3:** Preventing Financial Distress Before It Becomes a Crisis (Sponsored by Temenos)  
> **Hackathon:** Innovation Bound Hackathon — VIT Chennai  
> **Role 2:** Database Architect (Relational Schema & Rules Engine) — **Branch: Manas**

---

## 1. Problem Context & The Role of Aegis

Modern retail banking ledgers operate on a rigid, 19th-century primitive: **fixed monthly lump-sum NACH/e-mandate debits on calendar dates**. When a historically reliable borrower experiences an exogenous, transient shock (e.g. emergency surgery or delayed client invoice settlement), they face **temporary illiquidity**, not structural insolvency.

When an inflexible bank core executes a 100% debit against depleted balances:
1. **Debit Bounces**: Levies immediate punitive bounce and late fees.
2. **Credit Degradation**: Reporting a 30-day delinquency drops CIBIL/credit score by 40–70 points.
3. **Predatory Debt-Stacking**: Borrowers resort to 36%–48% APR digital payday lenders to avoid default.
4. **NPA Spiral**: A temporary 5-day liquidity mismatch is artificially converted into an unserviceable Non-Performing Asset.

**Aegis solves this** by calculating each borrower's **Minimum Survival Buffer**, predicting cashflow distress days before the debit date, and executing automated, elastic interventions (e.g., Streaming Micro-Amortization, Grace Period Extensions).

---

## 2. Advanced Database Architecture (Role 2)

Implemented in [`schema.sql`](schema.sql) (SQLite 3) and [`models.py`](models.py) (SQLAlchemy 2.0 ORM):

### Key Enterprise Features Added:

1. **Feature 1: Real-Time SQL View (`v_customer_risk_status`)**  
   Pre-computes each borrower's 30-day essential spending, minimum survival buffer, financial runway (in days), liquidity distress flag, and recommended forbearance action directly inside the database engine.
2. **Feature 2: Merchant Category Code Guardrail Table (`mcc_codes`)**  
   Guarantees that emergency forbearance is triggered only by legitimate, non-discretionary shocks (e.g., MCC `8062` Hospitals, `5912` Pharmacies) and prevents system gaming (e.g. self-transfers MCC `6012` or gambling `7995`).
3. **Feature 3: Enhanced Interventions with Daily Interest Accrual Tracking**  
   Tracks financial ledger adjustments on deferred balances during forbearance:
   - $\text{Daily Accrual Rate} = \frac{\text{APR}}{365 \times 100}$
   - $\text{Accrued Interest} = \text{Deferred Principal} \times \text{Daily Rate} \times \text{Days Deferred}$
   - Supports repayment schedules: `STREAMING_MICRO`, `BALLOON_AT_END`, and `TENURE_EXTENSION`.

---

## 3. Relational Entity Breakdown

| Table / View | Purpose | Key Columns |
| :--- | :--- | :--- |
| **`mcc_codes`** | Merchant Category Codes & shock eligibility guardrails | `code`, `category_name`, `is_essential`, `is_shock_eligible` |
| **`customers`** | Demographics, baseline income, and credit status | `id`, `archetype`, `monthly_income_avg`, `credit_score` |
| **`loans`** | Credit facilities, fixed EMI obligations, NACH status | `id`, `customer_id`, `monthly_emi`, `next_due_date`, `status` |
| **`transactions`** | Cashflow ledger linked to MCC codes and essential flags | `id`, `customer_id`, `mcc_code`, `timestamp`, `amount`, `is_essential`, `balance_after` |
| **`interventions`** | Forbearance ledger with daily accrual tracking | `id`, `loan_id`, `trigger_reason`, `deferred_principal`, `daily_accrual_rate`, `days_deferred`, `accrued_interest`, `repayment_schedule_type` |
| **`v_customer_risk_status`** *(VIEW)* | Real-time computed risk and runway engine | `customer_id`, `runway_days_remaining`, `minimum_survival_buffer`, `is_distressed`, `projected_deficit`, `recommended_intervention` |

---

## 4. Minimum Survival Buffer Mathematical Formulation

$$\text{Essential Expenses}_{30d} = \sum_{\substack{t \in \text{Debits}_{30d} \\ \text{is\_essential} = 1}} |t.\text{amount}|$$

$$\text{Minimum Survival Buffer} = \text{Essential Expenses}_{30d} \times 1.10 \quad \text{(10\% Emergency Margin)}$$

$$\text{Projected Post-EMI Balance} = \text{Current Liquid Balance} - \text{Upcoming Scheduled EMI}$$

$$\text{Financial Runway (Days)} = \left( \frac{\text{Current Liquid Balance}}{\text{Essential Expenses}_{30d}} \right) \times 30$$

$$\text{Distress Trigger} = \text{Projected Post-EMI Balance} < \text{Minimum Survival Buffer}$$

---

## 5. Synthetic Borrower Archetypes

Populated via [`seed_data.py`](seed_data.py):

| Archetype | Persona | Financial Profile | Scenario & Aegis Resolution |
| :--- | :--- | :--- | :--- |
| **1. Healthy** | **Priya Sharma** (`CUST-001`) | Income: ₹1,50,000/mo<br>Credit Score: 790<br>EMI: ₹18,500 | Balance: ₹1,77,000. Buffer: ₹50,930. Runway: 90.0 days. **Status: HEALTHY**. No intervention required. |
| **2. Medical Shock** | **Arun Kumar** (`CUST-002`) | Income: ₹48,000/mo<br>Credit Score: 735<br>EMI: ₹11,800 | Suffered ₹47,000 emergency hospital bill (verified via MCC 8062/5912). Liquid balance collapsed to ₹4,200. Buffer: ₹79,200. Runway: 0 days. Deficit: ₹86,800.<br>**Aegis Action:** **`STREAMING_MICRO_AMORTIZATION`** (weekly micro-debits of ₹2,950; daily interest accrued on ₹8,850 deferred principal over 30 days is ₹98.20). |
| **3. Volatile Income** | **Rohan Verma** (`CUST-003`) | Freelancer / UI Consultant<br>Credit Score: 710<br>EMI: ₹14,500 | Delayed ₹85,000 enterprise client invoice. Current balance down to ₹8,200. Buffer: ₹33,330. Runway: 0 days. Deficit: ₹39,630.<br>**Aegis Action:** **`GRACE_PERIOD_EXTENSION`** (14-day shift to align with expected invoice date; daily interest accrued on ₹14,500 over 14 days is ₹62.57). |

---

## 6. How to Use & Query

```bash
# 1. Reset / Seed SQLite database with MCC codes, archetypes, and accruals
python seed_data.py

# 2. Query the real-time Risk View using sqlite3 CLI
sqlite3 aegis.db "SELECT * FROM v_customer_risk_status;"

# 3. Or run analytical verification queries from queries.sql
sqlite3 aegis.db < queries.sql
```
