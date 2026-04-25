import { useState } from 'react'
import type { AnalyseResponse, ClauseRisk, PolicyRiskReport } from '../../types'
import ProgressBar from '../ui/ProgressBar'
import { RISK_COLORS } from '../../constants/risk'

interface Props { data: AnalyseResponse; policyName: string }
type SubTab = 'risk' | 'gdpr' | 'compliance' | 'sankey'
function scoreColor(s: number) {
  if (s <= 25) return '#10B981'
  if (s <= 50) return '#F59E0B'
  if (s <= 75) return '#F97316'
  return '#EF4444'
}

export default function SeeMode({ data, policyName }: Props) {
  const [subTab, setSubTab] = useState<SubTab>('risk')
  const { risk_report: rr, compliance } = data

  const tabStyle = (t: SubTab) => ({
    padding: '8px 16px', borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 600,
    background: subTab === t ? 'rgba(0,212,255,0.15)' : 'transparent',
    color: subTab === t ? '#00D4FF' : '#94A3B8',
    border: subTab === t ? '1px solid rgba(0,212,255,0.4)' : '1px solid transparent',
  })

  const gdprDims = [
    'Lawful Basis (Art.6)', 'Transparency (Art.13)', 'Data Minimisation (Art.5)',
    'Purpose Limitation (Art.5)', 'Retention Limits (Art.5)', 'User Rights (Art.15-22)',
    'Security (Art.32)', 'Breach Notification (Art.33)',
  ]
  const radarScores = gdprDims.map(d => compliance.radar_scores?.[d] ?? 50)

  return (
    <div style={{ background: '#111827', border: '1px solid #1E2D45', borderRadius: 16, padding: 24 }}>
      <div style={{ display: 'flex', gap: 8, marginBottom: 24, flexWrap: 'wrap' }}>
        <button style={tabStyle('risk')}       onClick={() => setSubTab('risk')}>🌡️ Risk</button>
        <button style={tabStyle('gdpr')}       onClick={() => setSubTab('gdpr')}>⚖️ GDPR Radar</button>
        <button style={tabStyle('compliance')} onClick={() => setSubTab('compliance')}>📋 Compliance</button>
        <button style={tabStyle('sankey')}     onClick={() => setSubTab('sankey')}>🌊 Data Flow</button>
      </div>

      {subTab === 'risk'       && <RiskGrid risks={rr.clause_risks} />}
      {subTab === 'gdpr'       && <GdprRadar dims={gdprDims} scores={radarScores} policyName={policyName} />}
      {subTab === 'compliance' && <ComplianceView compliance={compliance} />}
      {subTab === 'sankey'     && <DataFlowDiagram data={data} />}
    </div>
  )
}

// ── Risk Grid ─────────────────────────────────────────────────────────────────

const EMOJI_LABELS: Record<string, string> = {
  data_collection:      '👀 What They Collect',
  cookies_tracking:     '🍪 Cookies & Tracking',
  children_data:        '👶 Children\'s Data',
  contact_info:         '📧 Contact Info',
  purpose_limitation:   '🎯 How Data Is Used',
  retention_period:     '⏳ How Long They Keep It',
  data_security:        '🔒 Security',
  consent_mechanism:    '✅ Your Consent',
  user_rights:          '🛡️ Your Rights',
  third_party_sharing:  '🔗 Who Else Gets It',
  cross_border_transfer:'🌍 International Transfers',
  breach_notification:  '🚨 Breach Response',
}

