"""Search native IDE reference data without inferring runtime API semantics."""

from __future__ import annotations

import hashlib
import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from cli_anything.xcide.core.project import resolve_ide_root


CATALOGS = {
    "snippets": ("codeSnippet.json", "炫语言代码片段"),
    "language": ("help.json", "炫语言类型、关键字与指令帮助"),
    "controls": ("sys/objectName.config", "控件 XML 标签与中文名称"),
    "properties": ("sys/propertyList.json", "控件属性、帮助及原生候选值"),
    "property-help": ("sys/propertyList.json", "独立属性帮助条目"),
    "events": ("sys/events.xml", "控件事件与回调声明模板"),
    "custom-objects": ("customObject.config", "组合控件 XML 片段"),
    "build-options": ("sys/vc-set.json", "编译选项名称与原生字段映射"),
    "functions": ("sys/autoMatch_function.txt", "IDE 函数自动补全声明（未验证 API 可用性）"),
    "completion-tokens": ("sys/autoMatch_const.txt", "IDE 常量及其他补全词（不提供数值）"),
}
MAX_SOURCE_BYTES = 4 * 1024 * 1024


class ReferenceError(ValueError):
    """A requested reference or its installed source cannot be read reliably."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReferenceError(message)


def _strings(value: Any, keys: tuple[str, ...]) -> None:
    _require(isinstance(value, dict) and all(isinstance(value.get(k), str) for k in keys),
             f"字段必须为字符串：{', '.join(keys)}")


def _pointer(parts: list[str]) -> str:
    return "/" + "/".join(p.replace("~", "~0").replace("/", "~1") for p in parts)


def _read(root: Path, kind: str) -> tuple[str, dict[str, Any]]:
    _require(kind in CATALOGS, f"未知参考目录：{kind}")
    relative = "data/config/" + CATALOGS[kind][0]
    path = root / relative
    _require(path.resolve().is_relative_to(root), f"参考文件越过 IDE 安装目录：{relative}")
    with path.open("rb") as stream:
        raw = stream.read(MAX_SOURCE_BYTES + 1)
    _require(len(raw) <= MAX_SOURCE_BYTES, f"参考文件超过 {MAX_SOURCE_BYTES} 字节上限：{relative}")
    encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    text = raw.decode(encoding)
    return text, {"path": str(path.resolve()), "relative_path": relative,
                  "sha256": hashlib.sha256(raw).hexdigest(), "size": len(raw)}


def _json(text: str) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, f"JSON 字段重复：{key}")
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=pairs)


def _xml(text: str, root_tag: str, *, fragment: bool = False) -> ET.Element:
    _require(not re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", text, re.I), "参考 XML 不支持 DTD 或实体声明。")
    if fragment:
        text = re.sub(r"^\s*<\?xml\b[^?]*\?>", "", text, count=1)
        text = f"<{root_tag}>{text}</{root_tag}>"
    root = ET.fromstring(text)
    _require(root.tag == root_tag, f"参考 XML 根节点应为 <{root_tag}>。")
    return root


def _records(kind: str, text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    scopes: list[dict[str, Any]] = []
    if kind == "snippets":
        data = _json(text)
        _require(isinstance(data, list), "代码片段配置应为列表。")
        for i, item in enumerate(data):
            _strings(item, ("name", "comment", "data"))
            records.append({"id": str(i), "name": item["name"], "comment": item["comment"],
                            "code": item["data"], "pointer": f"/{i}"})
    elif kind in ("language", "property-help"):
        data = _json(text)
        _require(isinstance(data, dict), "帮助配置应为对象。")
        if kind == "property-help":
            data = data.get("help")
            _require(isinstance(data, dict), "属性 help 应为对象。")
        for key, value in data.items():
            _require(isinstance(value, str), f"帮助内容应为文本：{key}")
            pointer = ["help", key] if kind == "property-help" else [key]
            records.append({"id": key, "name": key, "text": value, "pointer": _pointer(pointer)})
    elif kind == "controls":
        root = _xml(text, "objects", fragment=True)
        for item in root:
            _strings(item.attrib, ("name",))
            records.append({"id": item.tag, "name": item.get("name"), "tag": item.tag,
                            "pointer": f"/{item.tag}"})
    elif kind == "properties":
        data = _json(text)
        _require(isinstance(data, dict) and isinstance(data.get("help", {}), dict),
                 "属性配置和 help 应为对象。")
        help_map = data.get("help", {})
        _require(all(isinstance(v, str) for v in help_map.values()), "属性帮助必须为文本。")

        def properties(node: dict, path: list[str]) -> None:
            _require(len(path) <= 32, "属性层级过深。")
            scopes.append({"id": "/".join(path), "name": path[-1]})
            for group, fields in node.items():
                if isinstance(fields, dict):
                    properties(fields, path + [group])
                    continue
                _require(isinstance(fields, list), f"属性分组应为列表：{'/'.join(path)}/{group}")
                for i, field in enumerate(fields):
                    _require(isinstance(field, list) and len(field) in (5, 6)
                             and all(isinstance(v, str) for v in field[:5]),
                             f"属性字段应有 5 个字符串和可选候选值：{group}[{i}]")
                    choices = field[5] if len(field) == 6 else []
                    _require(isinstance(choices, list) and all(isinstance(v, list) and len(v) == 2
                             and all(isinstance(s, str) for s in v) for v in choices),
                             f"属性候选值应为 [值, 显示名称] 列表：{field[2]}")
                    records.append({"id": "/".join(path + [group, field[2]]), "name": field[3],
                                    "attribute": field[2], "scope": "/".join(path), "group": group,
                                    "editor_type": field[0], "flags": field[1], "comment": field[4],
                                    "help": help_map.get(field[2], ""), "choices": choices,
                                    "pointer": _pointer(path + [group, str(i)])})
        for family, node in data.items():
            if family not in ("comment", "help"):
                _require(isinstance(node, dict), f"控件属性层级应为对象：{family}")
                properties(node, [family])
    elif kind == "events":
        root = _xml(text, "events")

        def events(node: ET.Element, path: list[str]) -> None:
            _require(len(path) <= 32, "事件层级过深。")
            if path:
                scopes.append({"id": "/".join(path), "name": path[-1],
                               "class_name": node.get("className", "")})
            for i, child in enumerate(node):
                if child.tag != "item":
                    events(child, path + [child.tag])
                    continue
                _strings(child.attrib, ("event", "declare", "remark"))
                records.append({"id": "/".join(path + [child.attrib["event"]]),
                                "name": child.attrib["event"], "scope": "/".join(path),
                                "class_name": node.get("className", ""),
                                "declaration": child.attrib["declare"], "remark": child.attrib["remark"],
                                "pointer": "/events/" + "/".join(path) + f"/*[{i + 1}]"})
        events(root, [])
    elif kind == "custom-objects":
        root = _xml(text, "customObject")
        for i, item in enumerate(root):
            _strings(item.attrib, ("customName",))
            records.append({"id": str(i), "name": item.get("customName"), "tag": item.tag,
                            "attributes": dict(item.attrib), "node_count": sum(1 for _ in item.iter()),
                            "xml": ET.tostring(item, encoding="unicode").rstrip(),
                            "pointer": f"/customObject/*[{i + 1}]"})
    elif kind == "build-options":
        data = _json(text)
        _require(isinstance(data, dict), "编译选项配置应为对象。")
        for name, item in data.items():
            _strings(item, ("xml_label", "uiType", "flag"))
            choices = item.get("list", {})
            _require(isinstance(choices, dict) and all(isinstance(v, str) for v in choices.values()),
                     f"编译选项候选值应为文本映射：{name}")
            records.append({"id": item["xml_label"], "name": name, "definition": item,
                            "pointer": _pointer([name])})
    elif kind in ("functions", "completion-tokens"):
        for i, line in enumerate(text.splitlines(), 1):
            if line.strip():
                records.append({"id": str(i), "name": line.strip(), "text": line, "line_number": i})
    ids = [r["id"] for r in records]
    _require(len(ids) == len(set(ids)), "参考配置包含重复 ID，不能唯一定位条目。")
    return records, scopes


def _load(root: Path, kind: str) -> dict[str, Any]:
    try:
        text, source = _read(root, kind)
        items, scopes = _records(kind, text)
    except (OSError, ValueError, ET.ParseError, RecursionError) as exc:
        raise ReferenceError(f"无法读取参考目录 {kind}：{exc}") from exc
    return {"catalog": kind, "source": source, "scopes": scopes, "items": items}


def list_sources(*, ide_root: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Discover known sources, reporting unavailable catalogs individually."""
    root = resolve_ide_root(ide_root)
    sources = []
    for kind, (relative, description) in CATALOGS.items():
        entry = {"catalog": kind, "description": description, "relative_path": "data/config/" + relative}
        try:
            data = _load(root, kind)
            entry.update(available=True, count=len(data["items"]), source=data["source"])
        except ReferenceError as exc:
            entry.update(available=False, count=None, error=str(exc))
        sources.append(entry)
    return {"ok": True, "ide_root": str(root), "sources": sources,
            "available_count": sum(s["available"] for s in sources)}


