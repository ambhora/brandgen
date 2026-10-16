# SPDX-FileCopyrightText: 2026 brandgen developers
#
# SPDX-License-Identifier: Apache-2.0

"""Rendering derived SVGs to PNG and PDF with cairosvg.

All text is outlined before a document reaches this module, so rendering
needs no fonts and no external programs.
"""

from __future__ import annotations

import pathlib as _pathlib

import cairosvg as _cairosvg

import brandgen.variant as _variant


class RenderError(RuntimeError):
    """Raised when a file could not be rendered."""


def pdf_width(*, millimetres: float) -> float:
    """The cairosvg output width giving a PDF page ``millimetres`` wide.

    cairosvg sizes its output in CSS pixels, 96 to the inch.
    """
    return millimetres / 25.4 * 96.0


def render(
    *,
    svg: bytes,
    path: _pathlib.Path,
    fmt: _variant.Format,
    width: float,
) -> None:
    """Write ``svg`` to ``path`` as ``fmt``, ``width`` CSS pixels wide."""
    writers = {
        _variant.Format.PNG: _cairosvg.svg2png,
        _variant.Format.PDF: _cairosvg.svg2pdf,
    }
    if fmt not in writers:
        raise RenderError(f"cannot render {fmt.value}")
    writers[fmt](bytestring=svg, write_to=str(path), output_width=width)
    if not path.is_file() or path.stat().st_size == 0:
        raise RenderError(f"no output was written for {path.name}")
