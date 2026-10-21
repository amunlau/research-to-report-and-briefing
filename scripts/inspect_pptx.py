#!/usr/bin/env python3
"""Read-only PPTX inventory; Python 3.9+, standard library, no Office or rendering.

Usage: python inspect_pptx.py --pptx deck.pptx [--include-text] [--out inventory.json]
Exit codes: 0 inventory generated, 1 structural errors found, 2 invalid input/output.
"""

import argparse
import hashlib
import json
import posixpath
import sys
import zipfile
import zlib
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET

MAX_XML_BYTES = 16 * 1024 * 1024
MAX_TOTAL_XML_BYTES = 128 * 1024 * 1024
MAX_MEMBERS = 50000
EMU_PER_INCH = 914400
KINDS = {"sp": "shape", "cxnSp": "connector", "pic": "picture",
         "grpSp": "group", "graphicFrame": "graphic_frame"}
LIMITATIONS = [
    "This is a partial OOXML inventory, not rendering or a complete schema validation.",
    "No visual text-overflow, legibility, factual accuracy, or scientific-meaning checks.",
    "Few pictures do not prove editability; native objects do not prove useful editing.",
    "Counts cover slide XML, not inherited master/layout objects or embedded chart text.",
    "AlternateContent branches may be counted and extracted together; counts and text are structural signals, not proof of visible slide content.",
    "Bounds use top-level unrotated transforms only; group/local coordinates are unmeasured.",
    "Picture ratios use clipped object rectangles, not visible pixels; overlap may exceed 1.",
    "Cropping, transparency, rotation, grouping and picture fills limit picture-area estimates.",
    "Notes are rough text extraction excluding date, slide-number, header, footer and slide-image placeholders.",
    "Optional full text follows XML paragraph order, not visual reading order; image/chart text, bullet markers and formula structure are not reconstructed.",
    "Character counts retain the text-node total and exclude inserted paragraph/line separators; they need not equal the full-text string length.",
    "No ZIP extraction, macros, embedded objects, external links, or Office execution occurs.",
]


def local(tag):
    return tag.rsplit("}", 1)[-1]

def child(node, name):
    return next((x for x in node if local(x.tag) == name), None)

def rel_id(node, name="id"):
    for key, value in node.attrib.items():
        if key.startswith("{") and key.split("}")[0].endswith("/relationships"):
            if local(key) == name:
                return value
    return None

def texts(node):
    return [x.text or "" for x in node.iter() if local(x.tag) == "t"]

def excerpt(parts, limit=600):
    return " ".join(" ".join(parts).split())[:limit]


def paragraphs(node):
    """Preserve paragraph and explicit line breaks without reconstructing layout."""
    result = []
    for para in node.iter():
        if local(para.tag) != "p":
            continue
        pieces = []
        for item in para.iter():
            tag = local(item.tag)
            if tag == "t":
                pieces.append(item.text or "")
            elif tag == "br":
                pieces.append("\n")
        result.append("".join(pieces))
    return result

