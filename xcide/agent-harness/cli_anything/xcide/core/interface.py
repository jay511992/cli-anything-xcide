"""炫彩界面布局 XML、resource.res 与 UI_ZIP 的本地清单和结构检查。"""

from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from typing import Any

from cli_anything.xcide.core.project import inspect_project
from cli_anything.xcide.core.files import _decode as _decode_text


_LAYOUT_ROOTS = {"windowUI", "layoutPanel", "xc_template_list", "xc_template_listBox",
                 "xc_template_listView", "xc_template_tree"}
_UI_TAGS = {"windowUI", "layoutPanel", "layoutEleUI", "layoutFrameUI", "elementUI", "scrollViewUI",
            "buttonUI", "textLinkUI", "editUI", "richTextBoxUI", "comboBoxUI", "listUI", "listBoxUI",
            "listViewUI", "treeUI", "scrollBarUI", "listHeaderUI", "progressBarUI", "sliderBarUI",
            "tabBarUI", "toolBarUI", "menuBarUI", "monthCalUI", "dateTimeUI", "paneUI", "propertyGridUI",
            "shapeText", "shapePicture", "shapeGif", "shapeRect", "shapeEllipse", "shapeGroupBox", "shapeLine",
            "xc_template_list", "xc_template_listBox", "xc_template_listView", "xc_template_tree"}
_REFERENCE_ATTRS = {"font", "bkInfoM", "id", "image", "icon"}
_NAME_REF = re.compile(r"@([^@\s,;(){}]+)")
_XML_DECL = re.compile(r"^\s*<\?xml[^>]*\?>", re.IGNORECASE)
_LAYOUT_MARKER = re.compile(r"<(?:" + "|".join(sorted(_LAYOUT_ROOTS | {"head"})) + r")(?=[\s/>])")
_GENERATED_DIRS = {"debug", "debug64", "release", "release64", "obj", "x64", "x86"}


class InterfaceError(ValueError):
    """布局/资源输入损坏或检查路径无效。"""


def _decode(path: Path) -> str:
    return _decode_text(path.read_bytes())[0]


def _parse_layout(path: Path) -> tuple[ET.Element, list[str]]:
    # 炫彩布局根为 <head/> 与主节点并列；在安全包装节点内解析，不要求标准单根文件。
    try:
        text = _decode(path)
        body = _XML_DECL.sub("", text, count=1).strip()
        fragment = ET.fromstring(f"<xcide_fragment>{body}</xcide_fragment>")
    except (OSError, UnicodeError, ET.ParseError) as exc:
        raise InterfaceError(f"布局 XML 结构无法解析：{path}: {exc}") from exc
    roots = [child for child in fragment if child.tag != "head"]
    if len(roots) != 1 or roots[0].tag not in _LAYOUT_ROOTS:
        tags = [child.tag for child in roots]
        raise InterfaceError(f"布局文件应有且仅有一个炫彩窗口/面板/模板根节点；实际：{tags}")
    return roots[0], [child.tag for child in fragment if child.tag == "head"]


def _ignored(path: Path, project_dir: Path, include_generated: bool) -> bool:
    ignored = {".git", ".cli-anything", "__pycache__"}
    if not include_generated:
        ignored |= _GENERATED_DIRS
    return any(part.casefold() in ignored for part in path.relative_to(project_dir).parts)


def _layout_files(project_dir: Path, *, include_generated: bool = False) -> list[Path]:
    paths = []
    for path in project_dir.rglob("*.xml"):
        if _ignored(path, project_dir, include_generated):
            continue
        if path.name.casefold() == "main.xml" or "布局文件" in path.relative_to(project_dir).parts:
            paths.append(path)
            continue
        try:
            text = _decode(path)
        except (OSError, UnicodeError):
            continue
        if _LAYOUT_MARKER.search(text):
            paths.append(path)
    return sorted(paths, key=lambda item: item.relative_to(project_dir).as_posix().casefold())


