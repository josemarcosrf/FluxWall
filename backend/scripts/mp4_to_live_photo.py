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
3. Adds the iOS timed-metadata tracks (mebx) to the MOV — ``live-photo-info``
   (one 144-byte sample per video frame) and ``still-image-time`` (the 89-byte
   sample that marks the still moment). These are copied from a real iPhone
   Live Photo template and re-timed to the output; without them the pair shows
   in Photos but the lock screen reports "Motion Not Available".
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
import struct
import subprocess
import sys
import uuid
from collections.abc import Iterator
from dataclasses import asdict
from datetime import datetime
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

# Confirmed working as a Lock Screen Live Wallpaper (matches a real Live
# Photo pair extracted from an iPhone: vendor-livp/IMG_7725.MOV/.HEIC).
DEFAULT_RESOLUTION = (1080, 1920)

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


def stamp_device_metadata(motion_mov: Path) -> None:
    """Add ``com.apple.quicktime.{make,model,software,creationdate}`` metadata.

    Real iPhone Live Photo MOVs carry these QuickTime metadata items; a
    synthetic MOV built by ffmpeg has none of them. Writes only the movie
    header in place (same technique makelive uses for ContentIdentifier), so
    all track data including the mebx tracks is preserved untouched.
    """
    import AVFoundation  # type: ignore[import-untyped]
    import objc  # type: ignore[import-untyped]
    from Foundation import NSURL  # type: ignore[import-untyped]

    def _item(key: str, value: str) -> AVFoundation.AVMutableMetadataItem:
        item = AVFoundation.AVMutableMetadataItem.metadataItem()
        item.setKey_(key)
        item.setKeySpace_('mdta')
        item.setValue_(value)
        item.setDataType_('com.apple.metadata.datatype.UTF-8')
        return item

    device_keys = {
        'com.apple.quicktime.make',
        'com.apple.quicktime.model',
        'com.apple.quicktime.software',
        'com.apple.quicktime.creationdate',
    }
    with objc.autorelease_pool():
        url = NSURL.fileURLWithPath_(str(motion_mov))
        movie, error = AVFoundation.AVMutableMovie.movieWithURL_options_error_(url, None, None)
        if movie is None:
            raise LivePhotoError(
                f'Could not open {motion_mov} as AVMutableMovie: {error.description() if error else "unknown error"}'
            )

        existing = [
            item
            for item in (movie.metadata() or [])
            if not (str(item.keySpace()) == 'mdta' and str(item.key()) in device_keys)
        ]
        creation_date = datetime.now().astimezone().strftime('%Y-%m-%dT%H:%M:%S%z')
        new_items = [
            _item('com.apple.quicktime.make', 'Apple'),
            _item('com.apple.quicktime.model', 'iPhone'),
            _item('com.apple.quicktime.software', '18.7'),
            _item('com.apple.quicktime.creationdate', creation_date),
        ]
        movie.setMetadata_(existing + new_items)

        success, error = movie.writeMovieHeaderToURL_fileType_options_error_(
            url, AVFoundation.AVFileTypeQuickTimeMovie, 0, None
        )
        if not success:
            raise LivePhotoError(
                f'writeMovieHeaderToURL failed for {motion_mov}: {error.description() if error else "unknown error"}'
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


# Template data for the iOS mebx timed-metadata tracks. Extracted from a real
# iPhone Live Photo MOV (vendor-livp/IMG_7673.MOV); the static boxes (stsd, hdlr,
# gmhd, dref, elst) and the sample bytes are replayed verbatim, only the timing
# (stts/stsc/stsz/stco) and track ids are recomputed for the output video.
_MEBX_TEMPLATE = Path(__file__).resolve().parent / '_mebx_template.json'


def _iter_boxes(data: bytes, start: int, end: int) -> Iterator[tuple[bytes, int, int]]:
    """Yield ``(box_type, box_start, box_end)`` for boxes within ``data[start:end]``."""
    pos = start
    while pos + 8 <= end:
        size = struct.unpack('>I', data[pos : pos + 4])[0]
        box_type = data[pos + 4 : pos + 8]
        header = 8
        if size == 1:
            size = struct.unpack('>Q', data[pos + 8 : pos + 16])[0]
            header = 16
        elif size == 0:
            size = end - pos
        if size < header or pos + size > end:
            break
        yield box_type, pos, pos + size
        pos += size


def _find_box(data: bytes, box_type: bytes, start: int, end: int) -> list[tuple[int, int]]:
    """Return ``(start, end)`` of the direct-child boxes of ``box_type``."""
    return [(s, e) for t, s, e in _iter_boxes(data, start, end) if t == box_type]


def _box(box_type: bytes, *parts: bytes) -> bytes:
    """Build a box from its 4-byte type and payload parts."""
    payload = b''.join(parts)
    return struct.pack('>I4s', 8 + len(payload), box_type) + payload


def _fullbox(flags: int, payload: bytes) -> bytes:
    """Build a version-0 full box body (version/flags followed by payload)."""
    return struct.pack('>I', flags) + payload


def _elst_box(entries: list[tuple[int, int]]) -> bytes:
    """Build an edit-list box; ``media_time`` of -1 marks an empty edit."""
    payload = struct.pack('>I', len(entries))
    for segment_duration, media_time in entries:
        payload += struct.pack('>IiHH', segment_duration, media_time, 1, 0)
    return _box(b'elst', _fullbox(0, payload))


def _stts_box(entries: list[tuple[int, int]]) -> bytes:
    """Build a sample-to-time box from ``(sample_count, delta)`` runs."""
    payload = struct.pack('>I', len(entries))
    for count, delta in entries:
        payload += struct.pack('>II', count, delta)
    return _box(b'stts', _fullbox(0, payload))


def _stsc_box(entries: list[tuple[int, int, int]]) -> bytes:
    """Build a sample-to-chunk box from ``(first_chunk, samples_per_chunk, desc)`` runs."""
    payload = struct.pack('>I', len(entries))
    for first_chunk, samples_per_chunk, desc_index in entries:
        payload += struct.pack('>III', first_chunk, samples_per_chunk, desc_index)
    return _box(b'stsc', _fullbox(0, payload))


def _stsz_box(sample_size: int, sample_count: int) -> bytes:
    """Build a sample-size box for uniformly sized samples."""
    return _box(b'stsz', _fullbox(0, struct.pack('>II', sample_size, sample_count)))


def _stco_box(chunk_offsets: list[int]) -> bytes:
    """Build a chunk-offset box."""
    payload = struct.pack('>I', len(chunk_offsets))
    for offset in chunk_offsets:
        payload += struct.pack('>I', offset)
    return _box(b'stco', _fullbox(0, payload))


def _build_trak(
    tkhd: bytes,
    mdhd: bytes,
    mdia_hdlr: bytes,
    gmhd: bytes,
    minf_hdlr: bytes,
    dref: bytes,
    stsd: bytes,
    elst: bytes,
    stts: bytes,
    stsc: bytes,
    stsz: bytes,
    stco: bytes,
) -> bytes:
    """Assemble a track box from its static template boxes + computed tables."""
    stbl = _box(b'stbl', stsd, stts, stsc, stsz, stco)
    minf = _box(b'minf', gmhd, minf_hdlr, _box(b'dinf', dref), stbl)
    mdia = _box(b'mdia', mdhd, mdia_hdlr, minf)
    return _box(b'trak', tkhd, _box(b'edts', elst), mdia)


def _patch_track_timing(
    tkhd: bytes, mdhd: bytes, track_id: int, tkhd_duration: int, mdhd_duration: int
) -> tuple[bytes, bytes]:
    """Patch the track id and durations into template tkhd/mdhd boxes."""
    tkhd_buf = bytearray(tkhd)
    tkhd_buf[20:24] = struct.pack('>I', track_id)
    tkhd_buf[28:32] = struct.pack('>I', tkhd_duration)
    mdhd_buf = bytearray(mdhd)
    mdhd_buf[24:28] = struct.pack('>I', mdhd_duration)
    return bytes(tkhd_buf), bytes(mdhd_buf)


def _read_u32_box_field(data: bytes, box_start: int, field_offset: int) -> int:
    return int(struct.unpack('>I', data[box_start + field_offset : box_start + field_offset + 4])[0])


def inject_mebx_tracks(mov_path: Path, still_sec: float, fps: int) -> None:
    """Add the ``live-photo-info`` and ``still-image-time`` mebx tracks to a MOV.

    iOS reads these timed-metadata tracks to enable lock-screen Live Wallpaper
    motion. ffmpeg drops mebx tracks even on ``-c copy``, and AVFoundation only
    emits a single 1-byte ``still-image-time`` sample — which Photos ignores, so
    the lock screen reports "Motion Not Available". Real iPhone Live Photo MOVs
    carry a ``live-photo-info`` track (one 144-byte sample per video frame) plus
    a ``still-image-time`` track whose single 89-byte sample marks the still
    moment. This re-muxes the video byte-for-byte (no re-encode) and appends both
    tracks, reusing the template's static boxes and sample bytes verbatim while
    recomputing the sample tables and track ids for this video.
    """
    if not _MEBX_TEMPLATE.is_file():
        raise LivePhotoError(
            f'Missing Live Photo template {_MEBX_TEMPLATE.name} '
            '(extracted from a real iPhone Live Photo, vendor-livp/IMG_7673.MOV).'
        )
    tpl = json.loads(_MEBX_TEMPLATE.read_text())
    lpi = tpl['lpi']
    sit = tpl['sit']

    data = mov_path.read_bytes()
    top = {t: (s, e) for t, s, e in _iter_boxes(data, 0, len(data))}
    if b'moov' not in top or b'mdat' not in top:
        raise LivePhotoError(f'Expected a moov+mdat layout in {mov_path}')
    moov_s, moov_e = top[b'moov']
    children_start = moov_s + 8

    mvhd_list = _find_box(data, b'mvhd', children_start, moov_e)
    trak_list = _find_box(data, b'trak', children_start, moov_e)
    if not mvhd_list or not trak_list:
        raise LivePhotoError(f'No mvhd/trak found in {mov_path}')
    mvhd_s, mvhd_e = mvhd_list[0]
    video_trak_s, video_trak_e = trak_list[0]
    video_trak = data[video_trak_s:video_trak_e]

    # Movie timescale + duration come from the ffmpeg video track.
    tkhd_list = _find_box(video_trak, b'tkhd', 8, len(video_trak))
    if not tkhd_list:
        raise LivePhotoError(f'No tkhd found in video track of {mov_path}')
    movie_duration = _read_u32_box_field(video_trak, tkhd_list[0][0], 28)

    # Number of video frames from the stts table (all runs summed).
    num_frames = 0
    mdia_list = _find_box(video_trak, b'mdia', 8, len(video_trak))
    mdia_s, mdia_e = mdia_list[0]
    minf_list = _find_box(video_trak, b'minf', mdia_s + 8, mdia_e)
    minf_s, minf_e = minf_list[0]
    stbl_list = _find_box(video_trak, b'stbl', minf_s + 8, minf_e)
    stbl_s, stbl_e = stbl_list[0]
    for stts_s, _stts_e in _find_box(video_trak, b'stts', stbl_s + 8, stbl_e):
        entry_count = _read_u32_box_field(video_trak, stts_s, 12)
        for i in range(entry_count):
            base = stts_s + 16 + i * 8
            num_frames += struct.unpack('>I', video_trak[base : base + 4])[0]
    if num_frames == 0:
        raise LivePhotoError(f'No video samples found in {mov_path}')

    # live-photo-info track: one 144-byte sample per video frame, but the track
    # itself always starts a bit after the video (matches real iPhone captures
    # and IntoLive-converted files alike: 57 samples for a 60-frame/60fps clip,
    # i.e. a 5% lead-in gap -- only confirmed at 1s duration so far, applied
    # proportionally here rather than as a fixed time offset).
    lead_gap_fraction = 0.05
    lead_gap_frames = max(0, min(num_frames - 1, round(lead_gap_fraction * num_frames)))
    lpi_num_samples = num_frames - lead_gap_frames
    lead_gap_ticks_movie = round(lead_gap_fraction * movie_duration)

    lpi_ts = int(lpi['timescale'])  # 60000
    sample_delta = lpi_ts // fps
    lpi_sample = bytes.fromhex(lpi['samples'][0])
    lpi_mdhd_dur = lpi_num_samples * sample_delta
    lpi_elst = _elst_box([(lead_gap_ticks_movie, -1), (movie_duration - lead_gap_ticks_movie, 0)])
    lpi_tkhd, lpi_mdhd = _patch_track_timing(
        bytes.fromhex(lpi['tkhd']), bytes.fromhex(lpi['mdhd']), 2, movie_duration, lpi_mdhd_dur
    )

    # still-image-time track: single 89-byte sample placed at the still moment.
    sit_ts = int(sit['timescale'])  # 600
    sit_sample = bytes.fromhex(sit['samples'][0])
    still_ticks = int(round(still_sec * sit_ts))
    still_ticks = max(still_ticks, 0)
    sit_elst = _elst_box([(still_ticks, -1), (1, 0)]) if still_ticks else _elst_box([(1, 0)])
    sit_tkhd_dur = still_ticks + 1
    sit_tkhd, sit_mdhd = _patch_track_timing(bytes.fromhex(sit['tkhd']), bytes.fromhex(sit['mdhd']), 3, sit_tkhd_dur, 1)

    # mebx samples are appended in their own mdat right after the video mdat.
    mebx_data = lpi_sample * lpi_num_samples + sit_sample
    mebx_data_start = moov_s + 8
    lpi_chunk_offset = mebx_data_start
    sit_chunk_offset = lpi_chunk_offset + lpi_num_samples * len(lpi_sample)

    lpi_trak = _build_trak(
        lpi_tkhd,
        lpi_mdhd,
        bytes.fromhex(lpi['mdia_hdlr']),
        bytes.fromhex(lpi['gmhd']),
        bytes.fromhex(lpi['minf_hdlr']),
        bytes.fromhex(lpi['dref']),
        bytes.fromhex(lpi['stsd']),
        lpi_elst,
        _stts_box([(lpi_num_samples, sample_delta)]),
        _stsc_box([(1, lpi_num_samples, 1)]),
        _stsz_box(len(lpi_sample), lpi_num_samples),
        _stco_box([lpi_chunk_offset]),
    )
    sit_trak = _build_trak(
        sit_tkhd,
        sit_mdhd,
        bytes.fromhex(sit['mdia_hdlr']),
        bytes.fromhex(sit['gmhd']),
        bytes.fromhex(sit['minf_hdlr']),
        bytes.fromhex(sit['dref']),
        bytes.fromhex(sit['stsd']),
        sit_elst,
        _stts_box([(1, 1)]),
        _stsc_box([(1, 1, 1)]),
        _stsz_box(len(sit_sample), 1),
        _stco_box([sit_chunk_offset]),
    )

    mvhd = bytearray(data[mvhd_s:mvhd_e])
    if len(mvhd) >= 108:
        mvhd[104:108] = struct.pack('>I', 4)  # next_track_id = 4

    # Keep the original moov children (mvhd, udta, ...) in order, replacing the
    # video trak and appending the two mebx traks. mvhd is emitted (patched)
    # below, so it must not be duplicated from the source moov.
    other_children = [data[s:e] for t, s, e in _iter_boxes(data, children_start, moov_e) if t not in (b'trak', b'mvhd')]
    new_moov = _box(b'moov', bytes(mvhd), *other_children, video_trak, lpi_trak, sit_trak)
    new_mdat = _box(b'mdat', mebx_data)

    tmp_path = mov_path.with_name(f'{mov_path.stem}.mebx.mov')
    tmp_path.write_bytes(data[:moov_s] + new_mdat + new_moov)
    tmp_path.replace(mov_path)


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
        default=None,
        help='iPhone preset resolution. Overridden by --width/--height. '
        'Default: 1080x1920 (confirmed working as a Lock Screen Live Wallpaper).',
    )
    p.add_argument('--width', type=int, help='Output width (overrides --model)')
    p.add_argument('--height', type=int, help='Output height (overrides --model)')
    p.add_argument('--fps', type=int, default=60, help='Output frame rate (default: 60)')
    p.add_argument(
        '--duration',
        type=float,
        default=1.0,
        help='Live Photo length in seconds (default: 1.0)',
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
        default=None,
        help='Frame (in output time) to use as the HEIC still (default: middle of the clip)',
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
    elif args.model is not None:
        width, height = MODEL_PRESETS[args.model]
    else:
        width, height = DEFAULT_RESOLUTION
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

    still_sec_requested = args.still_sec if args.still_sec is not None else duration / 2
    still_sec = min(max(still_sec_requested, 0.0), duration - 1.0 / args.fps)

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

    print(f'  Adding live-photo-info + still-image-time tracks @ {still_sec:.2f}s …', end=' ', flush=True)
    inject_mebx_tracks(motion_path, still_sec, args.fps)
    print('ok')

    print(f'  Extracting still @ {still_sec:.2f}s …', end=' ', flush=True)
    extract_still(motion_path, still_sec, still_png, args.quiet)
    make_still_heic(still_png, still_heic, args.quality)
    print('ok')

    print(f'  Stamping ContentIdentifier {asset_id} …', end=' ', flush=True)
    stamp_live_photo(still_heic, motion_path, asset_id)
    print('ok')

    print('  Stamping device metadata …', end=' ', flush=True)
    stamp_device_metadata(motion_path)
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
