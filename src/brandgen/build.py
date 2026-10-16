# SPDX-FileCopyrightText: 2026 brandgen developers
#
# SPDX-License-Identifier: Apache-2.0

"""Planning and running a build.

A build reads a source directory, prepares the three marks (the logo is
composed from the other two), derives one SVG per mark, colourway,
background and padding, renders it to every requested format, and records
every written file in ``manifest.json`` at the top of the output directory.
"""

from __future__ import annotations

import collections.abc as _abc
import concurrent.futures as _futures
import dataclasses as _dataclasses
import hashlib as _hashlib
import json as _json
import pathlib as _pathlib

import brandgen.document as _document
import brandgen.geometry as _geometry
import brandgen.lockup as _lockup
import brandgen.measure as _measure
import brandgen.metadata as _metadata
import brandgen.render as _render
import brandgen.source as _source
import brandgen.typeset as _typeset
import brandgen.variant as _variant


@_dataclasses.dataclass(frozen=True)
class Config:
    """Everything a build needs to know."""

    source: _pathlib.Path
    output: _pathlib.Path
    name: str
    marks: tuple[_variant.Mark, ...]
    colorways: tuple[_variant.Colorway, ...]
    backgrounds: tuple[_variant.Background, ...]
    paddings: tuple[_variant.Padding, ...]
    formats: tuple[_variant.Format, ...]
    png_widths: tuple[int, ...]
    pdf_width_mm: float
    layout: _lockup.Layout
    jobs: int

    def plan(self) -> list[_variant.Variant]:
        return _variant.plan(
            name=self.name,
            marks=self.marks,
            colorways=self.colorways,
            backgrounds=self.backgrounds,
            paddings=self.paddings,
            formats=self.formats,
            png_widths=self.png_widths,
        )


@_dataclasses.dataclass(frozen=True)
class Prepared:
    """A mark ready for deriving variants: outlined, measured, cleaned."""

    document: _document.Document
    ink: _geometry.Rect
    page: _geometry.Rect


@_dataclasses.dataclass(frozen=True)
class Marks:
    """The prepared marks of one source directory."""

    source: _source.Source
    marks: dict[_variant.Mark, Prepared]
    warnings: tuple[str, ...]


def _load(
    *, path: _pathlib.Path, font: _typeset.Font, notes: list[str]
) -> _document.Document:
    document = _document.clone(document=_document.read(path=path))
    _document.strip_metadata(root=document.root)
    count = _typeset.outline_text(root=document.root, font=font)
    if count:
        notes.append(f"{path.name}: outlined {count} live text element(s)")
    return document


def prepare(*, source: _source.Source, layout: _lockup.Layout) -> Marks:
    """Outline, measure and compose the marks of ``source``."""
    notes: list[str] = []
    font = _typeset.load(path=source.font)

    icon = _load(path=source.icon, font=font, notes=notes)
    icon_ink = _measure.ink(root=icon.root)
    wordmark = _load(path=source.wordmark, font=font, notes=notes)
    wordmark_ink = _measure.ink(root=wordmark.root)
    baseline = _measure.baseline(
        root=wordmark.root, box=wordmark_ink, font=font
    )
    if baseline.warning is not None:
        notes.append(f"{source.wordmark.name}: {baseline.warning}")

    logo = _lockup.compose(
        icon=_lockup.Part(document=icon, ink=icon_ink, baseline=icon_ink.y1),
        wordmark=_lockup.Part(
            document=wordmark, ink=wordmark_ink, baseline=baseline.y
        ),
        layout=layout,
    )
    marks = {
        _variant.Mark.ICON: Prepared(
            document=icon,
            ink=icon_ink,
            page=_document.page(root=icon.root),
        ),
        _variant.Mark.WORDMARK: Prepared(
            document=wordmark,
            ink=wordmark_ink,
            page=_document.page(root=wordmark.root),
        ),
        _variant.Mark.LOGO_HORIZONTAL: Prepared(
            document=logo.document,
            ink=_measure.ink(root=logo.document.root),
            page=logo.page,
        ),
    }
    return Marks(source=source, marks=marks, warnings=tuple(notes))


