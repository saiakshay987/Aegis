import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ShieldIcon, UserIcon, ArrowRightIcon } from '../../components/Icons.jsx'
import Spinner from '../../components/Spinner.jsx'
import { getAssessment } from '../../api/client.js'

const DEMO_IDS = ['USR0001', 'USR0050', 'USR0100', 'USR0250', 'USR0420']
export default function CustomerLogin() {
  const [userId,setUserId]=useState(''); const [loading,setLoading]=useState(false); const [error,setError]=useState(''); const nav=useNavigate()
  const handleLogin=async(uid)=>{
    const id=(uid||userId).trim()
    if(!id){setError('Enter a User ID');return}
    setLoading(true);setError('')
    try{
      // getAssessment only falls back to demo data when the backend is totally
      // unreachable (network error). If the backend is up but doesn't
      // recognize this ID, it throws — caught below — so a typo or a made-up
      // ID is correctly rejected instead of silently "logging in".
      const { isDemo } = await getAssessment(id)
      localStorage.setItem('aegis_uid',id)
      localStorage.setItem('aegis_role','customer')
      localStorage.setItem('aegis_demo_mode', isDemo ? '1' : '0')
      nav('/customer')
    }catch{
      setError('We could not find that profile. Check the ID or try a demo ID below.')
    }finally{
      setLoading(false)
    }
  }
  return <div className="min-h-screen hero-mesh relative overflow-hidden flex items-center justify-center p-4"><div className="geometric" /><div className="relative z-10 w-full max-w-[430px]"><button onClick={()=>nav('/')} className="text-sm text-slate-500 hover:text-violet-700 mb-5">← Back to home</button><motion.div initial={{opacity:0,y:14}} animate={{opacity:1,y:0}} className="glass rounded-3xl p-8"><div className="flex items-center gap-3 mb-8"><span className="icon-tile !w-11 !h-11"><ShieldIcon className="w-5 h-5" /></span><div><p className="text-xs text-violet-600 font-semibold uppercase tracking-wider">Welcome to</p><h1 className="text-2xl font-bold text-slate-950">Aegis customer portal</h1></div></div><p className="text-slate-500 text-sm leading-6 mb-7">Sign in to see a simple, supportive view of your financial wellbeing.</p><label className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 block">Customer ID</label><input className="input-field font-mono mb-4" placeholder="e.g. USR0001" value={userId} onChange={e=>{setUserId(e.target.value.toUpperCase());setError('')}} onKeyDown={e=>e.key==='Enter'&&handleLogin()} autoFocus />{error&&<p className="text-red-600 text-xs mb-4 p-3 bg-red-50 border border-red-100 rounded-xl">{error}</p>}<button onClick={()=>handleLogin()} disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2 py-3">{loading?<Spinner size="sm" />:<><UserIcon className="w-4 h-4" /> Continue <ArrowRightIcon className="w-4 h-4" /></>}</button><div className="mt-7 pt-5 border-t border-slate-100"><p className="text-xs text-slate-400 mb-3">Quick demo access</p><div className="flex flex-wrap gap-2">{DEMO_IDS.map(id=><button key={id} onClick={()=>handleLogin(id)} className="font-mono text-xs px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-slate-500 hover:border-violet-300 hover:text-violet-700">{id}</button>)}</div></div></motion.div></div></div>
}
