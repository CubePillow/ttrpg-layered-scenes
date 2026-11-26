/**
 * The version picked on the drawing page, handed to the layers page.
 * It stays in this browser tab only, until saves hold pictures.
 */
export type PickedPicture = {
  /** The plain picture the model drew; this is what gets split */
  image: string
  /** Its pixel version, for pixel-art stories */
  pixel?: string
  prompt: string
  seed: number
}

const key = (saveId: string) => `picked-picture:${saveId}`

export function keepPicked(saveId: string, picture: PickedPicture) {
  try {
    sessionStorage.setItem(key(saveId), JSON.stringify(picture))
    return true
  } catch {
    return false // Storage full or blocked
  }
}

export function loadPicked(saveId: string): PickedPicture | null {
  try {
    const text = sessionStorage.getItem(key(saveId))
    return text ? (JSON.parse(text) as PickedPicture) : null
  } catch {
    return null
  }
}

/** Forgets the picked picture, once its act is done. */
export function clearPicked(saveId: string) {
  try {
    sessionStorage.removeItem(key(saveId))
  } catch {
    // Storage blocked: nothing was kept
  }
}
