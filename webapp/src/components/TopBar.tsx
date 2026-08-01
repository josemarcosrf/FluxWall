import { useSyncExternalStore } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { FORMATS, IPHONE_MODELS } from '../lib/data';
import { outputStore } from '../lib/store';

export function TopBar(): React.JSX.Element {
  const output = useSyncExternalStore(outputStore.subscribe, outputStore.getSnapshot);
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
