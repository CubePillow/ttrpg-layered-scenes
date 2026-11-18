/** Heroes for the party setup screen: classes, sprites, colours and random names. */

export const MAX_PARTY = 6

export const HERO_COLORS = [
  { value: '#d9534f', label: 'Crimson' },
  { value: '#ff9a3c', label: 'Ember' },
  { value: '#e3c34f', label: 'Gold' },
  { value: '#5fae57', label: 'Moss' },
  { value: '#3fa7a0', label: 'Teal' },
  { value: '#4f7fd9', label: 'Sapphire' },
  { value: '#9a68d8', label: 'Amethyst' },
  { value: '#d868a8', label: 'Rose' },
]

/*
 * Sprites are drawn in layers on an 18 x 21 grid: the shared body, then the class on top.
 * '.' keeps what is underneath. An outline is added automatically.
 * c C: the player's colour and its shadow. s S: skin. h: hair. e: eyes. p P: trousers. B: boots.
 * m M: metal. f: white. g: gold. w W: wood. b: leather. r: magic. v: leaves. a: antler.
 */
const BODY = [
  '',
  '',
  '',
  '......hhhhhh',
  '.....hhhhhhhh',
  '.....hssssssh',
  '.....ssessess',
  '.....ssssssss',
  '......ssSSss',
  '.....cccccccc',
  '....ccCccccCcc',
  '....ccCccccCcc',
  '....ssCccccCss',
  '....ssbbbgbbbss',
  '......cccCcc',
  '......ppp.ppp',
  '......ppp.ppp',
  '......ppP.ppP',
  '......PPP.PPP',
  '.....BBBB.BBBB',
  '.....BBBB.BBBB',
]

export type HeroClass = {
  id: string
  name: string
  /** What the class does for the party */
  role: 'Frontline' | 'Scout' | 'Caster' | 'Support'
  motto: string
  gear: string[]
}

