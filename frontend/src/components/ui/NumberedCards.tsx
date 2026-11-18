import Panel from './Panel'
import styles from './NumberedCards.module.css'

type Props = { items: ReadonlyArray<{ title: string; text: string }> }

/** Ordered list of cards numbered 01, 02, 03 ... */
export default function NumberedCards({ items }: Props) {
  return (
    <ol className={styles.list}>
      {items.map((item, i) => (
        <Panel as="li" tone="solid" key={item.title} className={styles.card}>
          <span className={styles.number}>{String(i + 1).padStart(2, '0')}</span>
          <h3 className={styles.title}>{item.title}</h3>
          <p className={styles.text}>{item.text}</p>
        </Panel>
      ))}
    </ol>
  )
}
