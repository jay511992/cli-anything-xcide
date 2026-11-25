"""对炫语言工程进行本地源码、模块和布局一致性体检。"""

from __future__ import annotations

import os
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

from cli_anything.xcide.core import interface, modules
from cli_anything.xcide.core.project import inspect_project


_IGNORED_DIRS = {".git", ".cli-anything", "__pycache__", "debug", "debug64", "release", "release64", "obj", "x64", "x86"}


def _source_files(project_dir: Path) -> set[str]:
    found: set[str] = set()
    for current, directories, filenames in os.walk(project_dir):
        directories[:] = [name for name in directories if name.casefold() not in _IGNORED_DIRS]
        for filename in filenames:
            found.add((Path(current) / filename).relative_to(project_dir).as_posix().casefold())
    return found


def inspect_project_health(
    project_file: str | os.PathLike[str], *, ide_root: str | os.PathLike[str] | None = None,
    include_generated: bool = False,
) -> dict[str, Any]:
    """核对入口源码、模块引用、布局 XML 和本地界面归档。"""
    project = inspect_project(project_file)
    project_dir = Path(project["directory"])
    files = _source_files(project_dir)
    diagnostics: list[dict[str, str]] = []

    entries = [str(item.get("file", "")).replace("\\", "/") for item in project.get("files", [])]
    entry_counts = Counter(item.casefold() for item in entries if item)
    for entry, count in sorted(entry_counts.items()):
        if count > 1:
            diagnostics.append({"severity": "warning", "code": "duplicate-source-entry", "path": project["project_file"],
                                "message": f"<codeExpand> 中源码条目重复 {count} 次：{entry}"})
    source_missing = []
    for entry in entries:
        candidate = PurePosixPath(entry)
        if not entry or candidate.is_absolute() or ".." in candidate.parts:
            diagnostics.append({"severity": "error", "code": "unsafe-source-entry", "path": project["project_file"],
                                "message": f"<codeExpand> 源码路径必须是工程内相对路径：{entry!r}"})
            continue
        if entry.casefold() not in files:
            source_missing.append(entry)
            diagnostics.append({"severity": "error", "code": "missing-source-entry", "path": project["project_file"],
                                "message": f"工程登记的源码文件不存在：{entry}"})

    try:
        catalog = modules.list_modules(ide_root=ide_root, limit=10000)
        installed: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in catalog["modules"]:
            installed[str(item["file"]).casefold()].append(item)
    except (modules.ModuleError, FileNotFoundError, OSError) as exc:
        installed = {}
        diagnostics.append({"severity": "warning", "code": "module-catalog-unavailable", "path": str(project_dir),
                            "message": f"无法扫描所选 IDE 模块库：{exc}"})
    module_missing: list[str] = []
    ambiguous_modules: list[str] = []
    for item in project.get("modules", []):
        name = str(item.get("path", ""))
        matches = installed.get(Path(name).name.casefold(), [])
        if not matches:
            module_missing.append(name)
            diagnostics.append({"severity": "error", "code": "missing-module", "path": project["project_file"],
                                "message": f"工程引用模块不在所选 IDE 的已安装模块库中：{name}"})
        elif len(matches) > 1:
            ambiguous_modules.append(name)
            locations = ", ".join(value["relative_path"] for value in matches)
            diagnostics.append({"severity": "warning", "code": "ambiguous-module", "path": project["project_file"],
                                "message": f"模块文件名在模块库中重复，存在多个实现：{name} ({locations})"})

    ui = interface.inspect_interface(project["project_file"], include_generated=include_generated)
    diagnostics.extend(ui["diagnostics"])
    error_count = sum(item["severity"] == "error" for item in diagnostics)
    warning_count = sum(item["severity"] == "warning" for item in diagnostics)
    return {
        "ok": error_count == 0,
        "project": project,
        "checks": {"sourceEntryCount": len(entries), "missingSourceCount": len(source_missing),
                   "moduleReferenceCount": len(project.get("modules", [])), "missingModuleCount": len(module_missing),
                   "ambiguousModuleCount": len(ambiguous_modules), "layoutCount": ui["layoutCount"],
                   "validLayoutCount": ui["validLayoutCount"], "uiZipCount": ui["uiZipCount"],
                   "validUiZipCount": ui["validUiZipCount"]},
        "errorCount": error_count, "warningCount": warning_count, "diagnostics": diagnostics,
    }