def _resource_names(project_dir: Path, *, include_generated: bool = False) -> tuple[dict[str, set[str]], list[dict[str, str]]]:
    names: dict[str, set[str]] = {}
    problems: list[dict[str, str]] = []
    for path in project_dir.rglob("resource.res"):
        if _ignored(path, project_dir, include_generated):
            continue
        try:
            root = ET.fromstring(_decode(path))
        except (OSError, UnicodeError, ET.ParseError) as exc:
            problems.append({"severity": "error", "code": "resource-parse", "path": str(path), "message": str(exc)})
            continue
        if root.tag != "resources":
            problems.append({"severity": "error", "code": "resource-root", "path": str(path),
                             "message": f"resource.res 根节点应为 resources，实际为 {root.tag}"})
            continue
        relative = path.parent.relative_to(project_dir).as_posix()
        bucket = names.setdefault(relative, set())
        for element in root.iter():
            name = element.get("name")
            if name:
                bucket.add(name)
    for archive in project_dir.rglob("UI_ZIP.zip"):
        if _ignored(archive, project_dir, include_generated):
            continue
        try:
            with zipfile.ZipFile(archive) as bundle:
                resource_members = [name for name in bundle.namelist()
                                    if PurePosixPath(name.replace("\\", "/")).name.casefold() == "resource.res"]
                for member in resource_members:
                    try:
                        root = ET.fromstring(bundle.read(member).decode("utf-8-sig"))
                    except (KeyError, UnicodeDecodeError, ET.ParseError) as exc:
                        problems.append({"severity": "warning", "code": "archive-resource-parse",
                                         "path": archive.relative_to(project_dir).as_posix(),
                                         "message": f"UI ZIP 中的 resource.res 无法解析：{member}: {exc}"})
                        continue
                    if root.tag != "resources":
                        problems.append({"severity": "warning", "code": "archive-resource-root",
                                         "path": archive.relative_to(project_dir).as_posix(),
                                         "message": f"UI ZIP 中的资源根节点不是 resources：{member}"})
                        continue
                    bucket = names.setdefault(f"archive:{archive.relative_to(project_dir).as_posix()}:{member}", set())
                    bucket.update(element.get("name") for element in root.iter() if element.get("name"))
        except (OSError, zipfile.BadZipFile):
            continue
    return names, problems


def _resource_asset_diagnostics(project_dir: Path, *, include_generated: bool = False) -> list[dict[str, str]]:
    """核对 resource.res 中按文件加载的图片/字体是否真实存在。"""
    diagnostics: list[dict[str, str]] = []

    def validate(root: ET.Element, source: str, exists) -> None:
        for image in root.findall("./type_image/image"):
            value = str(image.get("value", "")).strip()
            if value and image.get("loadType", "file").casefold() == "file" and not exists(value):
                diagnostics.append({"severity": "warning", "code": "missing-resource-asset", "path": source,
                                    "message": f"图片资源文件不存在或未包含在 UI ZIP 中：{value}"})
        for font in root.findall("./type_font/font"):
            value = str(font.get("fontFile", "")).strip()
            if value and not exists(value):
                diagnostics.append({"severity": "warning", "code": "missing-resource-asset", "path": source,
                                    "message": f"字体资源文件不存在或未包含在 UI ZIP 中：{value}"})

    for path in project_dir.rglob("resource.res"):
        if _ignored(path, project_dir, include_generated):
            continue
        try:
            root = ET.fromstring(_decode(path))
        except (OSError, UnicodeError, ET.ParseError):
            continue

        def physical_exists(value: str) -> bool:
            candidate = (path.parent / value.replace("\\", "/")).resolve()
            try:
                candidate.relative_to(project_dir.resolve())
            except ValueError:
                return False
            return candidate.is_file()

        validate(root, path.relative_to(project_dir).as_posix(), physical_exists)

    for archive in project_dir.rglob("UI_ZIP.zip"):
        if _ignored(archive, project_dir, include_generated):
            continue
        try:
            with zipfile.ZipFile(archive) as bundle:
                files = {name.replace("\\", "/").casefold() for name in bundle.namelist() if not name.endswith("/")}
                for member in bundle.namelist():
                    if PurePosixPath(member.replace("\\", "/")).name.casefold() != "resource.res":
                        continue
                    try:
                        root = ET.fromstring(bundle.read(member).decode("utf-8-sig"))
                    except (KeyError, UnicodeDecodeError, ET.ParseError):
                        continue
                    parent = PurePosixPath(member.replace("\\", "/")).parent

                    def archive_exists(value: str) -> bool:
                        normalized = PurePosixPath(value.replace("\\", "/"))
                        if normalized.is_absolute() or ".." in normalized.parts or ":" in value:
                            return False
                        return (parent / normalized).as_posix().casefold() in files

                    validate(root, f"{archive.relative_to(project_dir).as_posix()}::{member}", archive_exists)
        except (OSError, zipfile.BadZipFile):
            continue
    return diagnostics


