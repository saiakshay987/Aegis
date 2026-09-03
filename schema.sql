-- ============================================================================
-- Aegis: Dynamic Liquidity Forbearance System
-- Relational Database Schema (SQLite 3)
-- Role: Database Architect
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- Table 1: MCC Codes (Feature 2: Merchant Category Code Guardrail)
-- Enforces Exogenous Shock validation (prevents self-transfer gaming)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mcc_codes (
    code VARCHAR(4) PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL,
    is_essential BOOLEAN NOT NULL DEFAULT 0,
    is_shock_eligible BOOLEAN NOT NULL DEFAULT 0, -- Only specific MCCs (e.g. 8062 Hospital) qualify as non-discretionary shock
    description VARCHAR(255)
);

-- ----------------------------------------------------------------------------
-- Table 2: Customers
-- Stores borrower demographic, income baseline, and credit status
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customers (
    id VARCHAR(36) PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    archetype VARCHAR(30) NOT NULL CHECK (archetype IN ('HEALTHY', 'MEDICAL_SHOCK', 'VOLATILE_INCOME')),
    monthly_income_avg DECIMAL(12, 2) NOT NULL,
    credit_score INT NOT NULL CHECK (credit_score BETWEEN 300 AND 900),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- Table 3: Loans
-- Stores credit facilities, fixed EMI obligations, and NACH mandate statuses
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS loans (
    id VARCHAR(36) PRIMARY KEY,
    customer_id VARCHAR(36) NOT NULL,
    loan_type VARCHAR(50) NOT NULL, -- 'PERSONAL', 'HOME', 'VEHICLE', 'EDUCATION', 'EQUIPMENT'
    principal_amount DECIMAL(12, 2) NOT NULL,
    interest_rate_apr DECIMAL(5, 2) NOT NULL,
    tenure_months INT NOT NULL,
    monthly_emi DECIMAL(12, 2) NOT NULL,
    next_due_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'FORBEARANCE', 'DELINQUENT', 'CLOSED')),
    nach_mandate_active BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- Table 4: Transactions
-- Cashflow ledger records with MCC verification and essential categorization
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    id VARCHAR(36) PRIMARY KEY,
    customer_id VARCHAR(36) NOT NULL,
    mcc_code VARCHAR(4),
    timestamp TIMESTAMP NOT NULL,
    amount DECIMAL(12, 2) NOT NULL, -- Positive for credits, negative for debits
    type VARCHAR(10) NOT NULL CHECK (type IN ('CREDIT', 'DEBIT')),
    category VARCHAR(30) NOT NULL, -- 'SALARY', 'INVOICE', 'GROCERIES', 'UTILITIES', 'RENT', 'HEALTHCARE', 'ENTERTAINMENT', 'SHOPPING', 'LOAN_EMI', 'OTHER'
    is_essential BOOLEAN NOT NULL DEFAULT 0,
    description VARCHAR(255),
    balance_after DECIMAL(12, 2) NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (mcc_code) REFERENCES mcc_codes(code) ON DELETE SET NULL
);

