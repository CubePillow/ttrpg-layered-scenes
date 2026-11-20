import { useEffect } from 'react'
import { canPlayUiSound, playUiSound, type UiSound } from './chiptune'

const INTERACTIVE = 'button:not(:disabled), a[href], input[type="radio"]:not(:disabled)'
const HOVER_TARGET = 'button:not(:disabled), a[href], label:has(input[type="radio"]:not(:disabled))'
const LEAVE_PAGE_MS = 180
const SPARKS = 8
const SPARK_COLORS = ['#ffe08a', '#ff9a3c', '#d8432f']

function soundFor(element: Element): UiSound {
  const label = element.textContent?.trim().toLowerCase() ?? ''
  if (/^(back|change )/.test(label)) return 'back'
  if (label.startsWith('lock in')) return 'lock'
  if (element.matches('[data-variant="primary"], a[href="/party"]')) return 'confirm'
  // Cards and radio choices are plain controls; ordinary buttons always have a variant
  return element.matches('button:not([data-variant]), input[type="radio"]') ? 'select' : 'tick'
}

/** A small burst of pixels where the player clicked. */
function burst(x: number, y: number) {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  for (let i = 0; i < SPARKS; i++) {
    const spark = document.createElement('span')
    const angle = (i / SPARKS) * Math.PI * 2
    const distance = 26 + (i % 3) * 8
    spark.setAttribute('aria-hidden', 'true')
    spark.dataset.spark = ''
    spark.style.cssText = `position:fixed;left:${x - 3}px;top:${y - 3}px;width:6px;height:6px;z-index:50;pointer-events:none;background:${SPARK_COLORS[i % SPARK_COLORS.length]}`
    document.body.append(spark)
    spark
      .animate(
        [
          { transform: 'translate(0, 0)', opacity: 1 },
          { transform: `translate(${Math.cos(angle) * distance}px, ${Math.sin(angle) * distance}px)`, opacity: 0 },
        ],
        { duration: 320, easing: 'steps(6)' },
      )
      .finished.finally(() => spark.remove())
  }
}

/** Sounds and a pixel burst for every button, link and choice in the app. */
export function useUiFeedback() {
  useEffect(() => {
    let hovered: Element | null = null

    const onHover = (event: PointerEvent) => {
      if (event.pointerType !== 'mouse') return
      const target = event.target instanceof Element ? event.target.closest(HOVER_TARGET) : null
      if (target && target !== hovered && canPlayUiSound()) playUiSound('hover')
      hovered = target
    }

    const onClick = (event: MouseEvent) => {
      const element = event.target instanceof Element ? event.target.closest(INTERACTIVE) : null
      if (!element) return
      const sound = soundFor(element)
      playUiSound(sound)

      if (sound !== 'tick' && sound !== 'back') {
        const box = element.getBoundingClientRect()
        const fromKeyboard = event.detail === 0
        burst(fromKeyboard ? box.left + box.width / 2 : event.clientX, fromKeyboard ? box.top + box.height / 2 : event.clientY)
      }

      // Let the sound finish before a link opens another page
      if (element instanceof HTMLAnchorElement && !event.defaultPrevented && !event.metaKey && !event.ctrlKey && !event.shiftKey) {
        if (element.origin === location.origin && element.pathname !== location.pathname) {
          event.preventDefault()
          window.setTimeout(() => location.assign(element.href), LEAVE_PAGE_MS)
        }
      }
    }

    document.addEventListener('pointerover', onHover)
    document.addEventListener('click', onClick)
    return () => {
      document.removeEventListener('pointerover', onHover)
      document.removeEventListener('click', onClick)
    }
  }, [])
}