def search_references(kind: str, query: str = "", *, ide_root: str | os.PathLike[str] | None = None,
                      scope: str | None = None, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    """Search literal native fields, optionally restricted to one exact scope."""
    _require(1 <= limit <= 2000 and offset >= 0, "limit 必须为 1..2000，offset 不能为负数。")
    data = _load(resolve_ide_root(ide_root), kind)
    if scope is not None:
        _require(scope in {s["id"] for s in data["scopes"]}, f"作用域不存在，请从 scopes 中选择：{scope}")
    needle = query.strip().casefold()
    matches = [r for r in data["items"] if (scope is None or r.get("scope") == scope)
               and (not needle or needle in json.dumps(r, ensure_ascii=False).casefold())]
    selected = matches[offset:offset + limit]
    next_offset = offset + len(selected)
    return {**data, "ok": True, "query": query, "scope": scope, "items": selected,
            "count": len(selected), "total": len(matches), "offset": offset,
            "truncated": next_offset < len(matches),
            "next_offset": next_offset if next_offset < len(matches) else None}


def show_reference(kind: str, identifier: str, *, ide_root: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Resolve an opaque exact ID from search results; never interpret it as a path."""
    data = _load(resolve_ide_root(ide_root), kind)
    matches = [r for r in data["items"] if r["id"] == identifier]
    _require(len(matches) == 1, f"参考条目不存在，请使用 search 返回的准确 ID：{kind}/{identifier}")
    return {"ok": True, "catalog": kind, "source": data["source"], "item": matches[0]}
