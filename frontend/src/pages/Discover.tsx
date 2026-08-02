import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import type { Generator, Preset } from '../lib/types';
import { GENERATORS, defaultsFor, generatorByName } from '../lib/data';
import { TopBar } from '../components/TopBar';
import { PhoneFrame } from '../components/PhoneFrame';
import { PreviewCanvas } from '../components/PreviewCanvas';
import { StillThumb } from '../components/StillThumb';
import { Glyph, friendlyName } from '../components/ui';

const HERO_CYCLE = [
  { g: 'game_of_life', p: 'gosper_gun' },
  { g: 'flowing_curve', p: 'tendrils' },
  { g: 'mandelbrot', p: 'seahorse_valley' },
  { g: 'julia', p: 'spiral' },
];

export function Discover(): React.JSX.Element {
  const [ci, setCi] = useState(0);
  const [playing, setPlaying] = useState(true);

  useEffect(() => {
    const iv = window.setInterval(() => setCi((i) => (i + 1) % HERO_CYCLE.length), 4200);
    return () => window.clearInterval(iv);
  }, []);

  const cur = HERO_CYCLE[ci];
  const heroGen = generatorByName(cur.g) as Generator;
  const heroPreset = heroGen.presets.find((x) => x.name === cur.p) as Preset;
  const heroParams = useMemo(
    () => ({ ...defaultsFor(heroGen), ...heroPreset.params }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [cur.g, cur.p],
  );

  return (
    <>
      <TopBar />

      <section className="hero" data-od-id="hero">
        <div>
          <h1 data-od-id="hero-heading">
            Generative <span className="hl">live wallpapers</span> for iPhone
          </h1>
          <p className="lede">
            Pick a generator, load a preset or go fully custom, watch it play on a phone frame — then export MP4,
            MOV, or a Live Photo and install it on your lock screen.
          </p>
          <div className="cta-row">
            <Link className="btn btn-primary" to="/studio" data-od-id="cta-open-studio">
              Open the studio
            </Link>
            <a className="btn" href="#generators" data-od-id="cta-browse-generators">
              Browse generators
            </a>
          </div>
        </div>
        <div>
          <PhoneFrame className="hero-phone">
            <PreviewCanvas generator={cur.g} params={heroParams} playing={playing} onPlayingChange={setPlaying} />
          </PhoneFrame>
          <div className="hero-note" id="hero-note">
            <b>{heroGen.display_name}</b> &middot; {friendlyName(cur.p)}
          </div>
        </div>
      </section>

      <section className="section" id="generators" data-od-id="generators">
        <div className="section-head">
          <h2 data-od-id="generators-heading">Generators</h2>
          <span className="count" id="generator-count">
            {GENERATORS.length} generators
          </span>
        </div>
        <div className="gen-grid" id="generator-grid">
          {GENERATORS.map((g) => (
            <GeneratorCard key={g.name} g={g} />
          ))}
        </div>
      </section>

      <section className="section" data-od-id="presets">
        <div className="section-head">
          <h2 data-od-id="presets-heading">Featured presets</h2>
          <span className="count">Stills rendered live from the same math the studio uses</span>
        </div>
        <div className="preset-grid" id="preset-grid">
          {GENERATORS.flatMap((g) => g.presets.slice(0, 2).map((p) => ({ g, p }))).map(({ g, p }) => (
            <PresetCard key={g.name + '-' + p.name} g={g} p={p} />
          ))}
        </div>
      </section>

      <footer className="muted" style={{ textAlign: 'center', padding: '0 24px 48px', fontSize: 12 }}>
        FluxWall — parametric iOS live wallpaper studio. Size estimates are raw-video estimates; the mock data layer
        mirrors the FastAPI contract so wiring the local API later is a config change, not a rewrite.
      </footer>
    </>
  );
}

function GeneratorCard({ g }: { g: Generator }): React.JSX.Element {
  const badges = g.unimplemented ? (
    <span className="badge">Coming soon</span>
  ) : g.next_release ? (
    <span className="badge accent">New</span>
  ) : null;

  return (
    <Link className="card card-hover gen-card" to={'/studio?gen=' + encodeURIComponent(g.name)} data-od-id={'generator-card-' + g.name}>
      <div className="ghead">
        <Glyph name={g.glyph} className="glyph" />
        <span className="gbadges">{badges}</span>
      </div>
      <h3>{g.display_name}</h3>
      <p>{g.description}</p>
      <div className="gfoot">
        <span className="count">
          {g.presets.length} preset{g.presets.length === 1 ? '' : 's'}
        </span>
        <span className="count accent">Open studio &#8594;</span>
      </div>
    </Link>
  );
}

function PresetCard({ g, p }: { g: Generator; p: Preset }): React.JSX.Element {
  const ph = g.unimplemented;
  return (
    <Link
      className="card card-hover preset-card"
      to={'/studio?gen=' + encodeURIComponent(g.name) + '&preset=' + encodeURIComponent(p.name)}
      data-od-id={'preset-card-' + g.name + '-' + p.name}
    >
      <div className={'shot' + (ph ? ' ph' : '')}>
        {ph ? (
          <>
            <Glyph name={g.glyph} />
            <span>Scaffolded</span>
          </>
        ) : (
          <StillThumb generator={g.name} params={{ ...defaultsFor(g), ...p.params }} width={60} height={130} phase={0.62} />
        )}
      </div>
      <b>{friendlyName(p.name)}</b>
      <div className="tags">
        <span className="tag">{g.display_name}</span>
        {ph && <span className="tag">Not rendering yet</span>}
      </div>
    </Link>
  );
}
