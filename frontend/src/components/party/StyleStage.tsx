import { Accent, Badge, Button, PageTitle, Panel } from '../ui'
import { ART_STYLES, AVAILABLE_ART_STYLES, type ArtStyleId } from '../../data/artStyles'
import { cx } from '../ui/cx'
import StylePreview from './StylePreview'
import styles from './party.module.css'

type Props = {
  selected: ArtStyleId
  onChoose: (style: ArtStyleId) => void
  onBack: () => void
}

/** After the heroes: the picture style of this game, shown on the home page campfire. */
export default function StyleStage({ selected, onChoose, onBack }: Props) {
  return (
    <Panel className={styles.style}>
      <PageTitle>
        Choose your <Accent>style</Accent>
      </PageTitle>
      <div className={styles.styleGrid}>
        {ART_STYLES.map((style) => {
          const available = AVAILABLE_ART_STYLES.includes(style.id)
          return (
            <button
              key={style.id}
              type="button"
              className={cx(styles.modeCard, styles.styleCard, style.id === selected && styles.styleOn)}
              aria-pressed={style.id === selected}
              disabled={!available}
              onClick={() => onChoose(style.id)}
            >
              <StylePreview style={style} />
              <span className={styles.modeName}>{style.name}</span>
              <span>{style.description}</span>
              {!available && <Badge>Coming soon</Badge>}
            </button>
          )
        })}
      </div>
      <div className={styles.backRow}>
        <Button onClick={onBack}>Back</Button>
      </div>
    </Panel>
  )
}
