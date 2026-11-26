/**
 * Export of an act's scene: the whole picture as one PNG, or every layer as its own PNG in one ZIP.
 * Everything happens in the browser, so no backend call and no Kaggle session are needed.
 */

/** What the export needs of a layer. Place and size are shares of the picture (0 to 1), as on the stage. */
export type ExportLayer = {
  name: string
  image: string
  x: number
  y: number
  w: number
  h: number
  hidden: boolean
}

type Size = { width: number; height: number }

async function loadImage(src: string) {
  const picture = new Image()
  picture.src = src
  await picture.decode()
  return picture
}

/** The picture size: the whole background as the split made it, so the export keeps the full resolution. */
export async function pictureSize(backgroundSource: string): Promise<Size> {
  const picture = await loadImage(backgroundSource)
  return { width: picture.naturalWidth, height: picture.naturalHeight }
}

/** Draws the given layers, back to front, where they are on the stage. */
async function draw(layers: ExportLayer[], size: Size, pixelStyle: boolean) {
  const canvas = document.createElement('canvas')
  canvas.width = size.width
  canvas.height = size.height
  const context = canvas.getContext('2d')!
  // Pixel art keeps its hard edges when it is scaled up
  context.imageSmoothingEnabled = !pixelStyle
  for (const layer of layers) {
    const picture = await loadImage(layer.image)
    context.drawImage(
      picture,
      layer.x * size.width,
      layer.y * size.height,
      layer.w * size.width,
      layer.h * size.height,
    )
  }
  return canvas
}

function toBlob(canvas: HTMLCanvasElement) {
  return new Promise<Blob>((resolve, reject) =>
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('The picture could not be made'))), 'image/png'),
  )
}

/**
 * Saves the file through a link that is never put on the page. A click on it then does not reach the app's
 * click handler (useUiFeedback), which would otherwise open the picture as a page instead of saving it.
 */
function download(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
}

/** A name that works as a file name on every system: "The Silent King" -> "the-silent-king" */
export function fileSafe(text: string) {
  return (
    text
      .normalize('NFKD')
      .replace(/[̀-ͯ]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 60) || 'scene'
  )
}

/** The scene as one PNG, as it looks on the stage (hidden layers left out). */
export async function exportScenePng(layers: ExportLayer[], size: Size, pixelStyle: boolean, baseName: string) {
  const canvas = await draw(
    layers.filter((l) => !l.hidden),
    size,
    pixelStyle,
  )
  download(await toBlob(canvas), `${baseName}.png`)
}

/**
 * Every shown layer as its own PNG of the full picture size, see-through around the object,
 * so the files line up again when stacked in an image editor. Numbered back to front.
 */
export async function exportLayersZip(layers: ExportLayer[], size: Size, pixelStyle: boolean, baseName: string) {
  const shown = layers.filter((l) => !l.hidden)
  const digits = String(shown.length).length
  const files: ZipFile[] = []
  for (const [i, layer] of shown.entries()) {
    const canvas = await draw([layer], size, pixelStyle)
    const number = String(i + 1).padStart(Math.max(2, digits), '0')
    files.push({
      name: `${number}-${fileSafe(layer.name)}.png`,
      data: new Uint8Array(await (await toBlob(canvas)).arrayBuffer()),
    })
  }
  download(makeZip(files), `${baseName}-layers.zip`)
}

/* ---- A small ZIP writer (files stored without compression, which suits PNGs that are compressed already) ---- */

export type ZipFile = { name: string; data: Uint8Array }

const CRC_TABLE = (() => {
  const table = new Uint32Array(256)
  for (let n = 0; n < 256; n++) {
    let c = n
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1
    table[n] = c >>> 0
  }
  return table
})()

export function crc32(data: Uint8Array) {
  let crc = 0xffffffff
  for (const byte of data) crc = CRC_TABLE[(crc ^ byte) & 0xff] ^ (crc >>> 8)
  return (crc ^ 0xffffffff) >>> 0
}

/** Date and time in the DOS format ZIP files use */
function dosTime(date: Date) {
  const time = (date.getHours() << 11) | (date.getMinutes() << 5) | Math.floor(date.getSeconds() / 2)
  const day = ((date.getFullYear() - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate()
  return { time, day }
}

export function makeZip(files: ZipFile[], date = new Date()): Blob {
  const encoder = new TextEncoder()
  const { time, day } = dosTime(date)
  const parts: Uint8Array[] = []
  const directory: Uint8Array[] = []
  let offset = 0

  for (const file of files) {
    const name = encoder.encode(file.name)
    const crc = crc32(file.data)
    const size = file.data.length

    const local = new DataView(new ArrayBuffer(30))
    local.setUint32(0, 0x04034b50, true) // Local file header
    local.setUint16(4, 20, true) // Version needed
    local.setUint16(6, 0x0800, true) // File names are UTF-8
    local.setUint16(8, 0, true) // Stored, no compression
    local.setUint16(10, time, true)
    local.setUint16(12, day, true)
    local.setUint32(14, crc, true)
    local.setUint32(18, size, true)
    local.setUint32(22, size, true)
    local.setUint16(26, name.length, true)
    local.setUint16(28, 0, true)
    parts.push(new Uint8Array(local.buffer), name, file.data)

    const central = new DataView(new ArrayBuffer(46))
    central.setUint32(0, 0x02014b50, true) // Central directory entry
    central.setUint16(4, 20, true) // Version made by
    central.setUint16(6, 20, true) // Version needed
    central.setUint16(8, 0x0800, true)
    central.setUint16(10, 0, true)
    central.setUint16(12, time, true)
    central.setUint16(14, day, true)
    central.setUint32(16, crc, true)
    central.setUint32(20, size, true)
    central.setUint32(24, size, true)
    central.setUint16(28, name.length, true)
    central.setUint32(42, offset, true) // Where the local header starts
    directory.push(new Uint8Array(central.buffer), name)

    offset += 30 + name.length + size
  }

  const directorySize = directory.reduce((sum, part) => sum + part.length, 0)
  const end = new DataView(new ArrayBuffer(22))
  end.setUint32(0, 0x06054b50, true) // End of central directory
  end.setUint16(8, files.length, true)
  end.setUint16(10, files.length, true)
  end.setUint32(12, directorySize, true)
  end.setUint32(16, offset, true)

  return new Blob([...parts, ...directory, new Uint8Array(end.buffer)] as BlobPart[], { type: 'application/zip' })
}