function RiskGrid({ risks }: { risks: ClauseRisk[] }) {
  const [expanded, setExpanded] = useState<string | null>(null)

  // Deduplicate: keep highest score per category (max 12 boxes)
  const seen = new Map<string, ClauseRisk>()
  risks.forEach(r => {
    const existing = seen.get(r.category)
    if (!existing || r.final_score > existing.final_score) seen.set(r.category, r)
  })
  const deduped = Array.from(seen.values()).slice(0, 12)
  const expandedRow = deduped.find(x => x.category === expanded)

  return (
    <div>
      <div style={{ marginBottom: 14, padding: '9px 14px', background: 'rgba(0,212,255,0.05)', border: '1px solid rgba(0,212,255,0.15)', borderRadius: 8, fontSize: 12, color: '#94A3B8' }}>
        Each box shows a risk score (0–100). Click a box for details. <span style={{ color: '#10B981', fontWeight: 600 }}>Green</span> = low &nbsp;|&nbsp; <span style={{ color: '#F59E0B', fontWeight: 600 }}>Amber</span> = medium &nbsp;|&nbsp; <span style={{ color: '#F97316', fontWeight: 600 }}>Orange</span> = high &nbsp;|&nbsp; <span style={{ color: '#EF4444', fontWeight: 600 }}>Red</span> = critical
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 10 }}>
        {deduped.map(r => (
          <div
            key={r.category}
            onClick={() => setExpanded(expanded === r.category ? null : r.category)}
            style={{
              background: scoreColor(r.final_score),
              borderRadius: 10,
              padding: '14px 16px',
              cursor: 'pointer',
              outline: expanded === r.category ? '2px solid rgba(255,255,255,0.6)' : 'none',
              outlineOffset: 2,
            }}
          >
            <div style={{ fontSize: 11, fontWeight: 700, color: 'rgba(255,255,255,0.85)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 }}>
              {EMOJI_LABELS[r.category] ?? r.category_label}
            </div>
            <div style={{ fontSize: 28, fontWeight: 800, color: '#fff', lineHeight: 1 }}>{Math.round(r.final_score)}</div>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.75)', textTransform: 'uppercase', letterSpacing: 0.5, marginTop: 4 }}>{r.risk_level}</div>
          </div>
        ))}
      </div>
      {expandedRow && (
        <div style={{ marginTop: 12, padding: '12px 16px', background: 'rgba(15,23,42,0.9)', border: `1px solid ${scoreColor(expandedRow.final_score)}`, borderRadius: 10 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#F1F5F9', marginBottom: 8 }}>
            {EMOJI_LABELS[expandedRow.category] ?? expandedRow.category_label}
            <span style={{ marginLeft: 10, fontSize: 11, fontWeight: 400, color: '#94A3B8' }}>Score: {Math.round(expandedRow.final_score)} · {expandedRow.risk_level.toUpperCase()}</span>
          </div>
          {(expandedRow.red_flags ?? []).length > 0 ? (expandedRow.red_flags ?? []).map((f, i) => (
            <div key={i} style={{ fontSize: 12, color: '#CBD5E1', marginBottom: 5, paddingLeft: 10, borderLeft: `3px solid ${scoreColor(expandedRow.final_score)}` }}>
              {f}
            </div>
          )) : (
            <div style={{ fontSize: 12, color: '#94A3B8' }}>No specific issues noted for this category.</div>
          )}
        </div>
      )}
      <div style={{ display: 'flex', gap: 16, marginTop: 14, flexWrap: 'wrap' }}>
        {([['#10B981','Low (0–25)'],['#F59E0B','Medium (26–50)'],['#F97316','High (51–75)'],['#EF4444','Critical (76–100)']] as [string,string][]).map(([c, l]) => (
          <span key={l} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: '#94A3B8' }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: c, display: 'inline-block' }} />
            {l}
          </span>
        ))}
      </div>
    </div>
  )
}

// ── GDPR SVG Radar ────────────────────────────────────────────────────────────

