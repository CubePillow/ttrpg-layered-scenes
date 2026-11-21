import { useEffect, useRef } from 'react'
import styles from './VoiceMeter.module.css'

const BARS = 5

/** Little bars that move with the microphone's loudness while someone speaks. */
export default function VoiceMeter() {
  const bars = useRef<(HTMLSpanElement | null)[]>([])

  useEffect(() => {
    let stopped = false
    let frame = 0
    let stream: MediaStream | null = null
    let context: AudioContext | null = null

    navigator.mediaDevices
      ?.getUserMedia({ audio: true })
      .then((media) => {
        if (stopped) return media.getTracks().forEach((t) => t.stop())
        stream = media
        context = new AudioContext()
        const analyser = context.createAnalyser()
        analyser.fftSize = 256
        context.createMediaStreamSource(media).connect(analyser)
        const data = new Uint8Array(analyser.frequencyBinCount)
        const step = Math.floor(data.length / (BARS * 2)) // Voices sit in the lower half

        const draw = () => {
          analyser.getByteFrequencyData(data)
          bars.current.forEach((bar, i) => {
            if (!bar) return
            let sum = 0
            for (let j = i * step; j < (i + 1) * step; j++) sum += data[j]
            const level = Math.min(1, sum / step / 160)
            bar.style.transform = `scaleY(${0.15 + level * 0.85})`
          })
          frame = requestAnimationFrame(draw)
        }
        draw()
      })
      .catch(() => {}) // No meter then; speech recognition still reports its own errors

    return () => {
      stopped = true
      cancelAnimationFrame(frame)
      stream?.getTracks().forEach((t) => t.stop())
      context?.close()
    }
  }, [])

  return (
    <span className={styles.meter} aria-hidden="true">
      {Array.from({ length: BARS }, (_, i) => (
        <span key={i} ref={(el) => void (bars.current[i] = el)} className={styles.bar} />
      ))}
    </span>
  )
}
