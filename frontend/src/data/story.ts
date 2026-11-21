/**
 * The shared story text: one field everyone writes in, kept as pieces that each remember who wrote them,
 * so the text can be shown in that hero's colour.
 */

export type StoryPiece = { heroId: string; text: string }

export const storyText = (pieces: StoryPiece[]) => pieces.map((p) => p.text).join('')

/** Joins neighbouring pieces by the same hero and drops empty ones. */
function tidy(pieces: StoryPiece[]): StoryPiece[] {
  const out: StoryPiece[] = []
  for (const piece of pieces) {
    if (!piece.text) continue
    const last = out[out.length - 1]
    if (last && last.heroId === piece.heroId) last.text += piece.text
    else out.push({ ...piece })
  }
  return out
}

/**
 * Applies an edit of the whole text. Only the part that changed is new: it is removed from the old pieces,
 * and what was typed in its place goes to `heroId`.
 */
export function editStory(pieces: StoryPiece[], next: string, heroId: string): StoryPiece[] {
  const old = storyText(pieces)
  let start = 0
  while (start < old.length && start < next.length && old[start] === next[start]) start++
  let end = 0
  while (end < old.length - start && end < next.length - start && old[old.length - 1 - end] === next[next.length - 1 - end]) end++

  const removedTo = old.length - end
  const before: StoryPiece[] = []
  const after: StoryPiece[] = []
  let at = 0
  for (const piece of pieces) {
    const from = at
    at += piece.text.length
    if (from < start) before.push({ heroId: piece.heroId, text: piece.text.slice(0, start - from) })
    if (at > removedTo) after.push({ heroId: piece.heroId, text: piece.text.slice(Math.max(0, removedTo - from)) })
  }
  return tidy([...before, { heroId, text: next.slice(start, next.length - end) }, ...after])
}

const words = typeof Intl !== 'undefined' && 'Segmenter' in Intl ? new Intl.Segmenter(undefined, { granularity: 'word' }) : null

/** How many words each hero has written. Chinese and other text without spaces is counted by its words too. */
export function wordsByHero(pieces: StoryPiece[]): Record<string, number> {
  const counts: Record<string, number> = {}
  for (const piece of pieces) {
    const n = words
      ? [...words.segment(piece.text)].filter((s) => s.isWordLike).length
      : piece.text.split(/\s+/).filter(Boolean).length
    counts[piece.heroId] = (counts[piece.heroId] ?? 0) + n
  }
  return counts
}
