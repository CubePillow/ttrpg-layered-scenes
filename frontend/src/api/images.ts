/** Pictures from the models in the Kaggle GPU session (backend/model_api.py). */

/** Makes a picture from a text prompt. Returns it as a data URL; throws with the backend's message when it fails. */
export async function generateImage(prompt: string, seed = Math.floor(Math.random() * 100_000)): Promise<string> {
  const response = await fetch('/api/images/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, seed, size: 512 }),
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(typeof body?.detail === 'string' ? body.detail : `Drawing failed (${response.status})`)
  }
  const { image } = (await response.json()) as { image: string }
  return image.startsWith('data:') ? image : `data:image/png;base64,${image}`
}

/** Keeps a picture on the backend with its save, and returns its id. */
export async function storePicture(saveId: string, image: string): Promise<string> {
  const response = await fetch('/api/pictures', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ saveId, image }),
  })
  if (!response.ok) throw new Error(`Keeping the picture failed (${response.status})`)
  return ((await response.json()) as { id: string }).id
}

export const pictureUrl = (id: string) => `/api/pictures/${encodeURIComponent(id)}`
