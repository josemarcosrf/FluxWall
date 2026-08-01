// localStorage helpers + the small shared "output" store (device/format)
// that drives the topbar chips via useSyncExternalStore.

const PREFIX = 'fw.';

export function storeGet<T>(key: string, def: T): T {
  try {
    const v = localStorage.getItem(PREFIX + key);
    return v ? (JSON.parse(v) as T) : def;
  } catch {
    return def;
  }
}

export function storeSet(key: string, v: unknown): void {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(v));
  } catch {
    /* private-mode or quota errors: ignore */
  }
}

export interface OutputSnapshot {
  device: string;
  format: string;
}

let output: OutputSnapshot = {
  device: storeGet('device', '15_pro'),
  format: storeGet('format', 'live_photo'),
};

const outputListeners = new Set<() => void>();
function emitOutput(): void {
  outputListeners.forEach((l) => l());
}

export const outputStore = {
  subscribe(listener: () => void): () => void {
    outputListeners.add(listener);
    return () => {
      outputListeners.delete(listener);
    };
  },
  getSnapshot(): OutputSnapshot {
    return output;
  },
  setDevice(device: string): void {
    output = { ...output, device };
    storeSet('device', device);
    emitOutput();
  },
  setFormat(format: string): void {
    output = { ...output, format };
    storeSet('format', format);
    emitOutput();
  },
};
