import { useEffect, useReducer, useSyncExternalStore } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import type { ExportJob } from '../lib/types';
import { FORMATS, generatorByName } from '../lib/data';
import { exportStore } from '../lib/exports';
import { TopBar } from '../components/TopBar';
import { StillThumb } from '../components/StillThumb';
import { Glyph, friendlyName } from '../components/ui';

function fmtName(id: string): string {
  const f = FORMATS.find((x) => x.id === id);
  return f ? f.name : id;
}

export function Library(): React.JSX.Element {
  const jobs = useSyncExternalStore(exportStore.subscribe, exportStore.all);
  const [, force] = useReducer((x: number) => x + 1, 0);
  const navigate = useNavigate();

  useEffect(() => {
    const iv = window.setInterval(async () => {
      const jobs = exportStore.all();
      for (const job of jobs) {
        if (job.status !== 'running' && job.status !== 'pending') continue;
        if (job.serverId) {
          try {
            await exportStore.refreshServer(job);
          } catch {
            /* transient polling failure: try again next tick */
          }
        } else {
          exportStore.status(job);
        }
      }
      const stillRunning = exportStore.all().some((j) => j.status === 'running' || j.status === 'pending');
      force();
      if (!stillRunning) window.clearInterval(iv);
    }, 800);
    return () => window.clearInterval(iv);
  }, []);

  const remove = (id: string) => {
    exportStore.remove(id);
    force();
  };

  return (
    <>
      <TopBar />
      <main className="layout">
        <div className="page-head" data-od-id="library-heading">
          <h1>My Exports</h1>
          <p>Jobs you generate from the studio land here — status and downloads are pulled from the FluxWall API.</p>
        </div>

        {jobs.length === 0 && (
          <div className="empty" data-od-id="empty-state">
            <h3>No exports yet</h3>
            <p>
              Generate your first wallpaper in the studio: pick a generator, tune it, and hit Generate &amp; Export.
            </p>
            <Link className="btn btn-primary" to="/studio" data-od-id="cta-empty-to-studio">
              Open the studio
            </Link>
          </div>
        )}

        {jobs.length > 0 && (
          <div className="job-list" data-od-id="job-list">
            {jobs.map((job, i) => (
              <JobCard
                key={job.id}
                job={job}
                index={i + 1}
                onRemove={remove}
                onAgain={() => {
                  let href = '/studio?gen=' + encodeURIComponent(job.gen);
                  if (job.preset && job.preset !== 'custom') href += '&preset=' + encodeURIComponent(job.preset);
                  navigate(href);
                }}
              />
            ))}
          </div>
        )}

        <section className="guide" data-od-id="install-guide">
          <h2>Install on your iPhone</h2>
          <p>How a Live Photo export reaches your lock screen.</p>

          <GuideStep n="1" title="Export a Live Photo">
            Use the Live Photo format in the studio. The export bundles a <code>HEIC</code> still + <code>MOV</code>{' '}
            motion pair with a shared ContentIdentifier, wrapped in a <code>.pvt</code> bundle.
          </GuideStep>
          <GuideStep n="2" title="Open the .pvt on macOS">
            Double-click the <code>.pvt</code> file — macOS Photos imports it as a Live Photo. Authoring is{' '}
            <strong>macOS-only</strong>: stamping the ContentIdentifier needs <code>makelive</code> (
            <code>uv sync --extra livephoto</code>). Without it the pair shows in Photos but the lock screen reports
            &ldquo;Motion Not Available&rdquo;.
          </GuideStep>
          <GuideStep n="3" title="Sync to your iPhone">
            Let iCloud Photos sync the imported Live Photo to your phone (iCloud Photos enabled on both devices).
          </GuideStep>
          <GuideStep n="4" title="Set it as your Lock Screen">
            On the iPhone: <code>Settings &rarr; Wallpaper &rarr; Add New Wallpaper &rarr; Photos</code>, pick the Live
            Photo, and set it.
          </GuideStep>
          <GuideStep n="5" title="Play it">
            Press and hold the lock screen to animate the wallpaper.
          </GuideStep>
          <GuideStep n="&rarr;" title="MP4 / MOV instead">
            Plain video exports work cross-platform — share them over AirDrop or any transfer method; Live Photo
            lock-screen pairing is the macOS-only part.
          </GuideStep>
        </section>
      </main>
    </>
  );
}

function JobCard({
  job,
  index,
  onRemove,
  onAgain,
}: {
  job: ExportJob;
  index: number;
  onRemove: (id: string) => void;
  onAgain: () => void;
}): React.JSX.Element {
  const pill = job.status === 'completed' ? 'ok' : job.status === 'failed' ? 'err' : 'accent';
  const title = job.genLabel + ' · ' + (job.preset === 'custom' ? 'custom' : friendlyName(job.preset));
  const meta = `${job.resW}×${job.resH} · ${job.fps} fps · ${job.duration}s · ${fmtName(job.format)}`;
  const running = job.status === 'running' || job.status === 'pending';

  return (
    <div className="job-card card" data-od-id={'job-card-' + index}>
      <div className="poster">
        <JobPoster job={job} />
      </div>
      <div className="jinfo">
        <div className="jtop">
          <h3>{title}</h3>
          <span className={'badge ' + pill}>{job.status}</span>
        </div>
        <div className="jmeta">
          <span className="num">{meta}</span>
        </div>
        {running && (
          <div className="progress" style={{ marginTop: 8 }}>
            <i style={{ width: Math.round(job.progress * 100) + '%' }} />
          </div>
        )}
        {job.status === 'failed' && job.error && (
          <p className="field-note" style={{ marginTop: 6, color: 'var(--err)' }}>
            {job.error}
          </p>
        )}
      </div>
      <div className="jactions">
        <button
          className="btn btn-sm btn-primary"
          data-od-id={'job-download-' + index}
          disabled={!(job.poster && job.status === 'completed')}
          onClick={() => exportStore.download(job)}
        >
          Download
        </button>
        <button className="btn btn-sm" data-od-id={'job-again-' + index} onClick={onAgain}>
          Export again
        </button>
        <button className="btn btn-sm" data-od-id={'job-remove-' + index} onClick={() => onRemove(job.id)}>
          Remove
        </button>
      </div>
    </div>
  );
}

function JobPoster({ job }: { job: ExportJob }): React.JSX.Element {
  if (job.poster) return <img src={job.poster} alt="" />;
  const gen = generatorByName(job.gen);
  if (gen && !gen.unimplemented) {
    return <StillThumb generator={job.gen} params={job.params} width={54} height={96} phase={0.62} />;
  }
  return (
    <span style={{ display: 'grid', placeItems: 'center', width: '100%', height: '100%' }}>
      <Glyph name={gen ? gen.glyph : 'fractal'} />
    </span>
  );
}

function GuideStep({ n, title, children }: { n: string; title: string; children: React.ReactNode }): React.JSX.Element {
  return (
    <div className="guide-step">
      <span className="n">{n}</span>
      <div>
        <h3>{title}</h3>
        <p>{children}</p>
      </div>
    </div>
  );
}
