import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { BookOpen, Headphones, BarChart2, MessageCircle, Baby, FileText, RefreshCw } from 'lucide-react'
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

export default function AnalysePage() {
  const { state, analyse, retry, reset, contradictions, contradictionsLoading } = useAnalysis()
  const [activeTab, setActiveTab] = useState<ModeTab>('read')
  // Shared language selection — ListenMode drives this, ReadMode uses it for display translation
  const [selectedLanguage, setSelectedLanguage] = useState('en')

  useEffect(() => { document.title = 'PrivacyLens — Analyse' }, [])

  const isTimeoutError = state.error?.includes('timed out') || state.error?.includes('too long') || state.error?.includes('still running')

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
    <div style={{ background: '#0A0E1A', minHeight: '100vh', paddingTop: 80 }} className="grid-bg">
      <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 16px' }}>

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

            {/* General error + retry button */}
            {state.error && (
              <div style={{ marginTop: 12, padding: '16px 18px', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 10 }}>
                <div style={{ color: '#EF4444', fontSize: 14, marginBottom: 12 }}>
                  {state.error}
                </div>
                <button
                  onClick={retry}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 6,
                    padding: '8px 18px', borderRadius: 8, fontSize: 13, fontWeight: 700,
                    background: isTimeoutError ? '#00D4FF' : 'rgba(239,68,68,0.15)',
                    color: isTimeoutError ? '#0A0E1A' : '#EF4444',
                    border: 'none', cursor: 'pointer',
                  }}
                >
                  <RefreshCw size={13} />
                  {isTimeoutError ? 'Retry (will be instant if same policy)' : 'Try Again'}
                </button>
              </div>
            )}
          </motion.div>
        )}

        {/* Progress bar */}
        {state.status === 'loading' && (
          <AnalysisProgress progress={state.progress} currentStep={state.currentStep} />
        )}

        {/* Results */}
        {state.status === 'success' && state.data && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
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
              <div style={{ display: 'flex', overflowX: 'auto' }}>
                {TABS.map(t => (
                  <button key={t.id} style={tabStyle(t.id)} onClick={() => setActiveTab(t.id)}>
                    {t.icon} {t.label}
                  </button>
                ))}
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
                  <SeeMode data={state.data} policyName={state.data.policy_name} />
                )}
                {activeTab === 'ask' && (
                  <AskMode data={state.data} audienceLevel="adult" policyText={state.policyText} />
                )}
                {activeTab === 'kids' && (
                  <KidsMode
                    data={state.data}
                    audienceLevel="child"
                  />
                )}
                {activeTab === 'report' && (
                  <ReportMode data={state.data} language="en" />
                )}
              </motion.div>
            </AnimatePresence>
          </motion.div>
        )}
      </div>
    </div>
  )
}
