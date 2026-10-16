# SPDX-FileCopyrightText: 2026 brandgen developers
#
# SPDX-License-Identifier: Apache-2.0

"""The source directory of a brand: icon, wordmark and brand font.

A source directory must contain ``icon.svg``, ``wordmark.svg`` and exactly
one ``*.ttf`` file.  Anything else in it, such as a hand-made ``logo.svg`` or
a palette, is ignored: the logo is composed from the icon and the wordmark.
"""

from __future__ import annotations

import dataclasses as _dataclasses
import pathlib as _pathlib


class SourceError(Exception):
    """Raised when a source directory is incomplete or ambiguous."""


@_dataclasses.dataclass(frozen=True)
class Source:
    """The files of one source directory."""

    directory: _pathlib.Path
    icon: _pathlib.Path
    wordmark: _pathlib.Path
    font: _pathlib.Path

    def files(self) -> tuple[_pathlib.Path, ...]:
        """Every file the build reads, in a stable order."""
        return (self.icon, self.wordmark, self.font)


def locate(*, directory: _pathlib.Path) -> Source:
    """Find the source files in ``directory``, or raise ``SourceError``."""
    directory = directory.expanduser().resolve()
    if not directory.is_dir():
        raise SourceError(f"{directory} is not a directory")

    missing = [
        name
        for name in ("icon.svg", "wordmark.svg")
        if not (directory / name).is_file()
    ]
    if missing:
        raise SourceError(f"{directory} has no {' or '.join(missing)}")

    fonts = sorted(directory.glob("*.ttf"))
    if not fonts:
        raise SourceError(f"{directory} has no .ttf brand font")
    if len(fonts) > 1:
        names = ", ".join(font.name for font in fonts)
        raise SourceError(f"{directory} has more than one .ttf: {names}")

    return Source(
        directory=directory,
        icon=directory / "icon.svg",
        wordmark=directory / "wordmark.svg",
        font=fonts[0],
    )
