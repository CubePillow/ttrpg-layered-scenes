import { useUiFeedback } from './audio/useUiFeedback'
import KaggleStatus from './components/kaggle/KaggleStatus'
import HomePage from './pages/HomePage'
import PartySetupPage from './pages/PartySetupPage'
import SavesPage from './pages/SavesPage'

/** Top-level component. Replace the address check with a router when there are more pages. */
export default function App() {
  useUiFeedback()

  const path = window.location.pathname

  let page

  if (path === '/party') {
    page = <PartySetupPage />
  } else if (path === '/saves') {
    page = <SavesPage />
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
