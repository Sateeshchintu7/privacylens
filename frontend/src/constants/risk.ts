export const RISK_COLORS = {
  critical: '#EF4444',
  high:     '#F97316',
  medium:   '#F59E0B',
  low:      '#10B981',
} as const

export const RISK_BG = {
  critical: 'rgba(239,68,68,0.12)',
  high:     'rgba(249,115,22,0.12)',
  medium:   'rgba(245,158,11,0.12)',
  low:      'rgba(16,185,129,0.12)',
} as const

export const RISK_LABELS = {
  critical: 'CRITICAL',
  high:     'HIGH RISK',
  medium:   'CAUTION',
  low:      'LOW RISK',
} as const

export type RiskLevel = keyof typeof RISK_COLORS

export const getRiskLevel = (score: number): RiskLevel => {
  if (score >= 76) return 'critical'
  if (score >= 51) return 'high'
  if (score >= 26) return 'medium'
  return 'low'
}
