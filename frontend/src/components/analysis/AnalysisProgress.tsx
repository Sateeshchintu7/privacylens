import { useEffect, useRef, useState } from 'react'

interface Props {
  progress: number
  currentStep: string
  language: string
}

const STEP_LABELS: Record<string, string[]> = {
  en: [
    'Fetching document...',
    'Cleaning and processing text...',
    'Extracting clauses with AI...',
    'Scoring privacy risk...',
    'Rewriting in plain English...',
    'Checking GDPR compliance...',
    'Detecting contradictions...',
    'Analysis complete!',
  ],
  hi: [
    'दस्तावेज़ प्राप्त कर रहे हैं...',
    'टेक्स्ट साफ़ कर रहे हैं...',
    'AI से खंड निकाल रहे हैं...',
    'गोपनीयता जोखिम स्कोर कर रहे हैं...',
    'सरल हिंदी में लिख रहे हैं...',
    'GDPR अनुपालन जांच रहे हैं...',
    'विरोधाभास खोज रहे हैं...',
    'विश्लेषण पूर्ण!',
  ],
  te: [
    'పత్రాన్ని తీసుకుంటున్నారు...',
    'వచనాన్ని శుభ్రం చేస్తున్నారు...',
    'AI తో నిబంధనలు వెలికితీస్తున్నారు...',
    'గోప్యతా ప్రమాదం స్కోర్ చేస్తున్నారు...',
    'సరళమైన తెలుగులో రాస్తున్నారు...',
    'GDPR సమ్మతి తనిఖీ చేస్తున్నారు...',
    'వైరుధ్యాలు కనుగొంటున్నారు...',
    'విశ్లేషణ పూర్తయింది!',
  ],
  ta: [
    'ஆவணம் பெறுகிறோம்...',
    'உரையை சுத்தம் செய்கிறோம்...',
    'AI மூலம் பிரிவுகளை பிரிக்கிறோம்...',
    'தனியுரிமை ஆபத்தை மதிப்பிடுகிறோம்...',
    'எளிய தமிழில் எழுதுகிறோம்...',
    'GDPR இணக்கத்தை சரிபார்க்கிறோம்...',
    'முரண்பாடுகளை கண்டுபிடிக்கிறோம்...',
    'பகுப்பாய்வு முடிந்தது!',
  ],
  fr: [
    'Récupération du document...',
    'Nettoyage du texte...',
    'Extraction des clauses avec l\'IA...',
    'Évaluation des risques...',
    'Réécriture en français simple...',
    'Vérification GDPR...',
    'Détection des contradictions...',
    'Analyse terminée!',
  ],
  de: [
    'Dokument wird abgerufen...',
    'Text wird bereinigt...',
    'Klauseln werden extrahiert...',
    'Datenschutzrisiko wird bewertet...',
    'Auf einfaches Deutsch umschreiben...',
    'DSGVO-Konformität prüfen...',
    'Widersprüche erkennen...',
    'Analyse abgeschlossen!',
  ],
  es: [
    'Obteniendo documento...',
    'Limpiando texto...',
    'Extrayendo cláusulas con IA...',
    'Puntuando riesgo de privacidad...',
    'Reescribiendo en español sencillo...',
    'Verificando cumplimiento GDPR...',
    'Detectando contradicciones...',
    '¡Análisis completo!',
  ],
  ar: [
    'جارٍ جلب المستند...',
    'جارٍ تنظيف النص...',
    'جارٍ استخراج البنود بالذكاء الاصطناعي...',
    'جارٍ تقييم مخاطر الخصوصية...',
    'جارٍ إعادة الكتابة بالعربية البسيطة...',
    'جارٍ فحص الامتثال للائحة GDPR...',
    'جارٍ اكتشاف التناقضات...',
    'اكتملت التحليل!',
  ],
}

function progressToStep(pct: number): number {
  if (pct < 15) return 0
  if (pct < 20) return 1
  if (pct < 50) return 2
  if (pct < 65) return 3
  if (pct < 75) return 4
  if (pct < 85) return 5
  if (pct < 100) return 6
  return 7
}

export default function AnalysisProgress({ progress, currentStep, language }: Props) {
  const startRef = useRef(Date.now())
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setElapsed(Math.floor((Date.now() - startRef.current) / 1000)), 500)
    return () => clearInterval(t)
  }, [])

  const labels = STEP_LABELS[language] ?? STEP_LABELS['en']
  const stepIdx = progressToStep(progress)
  const displayLabel = labels[stepIdx] ?? currentStep

  let statusMsg = ''
  if (elapsed < 3) statusMsg = 'Connecting to server...'
  else if (elapsed >= 5 && progress < 15) statusMsg = 'Server is waking up, please wait...'

  const clampedPct = Math.min(Math.max(progress, 0), 100)

  return (
    <div style={{ maxWidth: 560, margin: '60px auto', padding: '0 16px' }}>
      {/* Main progress card */}
      <div style={{
        background: '#111827', border: '1px solid #1E2D45', borderRadius: 16,
        padding: 28, marginBottom: 24,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div style={{ fontSize: 15, color: '#F1F5F9', fontWeight: 600 }}>
            {statusMsg || displayLabel}
          </div>
          <div style={{ fontSize: 14, color: '#00D4FF', fontFamily: 'monospace', fontWeight: 700 }}>
            {clampedPct}%
          </div>
        </div>

        {/* Progress bar */}
        <div style={{ height: 6, background: '#1A2236', borderRadius: 3, overflow: 'hidden' }}>
          <div style={{
            height: '100%', width: `${clampedPct}%`,
            background: 'linear-gradient(90deg, #00D4FF, #7C3AED)',
            borderRadius: 3, transition: 'width 0.4s ease-out',
            boxShadow: '0 0 10px rgba(0,212,255,0.4)',
          }} />
        </div>

        {/* Step dots */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 12 }}>
          {labels.slice(0, 8).map((_, i) => (
            <div key={i} style={{
              width: 8, height: 8, borderRadius: '50%',
              background: i <= stepIdx ? '#00D4FF' : '#1A2236',
              border: `1px solid ${i <= stepIdx ? '#00D4FF' : '#1E2D45'}`,
              transition: 'all 0.3s',
            }} />
          ))}
        </div>

        {elapsed > 0 && (
          <div style={{ marginTop: 10, fontSize: 12, color: '#475569' }}>
            {elapsed}s elapsed
          </div>
        )}
      </div>

      {/* Skeleton preview cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {[90, 80, 70, 60, 75].map((w, i) => (
          <div key={i} className="skeleton" style={{ height: 72, width: '100%', borderRadius: 10 }}>
            <div style={{ display: 'flex', gap: 12, padding: 14, opacity: 0 }}>
              <div style={{ width: 36, height: 36, borderRadius: 8, background: '#2D3B4E' }} />
              <div style={{ flex: 1 }}>
                <div style={{ height: 10, width: `${w}%`, background: '#2D3B4E', borderRadius: 4, marginBottom: 6 }} />
                <div style={{ height: 8, width: `${w - 20}%`, background: '#2D3B4E', borderRadius: 4 }} />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
