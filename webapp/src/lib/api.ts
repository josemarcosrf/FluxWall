// Typed client for the FluxWall FastAPI backend.
//
// BASE defaults to '' (same-origin: the FastAPI app also serves the built SPA).
// In dev, point VITE_API_BASE at the API, e.g. http://localhost:8000, and set
// VITE_USE_API=1 to switch the export flow from the local mock to the server.
import type { Params } from './types';

export const API_BASE: string = (import.meta.env.VITE_API_BASE as string | undefined) ?? '';
export const USE_API: boolean = (import.meta.env.VITE_USE_API as string | undefined) === '1';

export interface ApiGeneratorInfo {
  name: string;
  display_name: string;
  description: string;
  param_schema: Record<string, unknown>;
  presets: Record<string, unknown>;
}

export interface ApiPreset {
  id: string;
  generator: string;
  name: string;
  description: string;
  params: Params;
  export: Record<string, unknown>;
  tags: string[];
  version: number;
}

export interface ApiExportOptions {
  format: string;
  iphone_model: string;
  fps: number;
  duration_sec: number;
  quality: number;
}

export interface ApiExportStart {
  generator: string;
  params: Params;
  options: ApiExportOptions;
}

export interface ApiExportResponse {
  job_id: string;
  status_url: string;
  download_url: string | null;
}

export interface ApiJobStatus {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  current_frame: number;
  total_frames: number;
  output_path: string | null;
  error: string | null;
  download_url: string | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(API_BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: string };
      detail = body.detail ?? detail;
    } catch {
      /* non-JSON error body: fall back to statusText */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export const api = {
  listGenerators: () => request<ApiGeneratorInfo[]>('/api/generators'),
  listPresets: (generator?: string) =>
    request<ApiPreset[]>('/api/presets' + (generator ? `?generator=${generator}` : '')),
  startExport: (body: ApiExportStart) =>
    request<ApiExportResponse>('/api/export', { method: 'POST', body: JSON.stringify(body) }),
  jobStatus: (jobId: string) => request<ApiJobStatus>(`/api/export/status/${jobId}`),
};

/** Make a possibly-relative API URL absolute (prefixes API_BASE when needed). */
export function absUrl(url: string): string {
  return /^https?:\/\//i.test(url) ? url : API_BASE + url;
}
