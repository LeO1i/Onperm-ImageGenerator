import { NavLink } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/', label: 'Generate', end: true },
  { to: '/prompts', label: 'Prompts' },
  { to: '/history', label: 'History' },
  { to: '/settings', label: 'Settings' },
]

export function AppNav() {
  return (
    <nav className="app-nav" aria-label="Main navigation">
      <div className="app-brand">
        <span className="app-brand-mark" aria-hidden />
        <div>
          <strong>OnPrem</strong>
          <span className="app-brand-sub">Image Generator</span>
        </div>
      </div>
      <ul className="nav-list">
        {NAV_ITEMS.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                isActive ? 'nav-link active' : 'nav-link'
              }
            >
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
