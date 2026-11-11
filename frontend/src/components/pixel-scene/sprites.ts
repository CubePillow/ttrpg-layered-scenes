// ---------- Characters. '.' is transparent; other characters map to a palette.
// Back row: sitting behind the fire, facing the camera, lit by the flames.

export const DRUID = [
  'a.a.....a.a.',
  '.aa.....aa..',
  '..a.....a..v',
  '...ggggg..vt',
  '..gGsssGg..t',
  '..gGsssGg..t',
  '...ggggg...t',
  '..ggggggg..t',
  '.gggggggggst',
  '.gGgggggGg.t',
  '.gGgggggGg.t',
  '.ggggggggg.t',
  '.GGGGGGGGG.t',
]
export const DRUID_PALETTE: Record<string, string> = {
  a: '#c8b48a', // antlers
  g: '#4a6a3c', // firelit green hood and robe
  G: '#2c3f27',
  s: '#d99a6a', // face
  t: '#6b4a2a', // staff
  v: '#7fcf62', // leaves
}

export const BARD = [
  '.......f....',
  '......ff....',
  '...hhhhf....',
  '..hhhhhhh...',
  '...ssss.....',
  '...ssss.....',
  '..cccccc....',
  '.cccccccc..k',
  '.ccLlllcc.k.',
  '.cLllllLck..',
  '.cLllllLc...',
  '..LllLcc....',
  '.cccccccc...',
  '.CCCCCCCC...',
]
export const BARD_PALETTE: Record<string, string> = {
  f: '#f2dc8a', // feather
  h: '#8a3340', // cap
  s: '#d99a6a',
  c: '#3f7a6a', // tunic
  C: '#24463d',
  l: '#c07a44', // lute
  L: '#7a4426',
  k: '#7a4426', // lute neck
}

// Front row: between the camera and the fire, so they are dark silhouettes
// with a firelit rim. Drawn facing right; mirrored when they sit on the right.

export const KNIGHT = [
  '.pp..........',
  'ppp..........',
  '.p####.......',
  '..#####......',
  '..####r......',
  '..####r......',
  '...###.......',
  '.######r.....',
  '##########...',
  '##########r..',
  '##########r..',
  '.#########r..',
  '.##########r.',
  '..#########r.',
  '...##..####..',
]

export const MAGE = [
  '......#.......',
  '.....##.......',
  '....###.......',
  '....###.......',
  '...####.......',
  '..########....',
  '....###r...o..',
  '....###r...#..',
  '...####r...#..',
  '..######r..#..',
  '..#######r.#..',
  '.########r.#..',
  '.#########r#..',
  '.##########r..',
  '..##..####.#..',
]
