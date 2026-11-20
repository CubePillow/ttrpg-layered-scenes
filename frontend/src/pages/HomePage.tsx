import { useEffect, useState } from 'react'
import LayerPicker from '../components/layers/LayerPicker'
import PixelScene from '../components/pixel-scene/PixelScene'
import {
  Accent,
  Button,
  ButtonGroup,
  Eyebrow,
  Hero,
  Lede,
  NumberedCards,
  PageSection,
  PageTitle,
  SiteFooter,
} from '../components/ui'
import { listDrafts } from '../data/partyDraft'
import { LAYER_GROUPS, STEPS } from '../data/homeContent'
import { SCENE_LAYERS, type LayerId } from '../data/sceneLayers'
import styles from './HomePage.module.css'

export default function HomePage() {
  const [active, setActive] = useState<LayerId | null>(null)
  const [saveCount, setSaveCount] = useState(0)

  useEffect(() => {
    listDrafts().then((saves) => setSaveCount(saves.length))
  }, [])

  return (
    <>
      <Hero background={(className) => <PixelScene highlight={active} className={className} />}>
        <Eyebrow className={styles.eyebrow}>TTRPG · Layered Scene Builder</Eyebrow>
        <PageTitle>
          Paint the scene together, <Accent>layer by layer.</Accent>
        </PageTitle>
        <Lede className={styles.lede}>
          Describe a moment from your adventure. The AI turns it into a picture made of layers
          you can move, swap and redraw as the story unfolds.
        </Lede>
        <ButtonGroup className={styles.actions}>
          <Button variant="primary" href="/party">
            New story
          </Button>
          {saveCount > 0 ? (
            <Button href="/saves">Load story</Button>
          ) : (
            <Button disabled title="No saves yet: press Save when your party is ready">
              Load story
            </Button>
          )}
          <Button href="#how">How it works</Button>
        </ButtonGroup>

        <LayerPicker
          className={styles.layers}
          layers={SCENE_LAYERS}
          groups={LAYER_GROUPS}
          active={active}
          onActiveChange={setActive}
        />
      </Hero>

      <main>
        <PageSection id="how" heading="How it works">
          <NumberedCards items={STEPS} />
        </PageSection>
      </main>

      <SiteFooter>
        <p>Research prototype · focus on controllability and layer-by-layer editing</p>
      </SiteFooter>
    </>
  )
}
