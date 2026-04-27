export default function Footer() {
  return (
    <footer style={{
      background: '#0A0E1A', borderTop: '1px solid #1E2D45',
      padding: '20px 24px', textAlign: 'center',
      fontSize: 13, color: '#475569',
    }}>
      PrivacyLens · MSc Dissertation · Sateesh Kumar Payyavula · {new Date().getFullYear()}
    </footer>
  )
}
