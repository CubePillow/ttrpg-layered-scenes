import type { HTMLAttributes } from 'react'
import { cx } from './cx'
import styles from './ButtonGroup.module.css'

/** A row of buttons that wraps on small screens. */
export default function ButtonGroup({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cx(styles.group, className)} {...rest} />
}
