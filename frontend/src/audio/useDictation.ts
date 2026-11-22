import { useEffect, useRef, useState } from 'react'

/** The parts of the browser's speech recognition this uses (Chrome and Edge have it; Firefox does not). */
type Recognition = {
  lang: string
  continuous: boolean
  interimResults: boolean
  start: () => void
  stop: () => void
  onresult: ((event: { resultIndex: number; results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }> }) => void) | null
  onend: (() => void) | null
  onerror: ((event: { error: string }) => void) | null
}

type RecognitionClass = new () => Recognition

const Speech = (window as unknown as { SpeechRecognition?: RecognitionClass; webkitSpeechRecognition?: RecognitionClass })
const RecognitionImpl = Speech.SpeechRecognition ?? Speech.webkitSpeechRecognition

export const canDictate = RecognitionImpl !== undefined

/**
 * Voice input. While listening, each finished phrase goes to `onPhrase`; `heard` is the phrase still being spoken.
 * The browser sends the audio to its own speech service to turn it into text.
 */
export function useDictation(onPhrase: (text: string) => void, lang = navigator.language || 'en-US') {
  const [listening, setListening] = useState(false)
  const [heard, setHeard] = useState('')
  const [error, setError] = useState<string | null>(null)
  const recognition = useRef<Recognition | null>(null)
  const latest = useRef(onPhrase)

  useEffect(() => {
    latest.current = onPhrase
  })

  useEffect(() => () => recognition.current?.stop(), [])

  const start = () => {
    if (!RecognitionImpl || recognition.current) return
    const r = new RecognitionImpl()
    r.lang = lang
    r.continuous = true
    r.interimResults = true
    r.onresult = (event) => {
      let pending = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        if (result.isFinal) latest.current(result[0].transcript.trim())
        else pending += result[0].transcript
      }
      setHeard(pending)
    }
    r.onerror = (event) => setError(event.error === 'not-allowed' ? 'Microphone access was blocked' : 'Voice input stopped')
    r.onend = () => {
      recognition.current = null
      setListening(false)
      setHeard('')
    }
    recognition.current = r
    setError(null)
    setListening(true)
    r.start()
  }

  const stop = () => recognition.current?.stop()

  return { listening, heard, error, start, stop }
}