class Package:
    def __init__(self, archive):
        self.archive, self.errors, self.warnings, self.used = archive, [], [], 0
        self.names = set(archive.namelist())
        if len(self.names) != len(archive.infolist()):
            self.error("duplicate_zip_names", "", "Duplicate member names are ambiguous.")

    def error(self, code, part, detail):
        self.errors.append({"code": code, "part": part, "detail": detail})

    def warn(self, code, part, detail):
        self.warnings.append({"code": code, "part": part, "detail": detail})

    def xml(self, part, required=True):
        if part not in self.names:
            if required:
                self.error("missing_part", part, "Required ZIP member is absent.")
            return None
        try:
            info = self.archive.getinfo(part)
            if info.file_size > MAX_XML_BYTES or self.used + info.file_size > MAX_TOTAL_XML_BYTES:
                raise ValueError("XML size limit exceeded.")
            if info.flag_bits & 1:
                raise ValueError("Encrypted XML members are not supported.")
            with self.archive.open(info) as stream:
                data = stream.read(MAX_XML_BYTES + 1)
            self.used += len(data)
            if len(data) > MAX_XML_BYTES or self.used > MAX_TOTAL_XML_BYTES:
                raise ValueError("XML read budget exceeded.")
            probe = data.replace(b"\x00", b"").upper()
            if b"<!DOCTYPE" in probe or b"<!ENTITY" in probe:
                raise ValueError("DOCTYPE and ENTITY declarations are rejected.")
            return ET.fromstring(data)
        except (OSError, EOFError, ValueError, LookupError, RuntimeError, NotImplementedError, zlib.error,
                zipfile.BadZipFile, ET.ParseError) as exc:
            self.error("unreadable_xml", part, str(exc))
            return None

    def relationships(self, part, required=False):
        folder, name = posixpath.split(part)
        path = posixpath.join(folder, "_rels", name + ".rels")
        root = self.xml(path, required)
        result = {}
        if root is None:
            return result
        if local(root.tag) != "Relationships":
            self.error("invalid_relationship_root", path, "Expected Relationships.")
            return result
        for node in root:
            if local(node.tag) != "Relationship":
                continue
            rid, kind, target = (node.get(k) for k in ("Id", "Type", "Target"))
            if not rid or not kind or not target or rid in result:
                self.error("invalid_relationship", path, "Missing fields or duplicate relationship ID.")
                continue
            external = node.get("TargetMode", "Internal").lower() == "external"
            resolved = None
            if not external:
                try:
                    uri = urlsplit(target)
                    decoded = unquote(uri.path)
                    if uri.scheme or uri.netloc or uri.query or uri.fragment or "\\" in decoded:
                        raise ValueError("Unsupported internal target URI.")
                    resolved = posixpath.normpath(decoded.lstrip("/") if decoded.startswith("/")
                                                 else posixpath.join(folder, decoded))
                    if resolved in ("", ".", "..") or resolved.startswith("../"):
                        raise ValueError("Internal target escapes the package.")
                    if resolved not in self.names:
                        self.error("missing_relationship_target", path, resolved)
                except ValueError as exc:
                    resolved = None
                    self.error("invalid_relationship_target", path, str(exc))
            result[rid] = {"type": kind.rsplit("/", 1)[-1], "part": resolved,
                           "external": external}
        return result


def coordinate(value):
    if value is None or len(value) > 16:
        raise ValueError("Missing or excessively long integer coordinate.")
    return int(value)


def geometry(node):
    kind = local(node.tag)
    if kind == "grpSp":
        return None, "group_transform"
    holder = node if kind == "graphicFrame" else child(node, "spPr")
    transform = child(holder, "xfrm") if holder is not None else None
    if transform is None:
        return None, "missing_or_inherited_transform"
    try:
        if coordinate(transform.get("rot", "0")) % 21600000:
            return None, "rotated_transform"
        offset, extent = child(transform, "off"), child(transform, "ext")
        if offset is None or extent is None:
            return None, "incomplete_transform"
        box = [coordinate(offset.get("x")), coordinate(offset.get("y")),
               coordinate(extent.get("cx")), coordinate(extent.get("cy"))]
        if box[2] < 0 or box[3] < 0:
            return None, "invalid_transform"
        return box, None
    except (TypeError, ValueError):
        return None, "invalid_transform"


def notes_inventory(pkg, relationships, include_text=False):
    refs = [r for r in relationships.values() if r["type"] == "notesSlide"]
    output = {"present": bool(refs), "characters": 0, "excerpt": ""}
    if include_text:
        output.update(text="", paragraphs=[])
    if len(refs) > 1:
        pkg.error("multiple_notes_parts", "", "A slide has multiple notesSlide relationships.")
    if not refs:
        return output
    ref = refs[0]
    if ref["external"] or not ref["part"]:
        pkg.error("invalid_notes_target", "", "notesSlide must be an internal part.")
        return output
    output["part"] = ref["part"]
    root = pkg.xml(ref["part"])
    if root is None:
        return output
    if local(root.tag) != "notes":
        pkg.error("invalid_notes_root", ref["part"], "Expected notes.")
        return output
    parts, full_paragraphs = [], []
    for shape in root.iter():
        if local(shape.tag) == "sp":
            placeholders = [p.get("type") for p in shape.iter() if local(p.tag) == "ph"]
            if not any(p in {"dt", "sldNum", "hdr", "ftr", "sldImg"} for p in placeholders):
                parts.extend(texts(shape))
                if include_text:
                    full_paragraphs.extend(paragraphs(shape))
    output.update(characters=sum(map(len, parts)), excerpt=excerpt(parts))
    if include_text:
        output.update(text="\n".join(full_paragraphs), paragraphs=full_paragraphs)
    return output


