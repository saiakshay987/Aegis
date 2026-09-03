-- ============================================================================
-- Aegis: Analytical SQL Queries
-- Minimum Survival Buffer & Proactive Distress Detection Queries
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Query 1: Calculate Minimum Survival Buffer for a Single Borrower
-- Parameter: :customer_id, :evaluation_date
-- Buffer Formula: 30-day Essential Expenses + 10% Emergency Margin
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
WHERE c.id = 'CUST-002' -- e.g. Medical Shock archetype
GROUP BY c.id;

-- ----------------------------------------------------------------------------
-- Query 2: Enterprise Portfolio Distress Audit (All Borrowers)
-- Identifies borrowers whose upcoming NACH EMI will breach their survival buffer
-- ----------------------------------------------------------------------------
WITH EssentialExpenses AS (
    SELECT 
        customer_id,
        COALESCE(SUM(ABS(amount)), 0.0) AS essential_spend_30d,
        ROUND(COALESCE(SUM(ABS(amount)), 0.0) * 1.10, 2) AS survival_buffer
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
    COALESCE(lb.current_liquid_balance, 0.0) AS current_liquid_balance,
    l.id AS loan_id,
    l.monthly_emi,
    l.next_due_date,
    COALESCE(ee.survival_buffer, 0.0) AS survival_buffer,
    ROUND(COALESCE(lb.current_liquid_balance, 0.0) - l.monthly_emi, 2) AS projected_balance_post_emi,
    CASE 
        WHEN (COALESCE(lb.current_liquid_balance, 0.0) - l.monthly_emi) < COALESCE(ee.survival_buffer, 0.0) 
        THEN 'CRITICAL_DISTRESS' 
        ELSE 'HEALTHY' 
    END AS distress_status,
    CASE 
        WHEN (COALESCE(lb.current_liquid_balance, 0.0) - l.monthly_emi) < COALESCE(ee.survival_buffer, 0.0) 
        THEN ROUND(COALESCE(ee.survival_buffer, 0.0) - (COALESCE(lb.current_liquid_balance, 0.0) - l.monthly_emi), 2)
        ELSE 0.0 
    END AS projected_buffer_deficit
FROM customers c
JOIN loans l ON c.id = l.customer_id AND l.status = 'ACTIVE'
LEFT JOIN LatestLedgerBalance lb ON c.id = lb.customer_id
LEFT JOIN EssentialExpenses ee ON c.id = ee.customer_id
ORDER BY distress_status DESC, projected_buffer_deficit DESC;
