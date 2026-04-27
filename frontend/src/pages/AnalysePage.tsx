import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { BookOpen, Headphones, BarChart2, MessageCircle, Baby, FileText, RefreshCw, AlertTriangle, WifiOff, Clock } from 'lucide-react'
import { useAnalysis } from '../hooks/useAnalysis'
import DocumentInput from '../components/analysis/DocumentInput'
import AnalysisProgress from '../components/analysis/AnalysisProgress'
import SummaryCard from '../components/analysis/SummaryCard'
import ReadMode from '../components/modes/ReadMode'
import ListenMode from '../components/modes/ListenMode'
import SeeMode from '../components/modes/SeeMode'
import AskMode from '../components/modes/AskMode'
import KidsMode from '../components/modes/KidsMode'
import ReportMode from '../components/modes/ReportMode'

type ModeTab = 'read' | 'listen' | 'see' | 'ask' | 'kids' | 'report'

const TABS = [
  { id: 'read'   as ModeTab, icon: <BookOpen size={16} />,     label: 'Read'   },
  { id: 'listen' as ModeTab, icon: <Headphones size={16} />,   label: 'Listen' },
  { id: 'see'    as ModeTab, icon: <BarChart2 size={16} />,    label: 'See'    },
  { id: 'ask'    as ModeTab, icon: <MessageCircle size={16} />, label: 'Ask'   },
  { id: 'kids'   as ModeTab, icon: <Baby size={16} />,         label: 'Kids'   },
  { id: 'report' as ModeTab, icon: <FileText size={16} />,     label: 'Report' },
]

// ── Error classifier ─────────────────────────────────────────────────────────
function classifyError(error: string): { icon: React.ReactNode; title: string; detail: string; canAutoRetry: boolean } {
  const lower = error.toLowerCase()

  if (lower.includes('timeout') || lower.includes('timed out') || lower.includes('econnaborted')) {
    return {
      icon: <Clock size={20} color="#F59E0B" />,
      title: 'Server is taking longer than expected',
      detail: 'The analysis is still running. The result is likely cached — retry will be instant.',
      canAutoRetry: true,
    }
  }

  if (lower.includes('network') || lower.includes('enotfound') || lower.includes('err_internet')) {
    return {
      icon: <WifiOff size={20} color="#EF4444" />,
      title: 'No internet connection',
      detail: 'Check your connection and try again.',
      canAutoRetry: false,
    }
  }

  if (lower.includes('still running') || lower.includes('cached')) {
    return {
      icon: <Clock size={20} color="#00D4FF" />,
      title: 'Analysis ready',
      detail: 'The server finished processing. Click retry to load the cached result instantly.',
      canAutoRetry: true,
    }
  }

  if (lower.includes('500') || lower.includes('internal server')) {
    return {
      icon: <AlertTriangle size={20} color="#EF4444" />,
      title: 'Server error',
      detail: 'Something went wrong on our end. Try again or paste the text directly.',
      canAutoRetry: false,
    }
  }

  if (lower.includes('could not connect') || lower.includes('econnrefused')) {
    return {
      icon: <WifiOff size={20} color="#F59E0B" />,
      title: 'Server is waking up',
      detail: 'The server sleeps after 15 minutes of inactivity. It should be ready in 10–20 seconds.',
      canAutoRetry: true,
    }
  }

  return {
    icon: <AlertTriangle size={20} color="#EF4444" />,
    title: 'Analysis failed',
    detail: error,
    canAutoRetry: false,
  }
}

// ── Auto-retry countdown component ───────────────────────────────────────────
function AutoRetryCountdown({ seconds, onRetry }: { seconds: number; onRetry: () => void }) {
  const [remaining, setRemaining] = useState(seconds)

  useEffect(() => {
    if (remaining <= 0) { onRetry(); return }
    const t = setTimeout(() => setRemaining(r => r - 1), 1000)
    return () => clearTimeout(t)
  }, [remaining, onRetry])

  return (
    <span style={{ fontSize: 12, color: '#94A3B8' }}>
      Auto-retrying in {remaining}s...
    </span>
  )
}

