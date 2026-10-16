# SPDX-FileCopyrightText: 2026 brandgen developers
#
# SPDX-License-Identifier: Apache-2.0

import copy as _copy
import pathlib as _pathlib

import lxml.etree as _etree
import pytest as _pytest

import brandgen.build as _build
import brandgen.document as _document
import brandgen.geometry as _geometry
import brandgen.lockup as _lockup
import brandgen.measure as _measure
import brandgen.source as _source
import brandgen.variant as _variant

LAYOUT = _lockup.Layout(
    arrangement=_lockup.Arrangement.HORIZONTAL, body=0.625, gap=0.25
)


def _wordmark(*, top: float, baseline: float, bottom: float) -> _lockup.Part:
    root = _etree.Element(f"{{{_document.SVG_NS}}}svg")
    return _lockup.Part(
        document=_document.Document(root=root, prolog=()),
        ink=_geometry.Rect(x=0, y=top, width=100, height=bottom - top),
        baseline=baseline,
    )


def _ink_of(*, group: _etree._Element) -> _geometry.Rect:
    root = _etree.Element(
        f"{{{_document.SVG_NS}}}svg", nsmap={None: _document.SVG_NS}
    )
    root.append(_copy.deepcopy(group))
    return _measure.ink(root=root)


def test_descender_hangs_below_the_body() -> None:
    part = _wordmark(top=0, baseline=700, bottom=900)
    assert _lockup.body(wordmark=part) == 700


def test_overshoot_counts_as_body() -> None:
    part = _wordmark(top=0, baseline=700, bottom=710)
    assert _lockup.body(wordmark=part) == 710


def test_horizontal_lockup_follows_the_layout(source: _pathlib.Path) -> None:
    marks = _build.prepare(
        source=_source.locate(directory=source), layout=LAYOUT
    )
    logo = marks.marks[_variant.Mark.LOGO_HORIZONTAL]
    icon, wordmark = logo.document.root
    assert (icon.get("id"), wordmark.get("id")) == ("icon", "wordmark")

    # The icon ink is 200 high and starts at the origin of the logo.
    assert _ink_of(group=icon) == _geometry.Rect(
        x=0, y=0, width=200, height=200
    )
    assert logo.page.height == _pytest.approx(200)

    word = _ink_of(group=wordmark)
    # The body of "Hg" is the H: 0.625 x 200 = 125 high, centred.
    assert word.y == _pytest.approx(37.5, abs=1e-3)
    # The g hangs 200/700 of the body below the baseline.
    assert word.y1 == _pytest.approx(162.5 + 125 * 200 / 700, abs=1e-3)
    # A gap of 0.25 x 200 after the 200-wide icon.
    assert word.x == _pytest.approx(250, abs=1e-3)
    assert logo.page.width == _pytest.approx(word.x1, abs=1e-3)


def test_parts_keep_distinct_ids(source: _pathlib.Path) -> None:
    marks = _build.prepare(
        source=_source.locate(directory=source), layout=LAYOUT
    )
    root = marks.marks[_variant.Mark.LOGO_HORIZONTAL].document.root
    ids = [
        element.get("id")
        for element in root.iter()
        if isinstance(element.tag, str) and element.get("id")
    ]
    assert len(ids) == len(set(ids))
    assert "icon-body" in ids
