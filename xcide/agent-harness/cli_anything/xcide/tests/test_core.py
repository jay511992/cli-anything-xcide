from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import struct
import subprocess
import sys
import threading
import zipfile
import stat
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest
from click.testing import CliRunner

from cli_anything.xcide.core import archive, build, doctor, examples, interface, preview, project, references, templates, themes, ui_data, ui_templates
from cli_anything.xcide.core.session import Session
from cli_anything.xcide.core.files import FileOperationError, read_file, validate_path, write_file
from cli_anything.xcide.core.modules import (
    ModuleError,
    add_module,
    add_modules,
    list_modules,
    plan_module_dependencies,
    remove_module,
    search_modules,
)
from cli_anything.xcide.xcide_cli import cli


@pytest.fixture
def template(tmp_path: Path) -> Path:
    root = tmp_path / "official template"
    root.mkdir()
    (root / "template.xcproj").write_text(
        '<project name="" ui_loadType="1"><vc config="调试版" platform="x64" moduleLib="">'
        '<setting><config name="调试版"><x64><common platformToolset="vs2022" sdk="Windows10" />'
        '</x64><x86><common platformToolset="vs2022" sdk="Windows10" /></x86></config>'
        '<config name="发布版"><x64><common platformToolset="vs2022" sdk="Windows10" />'
        '</x64><x86><common platformToolset="vs2022" sdk="Windows10" /></x86></config>'
        '</setting></vc><modules><item path="module_base.h" name="基础模块" />'
        '</modules><codeExpand /><watches /><breakpoints /><bookmarks /></project>', encoding="utf-8")
    (root / "main.xc").write_text("函数 整型 入口函数_窗口()\n\t返回 0\n", encoding="utf-8")
    (root / "common.xh").write_text("// template header\n", encoding="utf-8")
    (root / "exe.rc").write_text("// native template resource\n", encoding="utf-8")
    (root / "exe.ico").write_bytes(b"icon")
    return root


