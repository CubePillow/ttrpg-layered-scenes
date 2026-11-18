import type { HTMLAttributes } from 'react'
import { cx } from './cx'
import styles from './SiteFooter.module.css'

export default function SiteFooter({ className, ...rest }: HTMLAttributes<HTMLElement>) {
  return <footer className={cx(styles.footer, className)} {...rest} />
}
