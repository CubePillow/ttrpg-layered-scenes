export type LayerId =
  | 'sky'
  | 'mountains'
  | 'tower'
  | 'forest'
  | 'campfire'
  | 'druid'
  | 'bard'
  | 'knight'
  | 'mage'
  | 'foreground'

export type SceneLayer = {
  id: LayerId
  label: string
  /** 'scenery' for places and things, 'party' for the characters */
  group: 'scenery' | 'party'
  /** The short per-layer prompt this layer would be generated from */
  prompt: string
}

/** Back to front, the order the layers are drawn in */
export const SCENE_LAYERS: SceneLayer[] = [
  { id: 'sky', label: 'Sky', group: 'scenery', prompt: 'starry dusk sky, full moon' },
  { id: 'mountains', label: 'Mountains', group: 'scenery', prompt: 'distant snowy mountains' },
  {
    id: 'tower',
    label: 'Tower',
    group: 'scenery',
    prompt: 'lonely stone tower on a hill, lit window',
  },
  { id: 'forest', label: 'Forest', group: 'scenery', prompt: 'dark pine forest, fireflies' },
  {
    id: 'campfire',
    label: 'Campfire',
    group: 'scenery',
    prompt: 'crackling campfire on a forest clearing, warm glow',
  },
  {
    id: 'druid',
    label: 'Druid',
    group: 'party',
    prompt: 'druid with an antler hood and a leafy staff, behind the fire',
  },
  {
    id: 'bard',
    label: 'Bard',
    group: 'party',
    prompt: 'bard with a feathered cap playing a lute, behind the fire',
  },
  {
    id: 'knight',
    label: 'Knight',
    group: 'party',
    prompt: 'knight with a plumed helmet and shield, seen from behind, left of the fire',
  },
  {
    id: 'mage',
    label: 'Mage',
    group: 'party',
    prompt: 'mage in a pointed hat with a glowing staff, seen from behind, right of the fire',
  },
  {
    id: 'foreground',
    label: 'Foreground',
    group: 'scenery',
    prompt: 'dark ferns and drifting embers close to the camera',
  },
]
