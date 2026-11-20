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

export default function HeroSprite({ classId, color, scale, label, className }: Props) {
  const pixels = useMemo(() => heroPixels(classId, color), [classId, color])
  return <PixelSprite pixels={pixels} scale={scale} label={label} className={className} />
}
