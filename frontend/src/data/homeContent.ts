/** Text content of the home page */

/** How the layer buttons are grouped */
export const LAYER_GROUPS = [
  { id: 'scenery', label: 'Scenery' },
  { id: 'party', label: 'Party' },
] as const

export const STEPS = [
  {
    title: 'Describe together',
    text: 'Everyone at the table adds words, a sketch or an idea. All of it is combined into one scene.',
  },
  {
    title: 'Split into layers',
    text: 'The scene is broken into layers, each with its own short prompt. Drag, resize and rotate them to say where things are.',
  },
  {
    title: 'Pick a version',
    text: 'The AI draws several versions of the scene. The group compares them and picks the one to keep.',
  },
  {
    title: 'Play on',
    text: 'When the story moves on, only the layers it affects change. Every phase stays in a timeline you can go back to.',
  },
]
