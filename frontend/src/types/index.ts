// PrivacyLens TypeScript types — mirrors api/schemas.py

export interface AnalyseRequest {
  input_type: 'url' | 'text' | 'pdf_base64'
  content: string
  audience_level: 'adult' | 'teen' | 'child'
  language: string
}

export interface ClauseResult {
  category: string
  category_label: string
  text: string
  char_count: number
  word_count: number
}

export interface ClauseRisk {
  category: string
  category_label: string
  risk_level: 'low' | 'medium' | 'high' | 'critical'
  final_score: number
  red_flags: string[]
  positive_signals: string[]
  explanation: string
}

export interface PolicyRiskReport {
  grade: string
  overall_score: number
  grade_explanation: string
  clause_risks: ClauseRisk[]
  top_red_flags: string[]
  positive_signals: string[]
}

export interface PlainClause {
  category: string
  category_label: string
  plain_summary: string
  what_it_means: string
  emoji: string
  reading_grade: number
  grade_target: number
  grade_met: boolean
}

export interface ReadabilityReport {
  flesch_kincaid_grade: number
  flesch_reading_ease: number
  avg_sentence_length: number
  comparison_label: string
  minutes_to_read?: number
}

export interface ComplianceGap {
  regulation: string
  article: string
  requirement: string
  status: string
  severity: string
  evidence: string
}

export interface ComplianceReport {
  gdpr_score: number
  ccpa_score: number
  dpdp_score: number
  eu_ai_act_score: number
  overall_score: number
  gaps: ComplianceGap[]
  critical_gaps: ComplianceGap[]
  radar_scores: Record<string, number>
  eu_ai_act_gaps: ComplianceGap[]
}

export interface Contradiction {
  contradiction_id: string
  clause_a_category: string
  clause_b_category: string
  clause_a_text: string
  clause_b_text: string
  contradiction_type: string
  severity: string
  plain_explanation: string
  example: string
}

export interface ContradictionReport {
  total_found: number
  contradictions: Contradiction[]
  has_critical: boolean
  summary: string
  candidates_screened: number
  llm_calls_made: number
}

export interface DarkPattern {
  category: string
  label: string
  severity: 'low' | 'medium' | 'high'
  description: string
  evidence: string
}

export interface DarkPatternReport {
  total_found: number
  patterns: DarkPattern[]
  has_high: boolean
  categories_found: string[]
  summary: string
}

export interface AnalyseResponse {
  policy_name: string
  policy_text?: string
  char_count: number
  clauses: ClauseResult[]
  risk_report: PolicyRiskReport
  plain_clauses: PlainClause[]
  readability: ReadabilityReport
  compliance: ComplianceReport
  contradictions: ContradictionReport
  dark_patterns: DarkPatternReport
  processing_ms: number
}

// Kids Mode
export interface KidsClause {
  category: string
  category_label: string
  kids_summary: string
  one_liner: string
  emoji: string
  risk_level: string
  concern_level: string
}

export interface KidsReport {
  age_group: string
  verdict: string
  verdict_emoji: string
  verdict_reason: string
  emoji_summary: string[]
  concerns: string[]
  positives: string[]
  clauses: KidsClause[]
}

export interface KidsResponse {
  report: KidsReport
}

// Audio
export interface AudioResponse {
  audio_base64: string
  duration_seconds: number
  engine_used: string
}

// Ask / RAG
export interface AskResponse {
  answer: string
  plain_answer: string
  source_quote: string
  confidence: number
  could_not_find: boolean
}

// Compare
export interface ClauseChange {
  category: string
  change_type: string
  old_text: string
  new_text: string
  risk_delta: number
  plain_summary: string
  severity: string
}

export interface PolicyDiff {
  policy_name: string
  old_date: string
  new_date: string
  total_changes: number
  worsened: ClauseChange[]
  improved: ClauseChange[]
  added: ClauseChange[]
  removed: ClauseChange[]
  unchanged_count: number
  overall_risk_delta: number
  plain_summary: string
  verdict: string
  verdict_emoji: string
}

export interface CompareResponse {
  diff: PolicyDiff
}

// Health
export interface HealthResponse {
  status: string
  gemini: boolean
  elevenlabs: boolean
  version: string
}

// Analysis state
export type AnalysisStatus = 'idle' | 'loading' | 'success' | 'error'

export interface AnalysisState {
  status: AnalysisStatus
  currentStep: string
  progress: number
  data: AnalyseResponse | null
  kidsData: KidsResponse | null
  error: string | null
  policyText: string
  blocked403: boolean
}
