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

/** Play: the shared story text and the acts drawn from it. Pictures go in by id, never as image data. */
/** A drawn act: its part of the story text, the prompt the picture was made from, and the picture's id. */
export type ActSave = { number: number; from: number; to: number; prompt: string; pictureId: string }

/** Where the act being played stands: still being written, or drawn */
export type ActState = 'writing' | 'drawn'

export type PlaySave = {
  /** The act being played, from 1 */
  act?: number
  /** Kept for saves from before acts */
  scene?: number
  actState?: ActState
  story?: StoryPiece[]
  acts?: ActSave[]
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
