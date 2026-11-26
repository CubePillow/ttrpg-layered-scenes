import { useUiFeedback } from './audio/useUiFeedback'
import KaggleStatus from './components/kaggle/KaggleStatus'
import DrawPage from './pages/DrawPage'
import HomePage from './pages/HomePage'
import LayersPage from './pages/LayersPage'
import PartySetupPage from './pages/PartySetupPage'
import SavesPage from './pages/SavesPage'
import StoryPage from './pages/StoryPage'

/** Top-level component. Replace the address check with a router when there are more pages. */
export default function App() {
  useUiFeedback()

  const path = window.location.pathname

  let page

  if (path === '/party') {
    page = <PartySetupPage />
  } else if (path === '/saves') {
    page = <SavesPage />
  } else if (path === '/layers') {
    page = <LayersPage />
  } else if (path === '/draw') {
    page = <DrawPage />
  } else if (path === '/story') {
    page = <StoryPage />
  } else {
    page = <HomePage />
  }

  return (
    <>
      {page}
      <KaggleStatus />
    </>
  )
}
