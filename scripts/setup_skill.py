#!/usr/bin/env python3
"""Read-only setup checks and explicit directory-copy installation.

Python 3.9+, standard library. No dependency installation or host configuration.
check does not launch a host, PPT engine, Office, renderer, or other helper.
Exit codes: 0 completed; 1 package/check problem; 2 invalid request/install failure.
"""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import posixpath
import re
import shutil
import stat
import sys
import uuid
from urllib.parse import unquote, urlsplit

NAME = "research-to-report-and-briefing"
SOURCE = Path(__file__).resolve().parent.parent
HOST_DIRS = {"codex": ".agents", "claude": ".claude"}
IGNORED = {"__pycache__", ".git", ".DS_Store"}
REQUIRED_RESOURCES = (
    "scripts/project_memory.py", "scripts/audit_content.py", "scripts/inspect_pptx.py",
    "assets/project.schema.json", "assets/memory-templates.json",
    "assets/content-ledger.schema.json", "assets/deck-plan.schema.json",
    "assets/acceptance-receipt.example.json", "assets/preference-profile.example.json",
    "assets/visual-profile.example.json", "assets/dense-technical.profile.example.json",
    "assets/timing-plan.example.json",
)


def within(path, parent):
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def linked(path):
    info = path.lstat()
    return (stat.S_ISLNK(info.st_mode) or
            bool(getattr(info, "st_file_attributes", 0) &
                 getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)))


def inventory(root):
    """Hash ordinary files; reject links/reparse points and cross-platform collisions."""
    if linked(root) or not root.is_dir():
        raise ValueError("Skill directory must be an ordinary directory: " + str(root))
    files, directories, seen = {}, [], set()

    def visit(folder):
        for path in sorted(folder.iterdir()):
            if path.name in IGNORED or path.suffix in {".pyc", ".pyo"}:
                continue
            if linked(path):
                raise ValueError("Linked files/directories are not copied: " + str(path))
            key = path.relative_to(root).as_posix()
            if key.casefold() in seen:
                raise ValueError("Case-insensitive path collision: " + key)
            seen.add(key.casefold())
            if path.is_dir():
                directories.append(key)
                visit(path)
            elif path.is_file():
                digest = hashlib.sha256()
                with path.open("rb") as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(block)
                files[key] = digest.hexdigest()
            else:
                raise ValueError("Unsupported filesystem object: " + str(path))

    visit(root)
    return {"files": files, "directories": sorted(directories)}


def markdown_destinations(text):
    """Read common inline links/reference definitions, excluding code examples."""
    prose, fence = [], None
    for line in text.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if marker:
            token, rest = marker.groups()
            if fence is None:
                fence = (token[0], len(token))
            elif token[0] == fence[0] and len(token) >= fence[1] and not rest.strip():
                fence = None
            continue
        if fence is None and not line.startswith(("    ", "\t")):
            prose.append(line)
    text = re.sub(r"(`+).*?\1", "", "\n".join(prose), flags=re.S)
    patterns = (r"!?\[[^\]\n]*\]\(\s*(?:<([^>\n]+)>|([^\s)]+))",
                r"(?m)^ {0,3}\[[^\]\n]+\]:\s*(?:<([^>\n]+)>|(\S+))")
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            yield match[1] or match[2]


def resource_problems(manifest):
    problems = []
    files = manifest["files"]
    available = set(files) | set(manifest["directories"])
    for relative in REQUIRED_RESOURCES:
        if relative not in files:
            problems.append("Missing required package resource: " + relative)
    for relative in files:
        if not relative.endswith(".md"):
            continue
        content = (SOURCE / relative).read_text(encoding="utf-8-sig")
        for destination in markdown_destinations(content):
            parsed = urlsplit(destination)
            # URLs, local anchors and absolute external paths are not bundled dependencies.
            if parsed.scheme or parsed.netloc or not parsed.path or parsed.path.startswith("/"):
                continue
            target = posixpath.normpath(posixpath.join(posixpath.dirname(relative), unquote(parsed.path)))
            if target == ".." or target.startswith("../") or target not in available:
                problems.append("Missing/outside package link in " + relative + ": " + destination)
    return problems


def unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def finite_json_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('JSON number exceeds the finite float range: ' + value)
    return number


def reject_json_constant(value):
    raise ValueError('Non-finite JSON constant is not supported: ' + value)


def package_check():
    problems = []
    manifest = None
    try:
        manifest = inventory(SOURCE)
        problems.extend(resource_problems(manifest))
        entry = (SOURCE / "SKILL.md").read_text(encoding="utf-8-sig")
        front = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", entry, re.S)
        if not front:
            problems.append("SKILL.md has no YAML frontmatter block.")
        else:
            # This is a small package check, not a general-purpose YAML parser.
            name = re.search(r"(?m)^name:\s*[\"']?([a-z0-9-]+)[\"']?\s*$", front[1])
            if not name or name[1] != NAME or SOURCE.name != NAME:
                problems.append("Folder name and frontmatter name must match " + NAME + ".")
            if not re.search(r"(?m)^description:\s*\S", front[1]):
                problems.append("SKILL.md needs a nonempty description.")
        for relative in manifest["files"]:
            path = SOURCE / relative
            if path.suffix == ".json":
                try:
                    json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=unique_json_object,
                               parse_constant=reject_json_constant, parse_float=finite_json_float)
                except ValueError as error:
                    raise ValueError("Invalid JSON in " + relative + ": " + str(error)) from error
            elif path.suffix == ".py":
                compile(path.read_bytes(), str(path), "exec")
    except (OSError, ValueError, SyntaxError, UnicodeError) as error:
        problems.append(str(error))
    if sys.version_info < (3, 9):
        problems.append("Packaged helpers require Python 3.9 or newer.")
    return manifest, problems


def destinations(args):
    if args.skills_dir:
        if args.host or args.scope or args.project:
            raise ValueError("--skills-dir is independent; omit --host, --scope and --project.")
        return {"custom": Path(args.skills_dir).expanduser().resolve()}
    scope = args.scope or "user"
    if scope == "project":
        if not args.project:
            raise ValueError("--scope project requires --project DIR.")
        root = Path(args.project).expanduser().resolve()
        if not root.is_dir():
            raise ValueError("Project directory must already exist: " + str(root))
    else:
        if args.project:
            raise ValueError("--project requires --scope project.")
        root = Path.home()
    if args.command == "install" and not args.host:
        raise ValueError("install requires --host codex|claude or --skills-dir PARENT.")
    hosts = [args.host] if args.host else list(HOST_DIRS)
    return {host: (root / HOST_DIRS[host] / "skills").resolve() for host in hosts}


def destination_status(parent, manifest):
    target = parent / NAME
    if not os.path.lexists(str(target)):
        status = {"status": "absent"}
    else:
        try:
            status = {"status": "same_content" if inventory(target) == manifest else "different_content"}
        except (OSError, ValueError) as error:
            status = {"status": "unreadable_or_unsupported", "detail": str(error)}
    return dict(status, path=str(target))


def check(args):
    parents = destinations(args)
    manifest, problems = package_check()
    candidates = []
    for parent in dict.fromkeys([SOURCE.parent] + list(parents.values())):
        entry = parent / "ppt-master" / "SKILL.md"
        if entry.is_file():
            candidates.append(str(entry))
    return {
        "command": "check", "status": "ok" if not problems else "problem",
        "source": str(SOURCE), "package_problems": problems,
        "package_structure": "basic_checks_passed" if not problems else "needs_attention",
        "host_loading": "not_verified; check discovery in the selected host after installation",
        "python": {"executable": sys.executable, "version": sys.version.split()[0],
                   "helper_syntax": "checked" if not problems else "see_package_problems",
                   "third_party_packages_required_by_bundled_helpers": False},
        "installation_targets": {host: destination_status(parent, manifest)
                                 for host, parent in parents.items()},
        "ppt_master": {"entrypoint_candidates": candidates,
                       "runtime_and_dependencies": "not_verified"},
        "path_candidates": {name: shutil.which(name) for name in
                            ("codex", "claude", "node", "soffice", "libreoffice", "pdftoppm")},
        "external_capabilities": {
            "network_and_search": "not_verified; supplied by the host and its configured tools",
            "ppt_generation": "not_verified; use a separately available PPT engine such as ppt-master",
            "pptx_rendering": "not_verified; a PATH candidate does not prove successful rendering",
            "fonts": "not_verified; confirm Microsoft YaHei or document an available substitute"},
        "limitations": ["This checks this package, not the complete Agent Skills specification.",
                        "No host, engine, renderer, Office process, or downloaded script was launched."]
    }, (0 if not problems else 1)


