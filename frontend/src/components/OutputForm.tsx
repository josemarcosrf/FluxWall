import { useState } from 'react';
import type { OutputOptions } from '../lib/types';
import { IPHONE_MODELS } from '../lib/data';
import { CmapField } from './ParamField';

interface OutputFormProps {
  state: OutputOptions;
  onOutput: (chg: Partial<OutputOptions>) => void;
}

/** Output group: device, frame rate, duration, colormap, seed. */
export function OutputForm({ state, onOutput }: OutputFormProps): React.JSX.Element {
  const [manualSeed, setManualSeed] = useState<number>(() => state.seed ?? 1337);
  const range = (
    id: keyof OutputOptions,
    label: string,
    min: number,
    max: number,
    step: number,
    value: number,
    unit: string,
  ) => (
    <div className="range-row">
      <div className="rv">
        <label>{label}</label>
        <output className="num">
          {value}
          {unit ? ' ' + unit : ''}
        </output>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onOutput({ [id]: step === 1 ? Math.round(parseFloat(e.target.value)) : parseFloat(e.target.value) })}
      />
      <div className="rminmax">
        <span>{min}</span>
        <span>
          {max}
          {unit ? ' ' + unit : ''}
        </span>
      </div>
    </div>
  );

  return (
    <>
      <div className="field">
        <label>Device</label>
        <select value={state.device} onChange={(e) => onOutput({ device: e.target.value })}>
          {IPHONE_MODELS.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name} · {m.w}×{m.h}
            </option>
          ))}
        </select>
      </div>

      {range('fps', 'Frame rate', 1, 60, 1, state.fps, 'fps')}
      {range('duration', 'Duration', 0.5, 30, 0.5, state.duration, 's')}

      <CmapField id="colormap" label="Colormap" value={state.colormap} onChange={(v) => onOutput({ colormap: v })} />

      <div className="field">
        <label>Seed</label>
        <div style={{ display: 'flex', gap: '8px' }}>
          <span className="switch">
            <input
              type="checkbox"
              checked={state.seed == null}
              onChange={(e) => onOutput({ seed: e.target.checked ? null : (manualSeed || null) })}
            />
            <i />
          </span>
          <input
            type="number"
            min={1}
            max={2147483647}
            style={{ flex: '1' }}
            disabled={state.seed == null}
            value={manualSeed}
            onChange={(e) => {
              const v = parseInt(e.target.value, 10);
              setManualSeed(v || 0);
              if (state.seed != null) onOutput({ seed: v || null });
            }}
          />
        </div>
        <div className="field-note">Auto seeds a reproducible pattern per export</div>
      </div>
    </>
  );
}
