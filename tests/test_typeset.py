# SPDX-FileCopyrightText: 2026 brandgen developers
#
# SPDX-License-Identifier: Apache-2.0

import pathlib as _pathlib

import lxml.etree as _etree
import pytest as _pytest

import brandgen.measure as _measure
import brandgen.typeset as _typeset


def _svg(*, body: str) -> _etree._Element:
    return _etree.fromstring(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2000 1000">'
        f"{body}</svg>"
    )


def test_extent_is_measured_from_the_baseline(font: _pathlib.Path) -> None:
    box = _typeset.extent(font=_typeset.load(path=font), text="Hg")
    assert (box.y, box.y1) == (-200, 700)
    assert (box.x, box.x1) == (100, 1100)


def test_live_text_becomes_a_labelled_path(font: _pathlib.Path) -> None:
    root = _svg(
        body='<text id="t" x="0" y="800" fill="#123456"'
        ' style="font-size:100px"><tspan>Hg</tspan></text>'
    )
    assert _typeset.outline_text(root=root, font=_typeset.load(path=font)) == 1
    (path,) = root
    assert _etree.QName(path).localname == "path"
    assert path.get("aria-label") == "Hg"
    assert path.get("fill") == "#123456"
    box = _measure.ink(root=root)
    assert box.y == _pytest.approx(800 - 70)
    assert box.y1 == _pytest.approx(800 + 20)
    assert box.x == _pytest.approx(10)


def test_baseline_is_recovered_from_the_label(font: _pathlib.Path) -> None:
    loaded = _typeset.load(path=font)
    root = _svg(body='<text x="0" y="800" style="font-size:1000px">Hg</text>')
    _typeset.outline_text(root=root, font=loaded)
    box = _measure.ink(root=root)
    found = _measure.baseline(root=root, box=box, font=loaded)
    assert found.warning is None
    assert found.text == "Hg"
    assert found.y == _pytest.approx(800)


def test_baseline_without_a_label_warns(font: _pathlib.Path) -> None:
    root = _svg(body='<rect x="0" y="100" width="50" height="300"/>')
    box = _measure.ink(root=root)
    found = _measure.baseline(root=root, box=box, font=_typeset.load(path=font))
    assert found.warning is not None
    assert found.y == _pytest.approx(400)
