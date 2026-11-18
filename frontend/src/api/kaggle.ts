/** The connection to the Kaggle GPU session (backend/kaggle_connection.py). */
export type KaggleState = {
  stage: 'off' | 'account' | 'notebook' | 'session' | 'ready' | 'stopping' | 'failed'
  progress: number
  message: string
  username: string | null
  started_at: string | null
  log: string[]
}

async function request(path: string, method = 'GET') {
  const response = await fetch(`/api/kaggle/${path}`, { method })
  if (!response.ok) throw new Error(`Kaggle request failed (${response.status})`)
  const state: KaggleState = await response.json()
  return state
}

export const getKaggleStatus = () => request('status')
export const connectKaggle = () => request('connect', 'POST')
export const stopKaggle = () => request('stop', 'POST')