def inspect_interface(project_file: str, *, include_generated: bool = False) -> dict[str, Any]:
    """列出工程布局及其嵌入布局 ZIP，并返回可定位结构/资源诊断。"""
    project = inspect_project(project_file)
    project_dir = Path(project["directory"])
    resource_names, diagnostics = _resource_names(project_dir, include_generated=include_generated)
    diagnostics.extend(_resource_asset_diagnostics(project_dir, include_generated=include_generated))
    layouts: list[dict[str, Any]] = []
    for path in _layout_files(project_dir, include_generated=include_generated):
        relative = path.relative_to(project_dir).as_posix()
        try:
            root, headers = _parse_layout(path)
        except InterfaceError as exc:
            layouts.append({"path": relative, "valid": False, "root": None, "elementCount": 0,
                            "namedElements": 0, "diagnostics": 1})
            diagnostics.append({"severity": "error", "code": "layout-parse", "path": relative, "message": str(exc)})
            continue
        elements = list(root.iter())
        named = [element for element in elements if element.get("name")]
        names = {element.get("name") for element in named}
        duplicated = sorted(name for name in names if sum(item.get("name") == name for item in named) > 1)
        issues = 0
        for name in duplicated:
            diagnostics.append({"severity": "warning", "code": "duplicate-element-name", "path": relative,
                                "message": f"布局元素 name 重复：{name}"})
            issues += 1
        for index, element in enumerate(elements):
            tag = element.tag
            if tag in {"elementUI", "buttonUI", "shapeText"} and any(
                    child.tag in _UI_TAGS and (child.get("layout.width") or child.get("layout.height"))
                    for child in list(element)):
                diagnostics.append({"severity": "warning", "code": "non-layout-parent", "path": relative,
                                    "message": f"{tag} 不是布局盒子，子元素布局尺寸可能无效（元素序号 {index}）。"})
                issues += 1
            for attribute in _REFERENCE_ATTRS:
                value = element.get(attribute, "")
                for reference in _NAME_REF.findall(value):
                    if reference.startswith(("WmUi:", "WmUi_Base:", "builtin:", "@")):
                        continue
                    declared = any(reference in bucket for bucket in resource_names.values())
                    if attribute in {"id", "bkInfoM", "font", "image", "icon"} and declared:
                        continue
                    if not declared and (project_dir / reference.replace("\\", "/")).is_file():
                        declared = True
                    if not declared:
                        # Built-in theme references and compound bkInfoM values cannot be
                        # confidently resolved from project-local resource.res files.
                        if reference.startswith(("windows", "微软雅黑", "宋体", "Arial", "Tahoma")):
                            continue
                        diagnostics.append({"severity": "warning", "code": "unresolved-resource", "path": relative,
                                            "message": f"无法在工程 resource.res 中确认资源引用 @{reference}（属性 {attribute}）。"})
                        issues += 1
            template_attrs = [value for key, value in element.attrib.items()
                              if key.casefold() in {"itemtemplate", "list.itemtemplate", "tree.itemtemplate"}]
            for value in template_attrs:
                template_file = value.split(",", 1)[0].strip().replace("\\", "/")
                candidates = [path.parent / template_file, project_dir / template_file]
                if not any(candidate.is_file() for candidate in candidates):
                    diagnostics.append({"severity": "warning", "code": "missing-item-template", "path": relative,
                                        "message": f"元素项模板文件不存在：{value}"})
                    issues += 1
        layouts.append({"path": relative, "valid": True, "root": root.tag, "rootCount": 1,
                        "headCount": len(headers), "elementCount": len(elements),
                        "namedElements": len(named), "diagnostics": issues})

    archives = []
    archive_paths = sorted((path for path in project_dir.rglob("UI_ZIP.zip")
                            if not _ignored(path, project_dir, include_generated)), key=lambda p: p.as_posix().casefold())
    for archive in archive_paths:
        entry: dict[str, Any] = {"path": archive.relative_to(project_dir).as_posix(), "valid": False,
                                 "entryCount": 0, "layoutCount": 0, "resourceCount": 0, "errors": []}
        try:
            with zipfile.ZipFile(archive) as bundle:
                bad = bundle.testzip()
                names = [name.replace("\\", "/") for name in bundle.namelist()]
                layouts_in_zip = [name for name in names if name.casefold().endswith(".xml")]
                resources_in_zip = [name for name in names if PurePosixPath(name).name.casefold() == "resource.res"]
                entry.update({"valid": bad is None, "entryCount": len(names),
                              "layoutCount": len(layouts_in_zip), "resourceCount": len(resources_in_zip),
                              "layoutMembers": layouts_in_zip, "resourceMembers": resources_in_zip})
                if bad is not None:
                    entry["errors"].append(f"ZIP CRC 验证失败：{bad}")
                for name in names:
                    member = PurePosixPath(name)
                    if member.is_absolute() or ".." in member.parts or (member.parts and ":" in member.parts[0]):
                        entry["errors"].append(f"ZIP 条目越界路径：{name}")
                for member in layouts_in_zip:
                    try:
                        raw = bundle.read(names[names.index(member)])
                        text = raw.decode("utf-8-sig")
                        body = _XML_DECL.sub("", text, count=1).strip()
                        fragment = ET.fromstring(f"<xcide_fragment>{body}</xcide_fragment>")
                        roots = [child.tag for child in fragment if child.tag != "head"]
                        if len(roots) != 1 or roots[0] not in _LAYOUT_ROOTS:
                            raise ValueError(f"无效的炫彩布局根节点：{roots}")
                    except (KeyError, UnicodeDecodeError, ET.ParseError, ValueError) as exc:
                        entry["errors"].append(f"布局 {member}：{exc}")
                entry["valid"] = entry["valid"] and not entry["errors"]
        except (OSError, zipfile.BadZipFile) as exc:
            entry["errors"].append(str(exc))
        if entry["errors"]:
            diagnostics.append({"severity": "error", "code": "ui-zip", "path": entry["path"],
                                "message": "; ".join(entry["errors"])})
        archives.append(entry)
    errors = sum(item["severity"] == "error" for item in diagnostics)
    warnings = sum(item["severity"] == "warning" for item in diagnostics)
    return {"ok": errors == 0, "project": project["project_file"], "layoutCount": len(layouts),
            "validLayoutCount": sum(item["valid"] for item in layouts), "uiZipCount": len(archives),
            "validUiZipCount": sum(item["valid"] for item in archives),
            "resourceCatalogs": len(resource_names), "errorCount": errors, "warningCount": warnings,
            "layouts": layouts, "uiArchives": archives, "diagnostics": diagnostics}
