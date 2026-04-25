import { useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import ProgressBar from '../ui/ProgressBar'

const STEPS = [
  'Fetching document...',
  'Cleaning and processing text...',
  'Extracting clauses with AI...',
  'Scoring privacy risk...',
  'Rewriting in plain English...',
  'Checking GDPR compliance...',
  'Detecting contradictions...',
]

// Map progress % to the step index that should now be active.
// Thresholds derived from delay timings in useAnalysis STEPS array.
function getActiveStep(progress: number): number {
  if (progress >= 88) return 6
  if (progress >= 81) return 5
  if (progress >= 72) return 4
  if (progress >= 61) return 3
  if (progress >= 48) return 2
  if (progress >= 20) return 1
  if (progress >= 5)  return 0
  return -1
}

interface Props {
  progress: number     // 0–100
  currentStep: string
}

export default function AnalysisProgress({ progress, currentStep }: Props) {
  // Monotonically-increasing set — steps are added but never removed.
  // This prevents green checkmarks from reverting to grey on re-render.
  const completedStepsRef = useRef<Set<number>>(new Set())

  useEffect(() => {
    const active = getActiveStep(progress)
    // Mark every step BEFORE the active one as permanently complete
    for (let i = 0; i < active; i++) {
      completedStepsRef.current.add(i)
    }
  }, [progress])

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
      style={{ background: '#111827', border: '1px solid #1E2D45', borderRadius: 16, padding: 28 }}
    >
      <div style={{ marginBottom: 20 }}>
        <ProgressBar value={progress} color="#00D4FF" height={4} />
        <div style={{ marginTop: 8, fontSize: 13, color: '#00D4FF', fontFamily: 'JetBrains Mono, monospace' }}>
          {progress.toFixed(0)}%
          {currentStep && (
            <span style={{ marginLeft: 10, color: '#64748B' }}>{currentStep}</span>
          )}
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {STEPS.map((step, index) => {
          const active = getActiveStep(progress) === index
          const done   = completedStepsRef.current.has(index)

          return (
            <div key={step} style={{
              display: 'flex', alignItems: 'center', gap: 12,
              opacity: done || active ? 1 : 0.35,
            }}>
              {/* Status circle */}
              <div style={{
                width: 24, height: 24, borderRadius: '50%', flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: done ? '#10B981' : active ? 'rgba(0,212,255,0.15)' : '#1E2D45',
                border: active ? '2px solid #00D4FF' : 'none',
                fontSize: 12,
              }}>
                {done ? (
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M2 6L5 9L10 3" stroke="white" strokeWidth="2"
                      strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                ) : active ? (
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                    style={{ width: 10, height: 10, border: '2px solid #00D4FF', borderTopColor: 'transparent', borderRadius: '50%' }}
                  />
                ) : null}
              </div>

              <span style={{
                fontSize: 14,
                color: done ? '#10B981' : active ? '#F1F5F9' : '#475569',
                fontWeight: active ? 600 : done ? 500 : 400,
              }}>
                {step}
              </span>
            </div>
          )
        })}
      </div>
    </motion.div>
  )
}
