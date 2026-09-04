import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { getRepaymentPlan, postConsent } from '../../api/client.js'
import { PageSpinner } from '../../components/Spinner.jsx'
import Card, { CardHeader } from '../../components/Card.jsx'
import DemoBanner from '../../components/DemoBanner.jsx'
import { CheckIcon, CashIcon, ClockIcon, AlertIcon, ShieldIcon, WarnIcon } from '../../components/Icons.jsx'
import Spinner from '../../components/Spinner.jsx'

const fmt = (n) => `₹${Number(n || 0).toLocaleString('en-IN')}`

function PlanCard({ plan, recommended, onConsent, consenting, disableConsent }) {
  const typeLabels = {
    reduced_emi:      { label: 'Reduced EMI',       color: 'aegis',   icon: <CashIcon className="w-4 h-4"/>   },
    emi_holiday:      { label: 'EMI Holiday',        color: 'warning', icon: <ClockIcon className="w-4 h-4"/>  },
    tenure_extension: { label: 'Tenure Extension',   color: 'blue',    icon: <AlertIcon className="w-4 h-4"/>  },
  }
  const meta  = typeLabels[plan.plan_type] || typeLabels.reduced_emi
  const colors = {
    aegis:   'border-aegis-600/50 bg-aegis-900/20',
    warning: 'border-warning/40  bg-warning/5',
    blue:    'border-blue-600/40 bg-blue-900/10',
  }

  return (
    <div className={`glass rounded-2xl p-5 border ${colors[meta.color]} ${recommended ? 'ring-1 ring-aegis-500' : ''}`}>
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className={`text-${meta.color === 'aegis' ? 'aegis-400' : meta.color === 'warning' ? 'warning' : 'blue-400'}`}>
            {meta.icon}
          </span>
          <span className="font-semibold text-sm">{meta.label}</span>
        </div>
        {recommended && (
          <span className="text-xs bg-aegis-600/20 border border-aegis-600/40 text-aegis-300 px-2 py-0.5 rounded-full">
            Recommended
          </span>
        )}
      </div>
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div>
          <p className="text-xs text-slate-500">New EMI</p>
          <p className="font-bold text-slate-900">{fmt(plan.recommended_emi)}</p>
        </div>
        <div>
          <p className="text-xs text-slate-500">Reduction</p>
          <p className="font-bold text-success">↓ {plan.reduction_pct}%</p>
        </div>
        <div>
          <p className="text-xs text-slate-500">Duration</p>
          <p className="font-bold text-slate-900">{plan.duration_months} months</p>
        </div>
        <div>
          <p className="text-xs text-slate-500">Interest Impact</p>
          <p className="font-bold text-warning">{fmt(plan.total_interest_impact)}</p>
        </div>
      </div>
      <p className="text-xs text-slate-400 mb-4">{plan.description}</p>
      {recommended && (
        disableConsent ? (
          <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-xl px-3 py-2 text-center">
            Can't accept a plan while showing demo data
          </p>
        ) : (
          <button
            onClick={() => onConsent(plan.plan_id)}
            disabled={consenting}
            className="btn-primary w-full flex items-center justify-center gap-2 py-2.5"
          >
            {consenting ? <Spinner size="sm" /> : <><CheckIcon className="w-4 h-4" /> Accept this plan</>}
          </button>
        )
      )}
    </div>
  )
}

