import { motion } from 'framer-motion'
import type { AnalyseResponse, ContradictionReport, DarkPatternReport } from '../../types'

interface Props {
  data: AnalyseResponse
  contradictions?: ContradictionReport | null
  contradictionsLoading?: boolean
  darkPatterns?: DarkPatternReport | null
}

// ── Inlined UI components ─────────────────────────────────────────────────────

function Spinner({ size = 14, color = '#475569' }: { size?: number; color?: string }) {
  return (
    <>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <div style={{
        width: size, height: size,
        border: `2px solid rgba(148,163,184,0.2)`,
        borderTop: `2px solid ${color}`,
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
        display: 'inline-block', flexShrink: 0,
      }} />
    </>
  )
}

function Bar({ value, color = '#00D4FF', height = 5 }: { value: number; color?: string; height?: number }) {
  return (
    <div style={{ background: '#1E2D45', borderRadius: height, height, overflow: 'hidden' }}>
      <div style={{
        width: `${Math.min(100, Math.max(0, value))}%`, height: '100%',
        background: color, borderRadius: height,
        boxShadow: `0 0 8px ${color}60`,
        transition: 'width 0.6s ease',
      }} />
    </div>
  )
}

const GRADE_COLOURS: Record<string, { bg: string; glow: string }> = {
  A: { bg: '#10B981', glow: 'rgba(16,185,129,0.4)'  },
  B: { bg: '#34D399', glow: 'rgba(52,211,153,0.3)'  },
  C: { bg: '#F59E0B', glow: 'rgba(245,158,11,0.4)'  },
  D: { bg: '#F97316', glow: 'rgba(249,115,22,0.4)'  },
  F: { bg: '#EF4444', glow: 'rgba(239,68,68,0.5)'   },
}

