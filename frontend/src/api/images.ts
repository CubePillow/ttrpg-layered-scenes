/** Pictures from the models in the Kaggle session (backend/model_api.py). Images are PNG data URLs. */

export const randomSeed = () => Math.floor(Math.random() * 100_000)

/** A new picture from text (SDXL-Turbo). */
export async function generateImage(prompt: string, seed = randomSeed()): Promise<string> {
  const response = await fetch('/api/images/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, seed }),
  })
  if (!response.ok) {
    const detail = await response
      .json()
      .then((data) => (typeof data.detail === 'string' ? data.detail : null))
      .catch(() => null)
    throw new Error(detail ?? `The picture could not be drawn (${response.status}). Is the backend running?`)
  }
  const data: { image: string } = await response.json()
  return data.image
}

export type PixelLayer = { name: string; x: number; y: number; width: number; height: number; image: string }

/**
 * Turns layers (back to front, the first one the background) into big pixels, all on one grid with one palette.
 * No AI: it runs on the backend (backend/pixelize.py). The images come back small, one image pixel per big pixel.
 */
export async function pixelize(layers: { name: string; image: string }[], block = 4, colors = 16) {
  const response = await fetch('/api/pixelize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ layers, block, colors }),
  })
  if (!response.ok) throw new Error(`The pixel filter failed (${response.status}). Is the backend running?`)
  const data: { grid: [number, number]; layers: PixelLayer[] } = await response.json()
  return data
}

/** The picture cut into a background and one layer per named object, back to front (Qwen-Image on Kaggle). */
export async function splitImage(image: string, names: string[]): Promise<{ name: string; image: string }[]> {
  const response = await fetch('/api/images/split', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image, names }),
  })
  if (!response.ok) {
    const detail = await response
      .json()
      .then((data) => (typeof data.detail === 'string' ? data.detail : null))
      .catch(() => null)
    throw new Error(detail ?? `The picture could not be split (${response.status}). Is the backend running?`)
  }
  const data: { layers: { name: string; image: string }[] } = await response.json()
  return data.layers
}
