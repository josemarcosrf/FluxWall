import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { ExportJob, Generator, OutputOptions, Params } from '../lib/types';
import { FORMATS, resolutionFor } from '../lib/data';
import { estimateSize, exportStore } from '../lib/exports';
import { Notice } from './ui';

interface ExportPanelProps {
  gen: Generator;
  preset: string;
  params: Params;
  output: OutputOptions;
  onFormatChange: (format: string) => void;
}

/** Export group: format, estimate, Generate & Export, inline progress, download. */
export function ExportPanel({ gen, preset, params, output, onFormatChange }: ExportPanelProps): React.JSX.Element {
  const [running, setRunning] = useState<ExportJob | null>(null);
  const [pct, setPct] = useState(0);
  const [eta, setEta] = useState(0);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!running) return;
    const iv = window.setInterval(() => {
      const s = exportStore.status(running);
      setPct(Math.round(s.progress * 100));
      setEta(Math.max(0, Math.round((running.finishAt - Date.now()) / 1000)));
      if (s.status === 'completed' || s.status === 'failed') {
        setDone(true);
        window.clearInterval(iv);
      }
    }, 300);
    return () => window.clearInterval(iv);
  }, [running]);

  const res = resolutionFor(output.device);
  const fmt = FORMATS.find((f) => f.id === output.format) || FORMATS[0];
  const est = estimateSize(res.w, res.h, output.fps, output.duration);

  const startExport = () => {
    if (gen.unimplemented) return;
    const job = exportStore.start({
      gen: gen.name,
      genLabel: gen.display_name,
      preset,
      params: { ...params, colormap: output.colormap },
      device: output.device,
      resW: res.w,
      resH: res.h,
      fps: output.fps,
      duration: output.duration,
      format: output.format,
    });
    setRunning(job);
    setPct(0);
    setDone(false);
    setEta(0);
  };

  return (
    <>
      <div className="field">
        <label>Format</label>
        <div className="segmented" data-od-id="export-format">
          {FORMATS.map((f) => (
            <button
              key={f.id}
              type="button"
              className={f.id === output.format ? 'active' : ''}
              onClick={() => onFormatChange(f.id)}
            >
              {f.name}
            </button>
          ))}
        </div>
      </div>

      <div className="export-status" data-od-id="export-estimate">
        <span>
          {fmt.name} · {res.name.replace(/^iPhone /, '')}
        </span>
        <span className="num">&nbsp;{est.toFixed(1)} MB raw</span>
      </div>

      {gen.unimplemented && (
        <Notice glyphName={gen.glyph}>
          Scaffolded generator &mdash; preview and export are disabled until this generator actually renders.
        </Notice>
      )}

      <button
        className="btn btn-primary btn-block"
        data-od-id="btn-export"
        disabled={gen.unimplemented || !!running}
        onClick={startExport}
        style={{ marginTop: '14px' }}
      >
        Generate &amp; Export
      </button>

      {running && (
        <div id="export-progress" data-od-id="export-progress" style={{ marginTop: '12px' }}>
          <div className={'progress' + (done ? ' ok' : '')}>
            <i style={{ width: pct + '%' }} />
          </div>
          <div className="export-status">
            <span id="ep-status">{done ? 'Completed' : 'Rendering&hellip;'}</span>
            <span className="num" id="ep-pct">
              {pct}%
            </span>
          </div>
          <div className="export-status">
            <span className="num" id="ep-eta">
              {done ? '' : '~' + eta + 's remaining'}
            </span>
            <Link to="/library" data-od-id="link-my-exports">
              My Exports
            </Link>
          </div>
          {done && running && (
            <>
              <button
                className="btn btn-primary btn-block"
                id="btn-download"
                data-od-id="btn-download"
                onClick={() => exportStore.download(running)}
                style={{ marginTop: '10px' }}
              >
                Download
              </button>
              <div className="field-note" id="ep-note">
                Static build &mdash; the download is a preview still (PNG) until the local API is wired for real encoding.
              </div>
            </>
          )}
        </div>
      )}
    </>
  );
}
