import { useEffect, useState } from 'react';
import type { GeneratorSchema, ParamField as ParamFieldSchema, ParamValue } from '../lib/types';
import { COLORMAPS } from '../lib/data';
import { cmapSwatch } from '../lib/render';

interface ParamFieldProps {
  field: ParamFieldSchema;
  value: ParamValue;
  onChange: (id: string, v: ParamValue) => void;
}

/** Pure JSON-Schema field renderer — any generator works with zero UI code. */
export function ParamField({ field, value, onChange }: ParamFieldProps): React.JSX.Element {
  const id = field.id;
  const setVal = (v: ParamValue) => onChange(id, v);
  const note = field.note ? <div className="field-note">{field.note}</div> : null;
  const label = <label>{field.label}</label>;

  if (field.type === 'bool') {
    return (
      <div className="field" data-od-id={'param-' + id}>
        {label}
        <div className="switch-row">
          <span className="switch">
            <input type="checkbox" checked={!!value} onChange={(e) => setVal(e.target.checked)} />
            <i />
          </span>
        </div>
      </div>
    );
  }

  if (field.type === 'int' || field.type === 'float') {
    const step = field.step != null ? field.step : field.type === 'int' ? 1 : 0.001;
    const isInt = field.type === 'int';
    const fmt = (v: number) => String(v) + (field.unit ? ' ' + field.unit : '');
    return (
      <div className="field" data-od-id={'param-' + id}>
        <div className="range-row">
          <div className="rv">
            <label>{field.label}</label>
            <output className="num">{fmt(Number(value ?? field.default ?? 0))}</output>
          </div>
          <input
            type="range"
            min={field.min}
            max={field.max}
            step={step}
            value={Number(value ?? field.default ?? 0)}
            onChange={(e) => {
              const v = isInt ? Math.round(parseFloat(e.target.value)) : parseFloat(e.target.value);
              setVal(v);
            }}
          />
          <div className="rminmax">
            <span>{field.min}</span>
            <span>
              {field.max}
              {field.unit ? ' ' + field.unit : ''}
            </span>
          </div>
        </div>
        {note}
      </div>
    );
  }

  if (field.type === 'enum') {
    const options = field.options || [];
    if (options.length <= 5) {
      return (
        <div className="field" data-od-id={'param-' + id}>
          {label}
          <div className="segmented">
            {options.map((o) => (
              <button
                key={o}
                type="button"
                className={o === value ? 'active' : ''}
                onClick={() => setVal(o)}
              >
                {o.replace(/_/g, ' ')}
              </button>
            ))}
          </div>
          {note}
        </div>
      );
    }
    return (
      <div className="field" data-od-id={'param-' + id}>
        {label}
        <select value={String(value ?? '')} onChange={(e) => setVal(e.target.value)}>
          {options.map((o) => (
            <option key={o} value={o}>
              {o.replace(/_/g, ' ')}
            </option>
          ))}
        </select>
        {note}
      </div>
    );
  }

  if (field.type === 'cmap') {
    return (
      <CmapField id={id} label={field.label} value={String(value ?? 'magma')} onChange={setVal} />
    );
  }

  if (field.type === 'color') {
    return (
      <div className="field" data-od-id={'param-' + id}>
        {label}
        <input type="color" value={String(value ?? '#000000')} onChange={(e) => setVal(e.target.value)} />
      </div>
    );
  }

  // text
  return (
    <div className="field" data-od-id={'param-' + id}>
      {label}
      <input
        type="text"
        value={String(value ?? '')}
        pattern={field.pattern || ''}
        onChange={(e) => setVal(e.target.value.trim())}
      />
      {note}
    </div>
  );
}

/** Colormap picker: gradient swatch + select. */
export function CmapField({  id,
  label,
  value,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
}): React.JSX.Element {
  const [swatch, setSwatch] = useState(() => cmapSwatch(value));

  useEffect(() => {
    setSwatch(cmapSwatch(value));
  }, [value]);

  return (
    <div className="field" data-od-id={'param-' + id}>
      <label>{label}</label>
      <div className="cmap-row">
        <span className="cmap-swatch" style={{ backgroundImage: 'url(' + swatch + ')' }} />
        <select
          value={value}
          onChange={(e) => {
            setSwatch(cmapSwatch(e.target.value));
            onChange(e.target.value);
          }}
        >
          {COLORMAPS.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

/** Render a full generator-params group from a JSON Schema. */
export function GenForm({
  schema,
  values,
  onChange,
}: {
  schema: GeneratorSchema;
  values: Record<string, ParamValue>;
  onChange: (id: string, v: ParamValue) => void;
}): React.JSX.Element {
  return (
    <>
      {schema.properties.map((f) => (
        <ParamField
          key={f.id}
          field={f}
          value={values[f.id] != null ? values[f.id] : (f.default ?? null)}
          onChange={onChange}
        />
      ))}
    </>
  );
}
