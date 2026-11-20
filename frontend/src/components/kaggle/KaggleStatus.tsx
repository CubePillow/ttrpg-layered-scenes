import { useEffect, useState } from 'react'
import { connectKaggle, getKaggleStatus, stopKaggle, type KaggleState } from '../../api/kaggle'
import styles from './KaggleStatus.module.css'

const POLL_MS = 3000
const cx = (...names: Array<string | false>) => names.filter(Boolean).join(' ')
const STEPS = [
  { stage: 'account', label: 'Account' },
  { stage: 'notebook', label: 'Notebook' },
  { stage: 'session', label: 'Loading models' },
  { stage: 'ready', label: 'Ready' },
]

const TITLES: Record<string, string> = {
  off: 'Kaggle: off',
  account: 'Kaggle: connecting',
  notebook: 'Kaggle: connecting',
  session: 'Kaggle: starting',
  ready: 'Kaggle: ready',
  stopping: 'Kaggle: stopping',
  failed: 'Kaggle: failed',
}

/** Shows how far the connection to the Kaggle GPU session has come, on every page. */
export default function KaggleStatus() {
  const [status, setStatus] = useState<KaggleState | null>(null)
  const [offline, setOffline] = useState(false)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    let active = true
    const load = () =>
      getKaggleStatus()
        .then((next) => {
          if (!active) return
          setStatus(next)
          setOffline(false)
        })
        .catch(() => {
          if (active) setOffline(true)
        })
    void load()
    const timer = window.setInterval(load, POLL_MS)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [])

  const act = (action: () => Promise<KaggleState>) => {
    action()
      .then(setStatus)
      .catch(() => setOffline(true))
  }

  const stage = offline ? 'offline' : (status?.stage ?? 'off')
  const current = STEPS.findIndex((step) => step.stage === stage)
  const connecting = current >= 0 && stage !== 'ready'
  const canConnect = !offline && (stage === 'off' || stage === 'failed')
  const canStop = !offline && (connecting || stage === 'ready')

  return (
    <aside className={styles.box} aria-label="Kaggle connection">
      <button type="button" className={styles.summary} aria-expanded={open} onClick={() => setOpen(!open)}>
        <span className={cx(styles.dot, styles[stage])} aria-hidden="true" />
        <span>{offline ? 'Backend offline' : TITLES[stage]}</span>
        {connecting && <span className={styles.percent}>{status?.progress}%</span>}
      </button>

      {connecting && (
        <div
          className={styles.track}
          role="progressbar"
          aria-label="Connection progress"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={status?.progress ?? 0}
        >
          <span className={styles.fill} style={{ width: `${status?.progress ?? 0}%` }} />
        </div>
      )}

      {open && (
        <div className={styles.details}>
          <ol className={styles.steps}>
            {STEPS.map((step, i) => (
              <li key={step.stage} className={cx(styles.step, i < current && styles.stepDone, i === current && styles.stepNow)}>
                {step.label}
              </li>
            ))}
          </ol>
          <p className={styles.message} role="status">
            {offline ? 'Start the backend to connect to Kaggle.' : status?.message}
          </p>
          {stage === 'session' && <p className={styles.note}>The progress is an estimate. Starting usually takes 5 to 12 minutes.</p>}
          {Boolean(status?.log.length) && <pre className={styles.log}>{status?.log.join('\n')}</pre>}
          <div className={styles.actions}>
            {canConnect && (
              <button type="button" className={cx(styles.action, styles.primary)} onClick={() => act(connectKaggle)}>
                Connect
              </button>
            )}
            {canStop && (
              <button type="button" className={styles.action} onClick={() => act(stopKaggle)}>
                Stop session
              </button>
            )}
          </div>
        </div>
      )}
    </aside>
  )
}
