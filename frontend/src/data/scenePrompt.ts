/**
 * Turns the newest part of the story into a prompt for the picture model.
 * SDXL-Turbo only reads about 75 tokens, so the prompt keeps to the style, the heroes in the passage, and the passage's last words.
 */
import type { ArtStyleId } from './artStyles'
import { HERO_COLORS, heroClass, type Hero } from './heroes'
import type { StoryPiece } from './story'

const STYLE_WORDS: Record<ArtStyleId, string> = {
  cartoon: 'cartoon illustration, flat colours, clean outlines',
  pixel: 'pixel art, retro game scene',
  paper_cutout: 'paper cut-out illustration, pastel layered paper',
  comic: 'comic book panel, bold ink, hard shadows',
}

const PASSAGE_WORDS = 40

const colourName = (hero: Hero) => (HERO_COLORS.find((c) => c.value === hero.color)?.label ?? '').toLowerCase()

/** What the picture should show: the text written since `from`, or the end of the story if nothing is new. */
export function scenePrompt(pieces: StoryPiece[], from: number, style: ArtStyleId, party: Hero[]) {
  const text = pieces.map((p) => p.text).join('')
  const passage = (text.slice(from).trim() || text.slice(-400)).replace(/\s+/g, ' ')

  // The heroes who wrote this passage or are named in it
  let at = 0
  const writers = new Set<string>()
  for (const piece of pieces) {
    if (at + piece.text.length > from && piece.text.trim()) writers.add(piece.heroId)
    at += piece.text.length
  }
  const inScene = party.filter((h) => writers.has(h.id) || passage.toLowerCase().includes(h.name.toLowerCase()))
  const heroes = inScene.map((h) => `${h.name} the ${colourName(h)} ${heroClass(h).name.toLowerCase()}`.replace(/\s+/g, ' '))

  const words = passage.split(' ')
  const shortPassage = words.length > PASSAGE_WORDS ? words.slice(-PASSAGE_WORDS).join(' ') : passage

  return [STYLE_WORDS[style], heroes.join(', '), shortPassage].filter(Boolean).join('. ')
}
