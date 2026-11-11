import { useState } from 'react'
import PixelScene from '../components/pixel-scene/PixelScene'
import { LAYER_GROUPS, STEPS } from '../data/homeContent'
import { SCENE_LAYERS, type LayerId } from '../data/sceneLayers'
import '../styles/home.css'

export default function HomePage() {
  const [active, setActive] = useState<LayerId | null>(null)
  const activeLayer = SCENE_LAYERS.find((l) => l.id === active)

  return (
    <>
      <header className="hero">
        <PixelScene highlight={active} className="hero-scene" />

        <div className="hero-panel pixel-box">
          <p className="eyebrow">TTRPG · Layered Scene Builder</p>
          <h1 className="title">
            Paint the scene together, <span className="accent">layer by layer.</span>
          </h1>
          <p className="lede">
            Describe a moment from your adventure. The AI turns it into a picture made of layers
            you can move, swap and redraw as the story unfolds.
          </p>
          <div className="actions">
            <a className="btn btn-primary" href="#how">
              How it works
            </a>
            <button className="btn" type="button" disabled>
              Start a scene <span className="soon">soon</span>
            </button>
          </div>

          <div className="layer-bar" onMouseLeave={() => setActive(null)}>
            <p className="layer-bar-label">This scene has {SCENE_LAYERS.length} layers</p>
            {LAYER_GROUPS.map((group) => (
              <div key={group.id} className="chip-group">
                <span className="chip-group-name">{group.label}</span>
                <div className="chips">
                  {SCENE_LAYERS.filter((l) => l.group === group.id).map((layer) => (
                    <button
                      key={layer.id}
                      type="button"
                      className={`chip${active === layer.id ? ' chip-on' : ''}`}
                      aria-pressed={active === layer.id}
                      onMouseEnter={() => setActive(layer.id)}
                      onFocus={() => setActive(layer.id)}
                      onBlur={() => setActive(null)}
                      onClick={() => setActive(active === layer.id ? null : layer.id)}
                    >
                      {layer.label}
                    </button>
                  ))}
                </div>
              </div>
            ))}
            <p className="layer-prompt" aria-live="polite">
              {activeLayer ? (
                <>
                  <span className="prompt-key">prompt&gt;</span> {activeLayer.prompt}
                </>
              ) : (
                'Hover a layer to highlight it and see its own prompt.'
              )}
            </p>
          </div>
        </div>
      </header>

      <main>
        <section id="how" className="how">
          <h2 className="section-title">How it works</h2>
          <ol className="steps">
            {STEPS.map((step, i) => (
              <li key={step.title} className="step pixel-box">
                <span className="step-num">{String(i + 1).padStart(2, '0')}</span>
                <h3 className="step-title">{step.title}</h3>
                <p>{step.text}</p>
              </li>
            ))}
          </ol>
        </section>
      </main>

      <footer className="footer">
        <p>Research prototype · focus on controllability and layer-by-layer editing</p>
      </footer>
    </>
  )
}
