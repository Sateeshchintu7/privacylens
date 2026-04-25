import { useState } from 'react'
import { Volume2, Download, Mic } from 'lucide-react'
import { useAudio } from '../../hooks/useAudio'
import LoadingSpinner from '../ui/LoadingSpinner'
import type { AnalyseResponse } from '../../types'

const LANGUAGES = [
  { code: 'en',    flag: '🇬🇧', name: 'English'              },
  { code: 'hi',    flag: '🇮🇳', name: 'Hindi'                },
  { code: 'te',    flag: '🇮🇳', name: 'Telugu'               },
  { code: 'ta',    flag: '🇮🇳', name: 'Tamil'                },
  { code: 'kn',    flag: '🇮🇳', name: 'Kannada'              },
  { code: 'ml',    flag: '🇮🇳', name: 'Malayalam'            },
  { code: 'bn',    flag: '🇧🇩', name: 'Bengali'              },
  { code: 'mr',    flag: '🇮🇳', name: 'Marathi'              },
  { code: 'gu',    flag: '🇮🇳', name: 'Gujarati'             },
  { code: 'pa',    flag: '🇮🇳', name: 'Punjabi'              },
  { code: 'ur',    flag: '🇵🇰', name: 'Urdu'                 },
  { code: 'es',    flag: '🇪🇸', name: 'Spanish'              },
  { code: 'fr',    flag: '🇫🇷', name: 'French'               },
  { code: 'de',    flag: '🇩🇪', name: 'German'               },
  { code: 'it',    flag: '🇮🇹', name: 'Italian'              },
  { code: 'pt',    flag: '🇵🇹', name: 'Portuguese'           },
  { code: 'nl',    flag: '🇳🇱', name: 'Dutch'                },
  { code: 'pl',    flag: '🇵🇱', name: 'Polish'               },
  { code: 'ru',    flag: '🇷🇺', name: 'Russian'              },
  { code: 'ar',    flag: '🇸🇦', name: 'Arabic'               },
  { code: 'zh-cn', flag: '🇨🇳', name: 'Chinese (Simplified)' },
  { code: 'ja',    flag: '🇯🇵', name: 'Japanese'             },
  { code: 'ko',    flag: '🇰🇷', name: 'Korean'               },
  { code: 'tr',    flag: '🇹🇷', name: 'Turkish'              },
  { code: 'vi',    flag: '🇻🇳', name: 'Vietnamese'           },
  { code: 'id',    flag: '🇮🇩', name: 'Indonesian'           },
  { code: 'th',    flag: '🇹🇭', name: 'Thai'                 },
]

interface Props {
  data: AnalyseResponse
  audienceLevel: string
  onLanguageChange?: (lang: string) => void
}

type ContentType = 'summary' | 'redflags' | 'full'

