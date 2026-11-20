import { useUiFeedback } from './audio/useUiFeedback'
import HomePage from './pages/HomePage'
import PartySetupPage from './pages/PartySetupPage'
import SavesPage from './pages/SavesPage'

/** Top-level component. Replace the address check with a router when there are more pages. */
export default function App() {
  useUiFeedback()
  const path = window.location.pathname
  if (path === '/party') return <PartySetupPage />
  if (path === '/saves') return <SavesPage />
  return <HomePage />
}
