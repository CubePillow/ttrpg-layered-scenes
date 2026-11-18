import type { HTMLAttributes } from 'react'
import { cx } from './cx'
import styles from './Panel.module.css'

type Props = HTMLAttributes<HTMLElement> & {
  as?: 'div' | 'li' | 'section' | 'article' | 'aside'
  /** glass: see-through, for use over a scene. solid: for use on the page background. */
  tone?: 'glass' | 'solid'
}

/** Pixel frame around any content. */
export default function Panel({ as: Tag = 'div', tone = 'glass', className, ...rest }: Props) {
  return <Tag className={cx(styles.panel, styles[tone], className)} {...rest} />
}
