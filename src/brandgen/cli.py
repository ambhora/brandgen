# SPDX-FileCopyrightText: 2026 brandgen developers
#
# SPDX-License-Identifier: Apache-2.0

"""Command line interface."""

from __future__ import annotations

import argparse as _argparse
import enum as _enum
import pathlib as _pathlib
import sys as _sys

import brandgen.build as _build
import brandgen.lockup as _lockup
import brandgen.metadata as _metadata
import brandgen.render as _render
import brandgen.source as _source
import brandgen.variant as _variant


def _members(
    *, values: list[str] | None, kind: type[_enum.Enum]
) -> tuple[_enum.Enum, ...]:
    if not values:
        return tuple(kind)
    return tuple(kind(value) for value in dict.fromkeys(values))


def _add_matrix(*, parser: _argparse.ArgumentParser) -> None:
    """Options that narrow the variant matrix; all default to everything."""
    parser.add_argument("--name", required=True, help="brand name in filenames")
    for option, kind in (
        ("--mark", _variant.Mark),
        ("--colorway", _variant.Colorway),
        ("--background", _variant.Background),
        ("--padding", _variant.Padding),
        ("--format", _variant.Format),
    ):
        parser.add_argument(
            option,
            action="append",
            choices=[member.value for member in kind],
            help="repeatable; default: all",
        )
    parser.add_argument(
        "--gap",
        type=float,
        default=0.2205625,
        help="logo: space between icon and wordmark as a fraction of the "
        "icon height; default: %(default)s",
    )
    parser.add_argument(
        "--body",
        type=float,
        default=0.625,
        help="logo: height of the wordmark from its top to its baseline as "
        "a fraction of the icon height; default: %(default)s",
    )
    parser.add_argument(
        "--png-width",
        action="append",
        type=int,
        help="PNG width in pixels, repeatable; default: 256 512 1024",
    )


def parser() -> _argparse.ArgumentParser:
    root = _argparse.ArgumentParser(
        prog="brandgen",
        description="Generate every distribution variant of a brand's marks "
        "from a source directory holding icon.svg, wordmark.svg and the "
        "brand font as a .ttf.",
    )
    root.add_argument(
        "--version", action="version", version=_metadata.__version__
    )
    commands = root.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build", help="write every variant")
    build.add_argument(
        "--input",
        type=_pathlib.Path,
        required=True,
        help="source directory with icon.svg, wordmark.svg and a .ttf",
    )
    build.add_argument(
        "--output",
        type=_pathlib.Path,
        required=True,
        help="directory to write the variants and manifest.json to",
    )
    _add_matrix(parser=build)
    build.add_argument(
        "--pdf-width-mm",
        type=float,
        default=200.0,
        help="page width of PDF output; default: %(default)s",
    )
    build.add_argument("--jobs", type=int, default=4, help="parallel workers")
    build.add_argument(
        "--quiet", action="store_true", help="only report problems"
    )

    plan = commands.add_parser("plan", help="list the files a build writes")
    _add_matrix(parser=plan)

    commands.add_parser("paddings", help="explain the padding rules")
    return root


def _config(*, args: _argparse.Namespace) -> _build.Config:
    return _build.Config(
        source=getattr(args, "input", _pathlib.Path(".")),
        output=getattr(args, "output", _pathlib.Path(".")),
        name=args.name,
        marks=_members(values=args.mark, kind=_variant.Mark),
        colorways=_members(values=args.colorway, kind=_variant.Colorway),
        backgrounds=_members(values=args.background, kind=_variant.Background),
        paddings=_members(values=args.padding, kind=_variant.Padding),
        formats=_members(values=args.format, kind=_variant.Format),
        png_widths=tuple(args.png_width or (256, 512, 1024)),
        pdf_width_mm=getattr(args, "pdf_width_mm", 200.0),
        layout=_lockup.Layout(
            arrangement=_lockup.Arrangement.HORIZONTAL,
            body=args.body,
            gap=args.gap,
        ),
        jobs=getattr(args, "jobs", 1),
    )


def execute(*, argv: list[str]) -> int:
    """Run the command line ``argv``; return the exit status."""
    args = parser().parse_args(argv)

    if args.command == "paddings":
        for padding in _variant.Padding:
            print(f"{padding.value:<11} {padding.description}")
        return 0

    config = _config(args=args)
    if args.command == "plan":
        variants = config.plan()
        for item in variants:
            print(item.relpath)
        print(f"{len(variants)} files", file=_sys.stderr)
        return 0

    try:
        result = _build.run(
            config=config,
            progress=None if args.quiet else lambda path: print(path),
        )
    except (_source.SourceError, _render.RenderError, ValueError) as error:
        print(f"error: {error}", file=_sys.stderr)
        return 1
    for warning in result.warnings:
        print(f"note: {warning}", file=_sys.stderr)
    if not args.quiet:
        print(f"wrote {len(result.written)} files, listed in {result.manifest}")
    return 0


def main() -> int:
    """Entry point of the ``brandgen`` console script."""
    return execute(argv=_sys.argv[1:])
