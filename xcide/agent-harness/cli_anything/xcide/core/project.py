"""Create, inspect, and safely locate native XCGUI IDE projects."""

from __future__ import annotations

import os
import hashlib
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
from contextvars import ContextVar
from functools import wraps
from pathlib import Path
from typing import Any

from filelock import FileLock


PROJECT_FILE = "template.xcproj"
TEMPLATE_RELATIVE = Path("data") / "template" / "项目模板" / "炫语言" / "空白窗口程序" / "空白窗口程序" / "project"
_NAME = re.compile(r"^[^<>:\"/\\|?*\x00-\x1f.]+$")


class ProjectError(ValueError):
    """An invalid or missing native IDE project or template."""


_PROJECT_SNAPSHOT: ContextVar[tuple[Path, bytes] | None] = ContextVar("xcide_project_snapshot", default=None)


def _project_update(function):
    """Serialize the complete read/modify/write operation for one project."""
    @wraps(function)
    def wrapped(project_file, *args, **kwargs):
        path = Path(project_file).expanduser().resolve()
        current = _PROJECT_SNAPSHOT.get()
        if current is not None and current[0] == path:
            return function(path, *args, **kwargs)
        identity = hashlib.sha256(os.path.normcase(str(path)).encode("utf-8")).hexdigest()
        lock_dir = Path(tempfile.gettempdir()) / "cli-anything-xcide-locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        with FileLock(str(lock_dir / (identity + ".lock")), timeout=15):
            token = _PROJECT_SNAPSHOT.set((path, path.read_bytes()))
            try:
                return function(path, *args, **kwargs)
            finally:
                _PROJECT_SNAPSHOT.reset(token)
    return wrapped


def _check_project_unchanged(path: Path) -> None:
    snapshot = _PROJECT_SNAPSHOT.get()
    if snapshot is not None and snapshot[0] == path:
        if not path.is_file() or path.read_bytes() != snapshot[1]:
            raise ProjectError(f"工程在操作期间被外部程序修改，已取消写入，请重新读取：{path}")


def _check_copy_destination(source: Path, destination: Path) -> None:
    if destination.resolve().is_relative_to(source.resolve()):
        raise ProjectError(f"不能把工程复制到源模板目录内部：{destination}")


def resolve_ide_root(ide_root: str | os.PathLike[str] | None = None) -> Path:
    """Resolve and verify the installation containing the native IDE executable."""
    explicit = ide_root or os.environ.get("XC_IDE_ROOT")
    if explicit:
        root = Path(explicit).expanduser().resolve()
        if not (root / "炫彩IDE.exe").is_file():
            raise ProjectError(f"The selected XC_IDE_ROOT does not contain 炫彩IDE.exe: {root}")
        return root
    candidates = []
    env_root = os.environ.get("XC_IDE_ROOT")
    if env_root:
        candidates.append(env_root)
    candidates.extend((r"I:\xcide", r"I:\炫彩ide", r"I:\炫彩IDE"))
    for candidate in candidates:
        if candidate:
            root = Path(candidate).expanduser().resolve()
            if (root / "炫彩IDE.exe").is_file():
                return root
    raise ProjectError("Could not find 炫彩IDE.exe; supply --ide or set XC_IDE_ROOT.")


def native_template_dir(ide_root: str | os.PathLike[str] | None = None) -> Path:
    """Find the blank-window project template shipped with the selected IDE."""
    root = resolve_ide_root(ide_root)
    template = root / TEMPLATE_RELATIVE
    for required in (PROJECT_FILE, "main.xc", "common.xh", "exe.rc"):
        if not (template / required).is_file():
            raise ProjectError(f"The installed blank-window template is incomplete: {template} (missing {required}).")
    return template


def _valid_name(name: str) -> str:
    candidate = name.strip()
    if candidate != name or candidate in ("", ".", "..") or not _NAME.fullmatch(candidate):
        raise ProjectError("Project name must be a valid single Windows filename without an extension.")
    if candidate.endswith((" ", ".")) or candidate.upper() in {"CON", "PRN", "AUX", "NUL"} or re.fullmatch(
        r"(?:COM|LPT)[1-9¹²³]", candidate.upper()
    ):
        raise ProjectError(f"{candidate!r} is not a supported Windows project directory name.")
    return candidate


