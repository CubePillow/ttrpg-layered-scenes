import { useMemo } from 'react'
import { PixelSprite } from '../ui'
import { heroPixels } from '../../data/heroes'

type Props = {
  classId: string
  color: string
  scale?: number
  label: string
  className?: string
}

/** Part of the hero's height, from the top, that shows the head and hat. */
const HEAD_SHARE = 0.45

/** Only the head of a hero sprite, cut out and centred in a square. */
function headPixels(pixels: (string | null)[][]) {
  const filled = pixels.map((row) => row.some(Boolean))
  const top = filled.indexOf(true)
  if (top < 0) return pixels
  const bottom = filled.lastIndexOf(true)
  const rows = pixels.slice(top, top + Math.max(1, Math.round((bottom - top + 1) * HEAD_SHARE)))
  const columns = rows.flatMap((row) => row.flatMap((color, x) => (color ? [x] : [])))
  const left = Math.min(...columns)
  const right = Math.max(...columns)
  const width = right - left + 1
  const side = Math.max(width, rows.length)
  const padLeft = Math.floor((side - width) / 2)
  const padTop = side - rows.length // Keep the head at the bottom of the square, like a bust
  const empty = () => Array<string | null>(side).fill(null)
  return [
    ...Array.from({ length: padTop }, empty),
    ...rows.map((row) => {
      const line = empty()
      row.slice(left, right + 1).forEach((color, x) => (line[padLeft + x] = color))
      return line
    }),
  ]
}

export default function HeroPortrait({ classId, color, scale, label, className }: Props) {
  const pixels = useMemo(() => headPixels(heroPixels(classId, color)), [classId, color])
  return <PixelSprite pixels={pixels} scale={scale} label={label} className={className} />
}