@pytest.fixture
def make_project(template: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(project, "native_template_dir", lambda _root=None: template)
    ide_root = tmp_path / "fixture-ide"
    (ide_root / "data" / "config").mkdir(parents=True)
    (ide_root / "炫彩IDE.exe").write_bytes(b"fixture ide")
    (ide_root / "data" / "config" / "config.config").write_text(
        '<config><vcDefaultSdk value="Windows10" />'
        '<vcDefaultPlatformToolset value="vs2022" /></config>', encoding="utf-8")
    def create(name="Native Demo", **kwargs):
        kwargs.setdefault("configuration", "发布版")
        kwargs.setdefault("platform", "x64")
        return project.create_project(tmp_path / "projects", name, ide_root=ide_root, **kwargs)
    create.ide_root = ide_root
    create.template_path = template
    return create


def _installed_template_root() -> Path:
    return Path(r"I:\xcide") / project.TEMPLATE_RELATIVE


def _fixture_ide_root(make_project) -> Path:
    return make_project.ide_root


@pytest.fixture
def ui_documents(make_project):
    info = make_project("UI Documents")
    root = Path(info["directory"])
    layout = ('<?xml version="1.0"?><head><bindClassName value="窗口类"/></head>'
              '<windowUI name="窗口" showT="false" show="true"><layoutEleUI>'
              '<buttonUI name="same" id="1" content="{binding field=caption source=data}"/>'
              '<buttonUI name="same" id="2"/><child><scrollBarUI itemID="3"/></child>'
              '</layoutEleUI></windowUI>')
    resource = ('<resources><type_image><image name="same" value="icon.svg" loadType="file"/>'
                '<image name="missing" value="missing.png"/><image name="symbolic" value="@WmUi:icon"/>'
                '</type_image><type_font><font name="same" fontFile="../font/a.ttf"/>'
                '<font name="system" fontName="微软雅黑"/></type_font><type_string/>'
                '<future_type><thing name="future" custom="yes"/></future_type></resources>')
    (root / "main.xml").write_bytes(b"\xfe\xff" + layout.encode("utf-16-be"))
    (root / "assets").mkdir()
    (root / "font").mkdir()
    (root / "font/a.ttf").write_bytes(b"\0font-data\xff")
    (root / "assets/resource.res").write_text(resource, encoding="utf-8")
    (root / "assets/icon.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
    zipped = root / "UI_ZIP.zip"
    with zipfile.ZipFile(zipped, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("布局/main.xml", layout.encode("utf-8-sig"))
        z.writestr("assets/resource.res", resource)
        z.writestr("assets/icon.svg", (root / "assets/icon.svg").read_bytes())
        z.writestr("font/a.ttf", (root / "font/a.ttf").read_bytes())
        z.writestr("empty/", b"")
    # Python 3.14 normalizes filenames while writing; preserve the native ZIP
    # variant by changing both same-length local/central directory names.
    zipped.write_bytes(zipped.read_bytes().replace("布局/main.xml".encode(), "布局\\main.xml".encode()))
    return {"root": root, "project": info["project_file"], "zip": zipped, "layout": layout, "resource": resource}


def test_archive_roundtrip_normalizes_backslashes_without_losing_original(ui_documents, tmp_path):
    doc = ui_documents
    listing = archive.list_archive(doc["zip"], project=doc["project"], limit=2)
    assert listing["entry_count"] == 5 and listing["next_offset"] == 2
    assert not listing["crc_verified"] and listing["problem_count"] == 0
    member = listing["items"][0]
    assert member["id"] == "布局/main.xml" and member["original_name"] == "布局\\main.xml"
    text = archive.read_member(doc["zip"], member["id"], project=doc["project"])
    assert text["content"] == doc["layout"] and text["source"]["crc_verified"] and text["bom"]
    assert text["source"]["sha256"] == hashlib.sha256(doc["layout"].encode("utf-8-sig")).hexdigest()
    with pytest.raises(archive.ArchiveError):
        archive.read_member(doc["zip"], "font/a.ttf", project=doc["project"])
    output = tmp_path / "font-copy.ttf"
    planned = archive.export_member(doc["zip"], "font/a.ttf", output, project=doc["project"], dry_run=True)
    assert planned["created"] is False and not output.exists()
    done = archive.export_member(doc["zip"], "font/a.ttf", output, project=doc["project"])
    assert done["created"] and done["verified"]
    assert output.read_bytes() == (doc["root"] / "font/a.ttf").read_bytes()
    with pytest.raises(archive.ArchiveError, match="覆盖"):
        archive.export_member(doc["zip"], "font/a.ttf", output, project=doc["project"])


@pytest.mark.parametrize("name", ["../escape", "/rooted", "C:/drive", "dir/../../escape", "a:stream",
                                  "CON.txt", "dir/name.", "dir/name ", "dir//name", "bad?.txt"])
def test_archive_unsafe_members_are_reported_and_not_exported(make_project, tmp_path, name):
    info = make_project()
    zipped = Path(info["directory"]) / "bad.zip"
    with zipfile.ZipFile(zipped, "w") as z:
        z.writestr(name, b"payload")
    listing = archive.list_archive(zipped, project=info["project_file"])
    assert listing["problem_count"] == 1 and not listing["items"][0]["readable"]
    output = tmp_path / "should-not-exist"
    with pytest.raises(archive.ArchiveError):
        archive.export_member(zipped, listing["items"][0]["id"], output, project=info["project_file"])
    assert not output.exists()


@pytest.mark.parametrize("case", ["case-collision", "slash-collision", "symlink", "encrypted", "bad-crc", "compression"])
def test_archive_member_integrity_and_ambiguity(make_project, case):
    info = make_project()
    zipped = Path(info["directory"]) / "bad.zip"
    member = "a/b.txt"
    with zipfile.ZipFile(zipped, "w") as z:
        if case == "symlink":
            node = zipfile.ZipInfo(member)
            node.create_system = 3
            node.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(node, b"link-target")
        else:
            z.writestr(member, b"payload")
        if case in {"case-collision", "slash-collision"}:
            other = "A/B.txt" if case == "case-collision" else "a-b.txt"
            z.writestr(other, b"other")
    if case == "slash-collision":
        zipped.write_bytes(zipped.read_bytes().replace(b"a-b.txt", b"a\\b.txt"))
    if case in {"encrypted", "bad-crc", "compression"}:
        raw = bytearray(zipped.read_bytes())
        central = raw.index(b"PK\x01\x02")
        if case == "encrypted":
            struct.pack_into("<H", raw, 6, 1)
            struct.pack_into("<H", raw, central + 8, 1)
        elif case == "compression":
            struct.pack_into("<H", raw, 8, 99)
            struct.pack_into("<H", raw, central + 10, 99)
        else:
            raw[raw.index(b"payload")] ^= 1
        zipped.write_bytes(raw)
    with pytest.raises(archive.ArchiveError):
        archive.read_member(zipped, member, project=info["project_file"])


def test_archive_read_limits_and_atomic_export_collision(ui_documents, tmp_path, monkeypatch):
    doc = ui_documents
    with monkeypatch.context() as patch:
        patch.setattr(archive, "MAX_MEMBER_BYTES", 2)
        assert archive.list_archive(doc["zip"], project=doc["project"])["problem_count"] == 4
        with pytest.raises(archive.ArchiveError):
            archive.member_bytes(doc["zip"], "font/a.ttf", project=doc["project"])
    with monkeypatch.context() as patch:
        patch.setattr(archive, "MAX_ARCHIVE_BYTES", 2)
        with pytest.raises(archive.ArchiveError, match="上限"):
            archive.list_archive(doc["zip"], project=doc["project"])
    with monkeypatch.context() as patch:
        patch.setattr(archive, "MAX_ENTRIES", 2)
        with pytest.raises(archive.ArchiveError, match="条目数"):
            archive.list_archive(doc["zip"], project=doc["project"])
    output = tmp_path / "race.bin"
    real_link = os.link
    def race(src, dst):
        Path(dst).write_bytes(b"other process")
        real_link(src, dst)
    monkeypatch.setattr(archive.os, "link", race)
    with pytest.raises(FileExistsError):
        archive.export_member(doc["zip"], "font/a.ttf", output, project=doc["project"])
    assert output.read_bytes() == b"other process"
    assert not list(tmp_path.glob(".xcide-export-*"))


def test_archive_export_refuses_installation_and_outside_input(ui_documents, make_project, tmp_path):
    doc = ui_documents
    with pytest.raises(archive.ArchiveError, match="安装目录"):
        archive.export_member(doc["zip"], "font/a.ttf", make_project.ide_root / "new.ttf",
                              project=doc["project"], ide_root=make_project.ide_root)
    with pytest.raises(FileOperationError):
        archive.list_archive(tmp_path / "outside.zip", project=doc["project"], ide_root=make_project.ide_root)
    with pytest.raises(archive.ArchiveError):
        archive.read_member(doc["zip"], "empty/", project=doc["project"])


@pytest.mark.parametrize("packed", [False, True])
def test_resource_queries_preserve_unknown_sections_and_resolve_relative_assets(ui_documents, packed):
    doc = ui_documents
    path = doc["zip"] if packed else doc["root"] / "assets/resource.res"
    kwargs = {"project": doc["project"], "member": "assets/resource.res" if packed else None}
    result = ui_data.list_resources(path, **kwargs)
    assert result["duplicate_names"] == ["same"] and result["total"] == 6
    assert result["sections"][2] == {"tag": "type_string", "count": 0, "attributes": {},
                                     "resource_count": 0, "folder_count": 0}
    assert result["items"][0]["assets"][0]["exists"] is True
    assert result["items"][1]["assets"][0]["exists"] is False
    assert result["items"][2]["assets"][0]["exists"] is None
    fonts = ui_data.list_resources(path, kind="type_font", **kwargs)
    assert fonts["items"][0]["assets"][0]["exists"] is True
    assert fonts["items"][1]["assets"] == []
    item = ui_data.show_resource(path, result["items"][-1]["id"], **kwargs)["item"]
    assert item["kind"] == "future_type" and item["attributes"]["custom"] == "yes"
    assert ui_data.list_resources(path, kind="type_string", **kwargs)["count"] == 0
    with pytest.raises(ui_data.UIDataError):
        ui_data.list_resources(path, kind="typo", **kwargs)
    with pytest.raises(ui_data.UIDataError):
        ui_data.show_resource(path, "same", **kwargs)


@pytest.mark.parametrize("packed", [False, True])
def test_resource_folders_are_recursive_categories_not_resource_names(ui_documents, packed):
    doc = ui_documents
    resource = ('<resources><type_image><folder name="分类">'
                '<image name="duplicate" value="icon.svg"/>'
                '<folder name="深层"><image name="deep" value="../font/a.ttf"/></folder>'
                '</folder><folder name="分类"><image name="duplicate" value="absent.png"/>'
                '</folder></type_image><type_font/></resources>')
    if packed:
        path = doc["root"] / "nested.zip"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("assets/resource.res", resource)
            z.writestr("assets/icon.svg", b"<svg/>")
            z.writestr("font/a.ttf", b"font")
    else:
        path = doc["root"] / "assets/nested.res"
        path.write_text(resource, encoding="utf-8")
    kwargs = {"project": doc["project"], "member": "assets/resource.res" if packed else None}
    result = ui_data.list_resources(path, **kwargs)
    assert result["total"] == 3 and result["duplicate_names"] == ["duplicate"]
    assert [n["id"] for n in result["items"]] == ["0/0/0", "0/0/1/0", "0/1/0"]
    assert [n["id"] for n in result["folders"]] == ["0/0", "0/0/1", "0/1"]
    assert result["sections"][0]["resource_count"] == 3
    assert result["sections"][0]["folder_count"] == 3
    assert [n["assets"][0]["exists"] for n in result["items"]] == [True, True, False]
    deep = ui_data.show_resource(path, "0/0/1/0", **kwargs)["item"]
    assert deep["name"] == "deep" and deep["parent"] == "0/0/1"
    assert deep["folder_ids"] == ["0/0", "0/0/1"]
    assert ui_data.list_resources(path, kind="type_font", **kwargs)["total"] == 0
    with pytest.raises(ui_data.UIDataError):
        ui_data.show_resource(path, "0/0", **kwargs)


@pytest.mark.parametrize("packed", [False, True])
def test_layout_queries_preserve_identity_bindings_and_designer_fields(ui_documents, packed):
    doc = ui_documents
    path = doc["zip"] if packed else doc["root"] / "main.xml"
    kwargs = {"project": doc["project"], "member": "布局/main.xml" if packed else None}
    result = ui_data.list_nodes(path, tag="buttonUI", **kwargs)
    assert result["node_count"] == 6 and result["total"] == 2
    assert [n["id"] for n in result["items"]] == ["0/0/0", "0/0/1"]
    assert result["items"][0]["bindings"] == {"content": "{binding field=caption source=data}"}
    second = ui_data.list_nodes(path, attribute="id", value="2", **kwargs)
    assert second["items"][0]["id"] == "0/0/1"
    root = ui_data.show_node(path, "0", **kwargs)
    assert root["item"]["attributes"]["showT"] == "false" and root["item"]["attributes"]["show"] == "true"
    assert project.ET.fromstring(root["xml"]).find("layoutEleUI") is not None
    assert "bindClassName" in root["heads"][0]
    assert ui_data.list_nodes(path, attribute="itemID", **kwargs)["items"][0]["parent"] == "0/0/2"
    assert ui_data.list_nodes(path, query="unmatched", **kwargs)["total"] == 0
    with pytest.raises(ui_data.UIDataError):
        ui_data.list_nodes(path, value="2", **kwargs)
    with pytest.raises(ui_data.UIDataError):
        ui_data.show_node(path, "same", **kwargs)


@pytest.mark.parametrize("text", ['<head/><windowUI/><windowUI/>', '<heiyue/>', '<windowUI>',
                                  '<!DOCTYPE x [<!ENTITY a "b">]><windowUI/>'])
def test_layout_rejects_unknown_and_malformed_input(ui_documents, text):
    doc = ui_documents
    path = doc["root"] / "bad.xml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ui_data.UIDataError):
        ui_data.list_nodes(path, project=doc["project"])


def test_layout_object_root_and_depth_limits(ui_documents, monkeypatch):
    doc = ui_documents
    path = doc["root"] / "object.xml"
    path.write_text('<head/><xc_template_object><buttonUI/></xc_template_object>', encoding="utf-8")
    assert ui_data.list_nodes(path, project=doc["project"])["root"] == "xc_template_object"
    monkeypatch.setattr(ui_data, "MAX_DEPTH", 1)
    with pytest.raises(ui_data.UIDataError, match="深度"):
        ui_data.list_nodes(path, project=doc["project"])


@pytest.fixture
def reference_ide(make_project):
    root = make_project.ide_root
    config = root / "data" / "config"
    (config / "sys").mkdir()
    native = {
        "codeSnippet.json": [{"name": "如果", "comment": "模板", "data": "如果 (真)\n\t占位"},
                             {"name": "if", "comment": "模板", "data": "如果 (真)\n\t占位"},
                             {"name": "如果", "comment": "用户定义", "data": "不同的内容"}],
        "help.json": {"整型": "4 字节，C++ int", "#头文件": "引用 C++ 头文件"},
        "sys/propertyList.json": {
            "comment": ["原生说明"], "help": {"content": "显示内容", "only.in.help": "独立帮助"},
            "elementUI": {"common": [["edit", "true", "content", "内容", ""]],
                "buttonUI": {"self": [["comboBox", "false", "buttonType", "按钮类型", "",
                                         [["", ""], ["check", "多选"]]]],
                             "textLinkUI": {"self": [["edit", "false", "content", "文本链接", ""]]}}}},
        "sys/vc-set.json": {"运行库": {"xml_label": "runtimeLibrary", "uiType": "comboBox", "flag": "cl",
                                      "default_debug": "/MDd", "default": "/MD", "list": {"动态库": "/MD"}}},
    }
    for name, value in native.items():
        (config / name).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8-sig")
    (config / "sys/objectName.config").write_text(
        '<?xml version="1.0"?><buttonUI name="按钮"/><editUI name="编辑框"/>', encoding="utf-8")
    (config / "sys/events.xml").write_text(
        '<events><elementUI className="元素类"><item event="BASE" declare="基础()" remark="基础事件"/>'
        '<buttonUI className="按钮类"><item event="XE_BNCLICK" declare="$[UI对象名称]_点击()" remark="点击事件"/>'
        '<textLinkUI/></buttonUI></elementUI></events>', encoding="utf-8")
    (config / "customObject.config").write_text(
        '<customObject><layoutEleUI customName="组合"><buttonUI content="A &amp; B"/></layoutEleUI></customObject>',
        encoding="utf-8")
    (config / "sys/autoMatch_function.txt").write_text("\n  BOOL XThing_Init();\n\nBOOL XThing_Init();\n", encoding="utf-8")
    (config / "sys/autoMatch_const.txt").write_text("XC_WINDOW\nfor(var i=0; i<count; i++)\n", encoding="utf-8")
    return root


def test_reference_sources_and_literal_content(reference_ide):
    inventory = references.list_sources(ide_root=reference_ide)
    assert inventory["available_count"] == 10
    for source in inventory["sources"]:
        assert source["available"] and source["count"] >= 1
        assert source["source"]["sha256"] == hashlib.sha256(Path(source["source"]["path"]).read_bytes()).hexdigest()
    snippets = references.search_references("snippets", "如果", ide_root=reference_ide)
    assert len({item["id"] for item in snippets["items"]}) == 3  # Duplicate names must remain addressable.
    assert references.show_reference("snippets", "0", ide_root=reference_ide)["item"]["code"] == "如果 (真)\n\t占位"
    controls = references.search_references("controls", "按钮", ide_root=reference_ide)["items"]
    assert controls[0]["id"] == "buttonUI"
    text = references.show_reference("language", "#头文件", ide_root=reference_ide)["item"]["text"]
    assert text == "引用 C++ 头文件"
    compiler = references.show_reference("build-options", "runtimeLibrary", ide_root=reference_ide)["item"]
    assert compiler["definition"]["default_debug"] == "/MDd"
    assert compiler["definition"]["list"] == {"动态库": "/MD"}
    custom = references.show_reference("custom-objects", "0", ide_root=reference_ide)["item"]
    assert custom["node_count"] == 2
    assert project.ET.fromstring(custom["xml"]).find("buttonUI").get("content") == "A & B"
    independent = references.show_reference("property-help", "only.in.help", ide_root=reference_ide)["item"]
    assert independent["text"] == "独立帮助" and independent["pointer"] == "/help/only.in.help"


def test_reference_completion_preserves_raw_line_numbers_and_duplicate_declarations(reference_ide):
    functions = references.search_references("functions", "xthing", ide_root=reference_ide)
    assert [x["id"] for x in functions["items"]] == ["2", "4"]
    assert functions["items"][0]["text"] == "  BOOL XThing_Init();"
    assert functions["items"][0]["line_number"] == 2
    assert references.show_reference("functions", "4", ide_root=reference_ide)["item"]["text"] == "BOOL XThing_Init();"
    token = references.search_references("completion-tokens", "for(", ide_root=reference_ide)["items"][0]
    assert token["text"] == "for(var i=0; i<count; i++)" and "value" not in token


def test_reference_hierarchy_and_pagination_do_not_invent_inheritance(reference_ide):
    parent = references.search_references("properties", scope="elementUI", ide_root=reference_ide)
    assert [p["attribute"] for p in parent["items"]] == ["content"]
    child = references.search_references("properties", scope="elementUI/buttonUI", ide_root=reference_ide)
    assert [p["attribute"] for p in child["items"]] == ["buttonType"]
    assert child["items"][0]["flags"] == "false"  # This is a native editor flag, not the attribute's default.
    assert child["items"][0]["choices"] == [["", ""], ["check", "多选"]]
    deep = references.search_references("properties", scope="elementUI/buttonUI/textLinkUI", ide_root=reference_ide)
    assert deep["items"][0]["help"] == "显示内容"
    assert deep["items"][0]["pointer"] == "/elementUI/buttonUI/textLinkUI/self/0"
    event = references.search_references("events", scope="elementUI/buttonUI", ide_root=reference_ide)
    assert [e["name"] for e in event["items"]] == ["XE_BNCLICK"]
    assert event["items"][0]["declaration"] == "$[UI对象名称]_点击()"
    empty = references.search_references("events", scope="elementUI/buttonUI/textLinkUI", ide_root=reference_ide)
    assert empty["count"] == 0 and empty["ok"]
    page = references.search_references("snippets", limit=2, ide_root=reference_ide)
    assert (page["total"], page["count"], page["truncated"], page["next_offset"]) == (3, 2, True, 2)
    last = references.search_references("snippets", offset=page["next_offset"], limit=2, ide_root=reference_ide)
    assert last["count"] == 1 and last["next_offset"] is None
    assert page["source"] == last["source"]
    assert references.search_references("language", "c++ INT", ide_root=reference_ide)["count"] == 1
    assert references.search_references("language", offset=999, ide_root=reference_ide)["count"] == 0


@pytest.mark.parametrize("kind,content", [
    ("snippets", '{}'),
    ("snippets", '[{"name":"broken","comment":"","data":null}]'),
    ("language", '{"type":{},"other":"text"}'),
    ("language", '{"same":"one","same":"two"}'),
    ("properties", '{"elementUI":{"self":[["edit","true","id"]]}}'),
    ("properties", '{"elementUI":{"self":[["edit","true","id","ID","",["invalid"]]]}}'),
    ("events", '<wrong/>'),
    ("events", '<events><buttonUI><item event="CLICK"/></buttonUI></events>'),
    ("events", '<!DOCTYPE events [<!ENTITY e "hello">]><events/>'),
    ("controls", '<buttonUI name="one"/><buttonUI name="two"/>'),
    ("custom-objects", '<customObject><buttonUI/></customObject>'),
    ("build-options", '{"runtime": {"xml_label":"runtimeLibrary","uiType":"comboBox","flag":"cl","list":[]}}'),
])
def test_reference_rejects_malformed_source_without_silently_dropping_items(reference_ide, kind, content):
    path = reference_ide / "data/config" / references.CATALOGS[kind][0]
    path.write_text(content, encoding="utf-8")
    with pytest.raises(references.ReferenceError):
        references.search_references(kind, ide_root=reference_ide)
    inventory = references.list_sources(ide_root=reference_ide)
    failed = next(s for s in inventory["sources"] if s["catalog"] == kind)
    assert failed["available"] is False and failed["count"] is None and failed["error"]
    expected_failed = {kind, "property-help"} if kind == "properties" else {kind}
    assert {s["catalog"] for s in inventory["sources"] if not s["available"]} == expected_failed
    assert inventory["available_count"] == 10 - len(expected_failed)


def test_reference_limits_missing_source_and_utf16(reference_ide, monkeypatch):
    path = reference_ide / "data/config/help.json"
    path.write_bytes(json.dumps({"整型": "整数"}, ensure_ascii=False).encode("utf-16"))
    assert references.show_reference("language", "整型", ide_root=reference_ide)["item"]["text"] == "整数"
    with monkeypatch.context() as patch:
        patch.setattr(references, "MAX_SOURCE_BYTES", 8)
        with pytest.raises(references.ReferenceError, match="超过"):
            references.search_references("language", ide_root=reference_ide)
    path.unlink()
    with pytest.raises(references.ReferenceError):
        references.search_references("language", ide_root=reference_ide)
    assert references.list_sources(ide_root=reference_ide)["available_count"] == 9


def test_reference_ids_scope_and_bounds_are_validated(reference_ide):
    for kind, identifier in [("controls", "../../config.config"), ("language", "整型/"), ("snippets", "-1")]:
        with pytest.raises(references.ReferenceError):
            references.show_reference(kind, identifier, ide_root=reference_ide)
    for kwargs in ({"scope": "buttonUI"}, {"scope": "unknown"}, {"limit": 0}, {"limit": 2001}, {"offset": -1}):
        with pytest.raises(references.ReferenceError):
            references.search_references("events", ide_root=reference_ide, **kwargs)
    with pytest.raises(references.ReferenceError):
        references.search_references("unknown", ide_root=reference_ide)


def test_reference_refuses_source_link_outside_installation(reference_ide, tmp_path):
    path = reference_ide / "data/config/help.json"
    outside = tmp_path / "outside.json"
    outside.write_text('{"outside":"should not be read"}', encoding="utf-8")
    path.unlink()
    try:
        path.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"Host cannot create test symlink: {exc}")
    with pytest.raises(references.ReferenceError, match="越过"):
        references.search_references("language", ide_root=reference_ide)


def test_new_project_preserves_native_modules_and_lists_existing_entrypoint(make_project):
    result = make_project()
    info = project.inspect_project(result["project_file"])
    assert result["configuration"] == "发布版"
    assert result["platform"] == "x64"
    assert info["files"] == [{"file": "main.xc", "state": "1,"}]
    assert info["modules"] == [{"path": "module_base.h", "name": "基础模块"}]
    assert {item.name for item in Path(result["directory"]).iterdir()} == {"Native Demo.xcproj", "main.xc", "common.xh", "exe.rc", "exe.ico"}
    assert result["platform_toolset"] == "vs2022"
    assert result["sdk"] == "Windows10"
    assert result["native_template"] == "XCGUI IDE official blank-window project template"


@pytest.mark.parametrize("platform", ["x64", "x86"])
def test_project_uses_selected_platform_from_installed_template(make_project, platform):
    result = make_project("Toolset " + platform, configuration="发布版", platform=platform)
    assert result["platform"] == platform
    assert (result["platform_toolset"], result["sdk"]) == ("vs2022", "Windows10")


def test_project_configuration_tracks_installed_ide_toolset_and_sdk(tmp_path, monkeypatch):
    ide_root = tmp_path / "ide"
    (ide_root / "data" / "config").mkdir(parents=True)
    (ide_root / "炫彩IDE.exe").write_bytes(b"fake")
    fixture_template = _installed_template_root()
    if not fixture_template.is_dir():
        pytest.skip("Installed IDE template is required to validate native project configurations")
    monkeypatch.setattr(project, "native_template_dir", lambda _root=None: fixture_template)
    config = ide_root / "data" / "config" / "config.config"
    config.write_text('<config><vcDefaultSdk value="Windows11" />'
                      '<vcDefaultPlatformToolset value="vs2022" /></config>', encoding="utf-8")
    result = project.create_project(tmp_path / "alternate-sdk", "Native Defaults", ide_root,
                                    configuration="调试版", platform="x86")
    assert (result["configuration"], result["platform"]) == ("调试版", "x86")
    assert (result["platform_toolset"], result["sdk"]) == ("vs2022", "Windows11")


def test_project_template_toolchain_defaults_survive_when_ide_config_is_unavailable(template, tmp_path, monkeypatch):
    root = tmp_path / "bare-ide"
    root.mkdir()
    (root / "炫彩IDE.exe").write_bytes(b"fixture ide")
    installed_template = _installed_template_root()
    if not installed_template.is_dir():
        pytest.skip("Installed IDE project template is required for its native SDK defaults")
    template_common = project.ET.parse(installed_template / "template.xcproj").getroot().find("./vc/setting/config[@name='发布版']/x64/common")
    monkeypatch.setattr(project, "native_template_dir", lambda _root=None: installed_template)
    result = project.create_project(tmp_path / "no-config", "Template Defaults", root,
                                    configuration="发布版", platform="x64")
    assert (result["platform_toolset"], result["sdk"]) == (
        template_common.get("platformToolset"), template_common.get("sdk"))


@pytest.mark.parametrize("name", ["", "..", "a/b", "a\\b", "foo.", "CON", "com3", "bad:name", " x "])
def test_invalid_windows_project_names_are_rejected(make_project, name):
    with pytest.raises(project.ProjectError):
        make_project(name)


def test_project_creation_refuses_destination_and_does_not_replace_file(make_project):
    first = make_project("No Replace")
    project_path = Path(first["project_file"])
    original = project_path.read_bytes()
    with pytest.raises(project.ProjectError, match="already exists"):
        make_project("No Replace")
    assert project_path.read_bytes() == original


def test_project_xml_and_source_entry_errors_are_explicit(tmp_path):
    malformed = tmp_path / "broken.xcproj"
    malformed.write_text("<project", encoding="utf-8")
    with pytest.raises(project.ProjectError, match="parse project XML"):
        project.inspect_project(malformed)
    valid = tmp_path / "valid.xcproj"
    valid.write_text('<project name="valid" />', encoding="utf-8")
    with pytest.raises(project.ProjectError, match="does not exist"):
        project.activate_source(valid, "missing.xc")


def test_activate_source_is_safe_idempotent_and_retains_modules(make_project):
    info = make_project("Activate")
    path = Path(info["project_file"])
    before = project.inspect_project(path)
    source = project.activate_source(path)
    unchanged = project.activate_source(path)
    after = project.inspect_project(path)
    assert source["added"] is False
    assert unchanged["added"] is False
    assert before["modules"] == after["modules"]
    with pytest.raises(project.ProjectError):
        project.activate_source(path, "../outside.xc")


def test_project_discovery_skips_compiler_output(tmp_path, make_project):
    created = make_project("Search Me")
    (tmp_path / "projects" / "debug64").mkdir()
    shutil.copy2(created["project_file"], tmp_path / "projects" / "debug64" / "generated.xcproj")
    direct = project.list_projects(tmp_path / "projects")
    recursive = project.list_projects(tmp_path / "projects", recursive=True)
    assert direct == []
    assert [item["name"] for item in recursive] == ["Search Me"]


def test_project_configuration_inventory_and_atomic_switch_preserve_other_fields(make_project):
    info = make_project("Configuration Switch")
    project_file = Path(info["project_file"])
    tree = project.ET.parse(project_file)
    root = tree.getroot()
    root.find("watches").append(project.ET.Element("item", {"name": "keep-watch"}))
    tree.write(project_file, encoding="utf-8", xml_declaration=True)
    before = project_file.read_bytes()

    inventory = project.list_configurations(project_file)
    assert inventory["active_configuration"] == "发布版"
    assert inventory["active_platform"] == "x64"
    assert {item["name"] for item in inventory["configurations"]} == {"调试版", "发布版"}
    switched = project.set_configuration(project_file, configuration="调试版", platform="x86")
    assert switched["changed"] is True
    assert (switched["configuration"], switched["platform"]) == ("调试版", "x86")
    parsed = project.ET.parse(project_file).getroot()
    assert parsed.find("watches/item").get("name") == "keep-watch"
    assert parsed.find("modules/item").get("path") == "module_base.h"
    assert project.set_configuration(project_file, configuration="调试版", platform="x86")["changed"] is False
    after = project_file.read_bytes()
    with pytest.raises(project.ProjectError, match="必须唯一存在"):
        project.set_configuration(project_file, configuration="不存在")
    with pytest.raises(project.ProjectError, match="至少指定"):
        project.set_configuration(project_file)
    assert project_file.read_bytes() == after
    assert before != after


def test_project_configuration_rejects_missing_platform_without_partial_update(make_project):
    info = make_project("Missing Platform")
    project_file = Path(info["project_file"])
    tree = project.ET.parse(project_file)
    config = tree.getroot().find("./vc/setting/config[@name='调试版']")
    config.remove(config.find("x86"))
    tree.write(project_file, encoding="utf-8", xml_declaration=True)
    before = project_file.read_bytes()
    with pytest.raises(project.ProjectError, match="没有 x86"):
        project.set_configuration(project_file, configuration="调试版", platform="x86")
    assert project_file.read_bytes() == before


def test_project_source_inventory_add_remove_and_path_safety(make_project):
    info = make_project("Source Registration")
    project_file = Path(info["project_file"])
    source = project_file.parent / "extra.xc"
    source.write_text("function main()\nreturn 0\n", encoding="utf-8")
    nested = project_file.parent / "src" / "helper.xcs"
    nested.parent.mkdir()
    nested.write_text("// helper\n", encoding="utf-8")
    inventory = project.list_project_sources(project_file)
    assert inventory["source_count"] == 3
    assert inventory["registered_count"] == 1
    registered = project.add_project_source(project_file, "extra.xc")
    assert registered["added"] is True
    assert project.add_project_source(project_file, "extra.xc")["added"] is False
    nested_registered = project.add_project_source(project_file, "src/helper.xcs")
    assert nested_registered["added"] is True
    assert project.inspect_project(project_file)["modules"] == info["modules"]
    removed = project.remove_project_source(project_file, "extra.xc")
    assert removed["removed"] is True and removed["source_deleted"] is False
    assert source.is_file()
    with pytest.raises(project.ProjectError):
        project.add_project_source(project_file, "../outside.xc")
    with pytest.raises(project.ProjectError):
        project.add_project_source(project_file, "missing.xc")


def test_project_breakpoint_crud_bounds_idempotency_and_diagnostics(make_project):
    info = make_project("Breakpoint Metadata")
    project_file = Path(info["project_file"])
    source = project_file.parent / "main.xc"
    source.write_text("line one\nline two\nline three\n", encoding="utf-8")
    initial = project.list_project_breakpoints(project_file)
    assert initial["breakpoint_count"] == 0
    assert project.set_project_breakpoint(project_file, "main.xc", 2)["added"] is True
    assert project.set_project_breakpoint(project_file, "main.xc", 2)["changed"] is False
    listed = project.list_project_breakpoints(project_file)
    assert listed["breakpoint_count"] == 1
    assert listed["files"][0]["breakpoints"] == [{"line": 2, "valid": True}]
    before_invalid = project_file.read_bytes()
    with pytest.raises(project.ProjectError, match="超出源码范围"):
        project.set_project_breakpoint(project_file, "main.xc", 4)
    assert project_file.read_bytes() == before_invalid
    assert project.set_project_breakpoint(project_file, "main.xc", 2, remove=True)["removed"] is True
    assert project.list_project_breakpoints(project_file)["breakpoint_count"] == 0

    tree = project.ET.parse(project_file)
    breakpoints = tree.getroot().find("breakpoints")
    file_node = project.ET.SubElement(breakpoints, "file", {"value": "missing.xc"})
    project.ET.SubElement(file_node, "item", {"lineno": "30"})
    tree.write(project_file, encoding="utf-8", xml_declaration=True)
    diagnostics = project.list_project_breakpoints(project_file)["diagnostics"]
    assert {item["code"] for item in diagnostics} == {"missing-breakpoint-source", "invalid-breakpoint-line"}


def test_ui_template_catalog_metadata_filter_payload_and_copy(make_project, tmp_path):
    root = make_project.ide_root / "data" / "template" / "皮肤"
    template_dir = root / "button skin"
    payload = template_dir / "project"
    (payload / "image").mkdir(parents=True)
    (payload / "layout.xml").write_text("<buttonUI />", encoding="utf-8")
    (payload / "image" / "normal.png").write_bytes(b"png")
    (payload / "Debug").mkdir()
    (payload / "Debug" / "skip.exe").write_bytes(b"old")
    (payload / "obj").mkdir()
    (payload / "obj" / "skip.obj").write_bytes(b"old")
    (template_dir / "template.config").write_text(
        "<xc_template><common/><name>三态按钮皮肤</name><type>皮肤</type><versionXCGUI>2.6</versionXCGUI>"
        "<author>本地测试</author><date>2026</date><objectType>buttonUI</objectType><childType/>"
        "<item/><explain>普通按钮状态贴图</explain><image/><path>project</path></xc_template>", encoding="utf-8")
    layout_dir = make_project.ide_root / "data" / "template" / "布局模板" / "sample layout"
    (layout_dir / "project").mkdir(parents=True)
    (layout_dir / "project" / "layout.xml").write_text("<windowUI />", encoding="utf-8")
    (layout_dir / "template.config").write_text(
        "<xc_template><name>样例布局</name><type>布局模板</type><path>project</path></xc_template>",
        encoding="utf-8")

    catalog = ui_templates.list_ui_templates(ide_root=make_project.ide_root, query="buttonUI")
    assert catalog["count"] == 1
    item = catalog["templates"][0]
    assert item["name"] == "三态按钮皮肤" and item["object_type"] == "buttonUI"
    assert ui_templates.list_ui_templates(ide_root=make_project.ide_root,
                                          category="布局模板")["count"] == 1
    inspected = ui_templates.inspect_ui_template(item["id"], ide_root=make_project.ide_root)
    assert inspected["file_count"] == 2
    destination = ui_templates.copy_ui_template(tmp_path / "assets", "button copy", item["id"],
                                               ide_root=make_project.ide_root)
    copied = Path(destination["destination"])
    assert destination["file_count"] == 2
    assert (copied / "layout.xml").is_file() and (copied / "image" / "normal.png").is_file()
    assert not (copied / "Debug").exists() and not (copied / "obj").exists()
    with pytest.raises(ui_templates.UITemplateError, match="already exists"):
        ui_templates.copy_ui_template(tmp_path / "assets", "button copy", item["id"],
                                      ide_root=make_project.ide_root)
    with pytest.raises(ui_templates.UITemplateError, match="installed template catalog"):
        ui_templates.copy_ui_template(root, "unsafe", item["id"], ide_root=make_project.ide_root)


def test_ui_template_search_skips_malformed_metadata_and_bad_payload(make_project):
    root = make_project.ide_root / "data" / "template" / "皮肤"
    malformed = root / "broken" / "template.config"
    malformed.parent.mkdir(parents=True)
    malformed.write_text("<xc_template", encoding="utf-8")
    unsafe = root / "unsafe" / "template.config"
    unsafe.parent.mkdir()
    unsafe.write_text("<xc_template><name>Unsafe</name><type>皮肤</type><path>../outside</path></xc_template>",
                      encoding="utf-8")
    assert ui_templates.list_ui_templates(ide_root=make_project.ide_root)["count"] == 0


def test_theme_catalog_extracts_native_editor_configuration_without_writing(make_project):
    root = make_project.ide_root / "data" / "theme" / "Fixture Theme"
    root.mkdir(parents=True)
    (root / "xctheme.config").write_text(
        '<xc_theme><font name="微软雅黑" size="9" /><skin path="data/xml/style1.css" />'
        '<designViewColor color="#FF28282D" /><editor><font name="Source Code Pro" '
        'nameZh="等宽字体" size="11" /><tabSize size="4" /><rowSpace value="8" />'
        '<editor_color margin.breakpoint="#FFE41414" margin.runRowArrow="#FFFFD837" />'
        '</editor></xc_theme>', encoding="utf-8")
    (make_project.ide_root / "data" / "xml").mkdir()
    skin_file = make_project.ide_root / "data" / "xml" / "style1.css"
    skin_file.write_text("/* local skin */", encoding="utf-8")

    catalog = themes.list_themes(ide_root=make_project.ide_root)
    assert catalog["count"] == 1
    entry = catalog["themes"][0]
    assert entry["id"] == "Fixture Theme/xctheme"
    assert entry["editor_font"] == "等宽字体" and entry["tab_size"] == "4"
    assert entry["breakpoint_color"] == "#FFE41414"
    assert Path(entry["skin_file"]) == skin_file.resolve()
    before = (root / "xctheme.config").read_bytes()
    detail = themes.inspect_theme(entry["id"], ide_root=make_project.ide_root)
    assert detail["design_view_color"] == "#FF28282D"
    assert (root / "xctheme.config").read_bytes() == before
    with pytest.raises(themes.ThemeError):
        themes.inspect_theme("../outside/xctheme", ide_root=make_project.ide_root)


def test_project_watch_and_bookmark_metadata_crud_preserves_native_shapes(make_project):
    info = make_project("Debug Metadata")
    project_file = Path(info["project_file"])
    source = project_file.parent / "main.xc"
    source.write_text("line one\nline two\nline three\n", encoding="utf-8")
    watch = project.set_project_debug_item(project_file, "watches", "count")
    assert watch["added"] is True
    assert project.set_project_debug_item(project_file, "watches", "count")["changed"] is False
    bookmark = project.set_project_debug_item(project_file, "bookmarks", "main.xc", line=3)
    assert bookmark["added"] is True
    metadata = project.list_project_debug_metadata(project_file)
    assert metadata["watches"] == [{"name": "count"}]
    assert metadata["bookmarks"] == [{"file": "main.xc", "lineno": "3"}]
    assert project.set_project_debug_item(project_file, "watches", "count", remove=True)["removed"] is True
    assert project.set_project_debug_item(project_file, "bookmarks", "main.xc", line=3,
                                          remove=True)["removed"] is True
    with pytest.raises(project.ProjectError, match="书签行号超出"):
        project.set_project_debug_item(project_file, "bookmarks", "main.xc", line=4)
    with pytest.raises(project.ProjectError, match="监视表达式"):
        project.set_project_debug_item(project_file, "watches", "first\nsecond")
    assert project.inspect_project(project_file)["modules"] == info["modules"]


def test_ide_template_catalog_finds_native_xuan_projects(make_project):
    template_directory = (make_project.ide_root / "data" / "template" / "项目模板" / "炫语言" /
                          "空白窗口程序" / "空白窗口程序" / "project")
    template_directory.mkdir(parents=True)
    shutil.copytree(make_project.template_path, template_directory, dirs_exist_ok=True)
    result = templates.list_templates(ide_root=make_project.ide_root)
    assert result["count"] == 1
    item = result["templates"][0]
    assert item["id"].endswith("template")
    assert item["configurations"] == ["调试版", "发布版"]
    assert item["platform"] == "x64"


def test_create_project_from_template_preserves_native_configuration_and_retargets_name(make_project, tmp_path):
    template_directory = (make_project.ide_root / "data" / "template" / "项目模板" / "炫语言" /
                          "空白窗口程序" / "空白窗口程序" / "project")
    template_directory.mkdir(parents=True)
    shutil.copytree(make_project.template_path, template_directory, dirs_exist_ok=True)
    catalog = templates.list_templates(ide_root=make_project.ide_root)
    item = catalog["templates"][0]
    result = templates.create_from_template(tmp_path / "template output", "Template Copy", item["id"],
                                            ide_root=make_project.ide_root)
    project_file = Path(result["project_file"])
    assert project_file.is_file()
    assert result["name"] == "Template Copy"
    assert result["configuration"] == "调试版"
    assert result["platform"] == "x64"
    assert result["configuration_preserved"] is True
    assert result["platform_preserved"] is True
    assert result["modules"] == [{"path": "module_base.h", "name": "基础模块"}]
    assert (project_file.parent / "main.xc").is_file()


def test_create_project_from_template_can_override_existing_platform_and_config(make_project, tmp_path):
    template_directory = (make_project.ide_root / "data" / "template" / "项目模板" / "炫语言" /
                          "空白窗口程序" / "空白窗口程序" / "project")
    template_directory.mkdir(parents=True)
    shutil.copytree(make_project.template_path, template_directory, dirs_exist_ok=True)
    item = templates.list_templates(ide_root=make_project.ide_root)["templates"][0]
    result = templates.create_from_template(tmp_path / "overridden", "Override", item["id"],
                                            ide_root=make_project.ide_root,
                                            configuration="发布版", platform="x86")
    assert (result["configuration"], result["platform"]) == ("发布版", "x86")
    with pytest.raises(templates.TemplateError, match="没有编译配置"):
        templates.create_from_template(tmp_path / "bad-config", "Bad", item["id"],
                                       ide_root=make_project.ide_root, configuration="不存在")


def _install_example(make_project, relative="炫彩界面库-示例/炫-按钮/按钮.xcproj"):
    example_root = make_project.ide_root / "data" / "示例"
    project_file = example_root / relative
    project_file.parent.mkdir(parents=True)
    shutil.copy2(make_project.template_path / "template.xcproj", project_file)
    shutil.copy2(make_project.template_path / "main.xc", project_file.parent / "main.xc")
    return example_root, project_file


def test_example_library_indexes_searches_and_describes_native_projects(make_project):
    example_root, project_file = _install_example(make_project)
    (project_file.parent / "resource.res").write_text("<resources />", encoding="utf-8")
    (project_file.parent / "Debug").mkdir()
    (project_file.parent / "Debug" / "ignored.exe").write_bytes(b"MZ")

    listing = examples.list_examples(ide_root=make_project.ide_root, query="按钮")
    assert listing["count"] == 1
    assert listing["examples"][0]["id"] == "炫彩界面库-示例/炫-按钮/按钮.xcproj"
    assert listing["examples"][0]["valid"] is True
    details = examples.inspect_example(listing["examples"][0]["id"], ide_root=make_project.ide_root)
    assert details["file_count"] == 3
    assert {item["path"] for item in details["files"]} == {"按钮.xcproj", "main.xc", "resource.res"}
    assert details["project"]["modules"] == [{"path": "module_base.h", "name": "基础模块"}]
    assert project_file.is_relative_to(example_root)


@pytest.mark.parametrize("identifier", ["", "../outside.xcproj", "C:/outside.xcproj", "sample.txt"])
def test_example_lookup_rejects_non_relative_or_non_project_ids(make_project, identifier):
    _install_example(make_project)
    with pytest.raises(examples.ExampleError):
        examples.inspect_example(identifier, ide_root=make_project.ide_root)


def test_example_copy_retargets_project_and_preserves_native_files_without_build_outputs(make_project, tmp_path):
    _example_root, source_project = _install_example(make_project)
    source_hash = hashlib.sha256(source_project.read_bytes()).hexdigest()
    source_dir = source_project.parent
    (source_dir / "resource.res").write_text("<resources />", encoding="utf-8")
    (source_dir / "UI_ZIP.zip").write_bytes(b"native archive")
    (source_dir / "Debug").mkdir()
    (source_dir / "Debug" / "old.exe").write_bytes(b"MZ")
    (source_dir / "obj").mkdir()
    (source_dir / "obj" / "old.obj").write_bytes(b"object")

    result = examples.copy_example(tmp_path / "derived", "按钮副本", "炫彩界面库-示例/炫-按钮/按钮.xcproj",
                                   ide_root=make_project.ide_root)
    target = Path(result["project_file"])
    assert target == tmp_path / "derived" / "按钮副本" / "按钮副本.xcproj"
    assert result["name"] == "按钮副本"
    assert result["platform"] == "x64"
    assert result["configuration"] == "调试版"
    assert result["modules"] == [{"path": "module_base.h", "name": "基础模块"}]
    assert (target.parent / "main.xc").is_file()
    assert (target.parent / "resource.res").is_file() and (target.parent / "UI_ZIP.zip").is_file()
    assert not (target.parent / "Debug").exists() and not (target.parent / "obj").exists()
    assert result["excluded_build_artifacts"] is True
    assert hashlib.sha256(source_project.read_bytes()).hexdigest() == source_hash
    with pytest.raises(examples.ExampleError, match="已存在"):
        examples.copy_example(tmp_path / "derived", "按钮副本", "炫彩界面库-示例/炫-按钮/按钮.xcproj",
                              ide_root=make_project.ide_root)


def test_example_copy_rejects_destinations_inside_the_installed_example_catalog(make_project):
    example_root, _source_project = _install_example(make_project)
    with pytest.raises(examples.ExampleError, match="示例目录内"):
        examples.copy_example(example_root / "derived", "Unsafe", "炫彩界面库-示例/炫-按钮/按钮.xcproj",
                              ide_root=make_project.ide_root)


def test_example_list_reports_corrupt_native_projects(make_project):
    root, _ = _install_example(make_project)
    broken = root / "broken" / "broken.xcproj"
    broken.parent.mkdir()
    broken.write_text("<project", encoding="utf-8")
    listing = examples.list_examples(ide_root=make_project.ide_root)
    invalid = next(item for item in listing["examples"] if item["id"] == "broken/broken.xcproj")
    assert invalid["valid"] is False and "无法解析" in invalid["error"]


def test_layout_inspector_supports_xcgui_multi_root_and_resource_references(make_project, tmp_path):
    info = make_project("Interface Inspection")
    project_dir = Path(info["directory"])
    (project_dir / "资源文件").mkdir()
    (project_dir / "资源文件" / "resource.res").write_text(
        '<resources><type_image><image name="ok.svg" value="svg\\ok.svg" /></type_image>'
        '<type_font><font name="yahei_10" size="10" />'
        '<font name="missing" size="10" fontFile="font\\missing.ttf" /></type_font></resources>', encoding="utf-8")
    (project_dir / "资源文件" / "svg").mkdir()
    (project_dir / "资源文件" / "svg" / "ok.svg").write_text("<svg />", encoding="utf-8")
    (project_dir / "main.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<!--窗口布局文件-->\n<head />\n'
        '<windowUI><layoutEleUI name="root"><buttonUI name="ok" font="@yahei_10" image="@ok.svg" />'
        '</layoutEleUI></windowUI>', encoding="utf-8")
    result = interface.inspect_interface(info["project_file"])
    assert result["ok"] is True
    assert result["layoutCount"] == 1
    assert result["validLayoutCount"] == 1
    assert result["layouts"][0]["root"] == "windowUI"
    assert result["layouts"][0]["headCount"] == 1
    assert result["errorCount"] == 0
    assert result["warningCount"] == 1
    assert result["diagnostics"][0]["code"] == "missing-resource-asset"


def test_layout_inspector_verifies_ui_zip_and_rejects_escaping_paths(make_project):
    info = make_project("UI Zip")
    project_dir = Path(info["directory"])
    import zipfile
    with zipfile.ZipFile(project_dir / "UI_ZIP.zip", "w") as archive:
        archive.writestr("布局文件/main.xml", '<head /><windowUI><buttonUI name="ok" /></windowUI>')
        archive.writestr("../outside.txt", "unsafe")
    result = interface.inspect_interface(info["project_file"])
    assert result["uiZipCount"] == 1
    assert result["validUiZipCount"] == 0
    assert any(item["code"] == "ui-zip" for item in result["diagnostics"])
    assert any("越界路径" in item["message"] for item in result["diagnostics"])


def test_project_doctor_finds_missing_entries_modules_and_broken_layout(make_project):
    info = make_project("Needs Doctor")
    module_root = make_project.ide_root / "data" / "XC-Module"
    module_root.mkdir(parents=True)
    (module_root / "module_base.h").write_text("//@模块名称 基础模块\n", encoding="utf-8")
    project_file = Path(info["project_file"])
    tree = project.ET.parse(project_file)
    root = tree.getroot()
    root.find("codeExpand").append(project.ET.Element("item", {"file": "missing.xc", "state": "1,"}))
    root.find("modules").append(project.ET.Element("item", {"path": "module_not_installed.h", "name": "missing"}))
    tree.write(project_file, encoding="utf-8", xml_declaration=True)
    (project_file.parent / "main.xml").write_text("<head /><windowUI><buttonUI></windowUI>", encoding="utf-8")
    result = doctor.inspect_project_health(project_file, ide_root=make_project.ide_root)
    assert result["ok"] is False
    assert result["checks"]["missingSourceCount"] == 1
    assert result["checks"]["missingModuleCount"] == 1
    assert {item["code"] for item in result["diagnostics"]} >= {
        "missing-source-entry", "missing-module", "layout-parse"}


def test_session_initialization_undo_redo_audit_and_history(tmp_path):
    session_path = tmp_path / "session.json"
    original = Session(session_path)
    one = tmp_path / "one" / "one.xcproj"
    two = tmp_path / "two" / "two.xcproj"
    original.select(project=one, action="first")
    original.save()
    next_session = Session(session_path)
    next_session.select(project=two, action="second")
    next_session.record_action("build", ok=True)
    next_session.save()
    assert Session(session_path).project == str(two.resolve())
    assert len(Session(session_path).history()) == 2
    assert next_session.undo()["project"] == str(one.resolve())
    assert next_session.redo()["project"] == str(two.resolve())
    next_session.save()
    loaded = Session(session_path)
    assert loaded.state["audit"][-1]["action"] == "build"
    assert loaded.state["revision"] == 3
    with pytest.raises(ValueError, match="between 1 and"):
        loaded.history(51)


def test_session_invalid_content_and_concurrent_revision(tmp_path):
    location = tmp_path / "session.json"
    location.write_text("not json", encoding="utf-8")
    stale = Session(location)
    fresh = Session(location)
    stale.select(project=tmp_path / "old.xcproj")
    stale.save()
    fresh.select(project=tmp_path / "new.xcproj")
    with pytest.raises(RuntimeError, match="changed concurrently"):
        fresh.save()
    assert Session(location).project == str((tmp_path / "old.xcproj").resolve())


def test_session_limit_and_malformed_history_are_bounded(tmp_path):
    session = Session(tmp_path / "broken-structure.json")
    session.state["revision"] = "broken"
    session.state["undo"] = ["invalid", {}]
    assert Session._empty()["schema_version"] == session.VERSION
    source = tmp_path / "seed.json"
    source.write_text(json.dumps({"schema_version": 1, "revision": "bad", "project": None,
                                  "undo": ["bad", None, {}], "redo": ["bad"]}), encoding="utf-8")
    loaded = Session(source)
    assert loaded.revision == 0
    assert loaded._undo == [None, {}]
    assert loaded._redo == []
    empty = Session(tmp_path / "empty-undo.json")
    with pytest.raises(ValueError, match="There is no"):
        empty.undo()


def test_session_save_protects_json_from_simultaneous_readers(tmp_path):
    location = tmp_path / "parallel.json"
    barrier = threading.Barrier(4)
    errors = []

    def writer(index):
        try:
            target = Session(location)
            target.select(project=tmp_path / f"{index}.xcproj")
            barrier.wait(timeout=5)
            target.save()
        except Exception as exc:  # expected revision conflict is safe, malformed JSON is not
            if "changed concurrently" not in str(exc):
                errors.append(exc)

    workers = [threading.Thread(target=writer, args=(index,)) for index in range(4)]
    for thread in workers:
        thread.start()
    for thread in workers:
        thread.join(timeout=10)
    parsed = json.loads(location.read_text(encoding="utf-8"))
    assert not errors
    assert parsed["revision"] >= 1
    assert isinstance(parsed["project"], str)


def test_local_path_rules_match_project_and_module_roots_and_reject_prefix_escapes(tmp_path):
    ide = tmp_path / "ide"
    (ide / "data" / "XC-Module").mkdir(parents=True)
    (ide / "data" / "XC-Module-dev").mkdir()
    (ide / "data" / "plug").mkdir()
    (ide / "炫彩IDE.exe").write_bytes(b"")
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    project_file = project_dir / "app.xcproj"
    project_file.write_text('<project name="app" />', encoding="utf-8")
    assert validate_path(project_dir / "main.xc", project=project_file, ide_root=ide) == project_dir / "main.xc"
    assert validate_path(ide / "data" / "XC-Module-dev" / "module.h", project=project_file, ide_root=ide)
    with pytest.raises(FileOperationError, match="outside"):
        validate_path(tmp_path / "project sibling" / "escape.xc", project=project_file, ide_root=ide)
    assert validate_path(tmp_path / "elsewhere" / "explicit.txt", allow_outside=True)


def test_local_editor_preserves_utf8_bom_crlf_and_round_trips(tmp_path, make_project):
    info = make_project("Local Files")
    source = Path(info["directory"]) / "main.xc"
    before = b"\xef\xbb\xbfold\r\nline\r\n"
    source.write_bytes(before)
    loaded = read_file(source, project=info["project_file"], ide_root=make_project.ide_root)
    assert (loaded["encoding"], loaded["bom"], loaded["crlf"]) == ("utf-8", True, True)
    assert loaded["content"] == "old\r\nline\r\n"
    result = write_file(source, "新内容\n下一行\n", project=info["project_file"], ide_root=make_project.ide_root)
    assert result["verified"] and result["bom"] and result["crlf"]
    assert source.read_bytes() == "\ufeff新内容\r\n下一行\r\n".encode("utf-8")
    assert result["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()


def test_local_editor_detects_gb18030_and_rejects_binary(tmp_path):
    source = tmp_path / "legacy.txt"
    source.write_bytes("旧编码".encode("gb18030"))
    loaded = read_file(source, allow_outside=True)
    assert loaded["encoding"] == "gb18030"
    result = write_file(source, "新内容", allow_outside=True)
    assert result["encoding"] == "gb18030"
    assert source.read_bytes().decode("gb18030") == "新内容"
    source.write_bytes(b"\x00\x01\x02")
    with pytest.raises(FileOperationError, match="二进制"):
        read_file(source, allow_outside=True)


def test_module_library_list_search_and_project_references(make_project, tmp_path):
    info = make_project("Local Modules")
    root = make_project.ide_root / "data" / "XC-Module"
    headers = root / "01_基础与综合"
    headers.mkdir(parents=True)
    (headers / "module_sample.h").write_text(
        "//@模块名称 本地示例模块\n//@版本 1.2\n//@作者 codex\n"
        "//@模块备注 包含网络和测试功能\n//@依赖 module_base.h; module_other.h\n",
        encoding="utf-8")
    listed = list_modules(ide_root=make_project.ide_root, project_file=info["project_file"], limit=20)
    sample = next(module for module in listed["modules"] if module["file"] == "module_sample.h")
    assert sample["name"] == "本地示例模块"
    assert sample["deps"] == ["module_base.h", "module_other.h"]
    assert sample["inProject"] is False
    assert search_modules("网络", ide_root=make_project.ide_root)["hits"][0]["file"] == "module_sample.h"
    assert search_modules(depends_on="module_base.h", ide_root=make_project.ide_root)["hits"][0]["file"] == "module_sample.h"
    (headers / "module_base.h").write_text("//@模块名称 根模块\n", encoding="utf-8")
    (headers / "module_other.h").write_text("//@模块名称 依赖模块\n//@依赖 module_base.h\n", encoding="utf-8")
    plan = plan_module_dependencies("module_sample.h", ide_root=make_project.ide_root)
    assert plan["ok"] is True
    assert plan["order"] == ["module_base.h", "module_other.h", "module_sample.h"]

    added = add_module(info["project_file"], "module_sample.h", ide_root=make_project.ide_root)
    assert added["added"] and added["restartRequired"]
    dependency_addition = add_modules(info["project_file"], ["module_sample.h"], ide_root=make_project.ide_root,
                                      with_dependencies=True)
    assert {item["file"] for item in dependency_addition["addedModules"]} == {"module_other.h"}
    assert dependency_addition["dependencyOrder"] == ["module_base.h", "module_other.h", "module_sample.h"]
    assert {item["path"] for item in project.inspect_project(info["project_file"])["modules"]} == {
        "module_base.h", "module_other.h", "module_sample.h"}
    assert not add_modules(info["project_file"], ["module_sample.h"], ide_root=make_project.ide_root,
                           with_dependencies=True)["added"]
    assert not add_module(info["project_file"], "module_sample.h", ide_root=make_project.ide_root)["added"]
    assert next(item for item in project.inspect_project(info["project_file"])["modules"]
                if item["path"] == "module_sample.h")["name"] == "本地示例模块"
    removed = remove_module(info["project_file"], "module_sample.h")
    assert removed["removed"] and removed["restartRequired"]
    assert not remove_module(info["project_file"], "module_sample.h")["removed"]
    with pytest.raises(ModuleError, match="找不到"):
        add_module(info["project_file"], "module_missing.h", ide_root=make_project.ide_root)


def test_module_dependency_plan_rejects_cycles_missing_and_ambiguous_edges(make_project, tmp_path):
    info = make_project("Module Dependency Diagnostics")
    root = make_project.ide_root / "data" / "XC-Module"
    first = root / "group_a"
    second = root / "group_b"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    (first / "module_cycle_a.h").write_text("//@依赖 module_cycle_b.h\n", encoding="utf-8")
    (first / "module_cycle_b.h").write_text("//@依赖 module_cycle_a.h\n//@依赖 module_missing.h\n",
                                            encoding="utf-8")
    (first / "module_collision.h").write_text("//@模块名称 A\n", encoding="utf-8")
    (second / "module_collision.h").write_text("//@模块名称 B\n", encoding="utf-8")
    plan = plan_module_dependencies("module_cycle_a.h", ide_root=make_project.ide_root)
    assert plan["ok"] is False
    assert len(plan["cycles"]) == 1
    assert any(item["code"] == "missing-module-dependency" for item in plan["diagnostics"])
    (first / "module_ambiguous_root.h").write_text("//@依赖 module_collision.h\n", encoding="utf-8")
    ambiguous = plan_module_dependencies("module_ambiguous_root.h", ide_root=make_project.ide_root)
    assert ambiguous["ok"] is False
    with pytest.raises(ModuleError, match="module_collision"):
        add_modules(info["project_file"], ["module_ambiguous_root.h"], ide_root=make_project.ide_root,
                    with_dependencies=True)
    assert project.inspect_project(info["project_file"])["modules"] == info["modules"]


def test_cli_module_dependencies_and_add_with_dependency_plan(make_project):
    info = make_project("CLI Module Dependencies")
    module_root = make_project.ide_root / "data" / "XC-Module" / "small-dependency-set"
    module_root.mkdir(parents=True)
    (module_root / "module_dep_base.h").write_text("//@模块名称 依赖基础\n", encoding="utf-8")
    (module_root / "module_dep_child.h").write_text("//@模块名称 依赖子项\n//@依赖 module_dep_base.h\n",
                                                    encoding="utf-8")
    project_path = info["project_file"]
    planned = CliRunner().invoke(cli, ["--json", "--ide", str(make_project.ide_root), "module", "dependencies",
                                      "module_dep_child.h"])
    assert planned.exit_code == 0, planned.output
    assert json.loads(planned.output)["order"] == ["module_dep_base.h", "module_dep_child.h"]

    added = CliRunner().invoke(cli, ["--json", "--ide", str(make_project.ide_root), "--project", project_path,
                                    "module", "add", "--file", "module_dep_child.h", "--with-dependencies"])
    assert added.exit_code == 0, added.output
    result = json.loads(added.output)
    assert result["dependencyOrder"] == ["module_dep_base.h", "module_dep_child.h"]
    assert [item["path"] for item in project.inspect_project(project_path)["modules"]] == [
        "module_base.h", "module_dep_base.h", "module_dep_child.h"]

    dry_run_path = Path(info["project_file"])
    before = dry_run_path.read_bytes()
    dry_run = CliRunner().invoke(cli, ["--json", "--dry-run", "--ide", str(make_project.ide_root),
                                       "--project", project_path, "module", "add", "--file",
                                       "module_dep_child.h", "--with-dependencies"])
    assert dry_run.exit_code == 0
    assert json.loads(dry_run.output)["with_dependencies"] is True
    assert dry_run_path.read_bytes() == before


def test_native_pe_reader_accepts_x64_and_refuses_invalid_headers(tmp_path):
    path = tmp_path / "fresh.exe"
    data = bytearray(256)
    data[0:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 128)
    data[128:132] = b"PE\0\0"
    struct.pack_into("<H", data, 132, 0x8664)
    path.write_bytes(data)
    observed = build.inspect_pe(path)
    assert observed["architecture"] == "AMD64"
    assert observed["bytes"] == len(data)
    assert len(observed["sha256"]) == 64
    data[128:132] = b"NOPE"
    path.write_bytes(data)
    with pytest.raises(build.BuildError, match="PE signature"):
        build.inspect_pe(path)


@pytest.mark.parametrize(("machine", "architecture"), [(0x14C, "x86"), (0xAA64, "ARM64")])
def test_native_pe_reader_reports_other_machine_types(tmp_path, machine, architecture):
    path = tmp_path / f"{architecture}.exe"
    data = bytearray(200)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 96)
    data[96:100] = b"PE\0\0"
    struct.pack_into("<H", data, 100, machine)
    path.write_bytes(data)
    assert build.inspect_pe(path)["architecture"] == architecture


def test_build_backend_needs_only_the_native_ide(tmp_path):
    root = tmp_path / "ide"
    root.mkdir()
    (root / "炫彩IDE.exe").write_bytes(b"fake executable")
    assert project.resolve_ide_root(root) == root
    assert not (root / "xc-plugin").exists()


def test_build_artifact_discovery_includes_native_release64_output(make_project, tmp_path, monkeypatch):
    """Find the newly built Windows executable in the IDE's real Release64 folder."""
    project_info = make_project("Release64 Artifact")
    project_file = Path(project_info["project_file"])
    ide_root = make_project.ide_root
    started_at_ns = 1_800_000_000_000_000_000
    monkeypatch.setattr(build.time, "time_ns", lambda: started_at_ns)

    def compile_to_release64(*_args, **_kwargs):
        artifact = project_file.parent / "Release64" / (project_file.parent.name + ".exe")
        artifact.parent.mkdir()
        pe = bytearray(512)
        pe[:2] = b"MZ"
        struct.pack_into("<I", pe, 0x3C, 128)
        pe[128:132] = b"PE\0\0"
        struct.pack_into("<H", pe, 132, 0x8664)
        artifact.write_bytes(pe)
        os.utime(artifact, ns=(started_at_ns, started_at_ns))
        return None

    monkeypatch.setattr(build, "_isolated_ide", lambda root, _project: (root, root / "炫彩IDE.exe", root / "data"))
    process = _FakeIDEProcess()
    monkeypatch.setattr(build, "_launch_ide", lambda *_args: process)
    monkeypatch.setattr(build, "_private_desktop", _FakeDesktop)
    monkeypatch.setattr(build, "_native_dialogs", lambda *_args: [])
    monkeypatch.setattr(build, "_remove_isolated_ide", lambda *_args: None)
    ticks = iter([10.0, 11.0, 14.1, 14.2, 16.3, 16.4, 16.5])
    monkeypatch.setattr(build.time, "monotonic", lambda: next(ticks, 17.0))
    monkeypatch.setattr(build.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(build, "_post_f7", compile_to_release64)
    monkeypatch.setattr(build, "_close_ide", lambda *_args, **_kwargs: setattr(process, "returncode", 0))
    result = build.build_project(project_file, ide_root=ide_root)
    assert result["ok"] is True
    assert result["exe"]["path"] == str(project_file.parent / "Release64" / "Release64 Artifact.exe")
    assert result["exe"]["architecture"] == "AMD64"


def test_preview_read_only_latest_does_not_need_or_call_ide(make_project, tmp_path):
    info = make_project("Preview Project")
    bundle_root = tmp_path / "published"
    result = preview.capture(recipe="project", project_path=info["project_file"],
                             root_dir=str(bundle_root), force=True)
    assert result["ok"] and result["status"] == "ok"
    latest = preview.latest(recipe="project", project_path=info["project_file"], root_dir=str(bundle_root))
    assert latest["bundle_id"] == result["bundle_id"]
    assert latest["protocol_version"] == "preview-bundle/v1"
    assert (Path(latest["_bundle_dir"]) / "artifacts" / "ide-state.json").is_file()


class _FakeIDEProcess:
    pid = 123
    returncode = None

    def poll(self):
        return self.returncode

    def close(self):
        pass


class _FakeDesktop:
    name = "xcide-test-unit"
    handle = 123

    def close(self):
        pass

    def observation(self):
        return {}


def test_cli_json_errors_are_valid_and_return_nonzero():
    result = CliRunner().invoke(cli, ["--json", "project", "info", "missing.xcproj"])
    assert result.exit_code == 1
    error = json.loads(result.stderr)
    assert error["ok"] is False
    assert error["error_type"] == "ProjectError"


def test_cli_dry_run_cannot_save_session_or_touch_project(tmp_path):
    project_file = tmp_path / "untouched.xcproj"
    project_file.write_text('<project name="untouched" />', encoding="utf-8")
    session_file = tmp_path / "session.json"
    session_file.write_text('{"schema_version":1,"revision":1,"project":null,"history":[],"undo":[],"redo":[]}', encoding="utf-8")
    before = session_file.read_bytes()
    runner = CliRunner()
    result = runner.invoke(cli, ["--dry-run", "--json", "--project", str(project_file), "--session-file",
                                 str(session_file), "status"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["dry_run"] is True
    assert session_file.read_bytes() == before


def test_cli_new_project_selects_session_and_persists_undo(tmp_path, make_project, monkeypatch):
    # Use the official-template-shaped fixture while keeping all generated files local.
    session_path = tmp_path / "selection.json"
    runner = CliRunner()
    template_path = _fixture_template_path(make_project)
    monkeypatch.setattr(project, "native_template_dir", lambda _root=None: template_path)
    result = runner.invoke(cli, ["--json", "--ide", str(_fixture_ide_root(make_project)), "--session-file", str(session_path), "project", "new",
                                 str(tmp_path / "cli-output"), "Cli Project"])
    assert result.exit_code == 0, result.output
    created = json.loads(result.output)
    saved = Session(session_path)
    assert saved.project == created["project_file"]
    assert saved.state["undo"]
    assert Path(created["project_file"]).is_file()


def test_cli_example_copy_dry_run_has_no_filesystem_or_session_side_effects(tmp_path, make_project):
    session_path = tmp_path / "example-session.json"
    session_path.write_text(json.dumps({"schema_version": 1, "revision": 0, "project": None,
                                       "history": [], "undo": [], "redo": []}), encoding="utf-8")
    before = session_path.read_bytes()
    result = CliRunner().invoke(cli, ["--json", "--dry-run", "--ide", str(make_project.ide_root),
                                      "--session-file", str(session_path), "example", "copy",
                                      str(tmp_path / "would-create"), "Example Copy",
                                      "--id", "category/example.xcproj"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["action"] == "example.copy"
    assert not (tmp_path / "would-create").exists()
    assert session_path.read_bytes() == before


def _fixture_template_path(make_project):
    return make_project.template_path


@pytest.mark.parametrize("second_operation", [
    "project.set_project_debug_item(target, 'watches', 'parallel_watch')",
    "modules.remove_module(target, 'module_base.h')",
])
def test_project_updates_serialize_across_processes(make_project, tmp_path, second_operation):
    info = make_project("Concurrent Changes")
    target = Path(info["project_file"])
    release = tmp_path / "release-first-writer"
    first_code = '''
import sys, time
from pathlib import Path
from cli_anything.xcide.core import project
target, release = Path(sys.argv[1]), Path(sys.argv[2])
original_write = project._atomic_project_xml
def paused_write(path, tree):
    print("READY", flush=True)
    deadline = time.monotonic() + 10
    while not release.exists():
        if time.monotonic() > deadline:
            raise RuntimeError("test release timed out")
        time.sleep(.02)
    original_write(path, tree)
project._atomic_project_xml = paused_write
project.set_configuration(target, configuration="调试版")
'''
    first = subprocess.Popen([sys.executable, "-X", "utf8", "-B", "-c", first_code, str(target), str(release)],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
    second = None
    try:
        assert first.stdout.readline().strip() == "READY"
        second = subprocess.Popen([sys.executable, "-B", "-c",
                                   "import sys; from cli_anything.xcide.core import project, modules; "
                                   "target = sys.argv[1]; " + second_operation, str(target)],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            second.wait(timeout=.5)
        except subprocess.TimeoutExpired:
            pass
        release.touch()
        first_out, first_err = first.communicate(timeout=15)
        second_out, second_err = second.communicate(timeout=15)
        assert first.returncode == 0, first_out + first_err
        assert second.returncode == 0, second_out + second_err
    finally:
        release.touch()
        for child in (first, second):
            if child is not None and child.poll() is None:
                child.terminate()
                child.communicate(timeout=5)
    result = project.inspect_project(target)
    assert result["configuration"] == "调试版"
    if "watches" in second_operation:
        assert project.list_project_debug_metadata(target)["watches"] == [{"name": "parallel_watch"}]
    else:
        assert result["modules"] == []


def test_project_update_refuses_external_change_before_commit(make_project, monkeypatch):
    target = Path(make_project("External Change")["project_file"])
    external = target.read_bytes().replace(b'ui_loadType="1"', b'ui_loadType="2"')
    original_write = project._atomic_project_xml

    def external_save(path, tree):
        path.write_bytes(external)
        original_write(path, tree)

    monkeypatch.setattr(project, "_atomic_project_xml", external_save)
    with pytest.raises(project.ProjectError, match="外部程序修改"):
        project.set_project_debug_item(target, "watches", "will_not_overwrite")
    assert target.read_bytes() == external
    assert not list(target.parent.glob(".*.cli-anything-*"))


@pytest.mark.parametrize(("encoding", "bom"), [("utf-16-le", b"\xff\xfe"), ("utf-16-be", b"\xfe\xff")])
def test_editor_preserves_utf16_bom_and_crlf(tmp_path, encoding, bom):
    target = tmp_path / "source.xc"
    target.write_bytes(bom + "旧内容\r\n下一行\r\n".encode(encoding))
    loaded = read_file(target, allow_outside=True)
    assert (loaded["encoding"], loaded["bom"], loaded["crlf"]) == (encoding, True, True)
    result = write_file(target, "新内容\n下一行\n", allow_outside=True)
    assert result["verified"]
    assert target.read_bytes() == bom + "新内容\r\n下一行\r\n".encode(encoding)
    write_file(target, "显式转换\n", allow_outside=True, no_bom=True)
    assert target.read_bytes() == "显式转换\r\n".encode("utf-8")


def test_template_copy_rejects_source_descendants_before_creating_directories(make_project):
    source = make_project.template_path
    with pytest.raises(project.ProjectError, match="源模板目录内部"):
        project.create_project(source / "nested", "Recursive", make_project.ide_root)
    assert not (source / "nested").exists()
    installed = make_project.ide_root / project.TEMPLATE_RELATIVE
    shutil.copytree(source, installed)
    template_id = templates.list_templates(ide_root=make_project.ide_root)["templates"][0]["id"]
    with pytest.raises(project.ProjectError, match="源模板目录内部"):
        templates.create_from_template(installed / "nested", "Recursive", template_id, make_project.ide_root)
    assert not (installed / "nested").exists()


@pytest.mark.parametrize("deleted", [False, True])
def test_remove_stale_breakpoint_and_bookmark(make_project, deleted):
    info = make_project("Stale Metadata")
    target = Path(info["project_file"])
    source = target.parent / "main.xc"
    project.set_project_breakpoint(target, "main.xc", 2)
    project.set_project_debug_item(target, "bookmarks", "main.xc", line=2)
    if deleted:
        source.unlink()
    else:
        source.write_text("// shortened\n", encoding="utf-8")
    assert project.set_project_breakpoint(target, "main.xc", 2, remove=True)["removed"]
    assert project.set_project_debug_item(target, "bookmarks", "main.xc", line=2, remove=True)["removed"]
    assert project.list_project_breakpoints(target)["breakpoint_count"] == 0
    assert project.list_project_debug_metadata(target)["bookmarks"] == []
    with pytest.raises(project.ProjectError):
        project.set_project_breakpoint(target, "../escape.xc", 2, remove=True)
    with pytest.raises(project.ProjectError):
        project.set_project_debug_item(target, "bookmarks", "main.xc", line=2)


@pytest.mark.parametrize("failure", ["conflict", "disk"])
def test_cli_completed_write_reports_session_warning_without_retry(make_project, tmp_path, monkeypatch, failure):
    info = make_project("Committed Operation")
    session_path = tmp_path / "session.json"
    original_save = Session.save

    def fail_save(session):
        if failure == "disk":
            raise OSError("simulated full disk")
        competing = Session(session.path)
        competing.select(project=tmp_path / "other.xcproj")
        original_save(competing)
        original_save(session)

    monkeypatch.setattr(Session, "save", fail_save)
    result = CliRunner().invoke(cli, ["--json", "--session-file", str(session_path), "--project",
                                     info["project_file"], "project", "debug", "watch-add", "committed"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["ok"] and payload["session_saved"] is False
    assert payload["session_warning"]["operation_completed"] is True
    assert payload["session_warning"]["retry_operation"] is False
    assert result.stderr == ""
    assert project.list_project_debug_metadata(info["project_file"])["watches"] == [{"name": "committed"}]
    if failure == "conflict":
        assert Session(session_path).project == str(tmp_path / "other.xcproj")


def test_cli_session_only_save_failure_does_not_report_success(make_project, tmp_path, monkeypatch):
    info = make_project("Session Failure")

    def fail_save(session):
        raise OSError("session storage unavailable")

    monkeypatch.setattr(Session, "save", fail_save)
    result = CliRunner().invoke(cli, ["--json", "--session-file", str(tmp_path / "session.json"),
                                     "project", "open", info["project_file"]])
    assert result.exit_code == 1
    assert not result.stdout
    assert json.loads(result.stderr)["ok"] is False


def test_repl_does_not_retry_failed_postcommit_session_save(make_project, tmp_path, monkeypatch):
    from cli_anything.xcide import xcide_cli
    info = make_project("REPL Session Warning")
    session_path = tmp_path / "session.json"
    saved = Session(session_path)
    saved.select(project=info["project_file"])
    saved.save()
    commands = iter(["project debug watch-add retained", "session status", "quit"])
    saves = []

    def fail_save(session):
        saves.append(session.path)
        raise OSError("temporary session write failure")

    class Skin:
        def __init__(self, *_args, **_kwargs):
            pass

        def print_banner(self):
            pass

        def create_prompt_session(self):
            return None

        def help(self, _commands):
            pass

        def get_input(self, *_args, **_kwargs):
            return next(commands)

        def print_goodbye(self):
            pass

        def error(self, error):
            pytest.fail(error)

    monkeypatch.setattr(Session, "save", fail_save)
    monkeypatch.setattr(xcide_cli, "ReplSkin", Skin)
    result = CliRunner().invoke(cli, ["--json", "--session-file", str(session_path), "repl"])
    assert result.exit_code == 0, result.output
    first, end = json.JSONDecoder().raw_decode(result.stdout)
    following = json.loads(result.stdout[end:])
    assert first["session_saved"] is False
    assert following["project"] == info["project_file"]
    assert saves == [session_path]
    assert project.list_project_debug_metadata(info["project_file"])["watches"] == [{"name": "retained"}]


def test_session_write_failure_keeps_revision_retryable(tmp_path, monkeypatch):
    session = Session(tmp_path / "session.json")
    session.select(project=tmp_path / "app.xcproj")

    def fail_replace(*_args):
        raise OSError("disk failure")

    with monkeypatch.context() as patch:
        patch.setattr(os, "replace", fail_replace)
        with pytest.raises(OSError, match="disk failure"):
            session.save()
    assert session.revision == 0
    assert session.modified
    session.save()
    assert Session(session.path).revision == 1


@pytest.mark.parametrize("shared_root", [False, True])
def test_preview_cache_and_latest_are_project_scoped(make_project, tmp_path, shared_root):
    from cli_anything.xcide.utils.preview_bundle import find_cached_manifest
    first = Path(make_project("Preview Isolation")["project_file"])
    second = (tmp_path / "second.xcproj") if shared_root else first.with_name("second.xcproj")
    shutil.copy2(first, second)  # Identical XML content must not imply identical source identity.
    root = str(tmp_path / "shared-previews") if shared_root else None
    one = preview.capture(recipe="project", project_path=str(first), root_dir=root)
    with pytest.raises(FileNotFoundError):
        preview.latest(recipe="project", project_path=str(second), root_dir=root)
    assert find_cached_manifest("xcide", "project", "capture", one["cache_key"],
                                project_path=str(second), root_dir=root) is None
    two = preview.capture(recipe="project", project_path=str(second), root_dir=root)
    assert not two["cached"]
    assert one["cache_key"] != two["cache_key"]
    for target, captured in ((first, one), (second, two)):
        assert preview.latest(recipe="project", project_path=str(target), root_dir=root)["bundle_id"] == captured["bundle_id"]
        assert preview.capture(recipe="project", project_path=str(target), root_dir=root)["cached"]


def test_interface_checks_long_comments_known_paths_and_utf16(make_project):
    target = Path(make_project("Layout Discovery")["project_file"])
    root = target.parent
    comment = "<!--" + "padding" * 100 + "-->"
    (root / "main.xml").write_text(comment + "<head/><windowUI>", encoding="utf-8")
    (root / "extra.xml").write_bytes((comment + "<head/><layoutPanel/>").encode("utf-16"))
    (root / "布局文件").mkdir()
    (root / "布局文件" / "broken.xml").write_text("<invalid", encoding="utf-8")
    (root / "unrelated.xml").write_text("<settings><header/><windowUIExample/></settings>", encoding="utf-8")
    result = interface.inspect_interface(str(target))
    assert result["layoutCount"] == 3
    assert result["validLayoutCount"] == 1
    assert {item["path"] for item in result["diagnostics"] if item["code"] == "layout-parse"} == {
        "main.xml", "布局文件/broken.xml"}
    assert result["ok"] is False


def test_interface_include_generated_applies_to_layouts_resources_and_zip(make_project):
    target = Path(make_project("Generated Layouts")["project_file"])
    generated = target.parent / "Release64"
    generated.mkdir()
    (generated / "main.xml").write_text("<head/><windowUI/>", encoding="utf-8")
    (generated / "resource.res").write_text('<resources><type_image><image name="missing" value="missing.png" />'
                                            '</type_image></resources>', encoding="utf-8")
    (generated / "UI_ZIP.zip").write_bytes(b"broken zip")
    assert interface.inspect_interface(str(target))["layoutCount"] == 0
    expanded = interface.inspect_interface(str(target), include_generated=True)
    assert (expanded["layoutCount"], expanded["uiZipCount"], expanded["resourceCatalogs"]) == (1, 1, 1)
    assert {item["code"] for item in expanded["diagnostics"]} >= {"missing-resource-asset", "ui-zip"}


@pytest.mark.parametrize("scenario", ["unrelated", "timeout", "same-size-write", "custom-output", "exited"])
def test_build_requires_configured_stable_output(make_project, tmp_path, monkeypatch, scenario):
    target = Path(make_project("Build Identity")["project_file"])
    expected = target.parent / "Release64" / "Build Identity.exe"
    if scenario == "custom-output":
        tree = project.ET.parse(target)
        selected = tree.getroot().find('./vc/setting/config[@name="发布版"]/x64')
        project.ET.SubElement(selected, "out", {"name": "custom", "out_path": str(tmp_path / "external-$output{literal}")})
        tree.write(target, encoding="utf-8")
        expected = tmp_path / "external-$output{literal}" / "custom.exe"
    started = 1_800_000_000_000_000_000
    clock = {"now": 0.0, "mtime": started, "exited": False}

    def compile_output(*_args):
        artifact = expected if scenario != "unrelated" else target.parent / "helper.exe"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        data = bytearray(512)
        data[:2] = b"MZ"
        struct.pack_into("<I", data, 0x3C, 128)
        data[128:132] = b"PE\0\0"
        struct.pack_into("<H", data, 132, 0x8664)
        artifact.write_bytes(data)
        os.utime(artifact, ns=(started, started))
        if scenario == "exited":
            clock["exited"] = True

    def sleep(seconds):
        clock["now"] += 31 if scenario == "timeout" else seconds
        if scenario == "same-size-write" and expected.exists():
            clock["mtime"] += 1000000000
            os.utime(expected, ns=(clock["mtime"], clock["mtime"]))

    class Process:
        pid = 123
        returncode = 0

        def poll(self):
            return 0 if clock["exited"] else None

        def close(self):
            pass

    monkeypatch.setattr(build.time, "time_ns", lambda: started)
    monkeypatch.setattr(build.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(build.time, "sleep", sleep)
    monkeypatch.setattr(build, "_isolated_ide", lambda root, p: (root, root / "炫彩IDE.exe", root / "data"))
    monkeypatch.setattr(build, "_launch_ide", lambda *_args: Process())
    monkeypatch.setattr(build, "_private_desktop", _FakeDesktop)
    monkeypatch.setattr(build, "_native_dialogs", lambda *_args: [])
    monkeypatch.setattr(build, "_post_f7", compile_output)
    monkeypatch.setattr(build, "_close_ide", lambda *_args, **_kwargs: clock.update(exited=True))
    monkeypatch.setattr(build, "_remove_isolated_ide", lambda *_args: None)
    result = build.build_project(target, ide_root=make_project.ide_root, timeout=30)
    assert result["ok"] == (scenario == "custom-output")
    assert result["expected_executable"] == str(expected)
    if scenario != "custom-output":
        assert result["exe"] is None


@pytest.mark.parametrize("unsupported", ["dll", "macro"])
def test_build_rejects_unresolvable_output_before_launch(make_project, monkeypatch, unsupported):
    target = Path(make_project("Unsupported Output")["project_file"])
    tree = project.ET.parse(target)
    selected = tree.getroot().find('./vc/setting/config[@name="发布版"]/x64')
    if unsupported == "dll":
        selected.find("common").set("type", "dll")
    else:
        project.ET.SubElement(selected, "out", {"out_path": "$(OutputDir)"})
    tree.write(target, encoding="utf-8")
    monkeypatch.setattr(build, "_isolated_ide", lambda *_args: pytest.fail("must reject before preparing an IDE"))
    with pytest.raises(build.BuildError):
        build.build_project(target, ide_root=make_project.ide_root)


def test_rendered_html_links_survive_relocation(tmp_path):
    renderer_path = Path(__file__).resolve().parents[3] / "tools" / "render_markdown.py"
    spec = importlib.util.spec_from_file_location("xcide_renderer", renderer_path)
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    source = tmp_path / "original" / "package"
    source.mkdir(parents=True)
    (source.parent / "DOCS.html").write_text("outside package", encoding="utf-8")
    (source / "other page.md").write_text("# Other", encoding="utf-8")
    (source / "other page.html").write_text("<html>other</html>", encoding="utf-8")
    md = source / "README.md"
    md.write_text("# Portable\n\n[Other](other%20page.md#anchor)\n", encoding="utf-8")
    output = source / "README.html"
    output.write_text(renderer.page(md, output), encoding="utf-8")
    relocated = tmp_path / "relocated"
    shutil.copytree(source, relocated)
    assert source.resolve().is_relative_to(tmp_path.resolve()) and source.resolve() != tmp_path.resolve()
    shutil.rmtree(source)  # A migrated bundle must not depend on its original directory.
    text = (relocated / "README.html").read_text(encoding="utf-8")

    class Links(HTMLParser):
        targets = []

        def handle_starttag(self, tag, attrs):
            if tag == "a":
                self.targets.extend(value for key, value in attrs if key == "href")

    parser = Links()
    parser.feed(text)
    assert "file:///" not in text and "DOCS.html" not in text
    assert parser.targets == ["other%20page.html#anchor"]
    assert all((relocated / unquote(urlsplit(link).path)).is_file() for link in parser.targets)


def test_native_compiler_diagnostics_require_positive_evidence():
    from cli_anything.xcide.core.diagnostics import parse_output
    blank = parse_output("启动完成")
    assert not blank["ok"] and blank["errorCount"] is None
    summary_only = parse_output("错误列表: 错误(0)")
    assert not summary_only["ok"] and not summary_only["compiled"]
    good = parse_output("编译完成, 耗时: 20毫秒\n错误列表: 错误(0)")
    assert good["ok"] and good["compiled"] and good["errorCount"] == 0
    assert not parse_output("跳过编译\n编译完成, 耗时: 0\n错误列表: 错误(0)")["ok"]
    assert not parse_output("编译完成, 耗时: 20")["ok"]


def test_native_compiler_errors_survive_zero_ide_summary():
    from cli_anything.xcide.core.diagnostics import parse_output
    text = """main.xc(14): 错误 C2065: 未声明标识符
module.obj : error LNK2019: unresolved external symbol
main.xc(9): warning C4996: deprecated
🐞*编译失败, 错误码: 2
错误列表: 错误(0)"""
    result = parse_output(text)
    assert result["failed"] and not result["ok"]
    assert result["errorCount"] == 2 and result["warningCount"] == 1
    assert result["failCode"] == 2
    assert result["diagnostics"][0]["line"] == 14
    assert result["diagnostics"][1]["code"] == "LNK2019"


def test_native_compiler_xc_positions_and_missing_detail():
    from cli_anything.xcide.core.diagnostics import parse_output
    result = parse_output("🐛检查错误: C:\\项目\\main.xc(2), 列(1-5)\n未定义: abc\n错误列表: 共有(2)个错误")
    assert result["errorCount"] == 2
    assert result["diagnostics"][0] == {"kind": "check", "severity": "error", "file": r"C:\项目\main.xc",
                                        "line": 2, "column": 1, "end_column": 5, "message": "未定义: abc"}


@pytest.mark.parametrize("step", [
    {"action": []}, {"action": "click", "x": True, "y": 1},
    {"action": "click", "x": -1, "y": 2}, {"action": "text", "text": ""},
    {"action": "screenshot", "name": "../escape"}, {"action": "key", "key": []},
    {"action": "key", "key": "ALT+F4"}, {"action": "wait", "seconds": float("nan")},
    {"action": "wait", "seconds": 31}, {"action": "close", "timeout": float("inf")},
    {"action": "assert_debug", "contains": "ok", "unknown": 3},
    {"action": "assert_debug", "contains": "ok", "after_action": 1},
])
def test_runtime_scenario_rejects_unsafe_steps(step):
    from cli_anything.xcide.core.runtime import validate_scenario
    with pytest.raises(ValueError):
        validate_scenario({"version": 1, "steps": [step, {"action": "assert_debug", "contains": "OK"}, {"action": "close"}]})


def test_runtime_scenario_requires_assertions_and_exit():
    from cli_anything.xcide.core.runtime import validate_scenario
    for value in [None, {"version": True, "steps": []}, {"version": 1, "steps": [{"action": "close"}]},
                  {"version": 1, "steps": [{"action": "assert_debug", "contains": "OK"}]}]:
        with pytest.raises(ValueError):
            validate_scenario(value)


def test_runtime_invalid_scenario_has_no_side_effects(tmp_path, monkeypatch):
    from cli_anything.xcide.core import runtime
    monkeypatch.setattr(runtime, "DebugProcess", lambda *a, **k: pytest.fail("must not launch"))
    target = tmp_path / "reports"
    with pytest.raises(ValueError):
        runtime.execute(tmp_path / "missing.exe", output=target, scenario={"version": 1, "steps": []})
    assert not target.exists()


def test_runtime_background_input_bounds_identity_and_utf16(monkeypatch):
    from types import SimpleNamespace
    from cli_anything.xcide.utils.win_desktop import Desktop
    desk = object.__new__(Desktop)
    desk.pid = 7
    desk.verify = lambda hwnd: None
    desk.geometry = lambda hwnd: {"size": [50, 50]}
    calls = []
    desk.request = lambda *a, **k: calls.append((a, k))
    assert desk.click(100, 20, 20, None, 1)["method"] == "xcgui-ui-thread-message"
    assert calls[0][1] == {"x": 20, "y": 20}
    with pytest.raises(ValueError, match="客户区"):
        desk.click(100, 50, 20, None, 1)
    with pytest.raises(ValueError, match="UTF-16"):
        desk.type_text(100, "😀" * 2049, None, 1)
    del desk.verify
    desk.owner = lambda hwnd: 99
    with pytest.raises(RuntimeError, match="不属于"):
        desk.verify(100)


def test_f7_targets_main_window_and_rejects_ambiguity(monkeypatch):
    from types import SimpleNamespace
    calls = []

    class Function:
        def __init__(self, fn):
            self.fn = fn

        def __call__(self, *args):
            return self.fn(*args)

    names = {1: "UAC Input Indicator", 2: "XCGUI"}
    api = SimpleNamespace(GetClassNameW=Function(lambda hwnd, buffer, count: setattr(buffer, "value", names[hwnd])),
                          GetWindowTextLengthW=lambda hwnd: 10,
                          PostMessageW=lambda *args: calls.append(args) or 1)
    monkeypatch.setattr(build, "_windows_api", lambda: (api, None))
    monkeypatch.setattr(build, "_ide_windows", lambda *args: [1, 2])
    build._post_f7(7, Path("ide.exe"), 123)
    assert len(calls) == 2 and all(call[0] == 2 and call[2] == 0x76 for call in calls)
    names[1] = "XCGUI"
    with pytest.raises(build.BuildError, match="唯一"):
        build._post_f7(7, Path("ide.exe"), 123)
    assert len(calls) == 2


def test_background_build_preserves_dialog_and_cleanup_failure(make_project, monkeypatch):
    target = Path(make_project("Blocked Build")["project_file"])
    process = _FakeIDEProcess()
    process.terminate_tree = lambda: setattr(process, "returncode", 1)
    monkeypatch.setattr(build, "_isolated_ide", lambda root, p: (root, root / "炫彩IDE.exe", root / "data"))
    monkeypatch.setattr(build, "_launch_ide", lambda *args: process)
    monkeypatch.setattr(build, "_private_desktop", _FakeDesktop)
    monkeypatch.setattr(build, "_native_dialogs", lambda *args: [{"title": "IDE error", "texts": ["invalid handle"]}])
    monkeypatch.setattr(build.time, "sleep", lambda _: None)
    monkeypatch.setattr(build, "_post_f7", lambda *args: None)
    monkeypatch.setattr(build, "_remove_isolated_ide", lambda *args: None)

    def failed_close(*args, **kwargs):
        raise build.BuildError("close timeout")

    monkeypatch.setattr(build, "_close_ide", failed_close)
    result = build.build_project(target, ide_root=make_project.ide_root)
    assert result["ok"] is False and result["terminated"] is True
    assert "对话框" in result["error"] and result["cleanup_error"] == "close timeout"
    assert result["ide_dialogs"][0]["texts"] == ["invalid handle"]


def test_runtime_protocol_shape_and_no_foreground_fallback():
    import ctypes
    from cli_anything.xcide.utils import win_desktop
    assert ctypes.sizeof(win_desktop.Request) == 8284
    source = Path(win_desktop.__file__).read_text("utf-8")
    for forbidden in ("SendInput", "SetCursorPos", "SetForegroundWindow", "SwitchDesktop", "AttachThreadInput", "ImageGrab"):
        assert forbidden not in source
    from cli_anything.xcide.core.runtime import validate_scenario
    with pytest.raises(ValueError, match="UTF-16"):
        validate_scenario({"version": 1, "steps": [{"action": "text", "text": "😀" * 2049},
                                                   {"action": "assert_debug", "contains": "x"}, {"action": "close"}]})


def test_output_bridge_rejects_wrong_identity_and_overflow(tmp_path):
    from cli_anything.xcide.core.diagnostics import read_snapshot
    target = tmp_path / "snapshot.json"
    project = tmp_path / "project.xcproj"
    value = {"pid": 42, "version": 3, "ready": True, "project": str(project), "truncated": False, "text": "ready"}
    target.write_text(json.dumps(value), encoding="utf-8")
    assert read_snapshot(target, 7, project) is None
    assert read_snapshot(target, 42, project)["text"] == "ready"
    with pytest.raises(RuntimeError, match="different project"):
        read_snapshot(target, 42, tmp_path / "other.xcproj")
    target.write_text(json.dumps({**value, "truncated": True}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="limit"):
        read_snapshot(target, 42, project)

