# SPDX-FileCopyrightText: 2026 brandgen developers
#
# SPDX-License-Identifier: Apache-2.0

"""Composing a logo from the icon and the wordmark.

A logo is a lockup: the icon and the wordmark placed together by a fixed
rule, the ``Layout``.  Its lengths are fractions of the height of the icon's
ink, so the rule holds whatever units the sources were drawn in.

The wordmark is sized by its body, from the top of the ink to the baseline,
so descenders hang below the line as they do in text.  Ink that reaches only
slightly below the baseline, the overshoot of round letters, counts as part
of the body.

Only the horizontal arrangement exists so far.  A new arrangement is a new
``Arrangement`` member and one placement branch in ``compose``.
"""

from __future__ import annotations

import copy as _copy
import dataclasses as _dataclasses
import enum as _enum

import lxml.etree as _etree

import brandgen.document as _document
import brandgen.geometry as _geometry


class Arrangement(_enum.Enum):
    """How the icon and the wordmark sit next to each other."""

    # Icon on the left, wordmark to its right, centred on one axis.
    HORIZONTAL = "horizontal"


@_dataclasses.dataclass(frozen=True)
class Layout:
    """The lockup rule; lengths are fractions of the icon's ink height."""

    arrangement: Arrangement
    # Height of the wordmark body: top of the ink to the baseline.
    body: float
    # Space between the icon's ink and the wordmark's ink.
    gap: float


# Attributes of an <svg> root that describe the document, not its paint.
_ROOT_ONLY = frozenset(
    {
        "id",
        "version",
        "width",
        "height",
        "viewBox",
        "x",
        "y",
        "preserveAspectRatio",
        "baseProfile",
    }
)


@_dataclasses.dataclass(frozen=True)
class Part:
    """A measured source mark: document, ink box and, for text, baseline."""

    document: _document.Document
    ink: _geometry.Rect
    baseline: float


@_dataclasses.dataclass(frozen=True)
class Lockup:
    """A composed logo and its page, the frame of its ``none`` padding."""

    document: _document.Document
    page: _geometry.Rect


def _placed(
    *,
    part: Part,
    prefix: str,
    scale: float,
    dx: float,
    dy: float,
) -> _etree._Element:
    """The content of ``part`` in a group that scales, then translates."""
    root = _copy.deepcopy(part.document.root)
    _document.strip_metadata(root=root)
    _document.prefix_ids(root=root, prefix=prefix)
    group = _etree.Element(f"{{{_document.SVG_NS}}}g")
    # Presentation attributes on the source root, such as an inherited fill,
    # must keep applying to the content once it moves into a group.
    for key, value in root.attrib.items():
        if not key.startswith("{") and key not in _ROOT_ONLY:
            group.set(key, value)
    group.set("id", prefix.rstrip("-"))
    group.set(
        "transform",
        "matrix({} 0 0 {} {} {})".format(
            *(
                _geometry.fmt_number(value=value)
                for value in (scale, scale, dx, dy)
            )
        ),
    )
    for child in root:
        if isinstance(child.tag, str) and _etree.QName(child).localname in (
            "title",
            "desc",
        ):
            continue
        group.append(child)
    return group


# The most a round letter dips below the baseline, relative to the body.
OVERSHOOT = 0.05


def body(*, wordmark: Part) -> float:
    """Height of the wordmark body: ink top to baseline, or to the ink
    bottom when the ink below the baseline is only overshoot."""
    above = wordmark.baseline - wordmark.ink.y
    below = wordmark.ink.y1 - wordmark.baseline
    return above + below if below <= OVERSHOOT * above else above


def compose(*, icon: Part, wordmark: Part, layout: Layout) -> Lockup:
    """Place ``icon`` and ``wordmark`` according to ``layout``."""
    unit = icon.ink.height

    if layout.arrangement is Arrangement.HORIZONTAL:
        # The icon ink starts at the origin and sets the height of the logo.
        icon_scale, icon_dx, icon_dy = 1.0, -icon.ink.x, -icon.ink.y
        # The wordmark body, top of ink to baseline, is centred on the icon.
        scale = layout.body * unit / body(wordmark=wordmark)
        left = icon.ink.width + layout.gap * unit
        top = (unit - layout.body * unit) / 2.0
        word_dx = left - wordmark.ink.x * scale
        word_dy = top - wordmark.ink.y * scale
        frame = _geometry.Rect(
            x=0.0,
            y=0.0,
            width=left + wordmark.ink.width * scale,
            height=unit,
        )
    else:
        raise NotImplementedError(f"{layout.arrangement.value} lockup")

    # A descender may reach below the icon; the page must still contain it.
    page = frame.union(
        other=_geometry.Rect(
            x=word_dx + wordmark.ink.x * scale,
            y=word_dy + wordmark.ink.y * scale,
            width=wordmark.ink.width * scale,
            height=wordmark.ink.height * scale,
        )
    )

    root = _etree.Element(
        f"{{{_document.SVG_NS}}}svg", nsmap={None: _document.SVG_NS}
    )
    root.set("version", "1.1")
    _document.set_canvas(root=root, canvas=page)
    root.append(
        _placed(
            part=icon, prefix="icon-", scale=icon_scale, dx=icon_dx, dy=icon_dy
        )
    )
    root.append(
        _placed(
            part=wordmark,
            prefix="wordmark-",
            scale=scale,
            dx=word_dx,
            dy=word_dy,
        )
    )
    document = _document.Document(root=root, prolog=icon.document.prolog)
    return Lockup(document=document, page=page)
