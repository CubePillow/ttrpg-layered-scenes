import { useEffect, useLayoutEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react'
import HeroPortrait from '../components/party/HeroPortrait'
import PixelScene from '../components/pixel-scene/PixelScene'
import { Badge, Button, Panel, SectionTitle } from '../components/ui'
import { canDictate, useDictation } from '../audio/useDictation'
import VoiceMeter from '../components/ui/VoiceMeter'
import { loadSave, storeSave, type Save, type ActState } from '../data/saves'
import { editStory, storyText, wordsByHero, type StoryPiece } from '../data/story'
import styles from './StoryPage.module.css'

type SaveState = 'saved' | 'saving' | 'failed'

const saveId = () => new URLSearchParams(window.location.search).get('save')

/**
 * The shared story: every player writes in one field, like a shared document.
 * Pick who is writing, and what they type shows in their hero's colour. Changes save on their own.
 */
export default function StoryPage() {
  const id = useRef(saveId())
  const [save, setSave] = useState<Save | null>(null)
  const [missing, setMissing] = useState(false)
  const [pieces, setPieces] = useState<StoryPiece[]>([])
  const [gmDirection, setGmDirection] = useState('')
  const [writer, setWriter] = useState<string | null>(null)
  const [saveState, setSaveState] = useState<SaveState>('saved')
  const mirror = useRef<HTMLDivElement>(null)
  const field = useRef<HTMLTextAreaElement>(null)
  /** Where the cursor is, so the writer's portrait can follow it */
  const [caret, setCaret] = useState(0)
  const [focused, setFocused] = useState(false)
  const [typing, setTyping] = useState(false)
  const typingTimer = useRef<number | undefined>(undefined)
  /** The portrait flag fades once the writer has been still for a moment */
  const [active, setActive] = useState(true)
  const activeTimer = useRef<number | undefined>(undefined)
  const wake = () => {
    setActive(true)
    window.clearTimeout(activeTimer.current)
    activeTimer.current = window.setTimeout(() => setActive(false), 1500)
  }
  const timer = useRef<number | undefined>(undefined)
  /** On the first line there is no room above the cursor, so the bubble goes below it instead */
  const marker = useRef<HTMLSpanElement>(null)
  const [below, setBelow] = useState(false)
  const [scrolled, setScrolled] = useState(0)
  useLayoutEffect(() => {
    if (!marker.current || !mirror.current) return
    setBelow(marker.current.offsetTop - mirror.current.scrollTop < 36)
  }, [caret, pieces, focused, writer, scrolled])

  useEffect(() => {
    if (!id.current) {
      setMissing(true)
      return
    }
    loadSave(id.current).then((loaded) => {
      if (!loaded) return setMissing(true)
      setSave(loaded)
      setPieces(loaded.play?.story ?? [])
      setGmDirection(loaded.play?.gmDirection ?? '')
      setWriter(loaded.setup.party[0]?.id ?? null)
    })
  }, [])

  /** Saves a moment after the last change, so typing does not send a save per key. */
  const keep = (next: StoryPiece[], delay = 600, direction = gmDirection) => {
    if (!save || !id.current) return
    setSaveState('saving')
    window.clearTimeout(timer.current)
    const saveTo = id.current
    timer.current = window.setTimeout(async () => {
      try {
        await storeSave(saveTo, {
          ...save,
          phase: 'playing',
          play: {
            ...save.play,
            act: save.play?.act ?? 1,
            actState: save.play?.actState ?? 'writing',
            gmDirection: direction,
            story: next,
          },
        })
        setSaveState('saved')
      } catch {
        setSaveState('failed')
      }
    }, delay)
  }

  const type = (text: string) => {
    if (!writer) return
    const next = editStory(pieces, text, writer)
    setPieces(next)
    keep(next)
    setTyping(true)
    window.clearTimeout(typingTimer.current)
    typingTimer.current = window.setTimeout(() => setTyping(false), 350)
    wake()
  }

  /** A spoken phrase goes in where the cursor is, from whoever is writing. */
  const dictation = useDictation((phrase) => {
    if (!phrase) return
    const text = storyText(pieces)
    const at = field.current?.selectionEnd ?? text.length
    const spaced = at > 0 && !/\s/.test(text[at - 1]) && /^\w/.test(phrase) ? ` ${phrase}` : phrase
    type(text.slice(0, at) + spaced + text.slice(at))
    setCaret(at + spaced.length) // The field may not have focus while speaking, so move the drawn cursor too
    requestAnimationFrame(() => field.current?.setSelectionRange(at + spaced.length, at + spaced.length))
  })

  if (missing) {
    return (
      <Frame>
        <p>This story could not be found.</p>
        <Button href="/saves">Load story</Button>
      </Frame>
    )
  }
  if (!save) return <Frame>Loading the story…</Frame>

  const { party } = save.setup
  const color = (heroId: string) => party.find((h) => h.id === heroId)?.color ?? 'inherit'
  const text = storyText(pieces)
  const counts = wordsByHero(pieces)
  const totalWords = Object.values(counts).reduce((sum, n) => sum + n, 0)
  const gmWordCount = gmDirection.trim() ? gmDirection.trim().split(/\s+/).length : 0

  /** The act being played; it moves on once drawing is built */
  const now: { number: number; state: ActState } = {
    number: save.play?.act ?? 1,
    state: save.play?.actState ?? 'writing',
  }
  /** Draws pieces in their writers' colours */
  const paint = (list: StoryPiece[], key: string) =>
    list.map((piece, i) => (
      <span key={`${key}${i}`} style={{ color: color(piece.heroId) }}>
        {piece.text}
      </span>
    ))

  const writing = party.find((h) => h.id === writer)

  /** Our own cursor: a bar in the writer's colour with their portrait as a flag on top, like a shared document */
  const showCursor = writing !== undefined && (focused || dictation.listening)

  return (
    <Frame
      actions={
        <Button onClick={() => keep(pieces, 0)} disabled={saveState === 'saving'} role="status">
          {{ saved: 'Saved ✓', saving: 'Saving…', failed: 'Not saved' }[saveState]}
        </Button>
      }
    >
      <div className={styles.titleRow}>
        <SectionTitle className={styles.title}>{save.setup.title}</SectionTitle>
        <span className={styles.actTag} data-state={now.state}>
          Act {now.number} · {now.state === 'drawn' ? 'Drawn' : 'Writing'}
        </span>
      </div>
      <div className={styles.direction}>
        <label className={styles.directionLabel} htmlFor="gm-direction">
          Gamemaster&apos;s direction
        </label>
        <p className={styles.directionHint}>Set a story beat or mood for the players to build on.</p>
        <div className={styles.directionEditor}>
          <textarea
            id="gm-direction"
            className={styles.directionField}
            value={gmDirection}
            placeholder="What should happen next?"
            spellCheck={false}
            onChange={(event) => {
              const direction = event.target.value
              setGmDirection(direction)
              keep(pieces, 600, direction)
            }}
          />
          <span className={styles.directionTotal}>
            {gmWordCount} {gmWordCount === 1 ? 'word' : 'words'}
          </span>
        </div>
      </div>
      <div className={styles.toolbar} style={{ '--writer': writing?.color } as CSSProperties}>
        <span className={styles.label}>Writing as</span>
        <div className={styles.writers} role="radiogroup" aria-label="Who is writing">
          {party.map((hero) => (
            <button
              key={hero.id}
              type="button"
              role="radio"
              aria-checked={writer === hero.id}
              className={styles.writer}
              style={{ '--hero': hero.color } as CSSProperties}
              onClick={() => setWriter(hero.id)}
            >
              <HeroPortrait classId={hero.classId} color={hero.color} scale={2} label={hero.name} />
              <span>{hero.name}</span>
              <span className={styles.count} title={`${counts[hero.id] ?? 0} words written`}>
                {counts[hero.id] ?? 0}
              </span>
            </button>
          ))}
        </div>
        {canDictate && (
          <button
            type="button"
            className={dictation.listening ? `${styles.mic} ${styles.micOn}` : styles.mic}
            aria-pressed={dictation.listening}
            onClick={dictation.listening ? dictation.stop : dictation.start}
          >
            {dictation.listening ? (
              <>
                <VoiceMeter />
                <span>Listening</span>
                <span className={styles.stop} aria-label="Stop">
                  ■
                </span>
              </>
            ) : (
              '🎤 Speak'
            )}
          </button>
        )}
      </div>
      {/* Shown only when something is going on; the field's placeholder already says how to write */}
      {(dictation.error || dictation.listening) && (
        <p className={dictation.listening ? `${styles.hint} ${styles.listening}` : styles.hint} role="status">
          {dictation.error
            ? `${dictation.error}. You can still type in the box.`
            : dictation.heard || `Listening to ${writing?.name ?? 'you'}… speak now, then press ■ to finish.`}
        </p>
      )}
      <div
        className={dictation.listening ? `${styles.editor} ${styles.editorListening}` : styles.editor}
        style={{ '--writer': writing?.color } as CSSProperties}
      >
        <div ref={mirror} className={styles.mirror} aria-hidden="true">
          {paint(piecesAround(pieces, caret).before, 'b')}
          {showCursor && writing && (
            <span ref={marker} className={below ? `${styles.marker} ${styles.below}` : styles.marker}>
              <span
                key={writing.id}
                className={[
                  styles.follower,
                  (typing || dictation.heard) && styles.busy,
                  !active && !dictation.listening && styles.idle,
                ]
                  .filter(Boolean)
                  .join(' ')}
              >
                <HeroPortrait classId={writing.classId} color={writing.color} scale={1.4} label={writing.name} />
              </span>
            </span>
          )}
          {paint(piecesAround(pieces, caret).after, 'a')}
          {/* Keeps a last empty line the same height as in the field */}
          {'​'}
        </div>
        <span className={styles.total}>
          {totalWords} {totalWords === 1 ? 'word' : 'words'}
        </span>
        <textarea
          ref={field}
          className={styles.field}
          value={text}
          placeholder={`${writing ? `${writing.name}: ` : ''}type what happens next${canDictate ? ', or press 🎤 Speak' : ''}…`}
          spellCheck={false}
          style={{ caretColor: showCursor ? 'transparent' : undefined }}
          onChange={(e) => {
            type(e.target.value)
            setCaret(e.target.selectionEnd)
          }}
          onSelect={(e) => {
            setCaret(e.currentTarget.selectionEnd)
            wake()
          }}
          onKeyUp={(e) => setCaret(e.currentTarget.selectionEnd)}
          onClick={(e) => setCaret(e.currentTarget.selectionEnd)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          onScroll={(e) => {
            if (mirror.current) mirror.current.scrollTop = e.currentTarget.scrollTop
            setScrolled(e.currentTarget.scrollTop)
          }}
        />
      </div>
      <div className={styles.drawRow}>
        <Button variant="primary" disabled>
          <BrushIcon />
          Draw this scene <Badge>coming soon</Badge>
        </Button>
      </div>
    </Frame>
  )
}

/** The pieces split at a place in the text, so something can be put there. */
function piecesAround(pieces: StoryPiece[], at: number) {
  const before: StoryPiece[] = []
  const after: StoryPiece[] = []
  let from = 0
  for (const piece of pieces) {
    const cut = Math.min(Math.max(at - from, 0), piece.text.length)
    if (cut > 0) before.push({ heroId: piece.heroId, text: piece.text.slice(0, cut) })
    if (cut < piece.text.length) after.push({ heroId: piece.heroId, text: piece.text.slice(cut) })
    from += piece.text.length
  }
  return { before, after }
}

/** A small pixel paintbrush. */
function BrushIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 8 8"
      shapeRendering="crispEdges"
      aria-hidden="true"
      fill="currentColor"
      className={styles.icon}
    >
      <rect x="6" y="0" width="2" height="1" />
      <rect x="5" y="1" width="2" height="1" />
      <rect x="4" y="2" width="2" height="1" />
      <rect x="3" y="3" width="2" height="1" />
      <rect x="1" y="4" width="3" height="1" />
      <rect x="0" y="5" width="3" height="2" />
      <rect x="0" y="7" width="2" height="1" />
    </svg>
  )
}

function Frame({ actions, children }: { actions?: ReactNode; children: ReactNode }) {
  return (
    <div className={styles.page}>
      <PixelScene highlight={null} className={styles.scene} />
      <div className={styles.shade} />
      <main className={styles.content}>
        <div className={styles.topBar}>
          <Button href="/">Home</Button>
          {actions}
        </div>
        <Panel className={styles.panel}>{children}</Panel>
      </main>
    </div>
  )
}
