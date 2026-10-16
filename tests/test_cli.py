# SPDX-FileCopyrightText: 2026 brandgen developers
#
# SPDX-License-Identifier: Apache-2.0

import pathlib as _pathlib

import pytest as _pytest

import brandgen.cli as _cli


def test_build_takes_input_and_output_options(
    source: _pathlib.Path, tmp_path: _pathlib.Path
) -> None:
    output = tmp_path / "out"
    status = _cli.execute(
        argv=[
            "build",
            "--input",
            str(source),
            "--output",
            str(output),
            "--name",
            "brand",
            "--format",
            "svg",
            "--quiet",
        ]
    )
    assert status == 0
    assert (output / "manifest.json").is_file()


def test_build_requires_input_and_output() -> None:
    with _pytest.raises(SystemExit):
        _cli.execute(argv=["build", "--name", "brand"])
