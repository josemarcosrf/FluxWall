import { useSyncExternalStore } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { FORMATS, IPHONE_MODELS } from '../lib/data';
import { outputStore } from '../lib/store';
import { getTheme, subscribeTheme, switchTheme } from '../lib/theme';

export function TopBar(): React.JSX.Element {
  const output = useSyncExternalStore(outputStore.subscribe, outputStore.getSnapshot);
  const theme = useSyncExternalStore(subscribeTheme, getTheme);
  const devName = IPHONE_MODELS.find((m) => m.id === output.device);
  const fmtName = FORMATS.find((f) => f.id === output.format);

  return (
    <header className="topbar" data-od-id="topbar">
      <Link className="brand" to="/">
        FluxWall<small>wallpaper studio</small>
      </Link>
      <nav className="topnav">
        <NavLink to="/" data-page="index" end>
          Discover
        </NavLink>
        <NavLink to="/studio" data-page="studio">
          Studio
        </NavLink>
        <NavLink to="/library" data-page="library">
          My Exports
        </NavLink>
      </nav>
      <div className="topbar-right">
        <button
          className="theme-toggle"
          onClick={switchTheme}
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          aria-label="Toggle light/dark theme"
          data-theme-state={theme}
        >
          {theme === 'dark' ? (
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="4" />
              <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
            </svg>
          )}
        </button>
        <Link className="chip" to="/studio">
          <b>Device</b>
          <span className="num">{devName ? devName.name : output.device}</span>
        </Link>
        <Link className="chip hide-sm" to="/studio">
          <b>Export</b>
          <span className="num">{fmtName ? fmtName.name : output.format}</span>
        </Link>
      </div>
    </header>
  );
}
