"""浏览、检查并派生炫彩 IDE 安装包中的炫语言示例工程。"""

from __future__ import annotations

import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterator

from cli_anything.xcide.core import project as project_core


EXAMPLE_RELATIVE = Path("data") / "示例"
_SKIP_DIRS = {".git", ".svn", ".cli-anything", "__pycache__", ".vs", "ipch",
              "debug", "debug64", "release", "release64", "obj", "x64", "x86"}
_SKIP_SUFFIXES = {".exe", ".obj", ".pdb", ".ilk", ".pch", ".idb", ".ipch"}


class ExampleError(ValueError):
    """IDE 示例路径无效、工程损坏或目标冲突。"""


def example_root(ide_root: str | os.PathLike[str] | None = None) -> Path:
    """返回所选 IDE 安装包中的真实示例工程目录。"""
    root = project_core.resolve_ide_root(ide_root) / EXAMPLE_RELATIVE
    if not root.is_dir():
        raise ExampleError(f"炫彩 IDE 示例目录不存在：{root}")
    return root.resolve()


def _walk_files(directory: Path) -> Iterator[Path]:
    """遍历源码和资源；跳过编译输出及符号链接目录/文件。"""
    for current, directories, filenames in os.walk(directory, followlinks=False):
        here = Path(current)
        directories[:] = sorted((name for name in directories
                                 if name.casefold() not in _SKIP_DIRS
                                 and not (here / name).is_symlink()), key=str.casefold)
        for filename in sorted(filenames, key=str.casefold):
            path = here / filename
            if path.is_symlink() or path.suffix.casefold() in _SKIP_SUFFIXES:
                continue
            yield path


def _metadata(path: Path, root: Path) -> dict[str, Any]:
    try:
        tree = ET.parse(path)
    except (OSError, ET.ParseError) as exc:
        raise ExampleError(f"无法解析炫语言示例工程 {path}：{exc}") from exc
    node = tree.getroot()
    if node.tag != "project":
        raise ExampleError(f"工程 XML 必须使用 <project> 根节点：{path}")
    vc = node.find("vc")
    setting = vc.find("setting") if vc is not None else None
    configurations = [item.get("name", "") for item in setting.findall("config")] if setting is not None else []
    return {
        "id": path.relative_to(root).as_posix(),
        "name": node.get("name") or path.stem,
        "category": path.parent.relative_to(root).as_posix(),
        "project_file": str(path.resolve()),
        "directory": str(path.parent.resolve()),
        "configuration": vc.get("config") if vc is not None else None,
        "platform": vc.get("platform") if vc is not None else None,
        "configurations": configurations,
        "module_count": len(node.findall("./modules/item")),
        "declared_file_count": len(node.findall("./codeExpand/item")),
    }


def list_examples(
    *, ide_root: str | os.PathLike[str] | None = None, query: str = "", limit: int = 200,
) -> dict[str, Any]:
    """按本地相对 ID、名称和分类搜索 IDE 随附的原生工程。"""
    if not 1 <= limit <= 2000:
        raise ExampleError("示例结果上限必须在 1 到 2000 之间。")
    root = example_root(ide_root)
    needle = query.strip().casefold()
    examples: list[dict[str, Any]] = []
    for current, directories, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        directories[:] = sorted((name for name in directories
                                 if name.casefold() not in _SKIP_DIRS
                                 and not (current_path / name).is_symlink()), key=str.casefold)
        for filename in sorted(filenames, key=str.casefold):
            path = current_path / filename
            if path.is_symlink() or path.suffix.casefold() != ".xcproj":
                continue
            try:
                entry = _metadata(path, root)
            except ExampleError as exc:
                entry = {"id": path.relative_to(root).as_posix(), "name": path.stem,
                         "category": path.parent.relative_to(root).as_posix(),
                         "project_file": str(path.resolve()), "valid": False, "error": str(exc)}
            else:
                entry["valid"] = True
            haystack = " ".join((entry["id"], entry["name"], entry["category"])).casefold()
            if needle and needle not in haystack:
                continue
            examples.append(entry)
    examples.sort(key=lambda item: item["id"].casefold())
    selected = examples[:limit]
    return {"ok": True, "root": str(root), "count": len(selected), "total": len(examples),
            "truncated": len(examples) > len(selected), "query": query, "examples": selected}