export const HERO_CLASSES: HeroClass[] = [
  {
    id: 'fighter',
    name: 'Fighter',
    role: 'Frontline',
    motto: 'First in, last out.',
    gear: [
      '..............f',
      '..............fm',
      '......mmmmmm..fm',
      '.....mmmmmmmm.fm',
      '.....mfmmmmMm.fm',
      '.....mMMMMMMm.fm',
      '..............fm',
      '..............fm',
      '.............gggg',
      '.....mmmmmmmm.bb',
      'gggggmfmmmmMmMss',
      'gcCcg.mfmmMm.Mss',
      'gcgcg.mmmmMm..ss',
      'gcgcg',
      '.gcg',
      '..g',
    ],
  },
  {
    id: 'wizard',
    name: 'Wizard',
    role: 'Caster',
    motto: 'Knowledge is a loaded spell.',
    gear: [
      '........cc.....r',
      '.......cccc...rfr',
      '......ccCccc...r',
      '....gggggggggg.w',
      '.....ffffffff..w',
      '.....ffssssff..w',
      '.....f......f..w',
      '.....ffffffff..w',
      '......ffffff...w',
      '.....ccffffcc..w',
      '....ccCfffCccssw',
      '....ccCcccCcc..w',
      '....ssCcccCcs..w',
      '.....ccgggcc...w',
      '.....cCccccCc..w',
      '.....cCccccCc..w',
      '.....cCccccCc..w',
      '.....cCccccCc..w',
      '....ccCccccCcc.w',
      '....ccCccccCcc.w',
      '.....BBB..BBB..w',
    ],
  },
  {
    id: 'rogue',
    name: 'Rogue',
    role: 'Scout',
    motto: 'You never saw me.',
    gear: [
      '',
      '',
      '......cccccc',
      '.....cccccccc',
      '....ccCCCCCCcc',
      '....cCssssssCc',
      '....cC......Cc',
      '....cCMMMMMMCc',
      '.....cCMMMMCc',
      '....ccCCCCCCcc',
      '...ccCbcccbCcc',
      '...ccCcbcbcCcc',
      '..ggss......ssgg',
      '...m..........m',
      '...m..........m',
      '...f..........f',
    ],
  },
  {
    id: 'cleric',
    name: 'Cleric',
    role: 'Support',
    motto: 'Faith mends what steel breaks.',
    gear: [
      '',
      '',
      '',
      '',
      '.....gggrgggg',
      '',
      '.............m.m',
      '.............mmm',
      '.............m.m',
      '.....ffffffff.w',
      '....ffcggcffffw',
      '....ffcggcffffw',
      '....ssfcgcfsssw',
      '.....ffcccff..w',
      '.....ffcCcfff',
      '.....ffcCcfff',
      '.....ffcCcfff',
      '.....ffcCcfff',
      '....fffcCcffff',
      '....fffcCcffff',
      '.....BBB..BBB',
    ],
  },
  {
    id: 'ranger',
    name: 'Ranger',
    role: 'Scout',
    motto: 'The wild keeps its own road.',
    gear: [
      '',
      '',
      '',
      '..wf..cccccc',
      '.w.f.cccccccc.g',
      '.w.fCCCCCCCCCC',
      'w..f',
      'w..f.........fgf',
      'w..f.........bbb',
      'w..f.bccccccbbbb',
      'w..f.........bbb',
      'w..f',
      'w..fss',
      'w..f',
      'w..f',
      '.w.f',
      '.w.f',
      '..wf',
    ],
  },
  {
    id: 'bard',
    name: 'Bard',
    role: 'Support',
    motto: 'Every legend needs a singer.',
    gear: [
      '',
      '..........fr',
      '..........ggf',
      '.....cccccCgf',
      '....ccccccccCc',
      '',
      '',
      '',
      '................WW',
      '...............W',
      '..............W',
      '.............W',
      '.......wwwwwW',
      '......wwWWwww',
      '......wWWWWww',
      '.......wwwww',
    ],
  },
  {
    id: 'barbarian',
    name: 'Barbarian',
    role: 'Frontline',
    motto: 'Plans are for the patient.',
    gear: [
      '',
      '',
      '....ff......ffmwmm',
      '.....fmmmmmmfmmwmm',
      '.....mmmmmmmmmmwmm',
      '.....hMMMMMMh.mwmm',
      '...............w',
      '.....hssssssh..w',
      '......hhhhhh...w',
      '.....ssssssss..w',
      '....sssSssSsss.w',
      '....sssSssSsss.w',
      '....ssSssssSsssw',
      '....ssccccccss.w',
      '......cCcCcC...w',
      '...............w',
      '...............w',
    ],
  },
  {
    id: 'druid',
    name: 'Druid',
    role: 'Support',
    motto: 'The forest remembers.',
    gear: [
      '....a........a.vv',
      '....aa......aa.vv',
      '.....aa....aa.wv',
      '......cccccc..w',
      '.....cccccccc.w',
      '.....cssssssc.w',
      '.....c......c.w',
      '.....cssssssc.w',
      '..............w',
      '.....cCccccCc.w',
      '....ccCccccCccw',
      '....ccCccccCccw',
      '....ssCccccCssw',
      '.....vvvvvvvv.w',
      '.....cCccccCc.w',
      '.....cCccccCc.w',
      '.....cCccccCc.w',
      '.....cCccccCc.w',
      '.....cCccccCc.w',
      '....ccCccccCccw',
      '.....BBB..BBB.w',
    ],
  },
  {
    id: 'monk',
    name: 'Monk',
    role: 'Scout',
    motto: 'Stillness strikes hardest.',
    gear: [
      '',
      '',
      '',
      '......ssssss',
      '.....ssssssss',
      '.....ssssssss',
      '',
      '',
      '',
      '.....cCffffCc',
      '....ssCffffCss',
      '....ssCffffCss',
      '....ffCffffCff',
      '....ffccccccff',
      '......ffffff',
      '......fff.fff',
      '......fff.fff',
      '......fff.fff',
      '......fff.fff',
    ],
  },
  {
    id: 'paladin',
    name: 'Paladin',
    role: 'Frontline',
    motto: 'An oath is the sharpest blade.',
    gear: [
      '',
      '',
      '......gggggg',
      '.....mmmmmmmm',
      '.....mgmmmmgm',
      '.....mMMMMMMm.mmm',
      '..............mmm',
      '...............w',
      '...............w',
      '.....gmmmmmmg..w',
      'ffffgmmggmmMg.sw',
      'fgcfgmmggmMMg.sw',
      'fggfssmmmmMm.ssw',
      'fcgf...........w',
      '.ff............w',
    ],
  },
  {
    id: 'sorcerer',
    name: 'Sorcerer',
    role: 'Caster',
    motto: 'Magic runs in the blood.',
    gear: [
      '',
      '',
      '.....r..hh..r',
      '.....hhrhhrhh',
      '....hhhhhhhhhh',
      '',
      '',
      '',
      '',
      '.....cCccccCc',
      '..r.ccCccccCcc.r',
      '.rfrccCccccCccrfr',
      '..r.ss.cccc.ss.r',
      '.....ccgggcc',
      '.....cCccccCc',
      '.....cCccccCc',
      '.....cCccccCc',
      '.....cCccccCc',
      '....ccCccccCcc',
      '....ccCccccCcc',
      '.....BBB..BBB',
    ],
  },
  {
    id: 'warlock',
    name: 'Warlock',
    role: 'Caster',
    motto: 'Every gift has its price.',
    gear: [
      '',
      '',
      '......PPPPPP',
      '.....PPPPPPPP',
      '....PPppppppPP',
      '....PpssssssPp',
      '....Pp......pP',
      '....PpssssssPp',
      '.....PPSSSSPP',
      '.....PcPPPPcP',
      '....PPcPPPPcPP',
      '..r.PPcPPPPcPP',
      '.rfrssPPPPPPssbbb',
      '..r..PPgggPP..bbb',
      '.....PcPPPPcP',
      '.....PcPPPPcP',
      '.....PcPPPPcP',
      '.....PcPPPPcP',
      '.....PcPPPPcP',
      '....PPcPPPPcPP',
      '.....BBB..BBB',
    ],
  },
]