def create_project(
    output_dir: str | os.PathLike[str],
    name: str,
    ide_root: str | os.PathLike[str] | None = None,
    *,
    configuration: str = "发布版",
    platform: str = "x64",
) -> dict[str, Any]:
    """Copy the real shipped template and retarget its project metadata."""
    project_name = _valid_name(name)
    if configuration not in ("发布版", "调试版") or platform not in ("x64", "x86"):
        raise ProjectError("Choose configuration 发布版 or 调试版 and platform x64 or x86.")
    parent = Path(output_dir).expanduser().resolve()
    destination = parent / project_name
    if destination.exists():
        raise ProjectError(f"Project destination already exists; refusing to overwrite: {destination}")
    template = native_template_dir(ide_root)
    _check_copy_destination(template, destination)
    installation_root = resolve_ide_root(ide_root)
    project_file = destination / (project_name + ".xcproj")
    staging_parent: Path | None = None
    staging_root: Path | None = None
    try:
        parent.mkdir(parents=True, exist_ok=True)
        staging_parent = Path(tempfile.mkdtemp(prefix="." + project_name + "-cli-anything-", dir=parent))
        staged_project = staging_parent / project_name
        shutil.copytree(template, staged_project)
        original = staged_project / PROJECT_FILE
        tree = ET.parse(original)
        root = tree.getroot()
        root.set("name", project_name)
        vc = root.find("vc")
        if vc is None:
            raise ProjectError("The installed template has no <vc> configuration element.")
        vc.set("config", configuration)
        vc.set("platform", platform)
        ide_config_path = installation_root / "data" / "config" / "config.config"
        sdk = "Windows7"
        toolset = "vs2015"
        if ide_config_path.is_file():
            try:
                ide_config = ET.parse(ide_config_path).getroot()
                sdk_node = ide_config.find("vcDefaultSdk")
                toolset_node = ide_config.find("vcDefaultPlatformToolset")
                sdk = sdk_node.get("value", sdk) if sdk_node is not None else sdk
                toolset = toolset_node.get("value", toolset) if toolset_node is not None else toolset
            except ET.ParseError:
                pass
        expected_sdk = sdk
        expected_toolset = toolset
        settings = vc.find("setting")
        if settings is None:
            raise ProjectError("The installed template has no <vc><setting> configurations.")
        for config in settings.findall("config"):
            if config.get("name") == configuration:
                for architecture in ("x64", "x86"):
                    arch_node = config.find(architecture)
                    common = arch_node.find("common") if arch_node is not None else None
                    if common is not None:
                        common.set("sdk", expected_sdk)
                        common.set("platformToolset", expected_toolset)
        code = root.find("codeExpand")
        if code is None:
            code = ET.SubElement(root, "codeExpand")
        if not any(item.get("file", "").replace("/", "\\").casefold() == "main.xc"
                   for item in code.findall("item")):
            ET.SubElement(code, "item", {"file": "main.xc", "state": "1,"})
        tree.write(original, encoding="utf-8", xml_declaration=True)
        activate_source(original)
        original.rename(staged_project / (project_name + ".xcproj"))
        if destination.exists() or any(entry.name.casefold() == project_name.casefold()
                                       for entry in parent.iterdir()):
            raise ProjectError(f"Project destination already exists; refusing to overwrite: {destination}")
        staged_project.rename(destination)
        staging_root = staging_parent
    except BaseException:
        if staging_parent is not None and staging_parent.exists():
            # Only our mkdtemp child of the verified output parent is removable.
            if staging_parent.resolve().parent == parent and staging_parent.name.startswith("." + project_name + "-cli-anything-"):
                shutil.rmtree(staging_parent)
        raise
    if staging_root is not None:
        staging_root.rmdir()
    result = inspect_project(project_file)
    result["native_template"] = "XCGUI IDE official blank-window project template"
    result["configuration_defaults_source"] = str(ide_config_path)
    return result


