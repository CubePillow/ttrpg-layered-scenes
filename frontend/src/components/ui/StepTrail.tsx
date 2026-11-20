import { cx } from './cx'
import styles from './StepTrail.module.css'

type Props = {
  steps: string[]
  /** Index of the current step */
  current: number
}

/** Shows how far along a multi-step flow the player is. */
export default function StepTrail({ steps, current }: Props) {
  return (
    <ol className={styles.trail}>
      {steps.map((step, i) => (
        <li
          key={step}
          className={cx(styles.step, i < current && styles.done, i === current && styles.current)}
          aria-current={i === current ? 'step' : undefined}
        >
          <span className={styles.marker} aria-hidden="true" />
          {step}
        </li>
      ))}
    </ol>
  )
}
