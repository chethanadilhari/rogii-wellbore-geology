import { NavLink } from 'react-router-dom';
import type { ReactNode } from 'react';
import { ModelStatus } from '../common/ModelStatus';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: '⌂' },
  { to: '/predict', label: 'Predict Well', icon: '↗' },
  { to: '/model', label: 'Model Information', icon: '◎' },
  { to: '/about', label: 'About', icon: 'ⓘ' },
] as const;

interface AppShellProps {
  children: ReactNode;
  title?: string;
  mobileOpen: boolean;
  onToggleMobile: () => void;
  onCloseMobile: () => void;
}

export function AppShell({
  children,
  title = 'Rogii TVT Prediction',
  mobileOpen,
  onToggleMobile,
  onCloseMobile,
}: AppShellProps) {
  return (
    <div className={`app-shell${mobileOpen ? ' mobile-open' : ''}`}>
      <aside className="app-sidebar" aria-label="Primary">
        <div className="sidebar-brand">
          <div className="sidebar-brand-mark" aria-hidden="true">
            RW
          </div>
          <div className="sidebar-brand-copy">
            <strong>Rogii Wellbore</strong>
            <span>TVT trailing-section prediction</span>
          </div>
        </div>
        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `sidebar-link${isActive ? ' active' : ''}`
              }
              onClick={onCloseMobile}
            >
              <span className="nav-icon" aria-hidden="true">
                {item.icon}
              </span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">Wellbore geology · ML prediction</div>
      </aside>

      <div
        className="sidebar-backdrop"
        onClick={onCloseMobile}
        aria-hidden="true"
      />

      <div className="app-main">
        <header className="app-header">
          <div className="header-left">
            <button
              type="button"
              className="icon-btn header-menu-btn"
              aria-label={mobileOpen ? 'Close navigation' : 'Open navigation'}
              aria-expanded={mobileOpen}
              onClick={onToggleMobile}
            >
              ☰
            </button>
            <div className="header-title">{title}</div>
          </div>
          <div className="header-right">
            <ModelStatus />
          </div>
        </header>
        <main className="page">{children}</main>
      </div>
    </div>
  );
}
