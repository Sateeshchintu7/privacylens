import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { Volume2, Lock } from 'lucide-react'
import { useAudio } from '../../hooks/useAudio'
import LoadingSpinner from '../ui/LoadingSpinner'
import { startKidsAnalysis, getKidsStatus } from '../../api/client'
import type { KidsReport, KidsResponse, AnalyseResponse } from '../../types'

const VERDICT_STYLES = {
  SAFE: { bg: 'linear-gradient(135deg, #064E3B, #065F46)', border: '#10B981', glow: 'rgba(16,185,129,0.2)', emoji: '✅' },
  ASK_PARENT: { bg: 'linear-gradient(135deg, #451A03, #78350F)', border: '#F59E0B', glow: 'rgba(245,158,11,0.2)', emoji: '⚠️' },
  BE_CAREFUL: { bg: 'linear-gradient(135deg, #450A0A, #7F1D1D)', border: '#EF4444', glow: 'rgba(239,68,68,0.2)', emoji: '🛑' },
}

const RISK_COLOURS: Record<string, string> = {
  critical: '#EF4444', high: '#F97316', medium: '#F59E0B', low: '#10B981', none: '#10B981',
}

type AgeGroup = 'child' | 'junior' | 'teen'

interface Props {
  data: AnalyseResponse | null
  audienceLevel: string
}

const KIDS_POLL_INTERVAL = 3_000
const KIDS_MAX_POLLS = 30  // 90s max