def _find_example(identifier: str, root: Path) -> tuple[Path, dict[str, Any]]:
    normalized = identifier.replace("\\", "/")
    parts = normalized.split("/")
    if (not normalized or normalized.startswith("/") or ":" in normalized
            or any(part in ("", ".", "..") for part in parts)
            or not normalized.casefold().endswith(".xcproj")):
        raise ExampleError("示例 ID 必须是 example list 返回的相对 .xcproj 路径。")
    candidates = []
    for current, directories, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        directories[:] = [name for name in directories
                          if name.casefold() not in _SKIP_DIRS and not (current_path / name).is_symlink()]
        for filename in filenames:
            path = current_path / filename
            if path.suffix.casefold() != ".xcproj" or path.is_symlink():
                continue
            if path.relative_to(root).as_posix().casefold() == normalized.casefold():
                candidates.append(path)
    if len(candidates) != 1:
        raise ExampleError(f"找不到准确的本地炫语言示例 ID：{identifier}")
    path = candidates[0].resolve()
    if not path.is_relative_to(root):
        raise ExampleError("示例工程路径越过了炫彩 IDE 示例目录。")
    return path, _metadata(path, root)


def inspect_example(identifier: str, *, ide_root: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """返回示例工程的配置、模块、入口登记和可复制文件清单。"""
    root = example_root(ide_root)
    project_file, metadata = _find_example(identifier, root)
    project = project_core.inspect_project(project_file)
    files = []
    for path in _walk_files(project_file.parent):
        files.append({"path": path.relative_to(project_file.parent).as_posix(), "bytes": path.stat().st_size})
    files.sort(key=lambda item: item["path"].casefold())
    return {"ok": True, **metadata, "project": project,
            "files": files, "file_count": len(files),
            "entrypoints": project["files"], "modules": project["modules"]}


def copy_example(
    output_dir: str | os.PathLike[str], name: str, identifier: str,
    *, ide_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """把示例安全复制到新目录，重命名工程 XML 并清除已生成构建文件。"""
    project_name = project_core._valid_name(name)
    root = example_root(ide_root)
    source_project, metadata = _find_example(identifier, root)
    parent = Path(output_dir).expanduser().resolve()
    if parent == root or root in parent.parents:
        raise ExampleError(f"不能把派生工程写入 IDE 安装包的示例目录内：{parent}")
    destination = parent / project_name
    if destination.exists() or (parent.is_dir() and any(
            entry.name.casefold() == project_name.casefold() for entry in parent.iterdir())):
        raise ExampleError(f"工程目标目录已存在，拒绝覆盖：{destination}")

    staging_parent: Path | None = None
    try:
        parent.mkdir(parents=True, exist_ok=True)
        staging_parent = Path(tempfile.mkdtemp(prefix=f".{project_name}-xcide-example-", dir=parent))
        staged = staging_parent / project_name
        shutil.copytree(source_project.parent, staged, ignore=_copy_ignore)
        copied_project = staged / source_project.name
        tree = ET.parse(copied_project)
        project_node = tree.getroot()
        if project_node.tag != "project":
            raise ExampleError(f"示例工程根节点不是 <project>：{source_project}")
        project_node.set("name", project_name)
        tree.write(copied_project, encoding="utf-8", xml_declaration=True)
        new_project = staged / f"{project_name}.xcproj"
        if copied_project != new_project:
            if new_project.exists():
                raise ExampleError(f"示例中已存在目标工程文件名：{new_project.name}")
            copied_project.rename(new_project)
        if destination.exists() or any(entry.name.casefold() == project_name.casefold()
                                       for entry in parent.iterdir() if entry != staging_parent):
            raise ExampleError(f"工程目标目录已存在，拒绝覆盖：{destination}")
        staged.rename(destination)
    except BaseException:
        if (staging_parent is not None and staging_parent.exists()
                and staging_parent.resolve().parent == parent
                and staging_parent.name.startswith(f".{project_name}-xcide-example-")):
            shutil.rmtree(staging_parent)
        raise
    if staging_parent is not None:
        staging_parent.rmdir()

    result = project_core.inspect_project(destination / f"{project_name}.xcproj")
    copied_files = list(_walk_files(destination))
    result.update({"native_example": metadata["id"], "example_project": str(source_project),
                   "copied_file_count": len(copied_files),
                   "excluded_build_artifacts": True})
    return result


def _copy_ignore(_directory: str, names: list[str]) -> set[str]:
    """让 copytree 仅保留源码、资源和工程文件，跳过符号链接及编译产物。"""
    ignored: set[str] = set()
    for name in names:
        path = Path(_directory) / name
        if path.is_symlink() or name.casefold() in _SKIP_DIRS or path.suffix.casefold() in _SKIP_SUFFIXES:
            ignored.add(name)
    return ignored
