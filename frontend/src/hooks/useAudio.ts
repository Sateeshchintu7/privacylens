import { useState, useRef, useCallback } from 'react'
import { generateAudio } from '../api/client'

interface AudioState {
  isGenerating: boolean
  isPlaying: boolean
  audioUrl: string | null
  duration: number
  engineUsed: string
  error: string | null
}

export function useAudio() {
  const [audioState, setAudioState] = useState<AudioState>({
    isGenerating: false,
    isPlaying: false,
    audioUrl: null,
    duration: 0,
    engineUsed: '',
    error: null,
  })
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const generate = useCallback(async (
    text: string,
    language = 'en',
    audienceLevel = 'adult',
    engine = 'auto',
  ) => {
    setAudioState(s => ({ ...s, isGenerating: true, error: null, audioUrl: null }))
    try {
      const res = await generateAudio({ text, language, audience_level: audienceLevel, engine })
      const blob = b64toBlob(res.data.audio_base64, 'audio/mpeg')
      const url  = URL.createObjectURL(blob)
      setAudioState(s => ({
        ...s,
        isGenerating: false,
        audioUrl: url,
        duration: res.data.duration_seconds,
        engineUsed: res.data.engine_used,
      }))
      return url
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Audio generation failed'
      setAudioState(s => ({ ...s, isGenerating: false, error: msg }))
      return null
    }
  }, [])

  const downloadAudio = useCallback((filename = 'privacylens-audio.mp3') => {
    if (!audioState.audioUrl) return
    const a = document.createElement('a')
    a.href = audioState.audioUrl
    a.download = filename
    a.click()
  }, [audioState.audioUrl])

  return { audioState, audioRef, generate, downloadAudio }
}

function b64toBlob(b64: string, mimeType: string): Blob {
  const byteChars = atob(b64)
  const bytes = new Uint8Array(byteChars.length)
  for (let i = 0; i < byteChars.length; i++) bytes[i] = byteChars.charCodeAt(i)
  return new Blob([bytes], { type: mimeType })
}