def inspect_project(project_file: str | os.PathLike[str]) -> dict[str, Any]:
    """Read project configuration, listed sources, module references, and paths."""
    path = Path(project_file).expanduser().resolve()
    if path.suffix.lower() != ".xcproj" or not path.is_file():
        raise ProjectError(f"Native .xcproj file does not exist: {path}")
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        raise ProjectError(f"Could not parse project XML {path}: {exc}") from exc
    root = tree.getroot()
    if root.tag != "project":
        raise ProjectError(f"Native project XML must use a <project> root element: {path}")
    vc = root.find("vc")
    modules = root.find("modules")
    files = root.find("codeExpand")
    if files is None:
        files = root.find("files")
    active_config = None
    setting = vc.find("setting") if vc is not None else None
    if setting is not None:
        active_config = next((item for item in setting.findall("config")
                              if item.get("name") == vc.get("config", "")), None)
    common = active_config.find(vc.get("platform", "x64")) if active_config is not None and vc is not None else None
    common = common.find("common") if common is not None else None
    return {
        "name": root.get("name") or path.stem,
        "project_file": str(path),
        "directory": str(path.parent),
        "configuration": vc.get("config") if vc is not None else None,
        "platform": vc.get("platform") if vc is not None else None,
        "module_library": vc.get("moduleLib") if vc is not None else None,
        "platform_toolset": common.get("platformToolset") if common is not None else None,
        "sdk": common.get("sdk") if common is not None else None,
        "modules": [dict(item.attrib) for item in modules.findall("item")] if modules is not None else [],
        "files": [dict(item.attrib) for item in files.findall("item")] if files is not None else [],
        "entrypoints": sorted(item.name for item in path.parent.glob("*.xc")),
    }


def list_configurations(project_file: str | os.PathLike[str]) -> dict[str, Any]:
    """列出工程真实声明的编译配置、可用架构和关键工具链参数。"""
    path = Path(inspect_project(project_file)["project_file"])
    root = ET.parse(path).getroot()
    vc = root.find("vc")
    setting = vc.find("setting") if vc is not None else None
    if vc is None or setting is None:
        raise ProjectError(f"工程没有标准 <vc><setting> 编译配置：{path}")
    configurations = []
    for config in setting.findall("config"):
        architectures = []
        for platform in ("x86", "x64"):
            platform_node = config.find(platform)
            if platform_node is None:
                continue
            common = platform_node.find("common")
            output = platform_node.find("out")
            architectures.append({"platform": platform,
                                  "active": config.get("name") == vc.get("config") and platform == vc.get("platform"),
                                  "common": dict(common.attrib) if common is not None else {},
                                  "output": dict(output.attrib) if output is not None else {}})
        configurations.append({"name": config.get("name", ""),
                                "active": config.get("name") == vc.get("config"),
                                "platforms": architectures})
    return {"project_file": str(path), "active_configuration": vc.get("config"),
            "active_platform": vc.get("platform"), "configurations": configurations}


