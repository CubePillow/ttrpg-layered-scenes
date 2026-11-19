/** The picture styles a party can choose. The ids match ArtStyleId in backend/games.py. */
export type ArtStyleId = 'pixel' | 'cartoon' | 'paper_cutout' | 'comic'

export type ArtStyle = {
  id: ArtStyleId
  name: string
  description: string
}

export const DEFAULT_ART_STYLE: ArtStyleId = 'cartoon'
export const AVAILABLE_ART_STYLES: ArtStyleId[] = ['cartoon', 'pixel']

export const ART_STYLES: ArtStyle[] = [
  { id: 'cartoon', name: 'Cartoon', description: 'Simple flat colours' },
  { id: 'pixel', name: 'Pixel art', description: 'Crisp retro blocks' },
  { id: 'paper_cutout', name: 'Paper cut-out', description: 'Pastel shapes cut from paper' },
  { id: 'comic', name: 'Comic', description: 'Bold ink and hard shadows' },
]

export const artStyle = (id: ArtStyleId) => ART_STYLES.find((style) => style.id === id) ?? ART_STYLES[0]
