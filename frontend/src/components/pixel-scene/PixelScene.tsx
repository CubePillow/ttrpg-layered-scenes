import { useEffect, useRef } from 'react'
import { SCENE_LAYERS, type LayerId } from '../../data/sceneLayers'
import { COLORS, SKY } from './palette'
import { bayer, hash, noise } from './pixelMath'
import { BARD, BARD_PALETTE, DRUID, DRUID_PALETTE, KNIGHT, MAGE } from './sprites'

/**
 * An animated pixel-art night scene drawn on a low-resolution canvas and
 * scaled up with crisp pixels. It is built from the same layers listed in
 * SCENE_LAYERS. Each layer is drawn into its own buffer and moves with its
 * own parallax depth. Selecting a layer keeps it bright and dims the others.
 */

const H = 180 // internal pixel height; width follows the element's aspect ratio
const PAD = 6 // extra pixels around each layer buffer so parallax never shows an edge
const BOTTOM = H + PAD

type Spark = { x: number; y: number; vx: number; vy: number; life: number }
type Buffer = { c: HTMLCanvasElement; g: CanvasRenderingContext2D }

type Props = {
  highlight: LayerId | null
  className?: string
}

export default function PixelScene({ highlight, className }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const highlightRef = useRef<LayerId | null>(highlight)
  const redrawRef = useRef<() => void>(() => {})

  useEffect(() => {
    highlightRef.current = highlight
    redrawRef.current()
  }, [highlight])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    let W = 320
    let sky: HTMLCanvasElement | null = null
    let stars: { x: number; y: number; phase: number; speed: number; big: boolean }[] = []
    let buffers = {} as Record<LayerId, Buffer>
    const sparks: Spark[] = []
    const groundTop = new Map<number, number>()

    // Smoothed pointer position in [-1, 1]
    const pointer = { x: 0, y: 0, tx: 0, ty: 0, lastMove: -Infinity }

    /** The context currently being drawn into (one layer buffer at a time) */
    let g: CanvasRenderingContext2D = ctx

    const rect = (x: number, y: number, w: number, h: number, color: string) => {
      g.fillStyle = color
      g.fillRect(Math.round(x), Math.round(y), Math.round(w), Math.round(h))
    }

    const drawSprite = (
      rows: string[],
      x: number,
      bottom: number,
      mirror: boolean,
      palette: Record<string, string>,
      backlit?: { top: string; rim: string },
    ) => {
      // Sprites face right; mirrored ones face left. The fire is the way they face.
      const fireDx = mirror ? -1 : 1
      const top = bottom - rows.length
      const at = (rx: number, ry: number) => {
        const row = rows[ry]
        if (!row || rx < 0 || rx >= row.length) return '.'
        return row[mirror ? row.length - 1 - rx : rx]
      }
      rows.forEach((row, ry) => {
        for (let rx = 0; rx < row.length; rx++) {
          const ch = at(rx, ry)
          let color = palette[ch]
          // Light the edges of dark silhouettes so they separate from the night behind them
          if (color && backlit && ch === '#') {
            if (at(rx + fireDx, ry) === '.') color = backlit.rim
            else if (at(rx, ry - 1) === '.') color = backlit.top
          }
          if (color) rect(x + rx, top + ry, 1, 1, color)
        }
      })
    }

    /** Sky gradient, dithered, plus the moon; static so it is rendered once per size */
    const buildSky = () => {
      const c = document.createElement('canvas')
      const cw = W + PAD * 2
      const ch = H + PAD * 2
      c.width = cw
      c.height = ch
      const sg = c.getContext('2d')!
      const img = sg.createImageData(cw, ch)
      const stops = SKY.map((hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)))
      for (let py = 0; py < ch; py++) {
        const y = py - PAD
        const pos = Math.max(0, Math.min(1, y / (H * 0.78))) * (stops.length - 1)
        const i = Math.min(Math.floor(pos), stops.length - 2)
        const f = pos - i
        for (let px = 0; px < cw; px++) {
          const col = f > bayer(px, py) ? stops[i + 1] : stops[i]
          const k = (py * cw + px) * 4
          img.data[k] = col[0]
          img.data[k + 1] = col[1]
          img.data[k + 2] = col[2]
          img.data[k + 3] = 255
        }
      }
      sg.putImageData(img, 0, 0)

      const mx = Math.round(W * 0.7) + PAD
      const my = 30 + PAD
      const r = 9
      for (let dy = -24; dy <= 24; dy++) {
        for (let dx = -24; dx <= 24; dx++) {
          const d = Math.hypot(dx, dy)
          const x = mx + dx
          const y = my + dy
          if (d <= r) {
            const crater =
              (dx === -3 && dy === -2) || (dx === 2 && dy === 3) || (dx === 3 && dy === 2) || (dx === -1 && dy === 4)
            sg.fillStyle = crater || dx + dy > 9 ? COLORS.moonShade : COLORS.moon
            sg.fillRect(x, y, 1, 1)
          } else if (d < r + 14) {
            const intensity = 1 - (d - r) / 14
            if (intensity * 0.55 > bayer(x, y)) {
              sg.fillStyle = COLORS.moonGlow
              sg.fillRect(x, y, 1, 1)
            }
          }
        }
      }
      return c
    }

    const resize = () => {
      const box = canvas.getBoundingClientRect()
      if (box.width === 0 || box.height === 0) return
      W = Math.max(160, Math.min(720, Math.round((H * box.width) / box.height)))
      canvas.width = W
      canvas.height = H
      sky = buildSky()
      buffers = Object.fromEntries(
        SCENE_LAYERS.map((l) => {
          const c = document.createElement('canvas')
          c.width = W + PAD * 2
          c.height = H + PAD * 2
          const bg = c.getContext('2d')!
          bg.translate(PAD, PAD)
          return [l.id, { c, g: bg }]
        }),
      ) as Record<LayerId, Buffer>
      const count = Math.round(W * 0.28)
      stars = Array.from({ length: count }, (_, i) => ({
        x: Math.floor(hash(i * 3.17) * W),
        y: Math.floor(hash(i * 7.73 + 1) * H * 0.55),
        phase: hash(i * 1.91) * Math.PI * 2,
        speed: 0.6 + hash(i * 5.3) * 2.2,
        big: hash(i * 9.1) > 0.93,
      }))
    }

    const drawPine = (x: number, base: number, h: number, color: string) => {
      rect(x, base - 2, 1, 3, COLORS.trunk)
      for (let r = 0; r < h; r++) {
        const tier = r % 5
        const half = Math.max(0, Math.floor(r * 0.32) - (tier === 0 ? 1 : 0))
        rect(x - half, base - 2 - h + r, half * 2 + 1, 1, color)
      }
    }

    /** A fern frond: a curved stem with leaflets, drawn in chunky 2px blocks */
    const drawFern = (x: number, y: number, len: number, dir: number, lean: number) => {
      for (let i = 0; i < len; i += 2) {
        const p = i / len
        const sx = x + dir * i * 0.55 * (1 + lean)
        const sy = y - i + p * p * len * 0.55
        rect(sx, sy, 2, 2, COLORS.fern)
        const leaf = Math.round((1 - p) * 7)
        if (i % 4 === 0 && leaf > 1) {
          rect(sx - leaf, sy + 1, leaf, 2, COLORS.fern)
          rect(sx + 2, sy + 1, leaf, 2, COLORS.fern)
          rect(sx - leaf, sy + 1, 1, 1, COLORS.fernEdge)
        }
      }
    }

    const draw = (t: number, dt: number) => {
      const hl = highlightRef.current

      const shift = (depth: number) => ({
        x: Math.round(-pointer.x * depth * 16),
        y: Math.round(-pointer.y * depth * 4),
      })

      /** Draw one layer into its own buffer, then onto the screen (dimmed if another layer is selected) */
      const layer = (id: LayerId, fn: () => void) => {
        const buf = buffers[id]
        if (!buf) return
        g = buf.g
        g.clearRect(-PAD, -PAD, W + PAD * 2, H + PAD * 2)
        fn()
        g = ctx
        ctx.globalAlpha = hl && hl !== id ? 0.3 : 1
        ctx.drawImage(buf.c, -PAD, -PAD)
        ctx.globalAlpha = 1
      }

      ctx.globalAlpha = 1
      ctx.fillStyle = COLORS.void
      ctx.fillRect(0, 0, W, H)

      // ---------- Sky: gradient, moon, twinkling stars, drifting clouds
      layer('sky', () => {
        if (sky) g.drawImage(sky, -PAD, -PAD)
        for (const s of stars) {
          const b = 0.5 + 0.5 * Math.sin(t * s.speed + s.phase)
          if (b < 0.25) continue
          const color = b > 0.75 ? COLORS.star : COLORS.starDim
          rect(s.x, s.y, 1, 1, color)
          if (s.big && b > 0.85) {
            rect(s.x - 1, s.y, 3, 1, color)
            rect(s.x, s.y - 1, 1, 3, color)
          }
        }
        for (let i = 0; i < 5; i++) {
          const w = 22 + hash(i + 40) * 30
          const span = W + w + 20
          const x = ((hash(i + 20) * span + t * (1.5 + hash(i + 60) * 2.5)) % span) - w - 10
          const y = 14 + hash(i + 80) * 50
          rect(x, y, w, 4, COLORS.cloud)
          rect(x + w * 0.2, y - 3, w * 0.45, 3, COLORS.cloud)
          rect(x + w * 0.2, y - 3, w * 0.45, 1, COLORS.cloudTop)
          rect(x + 3, y, w * 0.2 - 3, 1, COLORS.cloudTop)
        }
      })

      // ---------- Mountains: two ranges with snow caps
      layer('mountains', () => {
        const far = shift(0.15)
        for (let sx = -PAD; sx < W + PAD; sx++) {
          const wx = sx - far.x
          const top = Math.round(H * 0.5 - noise(wx / 42) * 40 - noise(wx / 11) * 6 + far.y)
          rect(sx, top, 1, BOTTOM - top, COLORS.mountainFar)
          if (top < H * 0.5 - 30) {
            const depth = 2 + Math.round(noise(wx / 5) * 3)
            for (let k = 0; k < depth; k++) {
              if (k < 2 || bayer(sx & 255, top + k) < 0.5) rect(sx, top + k, 1, 1, COLORS.snow)
            }
          }
        }
        const near = shift(0.25)
        for (let sx = -PAD; sx < W + PAD; sx++) {
          const wx = sx - near.x
          const top = Math.round(H * 0.64 - noise(wx / 30 + 50) * 30 - noise(wx / 9 + 20) * 5 + near.y)
          rect(sx, top, 1, BOTTOM - top, COLORS.mountainNear)
        }
      })

      // ---------- Tower on a hill, flickering windows, waving flag
      layer('tower', () => {
        const o = shift(0.4)
        const hx = Math.round(W * 0.87) + o.x
        const hillTop = Math.round(H * 0.6) + o.y
        for (let sx = hx - 80; sx <= hx + 80; sx++) {
          const d = (sx - hx) / 80
          const top = Math.round(hillTop + d * d * 44)
          rect(sx, top, 1, BOTTOM - top, COLORS.hill)
        }
        const x0 = hx - 6
        const topY = hillTop - 50
        rect(x0, topY, 12, hillTop - topY + 2, COLORS.stone)
        rect(x0 + 9, topY, 3, hillTop - topY + 2, COLORS.stoneShade)
        for (let y = topY + 3; y < hillTop; y += 4) {
          const off = (y / 4) % 2 === 0 ? 1 : 3
          for (let x = x0 + off; x < x0 + 9; x += 4) rect(x, y, 2, 1, COLORS.stoneLight)
        }
        rect(x0 - 2, topY - 4, 16, 4, COLORS.stone)
        rect(x0 + 11, topY - 4, 3, 4, COLORS.stoneShade)
        for (let i = 0; i < 4; i++) rect(x0 - 2 + i * 4, topY - 7, 2, 3, COLORS.stone)
        rect(hx, topY - 18, 1, 11, COLORS.door)
        const frame = Math.floor(t * 3) % 2
        rect(hx + 1, topY - 18, 5, 1, COLORS.flag)
        rect(hx + 1, topY - 17, frame ? 6 : 5, 1, COLORS.flag)
        rect(hx + 1 + frame, topY - 16, 4, 1, COLORS.flag)
        const flicker = noise(t * 6) > 0.45 ? COLORS.windowHot : COLORS.windowWarm
        rect(hx - 1, topY + 8, 2, 4, flicker)
        rect(hx - 2, topY + 26, 3, 4, noise(t * 5 + 9) > 0.4 ? COLORS.windowHot : COLORS.windowWarm)
        rect(hx - 2, hillTop - 5, 4, 7, COLORS.door)
      })

      // ---------- Forest: two rows of pines and fireflies
      layer('forest', () => {
        const o = shift(0.65)
        const groundY = Math.round(H * 0.8) + o.y
        const row = (spacing: number, minH: number, varH: number, base: number, color: string, seed: number) => {
          const first = Math.floor((-o.x - PAD - 12) / spacing)
          const last = Math.ceil((W - o.x + PAD + 12) / spacing)
          for (let k = first; k <= last; k++) {
            const sx = Math.round(k * spacing + hash(k + seed) * spacing * 0.6 + o.x)
            drawPine(sx, base, minH + hash(k + seed + 9) * varH, color)
          }
        }
        row(7, 12, 12, groundY - 2, COLORS.treeBack, 100)
        row(11, 20, 18, groundY + 6, COLORS.treeFront, 300)
        rect(-PAD, groundY + 5, W + PAD * 2, BOTTOM - groundY, COLORS.treeFront)
        for (let i = 0; i < 12; i++) {
          if (Math.sin(t * 2.6 + i * 5.1) < 0.2) continue
          const x = hash(i + 500) * W + Math.sin(t * 0.5 + i) * 14 + o.x
          const y = groundY - 14 + Math.sin(t * 0.8 + i * 2) * 12
          rect(x, y, 1, 1, COLORS.firefly)
        }
      })

      // The campfire and the party share one spot in the scene
      const camp = shift(1)
      const fx = Math.round(W * 0.68) + camp.x
      const fy = Math.round(H * 0.91) + camp.y
      const rim = noise(t * 8) > 0.5 ? COLORS.flameMid : COLORS.flameOuter
      const silhouette = { '#': COLORS.silhouette, r: rim, p: '#8a2a3a' }
      const outline = { top: '#5a3344', rim }

      // ---------- Campfire: ground, firelight, logs, flames, sparks
      layer('campfire', () => {
        const o = camp
        for (let sx = -PAD; sx < W + PAD; sx++) {
          const top = Math.round(H * 0.86 + noise((sx - o.x) / 22) * 5) + o.y
          groundTop.set(sx, top)
          rect(sx, top, 1, BOTTOM - top, COLORS.ground)
        }
        const glow = 0.85 + 0.15 * noise(t * 7)
        for (let dy = -18; dy <= 14; dy++) {
          for (let dx = -48; dx <= 48; dx++) {
            const x = fx + dx
            const y = fy + dy
            if (y < (groundTop.get(x) ?? BOTTOM)) continue
            const d = Math.hypot(dx, dy * 2)
            if (d >= 48) continue
            const inten = (1 - d / 48) * glow
            if (inten > 0.5 && (inten - 0.5) * 2 > bayer(x & 255, y)) rect(x, y, 1, 1, COLORS.glowNear)
            else if (inten * 1.4 > bayer(x & 255, y)) rect(x, y, 1, 1, COLORS.glowFar)
          }
        }

        for (const dx of [-6, -4, 4, 6]) rect(fx + dx, fy, 2, 1, COLORS.rock)
        rect(fx - 5, fy - 1, 11, 2, COLORS.log)
        rect(fx - 3, fy - 2, 7, 1, COLORS.logLight)

        const rows = 16
        for (let r = 0; r < rows; r++) {
          const p = r / rows
          const w = (1 - p) * 5.5 * (0.75 + 0.35 * noise(t * 9 + r * 0.6))
          if (w < 0.4) continue
          const sway = Math.round((noise(t * 4 + r * 0.25) - 0.5) * p * 7)
          const y = fy - 2 - r
          const hw = Math.round(w)
          rect(fx + sway - hw, y, hw * 2 + 1, 1, COLORS.flameOuter)
          const mid = Math.round(w * 0.6)
          if (p < 0.8) rect(fx + sway - mid, y, mid * 2 + 1, 1, COLORS.flameMid)
          const core = Math.round(w * 0.3)
          if (p < 0.55) rect(fx + sway - core, y, core * 2 + 1, 1, COLORS.flameCore)
        }

        if (!reduceMotion && Math.random() < 0.4) {
          sparks.push({
            x: (Math.random() - 0.5) * 4,
            y: -8,
            vx: (Math.random() - 0.5) * 6,
            vy: -(12 + Math.random() * 16),
            life: 1 + Math.random() * 1.2,
          })
        }
        for (let i = sparks.length - 1; i >= 0; i--) {
          const s = sparks[i]
          s.life -= dt
          s.x += (s.vx + Math.sin(t * 3 + i) * 3) * dt
          s.y += s.vy * dt
          if (s.life <= 0) {
            sparks.splice(i, 1)
            continue
          }
          rect(fx + s.x, fy + s.y, 1, 1, s.life > 0.8 ? COLORS.flameCore : COLORS.flameMid)
        }
      })

      // ---------- The party: one layer per character
      // Back row sits behind the fire, facing the camera and lit by the flames
      layer('druid', () => {
        drawSprite(DRUID, fx - 20, fy - 2, false, DRUID_PALETTE)
      })

      layer('bard', () => {
        drawSprite(BARD, fx + 8, fy - 2, false, BARD_PALETTE)
        // Music notes drifting up from the lute
        for (let k = 0; k < 3; k++) {
          const phase = (t * 0.45 + k / 3) % 1
          if (phase > 0.85) continue
          const nx = fx + 20 + phase * 10 + Math.sin(t * 2 + k * 2) * 2
          const ny = fy - 12 - phase * 26
          rect(nx, ny + 2, 2, 2, COLORS.note)
          rect(nx + 1, ny - 1, 1, 3, COLORS.note)
          if (k % 2 === 0) rect(nx + 2, ny - 1, 1, 1, COLORS.note)
        }
      })

      // Front row sits between the camera and the fire, so they are backlit silhouettes
      layer('knight', () => {
        drawSprite(KNIGHT, fx - 34, fy + 6, false, { ...silhouette, '#': '#1b1824' }, outline)
      })

      layer('mage', () => {
        const orb = 0.5 + 0.5 * Math.sin(t * 2.2)
        drawSprite(
          MAGE,
          fx + 19,
          fy + 6,
          true,
          { ...silhouette, '#': '#1d1530', o: orb > 0.5 ? '#e6d2ff' : '#a77cff' },
          outline,
        )
        // Soft glow around the staff's orb (mirrored sprite: the orb is in column 2)
        if (orb > 0.3) {
          const ox = fx + 19 + 2
          const oy = fy + 6 - MAGE.length + 6
          for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) rect(ox + dx, oy + dy, 1, 1, '#5b3d99')
        }
      })

      // ---------- Foreground: ferns and embers right in front of the camera
      layer('foreground', () => {
        const o = shift(1.7)
        const y = H + 4 + o.y
        drawFern(-4 + o.x, y, 46, 1, 0.3)
        drawFern(8 + o.x, y + 4, 34, 1, -0.2)
        drawFern(-10 + o.x, y - 6, 30, 1, 0.9)
        drawFern(W + 4 + o.x, y, 44, -1, 0.3)
        drawFern(W - 12 + o.x, y + 6, 30, -1, -0.3)
        for (let i = 0; i < 7; i++) {
          const bx = ((hash(i + 900) * (W + 40) + t * (2 + i)) % (W + 40)) - 20 + o.x
          const by = H * (0.25 + hash(i + 950) * 0.6) + Math.sin(t * 0.7 + i * 3) * 8 + o.y
          const size = 2 + Math.round(hash(i + 990) * 2)
          g.globalAlpha = 0.35 + 0.25 * Math.sin(t * 1.5 + i)
          rect(bx, by, size, size, i % 3 === 0 ? COLORS.flameCore : COLORS.flameMid)
          g.globalAlpha = 1
        }
      })
    }

    resize()
    const ro = new ResizeObserver(() => {
      resize()
      if (reduceMotion) draw(2, 0)
    })
    ro.observe(canvas)

    if (reduceMotion) {
      redrawRef.current = () => draw(2, 0)
      draw(2, 0)
      return () => {
        ro.disconnect()
        redrawRef.current = () => {}
      }
    }

    const onPointer = (e: PointerEvent) => {
      pointer.tx = (e.clientX / window.innerWidth) * 2 - 1
      pointer.ty = (e.clientY / window.innerHeight) * 2 - 1
      pointer.lastMove = performance.now()
    }
    window.addEventListener('pointermove', onPointer)

    let raf = 0
    let last = performance.now()
    const loop = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000)
      last = now
      const t = now / 1000
      // With no pointer (e.g. touch screens) the scene sways gently on its own
      if (now - pointer.lastMove > 4000) {
        pointer.tx = Math.sin(t * 0.25) * 0.6
        pointer.ty = 0
      }
      const k = Math.min(1, dt * 3)
      pointer.x += (pointer.tx - pointer.x) * k
      pointer.y += (pointer.ty - pointer.y) * k
      draw(t, dt)
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)

    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
      window.removeEventListener('pointermove', onPointer)
    }
  }, [])

  return <canvas ref={canvasRef} className={className} aria-hidden="true" />
}
