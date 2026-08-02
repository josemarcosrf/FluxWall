import type { ReactNode } from 'react';
import { glyph } from '../lib/glyphs';

/** The one flourish: device-frame with display notch. 9:19.5 aspect. */
export function PhoneFrame({ className = '', children }: { className?: string; children: ReactNode }): React.JSX.Element {
  return (
    <div className={'phone' + (className ? ' ' + className : '')}>
      <div className="phone-screen">
        {children}
        <div className="phone-notch" />
      </div>
    </div>
  );
}

/** Scaffolded-generator placeholder inside the frame (honest, framed). */
export function PhonePlaceholder({ glyphName }: { glyphName: string }): React.JSX.Element {
  return (
    <div className="phone-placeholder" data-od-id="preview-ph">
      <span dangerouslySetInnerHTML={{ __html: glyph(glyphName) }} aria-hidden="true" />
      <b>Scaffolded</b>
      <span>Not rendering yet — preview and export disabled.</span>
    </div>
  );
}
