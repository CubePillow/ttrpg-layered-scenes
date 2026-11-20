/**
 * One short chiptune loop per hero class, written for this project.
 * Melody: 32 sixteenth notes. Bass: 16 eighth notes. Drums: 16 sixteenth notes, repeated.
 * Notes are written like A4 or Bb3; '.' is a rest. Drums: k kick, s snare, h hi-hat.
 */
export type HeroTheme = {
  title: string
  bpm: number
  lead: OscillatorType
  bass: OscillatorType
  /** How long a note rings, in sixteenth notes */
  ring: number
  /** How long a bass note rings; 1.8 when left out */
  bassRing?: number
  /** Loudness from 0 to 1, and a slow fade-in when it is set; for quiet background music */
  soft?: number
  melody: string
  bassline: string
  drums: string
}

/** The quiet music that plays through the game, except while a hero is being chosen. */
export const AMBIENT_THEME: HeroTheme = {
  title: 'Campfire Rest',
  bpm: 58,
  lead: 'sine',
  bass: 'sine',
  ring: 7,
  bassRing: 8,
  soft: 0.6,
  melody:
    'E4 . . . G4 . . . A4 . . . . . . . G4 . . . E4 . . . D4 . . . . . . . C4 . . . E4 . . . G4 . . . . . . . A4 . . . G4 . . . E4 . . . . . . .',
  bassline: 'C3 . . . G2 . . . A2 . . . E2 . . . F2 . . . C3 . . . G2 . . . G2 . . .',
  drums: '................',
}

