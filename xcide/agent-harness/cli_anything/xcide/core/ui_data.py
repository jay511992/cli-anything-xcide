"""Inspect explicit layout and resource documents on disk or inside a UI ZIP."""

from __future__ import annotations

import posixpath
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from cli_anything.xcide.core import archive
from cli_anything.xcide.core.files import FileOperationError, validate_path


MAX_XML_BYTES = 4 * 1024 * 1024
MAX_NODES = 20000
MAX_DEPTH = 128
LAYOUT_ROOTS = {"windowUI", "layoutPanel", "xc_template_list", "xc_template_listBox",
                "xc_template_listView", "xc_template_tree", "xc_template_object"}


class UIDataError(ValueError):
    """The requested native XML data cannot be interpreted reliably."""


def _document(path, *, member=None, project=None, ide_root=None, fragment=False):
    if member is None:
        raw, source = archive.bounded_file(path, project=project, ide_root=ide_root, limit=MAX_XML_BYTES)
    else:
        raw, source = archive.member_bytes(path, member, project=project, ide_root=ide_root)
        if len(raw) > MAX_XML_BYTES:
            raise UIDataError(f"XML 超过 {MAX_XML_BYTES} 字节上限。")
    decoded = archive.text_content(raw)
    text = decoded["content"]
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", text, re.I):
        raise UIDataError("布局和资源 XML 不支持 DTD 或实体声明。")
    if fragment:
        text = "<xcide_fragment>" + re.sub(r"^\s*<\?xml[^?]*\?>", "", text, count=1) + "</xcide_fragment>"
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise UIDataError(f"XML 结构错误：{exc}") from exc
    stack = [(root, 0)]
    count = 0
    while stack:
        node, depth = stack.pop()
        count += 1
        if count > MAX_NODES or depth > MAX_DEPTH:
            raise UIDataError("XML 节点数或深度超过检查上限。")
        stack.extend((child, depth + 1) for child in node)
    return root, {**source, "encoding": decoded["encoding"], "bom": decoded["bom"], "crlf": decoded["crlf"]}


def _asset(value, path, member, *, project, ide_root, archive_records):
    result = {"value": value}
    if not value or value.startswith("@") or "$(" in value or "%" in value:
        return {**result, "status": "unresolved", "exists": None}
    normalized = value.replace("\\", "/")
    if normalized.startswith("/") or ":" in normalized:
        return {**result, "status": "external-or-qualified", "exists": None}
    if member is not None:
        relative = posixpath.normpath(posixpath.join(posixpath.dirname(member.replace("\\", "/")), normalized))
        if archive.path_issues(relative):
            return {**result, "status": "outside-archive", "exists": None}
        candidates = [r for r in archive_records if r["normalized_path"].casefold() == relative.casefold()]
        exists = len(candidates) == 1 and candidates[0]["readable"]
        return {**result, "path": relative, "status": "present" if exists else "missing-or-unreadable",
                "exists": exists}
    candidate = Path(path).expanduser().resolve().parent / normalized
    try:
        candidate = validate_path(candidate, project=project, ide_root=ide_root)
    except FileOperationError:
        return {**result, "status": "outside-scope", "exists": None}
    exists = candidate.is_file()
    return {**result, "path": str(candidate), "status": "present" if exists else "missing", "exists": exists}


def resource_records(path, *, member=None, project=None, ide_root=None):
    root, source = _document(path, member=member, project=project, ide_root=ide_root)
    if root.tag != "resources":
        raise UIDataError(f"资源表根节点应为 resources，实际为 {root.tag}")
    archive_records = []
    if member is not None:
        bundle, snapshot = archive._open(path, project=project, ide_root=ide_root)
        with bundle:
            archive_records = archive._index(bundle)
        if snapshot["sha256"] != source["archive"]["sha256"]:
            raise UIDataError("归档在读取期间变化，请重新查询。")
    entries = []
    sections = []
    folders = []
    for s, section in enumerate(root):
        start_entries, start_folders = len(entries), len(folders)
        stack = [(node, f"{s}/{i}", str(s), []) for i, node in reversed(list(enumerate(section)))]
        while stack:
            node, identifier, parent, folder_ids = stack.pop()
            if node.tag == "folder":
                folders.append({"id": identifier, "kind": section.tag, "parent": parent,
                                "name": node.get("name"), "attributes": dict(node.attrib),
                                "child_count": len(node)})
                stack.extend((child, f"{identifier}/{i}", identifier, folder_ids + [identifier])
                             for i, child in reversed(list(enumerate(node))))
                continue
            refs = []
            if section.tag == "type_image" and node.get("loadType", "file").casefold() == "file" and node.get("value"):
                refs.append(node.get("value"))
            if section.tag == "type_font" and node.get("fontFile"):
                refs.append(node.get("fontFile"))
            entries.append({"id": identifier, "parent": parent, "folder_ids": folder_ids,
                            "kind": section.tag, "tag": node.tag, "name": node.get("name"),
                            "attributes": dict(node.attrib), "xml": ET.tostring(node, encoding="unicode").rstrip(),
                            "assets": [_asset(v, path, member, project=project, ide_root=ide_root,
                                              archive_records=archive_records) for v in refs]})
        sections.append({"tag": section.tag, "count": len(section), "attributes": dict(section.attrib),
                         "resource_count": len(entries) - start_entries, "folder_count": len(folders) - start_folders})
    counts = Counter(e["name"] for e in entries if e["name"])
    return {"source": source, "sections": sections, "folders": folders, "entries": entries,
            "duplicate_names": sorted(n for n, count in counts.items() if count > 1)}


