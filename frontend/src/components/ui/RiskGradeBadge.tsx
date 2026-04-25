interface Props {
  grade: string
  score?: number
  size?: 'sm' | 'md' | 'lg'
  animate?: boolean
}

const GRADE_COLOURS: Record<string, { bg: string; glow: string; text: string }> = {
  A: { bg: '#10B981', glow: 'rgba(16,185,129,0.4)', text: '#fff' },
  B: { bg: '#34D399', glow: 'rgba(52,211,153,0.3)', text: '#fff' },
  C: { bg: '#F59E0B', glow: 'rgba(245,158,11,0.4)', text: '#fff' },
  D: { bg: '#F97316', glow: 'rgba(249,115,22,0.4)', text: '#fff' },
  F: { bg: '#EF4444', glow: 'rgba(239,68,68,0.5)', text: '#fff' },
}

const SIZES = {
  sm: { outer: 36, font: 18, score: 11 },
  md: { outer: 56, font: 28, score: 13 },
  lg: { outer: 96, font: 48, score: 16 },
}

export default function RiskGradeBadge({ grade, score, size = 'md', animate = false }: Props) {
  const c = GRADE_COLOURS[grade] ?? { bg: '#475569', glow: 'transparent', text: '#fff' }
  const s = SIZES[size]

  return (
    <div style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
      <div
        className={animate ? 'pulse-in' : ''}
        style={{
          width: s.outer, height: s.outer,
          borderRadius: 12,
          background: c.bg,
          boxShadow: `0 0 ${s.outer / 2}px ${c.glow}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: s.font,
          fontWeight: 900,
          color: c.text,
        }}
      >
        {grade}
      </div>
      {score !== undefined && (
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: s.score, color: '#94A3B8' }}>
          {score.toFixed(0)}/100
        </span>
      )}
    </div>
  )
}
