# SPDX-FileCopyrightText: 2026 brandgen developers
#
# SPDX-License-Identifier: Apache-2.0

"""Axis-aligned rectangles in SVG user units, and number formatting."""

from __future__ import annotations

import dataclasses as _dataclasses
import math as _math


def fmt_number(*, value: float) -> str:
    """Format a coordinate compactly and deterministically."""
    if not _math.isfinite(value):
        raise ValueError(f"non-finite coordinate: {value!r}")
    rounded = round(value, 6)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.6f}".rstrip("0").rstrip(".")


@_dataclasses.dataclass(frozen=True)
class Rect:
    """A rectangle with ``y`` growing downwards, as in SVG."""

    x: float
    y: float
    width: float
    height: float

    @property
    def x1(self) -> float:
        return self.x + self.width

    @property
    def y1(self) -> float:
        return self.y + self.height

    def union(self, *, other: Rect) -> Rect:
        x0 = min(self.x, other.x)
        y0 = min(self.y, other.y)
        x1 = max(self.x1, other.x1)
        y1 = max(self.y1, other.y1)
        return Rect(x=x0, y=y0, width=x1 - x0, height=y1 - y0)

    def viewbox(self) -> str:
        """The rectangle as the value of an SVG ``viewBox`` attribute."""
        values = (self.x, self.y, self.width, self.height)
        return " ".join(fmt_number(value=value) for value in values)
