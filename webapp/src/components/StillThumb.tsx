import { useEffect, useRef } from 'react';
import type { Params } from '../lib/types';
import { renderStill } from '../lib/render';

interface StillThumbProps {
  generator: string;
  params: Params;
  width: number;
  height: number;
  phase?: number;
  className?: string;
}

/** Static single-frame canvas thumbnail (real render, not a fake image). */
export function StillThumb({ generator, params, width, height, phase = 0, className }: StillThumbProps): React.JSX.Element {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const cv = ref.current;
    if (cv) renderStill(cv, generator, params, phase);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [generator, params, width, height, phase]);

  return <canvas ref={ref} width={width} height={height} className={className} />;
}
