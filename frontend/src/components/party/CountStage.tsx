import { Accent, Button, PageTitle, Panel } from '../ui'
import { MAX_PARTY } from '../../data/heroes'
import styles from './party.module.css'

type Props = {
  onChoose: (count: number) => void
  onBack: () => void
}

/** Local mode: how many people are playing. */
export default function CountStage({ onChoose, onBack }: Props) {
  return (
    <Panel className={styles.count}>
      <PageTitle>
        How many <Accent>players?</Accent>
      </PageTitle>
      <div className={styles.countGrid}>
        {Array.from({ length: MAX_PARTY }, (_, i) => i + 1).map((count) => (
          <button
            key={count}
            type="button"
            className={styles.countTile}
            aria-label={`${count} ${count === 1 ? 'player' : 'players'}`}
            onClick={() => onChoose(count)}
          >
            {count}
          </button>
        ))}
      </div>
      <div className={styles.backRow}>
        <Button onClick={onBack}>Back</Button>
      </div>
    </Panel>
  )
}
