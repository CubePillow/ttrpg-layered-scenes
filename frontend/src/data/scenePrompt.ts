/**
 * Turns the act's text into a prompt for the picture model.
 * SDXL-Turbo only reads about 75 tokens, so the prompt keeps to the look and the passage's last words.
 */
import type { StoryPiece } from './story'

/**
 * Every picture is drawn in one plain look that splits cleanly into layers: a flat vector look with
 * simple shapes, large colour blocks and few details. Players do not change it.
 * The chosen art style (pixel, ...) is put on afterwards, for example by the pixel filter (backend/pixelize.py).
 */
export const BASE_LOOK = 'flat colour vector illustration, simple shapes, large colour blocks, few details'

const PASSAGE_WORDS = 40

/** The look, the act's last words, then any repaints ("tree: autumn leaves") */
export function promptFor(actText: string, extras: string[] = []) {
  const words = actText.trim().split(/\s+/).filter(Boolean)
  const passage = words.slice(-PASSAGE_WORDS).join(' ')
  return [passage ? `${BASE_LOOK}. ${passage}` : BASE_LOOK, ...extras].join(', ')
}

/** What the picture should show: the text written since `from`, or the end of the story if nothing is new. */
export function scenePrompt(pieces: StoryPiece[], from: number) {
  const text = pieces.map((p) => p.text).join('')
  return promptFor(text.slice(from).trim() || text.slice(-400))
}
