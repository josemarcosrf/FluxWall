// Light/dark theme store, persisted to localStorage and applied to
// <html data-theme="light|dark">. Call initTheme() once at app mount.
import { storeGet, storeSet } from './store';

export type Theme = 'dark' | 'light';

const KEY = 'theme';
const listeners = new Set<() => void>();

function read(): Theme {
  // Saved preference wins; otherwise keep the original dark-studio look.
  return storeGet<Theme | null>(KEY, null) === 'light' ? 'light' : 'dark';
}

let theme: Theme = 'dark';
let initialized = false;

function apply(): void {
  document.documentElement.dataset.theme = theme;
}

/** Apply the persisted theme to <html>. Call at app mount before render. */
export function initTheme(): void {
  if (initialized) return;
  initialized = true;
  theme = read();
  apply();
}

export function getTheme(): Theme {
  return theme;
}

export function switchTheme(): void {
  theme = theme === 'dark' ? 'light' : 'dark';
  storeSet(KEY, theme);
  apply();
  listeners.forEach((l) => l());
}

export function subscribeTheme(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}