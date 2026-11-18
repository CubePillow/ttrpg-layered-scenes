/** Plays the hero themes with the Web Audio API, so no sound files are needed. */
import type { HeroTheme } from './heroThemes'

const VOLUME = 0.5
const FADE_SECONDS = 0.1
const LOOK_AHEAD_SECONDS = 0.15
const SOFT_FADE_IN_SECONDS = 2
const MUTE_KEY = 'ttrpg-music-muted'

const NOTE_INDEX: Record<string, number> = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 }

/** 'A4' -> 440 Hz; a rest gives null */
export function noteFrequency(note: string) {
  const match = /^([A-G])([#b]?)(\d)$/.exec(note)
  if (!match) return null
  const accidental = match[2] === '#' ? 1 : match[2] === 'b' ? -1 : 0
  const midi = 12 * (Number(match[3]) + 1) + NOTE_INDEX[match[1]] + accidental
  return 440 * 2 ** ((midi - 69) / 12)
}

function tone(ctx: BaseAudioContext, out: AudioNode, wave: OscillatorType, hz: number, at: number, length: number, level: number) {
  const osc = ctx.createOscillator()
  const gain = ctx.createGain()
  osc.type = wave
  osc.frequency.value = hz
  gain.gain.setValueAtTime(0.0001, at)
  gain.gain.exponentialRampToValueAtTime(level, at + 0.012)
  gain.gain.exponentialRampToValueAtTime(0.0001, at + length)
  osc.connect(gain).connect(out)
  osc.start(at)
  osc.stop(at + length + 0.02)
}

function noise(ctx: BaseAudioContext, out: AudioNode, at: number, length: number, level: number, cutoff: number) {
  const samples = Math.ceil(ctx.sampleRate * length)
  const buffer = ctx.createBuffer(1, samples, ctx.sampleRate)
  const data = buffer.getChannelData(0)
  for (let i = 0; i < samples; i++) data[i] = Math.random() * 2 - 1
  const source = ctx.createBufferSource()
  const filter = ctx.createBiquadFilter()
  const gain = ctx.createGain()
  source.buffer = buffer
  filter.type = 'highpass'
  filter.frequency.value = cutoff
  gain.gain.setValueAtTime(level, at)
  gain.gain.exponentialRampToValueAtTime(0.0001, at + length)
  source.connect(filter).connect(gain).connect(out)
  source.start(at)
}

/** Schedules everything that sounds on one sixteenth note of the loop. */
export function scheduleStep(ctx: BaseAudioContext, out: AudioNode, theme: HeroTheme, step: number, at: number) {
  const sixteenth = 60 / theme.bpm / 4
  const melody = theme.melody.split(' ')
  const bassline = theme.bassline.split(' ')

  const lead = noteFrequency(melody[step % melody.length])
  if (lead) tone(ctx, out, theme.lead, lead, at, sixteenth * theme.ring, theme.lead === 'sine' || theme.lead === 'triangle' ? 0.5 : 0.22)

  if (step % 2 === 0) {
    const bass = noteFrequency(bassline[(step / 2) % bassline.length])
    if (bass) tone(ctx, out, theme.bass, bass, at, sixteenth * (theme.bassRing ?? 1.8), theme.bass === 'sawtooth' || theme.bass === 'square' ? 0.2 : 0.42)
  }

  const drum = theme.drums[step % theme.drums.length]
  if (drum === 'k') tone(ctx, out, 'sine', 90, at, 0.12, 0.6)
  if (drum === 's') noise(ctx, out, at, 0.12, 0.28, 1500)
  if (drum === 'h') noise(ctx, out, at, 0.04, 0.12, 6000)
}

function readMuted() {
  try {
    return localStorage.getItem(MUTE_KEY) === '1'
  } catch {
    return false
  }
}

let context: AudioContext | null = null
let master: GainNode | null = null
let timer: number | undefined
let muted = readMuted()
let playing: { theme: HeroTheme; bus: GainNode; step: number; next: number } | null = null

function fadeOut(bus: GainNode, ctx: AudioContext) {
  bus.gain.cancelScheduledValues(ctx.currentTime)
  bus.gain.setValueAtTime(bus.gain.value, ctx.currentTime)
  bus.gain.linearRampToValueAtTime(0, ctx.currentTime + FADE_SECONDS)
  window.setTimeout(() => bus.disconnect(), FADE_SECONDS * 1000 + 30)
}

function tick() {
  if (!context || !playing) return
  const sixteenth = 60 / playing.theme.bpm / 4
  // After the tab was in the background, carry on from now instead of catching up
  if (playing.next < context.currentTime) playing.next = context.currentTime + 0.05
  while (playing.next < context.currentTime + LOOK_AHEAD_SECONDS) {
    scheduleStep(context, playing.bus, playing.theme, playing.step, playing.next)
    playing.next += sixteenth
    playing.step += 1
  }
}

/** Only one tab or window plays at a time: starting music here silences the others. */
const otherTabs = typeof BroadcastChannel === 'undefined' ? null : new BroadcastChannel('ttrpg-music')

/** Fades out the current theme, then starts this one, so two themes never sound together.
 * Browsers only allow sound after the player has clicked something. */
export function playTheme(theme: HeroTheme) {
  if (playing?.theme === theme) return
  context ??= new AudioContext()
  if (!master) {
    master = context.createGain()
    master.gain.value = muted ? 0 : VOLUME
    master.connect(context.destination)
  }
  void context.resume()
  otherTabs?.postMessage('playing')
  const wait = playing ? FADE_SECONDS + 0.02 : 0.05
  if (playing) fadeOut(playing.bus, context)

  const bus = context.createGain()
  const start = context.currentTime + wait
  bus.gain.setValueAtTime(theme.soft === undefined ? 1 : 0, start)
  if (theme.soft !== undefined) bus.gain.linearRampToValueAtTime(theme.soft, start + SOFT_FADE_IN_SECONDS)
  bus.connect(master)
  playing = { theme, bus, step: 0, next: context.currentTime + wait }
  timer ??= window.setInterval(tick, 30)
  tick()
}

export function stopTheme() {
  window.clearInterval(timer)
  timer = undefined
  if (context && playing) fadeOut(playing.bus, context)
  playing = null
}

if (otherTabs) otherTabs.onmessage = () => stopTheme()

// A page opened by a link may not make sound until the player clicks or presses a key on it
for (const event of ['pointerdown', 'keydown']) {
  window.addEventListener(event, () => {
    if (playing && context?.state === 'suspended' && !document.hidden) void context.resume()
  })
}

// No music from a tab nobody is looking at
document.addEventListener('visibilitychange', () => {
  if (!context || !playing) return
  void (document.hidden ? context.suspend() : context.resume())
})

// While developing: a code reload must not leave the old player running next to the new one
import.meta.hot?.dispose(() => {
  stopTheme()
  otherTabs?.close()
  void context?.close()
})

export const isMusicMuted = () => muted

export function setMusicMuted(value: boolean) {
  muted = value
  if (context && master) master.gain.setTargetAtTime(muted ? 0 : VOLUME, context.currentTime, 0.03)
  try {
    localStorage.setItem(MUTE_KEY, muted ? '1' : '0')
  } catch {
    // The choice just lasts until the page closes
  }
}
