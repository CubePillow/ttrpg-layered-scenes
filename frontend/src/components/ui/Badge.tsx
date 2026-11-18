import type { HTMLAttributes } from 'react'
import { cx } from './cx'
import styles from './Badge.module.css'

/** Small label, for example "soon" inside a button. */
export default function Badge({ className, ...rest }: HTMLAttributes<HTMLSpanElement>) {
  return <span className={cx(styles.badge, className)} {...rest} />
}
