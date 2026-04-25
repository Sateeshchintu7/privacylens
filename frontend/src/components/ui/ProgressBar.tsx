interface Props {
  value: number      // 0–100
  color?: string
  height?: number
  animated?: boolean
  label?: string
}

export default function ProgressBar({ value, color = '#00D4FF', height = 6, animated = true, label }: Props) {
  return (
    <div>
      {label && (
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <span style={{ fontSize: 13, color: '#94A3B8' }}>{label}</span>
          <span style={{ fontSize: 13, fontFamily: 'JetBrains Mono, monospace', color: '#F1F5F9' }}>
            {value.toFixed(0)}%
          </span>
        </div>
      )}
      <div style={{ background: '#1E2D45', borderRadius: height, height, overflow: 'hidden' }}>
        <div
          style={{
            width: `${Math.min(100, Math.max(0, value))}%`,
            height: '100%',
            background: color,
            borderRadius: height,
            boxShadow: `0 0 8px ${color}60`,
            transition: animated ? 'width 0.6s ease' : 'none',
          }}
        />
      </div>
    </div>
  )
}
