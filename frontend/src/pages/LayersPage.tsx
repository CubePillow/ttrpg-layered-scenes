import { useEffect, useRef, useState, type KeyboardEvent, type PointerEvent as ReactPointerEvent } from 'react'
import PixelScene from '../components/pixel-scene/PixelScene'
import { ActSteps, Button, Eyebrow, MusicToggle, Panel, SectionTitle, TextInput } from '../components/ui'
import { roman } from '../data/roman'
import { editLayer, pixelize, splitImage } from '../api/images'
import { pictureData, storePicture } from '../api/pictures'
import { clearPicked, loadPicked, type PickedPicture } from '../data/picked'
import { actStart, loadSave, storeSave, type ActSave, type Save } from '../data/saves'
import { editStory, splitStory, storyText, type StoryPiece } from '../data/story'
import styles from './LayersPage.module.css'

const MAX_OBJECTS = 8
/** The smallest a layer can be made, as a share of the picture's width */
const MIN_SIZE = 0.04

const saveId = () => new URLSearchParams(window.location.search).get('save')

/** A layer on the stage. Place and size are shares of the picture (0 to 1), so they hold at any stage size. */
type StageLayer = {
  name: string
  /** What is shown: the layer cut to its content, in pixel art for pixel-art stories */
  image: string
  /** The whole layer as the split made it, which is what gets kept; and its id once kept */
  source: string
  sourceId?: string
  x: number
  y: number
  w: number
  h: number
  hidden: boolean
  /** The repaint instructions this layer went through, oldest first; they also go into the act's prompt */
  edits?: string[]
  /** Where the split put it, for Reset */
  start: { x: number; y: number; w: number; h: number }
}

/** The part of a layer that is not see-through, cut out, with where it was in the picture. */
async function trimLayer(src: string) {
  const picture = new Image()
  picture.src = src
  await picture.decode()
  const { width: W, height: H } = picture
  const canvas = document.createElement('canvas')
  canvas.width = W
  canvas.height = H
  const context = canvas.getContext('2d')!
  context.drawImage(picture, 0, 0)
  const alpha = context.getImageData(0, 0, W, H).data
  let left = W
  let top = H
  let right = -1
  let bottom = -1
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      if (alpha[(y * W + x) * 4 + 3] > 127) {
        if (x < left) left = x
        if (x > right) right = x
        if (y < top) top = y
        if (y > bottom) bottom = y
      }
    }
  }
  if (right < 0) return null // Nothing in this layer
  const cut = document.createElement('canvas')
  cut.width = right - left + 1
  cut.height = bottom - top + 1
  cut.getContext('2d')!.drawImage(canvas, -left, -top)
  return { image: cut.toDataURL(), x: left / W, y: top / H, w: cut.width / W, h: cut.height / H }
}

type Part = { name: string; image: string; id?: string }

/** The split layers made ready for the stage: cut to their content, and turned into pixel art if the story is. */
async function stageLayers(parts: Part[], pixelStyle: boolean): Promise<StageLayer[]> {
  const layer = (part: Part, image: string, box: { x: number; y: number; w: number; h: number }): StageLayer => ({
    name: part.name,
    image,
    source: part.image,
    sourceId: part.id,
    ...box,
    hidden: false,
    start: box,
  })
  if (pixelStyle) {
    // All layers on one pixel grid with one palette, each cut to what it shows
    const { grid, layers: pixels } = await pixelize(parts.map(({ name, image }) => ({ name, image })))
    const [W, H] = grid
    return pixels.map((l, i) => layer(parts[i], l.image, { x: l.x / W, y: l.y / H, w: l.width / W, h: l.height / H }))
  }
  const cut = await Promise.all(parts.map((p) => trimLayer(p.image)))
  return parts.flatMap((p, i) => (cut[i] ? [layer(p, cut[i].image, cut[i])] : []))
}

/** Moves and resizes from where each layer was cut, as kept in the save */
const moved = (l: StageLayer) => ({
  dx: l.x - l.start.x,
  dy: l.y - l.start.y,
  scale: l.w / l.start.w,
  hidden: l.hidden,
  edits: l.edits ?? [],
})

