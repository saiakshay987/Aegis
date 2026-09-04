import { Routes, Route } from 'react-router-dom'
import Navbar from '../../components/Navbar.jsx'
import Sidebar from '../../components/Sidebar.jsx'
import CustomerHome from './CustomerHome.jsx'
import CustomerProjection from './CustomerProjection.jsx'
import CustomerRepayment from './CustomerRepayment.jsx'
import CustomerAnomalies from './CustomerAnomalies.jsx'
import CustomerBuffer from './CustomerBuffer.jsx'

export default function CustomerDash() { return <div className="min-h-screen bg-[#f8f8fc] bg-grid"><Navbar role="customer" /><Sidebar role="customer" /><main className="max-w-7xl mx-auto px-4 py-8 relative z-10 lg:pl-[264px]"><Routes><Route index element={<CustomerHome />} /><Route path="projection" element={<CustomerProjection />} /><Route path="repayment" element={<CustomerRepayment />} /><Route path="anomalies" element={<CustomerAnomalies />} /><Route path="buffer" element={<CustomerBuffer />} /></Routes></main></div> }
