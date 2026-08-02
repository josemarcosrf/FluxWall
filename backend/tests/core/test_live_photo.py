"""Tests for the Live Photo export helpers."""

from __future__ import annotations

import zipfile

from fluxwall.core import LivePhotoExporter


def test_create_ios_import_package_excludes_own_zip(tmp_path) -> None:
    bundle = tmp_path / 'bundle'
    bundle.mkdir()
    (bundle / 'still.heic').write_bytes(b'still')
    (bundle / 'motion.mov').write_bytes(b'motion')
    (bundle / 'manifest.json').write_text('{}')

    out_zip = bundle / 'bundle.zip'
    result = LivePhotoExporter.create_ios_import_package(bundle, out_zip)

    assert result == out_zip
    with zipfile.ZipFile(out_zip) as zf:
        names = zf.namelist()
    assert sorted(names) == ['manifest.json', 'motion.mov', 'still.heic']
    assert 'bundle.zip' not in names
