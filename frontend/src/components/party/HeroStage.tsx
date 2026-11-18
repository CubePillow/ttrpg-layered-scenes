import { useEffect, useRef, useState, type FormEvent } from 'react'
import { isMusicMuted, playTheme, setMusicMuted, stopTheme } from '../../audio/chiptune'
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
  onDone: () => void
}

/** Players take turns: each one picks a hero and locks it in, then the next player is up. */
export default function HeroStage({ count, party, onPartyChange, onBack, onDone }: Props) {
  const [index, setIndex] = useState(() => (party.length >= count ? 0 : party.length))
  const [draft, setDraft] = useState<Hero>(() => (party.length >= count ? party[0] : newHero(party)))
  const [locking, setLocking] = useState(false)
  // A name the player typed or already locked in is kept when the class changes
  const [nameKept, setNameKept] = useState(() => party.length >= count)
  const timer = useRef<number | undefined>(undefined)

  const [muted, setMuted] = useState(isMusicMuted)

  useEffect(() => () => window.clearTimeout(timer.current), [])

  // Each class has its own music; it changes as soon as another hero is picked
  useEffect(() => {
    playTheme(HERO_THEMES[draft.classId])
  }, [draft.classId])

  useEffect(() => stopTheme, [])

  const chosen = heroClass(draft)
  const others = party.filter((_, i) => i !== index)
  const nameOk = draft.name.trim().length > 0
  const takenNames = others.map((hero) => hero.name)

  const toggleMusic = () => {
    setMusicMuted(!muted)
    setMuted(!muted)
  }

  const update = (change: Partial<Hero>) => setDraft((hero) => ({ ...hero, ...change }))

  const chooseClass = (classId: string) => {
    update(nameKept ? { classId } : { classId, name: randomName(classId, takenNames) })
  }

  const goTo = (next: number, heroes: Hero[]) => {
    setIndex(next)
    setDraft(heroes[next] ?? newHero(heroes))
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
      if (index + 1 < count) goTo(index + 1, heroes)
      else onDone()
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
          <div className={styles.music}>
            <span className={styles.musicTitle}>{muted ? 'Music off' : `Now playing: ${HERO_THEMES[draft.classId].title}`}</span>
            <Button aria-pressed={!muted} onClick={toggleMusic}>
              {muted ? 'Music on' : 'Mute'}
            </Button>
          </div>
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
                    disabled={locking || !party[i]}
                    aria-label={party[i] ? `Change ${party[i].name}` : `Player ${i + 1}`}
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
