import { useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import ProgressBar from '../ui/ProgressBar'

// ── Localized step labels ──────────────────────────────────────────────────
const STEP_LABELS: Record<string, string[]> = {
  en: [
    'Fetching document...',
    'Cleaning and processing text...',
    'Extracting clauses with AI...',
    'Scoring privacy risk...',
    'Rewriting in plain English...',
    'Checking compliance...',
    'Detecting dark patterns...',
  ],
  hi: [
    'दस्तावेज़ प्राप्त हो रहा है...',
    'टेक्स्ट साफ़ किया जा रहा है...',
    'AI से क्लॉज़ निकाले जा रहे हैं...',
    'गोपनीयता जोखिम की जांच...',
    'सरल हिंदी में लिखा जा रहा है...',
    'अनुपालन जांच...',
    'डार्क पैटर्न खोजे जा रहे हैं...',
  ],
  te: [
    'పత్రం పొందబడుతోంది...',
    'టెక్స్ట్ శుభ్రం చేయబడుతోంది...',
    'AI ద్వారా నిబంధనలు సేకరించబడుతున్నాయి...',
    'గోప్యత ప్రమాదం స్కోరింగ్...',
    'సరళ తెలుగులో రాయబడుతోంది...',
    'సమ్మతి తనిఖీ...',
    'డార్క్ ప్యాటర్న్‌లు గుర్తించబడుతున్నాయి...',
  ],
  ta: [
    'ஆவணம் பெறப்படுகிறது...',
    'உரை சுத்தம் செய்யப்படுகிறது...',
    'AI மூலம் விதிகள் பிரிக்கப்படுகின்றன...',
    'தனியுரிமை ஆபத்து மதிப்பீடு...',
    'எளிய தமிழில் எழுதப்படுகிறது...',
    'இணக்கம் சரிபார்ப்பு...',
    'இருண்ட வடிவங்கள் கண்டறியப்படுகின்றன...',
  ],
  fr: [
    'Récupération du document...',
    'Nettoyage du texte...',
    'Extraction des clauses par IA...',
    'Évaluation des risques...',
    'Réécriture en français simple...',
    'Vérification de la conformité...',
    'Détection des dark patterns...',
  ],
  de: [
    'Dokument wird abgerufen...',
    'Text wird bereinigt...',
    'KI extrahiert Klauseln...',
    'Datenschutzrisiko wird bewertet...',
    'Umschreibung in einfaches Deutsch...',
    'Compliance-Prüfung...',
    'Dark Patterns werden erkannt...',
  ],
  es: [
    'Obteniendo documento...',
    'Limpiando texto...',
    'Extrayendo cláusulas con IA...',
    'Evaluando riesgo de privacidad...',
    'Reescribiendo en español simple...',
    'Verificando cumplimiento...',
    'Detectando patrones oscuros...',
  ],
  ar: [
    'جارِ جلب المستند...',
    'تنظيف النص...',
    'استخراج البنود بالذكاء الاصطناعي...',
    'تقييم مخاطر الخصوصية...',
    'إعادة الكتابة بلغة بسيطة...',
    'التحقق من الامتثال...',
    'كشف الأنماط المظلمة...',
  ],
}

// Map progress % to the step index that should now be active.
function getActiveStep(progress: number): number {
  if (progress >= 85) return 6
  if (progress >= 75) return 5
  if (progress >= 65) return 4
  if (progress >= 50) return 3
  if (progress >= 25) return 2
  if (progress >= 18) return 1
  if (progress >= 5)  return 0
  return -1
}

interface Props {
  progress: number     // 0–100
  currentStep: string
  language?: string
}

export default function AnalysisProgress({ progress, currentStep, language = 'en' }: Props) {
  // Pick the right language steps; fallback to English
  const STEPS = STEP_LABELS[language] || STEP_LABELS['en']

  // Monotonically-increasing set — steps are added but never removed.
  const completedStepsRef = useRef<Set<number>>(new Set())

  useEffect(() => {
    const active = getActiveStep(progress)
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
            <div key={index} style={{
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

      {/* Skeleton loading cards — show what results will look like */}
      {progress > 5 && progress < 95 && (
        <div style={{ marginTop: 24, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ fontSize: 11, color: '#475569', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4 }}>
            Preparing results...
          </div>
          {[1, 2, 3].map(i => (
            <div key={i} className="skeleton" style={{
              height: 56, borderRadius: 10,
              background: 'linear-gradient(90deg, #1A2236 25%, #243049 50%, #1A2236 75%)',
              backgroundSize: '200% 100%',
            }} />
          ))}
        </div>
      )}
    </motion.div>
  )
}
