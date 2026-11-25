/**
 * Turns the newest part of the story into a prompt for the picture model.
 * SDXL-Turbo only reads about 75 tokens, so the prompt keeps to the look and the passage's last words.
 */
import type { StoryPiece } from './story'

/**
 * Every picture is drawn in one plain look that splits cleanly into layers: a flat vector look with
 * simple shapes, large colour blocks and few details.
 * The chosen art style (pixel, ...) is put on afterwards, for example by the pixel filter (backend/pixelize.py).
 */
const BASE_LOOK = 'flat colour vector illustration, simple shapes, large colour blocks, few details'

const PASSAGE_WORDS = 40

/** What the picture should show: the text written since `from`, or the end of the story if nothing is new. */
export function scenePrompt(pieces: StoryPiece[], from: number) {
  const text = pieces.map((p) => p.text).join('')
  const passage = (text.slice(from).trim() || text.slice(-400)).replace(/\s+/g, ' ')
  const words = passage.split(' ')
  const shortPassage = words.length > PASSAGE_WORDS ? words.slice(-PASSAGE_WORDS).join(' ') : passage
  return [BASE_LOOK, shortPassage].filter(Boolean).join('. ')
}
