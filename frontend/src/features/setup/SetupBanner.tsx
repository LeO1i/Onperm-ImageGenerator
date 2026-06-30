import { Link } from 'react-router-dom'
import type { PreflightResult } from '../../api/types'

interface SetupBannerProps {
  preflight: PreflightResult
}

export function SetupBanner({ preflight }: SetupBannerProps) {
  const failedItems = preflight.items.filter(
    (item) => item.severity === 'critical' && item.status === 'fail',
  )

  if (failedItems.length === 0) return null

  return (
    <div className="setup-banner" role="alert">
      <div className="setup-banner-content">
        <h2>Setup required before you can generate images</h2>
        <p>
          Critical checks failed. Fix the issues below, then re-run checks in
          Settings.
        </p>
        <ul className="setup-banner-list">
          {failedItems.map((item) => (
            <li key={item.id}>
              <strong>{item.name}</strong>
              <span>{item.message}</span>
              {item.fix_hint && (
                <span className="fix-hint">{item.fix_hint}</span>
              )}
            </li>
          ))}
        </ul>
        <Link to="/settings" className="btn btn-secondary">
          Open System status
        </Link>
      </div>
    </div>
  )
}
