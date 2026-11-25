"""Search and safely copy layout/skin templates installed with XCGUI IDE."""

from __future__ import annotations

import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from cli_anything.xcide.core.project import resolve_ide_root


_SKIP_DIRS = {".git", ".svn", ".cli-anything", "__pycache__", ".vs", "ipch",
              "debug", "debug64", "release", "release64", "obj", "x64", "x86"}
_SKIP_SUFFIXES = {".exe", ".obj", ".pdb", ".ilk", ".pch", ".idb", ".ipch"}


class UITemplateError(ValueError):
    """XCGUI layout/skin template metadata, paths, or copy destination are invalid."""


def template_root(ide_root: str | os.PathLike[str] | None = None) -> Path:
    """Return the real installed IDE template asset tree."""
    root = resolve_ide_root(ide_root) / "data" / "template"
    if not root.is_dir():
        raise UITemplateError(f"XCGUI IDE template asset directory does not exist: {root}")
    return root.resolve()


def _entry(config_path: Path, root: Path) -> dict[str, Any]:
    try:
        xml = ET.parse(config_path).getroot()
    except (OSError, ET.ParseError) as exc:
        raise UITemplateError(f"Cannot parse XCGUI template metadata {config_path}: {exc}") from exc
    if xml.tag != "xc_template":
        raise UITemplateError(f"Template config must have <xc_template> root: {config_path}")
    fields = {node.tag: (node.text or "").strip() for node in xml.iter() if node is not xml}
    relative = config_path.relative_to(root)
    category = fields.get("type", "") or relative.parts[0]
    if category not in {"皮肤", "布局模板"}:
        raise UITemplateError(f"Unsupported template category: {category or '(empty)'}")
    source_root = config_path.parent.resolve()
    if not source_root.is_relative_to(root):
        raise UITemplateError("Template config path escapes the selected IDE installation.")
    payload_name = fields.get("path", "project") or "project"
    payload = (source_root / payload_name).resolve()
    if not payload.is_relative_to(source_root) or not payload.is_dir():
        raise UITemplateError(f"Template payload directory is missing or unsafe: {payload_name}")
    return {"id": config_path.relative_to(root).parent.as_posix(),
            "name": fields.get("name") or source_root.name,
            "category": category, "author": fields.get("author", ""),
            "version": fields.get("versionXCGUI", ""), "date": fields.get("date", ""),
            "object_type": fields.get("objectType", ""), "child_type": fields.get("childType", ""),
            "item_type": fields.get("item", ""), "explain": fields.get("explain", ""),
            "preview": fields.get("image", ""), "directory": str(source_root),
            "config_file": str(config_path.resolve()), "payload": str(payload)}


def _matches(entry: dict[str, Any], query: str) -> bool:
    needle = query.strip().casefold()
    haystack = " ".join(str(entry.get(key, "")) for key in
                         ("id", "name", "category", "author", "object_type", "child_type", "item_type", "explain"))
    return not needle or needle.casefold() in haystack.casefold()


def list_ui_templates(
    *, ide_root: str | os.PathLike[str] | None = None, query: str = "",
    category: str | None = None, limit: int = 200,
) -> dict[str, Any]:
    """List installed skin/layout templates using their native template.config files."""
    if not 1 <= limit <= 2000:
        raise UITemplateError("Template result limit must be between 1 and 2000.")
    if category not in {None, "皮肤", "布局模板"}:
        raise UITemplateError("Template category must be 皮肤 or 布局模板.")
    root = template_root(ide_root)
    entries = []
    for current, directories, filenames in os.walk(root, followlinks=False):
        here = Path(current)
        directories[:] = sorted((name for name in directories
                                 if name.casefold() not in _SKIP_DIRS and not (here / name).is_symlink()),
                                key=str.casefold)
        if "template.config" not in filenames:
            continue
        config_path = here / "template.config"
        try:
            item = _entry(config_path, root)
        except UITemplateError:
            continue
        if category and item["category"] != category:
            continue
        if not _matches(item, query):
            continue
        entries.append(item)
    entries.sort(key=lambda item: item["id"].casefold())
    selected = entries[:limit]
    return {"ok": True, "root": str(root), "query": query, "category": category,
            "count": len(selected), "total": len(entries), "truncated": len(entries) > len(selected),
            "templates": selected}


