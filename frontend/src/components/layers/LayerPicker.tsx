import { Chip } from '../ui'
import { cx } from '../ui/cx'
import styles from './LayerPicker.module.css'

type PickerLayer<Id extends string> = { id: Id; label: string; group: string; prompt: string }

type Props<Id extends string> = {
  layers: ReadonlyArray<PickerLayer<Id>>
  groups: ReadonlyArray<{ id: string; label: string }>
  active: Id | null
  onActiveChange: (id: Id | null) => void
  className?: string
}

/** Layer buttons in named groups, with the prompt of the active layer below. */
export default function LayerPicker<Id extends string>({ layers, groups, active, onActiveChange, className }: Props<Id>) {
  const activeLayer = layers.find((l) => l.id === active)

  return (
    <div className={cx(styles.picker, className)} onMouseLeave={() => onActiveChange(null)}>
      <p className={styles.label}>This scene has {layers.length} layers</p>
      {groups.map((group) => (
        <div key={group.id} className={styles.group}>
          <span className={styles.groupName}>{group.label}</span>
          <div className={styles.chips}>
            {layers
              .filter((l) => l.group === group.id)
              .map((layer) => (
                <Chip
                  key={layer.id}
                  selected={active === layer.id}
                  onMouseEnter={() => onActiveChange(layer.id)}
                  onFocus={() => onActiveChange(layer.id)}
                  onBlur={() => onActiveChange(null)}
                  onClick={() => onActiveChange(active === layer.id ? null : layer.id)}
                >
                  {layer.label}
                </Chip>
              ))}
          </div>
        </div>
      ))}
      <p className={styles.prompt} aria-live="polite">
        {activeLayer ? (
          <>
            <span className={styles.promptKey}>prompt&gt;</span> {activeLayer.prompt}
          </>
        ) : (
          'Hover a layer to highlight it and see its own prompt.'
        )}
      </p>
    </div>
  )
}
