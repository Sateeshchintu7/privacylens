import { motion } from 'framer-motion'
import { useState, useEffect } from 'react'
import type { PlainClause, ClauseRisk, DarkPatternReport } from '../../types'
import { RISK_COLORS, RISK_BG } from '../../constants/risk'
import { CATEGORY_ICONS, DEFAULT_ICON, getDataTypeIcons } from '../../constants/icons'
import { useTranslation } from '../../hooks/useTranslation'

interface Props {
  plainClauses: PlainClause[]
  clauseRisks: ClauseRisk[]
  darkPatterns?: DarkPatternReport
  language?: string
}

const RISK_COLOURS = RISK_COLORS as Record<string, string>
const RISK_BG_MAP  = RISK_BG    as Record<string, string>
const RISK_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 }

export default function ReadMode({ plainClauses, clauseRisks, darkPatterns, language = 'en' }: Props) {
  const riskMap = Object.fromEntries(clauseRisks.map(r => [r.category, r]))
  const { translateBatch, translating, isEnglish } = useTranslation(language)
  const [translatedSummaries, setTranslatedSummaries] = useState<string[]>([])
  const [translatedGists, setTranslatedGists] = useState<string[]>([])

  useEffect(() => {
    if (isEnglish || plainClauses.length === 0) {
      setTranslatedSummaries([])
      setTranslatedGists([])
      return
    }
    const summaries = plainClauses.map(c => c.plain_summary || c.what_it_means || '')
    const gists = plainClauses.map(c => c.what_it_means || '')
    translateBatch(summaries).then(setTranslatedSummaries)
    translateBatch(gists).then(setTranslatedGists)
  }, [plainClauses, language]) // eslint-disable-line react-hooks/exhaustive-deps

  // Keep original index mapping so translated summaries align with clauses
  const sortedWithIdx = plainClauses
    .map((c, origIdx) => ({ clause: c, origIdx }))
    .sort((a, b) => {
      const ra = riskMap[a.clause.category]?.risk_level ?? 'low'
      const rb = riskMap[b.clause.category]?.risk_level ?? 'low'
      return (RISK_ORDER[ra] ?? 3) - (RISK_ORDER[rb] ?? 3)
    })

  const SEVERITY_COLOR: Record<string, string> = { high: '#EF4444', medium: '#F59E0B', low: '#94A3B8' }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {translating && !isEnglish && (
        <div style={{ fontSize: 12, color: '#64748B', marginBottom: 4, textAlign: 'center' }}>
          Translating clause summaries…
        </div>
      )}
      {sortedWithIdx.map(({ clause, origIdx }, i) => {
        const risk = riskMap[clause.category]
        const level = risk?.risk_level ?? 'low'
        const colour = RISK_COLOURS[level]
        const riskScore = risk?.final_score ?? 0

        return (
          <motion.details
            key={clause.category}
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
            style={{ background: '#111827', border: `1px solid ${colour}33`, borderLeft: `4px solid ${colour}`, borderRadius: 10, overflow: 'hidden' }}
          >
            {/* DP-3 Level 1: always-visible gist — icon + name + risk badge */}
            <summary style={{ padding: '14px 18px', cursor: 'pointer', listStyle: 'none', userSelect: 'none' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                {/* DP-2: coloured SVG icon container matching risk level */}
                <div style={{
                  width: 32, height: 32, borderRadius: 8, flexShrink: 0,
                  background: RISK_BG_MAP[level] ?? 'rgba(148,163,184,0.1)',
                  border: `1px solid ${colour}30`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: colour,
                }}>
                  {CATEGORY_ICONS[clause.category] ?? DEFAULT_ICON}
                </div>
                <span style={{ fontWeight: 700, color: '#F1F5F9', fontSize: 15, flex: 1 }}>{clause.category_label}</span>
                <span style={{
                  padding: '3px 10px', borderRadius: 12, fontSize: 11, fontWeight: 700,
                  background: `${colour}22`, color: colour, textTransform: 'uppercase', letterSpacing: 0.5,
                }}>
                  {level}
                </span>
                {riskScore > 0 && (
                  <span style={{ fontSize: 12, color: '#475569', fontFamily: 'JetBrains Mono, monospace' }}>
                    {riskScore.toFixed(0)}/100
                  </span>
                )}
                <span style={{ fontSize: 11, color: '#475569' }}>▼</span>
              </div>
              {/* DP-3 Level 1 gist — one-line summary always visible */}
              {clause.what_it_means && (
                <div style={{ fontSize: 13, color: '#94A3B8', marginTop: 5, paddingLeft: 34, lineHeight: 1.5 }}>
                  {translatedGists[origIdx] || clause.what_it_means}
                </div>
              )}
              {/* DP-2: data type SVG icons detected from clause text */}
              {(() => {
                const icons = getDataTypeIcons(clause.plain_summary || '')
                return icons.length > 0 ? (
                  <div style={{ paddingLeft: 44, marginTop: 4, display: 'flex', gap: 6, color: '#64748B' }}>
                    {icons.map((icon, i) => (
                      <span key={i}>{icon}</span>
                    ))}
                  </div>
                ) : null
              })()}
            </summary>
            {/* DP-3 Level 2: detail on expand */}
            <div style={{ padding: '4px 18px 18px', borderTop: '1px solid #1E2D45' }}>
              <p style={{ fontSize: 15, color: '#F1F5F9', lineHeight: 1.7, margin: '12px 0 8px' }}>
                {translatedSummaries[origIdx] || clause.plain_summary}
              </p>
              {risk?.red_flags?.length > 0 && (
                <div style={{ marginTop: 10, padding: '8px 12px', background: 'rgba(239,68,68,0.06)', borderRadius: 8 }}>
                  {risk.red_flags.map((f, j) => (
                    <div key={j} style={{ fontSize: 12, color: '#EF4444', marginBottom: 3 }}>⚠ {f}</div>
                  ))}
                </div>
              )}
              <div style={{ marginTop: 8, fontSize: 11, color: '#475569', fontFamily: 'JetBrains Mono, monospace', display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                <span>FK Grade: {clause.reading_grade.toFixed(1)} | Target: {clause.grade_target}</span>
              </div>
            </div>
          </motion.details>
        )
      })}

      {darkPatterns && darkPatterns.total_found > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
          style={{ marginTop: 8, background: '#111827', border: '1px solid rgba(245,158,11,0.25)', borderLeft: '4px solid #F59E0B', borderRadius: 10, padding: '16px 18px' }}
        >
          <div style={{ fontSize: 15, fontWeight: 700, color: '#F59E0B', marginBottom: 14 }}>
            ⚠ Manipulation Tactics ({darkPatterns.total_found})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {darkPatterns.patterns.map((p, i) => {
              const col = SEVERITY_COLOR[p.severity] ?? '#94A3B8'
              return (
                <div key={i} style={{ padding: '10px 14px', background: 'rgba(245,158,11,0.05)', borderRadius: 8, borderLeft: `3px solid ${col}` }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontSize: 13, fontWeight: 700, color: col }}>{p.label}</span>
                    <span style={{ fontSize: 11, padding: '1px 7px', borderRadius: 8, background: `${col}20`, color: col, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                      {p.severity}
                    </span>
                  </div>
                  <div style={{ fontSize: 13, color: '#94A3B8', marginBottom: 4 }}>{p.description}</div>
                  <div style={{ fontSize: 12, color: '#475569', fontStyle: 'italic' }}>{p.evidence}</div>
                </div>
              )
            })}
          </div>
        </motion.div>
      )}
    </div>
  )
}
