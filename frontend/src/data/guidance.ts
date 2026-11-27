/**
 * The hints on the shared screen that tell the players what to do at each step (issue #15).
 * All texts are kept here, so the wording can be changed in one place.
 * Keep each hint to one short sentence: it is read aloud at the table, not studied.
 */
export const GUIDANCE = {
  setup: [
    'Sitting around one screen? Choose Local.',
    'Agree on a name for your story together.',
    'Count everyone at the table who will write.',
    'Pass the laptop around: each player picks a hero and a colour.',
    'Choose one look together: every picture of your story uses it.',
    'All set? Begin the adventure together.',
  ],
  story: {
    empty:
      'Gamemaster, set the mood. Players, pick your hero and write what happens next.',
    written:
      'Keep adding to the act together. When it feels complete, press Draw this scene.',
  },
  draw: {
    ready: 'Read the act once more together, then draw 3 versions.',
    drawing: 'The painter is at work. This takes a few seconds.',
    choose: 'Vote: which picture fits your story best? Click it to use it.',
  },
  layers: {
    name: 'Name the objects you want to move, from back to front, then split.',
    splitting: 'Cutting the picture into objects. This takes about a minute.',
    arrange:
      'Take turns: move, hide or repaint objects until the scene fits your story.',
  },
} as const
