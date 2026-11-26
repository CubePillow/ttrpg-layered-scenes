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

/**
 * One layer changed by a text instruction ("make the tree autumn red"), keeping it transparent
 * (Qwen-Image-2.1 on Kaggle, about half a minute). `accepted` is false when the model's check found the layer
 * wiped or flooded; the result is then the closest try.
 */
export async function editLayer(image: string, name: string, change: string, seed = randomSeed()) {
  // A few words alone ("autumn leaves") are often taken as no change at all; a plain instruction is followed
  const prompt = `Change the ${name} so that it becomes: ${change}. Redraw it as needed and make the change clearly visible. Keep the flat colour vector style with simple shapes.`
  const response = await fetch('/api/layers/edit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image, prompt, seed }),
  })
  if (!response.ok) {
    const detail = await response
      .json()
      .then((data) => (typeof data.detail === 'string' ? data.detail : null))
      .catch(() => null)
    throw new Error(detail ?? `The layer could not be changed (${response.status}). Is the backend running?`)
  }
  const data: { image: string; report: { accepted?: boolean } } = await response.json()
  return { image: data.image, accepted: data.report?.accepted !== false }
}
