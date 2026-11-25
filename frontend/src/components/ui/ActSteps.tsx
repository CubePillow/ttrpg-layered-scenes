import styles from './ActSteps.module.css'
import StepTrail from './StepTrail'

const STEPS = ['Write', 'Draw', 'Layers']

/** Where the act is: written, drawn, or being arranged in layers. Sits beside the page's buttons, on one line. */
export default function ActSteps({ current }: { current: 0 | 1 | 2 }) {
  return (
    <div className={styles.steps}>
      <StepTrail steps={STEPS} current={current} />
    </div>
  )
}
