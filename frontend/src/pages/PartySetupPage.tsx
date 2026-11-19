import { useEffect, useRef, useState } from 'react'
import { saveGame } from '../api/games'
import { isMusicMuted, playTheme, setMusicMuted, stopTheme } from '../audio/chiptune'
import { AMBIENT_THEME } from '../audio/heroThemes'
import CampaignStage from '../components/party/CampaignStage'
import CountStage from '../components/party/CountStage'
import HeroStage from '../components/party/HeroStage'
import ModeStage from '../components/party/ModeStage'
import ReadyStage, { type SaveState } from '../components/party/ReadyStage'
import StyleStage from '../components/party/StyleStage'
import PixelScene from '../components/pixel-scene/PixelScene'
import { Button, StepTrail } from '../components/ui'
import { DEFAULT_ART_STYLE, type ArtStyleId } from '../data/artStyles'
import type { Hero } from '../data/heroes'
import styles from './PartySetupPage.module.css'

const STEPS = ['Mode', 'Title', 'Players', 'Heroes', 'Style', 'Set off']
const HERO_STEP = 3
const STYLE_STEP = 4
const READY_STEP = 5

export default function PartySetupPage() {
  const [step, setStep] = useState(0)
  const [title, setTitle] = useState('')
  const [count, setCount] = useState(1)
  const [party, setParty] = useState<Hero[]>([])
  const [style, setStyle] = useState<ArtStyleId>(DEFAULT_ART_STYLE)
  const [muted, setMuted] = useState(isMusicMuted)
  const [saveState, setSaveState] = useState<SaveState>('saving')
  const gameId = useRef<string | null>(null)
  const saves = useRef(Promise.resolve())

  // Quiet music throughout; while choosing a hero, that hero's theme plays instead
  useEffect(() => {
    if (step !== HERO_STEP) playTheme(AMBIENT_THEME)
  }, [step])

  useEffect(() => stopTheme, [])

  const toggleMusic = () => {
    setMusicMuted(!muted)
    setMuted(!muted)
  }

  /** Saves run one after another, so this game is only ever created once. */
  const save = (chosenStyle: ArtStyleId) => {
    setSaveState('saving')
    saves.current = saves.current.then(async () => {
      try {
        gameId.current = await saveGame(gameId.current, title.trim(), chosenStyle, party)
        setSaveState('saved')
      } catch {
        setSaveState('failed')
      }
    })
  }

  const finishParty = (heroes: Hero[]) => {
    setParty(heroes)
    setStep(STYLE_STEP)
  }

  const chooseStyle = (chosenStyle: ArtStyleId) => {
    setStyle(chosenStyle)
    setStep(READY_STEP)
    save(chosenStyle)
  }

  const chooseCount = (players: number) => {
    setCount(players)
    setParty((heroes) => heroes.slice(0, players))
    setStep(HERO_STEP)
  }

  return (
    <div className={styles.page}>
      <PixelScene highlight={null} className={styles.scene} />
      <div className={styles.shade} />
      <main className={styles.content}>
        <div className={styles.topBar}>
          <StepTrail steps={STEPS} current={step} />
          <Button aria-pressed={!muted} onClick={toggleMusic}>
            {muted ? 'Music on' : 'Mute'}
          </Button>
        </div>
        {step === 0 && <ModeStage onLocal={() => setStep(1)} />}
        {step === 1 && (
          <CampaignStage title={title} onTitleChange={setTitle} onNext={() => setStep(2)} onBack={() => setStep(0)} />
        )}
        {step === 2 && <CountStage onChoose={chooseCount} onBack={() => setStep(1)} />}
        {step === HERO_STEP && (
          <HeroStage count={count} party={party} onPartyChange={setParty} onBack={() => setStep(2)} onDone={finishParty} />
        )}
        {step === STYLE_STEP && (
          <StyleStage selected={style} onChoose={chooseStyle} onBack={() => setStep(HERO_STEP)} />
        )}
        {step === READY_STEP && (
          <ReadyStage
            title={title.trim()}
            style={style}
            party={party}
            saveState={saveState}
            onRetrySave={() => save(style)}
            onChangeParty={() => setStep(HERO_STEP)}
            onChangeStyle={() => setStep(STYLE_STEP)}
          />
        )}
      </main>
    </div>
  )
}
