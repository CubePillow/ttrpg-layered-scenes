/** Pictures kept on the backend (backend/pictures.py). A save holds only their ids. */

/** Keeps a PNG (as a data URL) with the save; returns its id. */
export async function storePicture(saveId: string, image: string): Promise<string> {
  const response = await fetch('/api/pictures', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ saveId, image }),
  })
  if (!response.ok) throw new Error(`The picture could not be kept (${response.status}). Is the backend running?`)
  const data: { id: string } = await response.json()
  return data.id
}

export const pictureUrl = (id: string) => `/api/pictures/${encodeURIComponent(id)}`

/** A kept picture as a data URL, for sending it on to the models or the pixel filter. */
export async function pictureData(id: string): Promise<string> {
  const response = await fetch(pictureUrl(id))
  if (!response.ok) throw new Error(`A picture of this act is missing (${response.status}).`)
  const blob = await response.blob()
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(blob)
  })
}