export default function CustomerRepayment() {
  const [data,      setData]      = useState(null)
  const [isDemo,    setIsDemo]    = useState(false)
  const [loading,   setLoading]   = useState(true)
  const [consenting,setConsenting]= useState(false)
  const [accepted,  setAccepted]  = useState(false)
  const [consentMsg,setConsentMsg]= useState('')
  const uid = localStorage.getItem('aegis_uid')

  useEffect(() => {
    getRepaymentPlan(uid).then(({ data, isDemo }) => { setData(data); setIsDemo(isDemo) }).finally(() => setLoading(false))
  }, [uid])

  const handleConsent = async (planId) => {
    setConsenting(true)
    try {
      const res = await postConsent(uid, planId)
      setAccepted(true)
      setConsentMsg(res.message || 'Consent recorded successfully.')
    } catch {
      setConsentMsg('Failed to record consent. Please try again.')
    } finally {
      setConsenting(false)
    }
  }

  if (loading) return <PageSpinner />

  // Not eligible
  if (data && data.eligibility === false) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Adaptive Repayment</h1>
        <Card className="p-8 text-center">
          <CheckIcon className="w-12 h-12 text-success mx-auto mb-4" />
          <h2 className="text-xl font-bold text-success mb-2">You're in great shape!</h2>
          <p className="text-slate-400">{data.reason || 'Your current income comfortably covers your EMI obligations.'}</p>
          <div className="mt-6 grid sm:grid-cols-3 gap-4 text-left">
            <div className="glass rounded-xl p-4">
              <p className="text-xs text-slate-400">Monthly Income</p>
              <p className="font-bold text-slate-900">{fmt(data.projected_monthly_income)}</p>
            </div>
            <div className="glass rounded-xl p-4">
              <p className="text-xs text-slate-400">Total EMI</p>
              <p className="font-bold text-slate-900">{fmt(data.current_emi_total)}</p>
            </div>
            <div className="glass rounded-xl p-4">
              <p className="text-xs text-slate-400">Surplus</p>
              <p className="font-bold text-success">{fmt(data.surplus)}</p>
            </div>
          </div>
        </Card>
      </div>
    )
  }

  if (!data) return <div className="text-danger text-center py-20">Could not load repayment data.</div>

  return (
    <div className="space-y-6">
      {isDemo && <DemoBanner label="your repayment plan" />}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold">Adaptive Repayment Plan</h1>
        <p className="text-slate-400 text-sm mt-0.5">
          Aegis has detected financial pressure and prepared restructuring options
        </p>
      </motion.div>

      {/* Consent success */}
      <AnimatePresence>
        {accepted && (
          <motion.div
            initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="glass border border-success/40 rounded-2xl p-4 flex items-start gap-3 bg-success/5"
          >
            <ShieldIcon className="w-5 h-5 text-success flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-success">Plan Accepted</p>
              <p className="text-sm text-slate-300 mt-0.5">{consentMsg}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Hardship reasons */}
      {data.hardship_reasons?.length > 0 && (
        <Card className="p-5">
          <CardHeader title="Detected Hardship Signals" icon={<WarnIcon className="w-4 h-4"/>} />
          <div className="flex flex-wrap gap-2">
            {data.hardship_reasons.map((r, i) => (
              <span key={i} className="text-xs bg-warning/10 border border-warning/30 text-warning px-3 py-1 rounded-full">
                {r}
              </span>
            ))}
          </div>
        </Card>
      )}

      {/* Rationale */}
      {data.rationale && (
        <Card className="p-5 border-l-2 border-l-aegis-500">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Aegis Recommends</p>
          <p className="text-sm text-slate-200 leading-relaxed italic">"{data.rationale}"</p>
        </Card>
      )}

      {/* Financial summary */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4">
          <p className="text-xs text-slate-400 mb-1">Current EMI</p>
          <p className="text-xl font-bold text-slate-900">{fmt(data.original_emi ?? data.current_emi_total)}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-slate-400 mb-1">Safe Debit</p>
          <p className="text-xl font-bold text-success">{fmt(data.safe_debit_amount ?? data.available_for_emi)}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-slate-400 mb-1">Deferred</p>
          <p className="text-xl font-bold text-warning">{fmt(data.deferred_amount ?? data.gap_amount)}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-slate-400 mb-1">Deferral Period</p>
          <p className="text-xl font-bold text-slate-900">{data.deferral_months ?? data.recommended_plan?.duration_months ?? 0} mo</p>
        </Card>
      </div>

      {/* Plan cards */}
      {(data.recommended_plan || data.plan_id) && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Available Plans</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Recommended */}
            {data.recommended_plan && (
              <PlanCard
                plan={data.recommended_plan}
                recommended
                onConsent={handleConsent}
                consenting={consenting}
                disableConsent={isDemo}
              />
            )}
            {/* Alternatives */}
            {(data.alternative_plans || []).map((p, i) => (
              <PlanCard key={i} plan={p} recommended={false} onConsent={handleConsent} consenting={consenting} disableConsent={isDemo} />
            ))}
            {/* Fallback single plan from ORM endpoint */}
            {!data.recommended_plan && data.plan_id && (
              <PlanCard
                plan={{
                  plan_id: data.plan_id,
                  plan_type: 'reduced_emi',
                  recommended_emi: data.safe_debit_amount,
                  reduction_pct: Math.round((1 - (data.safe_debit_amount / (data.original_emi || 1))) * 100),
                  duration_months: data.deferral_months,
                  total_interest_impact: 0,
                  description: data.rationale,
                }}
                recommended
                onConsent={handleConsent}
                consenting={consenting}
                disableConsent={isDemo}
              />
            )}
          </div>
        </div>
      )}

      {/* Per-loan breakdown */}
      {data.per_loan_details?.length > 0 && (
        <Card className="p-5">
          <CardHeader title="Per-Loan Breakdown" icon={<CashIcon className="w-4 h-4"/>} />
          <div className="space-y-3">
            {data.per_loan_details.map((l, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                <div>
                  <p className="text-sm font-medium capitalize">{l.loan_type?.replace(/_/g,' ')}</p>
                  <p className="text-xs text-slate-400">{l.remaining_months} months remaining · {l.interest_rate}%</p>
                </div>
                <p className="font-bold text-slate-900">{fmt(l.current_emi)}</p>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}
