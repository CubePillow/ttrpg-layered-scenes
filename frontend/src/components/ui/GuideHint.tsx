import type { ReactNode } from 'react'
import { cx } from './cx'
import styles from './GuideHint.module.css'

/**
 * One short hint on the shared screen that tells the players what to do now (issue #15).
 * It is announced to screen readers when it changes, and fades in again for every new hint.
 */
export default function GuideHint({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <p className={cx(styles.hint, className)} role="status">
      <span className={styles.icon} aria-hidden="true">
        📜
      </span>
      {/* The key restarts the fade-in whenever the hint changes */}
      <span key={String(children)} className={styles.text}>
        {children}
      </span>
    </p>
  )
}
