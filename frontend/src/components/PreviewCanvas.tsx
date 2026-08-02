import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';
import type { Params } from '../lib/types';
import { PreviewEngine } from '../lib/render';

export interface PreviewHandle {
  /** Reset phase / frame / GOL state without touching the rAF loop. */
  reset: () => void;
}

interface PreviewCanvasProps {
  generator: string;
  params: Params;
  playing: boolean;
  onPlayingChange?: (playing: boolean) => void;
  width?: number;
  height?: number;
  className?: string;
}

/**
 * Live animated preview on a canvas. Restarts the render engine whenever
 * `generator` or `params` changes (mirrors the MJPEG stream restart);
 * play/pause is a controlled prop.
 */
export const PreviewCanvas = forwardRef<PreviewHandle, PreviewCanvasProps>(function PreviewCanvas(
  { generator, params, playing, onPlayingChange, width = 120, height = 260, className },
  ref,
) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const engineRef = useRef<PreviewEngine | null>(null);
  if (!engineRef.current) engineRef.current = new PreviewEngine();

  useEffect(() => {
    const engine = engineRef.current as PreviewEngine;
    engine.start(canvasRef.current as HTMLCanvasElement, generator, params);
    onPlayingChange?.(true);
    return () => engine.stop();
    // restart only on generator/param change; callback identity is stable
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [generator, params]);

  useEffect(() => {
    const engine = engineRef.current as PreviewEngine;
    if (playing) engine.play();
    else engine.pause();
  }, [playing]);

  useImperativeHandle(
    ref,
    () => ({
      reset: () => {
        (engineRef.current as PreviewEngine).reset(generator, params);
      },
    }),
    [generator, params],
  );

  return <canvas ref={canvasRef} width={width} height={height} className={className} data-od-id="preview-canvas" />;
});
