import { useEffect, useState } from 'react'
import PixelScene from '../components/pixel-scene/PixelScene'
import { ActSteps, Button, Eyebrow, MusicToggle, Panel, SectionTitle } from '../components/ui'
import { roman } from '../data/roman'
import { generateImage, pixelize, randomSeed } from '../api/images'
import { actStart, loadSave, type Save } from '../data/saves'
import { keepPicked } from '../data/picked'
import { scenePrompt } from '../data/scenePrompt'
import styles from './DrawPage.module.css'

const CANDIDATES = 3
/** SDXL-Turbo reads about 75 tokens, a little over 50 words; the rest of a longer prompt is cut off */
const PROMPT_WORDS = 55

const saveId = () => new URLSearchParams(window.location.search).get('save')
const wordCount = (text: string) => text.split(/\s+/).filter(Boolean).length

/** `image` is the plain picture the model drew, which is what gets split; `pixel` is how a pixel-art story shows it */
type Candidate = { seed: number; image: string | null; pixel?: string }

/**
 * Drawing the act: shows the prompt the picture model is given (built from the story, and open to changes),
 * then draws three versions from consecutive seeds, like the prototype, to pick one from.
 */
export default function DrawPage() {
  const id = saveId()
  const [save, setSave] = useState<Save | null>(null)
  const [missing, setMissing] = useState(!id)
  const [prompt, setPrompt] = useState('')
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [drawing, setDrawing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const pixelStyle = save?.setup.style === 'pixel'
  const built = save ? scenePrompt(save.play?.story ?? [], actStart(save.play, save.play?.act ?? 1)) : ''

  useEffect(() => {
    if (!id) return
    loadSave(id).then((loaded) => {
      if (!loaded) return setMissing(true)
      setSave(loaded)
      setPrompt(scenePrompt(loaded.play?.story ?? [], actStart(loaded.play, loaded.play?.act ?? 1)))
    })
  }, [id])

  const draw = async () => {
    const text = prompt.trim()
    if (!text || drawing) return
    const first = randomSeed()
    setError(null)
    setDrawing(true)
    setCandidates(Array.from({ length: CANDIDATES }, (_, i) => ({ seed: first + i, image: null })))
    // The GPU takes one request at a time, so the versions come one after another
    for (let i = 0; i < CANDIDATES; i++) {
      try {
        const image = await generateImage(text, first + i)
        // A pixel-art story gets the pixel version straight away; the plain picture is kept for splitting
        const pixel = pixelStyle ? (await pixelize([{ name: 'scene', image }])).layers[0].image : undefined
        setCandidates((all) => all.map((c, j) => (j === i ? { ...c, image, pixel } : c)))
      } catch (failure) {
        setError((failure as Error).message)
        setCandidates((all) => all.slice(0, i))
        break
      }
    }
    setDrawing(false)
  }

  /** Picking a version opens the layers page with it */
  const pick = (c: Candidate) => {
    if (!id || !c.image) return
    if (!keepPicked(id, { image: c.image, pixel: c.pixel, prompt: prompt.trim(), seed: c.seed })) {
      return setError('The picture could not be kept in this browser tab. Try again.')
    }
    window.location.assign(`/layers?save=${encodeURIComponent(id)}`)
  }

  const words = wordCount(prompt)
  const storyLink = id ? `/story?save=${encodeURIComponent(id)}` : '/saves'

  return (
    <div className={styles.page}>
      <PixelScene highlight={null} className={styles.scene} />
      <div className={styles.shade} />
      <main className={styles.content}>
        <div className={styles.topBar}>
          <ActSteps current={1} />
          <div className={styles.topActions}>
            <Button href="/">Home</Button>
            <MusicToggle />
          </div>
        </div>
        <Panel className={styles.panel}>
          {missing ? (
            <>
              <p>This story could not be found.</p>
              <Button href="/saves">Load story</Button>
            </>
          ) : !save ? (
            <p>Loading the story…</p>
          ) : (
            <>
              <header className={styles.header}>
                <div>
                  <Eyebrow>Act {roman(save.play?.act ?? 1)}</Eyebrow>
                  <SectionTitle className={styles.title}>{save.setup.title}</SectionTitle>
                </div>
              </header>

              <div className={styles.scroll}>
                <label htmlFor="prompt" className={styles.label}>
                  ✦ What the painter will draw <small>prompt for SDXL-Turbo</small>
                </label>
                <textarea
                  id="prompt"
                  className={styles.prompt}
                  value={prompt}
                  rows={4}
                  maxLength={2000}
                  disabled={drawing}
                  onChange={(e) => setPrompt(e.target.value)}
                />
                <div className={styles.promptFoot}>
                  <span className={words > PROMPT_WORDS ? styles.tooLong : undefined}>
                    {words} words{words > PROMPT_WORDS && ` · the model only reads about the first ${PROMPT_WORDS}`}
                  </span>
                  {prompt !== built && (
                    <button type="button" className={styles.reset} disabled={drawing} onClick={() => setPrompt(built)}>
                      Back to the prompt from the story
                    </button>
                  )}
                </div>
                <p className={styles.how}>
                  Made from: a flat vector look (simple shapes, large colour blocks, few details) and the last 40 words of this act's text.
                </p>
              </div>

              <div className={styles.actions}>
                <Button href={storyLink}>Back</Button>
                <Button variant="primary" disabled={!prompt.trim() || drawing} onClick={draw}>
                  <span className={drawing ? styles.rolling : undefined} aria-hidden="true">
                    🎲
                  </span>{' '}
                  {drawing
                    ? 'Drawing…'
                    : candidates.length
                      ? `Draw ${CANDIDATES} again`
                      : `Draw ${CANDIDATES} versions`}
                </Button>
              </div>

              {error && (
                <p className={styles.error} role="alert">
                  {error}
                </p>
              )}

              {candidates.length > 0 && <p className={styles.choose}>Choose the picture for this act</p>}
              {candidates.length > 0 && (
                <div className={styles.candidates} aria-label="Pick a version">
                  {candidates.map((c, i) => (
                    <figure key={c.seed} className={styles.figure}>
                      <span className={styles.banner}>{roman(i + 1)}</span>
                      {c.image ? (
                        <button type="button" className={styles.candidate} onClick={() => pick(c)} title="Use this one">
                          {c.pixel ? (
                            <img src={c.pixel} alt={`Version ${i + 1}, pixel art`} className={styles.pixel} />
                          ) : (
                            <img src={c.image} alt={`Version ${i + 1}`} />
                          )}
                        </button>
                      ) : (
                        <div className={styles.waiting}>
                          {drawing && (
                            <>
                              <span className={styles.die} aria-hidden="true">
                                🎲
                              </span>
                              Drawing {i + 1} of {CANDIDATES}…
                            </>
                          )}
                        </div>
                      )}
                      <figcaption>seed {c.seed}</figcaption>
                    </figure>
                  ))}
                </div>
              )}
            </>
          )}
        </Panel>
      </main>
    </div>
  )
}
