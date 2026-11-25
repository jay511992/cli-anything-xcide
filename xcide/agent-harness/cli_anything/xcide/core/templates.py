"""发现并基于炫彩 IDE 自带的炫语言工程模板创建项目。"""

from __future__ import annotations

import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from cli_anything.xcide.core import project as project_core


_SKIP_DIRS = {".git", ".cli-anything", "__pycache__", "debug", "debug64", "release", "release64", "obj", "x64", "x86"}
_SKIP_SUFFIXES = {".exe", ".obj", ".pdb", ".ilk", ".pch", ".idb", ".ipch"}


class TemplateError(ValueError):
    """IDE 模板不存在、不完整或不能安全实例化。"""


def template_root(ide_root: str | os.PathLike[str] | None = None) -> Path:
    """返回安装目录中炫语言的官方/用户工程模板根目录。"""
    return project_core.resolve_ide_root(ide_root) / "data" / "template" / "项目模板" / "炫语言"


def _template_metadata(path: Path, root: Path) -> dict[str, Any]:
    try:
        tree = ET.parse(path)
    except (OSError, ET.ParseError) as exc:
        raise TemplateError(f"无法解析 IDE 工程模板 {path}: {exc}") from exc
    node = tree.getroot()
    if node.tag != "project":
        raise TemplateError(f"工程模板必须使用 <project> 根节点：{path}")
    vc = node.find("vc")
    setting = vc.find("setting") if vc is not None else None
    configurations = [item.get("name", "") for item in setting.findall("config")] if setting is not None else []
    relative = path.relative_to(root).with_suffix("").as_posix()
    modules = node.findall("./modules/item")
    sources = node.findall("./codeExpand/item")
    return {
        "id": relative,
        "name": node.get("name") or path.stem,
        "project_file": str(path.resolve()),
        "directory": str(path.parent.resolve()),
        "platform": vc.get("platform") if vc is not None else None,
        "configuration": vc.get("config") if vc is not None else None,
        "configurations": configurations,
        "module_count": len(modules),
        "declared_file_count": len(sources),
        "has_vc_settings": bool(configurations),
    }


def list_templates(
    *, ide_root: str | os.PathLike[str] | None = None, query: str = "", limit: int = 200,
) -> dict[str, Any]:
    """按安装目录中的项目相对路径列出真实炫语言工程模板。"""
    if not 1 <= limit <= 2000:
        raise TemplateError("模板结果上限必须在 1 到 2000 之间。")
    root = template_root(ide_root).resolve()
    if not root.is_dir():
        raise TemplateError(f"炫语言工程模板目录不存在：{root}")
    needle = query.strip().casefold()
    templates: list[dict[str, Any]] = []
    for current, directories, files in os.walk(root):
        directories[:] = sorted((name for name in directories if name.casefold() not in _SKIP_DIRS),
                                key=str.casefold)
        for filename in sorted(files, key=str.casefold):
            if not filename.casefold().endswith(".xcproj"):
                continue
            path = Path(current) / filename
            try:
                entry = _template_metadata(path, root)
            except TemplateError:
                continue
            if needle and needle not in " ".join((entry["id"], entry["name"], entry["configuration"] or "")).casefold():
                continue
            templates.append(entry)
    templates.sort(key=lambda item: item["id"].casefold())
    selected = templates[:limit]
    return {"ok": True, "root": str(root), "count": len(selected), "total": len(templates),
            "truncated": len(templates) > len(selected), "query": query, "templates": selected}


def _find_template(identifier: str, root: Path) -> tuple[Path, dict[str, Any]]:
    normalized = identifier.replace("\\", "/").strip("/").casefold()
    if not normalized or normalized.startswith("/") or any(part in ("", ".", "..") for part in normalized.split("/")):
        raise TemplateError("模板 ID 必须使用 project templates 返回的相对 ID。")
    matches: list[dict[str, Any]] = []
    for candidate in root.rglob("*.xcproj"):
        if any(part.casefold() in _SKIP_DIRS for part in candidate.relative_to(root).parts):
            continue
        try:
            entry = _template_metadata(candidate, root)
        except TemplateError:
            continue
        if entry["id"].casefold() == normalized:
            matches.append(entry)
    if len(matches) != 1:
        raise TemplateError(f"找不到准确的炫语言工程模板 ID：{identifier}")
    path = Path(matches[0]["project_file"]).resolve()
    if not path.is_relative_to(root):
        raise TemplateError("模板路径越过了炫语言模板根目录。")
    return path, matches[0]


