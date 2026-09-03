-- ============================================================================
-- Aegis: Analytical SQL Queries
-- Includes Feature 1 (Risk View), Feature 2 (MCC Guardrail), and Feature 3 (Daily Accrual)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Query 1: Feature 1 - Real-Time Portfolio Risk View (v_customer_risk_status)
-- Evaluates financial runway (in days), survival buffer, and distress status
-- ----------------------------------------------------------------------------
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
    CASE WHEN is_distressed = 1 THEN 'CRITICAL_DISTRESS' ELSE 'HEALTHY' END AS liquidity_status,
    projected_deficit,
    recommended_intervention
FROM v_customer_risk_status
ORDER BY is_distressed DESC, projected_deficit DESC;

-- ----------------------------------------------------------------------------
-- Query 2: Feature 2 - Exogenous Shock Verification via MCC Guardrail
-- Verifies whether borrower expenditures originate from legitimate shock categories
-- (e.g. Hospital MCC 8062, Pharmacy MCC 5912) vs. unverified self-transfers (MCC 6012)
-- ----------------------------------------------------------------------------
SELECT 
    t.customer_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    t.timestamp,
    t.description,
    t.mcc_code,
    m.category_name,
    m.is_essential,
    m.is_shock_eligible,
    ABS(t.amount) AS expenditure_amount,
    CASE 
        WHEN m.is_shock_eligible = 1 THEN 'VERIFIED_EXOGENOUS_SHOCK'
        WHEN m.is_essential = 1 THEN 'STANDARD_ESSENTIAL_EXPENSE'
        ELSE 'DISCRETIONARY_OR_SELF_TRANSFER'
    END AS guardrail_classification
FROM transactions t
JOIN customers c ON t.customer_id = c.id
LEFT JOIN mcc_codes m ON t.mcc_code = m.code
WHERE t.type = 'DEBIT' 
  AND t.timestamp >= DATETIME('now', '-14 days')
ORDER BY t.timestamp DESC;

-- ----------------------------------------------------------------------------
-- Query 3: Feature 3 - Daily Interest Accrual & Forbearance Financial Ledger
-- Calculates daily interest accrued on deferred principal balances during forbearance
-- ----------------------------------------------------------------------------
SELECT 
    i.id AS intervention_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    i.action_type,
    i.trigger_reason,
    i.original_emi,
    i.adjusted_emi,
    i.deferred_principal,
    i.annual_interest_rate AS apr_pct,
    ROUND(i.daily_accrual_rate * 100, 5) || '% / day' AS daily_rate,
    i.days_deferred,
    i.accrued_interest AS total_accrued_interest,
    i.repayment_schedule_type,
    i.forbearance_start_date,
    i.forbearance_end_date,
    i.status
FROM interventions i
JOIN customers c ON i.customer_id = c.id;

-- ----------------------------------------------------------------------------
-- Query 4: Single Customer Minimum Survival Buffer Calculation
-- Parameter: CUST-002
-- Formula: 30-day essential debits + 10% emergency margin
-- ----------------------------------------------------------------------------
SELECT 
    c.id AS customer_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    c.archetype,
    c.credit_score,
    COALESCE(SUM(ABS(t.amount)), 0.0) AS essential_expenses_30d,
    ROUND(COALESCE(SUM(ABS(t.amount)), 0.0) * 0.10, 2) AS emergency_margin_10pct,
    ROUND(COALESCE(SUM(ABS(t.amount)), 0.0) * 1.10, 2) AS minimum_survival_buffer
FROM customers c
LEFT JOIN transactions t 
    ON c.id = t.customer_id 
    AND t.is_essential = 1 
    AND t.type = 'DEBIT'
    AND t.timestamp >= DATETIME('now', '-30 days')
WHERE c.id = 'CUST-002'
GROUP BY c.id;
