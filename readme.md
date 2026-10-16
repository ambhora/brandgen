<!--
SPDX-FileCopyrightText: 2026 brandgen developers

SPDX-License-Identifier: Apache-2.0
-->

# brandgen

Generates every distribution variant of a brand's marks from a source
directory. The brand assets live with the brand; this package only holds the
code.

```
uv run brandgen build --input path/to/source --output path/to/generated \
    --name kprof
```

## Input

The `--input` directory must contain:

| File | Purpose |
|------|---------|
| `icon.svg` | The icon. |
| `wordmark.svg` | The wordmark, outlined or as live text. |
| exactly one `*.ttf` | The brand font. |

Anything else in the directory, such as a hand-made `logo.svg` or a palette,
is ignored. The logo is composed from the icon and the wordmark.

The font is used for two things. Live `<text>` in either SVG is converted to
outlines with it, so no renderer needs the font installed. And it locates the
wordmark's baseline: the wordmark text, read from its `aria-label` (Inkscape
writes one when converting text to paths), is set in the font and matched to
the outlines. Without a label the bottom of the ink is used and the build
says so.

## The logo

The logo is the mark `logo-horizontal`: the icon on the left and the
wordmark to its right. All lengths are fractions of the icon's ink height:

| Option | Default | Meaning |
|--------|---------|---------|
| `--body` | `0.625` | Height of the wordmark from the top of its ink to the baseline. |
| `--gap` | `0.2205625` | Space between the icon's ink and the wordmark's ink. |

The wordmark body is centred vertically on the icon, and descenders hang
below it as in running text. Ink that reaches only slightly below the
baseline, the overshoot of round letters, counts as part of the body.

The defaults reproduce the Ambhora logo. The kprof logo uses
`--gap 0.359375`.

Only the horizontal arrangement exists. A vertical one is a new
`brandgen.lockup.Arrangement` member and one placement branch in
`brandgen.lockup.compose`; its mark would be `logo-vertical`.

## Output

Every mark in every legible colourway, background, padding and format:

| | transparent | white | black |
|-|:-:|:-:|:-:|
| **color** | yes | yes | yes |
| **white** | yes | | yes |
| **black** | yes | yes | |

| Padding | Clear space | Marks |
|---------|-------------|-------|
| `none` | the source page; for the logo, the composed page | all |
| `tight` | 10% of ink height | all |
| `clearspace` | 25% of ink height | all |
| `generous` | 50% of ink height | all |
| `avatar` | 10% of ink height, on a square | icon |

Formats are SVG, PDF (200 mm wide unless `--pdf-width-mm` says otherwise)
and PNG at 256, 512 and 1024 pixels (`--png-width`, repeatable). Padding
widens the canvas around the ink; the artwork itself is never moved.

Files are laid out as

```
<output>/<mark>/<format>/<name>-<mark>-<colorway>-on-<background>-<padding>[-<width>px].<ext>
```

and `<output>/manifest.json` lists every file with its size, SHA-256 and
canvas, together with the checksums of the three source files and the
layout used. SVG and PNG output is byte-for-byte reproducible; PDFs differ
between runs only in the creation date cairo writes into them.

Derived SVGs keep the comments in front of the source's root element, such
as an SPDX header, and drop editor metadata and `<metadata>` blocks.

`--mark`, `--colorway`, `--background`, `--padding` and `--format` narrow the
matrix; each is repeatable. `brandgen plan --name <name>` lists the files a
build would write, and `brandgen paddings` explains the padding rules.

## Development

```
uv sync
uv run pytest
uv run ruff check
uv run ruff format --check
```

The tests build their own font and marks, so the repository holds no brand
assets.

## Layout

```
src/brandgen/
  source.py     locating icon, wordmark and font
  document.py   reading, recolouring, recanvassing and writing SVG
  typeset.py    shaping with the brand font, outlining live text
  measure.py    ink boxes and the wordmark baseline
  lockup.py     composing the logo
  variant.py    the variant matrix and file naming
  render.py     PNG and PDF through cairosvg
  build.py      running a build and writing the manifest
  cli.py        command line interface
  metadata.py   version
```
