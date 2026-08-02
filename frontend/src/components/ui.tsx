import type { ReactNode } from 'react';
import { glyph } from '../lib/glyphs';

/** Inline SVG glyph mark (monoline stroke, inherits currentColor). */
export function Glyph({ name, className = '' }: { name: string; className?: string }): ReactNode {
  return <span className={className} dangerouslySetInnerHTML={{ __html: glyph(name) }} aria-hidden="true" />;
}

/** Status pill: base, accent, ok, err. */
export function Badge({
  children,
  tone = '',
}: {
  children: ReactNode;
  tone?: '' | 'accent' | 'ok' | 'err';
}): ReactNode {
  return <span className={'badge' + (tone ? ' ' + tone : '')}>{children}</span>;
}

/** Scaffolded-generator notice (honest, never a dead-feeling button). */
export function Notice({ glyphName, children }: { glyphName: string; children: ReactNode }): ReactNode {
  return (
    <div className="notice" data-od-id="notice-scaffolded">
      <Glyph name={glyphName} />
      <span>{children}</span>
    </div>
  );
}

export function friendlyName(name: string): string {
  return name.replace(/_/g, ' ');
}