@_project_update
def set_configuration(
    project_file: str | os.PathLike[str],
    *,
    configuration: str | None = None,
    platform: str | None = None,
) -> dict[str, Any]:
    """切换工程现有的编译配置/架构，保留 XML 中其他项目状态。"""
    if configuration is None and platform is None:
        raise ProjectError("至少指定 --configuration 或 --platform。")
    if platform is not None and platform not in {"x86", "x64"}:
        raise ProjectError("工程架构只能是 x86 或 x64。")
    info = inspect_project(project_file)
    path = Path(info["project_file"])
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        raise ProjectError(f"无法解析工程 XML {path}：{exc}") from exc
    root = tree.getroot()
    vc = root.find("vc")
    setting = vc.find("setting") if vc is not None else None
    if vc is None or setting is None:
        raise ProjectError(f"工程没有标准 <vc><setting> 编译配置：{path}")
    selected_configuration = configuration if configuration is not None else vc.get("config", "")
    selected_platform = platform if platform is not None else vc.get("platform", "x64")
    matching = [item for item in setting.findall("config") if item.get("name") == selected_configuration]
    if len(matching) != 1:
        choices = [item.get("name", "") for item in setting.findall("config")]
        raise ProjectError(f"工程配置 {selected_configuration!r} 必须唯一存在；可选：{', '.join(choices)}")
    if matching[0].find(selected_platform) is None:
        choices = [item.tag for item in matching[0] if item.tag in {"x86", "x64"}]
        raise ProjectError(f"配置 {selected_configuration!r} 没有 {selected_platform} 架构；可选：{', '.join(choices)}")
    before = {"configuration": vc.get("config"), "platform": vc.get("platform")}
    if before != {"configuration": selected_configuration, "platform": selected_platform}:
        vc.set("config", selected_configuration)
        vc.set("platform", selected_platform)
        _atomic_project_xml(path, tree)
    after = {"configuration": selected_configuration, "platform": selected_platform}
    return {"ok": True, "project_file": str(path), "before": before, "after": after,
            "changed": before != after, **inspect_project(path)}


_GENERATED_DIRS = {".git", ".svn", ".cli-anything", "__pycache__", ".vs", "debug", "debug64",
                   "release", "release64", "obj", "x64", "x86", "bin", "build", "dist"}


def _project_relative_file(project_file: str | os.PathLike[str], relative_path: str, *,
                           suffixes: set[str], must_exist: bool = True) -> tuple[Path, Path]:
    """Resolve a safe existing project-relative source file."""
    project = Path(inspect_project(project_file)["project_file"])
    candidate = Path(relative_path.replace("\\", "/"))
    if (not relative_path or candidate.is_absolute() or ":" in relative_path
            or ".." in candidate.parts or candidate.suffix.casefold() not in suffixes):
        extensions = ", ".join(sorted(suffixes))
        raise ProjectError(f"文件必须是工程内相对路径，且扩展名属于 {extensions}：{relative_path!r}")
    resolved = (project.parent / candidate).resolve()
    if not resolved.is_relative_to(project.parent) or (must_exist and not resolved.is_file()):
        raise ProjectError(f"工程内文件不存在或路径越界：{relative_path}")
    return project, resolved if must_exist else project.parent / candidate


def _atomic_project_xml(path: Path, tree: ET.ElementTree) -> None:
    """Atomically replace a native .xcproj after serializing XML to a sibling temp file."""
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.cli-anything-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            tree.write(handle, encoding="utf-8", xml_declaration=True)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.chmod(temporary, path.stat().st_mode)
        except OSError:
            pass
        _check_project_unchanged(path)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def list_project_sources(project_file: str | os.PathLike[str]) -> dict[str, Any]:
    """List project-local .xc/.xcs source files and whether each is in codeExpand."""
    info = inspect_project(project_file)
    root = Path(info["directory"])
    registered = {str(item.get("file", "")).replace("\\", "/").casefold()
                  for item in info["files"] if item.get("file")}
    sources = []
    for current, directories, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        directories[:] = sorted((name for name in directories
                                 if name.casefold() not in _GENERATED_DIRS
                                 and not (current_path / name).is_symlink()), key=str.casefold)
        for filename in sorted(filenames, key=str.casefold):
            path = current_path / filename
            if path.is_symlink() or path.suffix.casefold() not in {".xc", ".xcs"}:
                continue
            relative = path.relative_to(root).as_posix()
            sources.append({"file": relative, "bytes": path.stat().st_size,
                            "registered": relative.casefold() in registered})
    sources.sort(key=lambda item: item["file"].casefold())
    return {"project_file": info["project_file"], "source_count": len(sources),
            "registered_count": sum(item["registered"] for item in sources),
            "sources": sources, "registered_entries": info["files"]}


