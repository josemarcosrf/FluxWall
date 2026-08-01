import { useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { Generator, OutputOptions, Params, ParamValue } from '../lib/types';
import { GENERATORS, defaultsFor, generatorByName, resolutionFor } from '../lib/data';
import { storeGet, storeSet, outputStore } from '../lib/store';
import { TopBar } from '../components/TopBar';
import { PhoneFrame, PhonePlaceholder } from '../components/PhoneFrame';
import { PreviewCanvas } from '../components/PreviewCanvas';
import type { PreviewHandle } from '../components/PreviewCanvas';
import { Rail } from '../components/Rail';
import { OutputForm } from '../components/OutputForm';
import { GenForm } from '../components/ParamField';
import { ExportPanel } from '../components/ExportPanel';

function PlayIcon(): React.JSX.Element {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M8 5v14l11-7z" />
    </svg>
  );
}
function PauseIcon(): React.JSX.Element {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M6 5h4v14H6zM14 5h4v14h-4z" />
    </svg>
  );
}
function ResetIcon(): React.JSX.Element {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
      <path d="M3 3v5h5" />
    </svg>
  );
}

export function Studio(): React.JSX.Element {
  const [searchParams] = useSearchParams();
  const urlGen = searchParams.get('gen') ? decodeURIComponent(searchParams.get('gen') as string) : null;
  const urlPreset = searchParams.get('preset') ? decodeURIComponent(searchParams.get('preset') as string) : null;

  const startGen = useMemo<string>(() => {
    if (urlGen && generatorByName(urlGen)) return urlGen;
    const saved = storeGet<string | null>('lastGen', null);
    if (saved && generatorByName(saved)) return saved;
    return 'game_of_life';
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const [genName, setGenName] = useState<string>(startGen);
  const gen = generatorByName(genName) as Generator;

  const [presetName, setPresetName] = useState<string>(() => {
    if (urlPreset && gen.presets.some((p) => p.name === urlPreset)) return urlPreset;
    return 'custom';
  });

  const [params, setParams] = useState<Params>(() => {
    const d = defaultsFor(gen);
    if (urlPreset) {
      const p = gen.presets.find((x) => x.name === urlPreset);
      if (p) return { ...d, ...p.params };
    }
    return { ...d, ...storeGet<Params>('params.' + genName, {}) };
  });

  const [output, setOutput] = useState<OutputOptions>(() => ({
    device: storeGet('device', '15_pro'),
    fps: storeGet('fps', 30),
    duration: storeGet('duration', 3),
    colormap: storeGet('colormap', 'magma'),
    seed: storeGet('seed', null),
    format: storeGet('format', 'live_photo'),
  }));

  // ── Preview params: debounced stream restart (300ms) ──────────────
  const paramsRef = useRef(params);
  useEffect(() => {
    paramsRef.current = params;
  }, [params]);

  const [previewParams, setPreviewParams] = useState<Params>(() => ({ ...params, colormap: output.colormap, seed: output.seed }));
  const debounceTimer = useRef<number>(0);
  const pendingPreview = useRef<Params | null>(null);
  useEffect(() => () => window.clearTimeout(debounceTimer.current), []);

  const schedulePreview = (p: Params) => {
    pendingPreview.current = p;
    window.clearTimeout(debounceTimer.current);
    debounceTimer.current = window.setTimeout(() => {
      const pp = pendingPreview.current;
      if (pp) setPreviewParams({ ...pp });
    }, 300);
  };
  const restartPreview = (p: Params) => {
    pendingPreview.current = null;
    window.clearTimeout(debounceTimer.current);
    setPreviewParams({ ...p });
  };

  const [playing, setPlaying] = useState(true);
  const previewRef = useRef<PreviewHandle>(null);

  const saveGen = (name: string, p: Params) => {
    storeSet('lastGen', name);
    storeSet('params.' + name, p);
  };

  const selectGen = (name: string) => {
    if (name === genName) return;
    const g = generatorByName(name) as Generator;
    setGenName(name);
    setPresetName('custom');
    const p = { ...defaultsFor(g), ...storeGet<Params>('params.' + name, {}) };
    setParams(p);
    saveGen(name, p);
    restartPreview({ ...p, colormap: output.colormap, seed: output.seed });
  };

  const selectPreset = (name: string) => {
    setPresetName(name);
    const p = name === 'custom' ? defaultsFor(gen) : { ...defaultsFor(gen), ...gen.presets.find((x) => x.name === name)?.params };
    setParams(p);
    saveGen(genName, p);
    restartPreview({ ...p, colormap: output.colormap, seed: output.seed });
  };

  const onChangeParam = (id: string, v: ParamValue) => {
    const next = { ...paramsRef.current, [id]: v };
    paramsRef.current = next;
    setParams(next);
    saveGen(genName, next);
    schedulePreview({ ...next, colormap: output.colormap, seed: output.seed });
  };

  const resetParams = () => {
    const d = defaultsFor(gen);
    paramsRef.current = d;
    setParams(d);
    saveGen(genName, d);
    restartPreview({ ...d, colormap: output.colormap, seed: output.seed });
  };

  const onOutput = (chg: Partial<OutputOptions>) => {
    const next = { ...output, ...chg };
    setOutput(next);
    (Object.entries(chg) as [string, ParamValue][]).forEach(([k, v]) => storeSet(k, v));
    if (chg.device) outputStore.setDevice(chg.device);
    if (chg.format) outputStore.setFormat(chg.format);
    if ('colormap' in chg || 'seed' in chg) {
      schedulePreview({ ...paramsRef.current, colormap: next.colormap, seed: next.seed });
    }
  };

  const togglePlay = () => {
    if (gen.unimplemented) return;
    setPlaying((p) => !p);
  };
  const onReset = () => {
    if (gen.unimplemented) return;
    previewRef.current?.reset();
    setPlaying(true);
  };

  const res = resolutionFor(output.device);

  return (
    <>
      <TopBar />
      <main className="studio">
        <Rail generators={GENERATORS} gen={gen} presetName={presetName} onSelectGen={selectGen} onSelectPreset={selectPreset} />

        <section className="canvas-col" data-od-id="preview">
          <PhoneFrame>
            {gen.unimplemented ? (
              <PhonePlaceholder glyphName={gen.glyph} />
            ) : (
              <PreviewCanvas
                ref={previewRef}
                generator={genName}
                params={previewParams}
                playing={playing}
                onPlayingChange={setPlaying}
              />
            )}
          </PhoneFrame>

          <div className="preview-controls">
            <button className="icon-btn" data-od-id="btn-play" disabled={gen.unimplemented} onClick={togglePlay}>
              {playing ? <PauseIcon /> : <PlayIcon />}
              {playing ? ' Pause' : ' Play'}
            </button>
            <button className="icon-btn" data-od-id="btn-reset" disabled={gen.unimplemented} onClick={onReset}>
              <ResetIcon />
              Reset
            </button>
          </div>

          <div className="preview-meta">
            <span className="chip">
              <b>Device</b>
              <span className="num" data-od-id="chip-res">
                {res.w}×{res.h}
              </span>
            </span>
            <span className="chip">
              <b>Cmap</b>
              <span className="num" data-od-id="chip-cmap">
                {output.colormap}
              </span>
            </span>
            <span className="chip">
              <b>FPS</b>
              <span className="num" data-od-id="chip-fps">
                {output.fps} fps
              </span>
            </span>
          </div>
        </section>

        <aside className="panel" data-od-id="studio-panel">
          <div className="panel-group" data-od-id="panel-output">
            <h2>Output</h2>
            <OutputForm state={output} onOutput={onOutput} />
          </div>

          <div className="panel-group" data-od-id="panel-params">
            <div className="pg-head">
              <h2>Parameters</h2>
              <button className="btn btn-sm" data-od-id="btn-reset-params" onClick={resetParams}>
                Reset to defaults
              </button>
            </div>
            <GenForm schema={gen.param_schema} values={params} onChange={onChangeParam} />
          </div>

          <div className="panel-group" data-od-id="panel-export">
            <h2>Export</h2>
            <ExportPanel gen={gen} preset={presetName} params={params} output={output} onFormatChange={(f) => onOutput({ format: f })} />
          </div>
        </aside>
      </main>
    </>
  );
}
