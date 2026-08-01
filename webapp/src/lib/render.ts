// FluxWall — preview render engine.
// Real procedural math (Game of Life, Mandelbrot/Julia fields, complex-plane
// recurrences) rendered to canvas — mirrors what the FastAPI generator
// endpoints produce, low-res for preview performance. Ported from the
// prototype's assets/js/render.js.

import type { Params } from './types';

// ── Colormaps (matplotlib-style anchor stops) ─────────────────────
type Stop = [number, string];
type StopRgb = [number, number, number, number];

const CMAP_STOPS: Record<string, Stop[]> = {
  magma: [
    [0, '#000004'], [0.13, '#1d1147'], [0.3, '#51127c'], [0.46, '#82217c'], [0.62, '#b73779'], [0.78, '#de4a68'], [0.9, '#f7854f'], [1, '#f6d43e'],
  ],
  plasma: [
    [0, '#0d0887'], [0.2, '#46039f'], [0.35, '#7201a8'], [0.5, '#9c179e'], [0.63, '#bd3786'], [0.75, '#d8576b'], [0.86, '#ed7953'], [0.95, '#fb9f3a'], [1, '#f0f921'],
  ],
  viridis: [
    [0, '#440154'], [0.2, '#46327e'], [0.4, '#365c8d'], [0.55, '#277f8e'], [0.7, '#1fa187'], [0.85, '#4ac16d'], [0.95, '#a0da39'], [1, '#fde725'],
  ],
  inferno: [
    [0, '#000004'], [0.15, '#1f0c48'], [0.3, '#550f6d'], [0.45, '#88226a'], [0.58, '#a6365c'], [0.7, '#c64f5d'], [0.8, '#e06b45'], [0.9, '#f1983a'], [0.97, '#f4c830'], [1, '#fcffa4'],
  ],
  twilight: [
    [0, '#e2d9f1'], [0.15, '#b8b6e0'], [0.3, '#8c96cf'], [0.45, '#6c79bd'], [0.6, '#37529c'], [0.75, '#6b2f7f'], [0.88, '#b34979'], [1, '#f4b2c0'],
  ],
  turbo: [
    [0, '#30123b'], [0.14, '#3550a2'], [0.28, '#2472bd'], [0.42, '#0fa1ab'], [0.55, '#00c79a'], [0.7, '#70d26a'], [0.84, '#e0c73b'], [0.93, '#fc9422'], [1, '#b70d30'],
  ],
  hot: [
    [0, '#000000'], [0.3, '#3f0000'], [0.5, '#b30000'], [0.7, '#ff4d00'], [0.85, '#ffb300'], [1, '#fffdf0'],
  ],
  cool: [
    [0, '#0033ff'], [1, '#00ccff'],
  ],
  fire: [
    [0, '#000000'], [0.25, '#5a1200'], [0.45, '#9c2000'], [0.62, '#d44500'], [0.78, '#f27e00'], [0.9, '#ffc400'], [1, '#fff5d0'],
  ],
};

const LUTS: Record<string, Uint8Array> = {};

function cmapLUT(name: string): Uint8Array {
  const key = name || 'magma';
  if (LUTS[key]) return LUTS[key];
  const stops = CMAP_STOPS[key] || CMAP_STOPS.magma;
  const lut = new Uint8Array(256 * 3);
  const stopsRgb: StopRgb[] = stops.map(([p, hex]) => [
    p,
    parseInt(hex.slice(1, 3), 16),
    parseInt(hex.slice(3, 5), 16),
    parseInt(hex.slice(5, 7), 16),
  ]);
  for (let i = 0; i < 256; i++) {
    const t = i / 255;
    let s = 0;
    while (s < stopsRgb.length - 2 && t > stopsRgb[s + 1][0]) s++;
    const a = stopsRgb[s];
    const b = stopsRgb[s + 1];
    const k = b[0] === a[0] ? 0 : (t - a[0]) / (b[0] - a[0]);
    lut[i * 3] = a[1] + (b[1] - a[1]) * k;
    lut[i * 3 + 1] = a[2] + (b[2] - a[2]) * k;
    lut[i * 3 + 2] = a[3] + (b[3] - a[3]) * k;
  }
  LUTS[key] = lut;
  return lut;
}

function cmapFill(name: string, t: number): [number, number, number] {
  const lut = cmapLUT(name);
  const i = Math.floor((((t % 1) + 1) % 1) * 255.999);
  return [lut[i * 3], lut[i * 3 + 1], lut[i * 3 + 2]];
}