def derive(
    *,
    prepared: Prepared,
    colorway: _variant.Colorway,
    background: _variant.Background,
    padding: _variant.Padding,
) -> tuple[bytes, _geometry.Rect]:
    """One variant SVG and its canvas."""
    document = _document.clone(document=prepared.document)
    if colorway.ink is not None:
        _document.recolor(root=document.root, ink=colorway.ink)
    canvas = padding.canvas(ink=prepared.ink, page=prepared.page)
    _document.set_canvas(root=document.root, canvas=canvas)
    if background.fill is not None:
        _document.add_background(
            root=document.root, canvas=canvas, fill=background.fill
        )
    return _document.serialize(document=document), canvas


def _digest(*, path: _pathlib.Path) -> str:
    return _hashlib.sha256(path.read_bytes()).hexdigest()


@_dataclasses.dataclass(frozen=True)
class Result:
    written: tuple[_pathlib.Path, ...]
    warnings: tuple[str, ...]
    manifest: _pathlib.Path


def run(
    *,
    config: Config,
    progress: _abc.Callable[[str], None] | None,
) -> Result:
    """Write every planned variant and the manifest."""
    marks = prepare(
        source=_source.locate(directory=config.source),
        layout=config.layout,
    )
    groups: dict[tuple, list[_variant.Variant]] = {}
    for item in config.plan():
        groups.setdefault(item.key, []).append(item)

    def emit(members: list[_variant.Variant]) -> list[dict]:
        first = members[0]
        svg, canvas = derive(
            prepared=marks.marks[first.mark],
            colorway=first.colorway,
            background=first.background,
            padding=first.padding,
        )
        records = []
        for item in members:
            path = config.output / item.relpath
            path.parent.mkdir(parents=True, exist_ok=True)
            if item.format is _variant.Format.SVG:
                path.write_bytes(svg)
            else:
                width = (
                    float(item.width)
                    if item.width is not None
                    else _render.pdf_width(millimetres=config.pdf_width_mm)
                )
                _render.render(svg=svg, path=path, fmt=item.format, width=width)
            record = {
                "path": item.relpath,
                "mark": item.mark.value,
                "colorway": item.colorway.value,
                "background": item.background.value,
                "padding": item.padding.value,
                "format": item.format.value,
                "canvas": _dataclasses.asdict(canvas),
                "bytes": path.stat().st_size,
                "sha256": _digest(path=path),
            }
            if item.width is not None:
                record["width_px"] = item.width
            records.append(record)
            if progress is not None:
                progress(item.relpath)
        return records

    ordered = [groups[key] for key in sorted(groups, key=_sort_key)]
    with _futures.ThreadPoolExecutor(max_workers=max(1, config.jobs)) as pool:
        batches = list(pool.map(emit, ordered))
    files = sorted(
        (record for batch in batches for record in batch),
        key=lambda record: record["path"],
    )

    layout = config.layout
    manifest = {
        "generator": "brandgen",
        "version": _metadata.__version__,
        "name": config.name,
        "sources": {
            path.name: _digest(path=path) for path in marks.source.files()
        },
        "lockup": {
            "mark": _variant.Mark.LOGO_HORIZONTAL.value,
            "arrangement": layout.arrangement.value,
            "body": layout.body,
            "gap": layout.gap,
        },
        "paddings": {
            padding.value: {
                "ratio": padding.ratio,
                "description": padding.description,
            }
            for padding in config.paddings
        },
        "warnings": list(marks.warnings),
        "files": files,
    }
    config.output.mkdir(parents=True, exist_ok=True)
    manifest_path = config.output / "manifest.json"
    manifest_path.write_text(
        _json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return Result(
        written=tuple(config.output / record["path"] for record in files),
        warnings=marks.warnings,
        manifest=manifest_path,
    )


def _sort_key(key: tuple) -> tuple[str, ...]:
    return tuple(member.value for member in key)