function GdprRadar({ dims, scores, policyName }: { dims: string[]; scores: number[]; policyName: string }) {
  const CX = 260, CY = 215, R = 140
  const n = dims.length

  const pt = (i: number, score: number) => {
    const a = (i * 2 * Math.PI / n) - Math.PI / 2
    const r = (Math.max(0, Math.min(100, score)) / 100) * R
    return { x: CX + r * Math.cos(a), y: CY + r * Math.sin(a) }
  }
  const outerPt = (i: number) => {
    const a = (i * 2 * Math.PI / n) - Math.PI / 2
    const r = R + 28
    return { x: CX + r * Math.cos(a), y: CY + r * Math.sin(a) }
  }
  const poly = (pts: {x:number;y:number}[]) =>
    pts.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')

  const gridLevels = [25, 50, 75, 100]
  const idealPts  = dims.map((_, i) => pt(i, 100))
  const actualPts = dims.map((_, i) => pt(i, scores[i]))

  return (
    <div>
      <div style={{ fontSize: 12, color: '#94A3B8', marginBottom: 12 }}>
        GDPR compliance across 8 dimensions — <span style={{ color: '#F1F5F9' }}>{policyName}</span>
      </div>
      <svg viewBox="0 0 520 440" style={{ width: '100%', maxWidth: 560 }}>
        {/* Grid rings */}
        {gridLevels.map(pct => (
          <polygon key={pct}
            points={poly(dims.map((_, i) => pt(i, pct)))}
            fill="none" stroke="#1E2D45" strokeWidth="1"
          />
        ))}
        {/* Grid ring labels */}
        {gridLevels.map(pct => (
          <text key={`lbl-${pct}`}
            x={CX + 4} y={CY - (pct / 100) * R - 3}
            fontSize="9" fill="#475569"
          >{pct}</text>
        ))}
        {/* Axes */}
        {dims.map((_, i) => {
          const outer = pt(i, 100)
          return <line key={i} x1={CX} y1={CY} x2={outer.x} y2={outer.y} stroke="#1E2D45" strokeWidth="1" />
        })}
        {/* Ideal polygon */}
        <polygon points={poly(idealPts)}
          fill="rgba(124,58,237,0.06)" stroke="#7C3AED" strokeWidth="1.5" strokeDasharray="4 3" />
        {/* Actual polygon */}
        <polygon points={poly(actualPts)}
          fill="rgba(0,212,255,0.12)" stroke="#00D4FF" strokeWidth="2" />
        {/* Score dots */}
        {actualPts.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r="4" fill="#00D4FF" stroke="#111827" strokeWidth="1.5" />
        ))}
        {/* Labels */}
        {dims.map((dim, i) => {
          const lp = outerPt(i)
          const shortLabel = dim.replace(/\s*\(.*\)/, '')
          const anchor = lp.x < CX - 8 ? 'end' : lp.x > CX + 8 ? 'start' : 'middle'
          return (
            <g key={i}>
              <text x={lp.x} y={lp.y - 5} textAnchor={anchor} fontSize="10" fill="#94A3B8">{shortLabel}</text>
              <text x={lp.x} y={lp.y + 9} textAnchor={anchor} fontSize="12" fontWeight="700"
                fill={scores[i] >= 70 ? '#10B981' : scores[i] >= 40 ? '#F59E0B' : '#EF4444'}>
                {Math.round(scores[i])}
              </text>
            </g>
          )
        })}
        {/* Legend */}
        <rect x="10" y="422" width="10" height="10" fill="rgba(0,212,255,0.12)" stroke="#00D4FF" strokeWidth="1.5" rx="2" />
        <text x="25" y="431" fontSize="10" fill="#94A3B8">This Policy</text>
        <rect x="120" y="422" width="10" height="10" fill="rgba(124,58,237,0.06)" stroke="#7C3AED" strokeWidth="1.5" strokeDasharray="4 3" rx="2" />
        <text x="135" y="431" fontSize="10" fill="#94A3B8">GDPR Ideal (100)</text>
      </svg>
    </div>
  )
}

// ── Compliance Bars ───────────────────────────────────────────────────────────

const GAP_EXPLANATIONS: Record<string, string> = {
  'Art.5':   'Data must only be used for the purpose it was collected for',
  'Art.6':   'There must be a clear legal reason for collecting your data',
  'Art.7':   'Consent must be freely given and easy to withdraw at any time',
  'Art.12':  'Privacy information must be written in plain, understandable language',
  'Art.13':  'You must be told what data is collected, why, and for how long',
  'Art.13.1':'The company\'s identity and contact details must be clearly stated',
  'Art.13.2':'Your rights and data retention periods must be explained',
  'Art.15':  'You have the right to see all data the company holds on you',
  'Art.16':  'You can ask them to correct any wrong information about you',
  'Art.17':  'You can ask them to delete your data ("right to be forgotten")',
  'Art.20':  'You can take your data to another service (data portability)',
  'Art.21':  'You can object to your data being used for certain purposes',
  'Art.22':  'You have rights around automated decisions that affect you',
  'Art.32':  'The company must have proper security measures to protect your data',
  'Art.33':  'Data breaches must be reported to authorities within 72 hours',
  'Art.50':  'AI systems must clearly tell users they are interacting with AI',
  'Sec.1798.100': 'California residents can request to see all data held about them',
  'Sec.1798.105': 'California residents can request deletion of their personal data',
  'Sec.1798.120': 'California residents can opt out of the sale of their personal data',
  'Sec.5':   'The policy must clearly state what personal data is collected (DPDP)',
  'Sec.7':   'Proper consent must be obtained before collecting data (DPDP)',
  'Sec.11':  'Adequate security measures must protect personal data (DPDP)',
}

function gapLabel(article: string, requirement: string): string {
  return GAP_EXPLANATIONS[article] ?? requirement
}