export default function ListenMode({ data, audienceLevel, onLanguageChange }: Props) {
  const [lang, setLang] = useState('en')

  const handleLangChange = (newLang: string) => {
    setLang(newLang)
    onLanguageChange?.(newLang)
  }
  const [contentType, setContentType] = useState<ContentType>('summary')
  const { audioState, generate, downloadAudio } = useAudio()

  const MAX_AUDIO_CHARS = 1200 // ~1.5 min of speech; keeps gTTS fast on Render

  const buildText = (): string => {
    if (contentType === 'summary') {
      // Build full prose sentences — translates better than "Label: text" format
      const parts: string[] = []
      const grade = data.risk_report?.grade || 'unknown'
      const score = data.risk_report?.overall_score ?? 0
      parts.push(`This privacy policy received a risk grade of ${grade} with a score of ${score} out of 100.`)

      const gdpr = data.compliance?.gdpr_score
      const ccpa = data.compliance?.ccpa_score
      const dpdp = data.compliance?.dpdp_score
      if (gdpr !== undefined) {
        parts.push(
          `Compliance scores: GDPR ${Math.round(gdpr)} percent, ` +
          `CCPA ${Math.round(ccpa ?? 0)} percent, ` +
          `DPDP ${Math.round(dpdp ?? 0)} percent.`
        )
      }

      const topClauses = data.plain_clauses.slice(0, 3)
      topClauses.forEach(c => {
        if (c.plain_summary) parts.push(c.plain_summary)
      })

      return parts.join(' ').slice(0, MAX_AUDIO_CHARS)
    }
    if (contentType === 'redflags') {
      const flags = data.risk_report.top_red_flags
      if (!flags.length) return 'No major red flags found in this policy.'
      return (
        `This policy has ${flags.length} key concern${flags.length > 1 ? 's' : ''}. ` +
        flags.join('. ')
      ).slice(0, MAX_AUDIO_CHARS)
    }
    // full: all clause summaries as prose
    const full = data.plain_clauses
      .map(c => c.plain_summary || '')
      .filter(Boolean)
      .join(' ')
    return full.slice(0, MAX_AUDIO_CHARS)
  }

  const handleGenerate = () => generate(buildText(), lang, audienceLevel)

  const pillStyle = (active: boolean) => ({
    padding: '7px 16px', borderRadius: 20, fontSize: 13, cursor: 'pointer', fontWeight: active ? 600 : 400,
    background: active ? 'rgba(0,212,255,0.15)' : 'transparent',
    color: active ? '#00D4FF' : '#94A3B8',
    border: active ? '1px solid rgba(0,212,255,0.4)' : '1px solid #1E2D45',
    transition: 'all 0.2s',
  })

  return (
    <div style={{ background: '#111827', border: '1px solid #1E2D45', borderRadius: 16, padding: 28 }}>
      <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', marginBottom: 24 }}>
        {/* Language */}
        <div style={{ flex: 1, minWidth: 160 }}>
          <div style={{ fontSize: 12, color: '#475569', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>Language</div>
          <select
            value={lang} onChange={e => handleLangChange(e.target.value)}
            style={{ width: '100%', padding: '8px 12px', background: '#1A2236', border: '1px solid #1E2D45', borderRadius: 8, color: '#F1F5F9', fontSize: 14 }}
          >
            {LANGUAGES.map(l => <option key={l.code} value={l.code}>{l.flag} {l.name}</option>)}
          </select>
        </div>

        {/* Content type */}
        <div style={{ flex: 2 }}>
          <div style={{ fontSize: 12, color: '#475569', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>Content</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button style={pillStyle(contentType === 'summary')} onClick={() => setContentType('summary')}>Plain Summary</button>
            <button style={pillStyle(contentType === 'redflags')} onClick={() => setContentType('redflags')}>Red Flags Only</button>
            <button style={pillStyle(contentType === 'full')} onClick={() => setContentType('full')}>Full Details</button>
          </div>
        </div>
      </div>

      {/* Generate button */}
      <button
        onClick={handleGenerate}
        disabled={audioState.isGenerating}
        style={{
          width: '100%', padding: '14px', borderRadius: 10, fontSize: 15, fontWeight: 700,
          background: audioState.isGenerating ? '#1E2D45' : '#7C3AED',
          color: audioState.isGenerating ? '#475569' : '#fff',
          border: 'none', cursor: audioState.isGenerating ? 'not-allowed' : 'pointer',
          boxShadow: audioState.isGenerating ? 'none' : '0 0 20px rgba(124,58,237,0.3)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, transition: 'all 0.2s',
        }}
      >
        {audioState.isGenerating
          ? <><LoadingSpinner size={18} color="#fff" /> Generating audio...</>
          : <><Volume2 size={18} /> Generate Audio</>}
      </button>

      {/* Error */}
      {audioState.error && (
        <div style={{ marginTop: 12, padding: '10px 14px', background: 'rgba(239,68,68,0.1)', borderRadius: 8, color: '#EF4444', fontSize: 13 }}>
          {audioState.error}
        </div>
      )}

      {/* Audio player */}
      {audioState.audioUrl && (
        <div style={{ marginTop: 20 }}>
          <div style={{ marginBottom: 8, fontSize: 13, color: '#94A3B8' }}>
            Generated by: <span style={{ color: '#00D4FF', fontFamily: 'JetBrains Mono, monospace' }}>{audioState.engineUsed}</span>
            {audioState.duration > 0 && ` · ${audioState.duration.toFixed(1)}s`}
          </div>
          <audio controls src={audioState.audioUrl} style={{ width: '100%' }} />
          <button
            onClick={() => downloadAudio('privacylens-audio.mp3')}
            style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', background: 'transparent', border: '1px solid #1E2D45', borderRadius: 8, color: '#94A3B8', cursor: 'pointer', fontSize: 13 }}
          >
            <Download size={14} /> Download MP3
          </button>
        </div>
      )}

      {/* Voice input stub */}
      <div style={{ marginTop: 20, display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', background: '#1A2236', borderRadius: 8, border: '1px solid #1E2D45' }}>
        <Mic size={16} color="#475569" />
        <span style={{ fontSize: 13, color: '#475569' }}>Voice input — coming soon</span>
      </div>
    </div>
  )
}
