import { useEffect, useState } from 'react'
import HeroPortrait from '../components/party/HeroPortrait'
import PixelScene from '../components/pixel-scene/PixelScene'
import { Button, Panel, SectionTitle } from '../components/ui'
import { artStyle } from '../data/artStyles'
import { deleteSave, listSaves, type SaveSummary } from '../data/saves'
import styles from './SavesPage.module.css'

const savedWhen = (time: string) =>
  new Date(time).toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })

/** A small pixel bin. */
function TrashIcon() {
  return (
    <svg width="14" height="16" viewBox="0 0 7 8" shapeRendering="crispEdges" aria-hidden="true" fill="currentColor">
      <rect x="2" y="0" width="3" height="1" />
      <rect x="0" y="1" width="7" height="1" />
      <rect x="1" y="2" width="5" height="1" />
      <rect x="1" y="3" width="1" height="5" />
      <rect x="3" y="3" width="1" height="4" />
      <rect x="5" y="3" width="1" height="5" />
      <rect x="1" y="7" width="5" height="1" />
    </svg>
  )
}

/** The saved party setups; pick one to continue it. */
export default function SavesPage() {
  const [saves, setSaves] = useState<SaveSummary[] | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    listSaves().then(setSaves)
  }, [])

  /** The save whose Delete was pressed once; pressing "Sure?" then deletes it. */
  const [confirming, setConfirming] = useState<string | null>(null)

  const remove = async (save: SaveSummary) => {
    setConfirming(null)
    try {
      await deleteSave(save.id)
      setSaves((all) => all?.filter((s) => s.id !== save.id) ?? null)
    } catch {
      setFailed(true)
    }
  }

  return (
    <div className={styles.page}>
      <PixelScene highlight={null} className={styles.scene} />
      <div className={styles.shade} />
      <main className={styles.content}>
        <Panel className={styles.panel}>
          <div className={styles.header}>
            <SectionTitle>Load story</SectionTitle>
            <Button href="/">Home</Button>
          </div>
          {saves === null && <p>Loading saves…</p>}
          {saves?.length === 0 && <p>No saves yet. Press Save while setting up a party to keep it here.</p>}
          {failed && <p className={styles.error}>That save could not be deleted. Is the backend running?</p>}
          <ul className={styles.list}>
            {saves?.map((save) => (
              <li key={save.id} className={styles.save}>
                <a
                  className={styles.card}
                  href={`/party?save=${save.id}`}
                  aria-label={`Continue ${save.title || 'Untitled party'}`}
                >
                  <span className={styles.main}>
                    <span className={styles.top}>
                      <strong className={styles.title}>{save.title || 'Untitled party'}</strong>
                      <span className={styles.time}>{savedWhen(save.saved_at)}</span>
                    </span>
                    <span className={styles.meta}>
                      {[save.style && artStyle(save.style).name, save.progress].filter(Boolean).join(' · ')}
                    </span>
                  </span>
                  <span className={styles.heroes}>
                    {save.heroes.map((hero, i) => (
                      <span key={i} className={styles.head}>
                        <HeroPortrait classId={hero.classId} color={hero.color} scale={3} label={hero.name} />
                      </span>
                    ))}
                  </span>
                </a>
                <span className={styles.remove}>
                  {confirming === save.id ? (
                    <>
                      <button type="button" className={styles.danger} onClick={() => remove(save)}>
                        Delete
                      </button>
                      <button type="button" onClick={() => setConfirming(null)}>
                        Keep
                      </button>
                    </>
                  ) : (
                    <button
                      type="button"
                      aria-label="Delete this save"
                      title="Delete"
                      onClick={() => setConfirming(save.id)}
                    >
                      <TrashIcon />
                    </button>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </Panel>
      </main>
    </div>
  )
}
