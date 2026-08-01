// Monoline SVG glyph marks (ported from the prototype app layer).
export const GLYPHS: Record<string, string> = {
  grid: '<svg viewBox="0 0 24 24" fill="none" stroke-width="1.6"><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M9 4v16M15 4v16M4 9h16M4 15h16"/></svg>',
  fractal:
    '<svg viewBox="0 0 24 24" fill="none" stroke-width="1.6"><circle cx="12" cy="12" r="3.2"/><path d="M12 8.8V4M12 15.2V20M8.8 12H4M15.2 12H20M9.9 9.9L7 7M14.1 14.1L17 17M14.1 9.9L17 7M9.9 14.1L7 17"/></svg>',
  spiral:
    '<svg viewBox="0 0 24 24" fill="none" stroke-width="1.6"><path d="M12 12m-9 0a9 9 0 1 1 18 0a9 9 0 1 1-18 0"/><path d="M12 12m-4.5 0a4.5 4.5 0 1 1 9 0a4.5 4.5 0 1 1-9 0"/></svg>',
  curve:
    '<svg viewBox="0 0 24 24" fill="none" stroke-width="1.6"><path d="M3 14c2-8 4-8 6 0s4 8 6 0 4-8 6 0"/><path d="M3 18c2-8 4-8 6 0s4 8 6 0 4-8 6 0" opacity=".5"/></svg>',
  branch:
    '<svg viewBox="0 0 24 24" fill="none" stroke-width="1.6"><path d="M12 3v14M12 17c-4 0-5-2-6-5M12 14c3 0 4-1.5 5-4M12 20c-1.5 0-2.5 1-3 3M12 20c1.5 0 2.5 1 3 3"/></svg>',
  waves:
    '<svg viewBox="0 0 24 24" fill="none" stroke-width="1.6"><path d="M3 8c3-4 6 4 9 0s6 4 9 0M3 16c3-4 6 4 9 0s6 4 9 0" opacity=".6"/><path d="M3 12c3-4 6 4 9 0s6 4 9 0" opacity=".35"/></svg>',
  phone:
    '<svg viewBox="0 0 24 24" fill="none" stroke-width="1.5"><rect x="6" y="3" width="12" height="18" rx="3"/><path d="M10 6h4"/></svg>',
};

export function glyph(name: string): string {
  return GLYPHS[name] || GLYPHS.fractal;
}

/** Inline SVG via dangerouslySetInnerHTML for glyph marks. */
export function glyphMarkup(name: string): { __html: string } {
  return { __html: glyph(name) };
}