export default function KidsMode({ data, audienceLevel }: Props) {
  const [ageGroup, setAgeGroup] = useState<AgeGroup>('junior')
  const [kidsData, setKidsData] = useState<KidsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { audioState, generate } = useAudio()
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
  }

  const handleAgeSelect = async (age: AgeGroup) => {
    if (!data) return
    stopPolling()
    setKidsData(null)
    setError(null)
    setLoading(true)

    let jobId: string
    try {
      const res = await startKidsAnalysis({
        plain_clauses: data.plain_clauses as object[],
        risk_report: data.risk_report as object,
        age_group: age,
      })
      jobId = res.data.job_id
    } catch {
      setError('Could not start Kids Mode. Please try again.')
      setLoading(false)
      return
    }

    let polls = 0
    pollRef.current = setInterval(async () => {
      polls++
      if (polls > KIDS_MAX_POLLS) {
        stopPolling()
        setError('Kids Mode is taking too long. Please try again.')
        setLoading(false)
        return
      }
      try {
        const res = await getKidsStatus(jobId)
        const job = res.data
        if (job.status === 'complete' && job.result) {
          stopPolling()
          setKidsData(job.result)
          setLoading(false)
        } else if (job.status === 'error') {
          stopPolling()
          setError(job.error ?? 'Kids Mode failed.')
          setLoading(false)
        }
      } catch { /* network blip — keep polling */ }
    }, KIDS_POLL_INTERVAL)
  }

  useEffect(() => {
    handleAgeSelect(ageGroup)
    return stopPolling
  }, [ageGroup, data])

  const report: KidsReport | null = kidsData?.report ?? null
  const vStyle = VERDICT_STYLES[report?.verdict as keyof typeof VERDICT_STYLES] ?? VERDICT_STYLES['ASK_PARENT']

  const ageBtn = (a: AgeGroup, _label: string) => ({
    padding: '14px 28px', borderRadius: 28, minWidth: 120, fontSize: 15, fontWeight: 700,
    cursor: 'pointer', border: `2px solid ${ageGroup === a ? '#00D4FF' : '#1E2D45'}`,
    background: ageGroup === a ? '#00D4FF' : 'transparent',
    color: ageGroup === a ? '#0A0E1A' : '#94A3B8',
    boxShadow: ageGroup === a ? '0 0 20px rgba(0,212,255,0.3)' : 'none',
    transition: 'all 0.2s',
  })

  const handleReadAloud = () => {
    if (!report) return
    const verdict  = (report.verdict ?? 'ASK PARENT').replace(/_/g, ' ')
    const reason   = report.verdict_reason ?? ''
    const concerns = (report.concerns ?? []).slice(0, 3).join('. ')
    const text     = [verdict, reason, concerns].filter(Boolean).join('. ').trim()
    if (!text) return
    generate(text, 'en', audienceLevel)
  }

  return (
    <div style={{ background: '#0F1729', borderRadius: 16, padding: 24, minHeight: 400 }}>
      {/* Age selector */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 28, justifyContent: 'center', flexWrap: 'wrap' }}>
        <button style={ageBtn('child', '8–10 👧')} onClick={() => setAgeGroup('child')}>8–10 👧</button>
        <button style={ageBtn('junior', '11–13 🧑')} onClick={() => setAgeGroup('junior')}>11–13 🧑</button>
        <button style={ageBtn('teen', '14–17 🧒')} onClick={() => setAgeGroup('teen')}>14–17 🧒</button>
      </div>

      {error && (
        <div style={{ textAlign: 'center', padding: '20px', color: '#EF4444', fontSize: 14 }}>
          {error}
        </div>
      )}

      {loading && !error && (
        <div style={{ textAlign: 'center', padding: '60px 0', color: '#94A3B8' }}>
          <LoadingSpinner size={36} /> <div style={{ marginTop: 16 }}>Generating kids version...</div>
        </div>
      )}

      {!loading && report && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Verdict card */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
            style={{
              background: vStyle.bg,
              border: `2px solid ${vStyle.border}`,
              boxShadow: `0 0 40px ${vStyle.glow}`,
              borderRadius: 20, padding: 28, textAlign: 'center',
            }}
          >
            <motion.div
              initial={{ scale: 0 }} animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 260, damping: 20 }}
              style={{ fontSize: 80, marginBottom: 12 }}
            >
              {report.verdict_emoji}
            </motion.div>
            <div style={{ fontSize: 24, fontWeight: 800, color: '#F1F5F9', marginBottom: 8 }}>
              {report.verdict.replace('_', ' ')}
            </div>
            <div style={{ fontSize: 18, color: '#94A3B8', marginBottom: 16, lineHeight: 1.5 }}>
              {report.verdict_reason}
            </div>
            {report.emoji_summary?.length > 0 && (
              <div style={{ display: 'flex', justifyContent: 'center', gap: 16, fontSize: 32, flexWrap: 'wrap', marginBottom: 16 }}>
                {report.emoji_summary.slice(0, 5).map((e, i) => <span key={i}>{e}</span>)}
              </div>
            )}
            <button
              onClick={handleReadAloud}
              disabled={audioState.isGenerating}
              style={{
                width: '100%', maxWidth: 320, margin: '0 auto', padding: '12px', borderRadius: 10, fontSize: 15,
                fontWeight: 700, border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center',
                justifyContent: 'center', gap: 8,
                background: `${vStyle.border}33`, color: '#F1F5F9',
              }}
            >
              {audioState.isGenerating ? <><LoadingSpinner size={16} /> Generating...</> : <><Volume2 size={18} /> Read this to me</>}
            </button>
            {audioState.audioUrl && !audioState.isGenerating && (
              <audio controls src={audioState.audioUrl} style={{ width: '100%', maxWidth: 320, margin: '12px auto 0', display: 'block' }} />
            )}
          </motion.div>

          {/* Two columns */}
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            {/* Concerns */}
            {report.concerns?.length > 0 && (
              <motion.div
                initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }}
                style={{ flex: '1 1 280px', background: '#111827', border: '1px solid #1E2D45', borderRadius: 16, padding: 20 }}
              >
                <div style={{ fontSize: 16, fontWeight: 700, color: '#EF4444', marginBottom: 14 }}>🚨 Things to know</div>
                {report.concerns.map((c, i) => (
                  <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 10, padding: '8px 12px', borderLeft: '3px solid #EF4444', background: 'rgba(239,68,68,0.05)', borderRadius: '0 8px 8px 0' }}>
                    <span style={{ fontSize: 18, flexShrink: 0 }}>⚠️</span>
                    <span style={{ fontSize: 16, color: '#F1F5F9', lineHeight: 1.5 }}>{c}</span>
                  </div>
                ))}
              </motion.div>
            )}

            {/* Positives */}
            {report.positives?.length > 0 && (
              <motion.div
                initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 }}
                style={{ flex: '1 1 280px', background: '#111827', border: '1px solid #1E2D45', borderRadius: 16, padding: 20 }}
              >
                <div style={{ fontSize: 16, fontWeight: 700, color: '#10B981', marginBottom: 14 }}>✅ Good things</div>
                {report.positives.map((p, i) => (
                  <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 10, padding: '8px 12px', borderLeft: '3px solid #10B981', background: 'rgba(16,185,129,0.05)', borderRadius: '0 8px 8px 0' }}>
                    <span style={{ fontSize: 18, flexShrink: 0 }}>✅</span>
                    <span style={{ fontSize: 16, color: '#F1F5F9', lineHeight: 1.5 }}>{p}</span>
                  </div>
                ))}
              </motion.div>
            )}
          </div>

          {/* Clause cards */}
          {report.clauses?.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#94A3B8', marginBottom: 4 }}>Section by section:</div>
              {report.clauses.map((clause, i) => {
                const colour = RISK_COLOURS[clause.risk_level ?? 'low']
                return (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}
                    style={{
                      background: '#111827', borderRadius: 14, padding: '16px 20px',
                      border: `1px solid ${colour}33`, borderLeft: `4px solid ${colour}`,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                      <span style={{ fontSize: 28 }}>{clause.emoji}</span>
                      <span style={{ fontSize: 16, fontWeight: 700, color: '#F1F5F9' }}>{clause.category_label}</span>
                    </div>
                    <p style={{ fontSize: 17, color: '#F1F5F9', lineHeight: 1.7, margin: '0 0 8px' }}>{clause.kids_summary}</p>
                    <p style={{ fontSize: 14, color: '#94A3B8', fontStyle: 'italic', margin: 0 }}>{clause.one_liner}</p>
                  </motion.div>
                )
              })}
            </div>
          )}

          {/* Footer note */}
          <div style={{ textAlign: 'center', padding: '16px', background: 'rgba(0,212,255,0.04)', borderRadius: 12, border: '1px solid #1E2D45' }}>
            <Lock size={18} color="#475569" style={{ margin: '0 auto 8px', display: 'block' }} />
            <p style={{ fontSize: 14, color: '#475569', margin: 0, lineHeight: 1.6 }}>
              Always talk to a trusted adult before agreeing to any app's terms. 🔒
            </p>
          </div>
        </div>
      )}

      {!loading && !report && (
        <div style={{ textAlign: 'center', padding: '60px 0', color: '#475569' }}>
          Select an age group above to load Kids Mode.
        </div>
      )}
    </div>
  )
}
