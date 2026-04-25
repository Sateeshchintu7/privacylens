import { useState, useRef, useEffect } from 'react'
import { Send } from 'lucide-react'
import { askQuestion } from '../../api/client'
import LoadingSpinner from '../ui/LoadingSpinner'
import type { AnalyseResponse, AskResponse } from '../../types'

const SUGGESTED_QUESTIONS = [
  'Can they sell my data?',
  'How do I delete my account?',
  'Do they track my location?',
  'Is my data shared with advertisers?',
  'How long do they keep my data?',
  'What are my rights?',
  'Is this policy GDPR compliant?',
  'Do they use cookies to track me?',
]

interface Message {
  role: 'user' | 'bot'
  text: string
  answer?: AskResponse
}

interface Props { data: AnalyseResponse; audienceLevel: string; policyText: string }

export default function AskMode({ data, audienceLevel, policyText }: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const send = async (question: string) => {
    if (!question.trim() || loading) return
    setMessages(m => [...m, { role: 'user', text: question }])
    setInput('')
    setLoading(true)
    try {
      const res = await askQuestion({
        question,
        clauses: data.clauses,
        policy_text: data.policy_text || policyText || data.plain_clauses.map(c => c.plain_summary).join('\n'),
        audience_level: audienceLevel,
        compliance_report: data.compliance as object,
      })
      setMessages(m => [...m, { role: 'bot', text: res.data.plain_answer, answer: res.data }])
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      const msg = detail ?? 'Sorry, I could not answer that. Please try again.'
      setMessages(m => [...m, { role: 'bot', text: msg }])
    }
    setLoading(false)
  }

  const confColour = (c: number) => c >= 0.7 ? '#10B981' : c >= 0.4 ? '#F59E0B' : '#EF4444'
  const confLabel  = (c: number) => c >= 0.7 ? 'High ✅' : c >= 0.4 ? 'Moderate ⚠️' : 'Low ❓'

  return (
    <div style={{ background: '#111827', border: '1px solid #1E2D45', borderRadius: 16, padding: 24 }}>
      {/* Suggested chips */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 20 }}>
        {SUGGESTED_QUESTIONS.map(q => (
          <button
            key={q}
            onClick={() => send(q)}
            style={{
              padding: '6px 14px', borderRadius: 20, fontSize: 13, cursor: 'pointer',
              background: 'rgba(0,212,255,0.05)', border: '1px solid #1E2D45',
              color: '#94A3B8', transition: 'all 0.2s',
            }}
            onMouseEnter={e => { (e.target as HTMLElement).style.borderColor = '#00D4FF'; (e.target as HTMLElement).style.color = '#00D4FF'; }}
            onMouseLeave={e => { (e.target as HTMLElement).style.borderColor = '#1E2D45'; (e.target as HTMLElement).style.color = '#94A3B8'; }}
          >
            {q}
          </button>
        ))}
      </div>

      {/* Chat window */}
      <div style={{ minHeight: 300, maxHeight: 400, overflowY: 'auto', marginBottom: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', color: '#475569', padding: '40px 0', fontSize: 14 }}>
            💬 Ask anything about this policy
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
            {msg.role === 'user' ? (
              <div style={{ maxWidth: '75%', padding: '10px 16px', background: '#00D4FF', color: '#0A0E1A', borderRadius: '16px 16px 4px 16px', fontSize: 14, fontWeight: 600 }}>
                {msg.text}
              </div>
            ) : (
              <div style={{ maxWidth: '85%', background: '#1A2236', border: '1px solid #1E2D45', borderRadius: '4px 16px 16px 16px', padding: '12px 16px' }}>
                <div style={{ fontSize: 14, color: '#F1F5F9', lineHeight: 1.6, marginBottom: 8 }}>{msg.text}</div>
                {msg.answer && !msg.answer.could_not_find && msg.answer.source_quote && (
                  <div style={{ padding: '8px 12px', background: '#111827', borderRadius: 8, fontSize: 12, color: '#94A3B8', marginBottom: 8, borderLeft: '3px solid #1E2D45' }}>
                    📄 "{msg.answer.source_quote}"
                  </div>
                )}
                {msg.answer && (
                  <span style={{
                    fontSize: 11, padding: '2px 8px', borderRadius: 10,
                    background: `${confColour(msg.answer.confidence)}20`,
                    color: confColour(msg.answer.confidence),
                  }}>
                    {confLabel(msg.answer.confidence)}
                  </span>
                )}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#475569', fontSize: 13 }}>
            <LoadingSpinner size={16} /> Searching the policy...
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div style={{ display: 'flex', gap: 8 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send(input)}
          placeholder="Ask a question about this policy..."
          style={{
            flex: 1, padding: '12px 16px', background: '#1A2236', border: '1px solid #1E2D45',
            borderRadius: 10, color: '#F1F5F9', fontSize: 14,
          }}
          onFocus={e => (e.target.style.borderColor = '#00D4FF')}
          onBlur={e => (e.target.style.borderColor = '#1E2D45')}
        />
        <button
          onClick={() => send(input)}
          disabled={loading}
          style={{
            padding: '12px 16px', borderRadius: 10, background: '#00D4FF',
            border: 'none', cursor: loading ? 'not-allowed' : 'pointer', color: '#0A0E1A',
          }}
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  )
}
