interface Props { size?: number; color?: string }

export default function LoadingSpinner({ size = 24, color = '#00D4FF' }: Props) {
  return (
    <div style={{
      width: size, height: size,
      border: `2px solid rgba(0,212,255,0.2)`,
      borderTop: `2px solid ${color}`,
      borderRadius: '50%',
      animation: 'spin 0.8s linear infinite',
      display: 'inline-block',
    }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}
