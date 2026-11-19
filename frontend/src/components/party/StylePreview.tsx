import cartoon from '../../assets/styles/cartoon.jpg'
import comic from '../../assets/styles/comic.jpg'
import paperCutout from '../../assets/styles/paper_cutout.jpg'
import pixel from '../../assets/styles/pixel.png'
import type { ArtStyle, ArtStyleId } from '../../data/artStyles'
import { cx } from '../ui/cx'
import styles from './party.module.css'

/** The same campfire in each style: one generated scene, used as it is, pixelated with code or repainted with a LoRA. */
const PICTURES: Record<ArtStyleId, string> = { pixel, cartoon, paper_cutout: paperCutout, comic }

export default function StylePreview({ style }: { style: ArtStyle }) {
  return (
    <img
      src={PICTURES[style.id]}
      alt=""
      width={512}
      height={512}
      className={cx(styles.stylePreview, style.id === 'pixel' && styles.stylePixel)}
    />
  )
}
