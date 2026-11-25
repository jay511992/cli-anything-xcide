"""直接扫描已安装模块库并维护 .xcproj 模块引用。"""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from cli_anything.xcide.core.project import (
    ProjectError, inspect_project, resolve_ide_root, _project_update, _atomic_project_xml,
)


class ModuleError(RuntimeError):
    """模块库或工程模块配置无效。"""


_SKIP_DIRS = {"obj", ".git", "doc", "lib", "x64", "x86", "vendor", "debug", "release"}
_DEP_SEPARATORS = re.compile(r"[,;\s\"]+")


def _roots(ide_root: str | os.PathLike[str] | None = None) -> list[tuple[str, Path]]:
    install = resolve_ide_root(ide_root)
    return [("XC-Module", install / "data" / "XC-Module"),
            ("XC-Module-dev", install / "data" / "XC-Module-dev")]


def _header(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        lines = raw.decode("utf-8-sig").splitlines()[:320]
    except UnicodeDecodeError:
        lines = raw.decode("gb18030", errors="replace").splitlines()[:320]
    data: dict[str, Any] = {"name": path.name, "version": "", "author": "", "remark": "", "deps": []}
    keys = {"//@模块名称": "name", "//@版本": "version", "//@作者": "author", "//@模块备注": "remark"}
    for raw_line in lines:
        line = raw_line.strip()
        if "//@模块信息结束" in line:
            break
        for marker, field in keys.items():
            if line.startswith(marker):
                value = line[len(marker):].strip()
                if field != "name" or value:
                    data[field] = value
                break
        else:
            if line.startswith("//@依赖"):
                data["deps"].extend(value for value in _DEP_SEPARATORS.split(line[len("//@依赖"):].strip())
                                    if value and value != "无")
    return data


def _project_modules(project: dict[str, Any]) -> set[str]:
    return {str(item.get("path", "")).casefold() for item in project.get("modules", [])}


def _module_filename(value: str) -> str:
    """Validate a module identifier as a file name rather than an arbitrary path."""
    filename = Path(value).name
    if (filename != value or "\\" in value or "/" in value
            or not filename.casefold().startswith("module_")
            or Path(filename).suffix.casefold() not in {".h", ".xc"}):
        raise ModuleError("模块需要准确的 module_*.h 或 module_*.xc 文件名，不能传入路径。")
    return filename


def _resolve_catalog_module(filename: str, catalog: list[dict[str, Any]]) -> dict[str, Any]:
    matches = [item for item in catalog if str(item["file"]).casefold() == filename.casefold()]
    if not matches:
        raise ModuleError(f"IDE 模块库中找不到依赖模块：{filename}")
    if len(matches) > 1:
        locations = ", ".join(str(item["relative_path"]) for item in matches)
        raise ModuleError(f"模块文件名不唯一，无法安全解析依赖 {filename}：{locations}")
    return matches[0]


def plan_module_dependencies(
    module_file: str,
    *,
    ide_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """生成依赖优先的模块引用计划，不修改工程或模块文件。"""
    filename = _module_filename(module_file)
    catalog = list_modules(ide_root=ide_root, limit=10000)["modules"]
    return _dependency_plan(filename, catalog)


def _dependency_plan(filename: str, catalog: list[dict[str, Any]]) -> dict[str, Any]:
    """根据已扫描模块目录构造依赖计划，避免复制前重复遍历安装包。"""
    root = _resolve_catalog_module(filename, catalog)
    ordered: list[dict[str, Any]] = []
    visited: set[str] = set()
    active: list[dict[str, Any]] = []
    cycles: list[list[str]] = []
    external: dict[tuple[str, str], dict[str, Any]] = {}
    unresolved: dict[str, None] = {}
    ambiguous: dict[str, list[str]] = {}
    index: dict[str, list[dict[str, Any]]] = {}
    for item in catalog:
        index.setdefault(str(item["file"]).casefold(), []).append(item)

    def visit(item: dict[str, Any]) -> None:
        path_key = str(Path(item["path"]).resolve()).casefold()
        if any(str(Path(value["path"]).resolve()).casefold() == path_key for value in active):
            start = next(i for i, value in enumerate(active)
                         if str(Path(value["path"]).resolve()).casefold() == path_key)
            cycle = [str(value["file"]) for value in active[start:]] + [str(item["file"])]
            if cycle not in cycles:
                cycles.append(cycle)
            return
        if path_key in visited:
            return
        active.append(item)
        for dependency in item.get("deps", []):
            dependency_file = Path(str(dependency).replace("\\", "/")).name
            suffix = Path(dependency_file).suffix.casefold()
            if dependency_file.casefold().startswith("module_") and suffix in {".h", ".xc"}:
                matches = index.get(dependency_file.casefold(), [])
                if not matches:
                    unresolved.setdefault(dependency_file, None)
                elif len(matches) > 1:
                    ambiguous[dependency_file] = sorted(str(value["relative_path"]) for value in matches)
                else:
                    visit(matches[0])
            else:
                key = (str(item["file"]).casefold(), str(dependency).casefold())
                external[key] = {"module": item["file"], "dependency": str(dependency),
                                 "sibling_exists": (Path(item["path"]).parent / dependency_file).is_file()}
        active.pop()
        visited.add(path_key)
        ordered.append(item)

    visit(root)
    diagnostics = []
    diagnostics.extend({"severity": "error", "code": "missing-module-dependency",
                         "message": f"找不到模块依赖 {name}"} for name in unresolved)
    diagnostics.extend({"severity": "error", "code": "ambiguous-module-dependency",
                         "message": f"依赖 {name} 在模块库中存在多个同名实现：{', '.join(paths)}"}
                       for name, paths in sorted(ambiguous.items()))
    diagnostics.extend({"severity": "warning", "code": "module-dependency-cycle",
                         "message": "模块依赖存在循环：" + " -> ".join(cycle)} for cycle in cycles)
    diagnostics.extend({"severity": "info", "code": "external-header-dependency",
                         "message": f"{item['module']} 依赖外部头文件 {item['dependency']}；不作为 IDE 模块加入。"}
                       for item in external.values())
    return {"ok": not unresolved and not ambiguous, "root": filename,
            "modules": [{"file": item["file"], "name": item["name"], "path": item["path"],
                         "library": item["library"], "relative_path": item["relative_path"],
                         "deps": item["deps"]} for item in ordered],
            "order": [str(item["file"]) for item in ordered],
            "module_count": len(ordered), "externalDependencies": list(external.values()),
            "cycles": cycles, "diagnostics": diagnostics}


def list_modules(
    *,
    ide_root: str | os.PathLike[str] | None = None,
    project_file: str | os.PathLike[str] | None = None,
    limit: int = 80,
    project_only: bool = False,
) -> dict[str, Any]:
    """递归列出模块库头文件并合并工程引用状态。"""
    if not 1 <= limit <= 10000:
        raise ModuleError("模块数量上限必须在 1 到 10000 之间。")
    project = inspect_project(project_file) if project_file else None
    project_names = _project_modules(project or {})
    installed = resolve_ide_root(ide_root)
    libraries = _roots(installed)
    modules: list[dict[str, Any]] = []
    scanned = 0
    if project_only:
        for item in (project or {}).get("modules", []):
            name = str(item.get("path", ""))
            modules.append({"file": name, "name": item.get("name") or name, "path": "",
                            "deps": [], "inProject": True})
    else:
        for root_name, root in libraries:
            if not root.is_dir():
                continue
            for current, directories, filenames in os.walk(root):
                directories[:] = sorted((name for name in directories if name.casefold() not in _SKIP_DIRS),
                                        key=str.casefold)
                for filename in sorted(filenames, key=str.casefold):
                    path = Path(current) / filename
                    if not filename.casefold().startswith("module_") or path.suffix.casefold() not in {".h", ".xc"}:
                        continue
                    scanned += 1
                    try:
                        metadata = _header(path)
                    except OSError:
                        continue
                    relative = path.relative_to(root).as_posix()
                    modules.append({"file": filename, **metadata, "path": str(path),
                                    "library": root_name, "relative_path": relative,
                                    "inProject": filename.casefold() in project_names})
                    if len(modules) >= limit:
                        break
                if len(modules) >= limit:
                    break
            if len(modules) >= limit:
                break
    return {"ok": True, "modules": modules, "count": len(modules), "totalScanned": scanned,
            "hasProject": project is not None, "project": project["project_file"] if project else None,
            "rootDir": str(libraries[0][1]), "devDir": str(libraries[1][1])}


def search_modules(
    query: str = "",
    *,
    ide_root: str | os.PathLike[str] | None = None,
    project_file: str | os.PathLike[str] | None = None,
    limit: int = 40,
    depends_on: str | None = None,
) -> dict[str, Any]:
    """按名称、文件名、备注、作者评分；也支持依赖反查。"""
    if not query and not depends_on:
        raise ModuleError("模块搜索需要 QUERY 或 --depends-on 参数。")
    catalog = list_modules(ide_root=ide_root, project_file=project_file, limit=10000)
    needle = query.casefold().strip()
    dependency = depends_on.casefold().strip() if depends_on else ""
    hits = []
    for module in catalog["modules"]:
        deps = [str(item) for item in module.get("deps", [])]
        if dependency:
            if not any(Path(dep).name.casefold() == Path(dependency).name.casefold() for dep in deps):
                continue
            score = 100
            matches = ["dependsOn"]
        else:
            score, matches = 0, []
            for field, weight, tag in (("name", 100, "name"), ("file", 80, "file"),
                                       ("remark", 40, "remark"), ("author", 10, "author")):
                value = str(module.get(field, "")).casefold()
                if needle and needle in value:
                    score = max(score, weight)
                    matches.append(tag)
            if score == 0:
                continue
        hits.append({**module, "score": score, "match": matches})
    hits.sort(key=lambda item: (-item["score"], str(item["name"]).casefold(), item["file"].casefold()))
    return {**catalog, "hits": hits[:limit], "count": len(hits[:limit]), "query": query,
            "dependsOn": depends_on or ""}


def _atomic_tree_write(path: Path, tree: ET.ElementTree) -> None:
    _atomic_project_xml(path, tree)


def add_module(
    project_file: str | os.PathLike[str],
    module_file: str,
    *,
    ide_root: str | os.PathLike[str] | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """将模块库中准确存在的模块文件名写入本地 .xcproj。"""
    filename = _module_filename(module_file)
    result = add_modules(project_file, [filename], ide_root=ide_root, name=name)
    added = next((item for item in result["addedModules"]
                  if item["file"].casefold() == filename.casefold()), None)
    return {"ok": True, "added": added is not None, "moduleCount": result["moduleCount"],
            "file": filename, "project": result["project"], "addedModules": result["addedModules"],
            "restartRequired": result["restartRequired"],
            **({"name": added["name"], "modulePath": added["modulePath"]} if added else {})}


@_project_update
def add_modules(
    project_file: str | os.PathLike[str],
    module_files: list[str],
    *,
    ide_root: str | os.PathLike[str] | None = None,
    with_dependencies: bool = False,
    name: str | None = None,
) -> dict[str, Any]:
    """在单次原子 XML 更新中添加一个或多个模块及其完整模块依赖。"""
    project = inspect_project(project_file)
    if not module_files:
        raise ModuleError("至少需要指定一个模块文件名。")
    filenames = []
    filename_keys: set[str] = set()
    for value in module_files:
        filename = _module_filename(value)
        if filename.casefold() not in filename_keys:
            filename_keys.add(filename.casefold())
            filenames.append(filename)
    catalog = list_modules(ide_root=ide_root, limit=10000)["modules"]
    selected: list[dict[str, Any]] = []
    dependency_plans: list[dict[str, Any]] = []
    external: dict[tuple[str, str], dict[str, Any]] = {}
    cycles: list[list[str]] = []
    requested_keys = {filename.casefold() for filename in filenames}
    for filename in filenames:
        if with_dependencies:
            plan = _dependency_plan(filename, catalog)
            dependency_plans.append(plan)
            failures = [item["message"] for item in plan["diagnostics"] if item["severity"] == "error"]
            if failures:
                raise ModuleError("；".join(failures))
            for item in plan["modules"]:
                if item["path"].casefold() not in {value["path"].casefold() for value in selected}:
                    selected.append(item)
            external.update({(item["module"].casefold(), item["dependency"].casefold()): item
                             for item in plan["externalDependencies"]})
            cycles.extend(cycle for cycle in plan["cycles"] if cycle not in cycles)
        else:
            selected.append(_resolve_catalog_module(filename, catalog))

    target = Path(project["project_file"])
    tree = ET.parse(target)
    root = tree.getroot()
    block = root.find("modules")
    if block is None:
        block = ET.SubElement(root, "modules")
    existing = {str(item.get("path", "")).casefold() for item in block.findall("item")}
    additions = []
    for item in selected:
        filename = str(item["file"])
        if filename.casefold() in existing:
            continue
        display_name = name if name and filename.casefold() in requested_keys else item["name"]
        ET.SubElement(block, "item", {"path": filename, "name": display_name})
        existing.add(filename.casefold())
        additions.append({"file": filename, "name": display_name, "modulePath": item["path"]})
    if additions:
        _atomic_tree_write(target, tree)
    if not with_dependencies:
        for filename in filenames:
            plan = _dependency_plan(filename, catalog)
            dependency_plans.append(plan)
            external.update({(item["module"].casefold(), item["dependency"].casefold()): item
                             for item in plan["externalDependencies"]})
            cycles.extend(cycle for cycle in plan["cycles"] if cycle not in cycles)
    return {"ok": True, "added": bool(additions), "moduleCount": len(block.findall("item")),
            "project": str(target), "addedModules": additions,
            "restartRequired": bool(additions), "dependencyOrder": [str(item["file"]) for item in selected],
            "dependencyPlans": dependency_plans,
            "externalDependencies": list(external.values()), "cycles": cycles}


@_project_update
def remove_module(project_file: str | os.PathLike[str], module_file: str) -> dict[str, Any]:
    """从本地 .xcproj 删除准确模块文件名对应的引用。"""
    project = inspect_project(project_file)
    filename = Path(module_file).name
    if filename != module_file:
        raise ModuleError("--file 只接受模块头文件名，不能传入路径。")
    target = Path(project["project_file"])
    tree = ET.parse(target)
    block = tree.getroot().find("modules")
    if block is None:
        return {"ok": True, "removed": False, "moduleCount": 0,
                "file": filename, "project": str(target)}
    found = [item for item in block.findall("item")
             if str(item.get("path", "")).casefold() == filename.casefold()]
    for item in found:
        block.remove(item)
    if found:
        _atomic_tree_write(target, tree)
    return {"ok": True, "removed": bool(found), "moduleCount": len(block.findall("item")),
            "file": filename, "project": str(target), "restartRequired": bool(found)}
