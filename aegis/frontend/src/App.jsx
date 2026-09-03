import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LandingPage   from './pages/LandingPage.jsx'
import CustomerLogin from './pages/customer/CustomerLogin.jsx'
import CustomerDash  from './pages/customer/CustomerDash.jsx'
import AdminLogin    from './pages/admin/AdminLogin.jsx'
import AdminDash     from './pages/admin/AdminDash.jsx'
import UserDrilldown from './pages/admin/UserDrilldown.jsx'

function ProtectedRoute({ children, role }) {
  const stored = localStorage.getItem('aegis_role')
  if (stored !== role) return <Navigate to="/" replace />
  return children
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"               element={<LandingPage />} />
        <Route path="/login/customer" element={<CustomerLogin />} />
        <Route path="/login/admin"    element={<AdminLogin />} />

        <Route path="/customer/*" element={
          <ProtectedRoute role="customer">
            <CustomerDash />
          </ProtectedRoute>
        }/>

        <Route path="/admin" element={
          <ProtectedRoute role="admin">
            <AdminDash />
          </ProtectedRoute>
        }/>

        <Route path="/admin/user/:userId" element={
          <ProtectedRoute role="admin">
            <UserDrilldown />
          </ProtectedRoute>
        }/>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
