import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Shield, Menu, X } from 'lucide-react'

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const isAnalyse = location.pathname === '/analyse'

  return (
    <nav
      style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 50,
        background: scrolled ? 'rgba(10,14,26,0.95)' : 'transparent',
        backdropFilter: scrolled ? 'blur(12px)' : 'none',
        borderBottom: scrolled ? '1px solid #1E2D45' : 'none',
        transition: 'all 0.3s',
        padding: '0 24px',
        height: 64,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}
    >
      {/* Logo */}
      <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 8, textDecoration: 'none' }}>
        <Shield size={24} color="#00D4FF" />
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 18, fontWeight: 700, color: '#00D4FF' }}>
          PrivacyLens
        </span>
      </Link>

      {/* Desktop nav */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }} className="hidden-mobile">
        {!isAnalyse && (
          <Link
            to="/analyse"
            style={{
              padding: '8px 20px', background: '#00D4FF', color: '#0A0E1A',
              borderRadius: 8, textDecoration: 'none', fontSize: 14, fontWeight: 600,
              boxShadow: '0 0 20px rgba(0,212,255,0.3)',
            }}
          >
            Try the Tool →
          </Link>
        )}
      </div>

      {/* Mobile hamburger */}
      <button
        onClick={() => setMenuOpen(!menuOpen)}
        style={{ background: 'none', border: 'none', color: '#94A3B8', cursor: 'pointer', display: 'none' }}
        className="show-mobile"
        aria-label="Menu"
      >
        {menuOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      {/* Mobile menu */}
      {menuOpen && (
        <div style={{
          position: 'fixed', top: 64, left: 0, right: 0,
          background: '#111827', borderBottom: '1px solid #1E2D45',
          padding: 24, display: 'flex', flexDirection: 'column', gap: 16,
        }}>
          <Link to="/analyse" onClick={() => setMenuOpen(false)}
            style={{ color: '#00D4FF', textDecoration: 'none', fontWeight: 600, fontSize: 16 }}>
            Try the Tool →
          </Link>
        </div>
      )}

      <style>{`
        @media (max-width: 640px) {
          .hidden-mobile { display: none !important; }
          .show-mobile { display: block !important; }
        }
        @media (min-width: 641px) {
          .show-mobile { display: none !important; }
        }
      `}</style>
    </nav>
  )
}
