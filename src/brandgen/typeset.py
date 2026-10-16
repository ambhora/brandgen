# SPDX-FileCopyrightText: 2026 brandgen developers
#
# SPDX-License-Identifier: Apache-2.0

"""The brand font: shaping text, measuring it and turning it into outlines.

The font serves two purposes.  Live ``<text>`` in a source file is converted
to outlines with it, so no renderer ever needs the font installed.  And the
wordmark text is shaped with it to find the baseline, which an outlined
wordmark no longer records but which the logo layout depends on.
"""

from __future__ import annotations

import dataclasses as _dataclasses
import pathlib as _pathlib
import re as _re

import fontTools.pens.boundsPen as _boundspen
import fontTools.pens.svgPathPen as _svgpathpen
import fontTools.pens.transformPen as _transformpen
import fontTools.ttLib as _ttlib
import lxml.etree as _etree
import uharfbuzz as _hb

import brandgen.document as _document
import brandgen.geometry as _geometry


@_dataclasses.dataclass(frozen=True, eq=False)
class Font:
    """A loaded brand font."""

    path: _pathlib.Path
    units_per_em: int
    outlines: _ttlib.TTFont
    shaper: _hb.Font


def load(*, path: _pathlib.Path) -> Font:
    """Load the font at ``path``."""
    outlines = _ttlib.TTFont(str(path))
    shaper = _hb.Font(_hb.Face(_hb.Blob.from_file_path(str(path))))
    return Font(
        path=path,
        units_per_em=outlines["head"].unitsPerEm,
        outlines=outlines,
        shaper=shaper,
    )


@_dataclasses.dataclass(frozen=True)
class Placed:
    """One shaped glyph, positioned in font units on a y-up baseline."""

    name: str
    x: float
    y: float


def shape(*, font: Font, text: str) -> tuple[list[Placed], float]:
    """Shape ``text``; return the placed glyphs and the total advance."""
    buffer = _hb.Buffer()
    buffer.add_str(text)
    buffer.guess_segment_properties()
    _hb.shape(font.shaper, buffer, {"kern": True, "liga": True})
    order = font.outlines.getGlyphOrder()
    placed = []
    pen_x = 0.0
    for info, position in zip(
        buffer.glyph_infos, buffer.glyph_positions, strict=True
    ):
        placed.append(
            Placed(
                name=order[info.codepoint],
                x=pen_x + position.x_offset,
                y=float(position.y_offset),
            )
        )
        pen_x += position.x_advance
    return placed, pen_x


def extent(*, font: Font, text: str) -> _geometry.Rect:
    """The ink box of ``text`` in font units, ``y`` up from the baseline.

    ``y`` is the lowest point (negative below the baseline) and ``y1`` the
    highest, so ``y1`` is the height of the ink above the baseline.
    """
    glyphs = font.outlines.getGlyphSet()
    pen = _boundspen.BoundsPen(glyphs)
    placed, _ = shape(font=font, text=text)
    for glyph in placed:
        offset = (1, 0, 0, 1, glyph.x, glyph.y)
        glyphs[glyph.name].draw(_transformpen.TransformPen(pen, offset))
    if pen.bounds is None:
        raise ValueError(f"{text!r} has no ink in {font.path.name}")
    x0, y0, x1, y1 = pen.bounds
    return _geometry.Rect(x=x0, y=y0, width=x1 - x0, height=y1 - y0)


def outline(
    *,
    font: Font,
    text: str,
    x: float,
    y: float,
    size: float,
    anchor: str,
) -> str:
    """Path data for ``text`` at ``size``, with its baseline origin at x, y.

    ``anchor`` is the SVG ``text-anchor``: ``start``, ``middle`` or ``end``.
    """
    glyphs = font.outlines.getGlyphSet()
    scale = size / font.units_per_em
    placed, advance = shape(font=font, text=text)
    shift = {"start": 0.0, "middle": -advance / 2, "end": -advance}[anchor]
    pen = _svgpathpen.SVGPathPen(
        glyphs, ntos=lambda value: _geometry.fmt_number(value=value)
    )
    for glyph in placed:
        matrix = (
            scale,
            0,
            0,
            -scale,
            x + (glyph.x + shift) * scale,
            y - glyph.y * scale,
        )
        glyphs[glyph.name].draw(_transformpen.TransformPen(pen, matrix))
    return pen.getCommands()


# ------------------------------------------------------------------------------
# Live text
# ------------------------------------------------------------------------------


def _inherited(*, element: _etree._Element, name: str) -> str | None:
    """A presentation property of ``element``, as inherited from ancestors."""
    node = element
    while node is not None and isinstance(node.tag, str):
        for declaration in (node.get("style") or "").split(";"):
            key, _, value = declaration.partition(":")
            if key.strip() == name:
                return value.strip()
        if node.get(name) is not None:
            return node.get(name)
        node = node.getparent()
    return None


def _first_coordinate(*, element: _etree._Element, name: str) -> float:
    for node in element.iter():
        raw = node.get(name) if isinstance(node.tag, str) else None
        if raw:
            return float(raw.replace(",", " ").split()[0])
    return 0.0


def outline_text(*, root: _etree._Element, font: Font) -> int:
    """Replace every live ``<text>`` with an outlined ``<path>``.

    Single-line text is supported: the content of all ``<tspan>`` children
    is set from the first ``x``/``y`` found.  The text is set in the brand
    font whatever its ``font-family`` says.  Returns the number of replaced
    elements.
    """
    texts = list(root.iter(f"{{{_document.SVG_NS}}}text"))
    for text in texts:
        content = "".join(text.itertext()).strip()
        holder = next(
            (
                node
                for node in text.iter()
                if isinstance(node.tag, str) and (node.text or "").strip()
            ),
            text,
        )
        size = _inherited(element=holder, name="font-size") or "16"
        match = _re.fullmatch(r"([0-9.]+)(px)?", size.strip())
        if match is None:
            raise ValueError(f"unsupported font-size {size!r}; use px")
        path = _etree.Element(f"{{{_document.SVG_NS}}}path")
        for key in ("id", "transform", "class"):
            if text.get(key) is not None:
                path.set(key, text.get(key))
        path.set("fill", _inherited(element=holder, name="fill") or "#000000")
        path.set("aria-label", content)
        path.set(
            "d",
            outline(
                font=font,
                text=content,
                x=_first_coordinate(element=text, name="x"),
                y=_first_coordinate(element=text, name="y"),
                size=float(match.group(1)),
                anchor=_inherited(element=holder, name="text-anchor")
                or "start",
            ),
        )
        path.tail = text.tail
        text.getparent().replace(text, path)
    return len(texts)
