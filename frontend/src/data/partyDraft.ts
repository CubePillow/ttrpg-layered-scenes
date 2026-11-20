/** Party setups saved with the Save button. The backend keeps them (backend/party_draft.py), so any browser can continue one. */
import type { ArtStyleId } from './artStyles'
import type { Hero } from './heroes'

export type PartyDraft = {
  step: number
  title: string
  count: number
  party: Hero[]
  style: ArtStyleId
  gameId: string | null
}

/** What the list of saves shows about each one. */
export type DraftSummary = {
  id: string
  saved_at: string
  title: string
  step: number
  style: ArtStyleId | null
  players: number
  heroes: Pick<Hero, 'name' | 'classId' | 'color'>[]
}

const URL = '/api/party-drafts'

/** All saves, newest first; empty when the backend cannot be reached. */
export async function listDrafts(): Promise<DraftSummary[]> {
  try {
    const response = await fetch(URL)
    return response.ok ? await response.json() : []
  } catch {
    return []
  }
}

/** One save, or null when it is gone or the backend cannot be reached. */
export async function loadDraft(id: string): Promise<PartyDraft | null> {
  try {
    const response = await fetch(`${URL}/${encodeURIComponent(id)}`)
    if (!response.ok) return null
    const draft = (await response.json()) as PartyDraft
    return typeof draft.step === 'number' && Array.isArray(draft.party) ? draft : null
  } catch {
    return null
  }
}

/** Saves over the save with this id, or makes a new save. Returns the id of the save. */
export async function storeDraft(id: string | null, draft: PartyDraft): Promise<string> {
  const response = await fetch(id ? `${URL}/${encodeURIComponent(id)}` : URL, {
    method: id ? 'PUT' : 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(draft),
  })
  if (!response.ok) throw new Error(`Saving failed (${response.status})`)
  return id ?? ((await response.json()) as { id: string }).id
}

export async function deleteDraft(id: string) {
  const response = await fetch(`${URL}/${encodeURIComponent(id)}`, { method: 'DELETE' })
  if (!response.ok) throw new Error(`Deleting failed (${response.status})`)
}
