"""Replay 20 read-only discoveries against the local XCIDE installation.

Uses the installed CLI for implemented queries and reads native files for the
remaining gaps. Writes only the explicitly requested evidence JSON file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import uuid
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile


def explore(ide: Path) -> dict:
    executable = shutil.which("cli-anything-xcide")
    if not executable:
        raise RuntimeError("Install cli-anything-xcide before running this exploration.")
    hashes = {}
    rounds = []
    catalog_data = {}
    session = Path(tempfile.gettempdir()) / ("xcide-discovery-" + uuid.uuid4().hex + ".json")
    command = [executable, "--json", "--dry-run", "--ide", str(ide), "--session-file", str(session)]

    def read(relative):
        path = (ide / relative).resolve()
        if not path.is_relative_to(ide):
            raise ValueError(f"Source leaves installation: {relative}")
        raw = path.read_bytes()
        hashes.setdefault(str(path), hashlib.sha256(raw).hexdigest())
        return raw

    def xml(relative, fragment=False):
        text = read(relative).decode("utf-8-sig")
        if fragment:
            text = re.sub(r"^\s*<\?xml[^?]*\?>", "", text)
            text = "<fragment>" + text + "</fragment>"
        return ET.fromstring(text)

    def record(topic, sources, facts, status="deferred", invocation=None):
        rounds.append({"round": len(rounds) + 1, "topic": topic, "status": status,
                       "sources": sources, "facts": facts, "command": invocation})

    read("data/config/config.config")
    kinds = {
        "snippets": "codeSnippet.json", "language": "help.json", "controls": "sys/objectName.config",
        "properties": "sys/propertyList.json", "property-help": "sys/propertyList.json",
        "events": "sys/events.xml", "custom-objects": "customObject.config",
        "build-options": "sys/vc-set.json", "functions": "sys/autoMatch_function.txt",
        "completion-tokens": "sys/autoMatch_const.txt",
    }
    for kind, relative in kinds.items():
        relative = "data/config/" + relative
        read(relative)
        invocation = command + ["reference", "search", kind, "--limit", "2000"]
        result = subprocess.run(invocation, capture_output=True, text=True, encoding="utf-8", timeout=30, check=True)
        data = json.loads(result.stdout)
        if not data["ok"] or data["truncated"] or data["count"] != data["total"]:
            raise AssertionError(f"Incomplete discovery: {kind}")
        catalog_data[kind] = data
        facts = {"count": data["total"], "sample": data["items"][:2], "scope_count": len(data["scopes"])}
        if kind == "properties":
            facts["choice_fields"] = sum(bool(x["choices"]) for x in data["items"])
            facts["attribute_names"] = len({x["attribute"] for x in data["items"]})
        if kind == "property-help":
            fields = {x["attribute"] for x in catalog_data["properties"]["items"]}
            facts["help_without_property_row"] = [x["id"] for x in data["items"] if x["id"] not in fields]
        record(kind, [relative], facts, "implemented", invocation)

    labels = {}
    for language in ("ch", "en"):
        tree = xml(f"data/config/sys/customPropertyName_{language}.xml")
        labels[language] = {n.attrib["name"]: n.attrib["value"] for n in tree}
    record("属性中英文名称对照", [f"data/config/sys/customPropertyName_{lang}.xml" for lang in ("ch", "en")],
           {"counts": {k: len(v) for k, v in labels.items()},
            "only_ch": sorted(labels["ch"].keys() - labels["en"].keys()),
            "only_en": sorted(labels["en"].keys() - labels["ch"].keys())})

    palettes = xml("data/config/favoriteColor.config")
    record("收藏调色板与渐变", ["data/config/favoriteColor.config"],
           {"groups": [{"name": n.get("name"), "solid": len(n.findall("./solid/item")),
                        "gradient": len(n.findall("./gradient/item"))} for n in palettes]})

    colors = xml("data/config/customColor.config", True)
    record("自定义颜色的原始编码", ["data/config/customColor.config"],
           {"entries": [{"tag": n.tag, **n.attrib} for n in colors], "encoding_verified": False})

    toolchain = xml("data/config/sys/vc.config")
    paths = []
    for node in toolchain.findall(".//item"):
        value = node.get("path")
        if value:
            candidate = Path(value.replace("\\", "/"))
            resolved = candidate if candidate.is_absolute() else ide / candidate
            paths.append({"path": value, "exists": resolved.exists()})
    record("SDK 与工具集的目录配置", ["data/config/sys/vc.config"],
           {"sdks": [n.attrib for n in toolchain.findall("./sdk/config")],
            "toolsets": [n.attrib for n in toolchain.findall("./platformToolset/config")],
            "path_count": len(paths), "missing_paths": [x for x in paths if not x["exists"]],
            "compiler_invoked": False})

    templates = sorted((ide / "data/xml/item_template").glob("*.xml"))
    roots = Counter()
    binding_files = []
    for path in templates:
        relative = path.relative_to(ide).as_posix()
        tree = xml(relative, True)
        roots.update(n.tag for n in tree if n.tag != "head")
        if any("{binding" in v for n in tree.iter() for v in n.attrib.values()):
            binding_files.append(relative)
    record("IDE 自用列表项模板", [p.relative_to(ide).as_posix() for p in templates],
           {"count": len(templates), "roots": dict(roots), "binding_file_count": len(binding_files),
            "samples": binding_files[:3]})

    pages = ["config", "dir", "exclude", "link"]
    sources = [f"data/xml/layout_projectSetting_{name}.xml" for name in pages]
    fields = {name: [n.get("name") for n in xml(relative, True).iter() if n.get("name")]
              for name, relative in zip(pages, sources)}
    record("工程设置页面中的未封装字段", sources, {"named_controls": fields, "write_semantics_verified": False})

    resource = "例子/炫彩界面AI项目/资源文件/resource.res"
    tree = xml(resource)
    names = Counter(n.get("name") for section in tree for n in section if n.get("name"))
    record("磁盘资源表的可导入对象", [resource],
           {"sections": {n.tag: len(n) for n in tree}, "duplicate_names": [n for n, count in names.items() if count > 1]})

    archive = "例子/炫彩界面AI项目/UI_ZIP.zip"
    with ZipFile(BytesIO(read(archive))) as zipped:
        entries = zipped.infolist()
        record("UI ZIP 成员与资源表", [archive],
               {"member_count": len(entries), "xml_members": [n.filename for n in entries if n.filename.endswith(".xml")],
                "resource_members": [n.filename for n in entries if n.filename.endswith(".res")],
                "encrypted_members": sum(bool(n.flag_bits & 1) for n in entries),
                "duplicate_names": [name for name, count in Counter(n.filename for n in entries).items() if count > 1],
                "extracted": False})

    matches = sorted((ide / "data/XC-Module").rglob("module_sub_cxxastar.h"))
    if len(matches) != 1:
        raise AssertionError("Expected one module_sub_cxxastar.h for the forwarding-header probe")
    module = matches[0].relative_to(ide).as_posix()
    text = read(module).decode("utf-8-sig")
    lines = text.splitlines()
    forwards = [{"line": i + 1, "text": "\n".join(lines[i:i + 4])}
                for i, line in enumerate(lines) if line.strip().startswith("//@解析头文件")]
    record("模块声明转发与 API 提取边界", [module],
           {"alias_annotations": len(re.findall(r"^\s*//@别名", text, re.M)), "forward_declarations": forwards,
            "source_annotations": [line for line in lines if line.strip().startswith("//@src")]})

    native_tools = sorted((ide / "data/tool").glob("*.exe"))
    note = "data/tool/DbgView使用说明.txt"
    record("原生辅助工具的自动化入口", ["data/tool", note],
           {"executables": [p.name for p in native_tools], "debugview_help": read(note).decode("utf-8-sig").strip(),
            "executed": False, "headless_protocol_verified": False})

    after = {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in hashes}
    if len(rounds) != 20 or after != hashes or session.exists():
        raise AssertionError("Discovery must finish 20 rounds without altering source files or saving a session")
    return {"schema": "xcide-exploration/v1", "captured_at": datetime.now(timezone.utc).isoformat(),
            "ide_root": str(ide), "cli": executable, "round_count": len(rounds),
            "source_files_checked": len(hashes), "sources_unchanged": True,
            "source_hashes_before": hashes, "source_hashes_after": after, "rounds": rounds}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ide", type=Path, default=Path(r"I:\xcide"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ide = args.ide.resolve()
    output = args.output.resolve()
    if output.is_relative_to(ide):
        parser.error("Evidence output must be outside the IDE installation")
    evidence = explore(ide)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rounds": evidence["round_count"], "source_files_checked": evidence["source_files_checked"],
                      "sources_unchanged": evidence["sources_unchanged"], "output": str(output)}, ensure_ascii=False))
