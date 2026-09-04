import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ShieldIcon, ChartIcon, AlertIcon, HeartIcon, ArrowRightIcon, CheckIcon } from '../components/Icons.jsx'

const features = [
  { icon: <ChartIcon className="w-4 h-4" />, title: 'See your full picture', desc: 'A clear view of income, spending and repayment health in one calm dashboard.' },
  { icon: <AlertIcon className="w-4 h-4" />, title: 'Spot pressure early', desc: 'Gentle signals help you act before a difficult month becomes a crisis.' },
  { icon: <HeartIcon className="w-4 h-4" />, title: 'Repay with confidence', desc: 'Flexible plans protect your essentials while keeping you on track.' },
]
const flow = ['Transactions analysed', 'Baseline established', 'Support prepared', 'Recovery monitored']

export default function LandingPage() {
  const nav = useNavigate()
  return <div className="min-h-screen hero-mesh relative overflow-hidden">
    <div className="geometric" />
    <header className="relative z-10 border-b border-violet-100/80 bg-white/70 backdrop-blur-xl">
      <div className="max-w-6xl mx-auto px-6 h-[72px] flex items-center justify-between">
        <div className="flex items-center gap-2.5"><span className="icon-tile !w-9 !h-9"><ShieldIcon className="w-5 h-5" /></span><span className="text-xl font-bold tracking-tight text-slate-900">Aegis</span></div>
        <div className="flex gap-2"><button onClick={() => nav('/login/customer')} className="btn-ghost text-sm">Customer portal</button><button onClick={() => nav('/login/admin')} className="btn-primary text-sm">Bank admin <ArrowRightIcon className="inline w-4 h-4 ml-1" /></button></div>
      </div>
    </header>
    <main className="relative z-10 max-w-6xl mx-auto px-6">
      <section className="grid lg:grid-cols-[1.05fr_.95fr] items-center gap-14 pt-20 pb-20">
        <motion.div initial={{opacity:0,y:18}} animate={{opacity:1,y:0}} transition={{duration:.55}}>
          <div className="inline-flex items-center gap-2 rounded-full bg-violet-50 border border-violet-100 px-3 py-1.5 text-xs font-semibold text-violet-700 mb-7"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Financial clarity, built around you</div>
          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight leading-[1.05] text-slate-950">A calmer way to<br /><span className="gradient-text">move forward.</span></h1>
          <p className="text-slate-600 text-lg leading-8 max-w-xl mt-6 mb-8">Aegis helps borrowers and banks understand financial wellbeing early, with practical support that protects the essentials.</p>
          <div className="flex flex-wrap gap-3"><button onClick={() => nav('/login/customer')} className="btn-primary px-6 py-3">Explore your wellbeing <ArrowRightIcon className="inline w-4 h-4 ml-1" /></button><button onClick={() => nav('/login/admin')} className="btn-ghost px-6 py-3">For bank teams</button></div>
          <div className="flex flex-wrap gap-x-5 gap-y-2 mt-7 text-xs text-slate-500">{['Private by design','Early support','Human-first'].map(x => <span key={x}><CheckIcon className="inline w-3.5 h-3.5 text-violet-600 mr-1" />{x}</span>)}</div>
        </motion.div>
        <motion.div initial={{opacity:0,scale:.96}} animate={{opacity:1,scale:1}} transition={{duration:.65,delay:.12}} className="relative min-h-[390px] flex items-center justify-center">
          <div className="absolute w-72 h-72 rounded-[42px] bg-violet-200/45 rotate-12" /><div className="absolute w-64 h-64 rounded-[38px] border border-violet-300/60 -rotate-12" />
          <div className="relative w-[310px] rounded-3xl bg-white border border-white shadow-[0_24px_70px_rgba(76,29,149,.18)] p-5 rotate-[-4deg]"><div className="flex justify-between items-center mb-7"><div><p className="text-[10px] text-slate-400">Good morning</p><p className="text-sm font-bold text-slate-900">Your financial wellbeing</p></div><span className="icon-tile !w-8 !h-8"><ShieldIcon className="w-4 h-4" /></span></div><div className="rounded-2xl bg-violet-50 p-4 flex items-center gap-4"><div className="w-20 h-20 rounded-full border-[7px] border-violet-600 border-r-violet-200 flex items-center justify-center"><b className="text-xl text-violet-900">78</b></div><div><p className="text-xs font-semibold text-violet-900">Healthy breathing room</p><p className="text-[11px] text-slate-500 mt-1">You are on a steady path.</p></div></div><div className="grid grid-cols-2 gap-3 mt-3"><div className="rounded-xl bg-slate-50 p-3"><p className="text-[10px] text-slate-400">Balance</p><b className="text-sm text-slate-800">₹1,28,450</b></div><div className="rounded-xl bg-slate-50 p-3"><p className="text-[10px] text-slate-400">Next step</p><b className="text-sm text-slate-800">Stay consistent</b></div></div></div>
        </motion.div>
      </section>
      <section className="border-y border-violet-100 py-10"><div className="grid md:grid-cols-4 gap-6">{flow.map((item,i)=><div key={item} className="flex items-center gap-3"><span className="w-8 h-8 rounded-full bg-violet-100 text-violet-700 flex items-center justify-center text-xs font-bold">0{i+1}</span><span className="text-sm text-slate-600">{item}</span></div>)}</div></section>
      <section className="py-16 pb-24"><p className="text-xs font-bold uppercase tracking-[.18em] text-violet-600 text-center mb-3">Built for better decisions</p><h2 className="text-3xl font-bold text-slate-950 text-center mb-10">Support that feels simple.</h2><div className="grid md:grid-cols-3 gap-4">{features.map((f,i)=><motion.div key={f.title} initial={{opacity:0,y:12}} whileInView={{opacity:1,y:0}} viewport={{once:true}} transition={{delay:i*.08}} className="glass rounded-2xl p-6"><div className="icon-tile mb-5">{f.icon}</div><h3 className="font-bold text-slate-900 mb-2">{f.title}</h3><p className="text-sm text-slate-500 leading-6">{f.desc}</p></motion.div>)}</div></section>
    </main>
  </div>
}
