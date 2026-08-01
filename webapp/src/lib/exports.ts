// Export job store (localStorage-persisted history) + honest size estimate.
// Ported from the prototype's app layer.

import type { ExportJob, JobStatus, Params } from './types';
import { generatorByName } from './data';
import { renderStill } from './render';
import { storeGet, storeSet } from './store';

export function estimateSize(w: number, h: number, fps: number, duration: number): number {
  return (w * h * 3 * fps * duration) / (1024 * 1024);
}

const KEY = 'exports';
let cache: ExportJob[] | null = null;

function load(): ExportJob[] {
  if (!cache) cache = storeGet<ExportJob[]>(KEY, []);
  return cache;
}

const listeners = new Set<() => void>();
function emit(): void {
  listeners.forEach((l) => l());
}
function save(list: ExportJob[]): void {
  cache = list;
  storeSet(KEY, list);
  emit();
}

export interface NewJobData {
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
}

export const exportStore = {
  subscribe(listener: () => void): () => void {
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  },

  all(): ExportJob[] {
    return load();
  },

  start(jobData: NewJobData): ExportJob {
    const job: ExportJob = {
      id: 'job-' + Math.random().toString(36).slice(2, 10),
      created: Date.now(),
      finishAt: Date.now() + 4200 + (jobData.duration || 3) * 900,
      status: 'running',
      progress: 0,
      poster: null,
      ...jobData,
    };
    const list = this.all();
    list.unshift(job);
    save(list);
    return job;
  },

  status(job: ExportJob): { status: JobStatus; progress: number } {
    const now = Date.now();
    if (job.status === 'failed') return { status: 'failed', progress: 1 };
    if (now >= job.finishAt) {
      if (job.status !== 'completed') {
        job.status = 'completed';
        job.progress = 1;
        job.poster = this.renderPoster(job);
        save(this.all());
      }
      return { status: 'completed', progress: 1 };
    }
    return { status: 'running', progress: Math.min(0.99, (now - job.created) / (job.finishAt - job.created)) };
  },

  renderPoster(job: ExportJob): string | null {
    try {
      const cv = document.createElement('canvas');
      cv.width = 96;
      cv.height = 208;
      const gen = generatorByName(job.gen);
      if (!gen || gen.unimplemented) return null;
      renderStill(cv, job.gen, job.params, 0.55);
      return cv.toDataURL('image/jpeg', 0.72);
    } catch {
      return null;
    }
  },

  download(job: ExportJob): void {
    const data = job.poster;
    if (!data) return;
    const a = document.createElement('a');
    a.href = data;
    a.download =
      'fluxwall_' + job.gen + '_' + (job.preset || 'custom') + '_' + job.resW + 'x' + job.resH + '_' + job.fps + 'fps_' + job.duration + 's.png';
    document.body.appendChild(a);
    a.click();
    a.remove();
  },

  remove(id: string): void {
    cache = this.all().filter((j) => j.id !== id);
    storeSet(KEY, cache);
    emit();
  },
};
