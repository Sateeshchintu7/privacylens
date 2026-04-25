import axios from 'axios'
import type {
  AnalyseRequest, AnalyseResponse,
  KidsResponse, AudioResponse, AskResponse,
  CompareResponse, HealthResponse,
} from '../types'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://16.170.254.195',
  timeout: 180_000, // 3 min — LLM calls can be slow
})

api.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', {
      url: error.config?.url,
      status: error.response?.status,
      data: error.response?.data,
      message: error.message,
      code: error.code,
    })
    return Promise.reject(error)
  },
)

// Background job API — POST returns {job_id} instantly, GET polls for result
export const startAnalysis = (data: AnalyseRequest) =>
  api.post<{ job_id: string; cached: boolean }>('/api/analyse', data, { timeout: 30_000 })

export const getAnalysisStatus = (jobId: string) =>
  api.get<{
    status: 'running' | 'complete' | 'error'
    result: AnalyseResponse | null
    error: string | null
  }>(`/api/analyse/status/${jobId}`)

// Kept for backward compat
export const analysePolicy = (data: AnalyseRequest) =>
  api.post<AnalyseResponse>('/api/analyse', data)

// Kids Mode — background job pattern (POST returns {job_id}, GET polls for result)
export const startKidsAnalysis = (data: {
  plain_clauses: object[]
  risk_report: object
  age_group: string
}) => api.post<{ job_id: string }>('/api/kids', data, { timeout: 15_000 })

export const getKidsStatus = (jobId: string) =>
  api.get<{
    status: 'running' | 'complete' | 'error'
    result: KidsResponse | null
    error: string | null
  }>(`/api/kids/status/${jobId}`)

export const generateAudio = (data: {
  text: string
  language: string
  audience_level: string
  engine: string
}) => api.post<AudioResponse>('/api/audio', data)

export const askQuestion = (data: {
  question: string
  clauses: object[]
  policy_text: string
  audience_level: string
  compliance_report?: object
}) => api.post<AskResponse>('/api/ask', data)

// Report — single-shot comprehensive analysis
export const startReport = (data: {
  content: string
  input_type: string
  language: string
}) => api.post<{ job_id: string; cached: boolean }>('/api/analyse/report', data, { timeout: 15_000 })

export const getReportStatus = (jobId: string) =>
  api.get<{
    status: 'running' | 'complete' | 'error'
    result: Record<string, unknown> | null
    error: string | null
  }>(`/api/analyse/report/status/${jobId}`)

export const comparePolicies = (data: {
  old_content: string
  new_content: string
  policy_name: string
  old_date?: string
  new_date?: string
}) => api.post<CompareResponse>('/api/compare', data)

export const detectContradictions = (data: { clauses: object[] }) =>
  api.post<import('../types').ContradictionReport>('/api/contradictions', data)

export const checkHealth = () => api.get<HealthResponse>('/health')
