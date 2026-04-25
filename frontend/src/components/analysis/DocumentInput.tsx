import { useState, useRef } from 'react'
import { Link2, FileText, ClipboardList, Upload } from 'lucide-react'
import type { AnalyseRequest } from '../../types'

const LANGUAGES = [
  { code: 'en', flag: '🇬🇧', name: 'English' }, { code: 'es', flag: '🇪🇸', name: 'Spanish' },
  { code: 'fr', flag: '🇫🇷', name: 'French' }, { code: 'de', flag: '🇩🇪', name: 'German' },
  { code: 'it', flag: '🇮🇹', name: 'Italian' }, { code: 'pt', flag: '🇵🇹', name: 'Portuguese' },
  { code: 'zh', flag: '🇨🇳', name: 'Chinese' }, { code: 'ja', flag: '🇯🇵', name: 'Japanese' },
  { code: 'ar', flag: '🇸🇦', name: 'Arabic' }, { code: 'hi', flag: '🇮🇳', name: 'Hindi' },
]

interface Props {
  onSubmit: (req: AnalyseRequest) => void
  loading: boolean
}

type Tab = 'url' | 'pdf' | 'text'
type AudienceLevel = 'adult' | 'teen' | 'child'

export default function DocumentInput({ onSubmit, loading }: Props) {
  const [tab, setTab] = useState<Tab>('url')
  const [url, setUrl] = useState('')
  const [pastedText, setPastedText] = useState('')
  const [audience, setAudience] = useState<AudienceLevel>('adult')
  const [language, setLanguage] = useState('en')
  const [pdfFile, setPdfFile] = useState<File | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleSubmit = async () => {
    if (loading) return
    if (tab === 'url') {
      if (!url.trim()) return
      onSubmit({ input_type: 'url', content: url.trim(), audience_level: audience, language })
    } else if (tab === 'text') {
      if (!pastedText.trim()) return
      onSubmit({ input_type: 'text', content: pastedText.trim(), audience_level: audience, language })
    } else if (tab === 'pdf' && pdfFile) {
      const bytes = await pdfFile.arrayBuffer()
      const b64 = btoa(String.fromCharCode(...new Uint8Array(bytes)))
      onSubmit({ input_type: 'pdf_base64', content: b64, audience_level: audience, language })
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f?.type === 'application/pdf') setPdfFile(f)
  }

  const tabStyle = (t: Tab) => ({
    padding: '8px 20px', borderRadius: 8, cursor: 'pointer', fontSize: 14, fontWeight: 600,
    background: tab === t ? 'rgba(0,212,255,0.15)' : 'transparent',
    color: tab === t ? '#00D4FF' : '#94A3B8',
    border: tab === t ? '1px solid rgba(0,212,255,0.4)' : '1px solid transparent',
    display: 'flex', alignItems: 'center', gap: 6,
  })

  const audienceStyle = (a: AudienceLevel) => ({
    padding: '8px 20px', borderRadius: 24, cursor: 'pointer', fontSize: 14, fontWeight: 600,
    background: audience === a ? '#00D4FF' : 'rgba(255,255,255,0.03)',
    color: audience === a ? '#0A0E1A' : '#94A3B8',
    border: audience === a ? '1px solid #00D4FF' : '1px solid #1E2D45',
    boxShadow: audience === a ? '0 0 12px rgba(0,212,255,0.3)' : 'none',
    transition: 'all 0.2s',
  })

  return (
    <div style={{ background: '#111827', border: '1px solid #1E2D45', borderRadius: 16, padding: 28 }}>
      {/* Tab selector */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 24, flexWrap: 'wrap' }}>
        <button style={tabStyle('url')} onClick={() => setTab('url')}><Link2 size={15} /> URL</button>
        <button style={tabStyle('pdf')} onClick={() => setTab('pdf')}><FileText size={15} /> Upload PDF</button>
        <button style={tabStyle('text')} onClick={() => setTab('text')}><ClipboardList size={15} /> Paste Text</button>
      </div>

      {/* URL */}
      {tab === 'url' && (
        <input
          value={url} onChange={e => setUrl(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSubmit()}
          placeholder="https://policies.google.com/privacy"
          style={{
            width: '100%', padding: '14px 16px', background: '#1A2236',
            border: '1px solid #1E2D45', borderRadius: 8, color: '#F1F5F9',
            fontSize: 15, outline: 'none', boxSizing: 'border-box',
            transition: 'border-color 0.2s',
          }}
          onFocus={e => (e.target.style.borderColor = '#00D4FF')}
          onBlur={e => (e.target.style.borderColor = '#1E2D45')}
        />
      )}

      {/* PDF Drop Zone */}
      {tab === 'pdf' && (
        <div
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          style={{
            border: `2px dashed ${dragOver ? '#00D4FF' : '#1E2D45'}`,
            borderRadius: 12, padding: 40, textAlign: 'center', cursor: 'pointer',
            background: dragOver ? 'rgba(0,212,255,0.05)' : '#1A2236',
            transition: 'all 0.2s',
          }}
        >
          <Upload size={32} color="#475569" style={{ margin: '0 auto 12px', display: 'block' }} />
          {pdfFile
            ? <p style={{ color: '#10B981', fontWeight: 600 }}>✓ {pdfFile.name}</p>
            : <><p style={{ color: '#94A3B8' }}>Drag your PDF here or click to browse</p>
               <p style={{ fontSize: 12, color: '#475569', marginTop: 4 }}>PDF files only</p></>
          }
          <input ref={fileInputRef} type="file" accept=".pdf" style={{ display: 'none' }}
            onChange={e => { if (e.target.files?.[0]) setPdfFile(e.target.files[0]) }} />
        </div>
      )}

      {/* Paste Text */}
      {tab === 'text' && (
        <div style={{ position: 'relative' }}>
          <textarea
            value={pastedText} onChange={e => setPastedText(e.target.value)}
            placeholder="Paste the full policy text here..."
            rows={8}
            style={{
              width: '100%', padding: '14px 16px', background: '#1A2236',
              border: '1px solid #1E2D45', borderRadius: 8, color: '#F1F5F9',
              fontSize: 14, resize: 'vertical', fontFamily: 'inherit', boxSizing: 'border-box',
            }}
            onFocus={e => (e.target.style.borderColor = '#00D4FF')}
            onBlur={e => (e.target.style.borderColor = '#1E2D45')}
          />
          <span style={{ position: 'absolute', bottom: 12, right: 12, fontSize: 12, color: '#475569' }}>
            {pastedText.length.toLocaleString()} chars
          </span>
        </div>
      )}

      {/* Audience + Language */}
      <div style={{ marginTop: 20, display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 12, color: '#475569', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>Who is reading this?</div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button style={audienceStyle('adult')} onClick={() => setAudience('adult')}>👤 Adult</button>
            <button style={audienceStyle('teen')} onClick={() => setAudience('teen')}>🧑 Teen</button>
            <button style={audienceStyle('child')} onClick={() => setAudience('child')}>👧 Child</button>
          </div>
        </div>
        <div style={{ marginLeft: 'auto' }}>
          <div style={{ fontSize: 12, color: '#475569', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>Language</div>
          <select
            value={language} onChange={e => setLanguage(e.target.value)}
            style={{ padding: '8px 12px', background: '#1A2236', border: '1px solid #1E2D45', borderRadius: 8, color: '#F1F5F9', fontSize: 14, cursor: 'pointer' }}
          >
            {LANGUAGES.map(l => <option key={l.code} value={l.code}>{l.flag} {l.name}</option>)}
          </select>
        </div>
      </div>

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={loading}
        style={{
          marginTop: 20, width: '100%', padding: '14px', borderRadius: 10, fontSize: 16, fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer',
          background: loading ? '#1E2D45' : '#00D4FF', color: loading ? '#475569' : '#0A0E1A',
          border: 'none', boxShadow: loading ? 'none' : '0 0 25px rgba(0,212,255,0.3)',
          transition: 'all 0.2s',
        }}
      >
        {loading ? '⟳ Analysing...' : '→ Analyse Policy'}
      </button>
    </div>
  )
}
