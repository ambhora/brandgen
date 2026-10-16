# SPDX-FileCopyrightText: 2026 brandgen developers
#
# SPDX-License-Identifier: Apache-2.0

import pathlib as _pathlib

import pytest as _pytest

import brandgen.metadata as _metadata
import brandgen.source as _source


def test_extra_files_are_ignored(source: _pathlib.Path) -> None:
    found = _source.locate(directory=source)
    assert [path.name for path in found.files()] == [
        "icon.svg",
        "wordmark.svg",
        "brand.ttf",
    ]


def test_a_missing_font_is_reported(source: _pathlib.Path) -> None:
    (source / "brand.ttf").unlink()
    with _pytest.raises(_source.SourceError, match="no .ttf"):
        _source.locate(directory=source)


def test_two_fonts_are_ambiguous(source: _pathlib.Path) -> None:
    (source / "other.ttf").write_bytes((source / "brand.ttf").read_bytes())
    with _pytest.raises(_source.SourceError, match="more than one"):
        _source.locate(directory=source)


def test_the_version_is_semantic() -> None:
    version = _metadata.version()
    assert _metadata.parse(text="1.2.3-rc.1").prerelease == "rc.1"
    assert version.major >= 2
