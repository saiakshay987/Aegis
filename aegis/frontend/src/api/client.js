import axios from 'axios'

const BASE = '/api'

const http = axios.create({ baseURL: BASE, timeout: 15000 })

// ── Customer / ORM endpoints ──────────────────────────────────────
export const getAssessment    = (uid) => http.get(`/user/${uid}/assessment`).then(r => r.data)
export const getProjection    = (uid) => http.get(`/user/${uid}/projection`).then(r => r.data)
export const getRepaymentPlan = (uid) => http.get(`/user/${uid}/repayment-plan`).then(r => r.data)
export const getAnomalies     = (uid) => http.get(`/user/${uid}/anomalies`).then(r => r.data)
export const postConsent      = (uid, planId) =>
  http.post(`/user/${uid}/consent`, { plan_id: planId }).then(r => r.data)

// ── ML pipeline endpoints (richer data) ──────────────────────────
export const getMLAssessment   = (uid) => http.get(`/user/${uid}/assessment`).then(r => r.data)
export const getMLProjection   = (uid) => http.get(`/user/${uid}/projection`).then(r => r.data)
export const getSurvivalBuffer = (uid) => http.get(`/user/${uid}/survival-buffer`).then(r => r.data)

// ── Admin / Portfolio endpoints ───────────────────────────────────
export const getPortfolioSummary = () => http.get('/portfolio/summary').then(r => r.data)
export const getAtRiskUsers      = () => http.get('/portfolio/at-risk').then(r => r.data)

// ── ML health ────────────────────────────────────────────────────
export const getMLHealth = () => http.get('/ml/health').then(r => r.data)

export default http
