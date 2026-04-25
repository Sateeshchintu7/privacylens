/**
 * useTranslation.ts
 * Translates display text into the user's selected language via /api/translate.
 * Results are cached in-memory so the same text+language is never translated twice.
 */
import { useState, useCallback, useRef } from 'react'
import { api } from '../api/client'

const _cache = new Map<string, string>()

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

      // Return from cache when all items are already translated
      const cacheKeys = texts.map(t => `${langRef.current}:${t}`)
      if (cacheKeys.every(k => _cache.has(k)))
        return cacheKeys.map(k => _cache.get(k)!)

      setTranslating(true)
      try {
        const res = await api.post('/api/translate', {
          texts,
          language: langRef.current,
        }, { timeout: 30_000 })

        const translated: string[] = res.data?.translated ?? texts

        // Cache each result
        texts.forEach((t, i) => {
          _cache.set(`${langRef.current}:${t}`, translated[i] ?? t)
        })

        return translated
      } catch {
        return texts
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
