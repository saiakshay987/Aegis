-- ============================================================================
-- Aegis: Dynamic Liquidity Forbearance System
-- Relational Database Schema (SQLite 3)
-- Role: Database Architect
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- Table 1: Customers
-- Stores borrower profile, income baseline, and risk metadata
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
-- Table 2: Loans
-- Stores credit facilities, fixed EMI obligations, and NACH mandate statuses
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS loans (
    id VARCHAR(36) PRIMARY KEY,
    customer_id VARCHAR(36) NOT NULL,
    loan_type VARCHAR(50) NOT NULL, -- 'PERSONAL', 'HOME', 'VEHICLE', 'EDUCATION'
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
-- Table 3: Transactions
-- Ledger records used to calculate cashflows and essential living floors
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    id VARCHAR(36) PRIMARY KEY,
    customer_id VARCHAR(36) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    amount DECIMAL(12, 2) NOT NULL, -- Positive for credits, negative for debits
    type VARCHAR(10) NOT NULL CHECK (type IN ('CREDIT', 'DEBIT')),
    category VARCHAR(30) NOT NULL, -- 'SALARY', 'INVOICE', 'GROCERIES', 'UTILITIES', 'RENT', 'HEALTHCARE', 'ENTERTAINMENT', 'SHOPPING', 'LOAN_EMI', 'OTHER'
    is_essential BOOLEAN NOT NULL DEFAULT 0, -- 1 if non-discretionary living expense (groceries, rent, medical, utilities)
    description VARCHAR(255),
    balance_after DECIMAL(12, 2) NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- Table 4: Interventions
-- Records automated liquidity forbearance offers to preempt defaults
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interventions (
    id VARCHAR(36) PRIMARY KEY,
    loan_id VARCHAR(36) NOT NULL,
    customer_id VARCHAR(36) NOT NULL,
    trigger_reason VARCHAR(50) NOT NULL, -- 'LIQUIDITY_BUFFER_BREACH', 'EXOGENOUS_MEDICAL_SHOCK', 'INVOICE_DELAY'
    projected_deficit DECIMAL(12, 2) NOT NULL,
    survival_buffer DECIMAL(12, 2) NOT NULL, -- 30-day essential floor + 10% emergency margin
    action_type VARCHAR(30) NOT NULL CHECK (action_type IN ('STREAMING_MICRO_AMORTIZATION', 'INTEREST_ONLY_PAUSE', 'SPLIT_EMI', 'GRACE_PERIOD_EXTENSION')),
    original_emi DECIMAL(12, 2) NOT NULL,
    adjusted_emi DECIMAL(12, 2) NOT NULL,
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

CREATE INDEX IF NOT EXISTS idx_loans_customer_due 
    ON loans (customer_id, next_due_date, status);

CREATE INDEX IF NOT EXISTS idx_interventions_customer 
    ON interventions (customer_id, status);