@_project_update
def add_project_source(project_file: str | os.PathLike[str], relative_path: str) -> dict[str, Any]:
    """Register an existing .xc/.xcs file under project <codeExpand> without copying it."""
    project, source = _project_relative_file(project_file, relative_path, suffixes={".xc", ".xcs"})
    normalized = source.relative_to(project.parent).as_posix().replace("/", "\\")
    tree = ET.parse(project)
    root = tree.getroot()
    block = root.find("codeExpand")
    if block is None:
        block = root.find("files")
    if block is None:
        block = ET.SubElement(root, "codeExpand")
    existing = next((item for item in block.findall("item")
                     if str(item.get("file", "")).replace("/", "\\").casefold() == normalized.casefold()), None)
    if existing is not None:
        return {"ok": True, "added": False, "project_file": str(project),
                "source": str(source), "file": normalized, "files": [dict(item.attrib) for item in block.findall("item")]}
    ET.SubElement(block, "item", {"file": normalized, "state": "1,"})
    _atomic_project_xml(project, tree)
    return {"ok": True, "added": True, "project_file": str(project), "source": str(source),
            "file": normalized, "files": [dict(item.attrib) for item in block.findall("item")]}


@_project_update
def remove_project_source(project_file: str | os.PathLike[str], relative_path: str) -> dict[str, Any]:
    """Remove a project source-tree registration without deleting its source file."""
    project = Path(inspect_project(project_file)["project_file"])
    candidate = Path(relative_path.replace("\\", "/"))
    if (not relative_path or candidate.is_absolute() or ":" in relative_path or ".." in candidate.parts
            or candidate.suffix.casefold() not in {".xc", ".xcs"}):
        raise ProjectError(f"待取消登记的源码必须是工程内相对 .xc/.xcs 路径：{relative_path!r}")
    normalized = candidate.as_posix().replace("/", "\\")
    tree = ET.parse(project)
    block = tree.getroot().find("codeExpand")
    if block is None:
        block = tree.getroot().find("files")
    if block is None:
        return {"ok": True, "removed": False, "project_file": str(project),
                "file": normalized, "source_deleted": False}
    matches = [item for item in block.findall("item")
               if str(item.get("file", "")).replace("/", "\\").casefold() == normalized.casefold()]
    for item in matches:
        block.remove(item)
    if matches:
        _atomic_project_xml(project, tree)
    return {"ok": True, "removed": bool(matches), "project_file": str(project),
            "file": normalized, "source_deleted": False,
            "files": [dict(item.attrib) for item in block.findall("item")]}


def list_project_breakpoints(project_file: str | os.PathLike[str]) -> dict[str, Any]:
    """Read breakpoint metadata stored in a native .xcproj without opening the IDE."""
    info = inspect_project(project_file)
    project = Path(info["project_file"])
    root = ET.parse(project).getroot()
    files = []
    diagnostics = []
    block = root.find("breakpoints")
    if block is not None:
        for file_node in block.findall("file"):
            relative = str(file_node.get("value", ""))
            try:
                _project, source = _project_relative_file(project, relative, suffixes={".xc", ".xcs"})
                line_count = len(source.read_bytes().splitlines())
                valid = True
            except (ProjectError, OSError):
                line_count = None
                valid = False
                diagnostics.append({"severity": "warning", "code": "missing-breakpoint-source",
                                    "file": relative, "message": f"断点对应源码不存在或路径无效：{relative}"})
            lines = []
            for item in file_node.findall("item"):
                try:
                    number = int(item.get("lineno", "0"))
                except ValueError:
                    number = 0
                line_valid = valid and line_count is not None and 1 <= number <= line_count
                lines.append({"line": number if number > 0 else None, "valid": line_valid})
                if not line_valid:
                    diagnostics.append({"severity": "warning", "code": "invalid-breakpoint-line",
                                        "file": relative, "message": f"断点行号超出源码范围或无效：{relative}:{number}"})
            files.append({"file": relative, "line_count": line_count, "breakpoints": lines})
    return {"project_file": str(project), "breakpoint_count": sum(len(item["breakpoints"]) for item in files),
            "files": files, "diagnostics": diagnostics}


