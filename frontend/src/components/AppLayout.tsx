import { Outlet } from 'react-router-dom'
import { AppNav } from './AppNav'
import { SetupBanner } from '../features/setup/SetupBanner'
import { usePreflight } from '../hooks/usePreflight'

export function AppLayout() {
  const { preflight, canGenerate } = usePreflight()

  return (
    <div className="app-shell">
      <AppNav />
      <main className="app-main">
        {preflight && !canGenerate && <SetupBanner preflight={preflight} />}
        <Outlet />
      </main>
    </div>
  )
}