-- ----------------------------------------------------------------------------
-- Table 5: Interventions (Feature 3: Enhanced Daily Accrual Tracking)
-- Tracks automated liquidity forbearance, daily interest accrual, and schedules
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interventions (
    id VARCHAR(36) PRIMARY KEY,
    loan_id VARCHAR(36) NOT NULL,
    customer_id VARCHAR(36) NOT NULL,
    trigger_reason VARCHAR(50) NOT NULL, -- 'LIQUIDITY_BUFFER_BREACH', 'EXOGENOUS_MEDICAL_SHOCK', 'INVOICE_DELAY'
    projected_deficit DECIMAL(12, 2) NOT NULL,
    survival_buffer DECIMAL(12, 2) NOT NULL, -- 30-day essential floor + 10% margin
    action_type VARCHAR(30) NOT NULL CHECK (action_type IN ('STREAMING_MICRO_AMORTIZATION', 'INTEREST_ONLY_PAUSE', 'SPLIT_EMI', 'GRACE_PERIOD_EXTENSION')),
    original_emi DECIMAL(12, 2) NOT NULL,
    adjusted_emi DECIMAL(12, 2) NOT NULL,
    
    -- Feature 3: Daily Financial Tracking & Accrual
    deferred_principal DECIMAL(12, 2) NOT NULL DEFAULT 0.0,
    annual_interest_rate DECIMAL(5, 2) NOT NULL DEFAULT 0.0,
    daily_accrual_rate DECIMAL(10, 8) NOT NULL DEFAULT 0.0, -- (annual_interest_rate / 365.0 / 100.0)
    days_deferred INT NOT NULL DEFAULT 0,
    accrued_interest DECIMAL(12, 2) NOT NULL DEFAULT 0.0, -- (deferred_principal * daily_accrual_rate * days_deferred)
    forbearance_start_date DATE,
    forbearance_end_date DATE,
    repayment_schedule_type VARCHAR(30) DEFAULT 'STREAMING_MICRO' CHECK (repayment_schedule_type IN ('STREAMING_MICRO', 'BALLOON_AT_END', 'TENURE_EXTENSION')),

    status VARCHAR(20) NOT NULL DEFAULT 'PROPOSED' CHECK (status IN ('PROPOSED', 'ACCEPTED', 'ACTIVE', 'COMPLETED', 'REJECTED')),
    initiated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    FOREIGN KEY (loan_id) REFERENCES loans(id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- Indexes for High-Performance Queries
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_transactions_customer_time 
    ON transactions (customer_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_transactions_essential 
    ON transactions (customer_id, is_essential, type, timestamp);

CREATE INDEX IF NOT EXISTS idx_transactions_mcc 
    ON transactions (customer_id, mcc_code);

CREATE INDEX IF NOT EXISTS idx_loans_customer_due 
    ON loans (customer_id, next_due_date, status);

CREATE INDEX IF NOT EXISTS idx_interventions_customer 
    ON interventions (customer_id, status);

-- ----------------------------------------------------------------------------
-- Feature 1: Real-Time SQL View (v_customer_risk_status)
-- Automatically calculates survival buffer, financial runway, and distress status
-- ----------------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_customer_risk_status AS
WITH EssentialSpend AS (
    SELECT 
        customer_id,
        COALESCE(SUM(ABS(amount)), 0.0) AS essential_spend_30d,
        ROUND(COALESCE(SUM(ABS(amount)), 0.0) * 1.10, 2) AS minimum_survival_buffer
    FROM transactions
    WHERE is_essential = 1 
      AND type = 'DEBIT'
      AND timestamp >= DATETIME('now', '-30 days')
    GROUP BY customer_id
),
LatestLedgerBalance AS (
    SELECT 
        customer_id,
        balance_after AS current_liquid_balance
    FROM transactions t1
    WHERE timestamp = (
        SELECT MAX(t2.timestamp) 
        FROM transactions t2 
        WHERE t2.customer_id = t1.customer_id
    )
)
SELECT 
    c.id AS customer_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    c.archetype,
    c.credit_score,
    c.monthly_income_avg,
    COALESCE(lb.current_liquid_balance, 0.0) AS current_liquid_balance,
    l.id AS loan_id,
    l.loan_type,
    l.monthly_emi AS upcoming_emi,
    l.next_due_date,
    l.status AS loan_status,
    COALESCE(es.essential_spend_30d, 0.0) AS essential_spend_30d,
    COALESCE(es.minimum_survival_buffer, 0.0) AS minimum_survival_buffer,
    ROUND(COALESCE(lb.current_liquid_balance, 0.0) - l.monthly_emi, 2) AS projected_balance_post_emi,
    
    -- Financial runway: How many days of essential survival floor the current liquid balance covers
    ROUND((COALESCE(lb.current_liquid_balance, 0.0) / NULLIF(COALESCE(es.essential_spend_30d, 0.0), 0.0)) * 30.0, 1) AS runway_days_remaining,
    
    -- Distress Indicator
    CASE 
        WHEN (COALESCE(lb.current_liquid_balance, 0.0) - l.monthly_emi) < COALESCE(es.minimum_survival_buffer, 0.0) THEN 1 
        ELSE 0 
    END AS is_distressed,

    -- Buffer Deficit
    CASE 
        WHEN (COALESCE(lb.current_liquid_balance, 0.0) - l.monthly_emi) < COALESCE(es.minimum_survival_buffer, 0.0) 
        THEN ROUND(COALESCE(es.minimum_survival_buffer, 0.0) - (COALESCE(lb.current_liquid_balance, 0.0) - l.monthly_emi), 2)
        ELSE 0.0 
    END AS projected_deficit,

    -- Automated Elastic Forbearance Recommendation
    CASE 
        WHEN (COALESCE(lb.current_liquid_balance, 0.0) - l.monthly_emi) >= COALESCE(es.minimum_survival_buffer, 0.0) 
            THEN 'NONE_HEALTHY'
        WHEN c.archetype = 'MEDICAL_SHOCK' 
            THEN 'STREAMING_MICRO_AMORTIZATION'
        WHEN c.archetype = 'VOLATILE_INCOME' 
            THEN 'GRACE_PERIOD_EXTENSION'
        ELSE 'SPLIT_EMI'
    END AS recommended_intervention

FROM customers c
JOIN loans l ON c.id = l.customer_id AND l.status IN ('ACTIVE', 'FORBEARANCE')
LEFT JOIN LatestLedgerBalance lb ON c.id = lb.customer_id
LEFT JOIN EssentialSpend es ON c.id = es.customer_id;
