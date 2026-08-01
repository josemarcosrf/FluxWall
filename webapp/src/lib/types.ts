// Shared types for FluxWall — mirror the FastAPI contract 1:1
// (src/fluxwall/api/routes.py + core/models.py) so swapping in the real base
// URL later is a config change, not a rewrite.

export type ParamValue = string | number | boolean | null;
export type Params = Record<string, ParamValue>;

export type ParamType = 'enum' | 'text' | 'bool' | 'int' | 'float' | 'cmap' | 'color';

export interface ParamField {
  id: string;
  label: string;
  type: ParamType;
  default?: ParamValue;
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  note?: string;
  pattern?: string;
  options?: string[];
}

export interface GeneratorSchema {
  properties: ParamField[];
}

export interface Preset {
  name: string;
  description: string;
  params: Params;
}

export interface Generator {
  name: string;
  display_name: string;
  description: string;
  unimplemented: boolean;
  next_release?: boolean;
  glyph: string;
  param_schema: GeneratorSchema;
  presets: Preset[];
}

export interface IphoneModel {
  id: string;
  name: string;
  w: number;
  h: number;
}

export interface ExportFormat {
  id: string;
  name: string;
  desc: string;
  ext: string;
}

export type JobStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface ExportJob {
  id: string;
  gen: string;
  genLabel: string;
  preset: string;
  params: Params;
  device: string;
  resW: number;
  resH: number;
  fps: number;
  duration: number;
  format: string;
  created: number;
  finishAt: number;
  status: JobStatus;
  progress: number;
  poster: string | null;
}

export interface OutputOptions {
  device: string;
  fps: number;
  duration: number;
  colormap: string;
  seed: number | null;
  format: string;
}
