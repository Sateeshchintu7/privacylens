import { useState, useCallback, useRef } from 'react'
import { startAnalysis, getAnalysisStatus, checkHealth, detectContradictions } from '../api/client'
import type { AnalysisState, AnalyseRequest, AnalyseResponse, ContradictionReport } from '../types'

// Progress steps — compressed to ~60s (fallback if server doesn't report progress)
const STEPS: Array<{ pct: number; label: string; delay: number }> = [
  { pct: 10, label: 'Connecting to server...',          delay: 500     },
  { pct: 18, label: 'Fetching document...',             delay: 2_000   },
  { pct: 25, label: 'Cleaning and processing text...',  delay: 4_000   },
  { pct: 35, label: 'Extracting clauses with AI...',    delay: 8_000   },
  { pct: 50, label: 'Scoring privacy risk...',          delay: 18_000  },
  { pct: 65, label: 'Rewriting in plain English...',    delay: 30_000  },
  { pct: 78, label: 'Checking GDPR compliance...',      delay: 40_000  },
  { pct: 88, label: 'Detecting dark patterns...',       delay: 50_000  },
  { pct: 93, label: 'Finalising analysis...',           delay: 58_000  },
]

const POLL_INTERVAL_MS = 2_000   // poll every 2s (was 3s)
const MAX_POLLS        = 120     // 4 min at 2s interval

export function useAnalysis() {
  const [state, setState] = useState<AnalysisState>({
    status: 'idle',
    currentStep: '',
    progress: 0,
    data: null,
    kidsData: null,
    error: null,
    policyText: '',
    blocked403: false,
  })

  const [contradictionsLoading, setContradictionsLoading] = useState(false)
  const [contradictions, setContradictions] = useState<ContradictionReport | null>(null)

  const lastInputRef  = useRef<AnalyseRequest | null>(null)
  const pollRef       = useRef<ReturnType<typeof setInterval> | null>(null)
  const stepTimers    = useRef<ReturnType<typeof setTimeout>[]>([])

  // ── Cleanup ────────────────────────────────────────────────────────────────
  const clearTimers = useCallback(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
    stepTimers.current.forEach(t => clearTimeout(t))
    stepTimers.current = []
  }, [])

  // ── Contradiction background fetch ─────────────────────────────────────────
  const launchContradictions = useCallback((data: AnalyseResponse) => {
    setContradictionsLoading(true)
    setContradictions(null)
    detectContradictions({ clauses: data.clauses })
      .then(r => setContradictions(r.data))
      .catch(() => setContradictions(null))
      .finally(() => setContradictionsLoading(false))
  }, [])

  // ── Main analyse function ──────────────────────────────────────────────────
  const analyse = useCallback(async (input: AnalyseRequest) => {
    clearTimers()
    lastInputRef.current = input
    setContradictions(null)

    setState(s => ({
      ...s,
      status: 'loading', progress: 5, currentStep: 'Waking up server...',
      error: null, data: null, kidsData: null, blocked403: false,
    }))

    // Wake up Render free instance (sleeps after 15 min idle)
    try { await checkHealth() } catch { /* ignore — continue anyway */ }

    setState(s => ({ ...s, progress: 10, currentStep: 'Starting analysis...' }))

    // ── POST /api/analyse — returns job_id in < 1 second ───────────────────
    let jobId: string
    let isCached = false
    try {
      const res = await startAnalysis(input)
      jobId  = res.data.job_id
      isCached = res.data.cached
    } catch (err: unknown) {
      const e = err as { message?: string }
      setState(s => ({
        ...s, status: 'error',
        error: 'Could not connect to server. Please try again.',
      }))
      console.error('startAnalysis failed:', e.message)
      return
    }

    // ── Cache hit — fetch result immediately ────────────────────────────────
    if (isCached) {
      try {
        const res = await getAnalysisStatus(jobId)
        if (res.data.status === 'complete' && res.data.result) {
          setState(s => ({
            ...s, status: 'success', progress: 100, currentStep: 'Analysis complete!',
            data: res.data.result, policyText: input.content,
          }))
          launchContradictions(res.data.result)
          return
        }
      } catch { /* fall through to polling */ }
    }

    // ── Animate progress steps as fallback while job runs in background ─────
    STEPS.forEach(({ pct, label, delay }) => {
      const t = setTimeout(() => {
        setState(s => s.status === 'loading' ? { ...s, progress: Math.max(s.progress, pct), currentStep: label } : s)
      }, delay)
      stepTimers.current.push(t)
    })

    // ── Poll /api/analyse/status/{jobId} every 2 seconds ────────────────────
    let polls = 0
    pollRef.current = setInterval(async () => {
      polls++

      if (polls > MAX_POLLS) {
        clearTimers()
        setState(s => ({
          ...s, status: 'error',
          error:
            'The analysis is still running on the server. ' +
            'Click "Retry — Load Cached Result" below. ' +
            'The server cached the result during processing ' +
            'so the retry will be instant.',
        }))
        return
      }

      try {
        const res = await getAnalysisStatus(jobId)
        const job = res.data

        // Use real server-side progress if available
        if (job.status === 'running' && job.progress && job.current_step) {
          setState(s => s.status === 'loading' ? {
            ...s,
            progress: Math.max(s.progress, job.progress),
            currentStep: job.current_step,
          } : s)
        }

        if (job.status === 'complete' && job.result) {
          clearTimers()
          setState(s => ({
            ...s, status: 'success', progress: 100, currentStep: 'Analysis complete!',
            data: job.result, policyText: input.content,
          }))
          launchContradictions(job.result)

        } else if (job.status === 'error') {
          clearTimers()
          const errMsg = job.error ?? 'Analysis failed'
          if (errMsg.startsWith('BLOCKED_403')) {
            setState(s => ({ ...s, status: 'error', blocked403: true, error: null }))
          } else {
            setState(s => ({ ...s, status: 'error', error: errMsg }))
          }
        }
        // else: 'running' — keep polling
      } catch {
        // Network blip — keep polling, don't give up
      }
    }, POLL_INTERVAL_MS)
  }, [clearTimers, launchContradictions])

  // ── Retry last input ───────────────────────────────────────────────────────
  const retry = useCallback(() => {
    if (lastInputRef.current) analyse(lastInputRef.current)
  }, [analyse])

  // ── Reset ──────────────────────────────────────────────────────────────────
  const reset = useCallback(() => {
    clearTimers()
    setState({
      status: 'idle', currentStep: '', progress: 0,
      data: null, kidsData: null, error: null, policyText: '', blocked403: false,
    })
    setContradictions(null)
    setContradictionsLoading(false)
  }, [clearTimers])

  return { state, analyse, retry, reset, contradictions, contradictionsLoading }
}