/** A layer made ready again, put back where it was moved to, with its repaints */
const placeAgain = (l: StageLayer, m: ReturnType<typeof moved>): StageLayer => ({
  ...l,
  x: l.x + m.dx,
  y: l.y + m.dy,
  w: l.w * m.scale,
  h: l.h * m.scale,
  hidden: m.hidden,
  edits: m.edits,
})

/** The repaints as lines added to the act's text: " tree: autumn leaves." */
const repaintLines = (layers: { name: string; edits?: string[] }[]) =>
  layers.flatMap((l) => (l.edits ?? []).map((e) => ` ${l.name}: ${e}.`)).join('')

/**
 * The story with this act's text ending in the current repaint lines instead of the ones saved before,
 * so a repaint shows on the story and drawing pages too, and Undo takes its line out again.
 */
function storyWithRepaints(story: StoryPiece[], start: number, before: string, after: string, writer: string) {
  const { earlier, current } = splitStory(story, start)
  let text = storyText(current)
  if (before && text.endsWith(before)) text = text.slice(0, -before.length)
  return [...earlier, ...editStory(current, text + after, writer)]
}

/** The act's prompt with the repaints added, each once: "…, tree: autumn leaves" */
function promptWithEdits(base: string, layers: StageLayer[]) {
  const added = layers.flatMap((l) => (l.edits ?? []).map((e) => `${l.name}: ${e}`)).filter((e) => !base.includes(e))
  return [base, ...added].join(', ')
}

/**
 * The picked picture, split into a background and one layer per object.
 * Every object layer can then be dragged to move it and resized from its corner.
 */