def install(args):
    parents = destinations(args)
    parent = next(iter(parents.values()))
    target = parent / NAME
    manifest, problems = package_check()
    if problems:
        raise ValueError("Package checks failed: " + "; ".join(problems))
    if target == SOURCE:
        return {"command": "install", "status": "already_at_target", "path": str(target)}, 0
    if within(target, SOURCE) or within(SOURCE, target):
        raise ValueError("Source and installation target must not contain one another.")
    existing = destination_status(parent, manifest)
    if existing["status"] == "same_content":
        return {"command": "install", "status": "unchanged", "path": str(target)}, 0
    if existing["status"] != "absent":
        raise ValueError("Target already exists with different or unsupported contents; "
                         "nothing was overwritten: " + str(target))
    parent.mkdir(parents=True, exist_ok=True)
    # Inherit the chosen parent's permissions. On recent Windows Python builds,
    # tempfile's 0700 directory can be inaccessible to a restricted process token.
    # Keep the temporary leaf shorter than NAME so staging does not add a second
    # skill-directory level or unnecessarily exceed Windows path limits.
    for unused in range(8):
        stage = parent / (".rb-install-" + uuid.uuid4().hex[:16])
        try:
            stage.mkdir()
            break
        except FileExistsError:
            continue
    else:
        raise ValueError("Could not reserve a unique staging directory.")
    stage_resolved = stage.resolve()
    try:
        for relative in manifest["directories"]:
            (stage / relative).mkdir(parents=True, exist_ok=True)
        for relative in manifest["files"]:
            source_file = SOURCE / relative
            if linked(source_file):
                raise ValueError("Source changed to a link while copying: " + relative)
            shutil.copy2(str(source_file), str(stage / relative))
        if inventory(stage) != manifest or inventory(SOURCE) != manifest:
            raise ValueError("Source or copy changed during installation; installation was not published.")
        if os.path.lexists(str(target)):
            raise ValueError("Target appeared during installation; nothing was overwritten.")
        # Renaming publishes the complete directory, never a half-copied SKILL.md.
        # A concurrently created nonempty destination also makes rename fail.
        stage.rename(target)
    finally:
        # stage is the exact unique child created above, never a user-supplied path.
        if os.path.lexists(str(stage)):
            if (linked(stage) or stage.resolve() != stage_resolved or
                    stage_resolved.parent != parent or not stage.name.startswith(".rb-install-")):
                raise ValueError("Staging path changed; automatic cleanup was skipped: " + str(stage))
            shutil.rmtree(stage_resolved)
    return {"command": "install", "status": "installed", "path": str(target),
            "files_copied": len(manifest["files"]),
            "next_step": "Refresh the host's skill discovery; dependencies and host loading remain unverified."}, 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command")
    for command in ("check", "install"):
        sub = commands.add_parser(command)
        sub.add_argument("--host", choices=sorted(HOST_DIRS))
        sub.add_argument("--scope", choices=("user", "project"))
        sub.add_argument("--project", metavar="DIR")
        sub.add_argument("--skills-dir", metavar="PARENT")
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    try:
        result, code = check(args) if args.command == "check" else install(args)
    except (OSError, ValueError, shutil.Error) as error:
        result, code = {"command": args.command, "status": "error", "message": str(error)}, 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
