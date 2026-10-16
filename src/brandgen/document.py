# SPDX-FileCopyrightText: 2026 brandgen developers
#
# SPDX-License-Identifier: Apache-2.0

"""SVG documents: reading, tree surgery and serialisation.

Source files are opened read-only.  Every variant is built from a deep copy,
so the parsed source is never changed either.  Comments in front of the root
element, such as an SPDX header, travel with the document into every
derived SVG.
"""

from __future__ import annotations

import copy as _copy
import dataclasses as _dataclasses
import pathlib as _pathlib
import re as _re

import lxml.etree as _etree

import brandgen.geometry as _geometry

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"
SODIPODI_NS = "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"


@_dataclasses.dataclass(frozen=True)
class Document:
    """An SVG root element and the comments in front of it."""

    root: _etree._Element
    prolog: tuple[str, ...]


def read(*, path: _pathlib.Path) -> Document:
    """Parse the SVG at ``path``."""
    parser = _etree.XMLParser(remove_blank_text=False, resolve_entities=False)
    with path.open("rb") as handle:
        tree = _etree.parse(handle, parser)
    root = tree.getroot()
    prolog = [
        node.text
        for node in root.itersiblings(preceding=True)
        if isinstance(node, _etree._Comment)
    ]
    return Document(root=root, prolog=tuple(reversed(prolog)))


def clone(*, document: Document) -> Document:
    """A deep copy that can be changed without touching ``document``."""
    return Document(root=_copy.deepcopy(document.root), prolog=document.prolog)


def serialize(*, document: Document) -> bytes:
    """The document as UTF-8 bytes, prolog comments included."""
    head = b'<?xml version="1.0" encoding="UTF-8"?>\n'
    for text in document.prolog:
        head += f"<!--{text}-->\n".encode()
    return head + _etree.tostring(document.root, encoding="UTF-8") + b"\n"


# ------------------------------------------------------------------------------
# Geometry of the page
# ------------------------------------------------------------------------------


def page(*, root: _etree._Element) -> _geometry.Rect:
    """The document page: the ``viewBox``, else ``width`` by ``height``."""
    viewbox = root.get("viewBox")
    if viewbox:
        parts = viewbox.replace(",", " ").split()
        if len(parts) == 4:
            x, y, width, height = (float(part) for part in parts)
            return _geometry.Rect(x=x, y=y, width=width, height=height)
    return _geometry.Rect(
        x=0.0,
        y=0.0,
        width=_length(raw=root.get("width")),
        height=_length(raw=root.get("height")),
    )


def _length(*, raw: str | None) -> float:
    if not raw:
        raise ValueError("the SVG root has neither a viewBox nor a size")
    return float(_re.sub(r"[a-z%]+$", "", raw.strip()))


def set_canvas(*, root: _etree._Element, canvas: _geometry.Rect) -> None:
    """Point the document window at ``canvas``; the artwork does not move."""
    root.set("width", _geometry.fmt_number(value=canvas.width))
    root.set("height", _geometry.fmt_number(value=canvas.height))
    root.set("viewBox", canvas.viewbox())


def add_background(
    *, root: _etree._Element, canvas: _geometry.Rect, fill: str
) -> None:
    """Insert an opaque plate covering ``canvas`` behind the artwork."""
    plate = _etree.Element(f"{{{SVG_NS}}}rect")
    plate.set("id", "background-plate")
    plate.set("x", _geometry.fmt_number(value=canvas.x))
    plate.set("y", _geometry.fmt_number(value=canvas.y))
    plate.set("width", _geometry.fmt_number(value=canvas.width))
    plate.set("height", _geometry.fmt_number(value=canvas.height))
    plate.set("fill", fill)
    root.insert(0, plate)


# ------------------------------------------------------------------------------
# Paint
# ------------------------------------------------------------------------------

PAINT_PROPERTIES = ("fill", "stroke", "stop-color", "flood-color", "color")
KEPT_PAINTS = frozenset({"none", "transparent", "inherit", "currentcolor"})


def _repaintable(*, value: str) -> bool:
    value = value.strip().lower()
    return bool(value) and value not in KEPT_PAINTS and "url(" not in value


def recolor(*, root: _etree._Element, ink: str) -> None:
    """Rewrite every paint in the tree to the single colour ``ink``."""
    # Unpainted shapes inherit black; give them the ink as well.
    if root.get("fill") is None:
        root.set("fill", ink)
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        for name in PAINT_PROPERTIES:
            value = element.get(name)
            if value is not None and _repaintable(value=value):
                element.set(name, ink)
        style = element.get("style")
        if not style:
            continue
        declarations = []
        for declaration in style.split(";"):
            key, separator, value = declaration.partition(":")
            if not key.strip():
                continue
            if (
                separator
                and key.strip() in PAINT_PROPERTIES
                and _repaintable(value=value)
            ):
                declarations.append(f"{key.strip()}:{ink}")
            else:
                declarations.append(declaration.strip())
        element.set("style", ";".join(declarations))


# ------------------------------------------------------------------------------
# Clean-up and merging
# ------------------------------------------------------------------------------


def strip_metadata(*, root: _etree._Element) -> None:
    """Drop editor bookkeeping and embedded metadata.

    Inkscape and Sodipodi elements and attributes only matter to an editor,
    and a ``<metadata>`` block, such as a content credential, describes the
    source file and is no longer true for a derived one.
    """
    for element in list(root.iter()):
        if not isinstance(element.tag, str):
            continue
        name = _etree.QName(element)
        drop = name.namespace in (INKSCAPE_NS, SODIPODI_NS) or (
            name.namespace == SVG_NS and name.localname == "metadata"
        )
        if drop:
            parent = element.getparent()
            if parent is not None:
                parent.remove(element)
            continue
        for key in list(element.attrib):
            if key.startswith((f"{{{INKSCAPE_NS}}}", f"{{{SODIPODI_NS}}}")):
                del element.attrib[key]
    _etree.cleanup_namespaces(root)


def prefix_ids(*, root: _etree._Element, prefix: str) -> None:
    """Prefix every id, and every reference to one, with ``prefix``.

    Two documents merged into one must not share an id, so each part of a
    composed logo gets its own prefix.
    """
    ids = {
        element.get("id")
        for element in root.iter()
        if isinstance(element.tag, str) and element.get("id")
    }
    if not ids:
        return

    def rename(match: _re.Match[str]) -> str:
        name = match.group(2)
        return match.group(1) + (prefix + name if name in ids else name)

    pattern = _re.compile(r"(url\(\s*#|^#)([^)\s]+)")
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        for key, value in element.attrib.items():
            if key == "id":
                element.set(key, prefix + value)
            elif "#" in value:
                element.set(key, pattern.sub(rename, value))
