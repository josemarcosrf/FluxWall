import type { Generator } from '../lib/types';
import { defaultsFor } from '../lib/data';
import { Glyph, friendlyName } from './ui';
import { StillThumb } from './StillThumb';

interface RailProps {
  generators: Generator[];
  gen: Generator;
  presetName: string;
  onSelectGen: (name: string) => void;
  onSelectPreset: (name: string) => void;
}

/** Left rail: generator list + preset list for the current generator. */
export function Rail({ generators, gen, presetName, onSelectGen, onSelectPreset }: RailProps): React.JSX.Element {
  return (
    <aside className="rail" data-od-id="studio-rail">
      <div className="rail-group" data-od-id="rail-generators">
        <h2>Generators</h2>
        <div className="rail-list">
          {generators.map((g) => (
            <button
              key={g.name}
              className={'rail-item' + (g.name === gen.name ? ' active' : '')}
              data-od-id={'rail-generator-' + g.name}
              onClick={() => onSelectGen(g.name)}
            >
              <Glyph name={g.glyph} className="glyph" />
              <span className="t">
                <b>{g.display_name}</b>
                <span>{g.unimplemented ? 'Coming soon' : g.presets.length + ' presets'}</span>
              </span>
              <span className="count">{g.unimplemented ? '—' : g.presets.length}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="rail-group" data-od-id="rail-presets">
        <h2>Presets</h2>
        <div className="preset-list">
          <button
            className={'preset-item' + (presetName === 'custom' ? ' active' : '')}
            data-od-id="preset-item-custom"
            onClick={() => onSelectPreset('custom')}
          >
            <span className="thumb add">+</span>
            <span className="pinfo">
              <b>Custom</b>
              <span>Manual params</span>
            </span>
          </button>
          {gen.presets.map((p) => (
            <button
              key={p.name}
              className={'preset-item' + (presetName === p.name ? ' active' : '')}
              data-od-id={'preset-item-' + gen.name + '-' + p.name}
              onClick={() => onSelectPreset(p.name)}
            >
              {gen.unimplemented ? (
                <span className="thumb ph">
                  <Glyph name={gen.glyph} />
                </span>
              ) : (
                <span className="thumb">
                  <StillThumb generator={gen.name} params={{ ...defaultsFor(gen), ...p.params }} width={34} height={56} phase={0.62} />
                </span>
              )}
              <span className="pinfo">
                <b>{friendlyName(p.name)}</b>
                <span>{p.description}</span>
              </span>
            </button>
          ))}
        </div>
      </div>
    </aside>
  );
}
