import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Shield, Headphones, BarChart2, MessageCircle, Baby, ArrowRight, ChevronRight } from 'lucide-react'

const STATS = [
  '35+ Languages', '5 Output Modes', 'Free to Use',
  'Kids Safe', 'GDPR/CCPA/DPDP', 'Open Source',
]

const STEPS = [
  { icon: '📄', title: 'Input', desc: 'Paste a URL, upload a PDF, or type the text' },
  { icon: '🧠', title: 'Analyse', desc: 'AI extracts clauses, scores risk, checks compliance' },
  { icon: '🎯', title: 'Understand', desc: 'Read, Listen, See charts, Ask questions, or Kids Mode' },
]

const MODES = [
  { icon: <Shield size={32} color="#00D4FF" />, name: 'READ', desc: 'Plain English summary at Grade 6 reading level', color: '#00D4FF' },
  { icon: <Headphones size={32} color="#7C3AED" />, name: 'LISTEN', desc: 'Full audio in your language, kids voice included', color: '#7C3AED' },
  { icon: <BarChart2 size={32} color="#10B981" />, name: 'SEE', desc: 'Visual charts: risk heatmap, data flow, GDPR radar', color: '#10B981' },
  { icon: <MessageCircle size={32} color="#F59E0B" />, name: 'ASK', desc: 'Chat with the document — get cited answers', color: '#F59E0B' },
  { icon: <Baby size={32} color="#EF4444" />, name: 'KIDS', desc: 'Age-appropriate version with emoji safety verdict', color: '#EF4444' },
]

const WHO = ['👧 Children', '🧑 Teens', '👨 Adults', '🌍 Non-native speakers', '👁️ Visual learners', '📱 Mobile users', '🏢 Businesses', '🎓 Researchers']

