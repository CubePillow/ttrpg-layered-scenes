import { Accent, Badge, Button, PageTitle, Panel } from '../ui'
import { HERO_COLORS } from '../../data/heroes'
import HeroSprite from './HeroSprite'
import styles from './party.module.css'

type Props = {
  onLocal: () => void
}

/** First screen after Start a scene: play on one screen or online. */
export default function ModeStage({ onLocal }: Props) {
  return (
    <Panel className={styles.mode}>
      <PageTitle>
        Choose your <Accent>mode</Accent>
      </PageTitle>
      <div className={styles.modeGrid}>
        <button type="button" className={styles.modeCard} onClick={onLocal}>
          <span className={styles.modeArt} aria-hidden="true">
            <HeroSprite classId="fighter" color={HERO_COLORS[0].value} scale={3} label="" className={styles.idle} />
            <HeroSprite classId="wizard" color={HERO_COLORS[5].value} scale={3} label="" className={styles.idle} />
          </span>
          <span className={styles.modeName}>Local</span>
          <span>Everyone at one screen</span>
        </button>
        <button type="button" className={styles.modeCard} disabled>
          <span className={styles.modeArt} aria-hidden="true">
            <HeroSprite classId="rogue" color={HERO_COLORS[6].value} scale={3} label="" />
            <HeroSprite classId="bard" color={HERO_COLORS[4].value} scale={3} label="" />
          </span>
          <span className={styles.modeName}>
            Online <Badge>soon</Badge>
          </span>
          <span>Play together from anywhere</span>
        </button>
      </div>
      <div className={styles.backRow}>
        <Button href="/">Back</Button>
      </div>
    </Panel>
  )
}
