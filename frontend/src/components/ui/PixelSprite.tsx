import { useEffect, useRef } from 'react'

type Props = {
  /** Rows of colours; null is transparent */
  pixels: (string | null)[][]
  /** Screen pixels per sprite pixel */
  scale?: number
  label: string
  className?: string
}

/** Draws a small picture from a grid of colours, scaled up with crisp pixels. */
export default function PixelSprite({ pixels, scale = 4, label, className }: Props) {
  const ref = useRef<HTMLCanvasElement>(null)
  const height = pixels.length
  const width = pixels[0]?.length ?? 0

  useEffect(() => {
    const context = ref.current?.getContext('2d')
    if (!context) return
    context.clearRect(0, 0, width, height)
    pixels.forEach((row, y) =>
      row.forEach((color, x) => {
        if (!color) return
        context.fillStyle = color
        context.fillRect(x, y, 1, 1)
      }),
    )
  }, [pixels, width, height])

  return (
    <canvas
      ref={ref}
      width={width}
      height={height}
      role="img"
      aria-label={label}
      className={className}
      style={{ width: width * scale, height: height * scale, imageRendering: 'pixelated' }}
    />
  )
}
