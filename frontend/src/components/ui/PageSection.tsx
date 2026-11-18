import type { HTMLAttributes } from 'react'
import { cx } from './cx'
import { SectionTitle } from './Text'
import styles from './PageSection.module.css'

type Props = HTMLAttributes<HTMLElement> & { heading: string }

/** A titled block of a page with the standard width and spacing. */
export default function PageSection({ heading, className, children, ...rest }: Props) {
  return (
    <section className={cx(styles.section, className)} {...rest}>
      <SectionTitle className={styles.title}>{heading}</SectionTitle>
      {children}
    </section>
  )
}