function cmapCss(name: string, t: number): string {
  const c = cmapFill(name, t);
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

// Seeded RNG (mulberry32) so a seed always reproduces the same soup
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ── Game of Life ───────────────────────────────────────────────────
const GOL_PATTERNS: Record<string, string> = {
  glider: '.o.\n..o\n.oo',
  gosper_gun:
    '........................o...........o....\n......................o.o...........o....\n............oo......oo............oo......\n...........o...o....oo............oo......\noo........o.....o...oo.........................\noo........o...o.oo....o.o........................\n..........o.....o.......o.........................\n...........o...o....................................\n............oo........................................',
  pulsar:
    '..ooo...ooo..\n.............\no....o.o....o\no....o.o....o\no....o.o....o\n..ooo...ooo..\n.............\n..ooo...ooo..\no....o.o....o\no....o.o....o\no....o.o....o\n.............\n..ooo...ooo..',
  pentadecathlon: '..o....o..\n..o....o..\n..o....o..\noooo..oooo\n..o....o..\n..o....o..\n..o....o..',
  acorn: '.....o.....\n...o.o.....\n....oo..o..\n..o....o...\n...........',
  r_pentomino: '.oo\noo.\n.o.',
  diehard: '......o.\noo......\n.o...ooo',
};

function parsePattern(str: string, gw: number, gh: number): [number, number][] {
  const rows = str.split('\n');
  const cells: [number, number][] = [];
  const rh = rows.length;
  const rw = rows[0].length;
  const ox = Math.floor((gw - rw) / 2);
  const oy = Math.floor((gh - rh) / 2);
  for (let y = 0; y < rh; y++)
    for (let x = 0; x < rw; x++) if (rows[y][x] === 'o') cells.push([ox + x, oy + y]);
  return cells;
}

interface GolState {
  alive: Uint8Array;
  age: Float32Array;
  gw: number;
  gh: number;
}

function golInit(params: Params): GolState {
  const gw = Math.min(Number(params.grid_width) || 300, 420);
  const gh = Math.min(Number(params.grid_height) || 650, 640);
  const alive = new Uint8Array(gw * gh);
  const age = new Float32Array(gw * gh);
  const rng = mulberry32(params.seed && params.seed !== 0 ? Number(params.seed) : 1337);
  const pattern = String(params.initial_pattern || 'random');
  if (pattern === 'random') {
    for (let i = 0; i < gw * gh; i++) if (rng() < 0.16) alive[i] = 1;
  } else if (GOL_PATTERNS[pattern]) {
    parsePattern(GOL_PATTERNS[pattern], gw, gh).forEach(([x, y]) => {
      if (x >= 0 && y >= 0 && x < gw && y < gh) alive[y * gw + x] = 1;
    });
  }
  return { alive, age, gw, gh };
}

function golStep(state: GolState, birth: string, survive: string): void {
  const { alive, age, gw, gh } = state;
  const next = new Uint8Array(gw * gh);
  const b = birth.split('').map(Number);
  const s = survive.split('').map(Number);
  const bSet: Record<number, boolean> = {};
  const sSet: Record<number, boolean> = {};
  b.forEach((n) => {
    bSet[n] = true;
  });
  s.forEach((n) => {
    sSet[n] = true;
  });
  for (let y = 0; y < gh; y++) {
    for (let x = 0; x < gw; x++) {
      let n = 0;
      for (let dy = -1; dy <= 1; dy++)
        for (let dx = -1; dx <= 1; dx++) {
          if (dx === 0 && dy === 0) continue;
          let nx = x + dx;
          let ny = y + dy;
          if (nx < 0) nx = gw - 1;
          if (nx >= gw) nx = 0;
          if (ny < 0) ny = gh - 1;
          if (ny >= gh) ny = 0;
          n += alive[ny * gw + nx];
        }
      const i = y * gw + x;
      if (alive[i]) {
        next[i] = sSet[n] ? 1 : 0;
        if (next[i]) age[i] += 1;
        else age[i] = 0;
      } else if (bSet[n]) {
        next[i] = 1;
        age[i] = 0;
      }
    }
  }
  state.alive = next;
}

function golDraw(state: GolState, params: Params, ctx: CanvasRenderingContext2D, w: number, h: number, phase: number): void {
  const { alive, age, gw, gh } = state;
  ctx.fillStyle = String(params.color_dead || '#000000');
  ctx.fillRect(0, 0, w, h);
  const bx = w / gw;
  const by = h / gh;
  const trail = Math.max(1, Math.round(Number(params.trail_length) || 1));
  const decay = params.trail_decay != null ? Number(params.trail_decay) : 0.95;
  const trailCmap = String(params.trail_colormap || 'plasma');
  const liveColor = String(params.color_live || '#ffffff');
  void decay;
  for (let y = 0; y < gh; y++) {
    for (let x = 0; x < gw; x++) {
      const i = y * gw + x;
      if (!alive[i]) continue;
      const a = Math.min(1, age[i] / trail);
      const c = a >= 1 ? cmapCss(trailCmap, (age[i] - trail) / 20 + phase) : liveColor;
      ctx.fillStyle = c;
      ctx.fillRect(x * bx, y * by, Math.ceil(bx) + 1, Math.ceil(by) + 1);
    }
  }
}

// ── Mandelbrot / Julia fields ──────────────────────────────────────
function fractalField(kind: string, params: Params, w: number, h: number, phase: number, frame: number): Float32Array {
  const out = new Float32Array(w * h);
  const maxIter = Math.min(Number(params.max_iter) || 300, 140);
  const smooth = params.smooth_coloring !== false;
  const zoom = Number(params.zoom) || 1;
  const cx = params.center_x != null ? Number(params.center_x) : -0.5;
  const cy = params.center_y != null ? Number(params.center_y) : 0.0;
  const zf = (Number(params.zoom_factor_per_frame) || 1.0) - 1;

  if (kind === 'julia') {
    const mode = String(params.animation_mode || 'spin');
    const speed = (Number(params.spin_speed) || 1) * 0.5;
    const radius = Number(params.spin_radius) || 0.7885;
    let c = { r: Number(params.c_real) || 0, i: Number(params.c_imag) || 0 };
    if (mode === 'spin' || mode === 'spin_zoom') {
      const ang = phase * Math.PI * 2 * speed;
      c = { r: c.r + radius * Math.cos(ang), i: c.i + radius * Math.sin(ang) };
    }
    const z = zoom * Math.pow(1 + zf, frame * 0.5);
    for (let j = 0; j < h; j++) {
      const y = ((2 * j) / h - 1) / z;
      for (let i = 0; i < w; i++) {
        const x = ((2 * i) / w - 1) / z;
        let zr = x;
        let zi = y;
        let iter = 0;
        while (iter < maxIter) {
          const r2 = zr * zr;
          const i2 = zi * zi;
          if (r2 + i2 > 4) break;
          zi = 2 * zr * zi + c.i;
          zr = r2 - i2 + c.r;
          iter++;
        }
        out[j * w + i] =
          iter >= maxIter ? maxIter : smooth ? iter + 1 - Math.log2(Math.log(Math.sqrt(zr * zr + zi * zi))) : iter;
      }
    }
    return out;
  }

  const z = zoom * Math.pow(1 + zf, frame * 0.5);
  const spanX = 3.2 / z;
  const spanY = 2.4 / z;
  for (let j = 0; j < h; j++) {
    const y = cy - spanY / 2 + (spanY * j) / (h - 1);
    for (let i = 0; i < w; i++) {
      const x = cx - spanX / 2 + (spanX * i) / (w - 1);
      let zr = 0;
      let zi = 0;
      let iter = 0;
      while (iter < maxIter) {
        const r2 = zr * zr;
        const i2 = zi * zi;
        if (r2 + i2 > 4) break;
        zi = 2 * zr * zi + y;
        zr = r2 - i2 + x;
        iter++;
      }
      out[j * w + i] =
        iter >= maxIter ? maxIter : smooth ? iter + 1 - Math.log2(Math.log(Math.sqrt(zr * zr + zi * zi))) : iter;
    }
  }
  return out;
}

function fieldToImage(field: Float32Array, w: number, h: number, cmap: string, cycles: number, phase: number): ImageData {
  const img = new ImageData(w, h);
  const lut = cmapLUT(cmap);
  const d = img.data;
  for (let i = 0; i < w * h; i++) {
    let t = field[i] * (cycles || 1) + phase;
    t = ((t % 1) + 1) % 1;
    const idx = Math.floor(t * 255.999);
    d[i * 4] = lut[idx * 3];
    d[i * 4 + 1] = lut[idx * 3 + 1];
    d[i * 4 + 2] = lut[idx * 3 + 2];
    d[i * 4 + 3] = 255;
  }
  return img;
}

// ── Flowing curves (complex-plane recurrences) ─────────────────────
function curveXY(
  mode: string,
  steps: number,
  stepSize: number,
  omega: number,
  amp: number,
  freq: number,
  exp: number,
  tt: number,
): { xs: Float64Array; ys: Float64Array } {
  const xs = new Float64Array(steps + 1);
  const ys = new Float64Array(steps + 1);
  let rx = 0;
  let ry = 0;
  for (let n = 1; n <= steps; n++) {
    let phi: number;
    if (mode === 'prescribed') {
      const a = Math.pow(2000 - n, 1.5) / (3000 - n);
      const inner = 10 * Math.cos(100 * tt) * Math.sin(0.05 * n + 30 * tt) + 10 * tt;
      phi = 2 * Math.PI * tt * inner - 1.8 * n * tt + Math.PI / 2;
      rx += a * Math.cos(phi);
      ry += a * Math.sin(phi);
    } else {
      if (mode === 'linear') phi = omega * n + tt;
      else if (mode === 'log') phi = omega * Math.log(n + 1) + tt;
      else if (mode === 'sqrt') phi = omega * Math.sqrt(n) + tt;
      else if (mode === 'sin') phi = omega * n + amp * Math.sin(freq * n + tt);
      else if (mode === 'golden') phi = omega * n * Math.PI * (3 - Math.sqrt(5)) + tt;
      else phi = omega * Math.pow(n, exp) + tt;
      const A = stepSize * (1 + amp * Math.sin(freq * n + tt * 0.5));
      rx += A * Math.cos(phi);
      ry += A * Math.sin(phi);
    }
    xs[n] = rx;
    ys[n] = ry;
  }
  return { xs, ys };
}

export function curveDraw(params: Params, ctx: CanvasRenderingContext2D, w: number, h: number, phase: number): void {
  const p = curveXY(
    String(params.mode || 'sin'),
    Math.min(Number(params.steps) || 2000, 2000),
    Number(params.step_size) || 0.008,
    Number(params.omega) || 0.15,
    Number(params.mod_amp) || 0.5,
    Number(params.mod_freq) || 0.05,
    Number(params.exp) || 0.5,
    (Number(params.t_start) || 0) + (((phase % 1) + 1) % 1) * ((params.t_end != null ? Number(params.t_end) : 1) - (Number(params.t_start) || 0)),
  );
  const n = p.xs.length - 1;
  let xmin = Infinity;
  let xmax = -Infinity;
  let ymin = Infinity;
  let ymax = -Infinity;
  for (let i = 0; i <= n; i++) {
    if (p.xs[i] < xmin) xmin = p.xs[i];
    if (p.xs[i] > xmax) xmax = p.xs[i];
    if (p.ys[i] < ymin) ymin = p.ys[i];
    if (p.ys[i] > ymax) ymax = p.ys[i];
  }
  const pad = 0.08;
  const sx = Math.max(xmax - xmin, 1e-10);
  const sy = Math.max(ymax - ymin, 1e-10);
  const cxm = (xmin + xmax) / 2;
  const cym = (ymin + ymax) / 2;
  const aspect = w / h;
  let xspan: number;
  let yspan: number;
  if (sx / sy > aspect) {
    xspan = sx * (1 + pad);
    yspan = xspan / aspect;
  } else {
    yspan = sy * (1 + pad);
    xspan = yspan * aspect;
  }
  const kx = w / xspan;
  const ky = h / yspan;
  const ox = w / 2 - cxm * kx;
  const oy = h / 2 - cym * ky;
  ctx.fillStyle = '#000000';
  ctx.fillRect(0, 0, w, h);
  const cmap = String(params.colormap || 'magma');
  const lw = Math.max(0.4, (Number(params.line_width) || 0.6) * (w / 320));
  ctx.lineWidth = lw;
  ctx.globalAlpha = params.alpha != null ? Number(params.alpha) : 0.85;
  ctx.lineJoin = 'round';
  const buckets = 48;
  const perBucket = Math.max(1, Math.floor(n / buckets));
  for (let b = 0; b < buckets; b++) {
    const s0 = b * perBucket;
    const s1 = Math.min((b + 1) * perBucket, n);
    if (s1 <= s0) continue;
    ctx.strokeStyle = cmapCss(cmap, b / buckets + phase * 0.15);
    ctx.beginPath();
    ctx.moveTo(p.xs[s0] * kx + ox, p.ys[s0] * ky + oy);
    for (let i = s0 + 1; i <= s1; i++) ctx.lineTo(p.xs[i] * kx + ox, p.ys[i] * ky + oy);
    ctx.stroke();
  }
  ctx.globalAlpha = 1;
}

// ── Preview engine ─────────────────────────────────────────────────
// Mirrors the MJPEG stream contract: start/stop + per-frame ticks.
// play/pause only toggles the source; phase + GOL state are preserved.
export class PreviewEngine {
  private canvas: HTMLCanvasElement | null = null;
  private generator: string | null = null;
  private params: Params = {};
  private playing = false;
  private phase = 0;
  private frame = 0;
  private last = 0;
  private raf = 0;
  private gol: GolState | null = null;

  isPlaying(): boolean {
    return this.playing;
  }

  start(canvas: HTMLCanvasElement, generator: string, params: Params): void {
    this.stop();
    if (!canvas) return;
    this.canvas = canvas;
    this.generator = generator;
    this.params = params;
    this.playing = true;
    this.phase = 0;
    this.frame = 0;
    if (generator === 'game_of_life') this.gol = golInit(params);
    this.loop();
  }

  private loop(): void {
    const tick = (now: number): void => {
      if (!this.playing) return;
      const dt = this.last ? now - this.last : 0;
      this.last = now;
      this.phase += (dt / 1000) * (this.generator === 'flowing_curve' ? 0.14 : 0.1);
      this.frame++;
      this.render();
      this.raf = requestAnimationFrame(tick);
    };
    this.raf = requestAnimationFrame(tick);
  }

  private render(): void {
    if (!this.canvas || !this.generator) return;
    const w = this.canvas.width;
    const h = this.canvas.height;
    const ctx = this.canvas.getContext('2d');
    if (!w || !h || !ctx) return;
    const params = this.params;
    if (this.generator === 'game_of_life') {
      golStep(this.gol as GolState, String(params.rule_birth || '3'), String(params.rule_survive || '23'));
      golDraw(this.gol as GolState, params, ctx, w, h, this.phase);
    } else if (this.generator === 'mandelbrot' || this.generator === 'julia') {
      const fw = 96;
      const fh = 208;
      const field = fractalField(this.generator, params, fw, fh, this.phase, this.frame);
      const img = fieldToImage(field, fw, fh, String(params.colormap || 'magma'), (1 / (Number(params.max_iter) || 300)) * 12, this.phase);
      const tmp = document.createElement('canvas');
      tmp.width = fw;
      tmp.height = fh;
      tmp.getContext('2d')!.putImageData(img, 0, 0);
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(tmp, 0, 0, w, h);
    } else if (this.generator === 'flowing_curve') {
      curveDraw(params, ctx, w, h, this.phase);
    }
  }

  pause(): void {
    this.playing = false;
  }

  play(): void {
    if (this.playing || !this.canvas) return;
    this.playing = true;
    this.last = 0;
    this.loop();
  }

  reset(generator: string, params: Params): void {
    this.phase = 0;
    this.frame = 0;
    this.last = 0;
    if (generator === 'game_of_life') this.gol = golInit(params);
  }

  stop(): void {
    if (this.raf) cancelAnimationFrame(this.raf);
    this.raf = 0;
    this.last = 0;
  }
}

// static single frame for thumbnails
export function renderStill(canvas: HTMLCanvasElement, generator: string, params: Params, phase = 0): void {
  if (!canvas || !canvas.getContext) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  if (generator === 'game_of_life') {
    const state = golInit(params);
    for (let i = 0; i < 24; i++) golStep(state, String(params.rule_birth || '3'), String(params.rule_survive || '23'));
    golDraw(state, params, ctx, canvas.width, canvas.height, phase || 0);
  } else if (generator === 'mandelbrot' || generator === 'julia') {
    const fw = 40;
    const fh = 87;
    const field = fractalField(generator, params, fw, fh, 0, 0);
    const img = fieldToImage(field, fw, fh, String(params.colormap || 'magma'), (1 / (Number(params.max_iter) || 300)) * 12, 0);
    const tmp = document.createElement('canvas');
    tmp.width = fw;
    tmp.height = fh;
    tmp.getContext('2d')!.putImageData(img, 0, 0);
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(tmp, 0, 0, canvas.width, canvas.height);
  } else if (generator === 'flowing_curve') {
    curveDraw(params, ctx, canvas.width, canvas.height, 0.62);
  }
}

// ── CMAP gradient swatch builder ───────────────────────────────────
export function cmapSwatch(name: string): string {
  const cv = document.createElement('canvas');
  cv.width = 160;
  cv.height = 20;
  const ctx = cv.getContext('2d')!;
  const lut = cmapLUT(name);
  for (let x = 0; x < 160; x++) {
    const idx = Math.floor((x / 160) * 255);
    ctx.fillStyle = `rgb(${lut[idx * 3]},${lut[idx * 3 + 1]},${lut[idx * 3 + 2]})`;
    ctx.fillRect(x, 0, 1, 20);
  }
  return cv.toDataURL();
}
