import { useUiFeedback } from './audio/useUiFeedback'
import HomePage from './pages/HomePage'
import PartySetupPage from './pages/PartySetupPage'

/** Top-level component. Replace the address check with a router when there are more pages. */
export default function App() {
  useUiFeedback()
  return window.location.pathname === '/party' ? <PartySetupPage /> : <HomePage />
}
