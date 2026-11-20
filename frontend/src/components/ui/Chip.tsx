import type { ButtonHTMLAttributes } from 'react'
import { cx } from './cx'
import styles from './Chip.module.css'

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { selected?: boolean }

/** Small toggle button. */
export default function Chip({ selected = false, className, type = 'button', ...rest }: Props) {
  return <button type={type} aria-pressed={selected} className={cx(styles.chip, selected && styles.selected, className)} {...rest} />
}