@_project_update
def set_project_breakpoint(project_file: str | os.PathLike[str], relative_path: str, line: int, *,
                           remove: bool = False) -> dict[str, Any]:
    """Add or remove a line breakpoint in .xcproj after validating the project source and line range."""
    if line < 1:
        raise ProjectError("断点行号从 1 开始。")
    project, source = _project_relative_file(project_file, relative_path, suffixes={".xc", ".xcs"},
                                              must_exist=not remove)
    if not remove:
        line_count = len(source.read_bytes().splitlines())
        if line > line_count:
            raise ProjectError(f"断点行号超出源码范围：{line}，文件共 {line_count} 行。")
    normalized = source.relative_to(project.parent).as_posix().replace("/", "\\")
    tree = ET.parse(project)
    root = tree.getroot()
    block = root.find("breakpoints")
    if block is None:
        block = ET.SubElement(root, "breakpoints")
    file_node = next((item for item in block.findall("file")
                      if str(item.get("value", "")).replace("/", "\\").casefold() == normalized.casefold()), None)
    if remove:
        if file_node is None:
            return {"ok": True, "changed": False, "removed": False, "project_file": str(project),
                    "file": normalized, "line": line}
        matches = [item for item in file_node.findall("item") if item.get("lineno") == str(line)]
        for item in matches:
            file_node.remove(item)
        if not file_node.findall("item"):
            block.remove(file_node)
        changed = bool(matches)
    else:
        if file_node is None:
            file_node = ET.SubElement(block, "file", {"value": normalized})
        exists = any(item.get("lineno") == str(line) for item in file_node.findall("item"))
        if exists:
            return {"ok": True, "changed": False, "added": False, "project_file": str(project),
                    "file": normalized, "line": line}
        ET.SubElement(file_node, "item", {"lineno": str(line)})
        changed = True
    if changed:
        _atomic_project_xml(project, tree)
    return {"ok": True, "changed": changed, "added": changed and not remove,
            "removed": changed and remove, "project_file": str(project), "file": normalized, "line": line}


def list_project_debug_metadata(project_file: str | os.PathLike[str]) -> dict[str, Any]:
    """Read persisted watches, bookmarks and breakpoints from a native project file."""
    info = inspect_project(project_file)
    root = ET.parse(info["project_file"]).getroot()
    watches_node = root.find("watches")
    watches = [dict(item.attrib) for item in watches_node.iter("item")] if watches_node is not None else []
    bookmarks_node = root.find("bookmarks")
    bookmarks = []
    if bookmarks_node is not None:
        for file_node in bookmarks_node.findall("file"):
            bookmarks.extend({"file": file_node.get("value", ""), **item.attrib}
                             for item in file_node.findall("item"))
    return {"project_file": info["project_file"], "watches": watches,
            "bookmarks": bookmarks, "breakpoints": list_project_breakpoints(project_file)}


