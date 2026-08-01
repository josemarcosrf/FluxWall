// FluxWall — mocked data layer. Mirrors the FastAPI contract 1:1
// (src/fluxwall/api/routes.py + core/models.py). Swap the real base URL in
// later without touching the UI.
import type { ExportFormat, Generator, IphoneModel, Params, Preset } from './types';

export const IPHONE_MODELS: IphoneModel[] = [
  { id: '15_pro_max', name: 'iPhone 15/16 Pro Max', w: 1290, h: 2796 },
  { id: '15_pro', name: 'iPhone 15/16 Pro', w: 1179, h: 2556 },
  { id: '14_pro', name: 'iPhone 14/13/12 Pro', w: 1170, h: 2532 },
  { id: 'se', name: 'iPhone SE / 8', w: 750, h: 1334 },
];

export const COLORMAPS: string[] = [
  'magma',
  'plasma',
  'viridis',
  'inferno',
  'twilight',
  'turbo',
  'hot',
  'cool',
  'fire',
];

export const FORMATS: ExportFormat[] = [
  { id: 'mp4', name: 'MP4', desc: 'General video', ext: 'mp4' },
  { id: 'mov', name: 'MOV', desc: 'iOS-compatible video', ext: 'mov' },
  { id: 'live_photo', name: 'Live Photo', desc: 'HEIC + MOV — iOS lock screen', ext: 'livephoto' },
];

