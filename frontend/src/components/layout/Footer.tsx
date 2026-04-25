import { Shield } from 'lucide-react'

export default function Footer() {
  return (
    <footer style={{
      borderTop: '1px solid #1E2D45',
      padding: '32px 24px',
      textAlign: 'center',
      color: '#475569',
      fontSize: 13,
      background: '#111827',
    }}>
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <Shield size={16} color="#00D4FF" />
        <span style={{ color: '#94A3B8', fontWeight: 600 }}>PrivacyLens</span>
      </div>
      <p>Built for MSc Cyber Security &amp; Human Factors</p>
      <p style={{ marginTop: 4 }}>
        Sateesh Kumar Payyavula · University · 2025-26
      </p>
    </footer>
  )
}
