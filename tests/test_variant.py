# SPDX-FileCopyrightText: 2026 brandgen developers
#
# SPDX-License-Identifier: Apache-2.0

import brandgen.geometry as _geometry
import brandgen.variant as _variant


def _plan(*, formats: tuple[_variant.Format, ...]) -> list[_variant.Variant]:
    return _variant.plan(
        name="brand",
        marks=tuple(_variant.Mark),
        colorways=tuple(_variant.Colorway),
        backgrounds=tuple(_variant.Background),
        paddings=tuple(_variant.Padding),
        formats=formats,
        png_widths=(256, 512),
    )


def test_illegible_pairings_are_dropped() -> None:
    pairs = {
        (item.colorway, item.background)
        for item in _plan(formats=(_variant.Format.SVG,))
    }
    assert len(pairs) == 7
    assert (_variant.Colorway.WHITE, _variant.Background.WHITE) not in pairs
    assert (_variant.Colorway.BLACK, _variant.Background.BLACK) not in pairs


def test_avatar_is_for_the_icon_only() -> None:
    marks = {
        item.mark
        for item in _plan(formats=(_variant.Format.SVG,))
        if item.padding is _variant.Padding.AVATAR
    }
    assert marks == {_variant.Mark.ICON}


def test_every_format_and_width_is_planned() -> None:
    variants = _plan(formats=tuple(_variant.Format))
    # icon: 5 paddings, wordmark and logo: 4; 7 pairings; svg, pdf, 2 pngs.
    assert len(variants) == (5 + 4 + 4) * 7 * 4
    assert len({item.relpath for item in variants}) == len(variants)


def test_names_describe_the_variant() -> None:
    item = _variant.Variant(
        name="kprof",
        mark=_variant.Mark.LOGO_HORIZONTAL,
        colorway=_variant.Colorway.WHITE,
        background=_variant.Background.BLACK,
        padding=_variant.Padding.CLEARSPACE,
        format=_variant.Format.PNG,
        width=512,
    )
    assert item.relpath == (
        "logo-horizontal/png/"
        "kprof-logo-horizontal-white-on-black-clearspace-512px.png"
    )


def test_padding_grows_the_canvas_around_the_ink() -> None:
    ink = _geometry.Rect(x=10, y=20, width=400, height=100)
    page = _geometry.Rect(x=0, y=0, width=500, height=200)
    assert _variant.Padding.NONE.canvas(ink=ink, page=page) == page
    assert _variant.Padding.CLEARSPACE.canvas(
        ink=ink, page=page
    ) == _geometry.Rect(x=-15, y=-5, width=450, height=150)
    square = _variant.Padding.AVATAR.canvas(ink=ink, page=page)
    assert square.width == square.height == 420
