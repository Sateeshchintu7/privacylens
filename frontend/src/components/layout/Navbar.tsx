import { Link, useLocation } from 'react-router-dom'
import { Shield } from 'lucide-react'

export default function Navbar() {
  const { pathname } = useLocation()

  const linkStyle = (path: string) => ({
    textDecoration: 'none',
    fontSize: 14,
    fontWeight: 500,
    color: pathname === path ? '#00D4FF' : '#94A3B8',
    padding: '6px 12px',
    borderRadius: 6,
    transition: 'color 0.2s',
  })

  return (
    <nav style={{
      position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
      background: 'rgba(10,14,26,0.9)', backdropFilter: 'blur(12px)',
      borderBottom: '1px solid #1E2D45', height: 64,
      display: 'flex', alignItems: 'center', padding: '0 24px',
    }}>
      <div style={{ maxWidth: 1100, width: '100%', margin: '0 auto', display: 'flex', alignItems: 'center', gap: 24 }}>
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 8, textDecoration: 'none' }}>
          <Shield size={22} color="#00D4FF" />
          <span style={{ fontSize: 18, fontWeight: 800, color: '#F1F5F9', letterSpacing: '-0.5px' }}>
            Privacy<span style={{ color: '#00D4FF' }}>Lens</span>
          </span>
        </Link>

        <div style={{ marginLeft: 'auto', display: 'flex', gap: 4, alignItems: 'center' }}>
          <Link to="/" style={linkStyle('/')}>Home</Link>
          <Link to="/analyse" style={linkStyle('/analyse')}>Analyse</Link>
        </div>
      </div>
    </nav>
  )
}
