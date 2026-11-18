import type { CSSProperties } from 'react'
import { Accent, Badge, Button, ButtonGroup, Eyebrow, PageTitle, Panel } from '../ui'
import { heroClass, type Hero } from '../../data/heroes'
import HeroSprite from './HeroSprite'
import styles from './party.module.css'

type Props = {
  title: string
  party: Hero[]
  onBack: () => void
}

/** Step 3: the whole party lined up, ready to set off. */
export default function ReadyStage({ title, party, onBack }: Props) {
  return (
    <Panel className={styles.ready}>
      <Eyebrow>The party is ready</Eyebrow>
      <PageTitle className={styles.readyTitle}>
        <Accent>{title}</Accent>
      </PageTitle>
      <ul className={styles.lineup}>
        {party.map((hero, i) => (
          <li key={hero.id} className={styles.lineupHero} style={{ '--delay': `${i * 120}ms` } as CSSProperties}>
            <HeroSprite classId={hero.classId} color={hero.color} scale={5} label={heroClass(hero).name} className={styles.hop} />
            <span className={styles.plate} style={{ background: hero.color }} />
            <span className={styles.lineupName}>{hero.name}</span>
            <span className={styles.lineupClass}>{heroClass(hero).name}</span>
          </li>
        ))}
      </ul>
      <ButtonGroup className={styles.readyActions}>
        <Button onClick={onBack}>Change the party</Button>
        <Button variant="primary" disabled>
          Begin the adventure <Badge>soon</Badge>
        </Button>
      </ButtonGroup>
    </Panel>
  )
}
