import { useState, useRef } from 'react'
import { Link2, FileText, Upload } from 'lucide-react'
import type { AnalyseRequest } from '../../types'

interface Props {
  onSubmit: (req: AnalyseRequest) => void
  loading: boolean
}

const LANGUAGES = [
  { code: 'en',    label: '🌐 English' },
  { code: 'hi',    label: '🇮🇳 Hindi' },
  { code: 'te',    label: '🇮🇳 Telugu' },
  { code: 'ta',    label: '🇮🇳 Tamil' },
  { code: 'kn',    label: '🇮🇳 Kannada' },
  { code: 'ml',    label: '🇮🇳 Malayalam' },
  { code: 'bn',    label: '🇧🇩 Bengali' },
  { code: 'mr',    label: '🇮🇳 Marathi' },
  { code: 'es',    label: '🇪🇸 Spanish' },
  { code: 'fr',    label: '🇫🇷 French' },
  { code: 'de',    label: '🇩🇪 German' },
  { code: 'pt',    label: '🇵🇹 Portuguese' },
  { code: 'ar',    label: '🇸🇦 Arabic' },
  { code: 'zh-cn', label: '🇨🇳 Chinese' },
  { code: 'ja',    label: '🇯🇵 Japanese' },
]

type InputTab = 'url' | 'text' | 'pdf'

