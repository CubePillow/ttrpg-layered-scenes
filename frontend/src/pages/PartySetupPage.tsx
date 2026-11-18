import { useState } from 'react'
import CampaignStage from '../components/party/CampaignStage'
import CountStage from '../components/party/CountStage'
import HeroStage from '../components/party/HeroStage'
import ModeStage from '../components/party/ModeStage'
import ReadyStage from '../components/party/ReadyStage'
import PixelScene from '../components/pixel-scene/PixelScene'
import { StepTrail } from '../components/ui'
import type { Hero } from '../data/heroes'
import styles from './PartySetupPage.module.css'

const STEPS = ['Mode', 'Title', 'Players', 'Heroes', 'Set off']

export default function PartySetupPage() {
  const [step, setStep] = useState(0)
  const [title, setTitle] = useState('')
  const [count, setCount] = useState(1)
  const [party, setParty] = useState<Hero[]>([])

  const chooseCount = (players: number) => {
    setCount(players)
    setParty((heroes) => heroes.slice(0, players))
    setStep(3)
  }

  return (
    <div className={styles.page}>
      <PixelScene highlight={null} className={styles.scene} />
      <div className={styles.shade} />
      <main className={styles.content}>
        <StepTrail steps={STEPS} current={step} />
        {step === 0 && <ModeStage onLocal={() => setStep(1)} />}
        {step === 1 && (
          <CampaignStage title={title} onTitleChange={setTitle} onNext={() => setStep(2)} onBack={() => setStep(0)} />
        )}
        {step === 2 && <CountStage onChoose={chooseCount} onBack={() => setStep(1)} />}
        {step === 3 && (
          <HeroStage count={count} party={party} onPartyChange={setParty} onBack={() => setStep(2)} onDone={() => setStep(4)} />
        )}
        {step === 4 && <ReadyStage title={title.trim()} party={party} onBack={() => setStep(3)} />}
      </main>
    </div>
  )
}
