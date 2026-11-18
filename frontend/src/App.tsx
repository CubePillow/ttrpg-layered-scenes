import HomePage from './pages/HomePage'
import PartySetupPage from './pages/PartySetupPage'

/** Top-level component. Replace the address check with a router when there are more pages. */
export default function App() {
  return window.location.pathname === '/party' ? <PartySetupPage /> : <HomePage />
}