// GET /generators — plugin registry, schema-driven forms
export const GENERATORS: Generator[] = [
  {
    name: 'game_of_life',
    display_name: 'Game of Life',
    description: "Conway's Game of Life with customizable rules and color trails",
    unimplemented: false,
    glyph: 'grid',
    param_schema: {
      properties: [
        { id: 'initial_pattern', label: 'Initial pattern', type: 'enum', default: 'random',
          options: ['random', 'gosper_gun', 'glider', 'pulsar', 'pentadecathlon', 'acorn', 'r_pentomino', 'diehard'] },
        { id: 'rule_birth', label: 'Birth rule', type: 'text', pattern: '^[0-8]+$', default: '3', note: 'Digit set 0–8, e.g. "3"' },
        { id: 'rule_survive', label: 'Survival rule', type: 'text', pattern: '^[0-8]+$', default: '23', note: 'Digit set 0–8, e.g. "23"' },
        { id: 'wrap_edges', label: 'Wrap edges', type: 'bool', default: true },
        { id: 'grid_width', label: 'Grid width', type: 'int', min: 50, max: 1000, default: 300, unit: 'cells' },
        { id: 'grid_height', label: 'Grid height', type: 'int', min: 50, max: 1000, default: 650, unit: 'cells' },
        { id: 'trail_length', label: 'Trail length', type: 'int', min: 1, max: 100, default: 30, unit: 'frames' },
        { id: 'trail_decay', label: 'Trail decay', type: 'float', min: 0, max: 1, step: 0.01, default: 0.95 },
        { id: 'trail_colormap', label: 'Trail colormap', type: 'cmap', default: 'plasma' },
        { id: 'color_live', label: 'Live cell', type: 'color', default: '#ffffff' },
        { id: 'color_dead', label: 'Background', type: 'color', default: '#000000' },
      ],
    },
    presets: [
      { name: 'gosper_gun', description: 'The classic infinite glider generator', params: { initial_pattern: 'gosper_gun', trail_length: 40, trail_decay: 0.97 } },
      { name: 'glider_swarm', description: 'Multiple gliders in random directions', params: { initial_pattern: 'glider' } },
      { name: 'random_soup', description: 'Random seed soup with long trails', params: { initial_pattern: 'random', trail_length: 50 } },
      { name: 'pulsar', description: 'The classic 3-period pulsar oscillator', params: { initial_pattern: 'pulsar', trail_length: 20 } },
      { name: 'pentadecathlon', description: 'A 15-period orthogonal spaceship', params: { initial_pattern: 'pentadecathlon' } },
      { name: 'acorn', description: 'Slow-growing acorn, ~5,206 generations to fill', params: { initial_pattern: 'acorn', trail_length: 60 } },
      { name: 'r_pentomino', description: 'The chaotic five-cell methuselah', params: { initial_pattern: 'r_pentomino' } },
      { name: 'diehard', description: 'Dies out after 130 generations', params: { initial_pattern: 'diehard' } },
    ],
  },
  {
    name: 'mandelbrot',
    display_name: 'Mandelbrot Set',
    description: 'Classic Mandelbrot fractal with smooth zoom and color cycling',
    unimplemented: false,
    glyph: 'fractal',
    param_schema: {
      properties: [
        { id: 'center_x', label: 'Center X', type: 'float', min: -2, max: 2, step: 0.0001, default: -0.5 },
        { id: 'center_y', label: 'Center Y', type: 'float', min: -2, max: 2, step: 0.0001, default: 0.0 },
        { id: 'zoom', label: 'Zoom', type: 'float', min: 0.1, max: 1e12, step: 0.1, default: 1.0 },
        { id: 'max_iter', label: 'Max iterations', type: 'int', min: 50, max: 10000, default: 500, unit: 'iters' },
        { id: 'zoom_factor_per_frame', label: 'Zoom / frame', type: 'float', min: 1, max: 1.5, step: 0.005, default: 1.02 },
        { id: 'color_cycle_speed', label: 'Color cycle speed', type: 'float', min: 0, max: 1, step: 0.01, default: 0.05 },
        { id: 'smooth_coloring', label: 'Smooth coloring', type: 'bool', default: true },
      ],
    },
    presets: [
      { name: 'classic', description: 'Full Mandelbrot set at default zoom', params: { center_x: -0.5, center_y: 0.0, zoom: 1.0, max_iter: 300, zoom_factor_per_frame: 1.0, color_cycle_speed: 0.0 } },
      { name: 'seahorse_valley', description: 'Deep seahorse tendrils near the valley', params: { center_x: -0.744, center_y: 0.149, zoom: 600, max_iter: 800, zoom_factor_per_frame: 1.01 } },
      { name: 'elephant_valley', description: 'Elephant trunk spirals on the right arm', params: { center_x: 0.274, center_y: 0.482, zoom: 250, max_iter: 600, zoom_factor_per_frame: 1.012 } },
      { name: 'triple_spiral', description: 'Three-branch spiral detail', params: { center_x: -0.7436, center_y: 0.1314, zoom: 2000, max_iter: 900, zoom_factor_per_frame: 1.008 } },
      { name: 'minibrot', description: 'A full minibrot with orbiting miniatures', params: { center_x: -0.7435, center_y: 0.1314, zoom: 30000, max_iter: 1500, zoom_factor_per_frame: 1.006 } },
    ],
  },
  {
    name: 'julia',
    display_name: 'Julia Set',
    description: 'Julia set fractal with rotation and zoom animations',
    unimplemented: false,
    glyph: 'spiral',
    param_schema: {
      properties: [
        { id: 'c_real', label: 'c — real', type: 'float', min: -2, max: 2, step: 0.0001, default: -0.7 },
        { id: 'c_imag', label: 'c — imag', type: 'float', min: -2, max: 2, step: 0.0001, default: 0.27015 },
        { id: 'zoom', label: 'Zoom', type: 'float', min: 0.1, max: 1e10, step: 0.1, default: 1.0 },
        { id: 'max_iter', label: 'Max iterations', type: 'int', min: 50, max: 10000, default: 300, unit: 'iters' },
        { id: 'animation_mode', label: 'Animation', type: 'enum', default: 'spin', options: ['spin', 'zoom', 'spin_zoom'] },
        { id: 'spin_radius', label: 'Spin radius', type: 'float', min: 0.1, max: 2, step: 0.01, default: 0.7885 },
        { id: 'spin_speed', label: 'Spin speed', type: 'float', min: 0, max: 2, step: 0.05, default: 1.0 },
        { id: 'zoom_factor_per_frame', label: 'Zoom / frame', type: 'float', min: 1, max: 1.5, step: 0.005, default: 1.02 },
        { id: 'color_cycle_speed', label: 'Color cycle speed', type: 'float', min: 0, max: 1, step: 0.01, default: 0.03 },
        { id: 'smooth_coloring', label: 'Smooth coloring', type: 'bool', default: true },
      ],
    },
    presets: [
      { name: 'douady_rabbit', description: 'Classic rabbit-shaped Julia set', params: { c_real: -0.123, c_imag: 0.745, zoom: 1.2, max_iter: 300, animation_mode: 'spin' } },
      { name: 'dendrite', description: 'Tree-like branching Julia set', params: { c_real: 0.0, c_imag: -1.0, zoom: 1.5, max_iter: 300, animation_mode: 'spin' } },
      { name: 'spiral', description: 'Elegant spiral pattern', params: { c_real: -0.7, c_imag: 0.27015, zoom: 1.0, max_iter: 300, animation_mode: 'spin_zoom' } },
      { name: 'cauliflower', description: 'Cauliflower-like Julia set', params: { c_real: -0.12, c_imag: -0.77, zoom: 1.0, max_iter: 300, animation_mode: 'spin' } },
      { name: 'lightning', description: 'Lightning bolt patterns', params: { c_real: 0.3, c_imag: 0.5, zoom: 1.5, max_iter: 400, animation_mode: 'spin_zoom' } },
      { name: 'basilica', description: 'Basilica — the douady rabbit sibling', params: { c_real: -1.0, c_imag: 0.0, zoom: 1.0, max_iter: 300, animation_mode: 'spin' } },
      { name: 'siegel_disk', description: 'Golden-mean Siegel disk', params: { c_real: -0.39054, c_imag: -0.58679, zoom: 1.0, max_iter: 300, animation_mode: 'spin' } },
    ],
  },
  {
    name: 'flowing_curve',
    display_name: 'Flowing Curves',
    description: 'Complex-plane recurrence curves — flowing fractal lines',
    unimplemented: false,
    next_release: true,
    glyph: 'curve',
    param_schema: {
      properties: [
        { id: 'mode', label: 'Curve mode', type: 'enum', default: 'sin', options: ['sin', 'linear', 'log', 'sqrt', 'golden', 'poly', 'prescribed'] },
        { id: 'steps', label: 'Steps / frame', type: 'int', min: 100, max: 20000, default: 2000, unit: 'pts' },
        { id: 'step_size', label: 'Step magnitude', type: 'float', min: 0.001, max: 0.1, step: 0.001, default: 0.008 },
        { id: 'omega', label: 'Angular frequency', type: 'float', min: 0.01, max: 5, step: 0.01, default: 0.15 },
        { id: 'exp', label: 'Power exponent', type: 'float', min: 0.1, max: 5, step: 0.1, default: 0.5, note: 'poly mode only' },
        { id: 'mod_freq', label: 'Modulation freq', type: 'float', min: 0, max: 1, step: 0.005, default: 0.05 },
        { id: 'mod_amp', label: 'Modulation amp', type: 'float', min: 0, max: 2, step: 0.05, default: 0.5 },
        { id: 'adaptive', label: 'Adaptive timing', type: 'bool', default: false, note: 'Concentrate frames where the curve changes fastest' },
        { id: 'adaptive_strength', label: 'Adaptive strength', type: 'float', min: 0, max: 1, step: 0.05, default: 0.3 },
        { id: 't_start', label: 't start', type: 'float', min: 0, max: 1, step: 0.01, default: 0.0 },
        { id: 't_end', label: 't end', type: 'float', min: 0, max: 1, step: 0.01, default: 1.0, note: 'Narrow both to zoom into a slice of time' },
        { id: 'line_width', label: 'Line width', type: 'float', min: 0.1, max: 3, step: 0.1, default: 0.6 },
        { id: 'alpha', label: 'Line alpha', type: 'float', min: 0.1, max: 1, step: 0.05, default: 0.85 },
        { id: 'supersample', label: 'Motion blur', type: 'int', min: 1, max: 16, default: 1, unit: 'sub-samples' },
      ],
    },
    presets: [
      { name: 'tendrils', description: 'Tangly kelp-like tendrils that wave and drift (sin)', params: { mode: 'sin', steps: 2000, step_size: 0.008, omega: 0.15, mod_freq: 0.05, mod_amp: 0.5 } },
      { name: 'phyllotaxis', description: 'Golden-angle branching (golden)', params: { mode: 'golden', omega: 0.618, step_size: 0.015 } },
      { name: 'log_whorls', description: 'Tight logarithmic whorls that bloom outward', params: { mode: 'log', omega: 2.0, step_size: 0.02 } },
      { name: 'comet_tails', description: 'Wide sweeping arcs, comet-like tails (sqrt)', params: { mode: 'sqrt', omega: 0.5, step_size: 0.02 } },
      { name: 'power_burst', description: 'Power-law spiral, star-shaped bursts (poly)', params: { mode: 'poly', omega: 0.5, exp: 2.2, step_size: 0.015 } },
      { name: 'prescribed', description: 'The dense rapidly-evolving prescribed recurrence', params: { mode: 'prescribed' } },
    ],
  },
  {
    name: 'l_system',
    display_name: 'L-System',
    description: 'Lindenmayer system fractal plants and trees',
    unimplemented: true,
    glyph: 'branch',
    param_schema: {
      properties: [
        { id: 'axiom', label: 'Axiom', type: 'text', default: 'X' },
        { id: 'angle', label: 'Branch angle', type: 'float', min: 1, max: 180, step: 0.5, default: 25.0, unit: 'deg' },
        { id: 'iterations', label: 'Iterations', type: 'int', min: 1, max: 10, default: 6, unit: 'rewrites' },
        { id: 'line_width', label: 'Line width', type: 'float', min: 0.5, max: 10, step: 0.1, default: 2.0 },
        { id: 'color_by_depth', label: 'Color by depth', type: 'bool', default: true },
        { id: 'color_scheme', label: 'Color scheme', type: 'enum', default: 'plant', options: ['plant', 'rainbow', 'fire', 'mono'] },
        { id: 'animation_mode', label: 'Animation', type: 'enum', default: 'grow', options: ['grow', 'rotate', 'wind'] },
        { id: 'wind_strength', label: 'Wind strength', type: 'float', min: 0, max: 1, step: 0.05, default: 0.0 },
      ],
    },
    presets: [
      { name: 'fractal_tree', description: 'Classic binary tree fractal', params: { axiom: 'F', angle: 22.5, iterations: 5 } },
      { name: 'barnsley_fern', description: 'Iconic fern fractal', params: { axiom: 'X', angle: 25, iterations: 6 } },
      { name: 'dragon_curve', description: 'Heighway dragon curve', params: { axiom: 'FX', angle: 90, iterations: 12 } },
      { name: 'koch_snowflake', description: 'Classic Koch snowflake', params: { axiom: 'F--F--F', angle: 60, iterations: 5 } },
      { name: 'plant', description: 'Organic plant-like structure', params: { axiom: 'X', angle: 25, iterations: 6 } },
    ],
  },
  {
    name: 'color_cycle',
    display_name: 'Color Cycle',
    description: 'Procedural color cycling patterns (plasma, fire, aurora, flow)',
    unimplemented: true,
    glyph: 'waves',
    param_schema: {
      properties: [
        { id: 'pattern_type', label: 'Pattern', type: 'enum', default: 'plasma', options: ['plasma', 'fire', 'aurora', 'reaction_diffusion', 'flow_field'] },
        { id: 'frequency', label: 'Frequency', type: 'float', min: 0.001, max: 1, step: 0.001, default: 0.01 },
        { id: 'speed', label: 'Speed', type: 'float', min: 0.01, max: 2, step: 0.01, default: 0.1 },
        { id: 'turbulence', label: 'Turbulence', type: 'float', min: 0, max: 1, step: 0.05, default: 0.0 },
        { id: 'octaves', label: 'Octaves', type: 'int', min: 1, max: 8, default: 4 },
        { id: 'persistence', label: 'Persistence', type: 'float', min: 0.1, max: 1, step: 0.05, default: 0.5 },
      ],
    },
    presets: [
      { name: 'plasma', description: 'Classic plasma effect', params: { pattern_type: 'plasma', frequency: 0.01, speed: 0.1 } },
      { name: 'fire', description: 'Animated fire simulation', params: { pattern_type: 'fire', frequency: 0.02, speed: 0.15 } },
      { name: 'aurora', description: 'Northern lights effect', params: { pattern_type: 'aurora', frequency: 0.005, speed: 0.05 } },
    ],
  },
];

// GET /presets?generator=
export function presetsFor(generator: string): Preset[] {
  const g = GENERATORS.find((x) => x.name === generator);
  return g ? g.presets : [];
}

export function generatorByName(name: string): Generator | undefined {
  return GENERATORS.find((x) => x.name === name);
}

/** Schema defaults for a generator (used as the base of every params object). */
export function defaultsFor(g: Generator): Params {
  const d: Params = {};
  g.param_schema.properties.forEach((f) => {
    d[f.id] = f.default ?? null;
  });
  return d;
}

// Resolution helper for a device id
export function resolutionFor(deviceId: string): IphoneModel {
  const m = IPHONE_MODELS.find((x) => x.id === deviceId) || IPHONE_MODELS[0];
  return m;
}
