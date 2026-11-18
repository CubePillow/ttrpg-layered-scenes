import { useId } from 'react'
import styles from './SwatchPicker.module.css'

type Option = { value: string; label: string; disabled?: boolean }

type Props = {
  label: string
  options: Option[]
  value: string
  onChange: (value: string) => void
}

/** Choose one colour. Works with the arrow keys. */
export default function SwatchPicker({ label, options, value, onChange }: Props) {
  const name = useId()
  return (
    <fieldset className={styles.picker}>
      <legend className={styles.legend}>{label}</legend>
      <div className={styles.swatches}>
        {options.map((option) => (
          <label key={option.value} className={styles.swatch} style={{ backgroundColor: option.value }} title={option.label}>
            <input
              type="radio"
              name={name}
              aria-label={option.label}
              checked={value === option.value}
              disabled={option.disabled}
              onChange={() => onChange(option.value)}
            />
          </label>
        ))}
      </div>
    </fieldset>
  )
}