def slide_inventory(pkg, part, order, slide_id, canvas, include_text=False):
    output = {"order": order, "slide_id": slide_id, "part": part}
    root = pkg.xml(part)
    if root is None:
        return output
    if local(root.tag) != "sld":
        pkg.error("invalid_slide_root", part, "Expected sld.")
        return output
    relationships = pkg.relationships(part)
    for node in root.iter():
        for name in ("id", "embed", "link"):
            rid = rel_id(node, name)
            if rid and rid not in relationships:
                pkg.error("unresolved_relationship_id", part, rid)
    output["hidden"] = root.get("show", "1").lower() in {"0", "false", "off"}
    tree = next((x for x in root.iter() if local(x.tag) == "spTree"), None)
    if tree is None:
        pkg.error("missing_shape_tree", part, "Slide has no spTree.")
        return output
    counts = {v: 0 for v in KINDS.values()}
    counts.update(table=0, chart=0, native_text_shapes=0, picture_fill_shapes=0,
                  native_math_objects=0, nested_drawable_objects=0)
    counts["native_math_objects"] = sum(local(x.tag) == "oMath" for x in tree.iter())
    top = list(tree)
    objects = []
    metadata_containers = {"sp": "nvSpPr", "cxnSp": "nvCxnSpPr", "pic": "nvPicPr",
                           "grpSp": "nvGrpSpPr", "graphicFrame": "nvGraphicFramePr"}
    for node in tree.iter():
        tag = local(node.tag)
        if tag not in KINDS:
            continue
        counts[KINDS[tag]] += 1
        container = child(node, metadata_containers[tag])
        identity = child(container, "cNvPr") if container is not None else None
        objects.append({"kind": KINDS[tag], "id": identity.get("id") if identity is not None else None,
                        "name": identity.get("name") if identity is not None else None,
                        "nested": node not in top})
        if node not in top:
            counts["nested_drawable_objects"] += 1
        if tag == "sp":
            counts["native_text_shapes"] += bool(texts(node))
            counts["picture_fill_shapes"] += any(local(x.tag) == "blipFill" for x in node.iter())
        if tag == "graphicFrame":
            gd = next((x for x in node.iter() if local(x.tag) == "graphicData"), None)
            uri = gd.get("uri", "") if gd is not None else ""
            chart_refs = [relationships.get(rel_id(x), {}) for x in node.iter() if rel_id(x)]
            is_chart = uri.rstrip("/").lower().endswith(("/chart", "/chartex")) or any(
                r.get("type", "").lower() in {"chart", "chartex"} for r in chart_refs)
            counts["chart"] += int(is_chart)
            counts["table"] += int(uri.rstrip("/").endswith("/table") or any(
                local(x.tag) == "tbl" for x in node.iter()))
    parts = texts(tree)
    output.update(inventory=counts, objects=objects, native_text={"runs": len(parts),
                  "characters": sum(map(len, parts)), "excerpt": excerpt(parts)})
    if include_text:
        full_paragraphs = paragraphs(tree)
        output["native_text"].update(text="\n".join(full_paragraphs), paragraphs=full_paragraphs)
    measured, unmeasured, bounds, ratios = 0, [], [], []
    for index, node in enumerate(top, 1):
        if local(node.tag) not in KINDS:
            continue
        box, reason = geometry(node)
        if reason or not canvas:
            unmeasured.append({"top_level_index": index, "kind": KINDS[local(node.tag)],
                               "reason": reason or "unknown_canvas"})
            if reason == "invalid_transform":
                pkg.error("invalid_transform", part, "Invalid top-level transform at index %s." % index)
            continue
        measured += 1
        x, y, w, h = box
        cw, ch = canvas
        if x < 0 or y < 0 or x + w > cw or y + h > ch:
            bounds.append({"top_level_index": index, "box_emu": box})
        if local(node.tag) == "pic":
            area = max(0, min(x + w, cw) - max(x, 0)) * max(0, min(y + h, ch) - max(y, 0))
            ratios.append(area / (cw * ch))
    if bounds:
        pkg.warn("basic_bounds", part, "%s top-level rectangles extend beyond the canvas." % len(bounds))
    output["geometry"] = {"measured_top_level": measured, "unmeasured_top_level": unmeasured,
                          "nested_objects_unmeasured": counts["nested_drawable_objects"],
                          "out_of_bounds_hints": bounds}
    output["picture_area_estimate"] = {"measured_pictures": len(ratios),
        "unmeasured_pictures": counts["picture"] - len(ratios),
        "largest_clipped_rectangle_ratio": round(max(ratios, default=0), 4),
        "sum_clipped_rectangle_ratios_not_union": round(sum(ratios), 4),
        "near_full_slide_candidates_at_0_90": sum(r >= 0.90 for r in ratios)}
    output["external_relationships_not_followed"] = sum(r["external"] for r in relationships.values())
    media = {}
    for ref in relationships.values():
        if ref["type"] == "image" and not ref["external"] and ref["part"]:
            extension = posixpath.splitext(ref["part"])[1].lower() or "unknown"
            media.setdefault(extension, set()).add(ref["part"])
    output["image_media_formats_by_extension"] = {key: len(parts) for key, parts in sorted(media.items())}
    output["image_format_note"] = "Unique linked parts by extension, including fallbacks; formats are not decoded or proven editable."
    output["notes"] = notes_inventory(pkg, relationships, include_text)
    return output