function GradeBadge({ grade, score }: { grade: string; score: number }) {
  const c = GRADE_COLOURS[grade] ?? { bg: '#475569', glow: 'transparent' }
  return (
    <div style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
      <div
        className="pulse-in"
        style={{
          width: 96, height: 96, borderRadius: 12,
          background: c.bg,
          boxShadow: `0 0 48px ${c.glow}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 48, fontWeight: 900, color: '#fff',
        }}
      >
        {grade}
      </div>
      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 16, color: '#94A3B8' }}>
        {score.toFixed(0)}/100
      </span>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function SummaryCard({ data, contradictions, contradictionsLoading, darkPatterns }: Props) {
  const { risk_report: rr, readability, compliance, plain_clauses } = data

  const avgPlain = plain_clauses.length
    ? plain_clauses.reduce((s, p) => s + p.reading_grade, 0) / plain_clauses.length
    : 0

  const complianceColour = (s: number) =>
    s >= 75 ? '#10B981' : s >= 50 ? '#F59E0B' : '#EF4444'

  const processingTime = (data.processing_ms / 1000).toFixed(1)
  const analysedAt = new Date().toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })

  const policyDomain = (() => {
    try {
      if (data.policy_name.includes('http')) {
        return new URL(data.policy_name).hostname.replace('www.', '')
      }
    } catch { /* ignore */ }
    return null
  })()

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
      style={{
        background: '#111827',
        border: '1px solid',
        borderImage: 'linear-gradient(135deg, #00D4FF33, #7C3AED33) 1',
        borderRadius: 16,
        padding: 28,
        boxShadow: '0 0 40px rgba(0,212,255,0.06)',
      }}
    >
      {/* Quick stats bar */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 20, flexWrap: 'wrap' }}>
        {[
          { label: `${data.clauses.length} clauses`, color: '#00D4FF' },
          { label: `${rr.top_red_flags.length} red flags`, color: '#EF4444' },
          { label: `${darkPatterns?.total_found ?? 0} dark patterns`, color: '#F59E0B' },
          { label: `${processingTime}s`, color: '#10B981' },
        ].map((stat, i) => (
          <div key={i} style={{
            padding: '4px 12px', borderRadius: 20, fontSize: 12, fontWeight: 600,
            background: `${stat.color}12`, color: stat.color,
            border: `1px solid ${stat.color}30`,
          }}>
            {stat.label}
          </div>
        ))}
        {policyDomain && (
          <div style={{
            padding: '4px 12px', borderRadius: 20, fontSize: 12, fontWeight: 600,
            background: 'rgba(124,58,237,0.1)', color: '#A78BFA',
            border: '1px solid rgba(124,58,237,0.25)',
          }}>
            🌐 {policyDomain}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap' }}>
        {/* Grade badge */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, minWidth: 120 }}>
          <GradeBadge grade={rr.grade} score={rr.overall_score} />
          <div style={{ fontSize: 12, color: '#94A3B8', textAlign: 'center', maxWidth: 120 }}>
            {rr.grade_explanation}
          </div>
        </div>

        {/* Centre metrics */}
        <div style={{ flex: 1, minWidth: 220 }}>
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 13, color: '#94A3B8', marginBottom: 4 }}>Readability</div>
            <div
              title={`Original policy: Grade ${readability.flesch_kincaid_grade.toFixed(1)} — ${readability.comparison_label}. Grade 6 = children's book. Grade 12 = high school. Grade 14+ = university level. Lower is easier to read. PrivacyLens plain rewrites average Grade ${avgPlain.toFixed(1)}.`}
              style={{ fontSize: 15, color: '#F1F5F9', cursor: 'help' }}
            >
              📖 Original: <span style={{ fontFamily: 'JetBrains Mono, monospace', color: '#F59E0B' }}>Grade {readability.flesch_kincaid_grade.toFixed(1)}</span>
              {' → '}
              <span style={{ fontFamily: 'JetBrains Mono, monospace', color: avgPlain < readability.flesch_kincaid_grade ? '#10B981' : '#F97316' }}>
                Grade {avgPlain.toFixed(1)}
              </span>
              {avgPlain < readability.flesch_kincaid_grade ? ' ✨' : ' ⚠'}
            </div>
            <div style={{ fontSize: 11, color: '#475569', marginTop: 3 }}>
              {readability.comparison_label} · {readability.minutes_to_read} min read
            </div>
          </div>

          {contradictionsLoading && (
            <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Spinner size={14} color="#475569" />
              <span style={{ fontSize: 13, color: '#475569' }}>Checking for contradictions...</span>
            </div>
          )}
          {!contradictionsLoading && contradictions && contradictions.total_found > 0 && (
            <div style={{ marginBottom: 16, padding: '6px 12px', background: 'rgba(239,68,68,0.1)', borderRadius: 8, border: '1px solid rgba(239,68,68,0.2)', display: 'inline-block' }}>
              <span style={{ fontSize: 13, color: '#EF4444' }}>⚡ {contradictions.total_found} contradiction{contradictions.total_found !== 1 ? 's' : ''} found</span>
            </div>
          )}
          {!contradictionsLoading && contradictions && contradictions.total_found === 0 && (
            <div style={{ marginBottom: 16, padding: '6px 12px', background: 'rgba(16,185,129,0.08)', borderRadius: 8, border: '1px solid rgba(16,185,129,0.2)', display: 'inline-block' }}>
              <span style={{ fontSize: 13, color: '#10B981' }}>✓ No contradictions found</span>
            </div>
          )}
          {darkPatterns && darkPatterns.total_found > 0 && (() => {
            const dpColor = darkPatterns.total_found >= 3 ? '#EF4444' : '#F59E0B'
            const dpBg    = darkPatterns.total_found >= 3 ? 'rgba(239,68,68,0.1)' : 'rgba(245,158,11,0.1)'
            const dpBorder= darkPatterns.total_found >= 3 ? 'rgba(239,68,68,0.25)' : 'rgba(245,158,11,0.25)'
            return (
              <div style={{ marginBottom: 16, padding: '6px 12px', background: dpBg, borderRadius: 8, border: `1px solid ${dpBorder}`, display: 'inline-block' }}>
                <span style={{ fontSize: 13, color: dpColor }}>
                  ⚠ {darkPatterns.total_found} manipulation tactic{darkPatterns.total_found !== 1 ? 's' : ''} detected
                </span>
              </div>
            )
          })()}

          <div style={{ marginTop: 8 }}>
            <div style={{ fontSize: 13, color: '#94A3B8', marginBottom: 8 }}>Compliance</div>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              {[
                { label: 'GDPR', score: compliance.gdpr_score },
                { label: 'CCPA', score: compliance.ccpa_score },
                { label: 'DPDP', score: compliance.dpdp_score },
              ].map(c => (
                <div key={c.label} style={{ minWidth: 100 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontSize: 12, color: '#94A3B8' }}>{c.label}</span>
                    <span style={{ fontSize: 12, fontFamily: 'JetBrains Mono, monospace', color: complianceColour(c.score) }}>
                      {c.score.toFixed(0)}%
                    </span>
                  </div>
                  <Bar value={c.score} color={complianceColour(c.score)} height={5} />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Flags */}
        <div style={{ minWidth: 220, flex: 1 }}>
          {rr.top_red_flags.slice(0, 3).map((f, i) => (
            <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8, fontSize: 13, color: '#EF4444', alignItems: 'flex-start' }}>
              <span style={{ flexShrink: 0 }}>🚨</span>
              <span>{f}</span>
            </div>
          ))}
          {rr.positive_signals.slice(0, 2).map((s, i) => (
            <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8, fontSize: 13, color: '#10B981', alignItems: 'flex-start' }}>
              <span style={{ flexShrink: 0 }}>✅</span>
              <span>{s}</span>
            </div>
          ))}
          <div style={{ marginTop: 12, fontSize: 11, color: '#475569', fontFamily: 'JetBrains Mono, monospace' }}>
            Analysed on {analysedAt}
          </div>
        </div>
      </div>
    </motion.div>
  )
}
