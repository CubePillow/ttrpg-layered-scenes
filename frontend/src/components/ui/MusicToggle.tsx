import { useEffect, useState } from 'react'
import { isMusicMuted, playTheme, setMusicMuted, stopTheme } from '../../audio/chiptune'
import { AMBIENT_THEME } from '../../audio/heroThemes'
import Button from './Button'

/**
 * Plays the game's quiet campfire music while the page is open, with a button to mute it.
 * Browsers hold the sound back until the first click or key press on the page.
 */
export default function MusicToggle() {
  const [muted, setMuted] = useState(isMusicMuted)

  useEffect(() => {
    playTheme(AMBIENT_THEME)
    return stopTheme
  }, [])

  const toggle = () => {
    setMusicMuted(!muted)
    setMuted(!muted)
  }

  return (
    <Button aria-pressed={!muted} onClick={toggle} title={muted ? 'Turn the music on' : 'Mute the music'}>
      {muted ? '♪ Music on' : '♪ Mute'}
    </Button>
  )
}