export default function LandingPage() {
  const scanRef = useRef<HTMLDivElement>(null)

  useEffect(() => { document.title = 'PrivacyLens — Privacy Policies, Finally Explained' }, [])

  return (
    <div style={{ background: '#0A0E1A', minHeight: '100vh' }}>
      {/* ── HERO ─────────────────────────────────────────────────── */}
      <section
        className="grid-bg"
        style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '100px 24px 60px', position: 'relative', overflow: 'hidden' }}
      >
        {/* Glow orbs */}
        <div style={{ position: 'absolute', top: '20%', left: '10%', width: 400, height: 400, background: 'radial-gradient(circle, rgba(0,212,255,0.06) 0%, transparent 70%)', borderRadius: '50%', pointerEvents: 'none' }} />
        <div style={{ position: 'absolute', bottom: '20%', right: '10%', width: 300, height: 300, background: 'radial-gradient(circle, rgba(124,58,237,0.06) 0%, transparent 70%)', borderRadius: '50%', pointerEvents: 'none' }} />

        <div style={{ maxWidth: 1100, width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 40 }}>
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            style={{ border: '1px solid #1E2D45', borderRadius: 24, padding: '6px 16px', fontSize: 13, color: '#00D4FF', background: 'rgba(0,212,255,0.05)' }}
          >
            🔒 MSc Cyber Security &amp; Human Factors — 2025-26
          </motion.div>

          {/* Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            style={{ textAlign: 'center', fontSize: 'clamp(40px, 7vw, 72px)', fontWeight: 800, lineHeight: 1.1, margin: 0, color: '#F1F5F9' }}
          >
            Privacy Policies,{' '}
            <span style={{ color: '#00D4FF', textShadow: '0 0 40px rgba(0,212,255,0.4)' }}>
              Finally Explained.
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}
            style={{ fontSize: 20, color: '#94A3B8', textAlign: 'center', maxWidth: 600, lineHeight: 1.6, margin: 0 }}
          >
            PrivacyLens uses AI to decode any privacy policy, terms &amp; conditions,
            or legal document — in plain English, any language, for any age.
          </motion.p>

          {/* CTAs */}
          <motion.div
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
            style={{ display: 'flex', gap: 16, flexWrap: 'wrap', justifyContent: 'center' }}
          >
            <Link
              to="/analyse"
              style={{
                padding: '14px 28px', background: '#00D4FF', color: '#0A0E1A',
                borderRadius: 10, textDecoration: 'none', fontSize: 16, fontWeight: 700,
                boxShadow: '0 0 30px rgba(0,212,255,0.35)',
                display: 'flex', alignItems: 'center', gap: 8,
              }}
            >
              Analyse a Policy <ArrowRight size={18} />
            </Link>
            <a
              href="#how-it-works"
              style={{
                padding: '14px 28px', border: '1px solid #1E2D45', color: '#F1F5F9',
                borderRadius: 10, textDecoration: 'none', fontSize: 16, fontWeight: 600,
                background: 'rgba(255,255,255,0.03)',
              }}
            >
              How it Works
            </a>
          </motion.div>

          {/* Hero demo card */}
          <motion.div
            initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
            style={{ display: 'flex', gap: 20, width: '100%', maxWidth: 900, flexWrap: 'wrap', justifyContent: 'center', marginTop: 20 }}
          >
            {/* Original policy card */}
            <div ref={scanRef} style={{ flex: '1 1 380px', background: '#111827', border: '1px solid #1E2D45', borderRadius: 16, padding: 24, position: 'relative', overflow: 'hidden', minHeight: 200 }}>
              <div style={{ fontSize: 12, color: '#475569', marginBottom: 12, textTransform: 'uppercase', letterSpacing: 1 }}>Original Policy Text</div>
              <div style={{ fontSize: 11, color: '#475569', lineHeight: 1.8, fontFamily: 'monospace' }}>
                {`We and our partners process data to provide: Use precise geolocation data. Actively scan device characteristics for identification. Store and/or access information on a device. Personalised ads and content, ad and content measurement, audience insights and product development...`}
              </div>
              <div className="scan-line" />
            </div>

            {/* PrivacyLens output */}
            <div style={{ flex: '1 1 380px', background: '#111827', border: '1px solid #00D4FF', borderRadius: 16, padding: 24, boxShadow: '0 0 30px rgba(0,212,255,0.1)' }}>
              <div style={{ fontSize: 12, color: '#00D4FF', marginBottom: 12, textTransform: 'uppercase', letterSpacing: 1 }}>PrivacyLens Output</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                <div style={{ width: 48, height: 48, background: '#F59E0B', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'monospace', fontSize: 24, fontWeight: 900, boxShadow: '0 0 20px rgba(245,158,11,0.4)' }}>C</div>
                <div>
                  <div style={{ fontWeight: 700, color: '#F1F5F9' }}>Grade C — Some concerns</div>
                  <div style={{ fontSize: 12, color: '#94A3B8' }}>54/100 risk score</div>
                </div>
              </div>
              {[
                { icon: '🚨', text: 'Tracks your precise location', color: '#EF4444' },
                { icon: '🚨', text: 'Shares data with advertisers', color: '#EF4444' },
                { icon: '✅', text: 'You can request data deletion', color: '#10B981' },
              ].map((f, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.8 + i * 0.3 }}
                  style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8, fontSize: 13, color: f.color }}
                >
                  <span>{f.icon}</span> {f.text}
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── STATS BAR ─────────────────────────────────────────────── */}
      <div style={{ background: '#111827', borderTop: '1px solid #1E2D45', borderBottom: '1px solid #1E2D45', padding: '16px 24px', overflowX: 'auto' }}>
        <div style={{ display: 'flex', gap: 0, minWidth: 500, justifyContent: 'center', flexWrap: 'wrap' }}>
          {STATS.map((s, i) => (
            <div key={i} style={{ padding: '8px 24px', borderRight: i < STATS.length - 1 ? '1px solid #1E2D45' : 'none', fontSize: 14, color: '#94A3B8', whiteSpace: 'nowrap' }}>
              <span style={{ color: '#00D4FF', marginRight: 6 }}>✦</span>{s}
            </div>
          ))}
        </div>
      </div>

      {/* ── HOW IT WORKS ─────────────────────────────────────────── */}
      <section id="how-it-works" style={{ padding: '80px 24px', maxWidth: 1100, margin: '0 auto' }}>
        <motion.h2
          initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}
          style={{ textAlign: 'center', fontSize: 36, fontWeight: 800, color: '#F1F5F9', marginBottom: 48 }}
        >
          How PrivacyLens Works
        </motion.h2>
        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', justifyContent: 'center' }}>
          {STEPS.map((step, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.15 }}
              style={{ flex: '1 1 260px', maxWidth: 320, background: '#111827', border: '1px solid #1E2D45', borderRadius: 16, padding: 28, textAlign: 'center', cursor: 'default', transition: 'border-color 0.2s, box-shadow 0.2s' }}
              whileHover={{ borderColor: '#00D4FF', boxShadow: '0 0 20px rgba(0,212,255,0.1)' }}
            >
              <div style={{ fontSize: 40, marginBottom: 16 }}>{step.icon}</div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginBottom: 12 }}>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 13, color: '#00D4FF', background: 'rgba(0,212,255,0.1)', padding: '2px 10px', borderRadius: 20 }}>Step {i + 1}</span>
              </div>
              <div style={{ fontSize: 18, fontWeight: 700, color: '#F1F5F9', marginBottom: 8 }}>{step.title}</div>
              <div style={{ fontSize: 14, color: '#94A3B8', lineHeight: 1.6 }}>{step.desc}</div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── 5 MODES ─────────────────────────────────────────────── */}
      <section style={{ padding: '80px 24px', background: '#111827' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <motion.h2
            initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}
            style={{ textAlign: 'center', fontSize: 36, fontWeight: 800, color: '#F1F5F9', marginBottom: 12 }}
          >
            Five Ways to Understand Any Policy
          </motion.h2>
          <p style={{ textAlign: 'center', color: '#94A3B8', marginBottom: 48 }}>Choose the format that works for you.</p>
          <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', justifyContent: 'center' }}>
            {MODES.map((m, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, scale: 0.95 }} whileInView={{ opacity: 1, scale: 1 }} viewport={{ once: true }} transition={{ delay: i * 0.1 }}
                whileHover={{ y: -4, boxShadow: `0 0 30px ${m.color}20` }}
                style={{ flex: '1 1 180px', maxWidth: 220, background: '#1A2236', border: `1px solid #1E2D45`, borderRadius: 16, padding: 24, textAlign: 'center', cursor: 'default', transition: 'all 0.2s' }}
              >
                <div style={{ marginBottom: 16 }}>{m.icon}</div>
                <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 13, fontWeight: 700, color: m.color, marginBottom: 8 }}>{m.name}</div>
                <div style={{ fontSize: 13, color: '#94A3B8', lineHeight: 1.5 }}>{m.desc}</div>
              </motion.div>
            ))}
          </div>
          <div style={{ textAlign: 'center', marginTop: 40 }}>
            <Link
              to="/analyse"
              style={{ padding: '12px 24px', background: 'rgba(0,212,255,0.1)', border: '1px solid #00D4FF', color: '#00D4FF', borderRadius: 8, textDecoration: 'none', fontSize: 15, fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 6 }}
            >
              Try All Five Modes <ChevronRight size={16} />
            </Link>
          </div>
        </div>
      </section>

      {/* ── WHO IT'S FOR ─────────────────────────────────────────── */}
      <section style={{ padding: '80px 24px', maxWidth: 1100, margin: '0 auto' }}>
        <motion.h2
          initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}
          style={{ textAlign: 'center', fontSize: 36, fontWeight: 800, color: '#F1F5F9', marginBottom: 40 }}
        >
          Built for Everyone
        </motion.h2>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', justifyContent: 'center' }}>
          {WHO.map((w, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} transition={{ delay: i * 0.07 }}
              style={{ padding: '12px 20px', background: '#111827', border: '1px solid #1E2D45', borderRadius: 32, fontSize: 15, color: '#94A3B8' }}
            >
              {w}
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── FINAL CTA ─────────────────────────────────────────────── */}
      <section style={{ padding: '80px 24px', textAlign: 'center', background: '#111827', borderTop: '1px solid #1E2D45' }}>
        <motion.h2
          initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}
          style={{ fontSize: 40, fontWeight: 800, color: '#F1F5F9', marginBottom: 16 }}
        >
          Ready to decode your first policy?
        </motion.h2>
        <p style={{ color: '#94A3B8', fontSize: 18, marginBottom: 32 }}>Paste any URL and get results in under a minute.</p>
        <Link
          to="/analyse"
          style={{ padding: '16px 36px', background: '#00D4FF', color: '#0A0E1A', borderRadius: 12, textDecoration: 'none', fontSize: 18, fontWeight: 700, boxShadow: '0 0 40px rgba(0,212,255,0.35)', display: 'inline-flex', alignItems: 'center', gap: 10 }}
        >
          Analyse a Policy Now <ArrowRight size={20} />
        </Link>
      </section>
    </div>
  )
}
