import type { FormEvent } from 'react'
import { Accent, Button, ButtonGroup, Lede, PageTitle, Panel, TextInput } from '../ui'
import { HERO_COLORS, HERO_CLASSES, randomTitle } from '../../data/heroes'
import HeroSprite from './HeroSprite'
import styles from './party.module.css'

type Props = {
  title: string
  onTitleChange: (title: string) => void
  onNext: () => void
  onBack: () => void
}

/** Name the campaign. */
export default function CampaignStage({ title, onTitleChange, onNext, onBack }: Props) {
  const ready = title.trim().length > 0

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (ready) onNext()
  }

  return (
    <Panel className={styles.campaign}>
      <div className={styles.parade} aria-hidden="true">
        {HERO_CLASSES.slice(0, 5).map((heroClass, i) => (
          <HeroSprite
            key={heroClass.id}
            classId={heroClass.id}
            color={HERO_COLORS[i + 1].value}
            scale={3}
            label=""
            className={styles.idle}
          />
        ))}
      </div>
      <PageTitle>
        A new tale <Accent>begins.</Accent>
      </PageTitle>
      <Lede className={styles.lede}>Every legend needs a name. What will the bards call yours?</Lede>
      <form onSubmit={submit} className={styles.campaignForm}>
        <TextInput
          label="Title of the game"
          placeholder="The Shattered Crown"
          maxLength={40}
          value={title}
          onChange={(event) => onTitleChange(event.target.value)}
          action={<Button onClick={() => onTitleChange(randomTitle())}>Random</Button>}
        />
        <ButtonGroup>
          <Button onClick={onBack}>Back</Button>
          <Button variant="primary" type="submit" disabled={!ready}>
            Continue
          </Button>
        </ButtonGroup>
      </form>
    </Panel>
  )
}