export default function DocumentInput({ onSubmit, loading }: Props) {
  const [tab, setTab]             = useState<InputTab>('url')
  const [url, setUrl]             = useState('')
  const [text, setText]           = useState('')
  const [language, setLanguage]   = useState('en')
  const [audience, setAudience]   = useState<'adult' | 'teen' | 'child'>('adult')
  const [pdfName, setPdfName]     = useState('')
  const [pdfB64, setPdfB64]       = useState('')
  const [pdfError, setPdfError]   = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  const tabBtn = (t: InputTab, icon: React.ReactNode, label: string) => (
    <button
      onClick={() => setTab(t)}
      style={{
        display: 'flex', alignItems: 'center', gap: 6,
        padding: '9px 18px', cursor: 'pointer', fontSize: 14,
        fontWeight: tab === t ? 700 : 500,
        color: tab === t ? '#00D4FF' : '#94A3B8',
        borderBottom: tab === t ? '2px solid #00D4FF' : '2px solid transparent',
        background: 'transparent', border: 'none',
        borderBottomWidth: 2,
        transition: 'all 0.15s', whiteSpace: 'nowrap' as const,
      }}
    >
      {icon} {label}
    </button>
  )

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.type !== 'application/pdf') { setPdfError('Please select a PDF file'); return }
    if (file.size > 10 * 1024 * 1024) { setPdfError('PDF must be under 10 MB'); return }
    setPdfError('')
    setPdfName(file.name)
    const reader = new FileReader()
    reader.onload = ev => {
      const ab = ev.target?.result as ArrayBuffer
      const bytes = new Uint8Array(ab)
      let binary = ''
      bytes.forEach(b => binary += String.fromCharCode(b))
      setPdfB64(btoa(binary))
    }
    reader.readAsArrayBuffer(file)
  }

  const handleSubmit = () => {
    if (tab === 'url') {
      const trimmed = url.trim()
      if (!trimmed) return
      onSubmit({ input_type: 'url', content: trimmed, audience_level: audience, language })
    } else if (tab === 'text') {
      const trimmed = text.trim()
      if (trimmed.length < 100) return
      onSubmit({ input_type: 'text', content: trimmed, audience_level: audience, language })
    } else {
      if (!pdfB64) return
      onSubmit({ input_type: 'pdf_base64', content: pdfB64, audience_level: audience, language })
    }
  }

  const canSubmit = tab === 'url' ? !!url.trim() :
                    tab === 'text' ? text.trim().length >= 100 :
                    !!pdfB64

  const inputBase: React.CSSProperties = {
    width: '100%', padding: '12px 14px', background: '#1A2236',
    border: '1px solid #1E2D45', borderRadius: 8, color: '#F1F5F9',
    fontSize: 14, outline: 'none', boxSizing: 'border-box',
    transition: 'border-color 0.2s',
  }

  return (
    <div style={{ background: '#111827', border: '1px solid #1E2D45', borderRadius: 14, overflow: 'hidden' }}>
      {/* Tab bar */}
      <div style={{ display: 'flex', borderBottom: '1px solid #1E2D45', background: '#0A0E1A' }}>
        {tabBtn('url',  <Link2 size={14} />, 'URL')}
        {tabBtn('text', <FileText size={14} />, 'Paste Text')}
        {tabBtn('pdf',  <Upload size={14} />, 'Upload PDF')}
      </div>

      <div style={{ padding: 20 }}>
        {tab === 'url' && (
          <input
            type="url"
            placeholder="https://example.com/privacy-policy"
            value={url}
            onChange={e => setUrl(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && canSubmit && handleSubmit()}
            style={inputBase}
          />
        )}

        {tab === 'text' && (
          <>
            <textarea
              placeholder="Paste the full privacy policy text here... (min 100 characters)"
              value={text}
              onChange={e => setText(e.target.value)}
              rows={8}
              style={{ ...inputBase, resize: 'vertical', fontFamily: 'inherit', lineHeight: 1.6 }}
            />
            <div style={{ fontSize: 12, color: text.length < 100 ? '#94A3B8' : '#10B981', marginTop: 4 }}>
              {text.length} chars {text.length < 100 ? `(need ${100 - text.length} more)` : '✓'}
            </div>
          </>
        )}

        {tab === 'pdf' && (
          <div>
            <div
              onClick={() => fileRef.current?.click()}
              style={{
                border: '2px dashed #1E2D45', borderRadius: 8, padding: '32px 20px',
                textAlign: 'center', cursor: 'pointer', transition: 'border-color 0.2s',
              }}
              onMouseOver={e => (e.currentTarget.style.borderColor = '#00D4FF')}
              onMouseOut={e => (e.currentTarget.style.borderColor = '#1E2D45')}
            >
              <Upload size={28} color="#475569" style={{ marginBottom: 8 }} />
              <div style={{ color: '#94A3B8', fontSize: 14 }}>
                {pdfName || 'Click to upload PDF (max 10 MB)'}
              </div>
              {pdfB64 && <div style={{ color: '#10B981', fontSize: 12, marginTop: 4 }}>✓ {pdfName}</div>}
            </div>
            <input ref={fileRef} type="file" accept="application/pdf" onChange={handleFile} style={{ display: 'none' }} />
            {pdfError && <div style={{ color: '#EF4444', fontSize: 13, marginTop: 6 }}>{pdfError}</div>}
          </div>
        )}

        {/* Options row */}
        <div style={{ display: 'flex', gap: 12, marginTop: 16, flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ flex: '1 1 160px' }}>
            <label style={{ fontSize: 12, color: '#94A3B8', display: 'block', marginBottom: 4 }}>Language</label>
            <select
              value={language}
              onChange={e => setLanguage(e.target.value)}
              style={{ ...inputBase, padding: '9px 10px' }}
            >
              {LANGUAGES.map(l => <option key={l.code} value={l.code}>{l.label}</option>)}
            </select>
          </div>

          <div style={{ flex: '1 1 140px' }}>
            <label style={{ fontSize: 12, color: '#94A3B8', display: 'block', marginBottom: 4 }}>Reading level</label>
            <select
              value={audience}
              onChange={e => setAudience(e.target.value as 'adult' | 'teen' | 'child')}
              style={{ ...inputBase, padding: '9px 10px' }}
            >
              <option value="adult">Adult (Grade 6)</option>
              <option value="teen">Teen (Grade 7)</option>
              <option value="child">Child (Grade 3)</option>
            </select>
          </div>

          <div style={{ flex: '2 1 200px', display: 'flex', alignItems: 'flex-end' }}>
            <button
              onClick={handleSubmit}
              disabled={!canSubmit || loading}
              style={{
                width: '100%', padding: '11px 20px', borderRadius: 8,
                background: canSubmit && !loading ? '#00D4FF' : '#1A2236',
                color: canSubmit && !loading ? '#0A0E1A' : '#475569',
                border: 'none', cursor: canSubmit && !loading ? 'pointer' : 'not-allowed',
                fontSize: 15, fontWeight: 700,
                boxShadow: canSubmit && !loading ? '0 0 20px rgba(0,212,255,0.3)' : 'none',
                transition: 'all 0.2s',
              }}
            >
              {loading ? 'Analysing...' : '🔍 Analyse Privacy Policy'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