def _find_ui_template(identifier: str, root: Path) -> dict[str, Any]:
    normalized = identifier.replace("\\", "/")
    parts = normalized.split("/")
    if (not normalized or normalized.startswith("/") or ":" in normalized
            or any(part in {"", ".", ".."} for part in parts)):
        raise UITemplateError("Template ID must be a relative ID returned by ui-template list.")
    matches = []
    for current, directories, filenames in os.walk(root, followlinks=False):
        here = Path(current)
        directories[:] = [name for name in directories
                          if name.casefold() not in _SKIP_DIRS and not (here / name).is_symlink()]
        if "template.config" not in filenames:
            continue
        config_path = here / "template.config"
        try:
            item = _entry(config_path, root)
        except UITemplateError:
            continue
        if item["id"].casefold() == normalized.casefold():
            matches.append(item)
    if len(matches) != 1:
        raise UITemplateError(f"Cannot resolve one exact UI template ID: {identifier}")
    return matches[0]


def inspect_ui_template(
    identifier: str, *, ide_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Inspect native metadata and files supplied by one layout/skin template."""
    root = template_root(ide_root)
    entry = _find_ui_template(identifier, root)
    payload = Path(entry["payload"])
    files = []
    for current, directories, filenames in os.walk(payload, followlinks=False):
        here = Path(current)
        directories[:] = [name for name in directories
                          if name.casefold() not in _SKIP_DIRS and not (here / name).is_symlink()]
        for name in sorted(filenames, key=str.casefold):
            path = here / name
            if not path.is_symlink() and path.suffix.casefold() not in _SKIP_SUFFIXES:
                files.append({"file": path.relative_to(payload).as_posix(), "bytes": path.stat().st_size})
    files.sort(key=lambda item: item["file"].casefold())
    return {"ok": True, **entry, "file_count": len(files), "files": files}


def _ignore(_directory: str, names: list[str]) -> set[str]:
    ignored = set()
    for name in names:
        path = Path(_directory) / name
        if path.is_symlink() or name.casefold() in _SKIP_DIRS or path.suffix.casefold() in _SKIP_SUFFIXES:
            ignored.add(name)
    return ignored


def copy_ui_template(
    output_dir: str | os.PathLike[str], name: str, identifier: str,
    *, ide_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Copy one native template payload into a new destination directory."""
    root = template_root(ide_root)
    entry = _find_ui_template(identifier, root)
    parent = Path(output_dir).expanduser().resolve()
    if parent == root or root in parent.parents:
        raise UITemplateError(f"Cannot copy a template into the installed template catalog: {parent}")
    if not name or Path(name).name != name or name in {".", ".."} or any(c in name for c in '<>:"/\\|?*'):
        raise UITemplateError("Output name must be a single valid Windows filename.")
    destination = parent / name
    if destination.exists() or (parent.is_dir() and any(item.name.casefold() == name.casefold()
                                                        for item in parent.iterdir())):
        raise UITemplateError(f"Output directory already exists; refusing to overwrite: {destination}")
    payload = Path(entry["payload"])
    staging_parent: Path | None = None
    try:
        parent.mkdir(parents=True, exist_ok=True)
        staging_parent = Path(tempfile.mkdtemp(prefix=f".{name}-xcide-ui-template-", dir=parent))
        staged = staging_parent / name
        shutil.copytree(payload, staged, ignore=_ignore)
        if destination.exists() or any(item.name.casefold() == name.casefold() for item in parent.iterdir()
                                       if item != staging_parent):
            raise UITemplateError(f"Output directory already exists; refusing to overwrite: {destination}")
        staged.rename(destination)
    except BaseException:
        if (staging_parent is not None and staging_parent.exists()
                and staging_parent.resolve().parent == parent
                and staging_parent.name.startswith(f".{name}-xcide-ui-template-")):
            shutil.rmtree(staging_parent)
        raise
    if staging_parent is not None:
        staging_parent.rmdir()
    copied_count = sum(1 for _ in destination.rglob("*") if _.is_file() and not _.is_symlink())
    return {"ok": True, "template_id": entry["id"], "category": entry["category"],
            "destination": str(destination), "file_count": copied_count,
            "skipped_generated_artifacts": True}
