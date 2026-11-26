/**
 * Saved stories, kept by the backend (backend/saves.py) so any browser can load them.
 * One save is one story, in layers: the party setup first, then play, which later parts of the game fill in.
 */
import type { ArtStyleId } from './artStyles'
import type { Hero } from './heroes'
import type { StoryPiece } from './story'

export const SAVE_VERSION = 2

export type SavePhase = 'setup' | 'playing' | 'ended'

/** Everything chosen while setting up the party. It is saved on the last step, so loading it opens that step. */
export type SetupSave = {
  title: string
  count: number
  party: Hero[]
  style: ArtStyleId
  gameId: string | null
}

/** Play: the shared story text, the act being played, and the acts drawn so far. */

/** One split layer of a drawn act: how far it was moved (shares of the picture) and resized from where it was cut. */
export type LayerSave = {
  name: string
  pictureId: string
  dx: number
  dy: number
  scale: number
  hidden: boolean
  /** The repaint instructions this layer went through, oldest first */
  edits?: string[]
  /** On the background only: the layers deleted from this act, which the act's text and prompt mention as removed */
  removed?: string[]
}

/** A drawn act. Pictures are kept on the backend and held here by id; the pixel look is made again when shown. */
export type ActSave = {
  number: number
  /** The act's part of the story text, as character positions */
  from: number
  to: number
  prompt: string
  seed: number
  pictureId: string
  layers: LayerSave[]
}

/** Where an act's text starts: right after the text of the acts before it. */
export const actStart = (play: PlaySave | null | undefined, number: number) =>
  Math.max(0, ...(play?.acts ?? []).filter((a) => a.number < number).map((a) => a.to ?? 0))

/** Where the act being played stands: still being written, or drawn */
export type ActState = 'writing' | 'drawn'

export type PlaySave = {
  /** The act being played, from 1 */
  act?: number
  /** Kept for saves from before acts */
  scene?: number
  actState?: ActState
  /** The gamemaster's direction for the players' story contributions */
  gmDirection?: string
  story?: StoryPiece[]
  acts?: ActSave[]
  /** The picture prompt as last written on the drawing page, for the act being played */
  draft?: { act: number; prompt: string }
} & Record<string, unknown>

export type Save = {
  version: typeof SAVE_VERSION
  phase: SavePhase
  setup: SetupSave
  play: PlaySave | null
}

/** What the Load story page shows about each save. */
export type SaveSummary = {
  id: string
  saved_at: string
  title: string
  phase: SavePhase
  /** A few words on how far the story got, such as "Set off" or "Act 2 · Writing" */
  progress: string
  style: ArtStyleId | null
  heroes: Pick<Hero, 'name' | 'classId' | 'color'>[]
}

const URL = '/api/saves'

/** A save that is still in the party setup. */
export const setupSave = (setup: SetupSave): Save => ({ version: SAVE_VERSION, phase: 'setup', setup, play: null })

/** All saves, newest first; empty when the backend cannot be reached. */
export async function listSaves(): Promise<SaveSummary[]> {
  try {
    const response = await fetch(URL)
    return response.ok ? await response.json() : []
  } catch {
    return []
  }
}

/** One save, or null when it is gone or the backend cannot be reached. */
export async function loadSave(id: string): Promise<Save | null> {
  try {
    const response = await fetch(`${URL}/${encodeURIComponent(id)}`)
    if (!response.ok) return null
    const save = (await response.json()) as Save
    return save.version === SAVE_VERSION && Array.isArray(save.setup?.party) ? save : null
  } catch {
    return null
  }
}

/** Saves over the save with this id, or makes a new save. Returns the id of the save. */
export async function storeSave(id: string | null, save: Save): Promise<string> {
  const response = await fetch(id ? `${URL}/${encodeURIComponent(id)}` : URL, {
    method: id ? 'PUT' : 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(save),
  })
  if (!response.ok) throw new Error(`Saving failed (${response.status})`)
  return id ?? ((await response.json()) as { id: string }).id
}

export async function deleteSave(id: string) {
  const response = await fetch(`${URL}/${encodeURIComponent(id)}`, { method: 'DELETE' })
  if (!response.ok) throw new Error(`Deleting failed (${response.status})`)
}