const WIDTH = 18
const HEIGHT = 21
const OUTLINE = '#120d1c'

function mix(hex: string, target: number, amount: number) {
  const channels = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))
  const mixed = channels.map((c) => Math.round(c + (target - c) * amount))
  return `#${mixed.map((c) => c.toString(16).padStart(2, '0')).join('')}`
}

/** The hero as rows of colours (null = transparent), with a dark outline around it. */
export function heroPixels(classId: string, color: string): (string | null)[][] {
  const palette: Record<string, string> = {
    c: color,
    C: mix(color, 0, 0.35),
    s: '#e0a878',
    S: '#b97f58',
    h: '#5b3a29',
    e: '#17111f',
    p: '#4b3d6b',
    P: '#3a2e57',
    B: '#3b2a24',
    m: '#a9b2c4',
    M: '#68708a',
    f: '#f4efe0',
    g: '#e8bd4f',
    w: '#7a4e33',
    W: '#553323',
    b: '#6b4a2a',
    r: '#7fe0ff',
    v: '#7fcf62',
    a: '#c8b48a',
  }
  const gear = HERO_CLASSES.find((c) => c.id === classId)?.gear ?? []
  // One empty row and column on every side leaves room for the outline
  const grid: (string | null)[][] = Array.from({ length: HEIGHT + 2 }, () => Array(WIDTH + 2).fill(null))
  for (const layer of [BODY, gear]) {
    layer.forEach((row, y) => {
      ;[...row].forEach((ch, x) => {
        if (palette[ch]) grid[y + 1][x + 1] = palette[ch]
      })
    })
  }
  return grid.map((row, y) =>
    row.map((cell, x) => {
      if (cell) return cell
      const touches = [grid[y - 1]?.[x], grid[y + 1]?.[x], row[x - 1], row[x + 1]].some(Boolean)
      return touches ? OUTLINE : null
    }),
  )
}

export type Hero = {
  id: string
  classId: string
  name: string
  color: string
}

export function heroClass(hero: Pick<Hero, 'classId'>) {
  return HERO_CLASSES.find((c) => c.id === hero.classId) ?? HERO_CLASSES[0]
}

const pick = <T,>(items: readonly T[]) => items[Math.floor(Math.random() * items.length)]

