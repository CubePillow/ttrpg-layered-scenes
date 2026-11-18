import { useId, type InputHTMLAttributes, type ReactNode } from 'react'
import { cx } from './cx'
import styles from './TextInput.module.css'

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label: string
  /** Shown next to the input, for example a button */
  action?: ReactNode
}

/** One-line text input with a label. */
export default function TextInput({ label, action, className, ...rest }: Props) {
  const id = useId()
  return (
    <div className={cx(styles.field, className)}>
      <label htmlFor={id} className={styles.label}>
        {label}
      </label>
      <div className={styles.row}>
        <input id={id} type="text" autoComplete="off" className={styles.input} {...rest} />
        {action}
      </div>
    </div>
  )
}