@_project_update
def set_project_debug_item(
    project_file: str | os.PathLike[str],
    kind: str,
    value: str,
    *,
    line: int | None = None,
    remove: bool = False,
) -> dict[str, Any]:
    """Add or remove a native watch/bookmark entry; source files are never modified."""
    if kind not in {"watches", "bookmarks"}:
        raise ProjectError("调试元数据类型只能是 watches 或 bookmarks。")
    normalized = value.strip()
    if not normalized:
        raise ProjectError("调试元数据不能为空。")
    if kind == "watches" and (line is not None or "\n" in normalized or "\r" in normalized):
        raise ProjectError("监视表达式必须是单行文本，不能指定行号。")
    if kind == "bookmarks":
        if line is None or line < 1:
            raise ProjectError("书签需要指定大于 0 的源代码行号。")
        project, source = _project_relative_file(project_file, normalized, suffixes={".xc", ".xcs"},
                                                  must_exist=not remove)
        if not remove:
            line_count = len(source.read_bytes().splitlines())
            if line > line_count:
                raise ProjectError(f"书签行号超出源码范围：{line}，文件共 {line_count} 行。")
        normalized = source.relative_to(project.parent).as_posix().replace("/", "\\")
    else:
        project = Path(inspect_project(project_file)["project_file"])
    tree = ET.parse(project)
    root = tree.getroot()
    block = root.find(kind)
    if block is None:
        block = ET.SubElement(root, kind)
    if kind == "watches":
        attr = "name"
        matches = [item for item in block.findall("item") if item.get(attr, "").casefold() == normalized.casefold()]
        identity = {"expression": normalized}
    else:
        attr = "line"
        matches = [item for item in block.findall("file")
                   if str(item.get("value", "")).replace("/", "\\").casefold() == normalized.casefold()]
        file_node = matches[0] if matches else None
        matching_lines = ([item for item in file_node.findall("item") if item.get("lineno") == str(line)]
                          if file_node is not None else [])
        identity = {"file": normalized, "line": line}
    if kind == "watches":
        if remove:
            changed = bool(matches)
            for item in matches:
                block.remove(item)
        else:
            if matches:
                return {"ok": True, "changed": False, "kind": kind, **identity,
                        "project_file": str(project)}
            ET.SubElement(block, "item", {"name": normalized})
            changed = True
    elif remove:
        changed = bool(matching_lines)
        for item in matching_lines:
            file_node.remove(item)
        if file_node is not None and not file_node.findall("item"):
            block.remove(file_node)
    else:
        if matching_lines:
            return {"ok": True, "changed": False, "kind": kind, **identity,
                    "project_file": str(project)}
        file_node = file_node or ET.SubElement(block, "file", {"value": normalized})
        ET.SubElement(file_node, "item", {"lineno": str(line)})
        changed = True
    if changed:
        _atomic_project_xml(project, tree)
    return {"ok": True, "changed": changed, "added": changed and not remove,
            "removed": changed and remove, "kind": kind, **identity, "project_file": str(project)}


@_project_update
def activate_source(project_file: str | os.PathLike[str], source_path: str = "main.xc") -> dict[str, Any]:
    """List the template's actual entry point in native <codeExpand> metadata."""
    project = Path(inspect_project(project_file)["project_file"])
    relative = Path(source_path)
    if relative.is_absolute() or ".." in relative.parts or relative.suffix.lower() not in {".xc", ".xcs"}:
        raise ProjectError("Source entry must be an existing project-relative .xc or .xcs file.")
    source = (project.parent / relative).resolve()
    if not source.is_file() or not source.is_relative_to(project.parent):
        raise ProjectError(f"Project source does not exist inside the project directory: {source}")
    tree = ET.parse(project)
    root = tree.getroot()
    files = root.find("codeExpand")
    if files is None:
        files = ET.SubElement(root, "codeExpand")
    for item in files.findall("item"):
        if str(item.get("file", "")).replace("/", "\\").casefold() == str(relative).replace("/", "\\").casefold():
            return {"project_file": str(project), "source": str(source), "added": False,
                    "files": [dict(item.attrib) for item in files.findall("item")]}
    ET.SubElement(files, "item", {"file": str(relative).replace("/", "\\"), "state": "1,"})
    _atomic_project_xml(project, tree)
    return {"project_file": str(project), "source": str(source), "added": True,
            "files": [dict(item.attrib) for item in files.findall("item")]}


def list_projects(directory: str | os.PathLike[str], *, recursive: bool = False) -> list[dict[str, Any]]:
    """Find native IDE projects without walking generated or VCS directories."""
    root = Path(directory).expanduser().resolve()
    if not root.is_dir():
        raise ProjectError(f"Project search directory does not exist: {root}")
    ignored = {".git", ".svn", "__pycache__", ".cli-anything", "debug", "debug64", "release", "release64", "obj", "bin"}
    folded_ignored = {value.casefold() for value in ignored}
    results = []
    if recursive:
        for current, directories, filenames in os.walk(root):
            directories[:] = [entry for entry in directories if entry.casefold() not in folded_ignored]
            results.extend(inspect_project(Path(current) / filename) for filename in filenames if filename.lower().endswith(".xcproj"))
    else:
        results = [inspect_project(path) for path in sorted(root.glob("*.xcproj"))]
    return sorted(results, key=lambda project: project["project_file"].casefold())