function ComplianceView({ compliance }: { compliance: AnalyseResponse['compliance'] }) {
  const euAiScore = compliance.eu_ai_act_score ?? 0
  return (
    <div>
      <div style={{ display: 'flex', gap: 20, marginBottom: 20, flexWrap: 'wrap' }}>
        {([
          { label: 'GDPR (EU)',         score: compliance.gdpr_score  },
          { label: 'CCPA (California)', score: compliance.ccpa_score  },
          { label: 'DPDP (India)',      score: compliance.dpdp_score  },
        ]).map(c => (
          <div key={c.label} style={{ flex: '1 1 180px' }}>
            <ProgressBar
              value={c.score}
              color={c.score >= 75 ? '#10B981' : c.score >= 50 ? '#F59E0B' : '#EF4444'}
              height={12}
              label={c.label}
            />
          </div>
        ))}
      </div>
      <div style={{ marginBottom: 10, padding: '10px 14px', background: 'rgba(124,58,237,0.05)', border: '1px solid rgba(124,58,237,0.15)', borderRadius: 8, fontSize: 12, color: '#94A3B8' }}>
        <span style={{ fontWeight: 600, color: '#C4B5FD' }}>EU AI Act</span> requires companies to tell users when they are interacting with AI systems. Article 50 transparency obligations apply from <span style={{ color: '#F1F5F9' }}>August 2, 2026</span>.
      </div>
      <div style={{ marginBottom: 28, padding: '12px 16px', background: 'rgba(124,58,237,0.07)', border: '1px solid rgba(124,58,237,0.2)', borderRadius: 10 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <span style={{ fontSize: 13, fontWeight: 700, color: '#C4B5FD' }}>EU AI Act Art.50 (Transparency)</span>
          <span style={{ fontSize: 11, color: '#7C3AED', fontStyle: 'italic' }}>Enforcement begins Aug 2, 2026</span>
        </div>
        <ProgressBar
          value={euAiScore}
          color={euAiScore >= 75 ? '#10B981' : euAiScore >= 50 ? '#F59E0B' : '#EF4444'}
          height={10}
          label=""
        />
        {compliance.eu_ai_act_gaps && compliance.eu_ai_act_gaps.length > 0 && (
          <div style={{ marginTop: 10 }}>
            {compliance.eu_ai_act_gaps.map((g, i) => (
              <div key={i} style={{ fontSize: 12, color: '#94A3B8', marginBottom: 4, paddingLeft: 8, borderLeft: '2px solid rgba(124,58,237,0.4)' }}>
                {gapLabel(g.article, g.requirement)}
              </div>
            ))}
          </div>
        )}
      </div>
      {compliance.critical_gaps?.length > 0 && (
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#EF4444', marginBottom: 12 }}>🔴 Critical Gaps</div>
          {compliance.critical_gaps.map((g, i) => (
            <div key={i} style={{ padding: '10px 14px', background: 'rgba(239,68,68,0.06)', borderLeft: '3px solid #EF4444', borderRadius: '0 8px 8px 0', marginBottom: 8 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#EF4444', marginBottom: 2 }}>{g.regulation} · {g.article}</div>
              <div style={{ fontSize: 13, color: '#CBD5E1' }}>{gapLabel(g.article, g.requirement)}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Data Flow Diagram (CSS grid, always 3 columns) ───────────────────────────

// Maps each clause category to a specific (collected → purpose → recipient) flow
const _FLOW_DATA: Record<string, { collected: string; purpose: string; recipient: string }> = {
  data_collection:       { collected: 'Personal Data',       purpose: 'Service Operation', recipient: 'The Company'       },
  cookies_tracking:      { collected: 'Cookies & Tracking',  purpose: 'Analytics & Ads',   recipient: 'Advertisers'       },
  third_party_sharing:   { collected: 'Personal Data',       purpose: 'Business Ops',       recipient: 'Third Parties'     },
  retention_period:      { collected: 'Personal Data',       purpose: 'Record Keeping',     recipient: 'The Company'       },
  children_data:         { collected: "Children's Data",      purpose: 'Service Operation', recipient: 'The Company'       },
  cross_border_transfer: { collected: 'Personal Data',       purpose: 'Global Business',    recipient: 'International'     },
  user_rights:           { collected: 'Account Data',        purpose: 'User Control',       recipient: 'You'               },
  data_security:         { collected: 'All Data',            purpose: 'Protection',         recipient: 'Secure Storage'    },
  consent_mechanism:     { collected: 'Consent Records',     purpose: 'Legal Basis',        recipient: 'The Company'       },
  breach_notification:   { collected: 'Incident Data',       purpose: 'Compliance',         recipient: 'Regulators'        },
  contact_info:          { collected: 'Contact Details',     purpose: 'Support',            recipient: 'Support Team'      },
  purpose_limitation:    { collected: 'Usage Data',          purpose: 'Service Improvement', recipient: 'The Company'      },
}

const _DEFAULT_FLOWS = [
  { collected: 'Personal Data',      purpose: 'Service Operation', recipient: 'The Company',  risk: 'medium' },
  { collected: 'Cookies & Tracking', purpose: 'Analytics & Ads',   recipient: 'Advertisers',  risk: 'high'   },
  { collected: 'Personal Data',      purpose: 'Business Ops',      recipient: 'Third Parties', risk: 'high'  },
  { collected: 'Account Data',       purpose: 'User Control',      recipient: 'You',           risk: 'low'   },
]

function DataFlowDiagram({ data }: { data: AnalyseResponse }) {
  const riskMap: Record<string, string> = {}
  data.risk_report.clause_risks.forEach(cr => { riskMap[cr.category] = cr.risk_level })

  // Build flows from actual clause data; fall back to defaults if too few
  const flows = (() => {
    const seen = new Set<string>()
    const result: Array<{ collected: string; purpose: string; recipient: string; risk: string }> = []
    data.clauses.forEach((c: { category: string }) => {
      const fd = _FLOW_DATA[c.category]
      if (!fd) return
      const key = `${fd.collected}|${fd.purpose}|${fd.recipient}`
      if (seen.has(key)) return
      seen.add(key)
      result.push({ ...fd, risk: riskMap[c.category] ?? 'low' })
    })
    return result.length >= 2 ? result : _DEFAULT_FLOWS
  })()

  return (
    <div>
      <div style={{ fontSize: 12, color: '#475569', marginBottom: 14 }}>
        How data moves through this policy — each row is one data flow, coloured by risk level
      </div>

      {/* Column headers */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 40px 1fr 40px 1fr', marginBottom: 12 }}>
        {(['WHAT IS COLLECTED', '', 'HOW IT IS USED', '', 'WHO SEES IT'] as string[]).map((h, i) => (
          <div key={i} style={{
            fontSize: 10, fontWeight: 700, color: '#475569',
            textTransform: 'uppercase', letterSpacing: 1,
            textAlign: i === 0 ? 'left' : i === 4 ? 'right' : 'center',
          }}>{h}</div>
        ))}
      </div>

      {/* One row per flow */}
      {flows.map((flow, idx) => {
        const col = (RISK_COLORS as Record<string, string>)[flow.risk] ?? '#475569'
        return (
          <div key={idx} style={{
            display: 'grid',
            gridTemplateColumns: '1fr 40px 1fr 40px 1fr',
            alignItems: 'center',
            marginBottom: 10,
          }}>
            <div style={{ border: `2px solid ${col}`, borderRadius: 8, padding: '10px 14px', background: `${col}15` }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#F1F5F9' }}>{flow.collected}</div>
              <div style={{ fontSize: 10, color: col, textTransform: 'uppercase', marginTop: 2 }}>{flow.risk}</div>
            </div>
            <div style={{ textAlign: 'center', fontSize: 20, color: '#475569', lineHeight: 1 }}>→</div>
            <div style={{ border: `2px solid ${col}`, borderRadius: 8, padding: '10px 14px', background: `${col}15`, textAlign: 'center' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#F1F5F9' }}>{flow.purpose}</div>
            </div>
            <div style={{ textAlign: 'center', fontSize: 20, color: '#475569', lineHeight: 1 }}>→</div>
            <div style={{ border: `2px solid ${col}`, borderRadius: 8, padding: '10px 14px', background: `${col}15`, textAlign: 'right' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#F1F5F9' }}>{flow.recipient}</div>
            </div>
          </div>
        )
      })}

      <div style={{ display: 'flex', gap: 16, marginTop: 14, flexWrap: 'wrap' }}>
        {([['#10B981','Low'],['#F59E0B','Medium'],['#F97316','High'],['#EF4444','Critical']] as [string,string][]).map(([c, l]) => (
          <span key={l} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: '#94A3B8' }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: c, display: 'inline-block' }} />
            {l}
          </span>
        ))}
      </div>
    </div>
  )
}
