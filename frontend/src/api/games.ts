/** Saves a game and the hero each player chose on the backend (backend/games.py). */
import type { ArtStyleId } from '../data/artStyles'
import type { Hero } from '../data/heroes'

/** Creates the game, or updates it when it already has an id. Returns the id of the saved game. */
export async function saveGame(id: string | null, title: string, style: ArtStyleId, heroes: Hero[]) {
  const response = await fetch(id ? `/api/games/${id}` : '/api/games', {
    method: id ? 'PUT' : 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title,
      mode: 'local',
      style,
      players: heroes.map((hero, i) => ({ seat: i + 1, name: hero.name, class_id: hero.classId, color: hero.color })),
    }),
  })
  if (!response.ok) throw new Error(`Saving failed (${response.status})`)
  const game: { id: string } = await response.json()
  return game.id
}