export const HERO_THEMES: Record<string, HeroTheme> = {
  fighter: {
    title: 'Hold the Line',
    bpm: 126,
    lead: 'square',
    bass: 'triangle',
    ring: 1.4,
    melody: 'D5 . D5 F5 A5 . F5 . G5 . E5 . D5 . . . D5 . D5 F5 A5 . C6 . A5 . G5 . F5 . E5 .',
    bassline: 'D3 D3 A2 D3 Bb2 Bb2 C3 C3 D3 D3 A2 D3 F2 F2 A2 A2',
    drums: 'k.h.s.h.k.k.s.h.',
  },
  wizard: {
    title: 'The Arcane Study',
    bpm: 96,
    lead: 'triangle',
    bass: 'sine',
    ring: 2.2,
    melody: 'A4 C5 E5 A5 G#5 E5 C5 B4 A4 C5 E5 A5 B5 A5 G#5 E5 F4 A4 C5 F5 E5 C5 A4 G#4 E4 G#4 B4 E5 D5 B4 G#4 E4',
    bassline: 'A2 . E3 . A2 . E3 . F2 . C3 . E2 . B2 .',
    drums: '....h.......h...',
  },
  rogue: {
    title: 'Footsteps in the Dark',
    bpm: 112,
    lead: 'square',
    bass: 'triangle',
    ring: 0.7,
    melody: 'E4 . . G4 . . A4 . A#4 . B4 . . . . . E5 . D5 . B4 . A#4 . A4 . G4 . E4 . . .',
    bassline: 'E2 . E2 . G2 . A2 A#2 E2 . E2 . D2 . B1 .',
    drums: 'k...h.h.k.h...h.',
  },
  cleric: {
    title: 'Morning Hymn',
    bpm: 76,
    lead: 'triangle',
    bass: 'sine',
    ring: 3.6,
    melody: 'E5 . . . G5 . . . C6 . . . B5 . A5 . G5 . . . A5 . . . F5 . . . E5 . D5 .',
    bassline: 'C3 . G3 . A2 . E3 . F2 . C3 . G2 . G2 .',
    drums: '................',
  },
  ranger: {
    title: 'The Long Green Road',
    bpm: 118,
    lead: 'triangle',
    bass: 'triangle',
    ring: 1.5,
    melody: 'G4 . B4 D5 . B4 G5 . E5 . D5 B4 . A4 G4 . G4 . B4 D5 . G5 A5 . B5 . A5 G5 . E5 D5 .',
    bassline: 'G2 D3 G2 D3 C3 G3 D3 A2 G2 D3 G2 D3 C3 D3 G2 .',
    drums: 'k..h..s.k..h..s.',
  },
  bard: {
    title: 'A Round for the Tavern',
    bpm: 140,
    lead: 'square',
    bass: 'triangle',
    ring: 1.2,
    melody: 'C5 E5 G5 E5 C6 . G5 . A5 G5 F5 E5 D5 . G4 . C5 E5 G5 E5 C6 . E6 . D6 C6 B5 G5 C6 . . .',
    bassline: 'C3 G3 C3 G3 F2 C3 G2 D3 C3 G3 C3 G3 F2 G2 C3 .',
    drums: 'k.h.s.h.k.h.s.hh',
  },
  barbarian: {
    title: 'Blood and Thunder',
    bpm: 100,
    lead: 'sawtooth',
    bass: 'sawtooth',
    ring: 1.6,
    melody: 'E4 . E4 . G4 . E4 . A4 . G4 . E4 . D4 . E4 . E4 . B4 . A4 . G4 . A4 . E4 . . .',
    bassline: 'E2 E2 E2 G2 A2 A2 G2 D2 E2 E2 E2 B2 A2 G2 E2 E2',
    drums: 'k.k.s...k.k.s.ss',
  },
  druid: {
    title: 'Where the Moss Grows',
    bpm: 84,
    lead: 'sine',
    bass: 'triangle',
    ring: 2.8,
    melody: 'D5 . F#5 . A5 . . B5 A5 . F#5 . E5 . . . D5 . E5 . F#5 . A5 . B5 . D6 . B5 . A5 .',
    bassline: 'D3 . A3 . G2 . D3 . B2 . F#3 . A2 . E3 .',
    drums: '..h.....h..h....',
  },
  monk: {
    title: 'Still Water',
    bpm: 72,
    lead: 'triangle',
    bass: 'sine',
    ring: 3.2,
    melody: 'A4 . . . C5 . . D5 E5 . . . . . G5 . E5 . . . D5 . C5 . A4 . . . . . . .',
    bassline: 'A2 . . . E3 . . . D3 . . . E2 . . .',
    drums: 'k.......h.......',
  },
  paladin: {
    title: 'The Oath Unbroken',
    bpm: 120,
    lead: 'square',
    bass: 'triangle',
    ring: 1.8,
    melody: 'Bb4 . . D5 F5 . . Bb5 A5 . G5 . F5 . . . G5 . . A5 Bb5 . D6 . C6 . Bb5 . A5 . F5 .',
    bassline: 'Bb2 Bb2 F3 F3 Eb3 Eb3 F3 F3 G2 G2 D3 D3 Eb3 Eb3 F3 F3',
    drums: 'k.s.k.s.k.k.s.s.',
  },
  sorcerer: {
    title: 'Sparks in the Blood',
    bpm: 134,
    lead: 'sawtooth',
    bass: 'square',
    ring: 0.9,
    melody: 'C5 D5 E5 F#5 G#5 A#5 C6 . A#5 G#5 F#5 E5 D5 . C5 . E5 F#5 G#5 C6 D6 . C6 A#5 G#5 . F#5 . E5 D5 C5 .',
    bassline: 'C3 C3 E3 E3 F#2 F#2 G#2 A#2 C3 C3 E3 E3 G#2 G#2 A#2 A#2',
    drums: 'k.hhs.hhk.hhs.hs',
  },
  warlock: {
    title: 'The Price of Power',
    bpm: 80,
    lead: 'sawtooth',
    bass: 'sine',
    ring: 2.6,
    melody: 'B4 . . D5 . . F5 . E5 . . . C5 . . . B4 . . D5 . . G#5 . F5 . D5 . B4 . . .',
    bassline: 'B1 . . . F2 . . . C2 . . . B1 . F2 .',
    drums: 'k.....h.....s...',
  },
}
