# SPDX-FileCopyrightText: 2026 brandgen developers
#
# SPDX-License-Identifier: Apache-2.0

"""Fixtures built from the synthetic brand in ``sample.py``."""

from __future__ import annotations

import pathlib as _pathlib

import pytest as _pytest

import sample as _sample


@_pytest.fixture
def font(tmp_path: _pathlib.Path) -> _pathlib.Path:
    return _sample.build_font(path=tmp_path / "brand.ttf")


@_pytest.fixture
def source(tmp_path: _pathlib.Path) -> _pathlib.Path:
    return _sample.write_source(directory=tmp_path / "source")
