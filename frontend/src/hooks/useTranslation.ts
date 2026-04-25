/**
 * useTranslation.ts
 * Translates display text into the user's selected language via /api/translate.
 * Results are cached in sessionStorage so the same text+language is never translated twice across reloads.
 */
import { useState, useCallback, useRef } from 'react'
import { api } from '../api/client'

const CACHE_PREFIX = 'pl_trans_'

const ENGLISH_CODES = new Set(['en', 'en-gb', 'en-us', 'en-uk'])

export function useTranslation(language: string) {
  const [translating, setTranslating] = useState(false)
  const langRef = useRef(language)
  langRef.current = language

  const isEnglish = ENGLISH_CODES.has(language.toLowerCase())

  const translateBatch = useCallback(
    async (texts: string[]): Promise<string[]> => {
      if (ENGLISH_CODES.has(langRef.current.toLowerCase()) || texts.length === 0)
        return texts

      // Check sessionStorage cache
      const results: string[] = []
      const missingIdxs: number[] = []
      const missingTexts: string[] = []

      for (let i = 0; i < texts.length; i++) {
        const t = texts[i]
        const key = `${CACHE_PREFIX}${langRef.current}:${t}`
        const cached = sessionStorage.getItem(key)
        if (cached) {
          results[i] = cached
        } else {
          missingIdxs.push(i)
          missingTexts.push(t)
        }
      }

      if (missingTexts.length === 0) {
        return results
      }

      setTranslating(true)
      try {
        const res = await api.post('/api/translate', {
          texts: missingTexts,
          language: langRef.current,
        }, { timeout: 30_000 })

        const translated: string[] = res.data?.translated ?? missingTexts

        // Save to cache and merge into results
        missingTexts.forEach((t, i) => {
          const val = translated[i] ?? t
          sessionStorage.setItem(`${CACHE_PREFIX}${langRef.current}:${t}`, val)
          results[missingIdxs[i]] = val
        })

        return results
      } catch {
        missingTexts.forEach((t, i) => {
          results[missingIdxs[i]] = t
        })
        return results
      } finally {
        setTranslating(false)
      }
    },
    [] // stable — reads langRef dynamically
  )

  const translateOne = useCallback(
    async (text: string): Promise<string> => {
      if (!text) return text
      const results = await translateBatch([text])
      return results[0]
    },
    [translateBatch]
  )

  return { translateBatch, translateOne, translating, isEnglish }
}
