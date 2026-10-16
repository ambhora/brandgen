# SPDX-FileCopyrightText: 2026 brandgen developers
#
# SPDX-License-Identifier: Apache-2.0

"""The variant matrix: marks, colourways, backgrounds, paddings, formats."""

from __future__ import annotations

import dataclasses as _dataclasses
import enum as _enum

import brandgen.geometry as _geometry


class Mark(_enum.Enum):
    """The marks a brand ships."""

    ICON = "icon"
    WORDMARK = "wordmark"
    LOGO_HORIZONTAL = "logo-horizontal"


class Colorway(_enum.Enum):
    """The ink of the mark."""

    COLOR = "color"
    WHITE = "white"
    BLACK = "black"

    @property
    def ink(self) -> str | None:
        """The single ink colour, or ``None`` to keep the brand colours."""
        return {
            Colorway.COLOR: None,
            Colorway.WHITE: "#ffffff",
            Colorway.BLACK: "#000000",
        }[self]


class Background(_enum.Enum):
    """The canvas behind the mark."""

    TRANSPARENT = "transparent"
    WHITE = "white"
    BLACK = "black"

    @property
    def fill(self) -> str | None:
        """The plate colour, or ``None`` for no plate."""
        return {
            Background.TRANSPARENT: None,
            Background.WHITE: "#ffffff",
            Background.BLACK: "#000000",
        }[self]


class Padding(_enum.Enum):
    """Clear space around the mark, as a fraction of its ink height."""

    NONE = "none"
    TIGHT = "tight"
    CLEARSPACE = "clearspace"
    GENEROUS = "generous"
    AVATAR = "avatar"

    @property
    def ratio(self) -> float:
        return {
            Padding.NONE: 0.0,
            Padding.TIGHT: 0.10,
            Padding.CLEARSPACE: 0.25,
            Padding.GENEROUS: 0.50,
            Padding.AVATAR: 0.10,
        }[self]

    @property
    def description(self) -> str:
        return {
            Padding.NONE: "the source page, no clear space added",
            Padding.TIGHT: "10% of mark height, app icon and favicon",
            Padding.CLEARSPACE: "25% of mark height, minimum exclusion zone",
            Padding.GENEROUS: "50% of mark height, covers and title slides",
            Padding.AVATAR: "10% of mark height on a square, profile images",
        }[self]

    def applies_to(self, *, mark: Mark) -> bool:
        """Squaring a wide mark leaves mostly empty canvas, so avatars are
        made for the icon only."""
        return self is not Padding.AVATAR or mark is Mark.ICON

    def canvas(
        self, *, ink: _geometry.Rect, page: _geometry.Rect
    ) -> _geometry.Rect:
        """The canvas for a mark with this ink box and source page."""
        if self is Padding.NONE:
            return page
        pad = self.ratio * ink.height
        width = ink.width + 2.0 * pad
        height = ink.height + 2.0 * pad
        side_x = max(width, height) if self is Padding.AVATAR else width
        side_y = max(width, height) if self is Padding.AVATAR else height
        return _geometry.Rect(
            x=ink.x - pad - (side_x - width) / 2.0,
            y=ink.y - pad - (side_y - height) / 2.0,
            width=side_x,
            height=side_y,
        )


class Format(_enum.Enum):
    SVG = "svg"
    PNG = "png"
    PDF = "pdf"


def legible(*, colorway: Colorway, background: Background) -> bool:
    """False where the mark would vanish into its background."""
    return (colorway, background) not in (
        (Colorway.BLACK, Background.BLACK),
        (Colorway.WHITE, Background.WHITE),
    )


@_dataclasses.dataclass(frozen=True)
class Variant:
    """One output file."""

    name: str
    mark: Mark
    colorway: Colorway
    background: Background
    padding: Padding
    format: Format
    # Raster width in pixels; PNG only.
    width: int | None

    @property
    def stem(self) -> str:
        parts = [
            self.name,
            self.mark.value,
            self.colorway.value,
            "on",
            self.background.value,
            self.padding.value,
        ]
        if self.width is not None:
            parts.append(f"{self.width}px")
        return "-".join(parts)

    @property
    def relpath(self) -> str:
        filename = f"{self.stem}.{self.format.value}"
        return f"{self.mark.value}/{self.format.value}/{filename}"

    @property
    def key(self) -> tuple[Mark, Colorway, Background, Padding]:
        """Variants with equal keys share one derived SVG."""
        return (self.mark, self.colorway, self.background, self.padding)


def plan(
    *,
    name: str,
    marks: tuple[Mark, ...],
    colorways: tuple[Colorway, ...],
    backgrounds: tuple[Background, ...],
    paddings: tuple[Padding, ...],
    formats: tuple[Format, ...],
    png_widths: tuple[int, ...],
) -> list[Variant]:
    """Every output file, in a stable order, without illegible pairings."""
    variants = []
    for mark in marks:
        for colorway in colorways:
            for background in backgrounds:
                if not legible(colorway=colorway, background=background):
                    continue
                for padding in paddings:
                    if not padding.applies_to(mark=mark):
                        continue
                    for fmt in formats:
                        widths = png_widths if fmt is Format.PNG else (None,)
                        for width in widths:
                            variants.append(
                                Variant(
                                    name=name,
                                    mark=mark,
                                    colorway=colorway,
                                    background=background,
                                    padding=padding,
                                    format=fmt,
                                    width=width,
                                )
                            )
    return variants