def list_resources(path, *, member=None, project=None, ide_root=None, query="", kind=None, limit=100, offset=0):
    data = resource_records(path, member=member, project=project, ide_root=ide_root)
    if kind is not None and kind not in {s["tag"] for s in data["sections"]}:
        raise UIDataError(f"资源类型不存在：{kind}")
    entries = data.pop("entries")
    filtered = [entry for entry in entries if kind is None or entry["kind"] == kind]
    return {"ok": True, **data, "kind": kind, **archive.page(filtered, query=query, limit=limit, offset=offset)}


def show_resource(path, identifier, *, member=None, project=None, ide_root=None):
    data = resource_records(path, member=member, project=project, ide_root=ide_root)
    entries = [entry for entry in data.pop("entries") if entry["id"] == identifier]
    if len(entries) != 1:
        raise UIDataError(f"资源 ID 不存在，请使用 list 返回的准确 ID：{identifier}")
    return {"ok": True, **data, "item": entries[0]}


def layout_records(path, *, member=None, project=None, ide_root=None):
    fragment, source = _document(path, member=member, project=project, ide_root=ide_root, fragment=True)
    roots = [n for n in fragment if n.tag != "head"]
    if len(roots) != 1 or roots[0].tag not in LAYOUT_ROOTS:
        raise UIDataError(f"需要一个已知窗口/面板/模板根节点，实际为 {[n.tag for n in roots]}")
    root = roots[0]
    entries = []
    elements = {}
    stack = [(root, "0", None, 0)]
    while stack:
        node, identifier, parent, depth = stack.pop()
        attrs = dict(node.attrib)
        entries.append({"id": identifier, "parent": parent, "depth": depth, "tag": node.tag,
                        "name": node.get("name"), "attributes": attrs, "child_count": len(node),
                        "bindings": {k: v for k, v in attrs.items() if "{binding" in v},
                        "text": node.text or ""})
        elements[identifier] = node
        stack.extend((child, f"{identifier}/{i}", identifier, depth + 1) for i, child in reversed(list(enumerate(node))))
    return {"source": source, "root": root.tag, "node_count": len(entries), "entries": entries,
            "heads": [ET.tostring(h, encoding="unicode").rstrip() for h in fragment if h.tag == "head"],
            "elements": elements}


def list_nodes(path, *, member=None, project=None, ide_root=None, query="", tag=None,
               attribute=None, value=None, limit=100, offset=0):
    if value is not None and attribute is None:
        raise UIDataError("--value 必须与 --attribute 一起使用。")
    data = layout_records(path, member=member, project=project, ide_root=ide_root)
    data.pop("elements")
    entries = data.pop("entries")
    filtered = [e for e in entries if (tag is None or e["tag"] == tag)
                and (attribute is None or attribute in e["attributes"])
                and (value is None or e["attributes"][attribute] == value)]
    return {"ok": True, **data, **archive.page(filtered, query=query, limit=limit, offset=offset)}


def show_node(path, identifier, *, member=None, project=None, ide_root=None):
    data = layout_records(path, member=member, project=project, ide_root=ide_root)
    elements = data.pop("elements")
    matches = [e for e in data.pop("entries") if e["id"] == identifier]
    if len(matches) != 1:
        raise UIDataError(f"节点 ID 不存在，请使用 nodes 返回的准确 ID：{identifier}")
    return {"ok": True, **data, "item": matches[0],
            "xml": ET.tostring(elements[identifier], encoding="unicode").rstrip()}
