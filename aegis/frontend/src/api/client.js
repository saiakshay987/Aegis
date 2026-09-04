import axios from 'axios'

const BASE = '/api'
const http = axios.create({ baseURL: BASE, timeout: 15000 })

// ---------------------------------------------------------------------------
// Demo-data fallback policy
//
// A few read-only, customer-facing display endpoints fall back to canned
// demo data, but ONLY when the live backend could not be reached at all
// (network error / no response — e.g. the API server is down). This is
// intentional and ALWAYS visible to the caller via the `isDemo` flag on the
// returned value, and always logged with console.error — never silent.
//
// It does NOT apply to:
//   - errors where the backend responded but rejected the request (e.g. a
//     404 for an unknown user ID, a 500). Those are real errors and must
//     propagate to the caller — otherwise CustomerLogin would treat any
//     typed string as a valid login.
//   - portfolio-wide / admin endpoints (getPortfolioSummary, getAtRiskUsers,
//     getMLHealth). Fabricating portfolio-wide numbers for an admin/judge
//     view is actively misleading, so these always propagate errors and the
//     page is responsible for showing a real error state.
//   - mutations (postConsent). Faking a "success" on a write is dangerous.
// ---------------------------------------------------------------------------

async function withDemoFallback(fn, demoValue, label) {
  try {
    const data = await fn()
    return { data, isDemo: false }
  } catch (err) {
    const isConnectionFailure = !err?.response // request never got a response at all
    if (isConnectionFailure) {
      console.error(`[Aegis] Live connection failed for ${label} — showing demo data.`, err)
      return { data: demoValue, isDemo: true }
    }
    // Backend responded (404 unknown user, 500, etc.) — a real error, don't paper over it.
    throw err
  }
}

const demoAssessment = (uid = 'USR0001') => ({
  user_id: uid, name: uid === 'USR0050' ? 'Aarav Mehta' : 'Vansh Patel', age: uid === 'USR0050' ? 29 : 34,
  risk_status: 'Healthy', financial_oxygen_score: 78, balance: 128450, living_floor: 42000,
  monthly_income: 95000, monthly_expenses: 48600, active_loans: 2,
})
const demoProjection = () => ({
  current_balance: 128450,
  projections: { day_30: 141200, day_60: 153800, day_90: 168400 },
  avg_daily_income: 3167, avg_daily_burn: 1620, net_daily_flow: 1547, risk_trend: 'improving',
})
const demoRepayment = () => ({
  current_emi_total: 18400, original_emi: 18400, safe_debit_amount: 18400,
  deferred_amount: 0, deferral_months: 0, hardship_reasons: [],
  rationale: 'Your current repayment plan is within your healthy monthly buffer.',
})
const demoAnomalies = () => ({ anomalies: [], total_anomalies: 0 })
const demoSurvivalBuffer = () => ({
  current_balance: 128450, buffer_amount: 46200, total_monthly_essential: 42000,
  safety_margin_pct: 10, buffer_coverage_months: 3.1, buffer_status: 'strong', ring_fenced: false,
  monthly_essential_breakdown: { rent: 18000, groceries: 9000, utilities: 4000, transport: 6000, other: 5000 },
})

// Customer-facing display data — connection-failure fallback with visible isDemo flag.
export const getAssessment     = (uid) => withDemoFallback(() => http.get(`/user/${uid}/assessment`).then(r => r.data), demoAssessment(uid), 'assessment')
export const getProjection     = (uid) => withDemoFallback(() => http.get(`/user/${uid}/projection`).then(r => r.data), demoProjection(), 'projection')
export const getRepaymentPlan  = (uid) => withDemoFallback(() => http.get(`/user/${uid}/repayment-plan`).then(r => r.data), demoRepayment(), 'repayment plan')
export const getAnomalies      = (uid) => withDemoFallback(() => http.get(`/user/${uid}/anomalies`).then(r => r.data), demoAnomalies(), 'anomalies')
export const getSurvivalBuffer = (uid) => withDemoFallback(() => http.get(`/user/${uid}/survival-buffer`).then(r => r.data), demoSurvivalBuffer(), 'survival buffer')
export const getMLAssessment   = getAssessment
export const getMLProjection   = getProjection

// Mutation — never fake a success.
export const postConsent = (uid, planId) => http.post(`/user/${uid}/consent`, { plan_id: planId }).then(r => r.data)

// Portfolio-wide / admin — never fake, always propagate so the page can show a real error state.
export const getPortfolioSummary = () => http.get('/portfolio/summary').then(r => r.data)
export const getAtRiskUsers      = () => http.get('/portfolio/at-risk').then(r => r.data)
export const getMLHealth         = () => http.get('/ml/health').then(r => r.data)

export default http
