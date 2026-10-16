# SPDX-FileCopyrightText: 2026 brandgen developers
#
# SPDX-License-Identifier: Apache-2.0

import json as _json
import pathlib as _pathlib

import lxml.etree as _etree
import PIL.Image as _image

import brandgen.build as _build
import brandgen.lockup as _lockup
import brandgen.variant as _variant


def _config(
    *,
    source: _pathlib.Path,
    output: _pathlib.Path,
    formats: tuple[_variant.Format, ...],
) -> _build.Config:
    return _build.Config(
        source=source,
        output=output,
        name="brand",
        marks=tuple(_variant.Mark),
        colorways=tuple(_variant.Colorway),
        backgrounds=tuple(_variant.Background),
        paddings=(_variant.Padding.NONE, _variant.Padding.CLEARSPACE),
        formats=formats,
        png_widths=(128,),
        pdf_width_mm=100.0,
        layout=_lockup.Layout(
            arrangement=_lockup.Arrangement.HORIZONTAL, body=0.625, gap=0.25
        ),
        jobs=2,
    )


def test_build_writes_every_planned_file(
    source: _pathlib.Path, tmp_path: _pathlib.Path
) -> None:
    config = _config(
        source=source,
        output=tmp_path / "out",
        formats=tuple(_variant.Format),
    )
    result = _build.run(config=config, progress=None)
    planned = {item.relpath for item in config.plan()}
    manifest = _json.loads(result.manifest.read_text())
    assert {record["path"] for record in manifest["files"]} == planned
    assert all((config.output / path).is_file() for path in planned)
    assert set(manifest["sources"]) == {"icon.svg", "wordmark.svg", "brand.ttf"}
    assert manifest["lockup"]["arrangement"] == "horizontal"

    png = config.output / (
        "logo-horizontal/png/brand-logo-horizontal-color-on-white-none-128px.png"
    )
    assert _image.open(png).width == 128


def test_derived_svgs_keep_the_source_header(
    source: _pathlib.Path, tmp_path: _pathlib.Path
) -> None:
    config = _config(
        source=source,
        output=tmp_path / "out",
        formats=(_variant.Format.SVG,),
    )
    _build.run(config=config, progress=None)
    for mark in ("icon", "logo-horizontal"):
        path = config.output / (
            f"{mark}/svg/brand-{mark}-white-on-black-clearspace.svg"
        )
        text = path.read_text()
        # REUSE-IgnoreStart
        assert "SPDX-License-Identifier: CC0-1.0" in text
        # REUSE-IgnoreEnd
        assert "<metadata" not in text
        root = _etree.fromstring(path.read_bytes())
        fills = {
            element.get("fill")
            for element in root.iter()
            if isinstance(element.tag, str) and element.get("fill")
        }
        assert fills == {"#ffffff", "#000000"}


def test_svg_output_is_reproducible(
    source: _pathlib.Path, tmp_path: _pathlib.Path
) -> None:
    manifests = []
    for run in ("a", "b"):
        config = _config(
            source=source,
            output=tmp_path / run,
            formats=(_variant.Format.SVG, _variant.Format.PNG),
        )
        manifests.append(
            _build.run(config=config, progress=None).manifest.read_text()
        )
    assert manifests[0] == manifests[1]
