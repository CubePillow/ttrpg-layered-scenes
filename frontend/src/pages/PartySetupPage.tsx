import { useEffect, useState } from 'react'
import { isMusicMuted, playTheme, setMusicMuted, stopTheme } from '../audio/chiptune'
import { AMBIENT_THEME } from '../audio/heroThemes'
import CampaignStage from '../components/party/CampaignStage'
import CountStage from '../components/party/CountStage'
import HeroStage from '../components/party/HeroStage'
import ModeStage from '../components/party/ModeStage'
import ReadyStage from '../components/party/ReadyStage'
import PixelScene from '../components/pixel-scene/PixelScene'
import { Button, StepTrail } from '../components/ui'
import type { Hero } from '../data/heroes'
import styles from './PartySetupPage.module.css'

const STEPS = ['Mode', 'Title', 'Players', 'Heroes', 'Set off']
const HERO_STEP = 3

export default function PartySetupPage() {
  const [step, setStep] = useState(0)
  const [title, setTitle] = useState('')
  const [count, setCount] = useState(1)
  const [party, setParty] = useState<Hero[]>([])
  const [muted, setMuted] = useState(isMusicMuted)

  // Quiet music throughout; while choosing a hero, that hero's theme plays instead
  useEffect(() => {
    if (step !== HERO_STEP) playTheme(AMBIENT_THEME)
  }, [step])

  useEffect(() => stopTheme, [])

  const toggleMusic = () => {
    setMusicMuted(!muted)
    setMuted(!muted)
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
          <HeroStage count={count} party={party} onPartyChange={setParty} onBack={() => setStep(2)} onDone={() => setStep(4)} />
        )}
        {step === 4 && <ReadyStage title={title.trim()} party={party} onBack={() => setStep(HERO_STEP)} />}
      </main>
    </div>
  )
}
