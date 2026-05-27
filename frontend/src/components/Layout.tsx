import { ReactNode, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { Modal } from './Modal';
import { HelpWidget } from './HelpWidget';

interface AppLayoutProps {
  children: ReactNode;
  title?: string;
}

const SvgDashboard = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
    <rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
  </svg>
);
const SvgAnalytics = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/>
    <line x1="6" y1="20" x2="6" y2="14"/>
  </svg>
);
const SvgUpload = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
    <polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
  </svg>
);
const SvgReview = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
    <polyline points="14 2 14 8 20 8"/>
    <line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
    <polyline points="10 9 9 9 8 9"/>
  </svg>
);
const SvgLogout = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
    <polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
  </svg>
);
const SvgMoon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
  </svg>
);
const SvgSun = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="4"/>
    <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>
  </svg>
);

function SuperNovaLogo({ size = 32 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="SuperNova AI logo"
    >
      <circle cx="32" cy="32" r="30" fill="url(#snGlow)" opacity="0.18" />
      {[0, 45, 90, 135, 180, 225, 270, 315].map((deg, i) => {
        const rad = (deg * Math.PI) / 180;
        const inner = i % 2 === 0 ? 14 : 11;
        const outer = i % 2 === 0 ? 31 : 26;
        const x1 = 32 + Math.cos(rad) * inner;
        const y1 = 32 + Math.sin(rad) * inner;
        const x2 = 32 + Math.cos(rad) * outer;
        const y2 = 32 + Math.sin(rad) * outer;
        return (
          <line
            key={deg}
            x1={x1} y1={y1} x2={x2} y2={y2}
            stroke={i % 2 === 0 ? '#0F766E' : '#14B8A6'}
            strokeWidth={i % 2 === 0 ? 3 : 2}
            strokeLinecap="round"
          />
        );
      })}
      <circle cx="32" cy="32" r="10" fill="url(#snCore)" />
      <circle cx="32" cy="32" r="4.5" fill="#ffffff" opacity="0.95" />
      <line x1="32" y1="18" x2="32" y2="22" stroke="#5EEAD4" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="32" y1="42" x2="32" y2="46" stroke="#5EEAD4" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="18" y1="32" x2="22" y2="32" stroke="#5EEAD4" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="42" y1="32" x2="46" y2="32" stroke="#5EEAD4" strokeWidth="1.5" strokeLinecap="round" />
      <defs>
        <radialGradient id="snGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#0F766E" />
          <stop offset="100%" stopColor="#0F766E" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="snCore" cx="40%" cy="35%" r="65%">
          <stop offset="0%" stopColor="#2DD4BF" />
          <stop offset="100%" stopColor="#0F766E" />
        </radialGradient>
      </defs>
    </svg>
  );
}

export function AppLayout({ children, title }: AppLayoutProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [logoutModal, setLogoutModal] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark'>(
    () => (typeof document !== 'undefined' && document.documentElement.getAttribute('data-theme') === 'dark') ? 'dark' : 'light'
  );

  function toggleTheme() {
    const next = theme === 'dark' ? 'light' : 'dark';
    if (typeof document !== 'undefined') document.documentElement.setAttribute('data-theme', next);
    try { localStorage.setItem('supernova-theme', next); } catch { /* ignore */ }
    setTheme(next);
  }

  async function handleLogout() {
    await logout();
    navigate('/login', { replace: true });
  }

  return (
    <div className="app-shell">
      {/* Sticky Top Bar */}
      <header className="top-bar">
        <div className="top-bar-left">
          <div className="top-bar-logo">
            <SuperNovaLogo size={32} />
            <span className="logo-text">SuperNova AI</span>
          </div>
          {title && <span className="top-bar-title">{title}</span>}
        </div>
        <div className="top-bar-right">
          <button
            className="top-bar-theme-toggle"
            onClick={toggleTheme}
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            aria-label="Toggle dark mode"
          >
            {theme === 'dark' ? <SvgSun /> : <SvgMoon />}
          </button>
          <div className="top-bar-user">
            <div className="top-bar-avatar">{user?.full_name?.[0] ?? '?'}</div>
            <div className="top-bar-user-info">
              <span className="top-bar-name">{user?.full_name}</span>
              <span className="top-bar-role">
                {user?.role === 'sonologist' ? 'Sonologist' : 'Reviewer'}
              </span>
            </div>
          </div>
          <button className="top-bar-logout" onClick={() => setLogoutModal(true)} title="Log out">
            <SvgLogout />
          </button>
        </div>
      </header>

      {/* Main Layout (Sidebar + Content) */}
      <div className="app-main-layout">
        <nav className="sidebar" aria-label="Main navigation">
          <ul className="sidebar-nav">
            {user?.role === 'sonologist' ? (
              <>
                <li>
                  <NavLink to="/dashboard" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
                    <SvgDashboard /> <span>Dashboard</span>
                  </NavLink>
                </li>
                <li>
                  <NavLink to="/upload" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
                    <SvgUpload /> <span>New Upload</span>
                  </NavLink>
                </li>
                <li>
                  <NavLink to="/analytics" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
                    <SvgAnalytics /> <span>Analytics</span>
                  </NavLink>
                </li>
              </>
            ) : (
              <>
                <li>
                  <NavLink to="/review" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
                    <SvgReview /> <span>Review Dashboard</span>
                  </NavLink>
                </li>
                <li>
                  <NavLink to="/analytics" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
                    <SvgAnalytics /> <span>Analytics</span>
                  </NavLink>
                </li>
              </>
            )}
          </ul>
        </nav>
        <main className="main-content">
          {children}
        </main>
      </div>

      <Modal
        open={logoutModal}
        title="Log out?"
        message="You will be returned to the login screen."
        confirmLabel="Log out"
        cancelLabel="Stay"
        onConfirm={handleLogout}
        onCancel={() => setLogoutModal(false)}
      />
      <HelpWidget />
    </div>
  );
}

/** Small breadcrumb strip (kept for Segmentation / Reannotate) */
export function Breadcrumb({ items }: { items: string[] }) {
  return (
    <nav className="breadcrumb" aria-label="Breadcrumb">
      {items.map((item, i) => (
        <span key={i}>
          {i > 0 && <span className="breadcrumb-sep"> / </span>}
          <span className={i === items.length - 1 ? 'breadcrumb-current' : 'breadcrumb-item'}>{item}</span>
        </span>
      ))}
    </nav>
  );
}