def inspect(path, include_text=False):
    before = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    with zipfile.ZipFile(path) as archive:
        if len(archive.infolist()) > MAX_MEMBERS:
            raise ValueError("ZIP member count exceeds the inspection limit.")
        pkg = Package(archive)
        package_relationships = pkg.relationships("", required=True)
        candidates = [r for r in package_relationships.values() if r["type"] == "officeDocument"]
        part, root, relationships = None, None, {}
        if len(candidates) != 1 or candidates[0]["external"] or not candidates[0]["part"]:
            pkg.error("invalid_main_part", "_rels/.rels", "Expected one internal officeDocument relationship.")
        else:
            part = candidates[0]["part"]
            root = pkg.xml(part)
            relationships = pkg.relationships(part, required=True)
        canvas, slides = None, []
        if root is not None and local(root.tag) != "presentation":
            pkg.error("invalid_presentation_root", part, "Expected presentation.")
            root = None
        if root is not None:
            size = child(root, "sldSz")
            try:
                canvas = [coordinate(size.get("cx")), coordinate(size.get("cy"))]
                if min(canvas) <= 0:
                    raise ValueError("Canvas dimensions must be positive.")
            except (AttributeError, TypeError, ValueError):
                canvas = None
                pkg.error("invalid_canvas", part, "Missing or invalid sldSz dimensions.")
            sequence = child(root, "sldIdLst")
            seen = set()
            for node in sequence if sequence is not None else []:
                if local(node.tag) != "sldId":
                    continue
                rid, sid = rel_id(node), node.get("id")
                ref = relationships.get(rid, {})
                if not sid or sid in seen:
                    pkg.error("invalid_slide_id", part, "Missing or repeated slide ID.")
                seen.add(sid)
                order = len(slides) + 1
                if ref.get("type") != "slide" or ref.get("external") or not ref.get("part"):
                    pkg.error("invalid_slide_relationship", part, "Cannot resolve slide %s (%s)." % (order, rid))
                    slides.append({"order": order, "slide_id": sid, "part": None})
                else:
                    slides.append(slide_inventory(pkg, ref["part"], order, sid, canvas, include_text))
        after = path.stat()
        if not slides and not pkg.errors:
            pkg.warn("empty_presentation", part, "The presentation has no ordered slides.")
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            pkg.error("input_changed", str(path), "Input changed during inspection; identity is not stable.")
        report = {"status": "structural_errors" if pkg.errors else "inventory_generated",
                  "input": {"path": str(path.resolve()), "bytes": before.st_size, "sha256": digest.hexdigest()},
                  "canvas": {"emu": canvas, "inches": [round(v / EMU_PER_INCH, 4) for v in canvas] if canvas else None},
                  "slide_count": len(slides), "slides": slides, "errors": pkg.errors,
                  "warnings": pkg.warnings, "limitations": LIMITATIONS}
        return report, 1 if pkg.errors else 0


def main():
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pptx", required=True, type=Path)
    parser.add_argument("--include-text", action="store_true",
                        help="Include full slide XML paragraphs and notes; no image OCR or reading-order inference.")
    parser.add_argument("--out", type=Path, help="New JSON file; existing paths are never overwritten.")
    args = parser.parse_args()
    try:
        if not args.pptx.is_file() or args.pptx.suffix.lower() != ".pptx":
            raise ValueError("--pptx must name an existing .pptx file.")
        if args.out and args.out.exists():
            raise ValueError("--out already exists; choose a new path.")
        report, code = inspect(args.pptx, include_text=args.include_text)
        payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.out:
            with args.out.open("x", encoding="utf-8") as stream:
                stream.write(payload)
        else:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8")
            sys.stdout.write(payload)
        return code
    except (OSError, EOFError, ValueError, RuntimeError, NotImplementedError,
            zlib.error, zipfile.BadZipFile) as exc:
        print("inspect_pptx: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
