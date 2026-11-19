import type { CSSProperties } from 'react'
import { Accent, Badge, Button, ButtonGroup, Eyebrow, PageTitle, Panel } from '../ui'
import { artStyle, type ArtStyleId } from '../../data/artStyles'
import { heroClass, type Hero } from '../../data/heroes'
import HeroSprite from './HeroSprite'
import styles from './party.module.css'

export type SaveState = 'saving' | 'saved' | 'failed'

type Props = {
  title: string
  style: ArtStyleId
  party: Hero[]
  saveState: SaveState
  onRetrySave: () => void
  onChangeParty: () => void
  onChangeStyle: () => void
}

const SAVE_MESSAGE: Record<SaveState, string> = {
  saving: 'Saving the party...',
  saved: 'Party saved',
  failed: 'Could not save the party. Is the backend running?',
}

/** Last step: the whole party lined up, ready to set off. */
export default function ReadyStage({ title, style, party, saveState, onRetrySave, onChangeParty, onChangeStyle }: Props) {
  return (
    <Panel className={styles.ready}>
      <Eyebrow>The party is ready</Eyebrow>
      <PageTitle className={styles.readyTitle}>
        <Accent>{title}</Accent>
      </PageTitle>
      <p className={styles.readyStyle}>Style: {artStyle(style).name}</p>
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
      <p className={styles.saveNote} role="status">
        {SAVE_MESSAGE[saveState]}
      </p>
      <ButtonGroup className={styles.readyActions}>
        <Button onClick={onChangeParty}>Change the party</Button>
        <Button onClick={onChangeStyle}>Change the style</Button>
        {saveState === 'failed' && <Button onClick={onRetrySave}>Try again</Button>}
        <Button variant="primary" disabled>
          Begin the adventure <Badge>soon</Badge>
        </Button>
      </ButtonGroup>
    </Panel>
  )
}
