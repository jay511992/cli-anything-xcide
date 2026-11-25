"""Read XCGUI IDE editor themes from their installed native configuration files."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from cli_anything.xcide.core.project import resolve_ide_root


class ThemeError(ValueError):
    """An installed theme is missing, ambiguous, or contains invalid XML."""


def theme_root(ide_root: str | os.PathLike[str] | None = None) -> Path:
    root = resolve_ide_root(ide_root) / "data" / "theme"
    if not root.is_dir():
        raise ThemeError(f"炫彩 IDE 主题目录不存在：{root}")
    return root.resolve()


def _entry(config: Path, root: Path) -> dict[str, Any]:
    if config.is_symlink() or not config.resolve().is_relative_to(root):
        raise ThemeError(f"主题配置越过了所选 IDE 安装目录：{config}")
    try:
        xml = ET.parse(config).getroot()
    except (OSError, ET.ParseError) as exc:
        raise ThemeError(f"无法读取 IDE 主题配置 {config}：{exc}") from exc
    if xml.tag != "xc_theme":
        raise ThemeError(f"主题配置根节点应为 <xc_theme>：{config}")

    general_font = xml.find("font")
    editor = xml.find("editor")
    editor_font = editor.find("font") if editor is not None else None
    skin = xml.find("skin")
    design_color = xml.find("designViewColor")
    tab_size = editor.find("tabSize") if editor is not None else None
    row_space = editor.find("rowSpace") if editor is not None else None
    editor_colors = editor.find("editor_color") if editor is not None else None
    skin_path = skin.get("path", "").strip() if skin is not None else ""
    skin_file = None
    if skin_path:
        candidate = (root.parent.parent / skin_path.replace("\\", "/")).resolve()
        install = root.parent.parent.resolve()
        if candidate.is_relative_to(install) and candidate.is_file():
            skin_file = str(candidate)

    return {
        "id": config.relative_to(root).with_suffix("").as_posix(),
        "name": config.parent.name,
        "config_file": str(config.resolve()),
        "general_font": general_font.get("name") if general_font is not None else None,
        "general_font_size": general_font.get("size") if general_font is not None else None,
        "editor_font": (editor_font.get("nameZh") or editor_font.get("name"))
        if editor_font is not None else None,
        "editor_font_internal": editor_font.get("name") if editor_font is not None else None,
        "editor_font_size": editor_font.get("size") if editor_font is not None else None,
        "tab_size": tab_size.get("size") if tab_size is not None else None,
        "row_space": row_space.get("value") if row_space is not None else None,
        "design_view_color": design_color.get("color") if design_color is not None else None,
        "skin": skin_path,
        "skin_file": skin_file,
        "breakpoint_color": editor_colors.get("margin.breakpoint") if editor_colors is not None else None,
        "run_row_color": editor_colors.get("margin.runRowArrow") if editor_colors is not None else None,
    }


def list_themes(
    *, ide_root: str | os.PathLike[str] | None = None, query: str = "", limit: int = 200,
) -> dict[str, Any]:
    """List installed themes and selected truthful fields from their XML configs."""
    if not 1 <= limit <= 2000:
        raise ThemeError("主题结果上限必须在 1 到 2000 之间。")
    root = theme_root(ide_root)
    needle = query.strip().casefold()
    themes = []
    for config in root.rglob("xctheme.config"):
        if any(part.casefold() in {".git", "debug", "obj", "release"} for part in config.relative_to(root).parts):
            continue
        try:
            entry = _entry(config, root)
        except ThemeError:
            continue
        if not needle or needle in " ".join(str(value or "") for value in entry.values()).casefold():
            themes.append(entry)
    themes.sort(key=lambda item: item["id"].casefold())
    selected = themes[:limit]
    return {"ok": True, "root": str(root), "query": query, "count": len(selected),
            "total": len(themes), "truncated": len(themes) > len(selected), "themes": selected}


def inspect_theme(identifier: str, *, ide_root: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Read the config for one exact relative theme ID returned by ``list_themes``."""
    normalized = identifier.replace("\\", "/")
    parts = normalized.split("/")
    if (not normalized or normalized.startswith("/") or ":" in normalized
            or any(part in {"", ".", ".."} for part in parts)):
        raise ThemeError("主题 ID 必须是 theme list 返回的相对路径。")
    root = theme_root(ide_root)
    matches = []
    for config in root.rglob("xctheme.config"):
        if config.is_symlink() or not config.resolve().is_relative_to(root):
            continue
        if config.relative_to(root).with_suffix("").as_posix().casefold() == normalized.casefold():
            matches.append(config)
    if len(matches) != 1:
        raise ThemeError(f"无法将该主题 ID 唯一映射到本机主题配置：{identifier}")
    return {"ok": True, **_entry(matches[0], root)}
