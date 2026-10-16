# SPDX-FileCopyrightText: 2026 brandgen developers
#
# SPDX-License-Identifier: Apache-2.0

"""Measuring marks: the ink box, and the baseline of a wordmark.

Padding is measured from the ink, not from the page, and the logo layout
aligns the wordmark by its baseline, so both are needed before any variant
can be built.  The ink box is exact for paths and basic shapes; live text
must be outlined first, see ``brandgen.typeset.outline_text``.
"""

from __future__ import annotations

import dataclasses as _dataclasses
import io as _io

import lxml.etree as _etree
import svgelements as _svgelements

import brandgen.geometry as _geometry
import brandgen.typeset as _typeset


def ink(*, root: _etree._Element) -> _geometry.Rect:
    """The box around everything painted in the document."""
    parsed = _svgelements.SVG.parse(_io.BytesIO(_etree.tostring(root)))
    box: _geometry.Rect | None = None
    for element in parsed.elements():
        if not isinstance(element, _svgelements.Shape):
            continue
        if isinstance(element, _svgelements.SVG):
            continue
        bounds = element.bbox()
        if bounds is None:
            continue
        x0, y0, x1, y1 = (float(value) for value in bounds)
        found = _geometry.Rect(x=x0, y=y0, width=x1 - x0, height=y1 - y0)
        box = found if box is None else box.union(other=found)
    if box is None:
        raise ValueError("the document paints nothing")
    return box


@_dataclasses.dataclass(frozen=True)
class Baseline:
    """Where the baseline of a wordmark lies, and how it was found."""

    y: float
    text: str | None
    warning: str | None


def baseline(
    *, root: _etree._Element, box: _geometry.Rect, font: _typeset.Font
) -> Baseline:
    """Locate the baseline of the wordmark whose ink box is ``box``.

    The wordmark text is read from an ``aria-label``, which Inkscape and
    this package both write when outlining text.  Shaping that text in the
    brand font gives the share of the ink that lies above the baseline.
    Without a label, or when the shaped text does not match the outlines,
    the bottom of the ink is used and a warning is returned.
    """
    labels = [
        element.get("aria-label")
        for element in root.iter()
        if isinstance(element.tag, str) and element.get("aria-label")
    ]
    if not labels:
        return Baseline(
            y=box.y1,
            text=None,
            warning="wordmark has no aria-label; "
            "aligning on the bottom of the ink instead of the baseline",
        )

    text = " ".join(labels)
    shaped = _typeset.extent(font=font, text=text)
    scale = box.height / shaped.height
    mismatch = abs(shaped.width * scale - box.width) / box.width
    if mismatch > 0.02:
        return Baseline(
            y=box.y1,
            text=text,
            warning=f"{text!r} set in the brand font does not match the "
            f"wordmark outlines ({mismatch:.1%} off in width); "
            "aligning on the bottom of the ink instead of the baseline",
        )
    return Baseline(y=box.y + shaped.y1 * scale, text=text, warning=None)