export default function AnalysePage() {
  const { state, analyse, retry, reset, contradictions, contradictionsLoading } = useAnalysis()
  const [activeTab, setActiveTab] = useState<ModeTab>('read')
  // Shared language selection — ListenMode drives this, ReadMode uses it for display translation
  const [selectedLanguage, setSelectedLanguage] = useState('en')

  useEffect(() => { document.title = 'PrivacyLens — Analyse' }, [])

  const tabStyle = (t: ModeTab) => ({
    display: 'flex', alignItems: 'center', gap: 6, padding: '10px 20px',
    cursor: 'pointer', fontSize: 14, fontWeight: activeTab === t ? 700 : 500,
    color: activeTab === t ? '#00D4FF' : '#94A3B8',
    borderBottom: activeTab === t ? '2px solid #00D4FF' : '2px solid transparent',
    boxShadow: activeTab === t ? '0 4px 12px rgba(0,212,255,0.1)' : 'none',
    background: 'transparent', border: 'none',
    transition: 'all 0.2s', whiteSpace: 'nowrap' as const,
  })

  return (
    <div style={{ background: '#0A0E1A', minHeight: '100vh', paddingTop: 80, overflowX: 'hidden' }} className="grid-bg">
      <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 16px', width: '100%', boxSizing: 'border-box' }}>

        {/* Header */}
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontSize: 28, fontWeight: 800, color: '#F1F5F9', margin: '0 0 8px' }}>
            Analyse a Policy
          </h1>
          <p style={{ color: '#94A3B8', fontSize: 15, margin: 0 }}>
            Paste a URL, upload a PDF, or type the text below.
          </p>
        </div>

        {/* Input + error (idle or error state) */}
        {(state.status === 'idle' || state.status === 'error') && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
            <DocumentInput onSubmit={analyse} loading={false} />

            {/* 403 blocked */}
            {state.blocked403 && (
              <div style={{ marginTop: 12, padding: '18px 20px', background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.35)', borderRadius: 10 }}>
                <div style={{ fontWeight: 700, color: '#F59E0B', marginBottom: 8, fontSize: 15 }}>
                  Website blocked automated access
                </div>
                <div style={{ color: '#94A3B8', fontSize: 14, lineHeight: 1.7 }}>
                  This site prevents automated scraping. To analyse it:
                  <ol style={{ margin: '8px 0 0', paddingLeft: 22 }}>
                    <li>Open the privacy policy page in your browser</li>
                    <li>Select all text (Ctrl+A / Cmd+A) and copy (Ctrl+C / Cmd+C)</li>
                    <li>Switch to the <span style={{ color: '#00D4FF', fontWeight: 600 }}>Paste Text</span> tab above and paste it there</li>
                  </ol>
                </div>
              </div>
            )}

            {/* Context-aware error with auto-retry */}
            {state.error && (() => {
              const errInfo = classifyError(state.error)
              return (
                <div style={{ marginTop: 12, padding: '18px 20px', background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                    {errInfo.icon}
                    <span style={{ color: '#F1F5F9', fontSize: 15, fontWeight: 700 }}>{errInfo.title}</span>
                  </div>
                  <div style={{ color: '#94A3B8', fontSize: 14, marginBottom: 14, lineHeight: 1.6 }}>
                    {errInfo.detail}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                    <button
                      onClick={retry}
                      style={{
                        display: 'inline-flex', alignItems: 'center', gap: 6,
                        padding: '9px 20px', borderRadius: 8, fontSize: 13, fontWeight: 700,
                        background: errInfo.canAutoRetry ? '#00D4FF' : 'rgba(239,68,68,0.15)',
                        color: errInfo.canAutoRetry ? '#0A0E1A' : '#EF4444',
                        border: 'none', cursor: 'pointer',
                        boxShadow: errInfo.canAutoRetry ? '0 0 16px rgba(0,212,255,0.25)' : 'none',
                      }}
                    >
                      <RefreshCw size={13} />
                      {errInfo.canAutoRetry ? 'Retry — Load Cached Result' : 'Try Again'}
                    </button>
                    {errInfo.canAutoRetry && (
                      <AutoRetryCountdown seconds={8} onRetry={retry} />
                    )}
                  </div>
                </div>
              )
            })()}
          </motion.div>
        )}

        {/* Progress bar — with language-aware step labels */}
        {state.status === 'loading' && (
          <AnalysisProgress
            progress={state.progress}
            currentStep={state.currentStep}
            language={selectedLanguage}
          />
        )}

        {/* Results */}
        {state.status === 'success' && state.data && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#94A3B8' }}>
                📄 {state.data.policy_name.slice(0, 60)}
              </div>
              <button
                onClick={reset}
                style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '7px 14px', background: 'transparent', border: '1px solid #1E2D45', borderRadius: 8, color: '#94A3B8', cursor: 'pointer', fontSize: 13 }}
              >
                <RefreshCw size={13} /> New Analysis
              </button>
            </div>

            <div style={{ marginBottom: 24 }}>
              <SummaryCard
                data={state.data}
                contradictions={contradictions}
                contradictionsLoading={contradictionsLoading}
                darkPatterns={state.data.dark_patterns}
              />
            </div>

            {/* Mode tabs */}
            <div style={{ position: 'sticky', top: 64, zIndex: 30, background: 'rgba(10,14,26,0.95)', backdropFilter: 'blur(12px)', borderBottom: '1px solid #1E2D45', marginBottom: 24 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', overflowX: 'auto', WebkitOverflowScrolling: 'touch' as any, scrollbarWidth: 'none' as any }}>
                {TABS.map(t => (
                  <button key={t.id} style={tabStyle(t.id)} onClick={() => setActiveTab(t.id)}>
                    {t.icon} {t.label}
                  </button>
                ))}
                </div>
                <div style={{ paddingRight: 8, flexShrink: 0 }}>
                  <select
                    value={selectedLanguage}
                    onChange={e => setSelectedLanguage(e.target.value)}
                    style={{
                      padding: '6px 10px', background: '#1A2236', border: '1px solid #1E2D45',
                      borderRadius: 8, color: '#F1F5F9', fontSize: 12, cursor: 'pointer',
                      outline: 'none',
                    }}
                  >
                    <option value="en">🌐 English</option>
                    <option value="hi">🇮🇳 Hindi</option>
                    <option value="te">🇮🇳 Telugu</option>
                    <option value="ta">🇮🇳 Tamil</option>
                    <option value="kn">🇮🇳 Kannada</option>
                    <option value="ml">🇮🇳 Malayalam</option>
                    <option value="bn">🇧🇩 Bengali</option>
                    <option value="mr">🇮🇳 Marathi</option>
                    <option value="gu">🇮🇳 Gujarati</option>
                    <option value="pa">🇮🇳 Punjabi</option>
                    <option value="ur">🇵🇰 Urdu</option>
                    <option value="es">🇪🇸 Spanish</option>
                    <option value="fr">🇫🇷 French</option>
                    <option value="de">🇩🇪 German</option>
                    <option value="it">🇮🇹 Italian</option>
                    <option value="pt">🇵🇹 Portuguese</option>
                    <option value="nl">🇳🇱 Dutch</option>
                    <option value="ru">🇷🇺 Russian</option>
                    <option value="ar">🇸🇦 Arabic</option>
                    <option value="zh-cn">🇨🇳 Chinese</option>
                    <option value="ja">🇯🇵 Japanese</option>
                    <option value="ko">🇰🇷 Korean</option>
                    <option value="tr">🇹🇷 Turkish</option>
                    <option value="vi">🇻🇳 Vietnamese</option>
                  </select>
                </div>
              </div>
            </div>

            <AnimatePresence mode="wait">
              <motion.div
                key={activeTab}
                initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.2 }}
              >
                {activeTab === 'read' && (
                  <ReadMode
                    plainClauses={state.data.plain_clauses}
                    clauseRisks={state.data.risk_report.clause_risks}
                    darkPatterns={state.data.dark_patterns}
                    language={selectedLanguage}
                    loading={false}
                  />
                )}
                {activeTab === 'listen' && (
                  <ListenMode
                    data={state.data}
                    audienceLevel="adult"
                    onLanguageChange={setSelectedLanguage}
                  />
                )}
                {activeTab === 'see' && (
                  <SeeMode data={state.data} policyName={state.data.policy_name} language={selectedLanguage} />
                )}
                {activeTab === 'ask' && (
                  <AskMode data={state.data} audienceLevel="adult" policyText={state.policyText} language={selectedLanguage} />
                )}
                {activeTab === 'kids' && (
                  <KidsMode
                    data={state.data}
                    audienceLevel="child"
                    language={selectedLanguage}
                  />
                )}
                {activeTab === 'report' && (
                  <ReportMode data={state.data} language={selectedLanguage} />
                )}
              </motion.div>
            </AnimatePresence>
          </motion.div>
        )}
      </div>
    </div>
  )
}
