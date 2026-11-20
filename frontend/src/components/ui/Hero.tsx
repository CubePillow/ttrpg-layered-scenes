import type { ReactNode } from 'react'
import Panel from './Panel'
import styles from './Hero.module.css'

type Props = {
  /** Draws the full-size background; put the given class name on it. */
  background: (className: string) => ReactNode
  children: ReactNode
}

/** Full-screen opening of a page: a background with a panel on top. */
export default function Hero({ background, children }: Props) {
  return (
    <header className={styles.hero}>
      {background(styles.background)}
      <Panel className={styles.panel}>{children}</Panel>
    </header>
  )
}