export default function LayersPage() {
  const id = saveId()
  /** The picture to split: the one just picked on the drawing page, or the act's kept picture */
  const [picked, setPicked] = useState<(PickedPicture & { pictureId?: string }) | null>(() =>
    id ? loadPicked(id) : null,
  )
  const [save, setSave] = useState<Save | null>(null)
  const [saving, setSaving] = useState<'idle' | 'saving' | 'saved' | 'failed'>('idle')
  /** The objects to cut out, comma separated, back to front, as in the prototype */
  const [namesText, setNamesText] = useState('')
  const names = [
    ...new Set(
      namesText
        .split(',')
        .map((n) => n.trim())
        .filter(Boolean),
    ),
  ]
  const [layers, setLayers] = useState<StageLayer[]>([])
  const [selected, setSelected] = useState<number | null>(null)
  const [splitting, setSplitting] = useState(false)
  /** A short message in the toolbar, such as what was just deleted */
  const [notice, setNotice] = useState<string | null>(null)
  const noticeTimer = useRef<number | undefined>(undefined)
  /** Changing the selected layer by a text instruction */
  const [editText, setEditText] = useState('')
  const [editing, setEditing] = useState(false)
  const [editNote, setEditNote] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const stage = useRef<HTMLDivElement>(null)
  /** The drag going on: moving a layer, or resizing it from its corner */
  const drag = useRef<{ index: number; mode: 'move' | 'resize'; px: number; py: number; box: StageLayer } | null>(null)

  useEffect(() => {
    if (!id) return
    loadSave(id).then(async (loaded) => {
      setSave(loaded)
      if (!loaded) return
      // Open the act as it was kept, unless another picture has been picked since
      const kept = loaded.play?.acts?.find((a) => a.number === (loaded.play?.act ?? 1))
      const fresh = loadPicked(id)
      if (!kept || (fresh && fresh.seed !== kept.seed)) return
      try {
        const image = await pictureData(kept.pictureId)
        const parts = await Promise.all(
          kept.layers.map(async (l) => ({ name: l.name, image: await pictureData(l.pictureId), id: l.pictureId })),
        )
        const restored = (await stageLayers(parts, loaded.setup.style === 'pixel')).map((l, i) => {
          const m = kept.layers[i]
          return placeAgain(l, { ...m, edits: m.edits ?? [] })
        })
        setPicked({ image, prompt: kept.prompt, seed: kept.seed, pictureId: kept.pictureId })
        setLayers(restored)
        setSaving('saved')
      } catch (failure) {
        setError((failure as Error).message)
      }
    })
  }, [id])

  const pixelStyle = save?.setup.style === 'pixel'
  const drawLink = id ? `/draw?save=${encodeURIComponent(id)}` : '/saves'

  /**
   * Keeps the act: the picked picture and every layer go to the backend once (only their ids go in the save),
   * then the save gets the act with how each layer was moved, and the act counts as drawn.
   */
  const keepAct = async (current: StageLayer[] = layers): Promise<Save | null> => {
    if (!id || !save || !picked || saving === 'saving') return null
    setSaving('saving')
    setError(null)
    try {
      const pictureId = picked.pictureId ?? (await storePicture(id, picked.image))
      const ids = await Promise.all(current.map((l) => l.sourceId ?? storePicture(id, l.source)))
      setPicked({ ...picked, pictureId })
      // Remember which pictures are kept, so they are not sent again
      const kept = new Map(current.map((l, i) => [l.source, ids[i]]))
      setLayers((all) => all.map((l) => ({ ...l, sourceId: l.sourceId ?? kept.get(l.source) })))
      const number = save.play?.act ?? 1
      const start = actStart(save.play, number)
      const before = repaintLines(save.play?.acts?.find((a) => a.number === number)?.layers ?? [])
      const oldStory = save.play?.story ?? []
      const writer = splitStory(oldStory, start).current.at(-1)?.heroId ?? save.setup.party[0]?.id ?? ''
      const story = storyWithRepaints(oldStory, start, before, repaintLines(current), writer)
      const act: ActSave = {
        number,
        from: start,
        to: storyText(story).length,
        // A prompt changed on the drawing page since the picture was picked wins
        // and the repaints are added, so Undo of a repaint takes its words out again
        prompt: promptWithEdits(save.play?.draft?.act === number ? save.play.draft.prompt : picked.prompt, current),
        seed: picked.seed,
        pictureId,
        layers: current.map((l, i) => ({ name: l.name, pictureId: ids[i], ...moved(l) })),
      }
      const play = save.play ?? {}
      const next: Save = {
        ...save,
        phase: 'playing',
        play: {
          ...play,
          story,
          act: number,
          actState: 'drawn',
          acts: [...(play.acts ?? []).filter((a) => a.number !== number), act],
        },
      }
      await storeSave(id, next)
      setSave(next)
      setSaving('saved')
      return next
    } catch (failure) {
      setError((failure as Error).message)
      setSaving('failed')
      return null
    }
  }

  const split = async () => {
    if (!picked || names.length === 0 || names.length > MAX_OBJECTS || splitting) return
    setError(null)
    setSplitting(true)
    try {
      const next = await stageLayers(await splitImage(picked.image, names), pixelStyle)
      setLayers(next)
      setSelected(next.length > 1 ? 1 : null)
      // Kept right away: a split takes the GPU a minute, and a page reload would otherwise lose it
      void keepAct(next)
    } catch (failure) {
      setError((failure as Error).message)
    }
    setSplitting(false)
  }

  /** Earlier versions of the layers, newest last, for Undo */
  const history = useRef<StageLayer[][]>([])
  const [undoCount, setUndoCount] = useState(0)
  /** Steps taken back by Undo, newest last, for Redo */
  const future = useRef<StageLayer[][]>([])
  const [redoCount, setRedoCount] = useState(0)

  /** Remembers the layers as they are now, so the next change can be undone */
  const remember = () => {
    history.current = [...history.current.slice(-49), layers]
    setUndoCount(history.current.length)
    // A new change ends the steps Redo could bring back
    future.current = []
    setRedoCount(0)
  }

  /** Replaces all layers, as one step that Undo can take back */
  const commit = (next: StageLayer[]) => {
    remember()
    setLayers(next)
    setSaving('idle')
  }

  /** Changes one layer. A drag records one step when it starts, so its moves pass `record = false`. */
  const change = (index: number, box: Partial<StageLayer>, record = true) => {
    if (record) remember()
    setLayers((all) => all.map((l, i) => (i === index ? { ...l, ...box } : l)))
    setSaving('idle')
  }

  /** Shows an earlier or later version of the layers */
  const show = (version: StageLayer[]) => {
    setLayers(version)
    const still = selected !== null && selected < version.length ? selected : null
    setSelected(still)
    // The repaint box shows the instruction of the version now shown
    setEditText(still === null ? '' : (version[still].edits?.at(-1) ?? ''))
    setSaving('idle')
    void keepAct(version) // Kept at once, so a reload does not bring back an undone repaint
  }

  /** Back to naming the objects: the layers and their steps are dropped */
  const splitAgain = () => {
    history.current = []
    future.current = []
    setUndoCount(0)
    setRedoCount(0)
    setLayers([])
  }

  const undo = () => {
    const last = history.current.at(-1)
    if (!last) return
    history.current = history.current.slice(0, -1)
    future.current = [...future.current, layers]
    setUndoCount(history.current.length)
    setRedoCount(future.current.length)
    show(last)
  }

  const redo = () => {
    const next = future.current.at(-1)
    if (!next) return
    future.current = future.current.slice(0, -1)
    history.current = [...history.current, layers]
    setUndoCount(history.current.length)
    setRedoCount(future.current.length)
    show(next)
  }

  /**
   * Repaints the selected layer from a text instruction. The whole layer goes to the model, as the split made it;
   * then every layer is made ready again (one shared pixel palette), keeping where each was moved to.
   */
  const repaint = async () => {
    const index = selected
    const text = editText.trim()
    if (index === null || !text || editing) return
    setEditing(true)
    setEditNote(null)
    setError(null)
    try {
      const { image, accepted } = await editLayer(layers[index].source, layers[index].name, text)
      const parts = layers.map((l, i) => ({
        name: l.name,
        image: i === index ? image : l.source,
        id: i === index ? undefined : l.sourceId,
      }))
      const fresh = await stageLayers(parts, pixelStyle)
      const next = fresh.map((l, i) => {
        const m = moved(layers[i])
        return placeAgain(l, i === index ? { ...m, edits: [...m.edits, text] } : m)
      })
      commit(next)
      void keepAct(next) // A repaint is GPU work too, so it is kept at once
      if (!accepted) setEditNote('The model was not sure about this change; Undo takes it back.')
    } catch (failure) {
      setError((failure as Error).message)
    }
    setEditing(false)
  }

  /** Deletes an object layer; the background always stays */
  const remove = (index: number) => {
    if (index === 0) return
    const next = layers.filter((_, i) => i !== index)
    commit(next)
    // Keep a layer selected, so the side panel stays; the note says how to get the deleted one back
    setSelected(next.length > 1 ? Math.min(index, next.length - 1) : null)
    setNotice(`Deleted ${layers[index].name}. Undo brings it back.`)
    window.clearTimeout(noticeTimer.current)
    noticeTimer.current = window.setTimeout(() => setNotice(null), 4000)
  }

  /** Moves an object layer one place to the front (+1) or the back (-1); the background stays at the back */
  const reorder = (index: number, step: 1 | -1) => {
    const to = index + step
    if (index === 0 || to < 1 || to >= layers.length) return
    const next = [...layers]
    ;[next[index], next[to]] = [next[to], next[index]]
    commit(next)
    setSelected(to)
  }

  // Ctrl+Z undoes, Ctrl+Y or Ctrl+Shift+Z redoes (Cmd on a Mac), except while typing in a field
  const undoRef = useRef(undo)
  const redoRef = useRef(redo)
  useEffect(() => {
    undoRef.current = undo
    redoRef.current = redo
  })
  useEffect(() => {
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (!(event.ctrlKey || event.metaKey)) return
      const key = event.key.toLowerCase()
      const wantsRedo = key === 'y' || (key === 'z' && event.shiftKey)
      if (key !== 'z' && !wantsRedo) return
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return
      event.preventDefault()
      if (wantsRedo) redoRef.current()
      else undoRef.current()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  /** Keeps the act (if it is not kept yet), then the story goes on with the next act, written after this one's text */
  const nextAct = async () => {
    if (!id) return
    const kept = saving === 'saved' ? save : await keepAct()
    if (!kept) return
    const play = kept.play ?? {}
    try {
      await storeSave(id, { ...kept, play: { ...play, act: (play.act ?? 1) + 1, actState: 'writing' } })
      clearPicked(id)
      window.location.assign(`/story?save=${encodeURIComponent(id)}`)
    } catch (failure) {
      setError((failure as Error).message)
    }
  }

  const startDrag = (event: ReactPointerEvent, index: number, mode: 'move' | 'resize') => {
    if (index === 0) return // The background stays where it is
    event.preventDefault()
    event.stopPropagation()
    setSelected(index)
    ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
    remember()
    drag.current = { index, mode, px: event.clientX, py: event.clientY, box: layers[index] }
  }

  const moveDrag = (event: ReactPointerEvent) => {
    const d = drag.current
    const size = stage.current?.getBoundingClientRect()
    if (!d || !size) return
    const dx = (event.clientX - d.px) / size.width
    const dy = (event.clientY - d.py) / size.height
    if (d.mode === 'move') {
      change(d.index, { x: d.box.x + dx, y: d.box.y + dy }, false)
    } else {
      // From the bottom right corner, keeping the layer's shape
      const scale = Math.max(MIN_SIZE / d.box.w, (d.box.w + dx) / d.box.w)
      change(d.index, { w: d.box.w * scale, h: d.box.h * scale }, false)
    }
  }

  const endDrag = () => {
    drag.current = null
  }

  /** Arrow keys nudge the selected layer; Shift moves it further */
  const nudge = (event: KeyboardEvent) => {
    if (selected === null || selected === 0) return
    const step = event.shiftKey ? 0.05 : 0.01
    const moves: Record<string, [number, number]> = {
      ArrowLeft: [-step, 0],
      ArrowRight: [step, 0],
      ArrowUp: [0, -step],
      ArrowDown: [0, step],
    }
    const move = moves[event.key]
    if (!move) return
    event.preventDefault()
    const l = layers[selected]
    change(selected, { x: l.x + move[0], y: l.y + move[1] })
  }

  const percent = (n: number) => `${n * 100}%`

  return (
    <div className={styles.page}>
      <PixelScene highlight={null} className={styles.scene} />
      <div className={styles.shade} />
      <main className={styles.content}>
        <div className={styles.topBar}>
          <ActSteps current={2} />
          <div className={styles.topActions}>
            <Button href="/">Home</Button>
            <MusicToggle />
            {layers.length > 0 && (
              <Button onClick={() => keepAct()} disabled={saving === 'saving' || saving === 'saved'}>
                {{ idle: 'Save', saving: 'Saving…', saved: 'Saved ✓', failed: 'Save again' }[saving]}
              </Button>
            )}
          </div>
        </div>
        <Panel className={styles.panel}>
          <header className={styles.header}>
            <div>
              <Eyebrow>Act {roman(save?.play?.act ?? 1)}</Eyebrow>
              <SectionTitle className={styles.title}>{save?.setup.title ?? 'Layers'}</SectionTitle>
            </div>
          </header>

          {!picked ? (
            <>
              <p>No picture picked yet.</p>
              <Button variant="primary" href={drawLink}>
                Draw the scene
              </Button>
            </>
          ) : layers.length === 0 ? (
            <>
              <div className={styles.editor}>
                <div className={styles.picture}>
                  <img
                    src={pixelStyle && picked.pixel ? picked.pixel : picked.image}
                    alt="The picked picture"
                    className={pixelStyle ? styles.pixel : undefined}
                  />
                  {splitting && <span className={styles.working}>Cutting out {names.length} objects…</span>}
                </div>
                <div className={styles.side}>
                  <span className={styles.sideTitle}>Objects to cut out</span>
                  <TextInput
                    label="Back to front, with commas"
                    placeholder="cottage, tree, fox"
                    value={namesText}
                    maxLength={500}
                    disabled={splitting}
                    onChange={(e) => setNamesText(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && split()}
                  />
                  <span className={styles.hint}>
                    {names.length > MAX_OBJECTS
                      ? `At most ${MAX_OBJECTS} objects at once`
                      : `${names.length} object${names.length === 1 ? '' : 's'} + the background`}
                  </span>
                </div>
              </div>
              <footer className={styles.footer}>
                <Button href={drawLink}>Back</Button>
                <Button
                  variant="primary"
                  disabled={names.length === 0 || names.length > MAX_OBJECTS || splitting}
                  onClick={split}
                >
                  {splitting ? 'Splitting…' : 'Split'}
                </Button>
              </footer>
            </>
          ) : (
            <>
              <div className={styles.toolbar}>
                <span className={notice ? styles.notice : styles.hint} role="status">
                  {notice ?? 'Drag to move · drag the corner to resize · arrow keys nudge'}
                </span>
                <div className={styles.tools}>
                  <Button onClick={undo} disabled={undoCount === 0} title="Undo (Ctrl+Z)">
                    ↶ Undo
                  </Button>
                  <Button onClick={redo} disabled={redoCount === 0} title="Redo (Ctrl+Y)">
                    ↷ Redo
                  </Button>
                  <Button onClick={() => commit(layers.map((l) => ({ ...l, ...l.start, hidden: false })))}>
                    Reset
                  </Button>
                  <Button onClick={splitAgain}>Split again</Button>
                </div>
              </div>
              <div className={styles.editor}>
                <div
                  ref={stage}
                  className={styles.stage}
                  tabIndex={0}
                  aria-label="The scene: drag a layer to move it, drag its corner to resize it, arrow keys nudge it"
                  onPointerDown={() => setSelected(null)}
                  onKeyDown={nudge}
                >
                  {layers.map((l, i) =>
                    l.hidden ? null : (
                      <div
                        key={l.name + i}
                        className={`${styles.layer} ${i === 0 ? styles.background : ''} ${selected === i ? styles.selected : ''}`}
                        style={{ left: percent(l.x), top: percent(l.y), width: percent(l.w), height: percent(l.h) }}
                        onPointerDown={(e) => startDrag(e, i, 'move')}
                        onPointerMove={moveDrag}
                        onPointerUp={endDrag}
                        onPointerCancel={endDrag}
                      >
                        <img
                          src={l.image}
                          alt={l.name}
                          draggable={false}
                          className={pixelStyle ? styles.pixel : undefined}
                        />
                        {selected === i && (
                          <span
                            className={styles.handle}
                            aria-hidden="true"
                            onPointerDown={(e) => startDrag(e, i, 'resize')}
                            onPointerMove={moveDrag}
                            onPointerUp={endDrag}
                            onPointerCancel={endDrag}
                          />
                        )}
                      </div>
                    ),
                  )}
                </div>

                <div className={styles.side}>
                  <span className={styles.sideTitle}>Layers</span>
                  <ol className={styles.list}>
                    {layers.map((l, i) => (
                      <li key={l.name + i} className={selected === i ? styles.current : undefined}>
                        <button type="button" className={styles.layerName} onClick={() => setSelected(i)}>
                          <img src={l.image} alt="" className={pixelStyle ? styles.pixel : undefined} />
                          {l.name}
                        </button>
                        <span className={styles.tools}>
                          {i > 0 && (
                            <>
                              <button
                                type="button"
                                className={styles.eye}
                                aria-label={`Move ${l.name} to the front`}
                                title="Further to the front"
                                disabled={i === layers.length - 1}
                                onClick={() => reorder(i, 1)}
                              >
                                ▲
                              </button>
                              <button
                                type="button"
                                className={styles.eye}
                                aria-label={`Move ${l.name} to the back`}
                                title="Further to the back"
                                disabled={i === 1}
                                onClick={() => reorder(i, -1)}
                              >
                                ▼
                              </button>
                            </>
                          )}
                          <button
                            type="button"
                            className={styles.eye}
                            aria-pressed={!l.hidden}
                            aria-label={l.hidden ? `Show ${l.name}` : `Hide ${l.name}`}
                            title={l.hidden ? 'Show' : 'Hide'}
                            onClick={() => change(i, { hidden: !l.hidden })}
                          >
                            <EyeIcon open={!l.hidden} />
                          </button>
                          {i > 0 && (
                            <button
                              type="button"
                              className={`${styles.eye} ${styles.bin}`}
                              aria-label={`Delete ${l.name}`}
                              title="Delete this layer"
                              onClick={() => remove(i)}
                            >
                              <BinIcon />
                            </button>
                          )}
                        </span>
                      </li>
                    ))}
                  </ol>
                  {selected !== null && layers[selected] && (
                    <form
                      className={styles.editBox}
                      onSubmit={(event) => {
                        event.preventDefault()
                        repaint()
                      }}
                    >
                      <label htmlFor="repaint" className={styles.editTitle}>
                        ✎ Repaint the {layers[selected].name}
                      </label>
                      <span className={styles.hint}>Describe the change</span>
                      <textarea
                        id="repaint"
                        className={styles.editText}
                        rows={4}
                        placeholder="e.g. autumn leaves, orange and red"
                        value={editText}
                        maxLength={300}
                        disabled={editing}
                        onChange={(e) => setEditText(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault()
                            repaint()
                          }
                        }}
                      />
                      <Button type="submit" variant="primary" disabled={!editText.trim() || editing}>
                        {editing ? 'Repainting… (~30 s)' : 'Repaint'}
                      </Button>
                      {editNote && <span className={styles.hint}>{editNote}</span>}
                    </form>
                  )}
                </div>
              </div>
              <footer className={styles.footer}>
                <Button href={drawLink}>Back</Button>
                <Button variant="primary" onClick={nextAct} disabled={saving === 'saving'}>
                  {saving === 'saving' ? 'Saving…' : `Write act ${(save?.play?.act ?? 1) + 1} →`}
                </Button>
              </footer>
            </>
          )}

          {error && (
            <p className={styles.error} role="alert">
              {error}
            </p>
          )}
        </Panel>
      </main>
    </div>
  )
}

/** A small pixel eye; struck through when the layer is hidden. */
function EyeIcon({ open }: { open: boolean }) {
  return (
    <svg width="18" height="14" viewBox="0 0 9 7" shapeRendering="crispEdges" aria-hidden="true" fill="currentColor">
      <rect x="3" y="1" width="3" height="1" />
      <rect x="1" y="2" width="2" height="1" />
      <rect x="6" y="2" width="2" height="1" />
      <rect x="0" y="3" width="1" height="1" />
      <rect x="8" y="3" width="1" height="1" />
      <rect x="1" y="4" width="2" height="1" />
      <rect x="6" y="4" width="2" height="1" />
      <rect x="3" y="5" width="3" height="1" />
      {open ? (
        <rect x="4" y="3" width="1" height="1" />
      ) : (
        <path d="M0 6h1v1H0zM1 5h1v1H1zM7 1h1v1H7zM8 0h1v1H8zM2 4h1v1H2zM3 3h1v1H3zM5 3h1v1H5zM6 2h1v1H6zM4 3h1v1H4z" />
      )}
    </svg>
  )
}

/** A small pixel bin. */
function BinIcon() {
  return (
    <svg width="12" height="14" viewBox="0 0 6 7" shapeRendering="crispEdges" aria-hidden="true" fill="currentColor">
      <rect x="2" y="0" width="2" height="1" />
      <rect x="0" y="1" width="6" height="1" />
      <rect x="1" y="2" width="1" height="5" />
      <rect x="3" y="2" width="1" height="4" />
      <rect x="4" y="2" width="1" height="5" />
      <rect x="1" y="6" width="4" height="1" />
    </svg>
  )
}
