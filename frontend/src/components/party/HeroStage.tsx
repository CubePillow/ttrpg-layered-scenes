import { useEffect, useRef, useState, type FormEvent } from 'react'
import { playTheme } from '../../audio/chiptune'
import { HERO_THEMES } from '../../audio/heroThemes'
import { Button, ButtonGroup, Panel, SectionTitle, SwatchPicker, TextInput } from '../ui'
import { cx } from '../ui/cx'
import { HERO_CLASSES, HERO_COLORS, heroClass, newHero, randomName, type Hero } from '../../data/heroes'
import HeroSprite from './HeroSprite'
import styles from './party.module.css'

const LOCK_MS = 700

type Props = {
  count: number
  party: Hero[]
  onPartyChange: (party: Hero[]) => void
  onBack: () => void
  onDone: (heroes: Hero[]) => void
}

/** The first player who has no hero yet, or -1 when everyone has one. Players can lock in out of order. */
const firstOpen = (party: (Hero | undefined)[], count: number) =>
  Array.from({ length: count }, (_, i) => i).find((i) => !party[i]) ?? -1

/** Each player picks a hero and locks it in. Click any player in the tray to choose or change that player's hero. */
export default function HeroStage({ count, party, onPartyChange, onBack, onDone }: Props) {
  const [index, setIndex] = useState(() => Math.max(0, firstOpen(party, count)))
  const [draft, setDraft] = useState<Hero>(() => party[index] ?? newHero(party.filter(Boolean)))
  const [locking, setLocking] = useState(false)
  // A name the player typed or already locked in is kept when the class changes
  const [nameKept, setNameKept] = useState(() => Boolean(party[index]))
  const timer = useRef<number | undefined>(undefined)

  useEffect(() => () => window.clearTimeout(timer.current), [])

  // Each class has its own music; it changes as soon as another hero is picked
  useEffect(() => {
    playTheme(HERO_THEMES[draft.classId])
  }, [draft.classId])

  const chosen = heroClass(draft)
  const others = party.filter((hero, i) => hero && i !== index)
  const nameOk = draft.name.trim().length > 0
  const takenNames = others.map((hero) => hero.name)

  const update = (change: Partial<Hero>) => setDraft((hero) => ({ ...hero, ...change }))

  const chooseClass = (classId: string) => {
    update(nameKept ? { classId } : { classId, name: randomName(classId, takenNames) })
  }

  const goTo = (next: number, heroes: Hero[]) => {
    setIndex(next)
    setDraft(heroes[next] ?? newHero(heroes.filter((hero, i) => hero && i !== next)))
    setNameKept(Boolean(heroes[next]))
  }

  const lockIn = (event: FormEvent) => {
    event.preventDefault()
    if (!nameOk || locking) return
    const heroes = [...party]
    heroes[index] = { ...draft, name: draft.name.trim() }
    onPartyChange(heroes)

    const finish = () => {
      setLocking(false)
      const next = firstOpen(heroes, count)
      if (next >= 0) goTo(next, heroes)
      else onDone(heroes)
    }
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      finish()
      return
    }
    setLocking(true)
    timer.current = window.setTimeout(finish, LOCK_MS)
  }

  return (
    <Panel className={styles.forge}>
      <form onSubmit={lockIn}>
        <header className={styles.forgeHeader}>
          <p className={styles.playerTag} style={{ color: draft.color }}>
            Player {index + 1} of {count}
          </p>
          <SectionTitle>Choose your hero</SectionTitle>
          <p className={styles.musicTitle}>Theme: {HERO_THEMES[draft.classId].title}</p>
        </header>

        <div className={styles.forgeGrid}>
          <fieldset className={styles.roster} disabled={locking}>
            <legend className={styles.visuallyHidden}>Hero class</legend>
            {HERO_CLASSES.map((option) => (
              <label key={option.id} className={cx(styles.rosterCard, draft.classId === option.id && styles.rosterOn)}>
                <input
                  type="radio"
                  name="hero-class"
                  checked={draft.classId === option.id}
                  onChange={() => chooseClass(option.id)}
                />
                <HeroSprite classId={option.id} color={draft.color} scale={2} label="" />
                <span>{option.name}</span>
              </label>
            ))}
          </fieldset>

          <div className={styles.preview}>
            <div className={styles.previewStage}>
              <div key={`${index}-${draft.classId}`} className={styles.previewHero}>
                <HeroSprite
                  classId={draft.classId}
                  color={draft.color}
                  scale={8}
                  label={`${draft.name}, ${chosen.name}`}
                  className={locking ? styles.lockedHero : styles.idle}
                />
              </div>
              {locking && (
                <p className={styles.stamp} role="status">
                  Locked in!
                </p>
              )}
            </div>
            <div className={styles.pedestal} style={{ background: draft.color }} />
            <p className={styles.heroName}>{draft.name || '???'}</p>
            <p className={styles.heroClass}>
              {chosen.name} · {chosen.role}
            </p>
            <p className={styles.motto}>“{chosen.motto}”</p>
          </div>

          <div className={styles.sheet}>
            <TextInput
              label="Hero name"
              maxLength={18}
              value={draft.name}
              disabled={locking}
              onChange={(event) => {
                setNameKept(true)
                update({ name: event.target.value })
              }}
              action={
                <Button
                  disabled={locking}
                  onClick={() => {
                    setNameKept(false)
                    update({ name: randomName(draft.classId, takenNames) })
                  }}
                >
                  Random
                </Button>
              }
            />
            <SwatchPicker
              label="Colour"
              value={draft.color}
              onChange={(color) => update({ color })}
              options={HERO_COLORS.map((color) => ({ ...color, disabled: others.some((hero) => hero.color === color.value) }))}
            />
          </div>
        </div>

        <div className={styles.tray}>
          <ul className={styles.slots} aria-label="Party">
            {Array.from({ length: count }, (_, i) => {
              const hero = i === index ? draft : party[i]
              return (
                <li key={i}>
                  <button
                    type="button"
                    className={cx(styles.slot, party[i] && styles.slotLocked, i === index && styles.slotOn)}
                    disabled={locking}
                    aria-label={party[i] ? `Change ${party[i].name}` : `Choose a hero for player ${i + 1}`}
                    aria-current={i === index ? 'true' : undefined}
                    onClick={() => goTo(i, party)}
                  >
                    {hero ? (
                      <>
                        <HeroSprite classId={hero.classId} color={hero.color} scale={2} label="" />
                        <span className={styles.slotName}>P{i + 1}</span>
                      </>
                    ) : (
                      <span className={styles.slotEmpty}>P{i + 1}</span>
                    )}
                  </button>
                </li>
              )
            })}
          </ul>
          <ButtonGroup className={styles.trayActions}>
            <Button disabled={locking} onClick={() => (index > 0 ? goTo(index - 1, party) : onBack())}>
              Back
            </Button>
            <Button variant="primary" type="submit" disabled={!nameOk || locking}>
              Lock in
            </Button>
          </ButtonGroup>
        </div>
      </form>
    </Panel>
  )
}