def _copy_ignore(_directory: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        path = Path(name)
        if name.casefold() in _SKIP_DIRS or path.suffix.casefold() in _SKIP_SUFFIXES:
            ignored.add(name)
    return ignored


def create_from_template(
    output_dir: str | os.PathLike[str],
    name: str,
    template_id: str,
    ide_root: str | os.PathLike[str] | None = None,
    *,
    configuration: str | None = None,
    platform: str | None = None,
) -> dict[str, Any]:
    """复制所选本地工程模板，保留其资源和自定义项目配置。"""
    project_name = project_core._valid_name(name)
    root = template_root(ide_root).resolve()
    source_project, metadata = _find_template(template_id, root)
    parent = Path(output_dir).expanduser().resolve()
    destination = parent / project_name
    project_core._check_copy_destination(source_project.parent, destination)
    if destination.exists() or (parent.is_dir() and any(item.name.casefold() == project_name.casefold()
                                                        for item in parent.iterdir())):
        raise TemplateError(f"工程目标目录已存在，拒绝覆盖：{destination}")
    staging_parent: Path | None = None
    try:
        parent.mkdir(parents=True, exist_ok=True)
        staging_parent = Path(tempfile.mkdtemp(prefix=f".{project_name}-xcide-template-", dir=parent))
        staged = staging_parent / project_name
        shutil.copytree(source_project.parent, staged, ignore=_copy_ignore)
        copied_project = staged / source_project.name
        tree = ET.parse(copied_project)
        project_node = tree.getroot()
        if project_node.tag != "project":
            raise TemplateError(f"工程模板根节点不是 <project>：{source_project}")
        vc = project_node.find("vc")
        selected_config = configuration or (vc.get("config") if vc is not None else None)
        selected_platform = platform or (vc.get("platform") if vc is not None else None)
        if vc is not None:
            setting = vc.find("setting")
            configs = {item.get("name"): item for item in setting.findall("config")} if setting is not None else {}
            if configuration and selected_config not in configs:
                raise TemplateError(f"模板 {metadata['id']} 没有编译配置 {configuration!r}；可选：{', '.join(configs)}")
            if selected_platform and selected_platform not in ("x86", "x64"):
                raise TemplateError("目前只支持 x86 和 x64 工程平台。")
            if platform and selected_config in configs and configs[selected_config].find(selected_platform) is None:
                raise TemplateError(f"模板配置 {selected_config!r} 不包含 {selected_platform} 平台节点。")
            if configuration:
                vc.set("config", selected_config or "")
            if platform:
                vc.set("platform", selected_platform or "")
        elif configuration or platform:
            raise TemplateError(f"模板 {metadata['id']} 不含标准 <vc> 设置，不能覆盖配置或架构。")
        name_node = project_node.get("name")
        if name_node is not None:
            project_node.set("name", project_name)
        tree.write(copied_project, encoding="utf-8", xml_declaration=True)
        new_project = staged / f"{project_name}.xcproj"
        if copied_project != new_project:
            if new_project.exists():
                raise TemplateError(f"模板目录中已存在目标工程文件名：{new_project.name}")
            copied_project.rename(new_project)
        if destination.exists() or any(item.name.casefold() == project_name.casefold()
                                       for item in parent.iterdir() if item != staging_parent):
            raise TemplateError(f"工程目标目录已存在，拒绝覆盖：{destination}")
        staged.rename(destination)
    except BaseException:
        if staging_parent is not None and staging_parent.exists():
            if staging_parent.resolve().parent == parent and staging_parent.name.startswith(f".{project_name}-xcide-template-"):
                shutil.rmtree(staging_parent)
        raise
    if staging_parent is not None:
        staging_parent.rmdir()
    result = project_core.inspect_project(destination / f"{project_name}.xcproj")
    result.update({"native_template": metadata["id"], "template_project": str(source_project),
                   "configuration_preserved": configuration is None,
                   "platform_preserved": platform is None})
    return result
