import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Navbar from './components/layout/Navbar'
import Footer from './components/layout/Footer'
import LandingPage from './pages/LandingPage'
import AnalysePage from './pages/AnalysePage'

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/"        element={<LandingPage />} />
        <Route path="/analyse" element={<AnalysePage />} />
        <Route path="*"        element={
          <div style={{ textAlign: 'center', padding: '120px 24px', color: '#94A3B8' }}>
            <div style={{ fontSize: 72, marginBottom: 16 }}>404</div>
            <div style={{ fontSize: 18 }}>Page not found</div>
            <a href="/" style={{ color: '#00D4FF', textDecoration: 'none', display: 'block', marginTop: 20 }}>← Back to home</a>
          </div>
        } />
      </Routes>
      <Footer />
    </BrowserRouter>
  )
}
