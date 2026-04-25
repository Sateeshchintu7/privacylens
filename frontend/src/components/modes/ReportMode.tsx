import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { startReport, getReportStatus } from '../../api/client'
import LoadingSpinner from '../ui/LoadingSpinner'
import ProgressBar from '../ui/ProgressBar'
import type { AnalyseResponse } from '../../types'

interface Props { data: AnalyseResponse; language?: string }

type Report = Record<string, unknown>

const POLL_INTERVAL = 3_000
const MAX_POLLS = 40 // 2 min

function scoreColor(s: number) {
  if (s >= 75) return '#10B981'
  if (s >= 50) return '#F59E0B'
  if (s >= 25) return '#F97316'
  return '#EF4444'
}

export default function ReportMode({ data, language = 'en' }: Props) {
  const [report, setReport]   = useState<Report | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState<string | null>(null)
  const [section, setSection] = useState<string>('summary')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
  }

  useEffect(() => {
    const policyText = data.policy_text || data.plain_clauses.map(c => c.plain_summary).join('\n')
    if (!policyText || policyText.length < 100) {
      setError('Policy text unavailable for comprehensive report.')
      return
    }

    setLoading(true)
    setError(null)
    setReport(null)

    let jobId = ''
    startReport({ content: policyText, input_type: 'text', language })
      .then(res => {
        jobId = res.data.job_id
        let polls = 0
        pollRef.current = setInterval(async () => {
          polls++
          if (polls > MAX_POLLS) {
            stopPolling()
            setError('Report timed out. Please try again.')
            setLoading(false)
            return
          }
          try {
            const status = await getReportStatus(jobId)
            if (status.data.status === 'complete' && status.data.result) {
              stopPolling()
              setReport(status.data.result as Report)
              setLoading(false)
            } else if (status.data.status === 'error') {
              stopPolling()
              setError(status.data.error ?? 'Report generation failed.')
              setLoading(false)
            }
          } catch { /* keep polling on network blip */ }
        }, POLL_INTERVAL)
      })
      .catch(() => {
        setError('Could not start report. Please try again.')
        setLoading(false)
      })

    return stopPolling
  }, [data, language])

  if (loading) return (
    <div style={{ background: '#111827', border: '1px solid #1E2D45', borderRadius: 16, padding: 40, textAlign: 'center' }}>
      <LoadingSpinner size={40} />
      <div style={{ marginTop: 16, color: '#94A3B8', fontSize: 15 }}>Generating comprehensive report...</div>
      <div style={{ marginTop: 8, color: '#475569', fontSize: 13 }}>One Gemini call analyses the whole policy coherently</div>
    </div>
  )

  if (error) return (
    <div style={{ background: '#111827', border: '1px solid #1E2D45', borderRadius: 16, padding: 28 }}>
      <div style={{ color: '#EF4444', marginBottom: 12 }}>{error}</div>
    </div>
  )

  if (!report) return null

  const summary   = report.plain_summary as Record<string, string> ?? {}
  const verdict   = report.final_verdict as Record<string, unknown> ?? {}
  const comp      = report.compliance   as Record<string, unknown> ?? {}
  const redFlags  = (report.red_flags   as unknown[]) ?? []
  const posSig    = (report.positive_signals as unknown[]) ?? []
  const clauses   = (report.clause_analysis as unknown[]) ?? []
  const darkPat   = (report.dark_patterns as unknown[]) ?? []

  const tabs: [string, string][] = [
    ['summary',    '📋 Summary'],
    ['verdict',    '⚖️ Verdict'],
    ['compliance', '🏛 Compliance'],
    ['clauses',    '🔍 Clauses'],
    ['flags',      '🚩 Flags'],
  ]

  const tabStyle = (id: string) => ({
    padding: '8px 16px', borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 600,
    background: section === id ? 'rgba(124,58,237,0.15)' : 'transparent',
    color: section === id ? '#C4B5FD' : '#94A3B8',
    border: section === id ? '1px solid rgba(124,58,237,0.4)' : '1px solid transparent',
  })

  return (
    <div style={{ background: '#111827', border: '1px solid #1E2D45', borderRadius: 16, padding: 24 }}>
      <div style={{ display: 'flex', gap: 8, marginBottom: 24, flexWrap: 'wrap' }}>
        {tabs.map(([id, label]) => (
          <button key={id} style={tabStyle(id)} onClick={() => setSection(id)}>{label}</button>
        ))}
      </div>

      {section === 'summary' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Card title="Overview" color="#00D4FF">
            <p style={{ fontSize: 15, color: '#F1F5F9', lineHeight: 1.7 }}>{summary.overview}</p>
          </Card>
          {summary.analogy && (
            <Card title="Simple Analogy" color="#7C3AED">
              <p style={{ fontSize: 14, color: '#CBD5E1', lineHeight: 1.7, fontStyle: 'italic' }}>"{summary.analogy}"</p>
            </Card>
          )}
          {summary.the_catch && (
            <Card title="The Catch" color="#EF4444">
              <p style={{ fontSize: 14, color: '#FCA5A5', lineHeight: 1.7 }}>{summary.the_catch}</p>
            </Card>
          )}
          {(report.data_collected as unknown[] ?? []).length > 0 && (
            <Card title="Data Collected" color="#F59E0B">
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 8 }}>
                {(report.data_collected as Record<string, string>[]).map((d, i) => (
                  <div key={i} style={{ padding: '10px 14px', background: '#0A0E1A', borderRadius: 8, borderLeft: `3px solid ${d.risk_level === 'critical' ? '#EF4444' : d.risk_level === 'high' ? '#F97316' : '#F59E0B'}` }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: '#F1F5F9' }}>{d.type}</div>
                    <div style={{ fontSize: 12, color: '#94A3B8', marginTop: 3 }}>{d.why_they_want_it}</div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </motion.div>
      )}

      {section === 'verdict' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <div style={{
            padding: 28, borderRadius: 16, textAlign: 'center', marginBottom: 20,
            background: verdict.is_safe ? 'linear-gradient(135deg,#064E3B,#065F46)' : 'linear-gradient(135deg,#450A0A,#7F1D1D)',
            border: `2px solid ${verdict.is_safe ? '#10B981' : '#EF4444'}`,
          }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>{verdict.is_safe ? '✅' : '⚠️'}</div>
            <div style={{ fontSize: 22, fontWeight: 800, color: '#F1F5F9', marginBottom: 8 }}>
              {String(verdict.verdict ?? 'Use with caution')}
            </div>
            <div style={{ fontSize: 15, color: '#94A3B8' }}>{String(verdict.recommendation ?? '')}</div>
          </div>
          {(verdict.action_steps as string[] ?? []).length > 0 && (
            <Card title="Action Steps" color="#00D4FF">
              {(verdict.action_steps as string[]).map((step, i) => (
                <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 8, fontSize: 14, color: '#CBD5E1' }}>
                  <span style={{ color: '#00D4FF', fontWeight: 700, flexShrink: 0 }}>{i + 1}.</span>
                  <span>{step}</span>
                </div>
              ))}
            </Card>
          )}
        </motion.div>
      )}

      {section === 'compliance' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 4 }}>
            {([
              { key: 'gdpr', label: 'GDPR (EU)',         score: data.compliance.gdpr_score  },
              { key: 'ccpa', label: 'CCPA (California)', score: data.compliance.ccpa_score  },
              { key: 'dpdp', label: 'DPDP (India)',      score: data.compliance.dpdp_score  },
            ] as { key: string; label: string; score: number }[]).map(({ key, label, score }) => {
              const c = comp[key] as Record<string, unknown> ?? {}
              return (
                <div key={key} style={{ flex: '1 1 160px', padding: '16px', background: '#0A0E1A', borderRadius: 12, border: `1px solid ${scoreColor(score)}33` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                    <span style={{ fontSize: 13, fontWeight: 700, color: '#F1F5F9', textTransform: 'uppercase' }}>{label}</span>
                    <span style={{ fontSize: 22, fontWeight: 800, color: scoreColor(score) }}>{score}%</span>
                  </div>
                  <ProgressBar value={score} color={scoreColor(score)} height={8} />
                  {c.explanation != null && (
                    <div style={{ marginTop: 8, fontSize: 12, color: '#94A3B8' }}>{String(c.explanation)}</div>
                  )}
                  {(c.gaps as string[] ?? []).length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      {(c.gaps as string[]).slice(0, 2).map((g, i) => (
                        <div key={i} style={{ fontSize: 11, color: '#EF4444', marginBottom: 2 }}>• {g}</div>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
          <div style={{ fontSize: 11, color: '#475569', marginBottom: 4 }}>
            Scores calculated from extracted clauses using GDPR, CCPA, and DPDP compliance mapping.
          </div>
          {comp.overall_explanation != null && (
            <Card title={`Overall: ${String(comp.overall_grade ?? '?')}`} color="#7C3AED">
              <p style={{ fontSize: 14, color: '#CBD5E1' }}>{String(comp.overall_explanation)}</p>
            </Card>
          )}
        </motion.div>
      )}

      {section === 'clauses' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {clauses.length === 0 && <div style={{ color: '#475569', fontSize: 14 }}>No clause analysis available.</div>}
          {(clauses as Record<string, string>[]).map((c, i) => (
            <details key={i} style={{ background: '#0A0E1A', borderRadius: 10, padding: 0, border: `1px solid ${c.risk_level === 'critical' ? '#EF4444' : c.risk_level === 'high' ? '#F97316' : c.risk_level === 'medium' ? '#F59E0B' : '#10B981'}33`, overflow: 'hidden' }}>
              <summary style={{ padding: '12px 16px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10, listStyle: 'none', userSelect: 'none' }}>
                <span style={{ flex: 1, fontWeight: 600, color: '#F1F5F9', fontSize: 14 }}>{c.clause_name}</span>
                <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 8, background: 'rgba(239,68,68,0.1)', color: c.risk_level === 'critical' ? '#EF4444' : c.risk_level === 'high' ? '#F97316' : '#F59E0B', textTransform: 'uppercase' }}>
                  {c.risk_level}
                </span>
              </summary>
              <div style={{ padding: '8px 16px 16px', borderTop: '1px solid #1E2D45' }}>
                <p style={{ fontSize: 14, color: '#F1F5F9', margin: '10px 0 6px' }}>{c.what_it_means}</p>
                {c.why_risky && <p style={{ fontSize: 13, color: '#EF4444', margin: '0 0 6px' }}>⚠ {c.why_risky}</p>}
                {c.quote && <p style={{ fontSize: 12, color: '#475569', fontStyle: 'italic', borderLeft: '2px solid #1E2D45', paddingLeft: 10 }}>"{c.quote}"</p>}
              </div>
            </details>
          ))}
        </motion.div>
      )}

      {section === 'flags' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {redFlags.length > 0 && (
            <Card title={`🔴 Red Flags (${redFlags.length})`} color="#EF4444">
              {(redFlags as Record<string, string>[]).map((f, i) => (
                <div key={i} style={{ padding: '10px 14px', background: 'rgba(239,68,68,0.05)', borderLeft: '3px solid #EF4444', borderRadius: '0 8px 8px 0', marginBottom: 8 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: '#FCA5A5' }}>{f.flag}</div>
                  <div style={{ fontSize: 13, color: '#94A3B8', marginTop: 3 }}>{f.explanation}</div>
                  {f.what_user_should_do && <div style={{ fontSize: 12, color: '#10B981', marginTop: 4 }}>→ {f.what_user_should_do}</div>}
                </div>
              ))}
            </Card>
          )}
          {posSig.length > 0 && (
            <Card title={`✅ Positive Signals (${posSig.length})`} color="#10B981">
              {(posSig as Record<string, string>[]).map((s, i) => (
                <div key={i} style={{ padding: '8px 12px', borderLeft: '3px solid #10B981', marginBottom: 6 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: '#6EE7B7' }}>{s.signal}</div>
                  <div style={{ fontSize: 13, color: '#94A3B8' }}>{s.explanation}</div>
                </div>
              ))}
            </Card>
          )}
          {darkPat.length > 0 && (
            <Card title={`⚠ Manipulation Tactics (${darkPat.length})`} color="#F59E0B">
              {(darkPat as Record<string, string>[]).map((p, i) => (
                <div key={i} style={{ padding: '8px 12px', borderLeft: '3px solid #F59E0B', marginBottom: 6 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: '#FCD34D' }}>{p.pattern}</div>
                  <div style={{ fontSize: 13, color: '#94A3B8' }}>{p.explanation}</div>
                </div>
              ))}
            </Card>
          )}
        </motion.div>
      )}
    </div>
  )
}

function Card({ title, color, children }: { title: string; color: string; children: React.ReactNode }) {
  return (
    <div style={{ padding: '16px 20px', background: '#0A0E1A', borderRadius: 12, border: `1px solid ${color}22` }}>
      <div style={{ fontSize: 14, fontWeight: 700, color, marginBottom: 12 }}>{title}</div>
      {children}
    </div>
  )
}
