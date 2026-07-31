#!/usr/bin/env python3
# ruff: noqa: T201  # CLI script uses print for progress output
"""Convert an MP4 animation into an iOS Live Photo bundle.

A Live Photo is a still image + motion video pair that share a matching
``ContentIdentifier`` (a UUID): the image carries it in its Apple MakerNote
(key "17"), the video in its QuickTime metadata. iOS Photos pairs the two
files when the values match, and the result can be set as a lock-screen Live
Wallpaper (press-and-hold to animate).

This script:

1. Re-times the source MP4 into a portrait MOV tuned for a lock screen.
   ``--start-sec``, ``--speed`` and ``--duration`` select *which* part of the
   animation is shown and at what tempo — so the time signature of the source
   (e.g. high-fps slow-motion regions) is under your control, not flattened.
2. Extracts a still frame and encodes it as HEIC (``pillow-heif``).
3. Adds the ``com.apple.quicktime.still-image-time`` timed-metadata track
   (mebx) to the MOV — the track iOS needs to enable lock-screen motion.
4. Stamps the shared ContentIdentifier into both files (``makelive``, macOS).
5. Writes a ``manifest.json`` and a ``.pvt`` bundle that imports into macOS
   Photos by double-clicking (then syncs to an iPhone via iCloud).

Usage:
  uv run scripts/mp4_to_live_photo.py output/flowing_curve_....mp4 --model pro
  uv run scripts/mp4_to_live_photo.py input.mp4 --speed 0.5 --start-sec 1.0 --fps 60
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import uuid
from dataclasses import asdict
from pathlib import Path

import numpy as np
from PIL import Image

from fluxwall.core.exporters.heic import HEIF_AVAILABLE, save_heic  # type: ignore[import-untyped]
from fluxwall.core.exporters.live_photo import LivePhotoManifest  # type: ignore[import-untyped]

# Logical iPhone resolutions, portrait (see AGENTS.md).
MODEL_PRESETS: dict[str, tuple[int, int]] = {
    'pro-max': (1290, 2796),  # iPhone 15/16 Pro Max
    'pro': (1179, 2556),  # iPhone 15/16 Pro
    'pro-old': (1170, 2532),  # iPhone 14/13/12 Pro
    'se': (750, 1334),  # iPhone SE / 8
}

HEVC_VT_Q = 65


class LivePhotoError(RuntimeError):
    """Raised when a step of the Live Photo pipeline fails."""


def probe_video(path: Path) -> dict[str, float | int]:
    """Return duration (s) and frame rate of the video via ffprobe."""
    result = subprocess.run(
        [
            'ffprobe',
            '-v',
            'error',
            '-select_streams',
            'v:0',
            '-show_entries',
            'stream=duration,r_frame_rate',
            '-show_entries',
            'format=duration',
            '-of',
            'json',
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    stream = (data.get('streams') or [{}])[0]
    fmt = data.get('format') or {}
    duration = float(stream.get('duration') or fmt.get('duration') or 0.0)
    num, _, den = str(stream.get('r_frame_rate') or '0/1').partition('/')
    fps = int(num) / int(den) if int(den) else 0.0
    return {'duration': duration, 'fps': fps}


def even_resolution(w: int, h: int) -> tuple[int, int]:
    """Round width/height down to even values (required for yuv420p)."""
    return w - (w % 2), h - (h % 2)


def build_filter_graph(
    speed: float,
    fps: int,
    width: int,
    height: int,
    interpolate: bool,
) -> str:
    """Build the ffmpeg -vf chain that re-times and re-frames the source.

    ``setpts=(1/speed)*PTS`` time-stretches: speed < 1 = slow motion,
    speed > 1 = fast-forward. The resample step then fixes the output frame
    rate (plain ``fps`` drops/duplicates frames; ``framerate`` blends them for
    smoother temporal interpolation).
    """
    filters = [f'setpts=(1/{speed})*PTS']
    if interpolate:
        filters.append(f'framerate=fps={fps}')
    else:
        filters.append(f'fps={fps}')
    filters.append(f'scale={width}:{height}:force_original_aspect_ratio=increase')
    filters.append(f'crop={width}:{height}')
    filters.append('setsar=1')
    return ','.join(filters)


def transcode_motion(
    input_path: Path,
    output_path: Path,
    start_sec: float,
    window_len: float,
    duration: float,
    speed: float,
    fps: int,
    width: int,
    height: int,
    codec: str,
    crf: int,
    preset: str,
    interpolate: bool,
    quiet: bool,
) -> None:
    """Transcode a window of the source into a portrait HEVC/hvc1 MOV."""
    cmd = [
        'ffmpeg',
        '-y',
        '-v',
        'error',
        '-ss',
        f'{start_sec:.6f}',
        '-t',
        f'{window_len:.6f}',
        '-i',
        str(input_path),
        '-map',
        '0:v:0',
        '-vf',
        build_filter_graph(speed, fps, width, height, interpolate),
        '-c:v',
        codec,
    ]
    if codec == 'hevc_videotoolbox':
        cmd += ['-q:v', str(HEVC_VT_Q), '-allow_sw', '1']
    else:
        cmd += ['-crf', str(crf), '-preset', preset]
    cmd += [
        '-tag:v',
        'hvc1',
        '-pix_fmt',
        'yuv420p',
        '-an',
        '-sn',
        '-dn',
        '-t',
        f'{duration:.6f}',
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=quiet, text=True)


def extract_still(
    motion_path: Path,
    still_sec: float,
    output_png: Path,
    quiet: bool,
) -> None:
    """Extract a single frame from the finished MOV as a PNG."""
    subprocess.run(
        [
            'ffmpeg',
            '-y',
            '-v',
            'error',
            '-ss',
            f'{still_sec:.6f}',
            '-i',
            str(motion_path),
            '-frames:v',
            '1',
            str(output_png),
        ],
        check=True,
        capture_output=quiet,
        text=True,
    )


def make_still_heic(png_path: Path, output_heic: Path, quality: int) -> None:
    """Encode the extracted still as HEIC via pillow-heif."""
    if not HEIF_AVAILABLE:
        raise LivePhotoError('pillow-heif is not available. Install it with: uv add pillow-heif')
    frame = np.asarray(Image.open(png_path).convert('RGB'))
    save_heic(frame, output_heic, quality=quality)


def stamp_live_photo(still_heic: Path, motion_mov: Path, asset_id: str) -> None:
    """Stamp the shared ContentIdentifier into both files (requires makelive)."""
    try:
        import makelive  # type: ignore[import-untyped]
    except ImportError as exc:
        raise LivePhotoError(
            'makelive is required to write the iOS ContentIdentifier metadata.\n'
            '  Install it (macOS only) with: uv sync --extra livephoto\n'
            '  or: uv add --optional livephoto makelive'
        ) from exc

    makelive.make_live_photo(str(still_heic), str(motion_mov), asset_id=asset_id)

    image_id = makelive.live_id(str(still_heic))
    video_id = makelive.live_id(str(motion_mov))
    if not (image_id == video_id == asset_id):
        raise LivePhotoError(
            f'ContentIdentifier mismatch after stamping: image={image_id!r} video={video_id!r} expected={asset_id!r}'
        )


def write_manifest(
    out_dir: Path,
    asset_id: str,
    duration: float,
    width: int,
    height: int,
) -> None:
    """Write the Live Photo bundle manifest (project convention)."""
    manifest = LivePhotoManifest(
        still_image='still.heic',
        motion_video='motion.mov',
        still_identifier=asset_id,
        motion_identifier=asset_id,
        duration=duration,
        render_type='live_photo',
        width=width,
        height=height,
    )
    with (out_dir / 'manifest.json').open('w') as f:
        json.dump(asdict(manifest), f, indent=2)


def add_still_image_time(mov_path: Path, still_sec: float) -> None:
    """Add the ``com.apple.quicktime.still-image-time`` timed-metadata track.

    iOS reads this mebx track to know where the still frame sits in the video;
    without it the pair shows in Photos but the lock screen reports "Motion Not
    Available". ffmpeg cannot write mebx tracks (it drops them even on `-c copy`),
    so this re-muxes the video with AVFoundation (sample passthrough, no
    re-encode) and appends the single-sample timed-metadata track via an
    AVAssetWriter metadata adaptor. The writer emits a leading empty edit, so the
    sample's presentation time equals the still moment — matching real iPhone
    Live Photo MOVs.
    """
    import threading
    import time

    try:
        import AVFoundation  # type: ignore[import-untyped]
        import CoreMedia  # type: ignore[import-untyped]
        from Foundation import NSURL, NSNumber  # type: ignore[import-untyped]
    except ImportError as exc:
        raise LivePhotoError(
            'makelive (AVFoundation) is required to write the still-image-time track.\n'
            '  Install it (macOS only) with: uv sync --extra livephoto'
        ) from exc

    url = NSURL.fileURLWithPath_(str(mov_path))
    asset = AVFoundation.AVURLAsset.assetWithURL_(url)
    tracks = asset.tracksWithMediaType_(AVFoundation.AVMediaTypeVideo)
    if not tracks:
        raise LivePhotoError(f'No video track found in {mov_path}')
    video_track = tracks[0]

    tmp_path = mov_path.with_name(f'{mov_path.stem}.mebx.mov')

    reader, rerr = AVFoundation.AVAssetReader.assetReaderWithAsset_error_(asset, None)
    if reader is None:
        raise LivePhotoError(f'AVAssetReader could not open {mov_path}: {rerr}')
    reader_output = AVFoundation.AVAssetReaderTrackOutput.alloc().initWithTrack_outputSettings_(video_track, None)
    reader_output.setAlwaysCopiesSampleData_(False)
    reader.addOutput_(reader_output)

    writer, werr = AVFoundation.AVAssetWriter.assetWriterWithURL_fileType_error_(
        NSURL.fileURLWithPath_(str(tmp_path)), AVFoundation.AVFileTypeQuickTimeMovie, None
    )
    if writer is None:
        raise LivePhotoError(f'AVAssetWriter could not create {tmp_path}: {werr}')

    video_input = AVFoundation.AVAssetWriterInput.alloc().initWithMediaType_outputSettings_sourceFormatHint_(
        AVFoundation.AVMediaTypeVideo, None, video_track.formatDescriptions()[0]
    )
    writer.addInput_(video_input)

    spec = {
        CoreMedia.kCMMetadataFormatDescriptionMetadataSpecificationKey_Identifier: (
            'mdta/com.apple.quicktime.still-image-time'
        ),
        CoreMedia.kCMMetadataFormatDescriptionMetadataSpecificationKey_DataType: ('com.apple.metadata.datatype.int8'),
    }
    status, metadata_desc = CoreMedia.CMMetadataFormatDescriptionCreateWithMetadataSpecifications(
        None, CoreMedia.kCMMetadataFormatType_Boxed, [spec], None
    )
    if status != 0:
        raise LivePhotoError(f'Could not build still-image-time metadata description: status {status}')
    metadata_input = AVFoundation.AVAssetWriterInput.alloc().initWithMediaType_outputSettings_sourceFormatHint_(
        AVFoundation.AVMediaTypeMetadata, None, metadata_desc
    )
    writer.addInput_(metadata_input)
    adaptor = AVFoundation.AVAssetWriterInputMetadataAdaptor.alloc().initWithAssetWriterInput_(metadata_input)

    try:
        if not writer.startWriting():
            raise LivePhotoError(f'AVAssetWriter startWriting failed: {writer.error()}')
        if not reader.startReading():
            raise LivePhotoError(f'AVAssetReader startReading failed: {reader.error()}')
        writer.startSessionAtSourceTime_(CoreMedia.kCMTimeZero)

        item = AVFoundation.AVMutableMetadataItem.metadataItem()
        item.setKey_('com.apple.quicktime.still-image-time')
        item.setKeySpace_(AVFoundation.AVMetadataKeySpaceQuickTimeMetadata)
        item.setValue_(NSNumber.numberWithInt_(-1))
        item.setDataType_('com.apple.metadata.datatype.int8')
        still_time = CoreMedia.CMTimeMake(int(still_sec * 600), 600)
        group = AVFoundation.AVTimedMetadataGroup.alloc().initWithItems_timeRange_(
            [item], CoreMedia.CMTimeRangeMake(still_time, CoreMedia.CMTimeMake(1, 600))
        )
        if not adaptor.appendTimedMetadataGroup_(group):
            raise LivePhotoError(f'Could not append still-image-time metadata: {writer.error()}')
        metadata_input.markAsFinished()

        done = False
        while not done:
            while video_input.isReadyForMoreMediaData():
                sample = reader_output.copyNextSampleBuffer()
                if sample is None:
                    video_input.markAsFinished()
                    done = True
                    break
                if not video_input.appendSampleBuffer_(sample):
                    raise LivePhotoError(f'Failed to write video samples: {writer.error()}')
            if not done:
                time.sleep(0.002)

        reader.cancelReading()
        finished = threading.Event()
        writer.finishWritingWithCompletionHandler_(finished.set)
        if not finished.wait(120):
            raise LivePhotoError('Timed out waiting for AVAssetWriter to finish')
        if writer.status() != AVFoundation.AVAssetWriterStatusCompleted:
            raise LivePhotoError(f'AVAssetWriter failed: {writer.error()}')

        tmp_path.replace(mov_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def make_pvt(out_dir: Path, base_name: str, asset_id: str) -> Path:
    """Package the pair as a .pvt bundle for macOS Photos import (makelive).

    A .pvt is a folder (shown by Finder as a single file) containing
    metadata.plist plus the stamped still/motion pair. Double-clicking it on
    macOS imports the Live Photo straight into Photos, which then syncs to an
    iPhone via iCloud.
    """
    try:
        import makelive
    except ImportError as exc:
        raise LivePhotoError(
            'makelive is required to write the .pvt package.  Install it (macOS only) with: uv sync --extra livephoto'
        ) from exc

    _, pvt_package = makelive.save_live_photo_pair_as_pvt(
        str(out_dir / 'still.heic'),
        str(out_dir / 'motion.mov'),
        pvt_path=str(out_dir),
        asset_id=asset_id,
    )
    pvt_path = out_dir.parent / f'{base_name}.pvt'
    if pvt_package != pvt_path:
        if pvt_path.is_dir():
            shutil.rmtree(pvt_path)
        pvt_path.unlink(missing_ok=True)
        pvt_package.rename(pvt_path)
    return pvt_path


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='Convert an MP4 into an iOS Live Photo bundle')
    p.add_argument('input', help='Input MP4 (e.g. a flowing_curve_demo.py output)')
    p.add_argument(
        '--model',
        choices=sorted(MODEL_PRESETS),
        default='pro',
        help='iPhone preset resolution (default: pro = 15/16 Pro). Overridden by --width/--height.',
    )
    p.add_argument('--width', type=int, help='Output width (overrides --model)')
    p.add_argument('--height', type=int, help='Output height (overrides --model)')
    p.add_argument('--fps', type=int, default=30, help='Output frame rate (default: 30)')
    p.add_argument(
        '--duration',
        type=float,
        default=3.0,
        help='Live Photo length in seconds (default: 3)',
    )
    p.add_argument(
        '--start-sec',
        type=float,
        default=0.0,
        help='Where in the source to start the clip, in source seconds (default: 0)',
    )
    p.add_argument(
        '--speed',
        type=float,
        default=1.0,
        help='Playback speed vs source: 1.0 = same tempo, 0.5 = 2x slow motion, '
        '2.0 = 2x fast-forward (default: 1). Keeps the source time signature; '
        'does not flatten it.',
    )
    p.add_argument(
        '--still-sec',
        type=float,
        default=1.0,
        help='Frame (in output time) to use as the HEIC still (default: 1)',
    )
    p.add_argument(
        '--codec',
        choices=['libx265', 'hevc_videotoolbox'],
        default='libx265',
        help='HEVC encoder: libx265 (portable) or hevc_videotoolbox (macOS HW)',
    )
    p.add_argument('--crf', type=int, default=18, help='libx265 quality (default: 18)')
    p.add_argument('--preset', default='medium', help='libx265 preset (default: medium)')
    p.add_argument(
        '--interpolate',
        action='store_true',
        help='Blend frames when resampling instead of dropping/duplicating — '
        'smoother motion when downsampling from a high-fps source',
    )
    p.add_argument('--quality', type=int, default=90, help='HEIC still quality (default: 90)')
    p.add_argument('--output', default='output', help='Output directory (default: output)')
    p.add_argument('--base-name', help='Base name for outputs (default: <input stem>_livephoto)')
    p.add_argument('--quiet', action='store_true', help='Suppress ffmpeg output')
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f'Error: input not found: {input_path}', file=sys.stderr)
        return 2

    if (args.width is None) != (args.height is None):
        print('Error: --width and --height must be provided together', file=sys.stderr)
        return 2
    if args.width is not None and args.height is not None:
        width, height = args.width, args.height
    else:
        width, height = MODEL_PRESETS[args.model]
    width, height = even_resolution(width, height)

    if args.speed <= 0:
        print('Error: --speed must be > 0', file=sys.stderr)
        return 2
    if args.duration <= 0:
        print('Error: --duration must be > 0', file=sys.stderr)
        return 2
    if args.fps < 1:
        print('Error: --fps must be >= 1', file=sys.stderr)
        return 2

    src = probe_video(input_path)
    src_duration = float(src['duration'])
    src_fps = float(src['fps'])

    if args.start_sec >= src_duration:
        print(
            f'Error: --start-sec {args.start_sec} is beyond source length {src_duration:.1f}s',
            file=sys.stderr,
        )
        return 2

    window_len = args.duration * args.speed
    available = src_duration - args.start_sec
    if window_len > available:
        clamped = True
        window_len = available
    else:
        clamped = False
    duration = window_len / args.speed

    if args.fps > src_fps:
        print(f'  Note: output {args.fps}fps > source {src_fps:.0f}fps — frames will be duplicated.')

    base_name = args.base_name or f'{input_path.stem}_livephoto'
    out_dir = Path(args.output) / base_name
    out_dir.mkdir(parents=True, exist_ok=True)
    motion_path = out_dir / 'motion.mov'
    still_png = out_dir / '_still.png'
    still_heic = out_dir / 'still.heic'
    asset_id = str(uuid.uuid4()).upper()

    print(f'  Input:   {input_path} ({src_duration:.1f}s, {src_fps:.0f}fps)')
    print(f'  Output:  {width}x{height} {args.fps}fps, {duration:.2f}s, HEVC/{args.codec}')
    print(
        f'  Window:  source [{args.start_sec:.2f}, {args.start_sec + window_len:.2f}]s '
        f'-> {duration:.2f}s at {args.speed:g}x speed'
    )
    if clamped:
        print(f'  Note:    source too short for full window; effective speed {args.speed:g}x over {duration:.2f}s')

    still_sec = min(max(args.still_sec, 0.0), duration - 1.0 / args.fps)

    print('  Encoding motion.mov …', end=' ', flush=True)
    transcode_motion(
        input_path,
        motion_path,
        args.start_sec,
        window_len,
        duration,
        args.speed,
        args.fps,
        width,
        height,
        args.codec,
        args.crf,
        args.preset,
        args.interpolate,
        args.quiet,
    )
    print('ok')

    print(f'  Adding still-image-time track @ {still_sec:.2f}s …', end=' ', flush=True)
    add_still_image_time(motion_path, still_sec)
    print('ok')

    print(f'  Extracting still @ {still_sec:.2f}s …', end=' ', flush=True)
    extract_still(motion_path, still_sec, still_png, args.quiet)
    make_still_heic(still_png, still_heic, args.quality)
    print('ok')

    print(f'  Stamping ContentIdentifier {asset_id} …', end=' ', flush=True)
    stamp_live_photo(still_heic, motion_path, asset_id)
    print('ok')

    write_manifest(out_dir, asset_id, duration, width, height)

    print('  Packaging .pvt …', end=' ', flush=True)
    pvt_path = make_pvt(out_dir, base_name, asset_id)
    print('ok')

    still_png.unlink(missing_ok=True)

    print()
    print(f'  Done. Bundle in {out_dir}')
    print(f'  Package: {pvt_path}')
    print()
    print(
        '  Import to iPhone: double-click the .pvt on this Mac to import into '
        'Photos, let iCloud sync it to your iPhone, then set it as a lock-screen '
        'Live Wallpaper.'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
