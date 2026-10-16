# SPDX-FileCopyrightText: 2026 brandgen developers
#
# SPDX-License-Identifier: Apache-2.0

"""Package version, kept as one string and parsed as a semantic version."""

from __future__ import annotations

import dataclasses as _dataclasses
import re as _re

# Read by hatchling at build time, so it must stay a plain string literal.
__version__ = "2.0.0"


@_dataclasses.dataclass(frozen=True)
class Version:
    """A semantic version, ``major.minor.patch[-prerelease]``."""

    major: int
    minor: int
    patch: int
    prerelease: str | None


def parse(*, text: str) -> Version:
    """Parse ``text`` as a semantic version, or raise ``ValueError``."""
    match = _re.fullmatch(
        r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
        r"(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?",
        text,
    )
    if match is None:
        raise ValueError(f"not a semantic version: {text!r}")
    return Version(
        major=int(match.group(1)),
        minor=int(match.group(2)),
        patch=int(match.group(3)),
        prerelease=match.group(4),
    )


def version() -> Version:
    """The version of this package."""
    return parse(text=__version__)