/** Name parts per class, so that a wizard and a barbarian sound different. */
const NAME_PARTS: Record<string, { start: string[]; end: string[] }> = {
  fighter: { start: ['Bran', 'Cas', 'Dov', 'Gar', 'Hal', 'Mar', 'Rol', 'Ty'], end: ['den', 'ek', 'mund', 'on', 'ran', 'ric'] },
  wizard: { start: ['Aldr', 'Eld', 'Ith', 'Mer', 'Oph', 'Quor', 'Thal', 'Zeph'], end: ['andor', 'azar', 'eon', 'imus', 'ion', 'ius'] },
  rogue: { start: ['Dax', 'Jax', 'Kit', 'Nix', 'Ren', 'Shae', 'Sly', 'Ves'], end: ['a', 'ette', 'ey', 'ik', 'in', 'o'] },
  cleric: { start: ['Ama', 'Aur', 'Ben', 'Cel', 'Luc', 'Ori', 'Ser', 'Sol'], end: ['ael', 'ara', 'elle', 'ena', 'iel', 'ius'] },
  ranger: { start: ['Ash', 'Bri', 'Hale', 'Lark', 'Row', 'Tam', 'Thorn', 'Wren'], end: ['dal', 'ett', 'ley', 'lin', 'wick', 'wyn'] },
  bard: { start: ['Cad', 'Dan', 'Fel', 'Jas', 'Lir', 'Mel', 'Pip', 'Tal'], end: ['ando', 'enza', 'io', 'lyn', 'per', 'ric'] },
  barbarian: { start: ['Bor', 'Grom', 'Hrod', 'Krag', 'Ragn', 'Skar', 'Thok', 'Urg'], end: ['ak', 'gar', 'grim', 'nar', 'rok', 'ulf'] },
  druid: { start: ['Bryn', 'Elm', 'Fern', 'Lor', 'Moss', 'Oak', 'Sylv', 'Wil'], end: ['ael', 'ara', 'dra', 'leaf', 'thorn', 'wyn'] },
  monk: { start: ['Ansa', 'Ilo', 'Kai', 'Nao', 'Oren', 'Sen', 'Tem', 'Vey'], end: ['en', 'ko', 'ma', 'ra', 'ri', 'shi'] },
  paladin: { start: ['Aer', 'Alar', 'Ced', 'Gal', 'Leon', 'Perc', 'Rein', 'Theo'], end: ['ard', 'hard', 'ius', 'mont', 'ric', 'wald'] },
  sorcerer: { start: ['Ky', 'Lyx', 'Nyra', 'Ryn', 'Sera', 'Vael', 'Xan', 'Zar'], end: ['ara', 'iel', 'ith', 'ix', 'ora', 'ys'] },
  warlock: { start: ['Bel', 'Drav', 'Hex', 'Mal', 'Mor', 'Nyx', 'Vor', 'Zul'], end: ['ath', 'azar', 'ek', 'gath', 'ius', 'oth'] },
}

/** A name that suits the class and is not in `taken`. */
export function randomName(classId: string, taken: string[] = []) {
  const parts = NAME_PARTS[classId] ?? NAME_PARTS.fighter
  const used = new Set(taken.map((name) => name.toLowerCase()))
  const options = parts.start.flatMap((start) =>
    parts.end
      // Skip joins such as "Nyra" + "ara", where the same letter meets itself
      .filter((end) => start.at(-1)?.toLowerCase() !== end[0])
      .map((end) => start + end)
      .filter((name) => !used.has(name.toLowerCase())),
  )
  return options.length ? pick(options) : pick(parts.start)
}

const TITLE_ADJECTIVE = ['Ashen', 'Broken', 'Drowned', 'Forgotten', 'Hollow', 'Last', 'Moonlit', 'Shattered', 'Silent', 'Sunken', 'Whispering', 'Winter']
const TITLE_NOUN = ['Banner', 'Citadel', 'Crown', 'Dragon', 'Harbour', 'King', 'Lantern', 'Oath', 'Road', 'Throne', 'Tower', 'Vale']
export const randomTitle = () => `The ${pick(TITLE_ADJECTIVE)} ${pick(TITLE_NOUN)}`

/** A new hero whose class and colour are not taken yet, when that is possible. */
export function newHero(party: Hero[]): Hero {
  const freeClasses = HERO_CLASSES.filter((c) => !party.some((h) => h.classId === c.id))
  const freeColors = HERO_COLORS.filter((c) => !party.some((h) => h.color === c.value))
  const classId = pick(freeClasses.length ? freeClasses : HERO_CLASSES).id
  return {
    id: crypto.randomUUID(),
    classId,
    color: pick(freeColors.length ? freeColors : HERO_COLORS).value,
    name: randomName(classId, party.map((hero) => hero.name)),
  }
}
