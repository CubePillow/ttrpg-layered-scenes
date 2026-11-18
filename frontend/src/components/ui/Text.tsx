import type { HTMLAttributes } from 'react'
import { cx } from './cx'
import styles from './Text.module.css'

type ParagraphProps = HTMLAttributes<HTMLParagraphElement>
type HeadingProps = HTMLAttributes<HTMLHeadingElement>

/** Small line above a title. */
export function Eyebrow({ className, ...rest }: ParagraphProps) {
  return <p className={cx(styles.eyebrow, className)} {...rest} />
}

/** The one main title of a page. */
export function PageTitle({ className, ...rest }: HeadingProps) {
  return <h1 className={cx(styles.pageTitle, className)} {...rest} />
}

export function SectionTitle({ className, ...rest }: HeadingProps) {
  return <h2 className={cx(styles.sectionTitle, className)} {...rest} />
}

/** Short introduction under a title. */
export function Lede({ className, ...rest }: ParagraphProps) {
  return <p className={cx(styles.lede, className)} {...rest} />
}

/** Highlighted words inside a title or sentence. */
export function Accent({ className, ...rest }: HTMLAttributes<HTMLSpanElement>) {
  return <span className={cx(styles.accent, className)} {...rest} />
}
