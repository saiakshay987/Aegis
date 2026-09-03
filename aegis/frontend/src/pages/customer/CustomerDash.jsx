import { Routes, Route } from 'react-router-dom'
import Navbar from '../../components/Navbar.jsx'
import CustomerHome       from './CustomerHome.jsx'
import CustomerProjection from './CustomerProjection.jsx'
import CustomerRepayment  from './CustomerRepayment.jsx'
import CustomerAnomalies  from './CustomerAnomalies.jsx'
import CustomerBuffer     from './CustomerBuffer.jsx'

export default function CustomerDash() {
  return (
    <div className="min-h-screen bg-surface bg-grid">
      <div className="orb w-72 h-72 bg-aegis-700 top-0 right-0 opacity-10" />
      <Navbar role="customer" />
      <main className="max-w-7xl mx-auto px-4 py-8 relative z-10">
        <Routes>
          <Route index             element={<CustomerHome />} />
          <Route path="projection" element={<CustomerProjection />} />
          <Route path="repayment"  element={<CustomerRepayment />} />
          <Route path="anomalies"  element={<CustomerAnomalies />} />
          <Route path="buffer"     element={<CustomerBuffer />} />
        </Routes>
      </main>
    </div>
  )
}
