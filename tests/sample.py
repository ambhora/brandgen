# SPDX-FileCopyrightText: 2026 brandgen developers
#
# SPDX-License-Identifier: Apache-2.0

"""A synthetic brand: a test font and a source directory.

Used by the test fixtures and, as a script, by CI to build a source
directory for an end-to-end run of the installed command line:

    python tests/sample.py <directory>

Every glyph of the test font is a rectangle with known extents in a
1000-unit em, which makes expected geometry easy to compute by hand:

``H``  x 100..500, y 0..700      cap height 700, flat on the baseline
``o``  x 100..500, y -10..510    round letter, overshoots by 10
``g``  x 100..500, y -200..500   descender of 200
"""

from __future__ import annotations

import pathlib as _pathlib
import sys as _sys

import fontTools.fontBuilder as _fontbuilder
import fontTools.pens.ttGlyphPen as _ttglyphpen

GLYPHS = {"H": (0, 700), "o": (-10, 510), "g": (-200, 500)}


def _rectangle(*, bottom: int, top: int):
    pen = _ttglyphpen.TTGlyphPen(None)
    pen.moveTo((100, bottom))
    pen.lineTo((100, top))
    pen.lineTo((500, top))
    pen.lineTo((500, bottom))
    pen.closePath()
    return pen.glyph()


def build_font(*, path: _pathlib.Path) -> _pathlib.Path:
    names = [".notdef", "space", *GLYPHS]
    builder = _fontbuilder.FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder(names)
    builder.setupCharacterMap(
        {ord(" "): "space", **{ord(name): name for name in GLYPHS}}
    )
    glyphs = {
        ".notdef": _rectangle(bottom=0, top=700),
        "space": _ttglyphpen.TTGlyphPen(None).glyph(),
        **{
            name: _rectangle(bottom=bottom, top=top)
            for name, (bottom, top) in GLYPHS.items()
        },
    }
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics({name: (600, 100) for name in names})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable({"familyName": "Test", "styleName": "Regular"})
    builder.setupOS2()
    builder.setupPost()
    builder.save(str(path))
    return path


# A licence header that the build must carry into derived files.
# REUSE-IgnoreStart
ICON = """<?xml version="1.0" encoding="UTF-8"?>
<!-- SPDX-License-Identifier: CC0-1.0 -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240">
  <metadata>source only</metadata>
  <rect id="body" x="20" y="20" width="200" height="200" fill="#2971b7"/>
  <circle id="dial" cx="120" cy="120" r="60" fill="#ac495c"/>
</svg>
"""
# REUSE-IgnoreEnd

WORDMARK = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1300 1000">
  <text x="0" y="800" style="font-size:1000px;fill:#2971b7">Hg</text>
</svg>
"""


def write_source(*, directory: _pathlib.Path) -> _pathlib.Path:
    """Write a complete source directory, with the extra files real ones
    carry and the build ignores."""
    directory.mkdir(parents=True, exist_ok=True)
    build_font(path=directory / "brand.ttf")
    (directory / "icon.svg").write_text(ICON)
    (directory / "wordmark.svg").write_text(WORDMARK)
    (directory / "logo.svg").write_text("not read")
    (directory / "palette.json").write_text("{}")
    return directory


if __name__ == "__main__":
    write_source(directory=_pathlib.Path(_sys.argv[1]))
