from __future__ import annotations

import json
import os
import subprocess
import hashlib
import shutil
import tempfile
import uuid
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from cli_anything.xcide.core.project import create_project
from cli_anything.xcide.core.session import Session
from cli_anything.xcide.tests.conftest import _resolve_cli


CLI_BASE = _resolve_cli("cli-anything-xcide")


def _run(args: list[str], *, env: dict[str, str] | None = None, check: bool = True):
    command_args = list(args)
    command_env = dict(os.environ)
    for key in ("XC_MCP_TOKEN", "XC_MCP_PROJECT", "XC_MCP_INSTANCE", "XC_MCP_URL", "XC_MCP_INSTANCE_DIR"):
        command_env.pop(key, None)
    if env:
        command_env.update(env)
    if "--session-file" not in command_args:
        command_args[0:0] = ["--session-file", str(Path(tempfile.gettempdir()) / ("cli-anything-xcide-" + uuid.uuid4().hex + ".json"))]
    return subprocess.run(CLI_BASE + command_args, capture_output=True, text=True,
                         encoding="utf-8", errors="replace", env=command_env,
                          timeout=300, check=check)


def _template_root(ide_root: Path) -> Path:
    return ide_root / "data" / "template" / "项目模板" / "炫语言" / "空白窗口程序" / "空白窗口程序" / "project"


class TestCLISubprocess:
    """Run the installed console command just as a script or agent would."""

    @pytest.mark.parametrize("field,value", [("undo", None), ("audit", {}), ("project", []),
                                             ("redo", [{"project": 7}])])
    def test_installed_malformed_session_preserves_data_and_returns_json(self, tmp_path, field, value):
        location = tmp_path / "damaged-session.json"
        raw = json.dumps({**Session._empty(), field: value}).encode("utf-8")
        location.write_bytes(raw)
        result = _run(["--json", "--session-file", str(location), "session", "status"], check=False)
        assert result.returncode == 1 and not result.stdout
        assert field in json.loads(result.stderr)["error"]
        assert location.read_bytes() == raw

    def test_installed_preview_refreshes_after_source_changes(self, tmp_path):
        info = create_project(tmp_path, "Preview Sources", Path(r"I:\xcide"))
        args = ["--json", "--project", info["project_file"], "--session-file", str(tmp_path / "session.json"),
                "preview", "capture", "--root", str(tmp_path / "previews")]
        first = json.loads(_run(args).stdout)
        extra = Path(info["directory"]) / "extra.xc"
        extra.write_text("// extra source", encoding="utf-8")
        second = json.loads(_run(args).stdout)
        assert not second["cached"] and first["bundle_id"] != second["bundle_id"]
        payload = json.loads((Path(second["_bundle_dir"]) / "artifacts/ide-state.json").read_text("utf-8"))
        assert "extra.xc" in payload["project"]["entrypoints"]
        extra.unlink()
        third = json.loads(_run(args).stdout)
        assert third["cached"] and third["bundle_id"] == first["bundle_id"]

    def test_installed_interface_and_doctor_accept_native_object_template(self, tmp_path):
        ide = Path(r"I:\xcide")
        source = ide / "data/template/皮肤/template-关闭按钮/project/layout.xml"
        original = source.read_bytes()
        info = create_project(tmp_path, "Native Object", ide)
        shutil.copyfile(source, Path(info["directory"]) / "layout.xml")
        prefix = ["--json", "--ide", str(ide), "--project", info["project_file"],
                  "--session-file", str(tmp_path / "session.json")]
        result = json.loads(_run(prefix + ["interface", "check"]).stdout)
        layout = next(item for item in result["layouts"] if item["path"] == "layout.xml")
        assert layout["valid"] and layout["root"] == "xc_template_object"
        health = json.loads(_run(prefix + ["project", "doctor"]).stdout)
        assert health["ok"]
        assert source.read_bytes() == original

    def test_editor_commit_survives_session_save_failure_and_preserves_utf16(self, tmp_path):
        info = create_project(tmp_path, "UTF16 Commit", Path(r"I:\xcide"))
        target = Path(info["project_file"]).parent / "main.xc"
        target.write_bytes(b"\xfe\xff" + "旧内容\r\n".encode("utf-16-be"))
        input_file = tmp_path / "input.txt"
        input_file.write_text("新内容\n下一行\n", encoding="utf-8")
        blocked_parent = tmp_path / "session-parent-is-a-file"
        blocked_parent.write_bytes(b"do not overwrite")
        completed = _run(["--json", "--project", info["project_file"], "--session-file",
                          str(blocked_parent / "session.json"), "editor", "write", str(target), str(input_file)])
        result = json.loads(completed.stdout)
        assert result["ok"] and result["verified"]
        assert result["session_saved"] is False
        assert result["session_warning"]["retry_operation"] is False
        assert completed.stderr == ""
        assert target.read_bytes() == b"\xfe\xff" + "新内容\r\n下一行\r\n".encode("utf-16-be")
        assert blocked_parent.read_bytes() == b"do not overwrite"

    def test_stale_debug_entries_can_be_removed_through_installed_commands(self, tmp_path):
        info = create_project(tmp_path, "Stale Entries", Path(r"I:\xcide"))
        args = ["--json", "--project", info["project_file"]]
        _run(args + ["project", "breakpoints", "add", "main.xc", "2"])
        _run(args + ["project", "debug", "bookmark-add", "main.xc", "2"])
        (Path(info["directory"]) / "main.xc").unlink()
        breakpoint = json.loads(_run(args + ["project", "breakpoints", "remove", "main.xc", "2"]).stdout)
        bookmark = json.loads(_run(args + ["project", "debug", "bookmark-remove", "main.xc", "2"]).stdout)
        assert breakpoint["removed"] and bookmark["removed"]

    def test_installed_help(self):
        result = _run(["--help"])
        assert all(name in result.stdout for name in ("project", "preview", "theme", "reference", "archive", "resource"))

    def test_installed_ui_archive_exports_exact_member_without_overwrite(self, tmp_path):
        source = Path(r"I:\xcide\例子\炫彩界面AI项目\UI_ZIP.zip")
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        args = ["--json", "--ide", r"I:\xcide", "--session-file", str(tmp_path / "session.json")]
        listing = json.loads(_run(args + ["archive", "list", str(source), "main.xml"]).stdout)
        member = next(n["id"] for n in listing["items"] if n["id"].endswith("main.xml"))
        text = json.loads(_run(args + ["archive", "read", str(source), member]).stdout)
        assert "<windowUI" in text["content"] and text["source"]["crc_verified"]
        target = tmp_path / "exported-main.xml"
        planned = json.loads(_run(args[:1] + ["--dry-run"] + args[1:] + ["archive", "export", str(source), member, str(target)]).stdout)
        assert planned["dry_run"] and not target.exists()
        result = json.loads(_run(args + ["archive", "export", str(source), member, str(target)]).stdout)
        assert result["created"] and result["verified"]
        assert hashlib.sha256(target.read_bytes()).hexdigest() == text["source"]["sha256"]
        failed = _run(args + ["archive", "export", str(source), member, str(target)], check=False)
        assert failed.returncode == 1 and json.loads(failed.stderr)["ok"] is False
        assert hashlib.sha256(source.read_bytes()).hexdigest() == before

    def test_installed_named_resource_catalog_and_packed_fonts(self):
        source = Path(r"I:\xcide\data\template\项目模板\炫语言\用户模板\暗黑UI\project\UI_ZIP.zip")
        args = ["--json", "--dry-run", "--ide", r"I:\xcide"]
        result = json.loads(_run(args + ["resource", "list", str(source), "--member", "WmUi/Dark/WmUi.res",
                                         "--kind", "type_bkInfo", "--limit", "2"]).stdout)
        assert result["total"] > 100 and result["count"] == 2 and result["next_offset"] == 2
        item = json.loads(_run(args + ["resource", "show", str(source), result["items"][0]["id"],
                                       "--member", "WmUi/Dark/WmUi.res"]).stdout)
        assert item["item"] == result["items"][0]
        fonts = json.loads(_run(args + ["resource", "list", str(source), "--member", "WmUi/WmUi_Base.res",
                                        "--kind", "type_font"]).stdout)
        assets = [a for n in fonts["items"] for a in n["assets"]]
        assert assets and all(a["exists"] for a in assets)
        nested = r"I:\xcide\data\示例\炫彩界面库-高级示例\xc-QQ音乐\resource.res"
        images = json.loads(_run(args + ["resource", "list", nested, "--kind", "type_image", "--limit", "2000"]).stdout)
        folder = next(n for n in images["folders"] if n["name"] == "音乐馆")
        assert len([n for n in images["items"] if folder["id"] in n["folder_ids"]]) == 12
        assert "音乐馆" not in images["duplicate_names"]

    def test_installed_layout_nodes_on_disk_and_in_archive(self):
        args = ["--json", "--dry-run", "--ide", r"I:\xcide"]
        source = r"I:\xcide\data\xml\item_template\ActionView_ListBox_Item.xml"
        nodes = json.loads(_run(args + ["interface", "nodes", source, "--attribute", "content"]).stdout)
        assert nodes["items"] and any(n["bindings"] for n in nodes["items"])
        node = json.loads(_run(args + ["interface", "node", source, nodes["items"][0]["id"]]).stdout)
        assert node["item"] == nodes["items"][0] and "shapeText" in node["xml"]
        zipped = r"I:\xcide\例子\炫彩界面AI项目\UI_ZIP.zip"
        packed = json.loads(_run(args + ["interface", "nodes", zipped, "--member", "布局文件/main.xml", "--tag", "buttonUI"]).stdout)
        assert packed["root"] == "windowUI" and packed["items"]
        assert packed["source"]["crc_verified"] and packed["source"]["archive"]["sha256"]

    def test_installed_reference_catalogs_are_readonly_and_have_native_provenance(self, tmp_path):
        root = Path(r"I:\xcide")
        session = tmp_path / "reference-session.json"
        args = ["--json", "--dry-run", "--ide", str(root), "--session-file", str(session)]
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in [
            root / "data/config/config.config", root / "data/config/codeSnippet.json",
            root / "data/config/sys/propertyList.json", root / "data/config/sys/events.xml"]}
        sources = json.loads(_run(args + ["reference", "sources"]).stdout)
        assert sources["available_count"] == 10
        for source in sources["sources"]:
            kind = source["catalog"]
            page = json.loads(_run(args + ["reference", "search", kind, "--limit", "1"]).stdout)
            assert page["total"] == source["count"] and page["count"] == 1
            item = page["items"][0]
            shown = json.loads(_run(args + ["reference", "show", kind, item["id"]]).stdout)
            assert shown["item"] == item
            assert shown["source"]["sha256"] == hashlib.sha256(Path(shown["source"]["path"]).read_bytes()).hexdigest()
        event = json.loads(_run(args + ["reference", "show", "events", "elementUI/buttonUI/XE_BNCLICK"]).stdout)
        assert "$[UI对象名称]" in event["item"]["declaration"]
        prop = json.loads(_run(args + ["reference", "search", "properties", "buttonType",
                                       "--scope", "elementUI/buttonUI"]).stdout)
        assert ["check", "多选"] in prop["items"][0]["choices"]
        assert not session.exists() and not Path(str(session) + ".lock").exists()
        assert all(hashlib.sha256(p.read_bytes()).hexdigest() == digest for p, digest in before.items())

    def test_installed_native_snippet_can_feed_editor_workflow(self, tmp_path):
        args = ["--json", "--ide", r"I:\xcide"]
        found = json.loads(_run(args + ["reference", "search", "snippets", "如果"]).stdout)
        snippet = next(item for item in found["items"] if item["name"] == "如果")
        shown = json.loads(_run(args + ["reference", "show", "snippets", snippet["id"]]).stdout)
        created = json.loads(_run(args + ["project", "new", str(tmp_path), "Snippet Workflow"]).stdout)
        source = tmp_path / "snippet-input.txt"
        source.write_text(shown["item"]["code"], encoding="utf-8")
        target = Path(created["directory"]) / "snippet.xc"
        selected = ["--json", "--project", created["project_file"]]
        write = json.loads(_run(selected + ["editor", "write", str(target), str(source)]).stdout)
        assert write["verified"]
        read = json.loads(_run(selected + ["editor", "read", str(target)]).stdout)
        assert read["content"].replace("\r\n", "\n") == shown["item"]["code"].replace("\r\n", "\n")
        assert target.read_bytes().startswith(b"\xef\xbb\xbf")

    def test_installed_reference_errors_and_partial_catalog_discovery(self, tmp_path):
        root = tmp_path / "incomplete IDE"
        (root / "data/config").mkdir(parents=True)
        (root / "炫彩IDE.exe").write_bytes(b"fixture")
        (root / "data/config/help.json").write_text('{"keyword": {}}', encoding="utf-8")
        args = ["--json", "--dry-run", "--ide", str(root)]
        failed = _run(args + ["reference", "search", "language"], check=False)
        assert failed.returncode == 1 and not failed.stdout
        error = json.loads(failed.stderr)
        assert error["ok"] is False and error["error_type"] == "ReferenceError"
        assert "Traceback" not in failed.stderr
        inventory = json.loads(_run(args + ["reference", "sources"]).stdout)
        assert inventory["ok"] and inventory["available_count"] == 0
        assert all(s["available"] is False and s["error"] for s in inventory["sources"])

    def test_real_editor_themes_can_be_inspected_without_mcp(self):
        installed_root = Path(r"I:\xcide")
        assert (installed_root / "data" / "theme").is_dir()
        themes = json.loads(_run(["--json", "--ide", str(installed_root), "theme", "list", "黑色"]).stdout)
        assert themes["ok"] is True and themes["count"] >= 1
        item = themes["themes"][0]
        assert item["editor_font"] and item["tab_size"] == "4"
        details = json.loads(_run(["--json", "--ide", str(installed_root), "theme", "info", item["id"]]).stdout)
        assert details["name"] == item["name"]
        assert details["config_file"].endswith("xctheme.config")
        assert details["skin_file"] and Path(details["skin_file"]).is_file()

    def test_create_inspect_and_reject_collision(self, tmp_path):
        out = tmp_path / "native project workflow"
        session_file = tmp_path / "create-session.json"
        command = ["--json", "--session-file", str(session_file), "project", "new", str(out), "Agent Project"]
        created = json.loads(_run(command).stdout)
        assert created["project_file"].endswith("Agent Project.xcproj")
        assert created["platform"] == "x64"
        assert created["modules"] == [{"path": "module_base.h", "name": "基础模块"}]
        assert created["files"] == [{"file": "main.xc", "state": "1,"}]
        source = Path(created["directory"]) / "main.xc"
        assert source.is_file()
        inspected = json.loads(_run(["--json", "project", "info", created["project_file"]]).stdout)
        assert inspected["name"] == "Agent Project"
        assert inspected["entrypoints"] == ["main.xc"]
        conflict = _run(command, check=False)
        assert conflict.returncode != 0
        error = json.loads(conflict.stderr)
        assert error["ok"] is False and "already exists" in error["error"]
        print(f"\n  Native project: {created['project_file']}")

    def test_project_configuration_commands_switch_without_mcp(self, tmp_path):
        installed_root = Path(r"I:\xcide")
        ide_root = tmp_path / "configuration IDE"
        (ide_root / "data" / "config").mkdir(parents=True)
        (ide_root / "data" / "XC-Module").mkdir(parents=True)
        (ide_root / "炫彩IDE.exe").write_bytes(b"fixture IDE marker")
        target_template = (ide_root / "data" / "template" / "项目模板" / "炫语言" / "空白窗口程序"
                           / "空白窗口程序" / "project")
        shutil.copytree(_template_root(installed_root), target_template)
        output = tmp_path / "configuration projects"
        created = json.loads(_run(["--json", "--ide", str(ide_root), "project", "new",
                                   str(output), "Config Switch"]).stdout)
        project_file = Path(created["project_file"])

        inventory = json.loads(_run(["--json", "--project", str(project_file), "project", "config", "list"]).stdout)
        assert inventory["active_configuration"] == "发布版"
        assert inventory["active_platform"] == "x64"
        assert len(inventory["configurations"]) == 2
        before = project_file.read_bytes()
        dry_run = json.loads(_run(["--json", "--dry-run", "--project", str(project_file), "project", "config",
                                   "set", "--configuration", "调试版", "--platform", "x86"]).stdout)
        assert dry_run["dry_run"] is True
        assert project_file.read_bytes() == before

        switched = json.loads(_run(["--json", "--project", str(project_file), "project", "config", "set",
                                    "--configuration", "调试版", "--platform", "x86"]).stdout)
        assert switched["before"] == {"configuration": "发布版", "platform": "x64"}
        assert switched["after"] == {"configuration": "调试版", "platform": "x86"}
        checked = json.loads(_run(["--json", "project", "info", str(project_file)]).stdout)
        assert (checked["configuration"], checked["platform"]) == ("调试版", "x86")

        quoted = 'Debug "QA" and \'team\''
        tree = ET.parse(project_file)
        tree.getroot().find("./vc/setting/config").set("name", quoted)
        tree.write(project_file, encoding="utf-8", xml_declaration=True)
        result = json.loads(_run(["--json", "--project", str(project_file), "project", "config", "set",
                                 "--configuration", quoted, "--platform", "x64"]).stdout)
        assert result["configuration"] == quoted
        checked = json.loads(_run(["--json", "project", "info", str(project_file)]).stdout)
        assert (checked["configuration"], checked["platform"]) == (quoted, "x64")

        invalid = _run(["--json", "--project", str(project_file), "project", "config", "set",
                        "--configuration", "不存在"], check=False)
        assert invalid.returncode == 1
        assert json.loads(invalid.stderr)["ok"] is False
        print(f"\n  Native configuration switch: {project_file}")

    def test_project_sources_and_breakpoints_commands_without_mcp(self, tmp_path):
        installed_root = Path(r"I:\xcide")
        ide_root = tmp_path / "source metadata IDE"
        (ide_root / "data" / "config").mkdir(parents=True)
        (ide_root / "data" / "XC-Module").mkdir(parents=True)
        (ide_root / "炫彩IDE.exe").write_bytes(b"fixture IDE marker")
        target_template = (ide_root / "data" / "template" / "项目模板" / "炫语言" / "空白窗口程序"
                           / "空白窗口程序" / "project")
        shutil.copytree(_template_root(installed_root), target_template)
        output = tmp_path / "source metadata projects"
        created = json.loads(_run(["--json", "--ide", str(ide_root), "project", "new",
                                   str(output), "Source Metadata"]).stdout)
        project_file = Path(created["project_file"])
        (project_file.parent / "extra.xc").write_text("line one\nline two\nline three\n", encoding="utf-8")

        listing = json.loads(_run(["--json", "--project", str(project_file), "project", "sources", "list"]).stdout)
        extra = next(item for item in listing["sources"] if item["file"] == "extra.xc")
        assert extra["registered"] is False
        added = json.loads(_run(["--json", "--project", str(project_file), "project", "sources",
                                 "add", "extra.xc"]).stdout)
        assert added["added"] is True
        dry_run_before = project_file.read_bytes()
        dry_run = json.loads(_run(["--json", "--dry-run", "--project", str(project_file), "project",
                                   "breakpoints", "add", "extra.xc", "2"]).stdout)
        assert dry_run["dry_run"] is True
        assert project_file.read_bytes() == dry_run_before
        breakpoint = json.loads(_run(["--json", "--project", str(project_file), "project", "breakpoints",
                                      "add", "extra.xc", "2"]).stdout)
        assert breakpoint["added"] is True
        listed = json.loads(_run(["--json", "--project", str(project_file), "project", "breakpoints", "list"]).stdout)
        assert listed["breakpoint_count"] == 1
        assert listed["files"][0]["breakpoints"] == [{"line": 2, "valid": True}]
        invalid = _run(["--json", "--project", str(project_file), "project", "breakpoints", "add",
                        "extra.xc", "30"], check=False)
        assert invalid.returncode == 1 and json.loads(invalid.stderr)["ok"] is False
        removed_breakpoint = json.loads(_run(["--json", "--project", str(project_file), "project",
                                              "breakpoints", "remove", "extra.xc", "2"]).stdout)
        assert removed_breakpoint["removed"] is True
        removed_source = json.loads(_run(["--json", "--project", str(project_file), "project",
                                          "sources", "remove", "extra.xc"]).stdout)
        assert removed_source["removed"] is True and removed_source["source_deleted"] is False
        assert (project_file.parent / "extra.xc").is_file()

        watch = json.loads(_run(["--json", "--project", str(project_file), "project", "debug", "watch-add",
                                 "counter_value"]).stdout)
        assert watch["added"] is True
        bookmark = json.loads(_run(["--json", "--project", str(project_file), "project", "debug",
                                    "bookmark-add", "extra.xc", "2"]).stdout)
        assert bookmark["added"] is True
        debug = json.loads(_run(["--json", "--project", str(project_file), "project", "debug", "list"]).stdout)
        assert debug["watches"] == [{"name": "counter_value"}]
        assert debug["bookmarks"] == [{"file": "extra.xc", "lineno": "2"}]
        assert debug["breakpoints"]["breakpoint_count"] == 0

    def test_installed_ui_template_can_be_found_inspected_and_copied(self, tmp_path):
        installed_root = Path(r"I:\xcide")
        ide_root = tmp_path / "UI template IDE"
        source_skin = installed_root / "data" / "template" / "皮肤" / "template-关闭按钮"
        target_skin = ide_root / "data" / "template" / "皮肤" / "template-关闭按钮"
        (ide_root / "data").mkdir(parents=True)
        (ide_root / "炫彩IDE.exe").write_bytes(b"fixture IDE marker")
        shutil.copytree(source_skin, target_skin)
        (target_skin / "project" / "Debug").mkdir()
        (target_skin / "project" / "Debug" / "ignored.exe").write_bytes(b"generated")

        listed = json.loads(_run(["--json", "--ide", str(ide_root), "ui-template", "list", "关闭"]).stdout)
        assert listed["count"] == 1
        item = listed["templates"][0]
        assert item["category"] == "皮肤"
        details = json.loads(_run(["--json", "--ide", str(ide_root), "ui-template", "info", item["id"]]).stdout)
        assert details["file_count"] >= 4
        assert all(not entry["file"].startswith("Debug/") for entry in details["files"])
        target = tmp_path / "copied UI assets"
        copied = json.loads(_run(["--json", "--ide", str(ide_root), "ui-template", "copy",
                                  str(target), "close button assets", "--id", item["id"]]).stdout)
        destination = Path(copied["destination"])
        assert copied["category"] == "皮肤"
        assert copied["file_count"] == details["file_count"]
        assert (destination / "layout.xml").is_file()
        assert not (destination / "Debug").exists()
        dry_root = tmp_path / "dry UI assets"
        dry = json.loads(_run(["--json", "--dry-run", "--ide", str(ide_root), "ui-template", "copy",
                               str(dry_root), "Not Copied", "--id", item["id"]]).stdout)
        assert dry["dry_run"] is True and not dry_root.exists()

    def test_native_template_ui_and_project_doctor_commands_need_no_plugin(self, tmp_path):
        installed_root = Path(r"I:\xcide")
        ide_root = tmp_path / "feature IDE"
        (ide_root / "data" / "config").mkdir(parents=True)
        (ide_root / "data" / "XC-Module").mkdir(parents=True)
        (ide_root / "炫彩IDE.exe").write_bytes(b"fixture IDE marker")
        base_module = ide_root / "data" / "XC-Module" / "module_base.h"
        base_module.write_text("//@模块名称 基础模块\n", encoding="utf-8")
        source_template = _template_root(installed_root)
        target_template = ide_root / "data" / "template" / "项目模板" / "炫语言" / "空白窗口程序" / "空白窗口程序" / "project"
        shutil.copytree(source_template, target_template)
        (target_template / "main.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<head />\n'
            '<windowUI><buttonUI name="ok" font="@test_font" /></windowUI>', encoding="utf-8")
        (target_template / "资源文件").mkdir()
        (target_template / "资源文件" / "resource.res").write_text(
            '<resources><type_font><font name="test_font" size="10" /></type_font></resources>',
            encoding="utf-8")
        import zipfile
        with zipfile.ZipFile(target_template / "UI_ZIP.zip", "w") as archive:
            archive.writestr("布局文件/main.xml", '<head /><windowUI><buttonUI name="archived" /></windowUI>')
            archive.writestr("资源文件/resource.res", '<resources />')

        templates = json.loads(_run(["--json", "--ide", str(ide_root), "project", "template", "list"]).stdout)
        assert templates["count"] == 1
        template_id = templates["templates"][0]["id"]
        output = tmp_path / "template project output"
        created = json.loads(_run(["--json", "--ide", str(ide_root), "project", "new",
                                   str(output), "Template Copy", "--template", template_id]).stdout)
        project_file = Path(created["project_file"])
        assert created["native_template"] == template_id
        assert created["configuration"] == "调试版"
        assert created["platform"] == "x64"
        assert (project_file.parent / "common.xh").is_file()
        assert (project_file.parent / "UI_ZIP.zip").is_file()

        interface = json.loads(_run(["--json", "--ide", str(ide_root), "--project", str(project_file),
                                     "interface", "list"]).stdout)
        assert interface["layoutCount"] == 1
        assert interface["uiZipCount"] == 1
        assert interface["uiArchives"][0]["layoutMembers"] == ["布局文件/main.xml"]
        checked = json.loads(_run(["--json", "--ide", str(ide_root), "--project", str(project_file),
                                   "interface", "check"]).stdout)
        assert checked["ok"] is True
        assert checked["warningCount"] == 0
        (project_file.parent / "main.xml").write_text("<head /><windowUI><buttonUI></windowUI>", encoding="utf-8")
        broken_layout = _run(["--json", "--ide", str(ide_root), "--project", str(project_file),
                              "interface", "check"], check=False)
        assert broken_layout.returncode == 1
        broken_result = json.loads(broken_layout.stdout)
        assert broken_result["ok"] is False and broken_result["errorCount"] == 1
        health_result = _run(["--json", "--ide", str(ide_root), "--project", str(project_file),
                              "project", "doctor"], check=False)
        assert health_result.returncode == 1
        health = json.loads(health_result.stdout)
        assert health["ok"] is False
        assert health["checks"]["validLayoutCount"] == 0
        assert any(item["code"] == "layout-parse" for item in health["diagnostics"])
        print(f"\n  Template project: {created['project_file']}")

    def test_local_example_library_can_inspect_and_derive_a_native_project(self, tmp_path):
        installed_root = Path(r"I:\xcide")
        ide_root = tmp_path / "example IDE"
        (ide_root / "data" / "config").mkdir(parents=True)
        (ide_root / "data" / "XC-Module").mkdir(parents=True)
        (ide_root / "炫彩IDE.exe").write_bytes(b"fixture IDE marker")
        example_source = ide_root / "data" / "示例" / "炫彩界面库-示例" / "炫-按钮"
        example_source.mkdir(parents=True)
        source_template = _template_root(installed_root)
        source_project = example_source / "炫-按钮.xcproj"
        shutil.copy2(source_template / "template.xcproj", source_project)
        shutil.copy2(source_template / "main.xc", example_source / "main.xc")
        (example_source / "main.xml").write_text(
            '<head /><windowUI><buttonUI name="ok" /></windowUI>', encoding="utf-8")
        (example_source / "resource.res").write_text("<resources />", encoding="utf-8")
        (example_source / "Debug").mkdir()
        (example_source / "Debug" / "old.exe").write_bytes(b"old generated executable")
        original_hash = hashlib.sha256(source_project.read_bytes()).hexdigest()

        listed = json.loads(_run(["--json", "--ide", str(ide_root), "example", "list", "按钮"]).stdout)
        assert listed["count"] == 1
        example_id = listed["examples"][0]["id"]
        details = json.loads(_run(["--json", "--ide", str(ide_root), "example", "info", example_id]).stdout)
        assert details["name"] == source_project.stem
        assert details["file_count"] == 4
        assert "Debug/old.exe" not in {item["path"] for item in details["files"]}

        output = tmp_path / "derived examples"
        derived = json.loads(_run(["--json", "--ide", str(ide_root), "example", "copy",
                                   str(output), "按钮派生项目", "--id", example_id]).stdout)
        project_file = Path(derived["project_file"])
        assert derived["name"] == "按钮派生项目"
        assert derived["native_example"] == example_id
        assert derived["modules"] == [{"path": "module_base.h", "name": "基础模块"}]
        assert derived["configuration"] == "调试版"
        assert (project_file.parent / "main.xc").is_file()
        assert (project_file.parent / "main.xml").is_file()
        assert not (project_file.parent / "Debug").exists()
        assert hashlib.sha256(source_project.read_bytes()).hexdigest() == original_hash

        dry_output = tmp_path / "dry example copy"
        dry_run = json.loads(_run(["--json", "--dry-run", "--ide", str(ide_root), "example", "copy",
                                   str(dry_output), "Not Created", "--id", example_id]).stdout)
        assert dry_run["dry_run"] is True and not dry_output.exists()
        missing = _run(["--json", "--ide", str(ide_root), "example", "info", "missing.xcproj"], check=False)
        assert missing.returncode == 1
        assert json.loads(missing.stderr)["ok"] is False
        print(f"\n  Derived native example project: {project_file}")

    def test_project_listing_and_read_only_latest(self, tmp_path):
        out = tmp_path / "discovery"
        session_file = tmp_path / "listing-session.json"
        created = json.loads(_run(["--json", "--session-file", str(session_file), "project", "new", str(out), "Search Project"]).stdout)
        rows = json.loads(_run(["--json", "project", "list", str(out), "--recursive"]).stdout)
        assert rows["count"] == 1
        assert rows["projects"][0]["name"] == "Search Project"
        latest = _run(["--json", "--session-file", str(session_file), "--project", created["project_file"],
                       "preview", "latest", "--recipe", "project"], check=False)
        assert latest.returncode != 0
        assert json.loads(latest.stderr)["ok"] is False

    def test_local_editor_and_module_commands_need_no_plugin(self, tmp_path):
        installed_root = Path(r"I:\xcide")
        ide_root = tmp_path / "minimal IDE"
        assert (installed_root / "炫彩IDE.exe").is_file()
        (ide_root / "data" / "config").mkdir(parents=True)
        (ide_root / "data" / "XC-Module").mkdir(parents=True)
        (ide_root / "炫彩IDE.exe").write_bytes(b"fixture IDE marker")
        ide_note = ide_root / "data" / "config" / "local-readme.txt"
        ide_note.write_text("IDE installation note\n", encoding="utf-8")
        source_template = _template_root(installed_root)
        target_template = ide_root / "data" / "template" / "项目模板" / "炫语言" / "空白窗口程序" / "空白窗口程序" / "project"
        shutil.copytree(source_template, target_template)
        out = tmp_path / "local backend"
        session_file = tmp_path / "local-session.json"
        created = json.loads(_run(["--json", "--ide", str(ide_root), "--session-file", str(session_file),
                                   "project", "new", str(out), "No MCP Project"]).stdout)
        project_file = Path(created["project_file"])
        source = project_file.parent / "main.xc"
        install_content = json.loads(_run(["--json", "--ide", str(ide_root),
                                           "editor", "read", str(ide_note)]).stdout)
        assert install_content["ok"] is True
        assert install_content["content"] == ide_note.read_bytes().decode("utf-8")
        content = json.loads(_run(["--json", "--ide", str(ide_root), "--project", str(project_file),
                                   "editor", "read", str(source)]).stdout)
        assert content["ok"] is True
        # read_text() converts CRLF to LF; the CLI intentionally preserves the
        # bytes' original newline style, so decode the file without newline IO.
        assert content["content"] == source.read_bytes().decode("utf-8-sig")

        output_dir = tmp_path / "input files"
        output_dir.mkdir()
        replacement = output_dir / "main-new.txt"
        replacement.write_text("// 本地更新\n", encoding="utf-8")
        written = json.loads(_run(["--json", "--ide", str(ide_root), "--project", str(project_file),
                                   "editor", "write", str(source), str(replacement)]).stdout)
        assert written["verified"] is True
        assert source.read_bytes().startswith(b"\xef\xbb\xbf")
        assert "本地更新" in source.read_bytes().decode("utf-8-sig")

        module_header = ide_root / "data" / "XC-Module" / "__cli_anything_test_module" / "module_no_mcp_probe.h"
        module_header.parent.mkdir(parents=True)
        module_header.write_text("//@模块名称 无 MCP 验收模块\n//@依赖 module_base.h\n", encoding="utf-8")
        (module_header.parent / "module_base.h").write_text("//@模块名称 临时依赖基础\n", encoding="utf-8")
        found = json.loads(_run(["--json", "--ide", str(ide_root), "module", "search", "无 MCP 验收模块"]).stdout)
        assert found["count"] >= 1
        dependency_plan = json.loads(_run(["--json", "--ide", str(ide_root), "module", "dependencies",
                                           module_header.name]).stdout)
        assert dependency_plan["order"] == ["module_base.h", module_header.name]
        added = json.loads(_run(["--json", "--ide", str(ide_root), "--project", str(project_file),
                                 "module", "add", "--file", module_header.name,
                                 "--with-dependencies"]).stdout)
        assert added["added"] is True and added["restartRequired"] is True
        assert added["dependencyOrder"] == ["module_base.h", module_header.name]
        assert {item["file"] for item in json.loads(_run(["--json", "--project", str(project_file),
                                                          "module", "list", "--project-only"]).stdout)["modules"]} >= {
            "module_base.h", module_header.name}
        removed = json.loads(_run(["--json", "--ide", str(ide_root), "--project", str(project_file),
                                   "module", "remove", "--file", module_header.name]).stdout)
        assert removed["removed"] is True
        removed_base = json.loads(_run(["--json", "--ide", str(ide_root), "--project", str(project_file),
                                        "module", "remove", "--file", "module_base.h"]).stdout)
        assert removed_base["removed"] is True
        assert (project_file.parent / "main.xc").is_file()

    def test_dry_run_has_no_side_effects_or_ide_calls(self, tmp_path):
        out = tmp_path / "dry-run-output"
        session = tmp_path / "session.json"
        session.write_text('{"schema_version": 1, "revision": 0, "project": null, "history": [], "undo": [], "redo": []}', encoding="utf-8")
        before = session.read_bytes()
        result = _run(["--json", "--dry-run", "--session-file", str(session), "project", "new", str(out), "No Write"])
        assert json.loads(result.stdout)["dry_run"] is True
        assert not out.exists()
        assert session.read_bytes() == before

    def test_selected_session_round_trip_and_undo_redo(self, tmp_path):
        out = tmp_path / "session-workflow"
        session_file = tmp_path / "selected-session.json"
        first = json.loads(_run(["--json", "--session-file", str(session_file), "project", "new", str(out), "First Project"]).stdout)
        second = json.loads(_run(["--json", "--session-file", str(session_file), "project", "new", str(out), "Second Project"]).stdout)
        assert Session(session_file).project == second["project_file"]
        undone = json.loads(_run(["--json", "--session-file", str(session_file), "session", "undo"]).stdout)
        assert undone["project"] == first["project_file"]
        redone = json.loads(_run(["--json", "--session-file", str(session_file), "session", "redo"]).stdout)
        assert redone["project"] == second["project_file"]


class TestRealIDEAcceptance:
    """One x64 F7 acceptance test in a temporary, plugin-free IDE copy."""

    @pytest.mark.parametrize("custom_output", [False, True])
    def test_blank_window_template_compiles_to_fresh_amd64(self, tmp_path, custom_output):
        ide_root = Path(r"I:\xcide")
        template = _template_root(ide_root)
        assert (ide_root / "炫彩IDE.exe").is_file()
        assert (template / "template.xcproj").is_file()
        acceptance_root = tmp_path / "real IDE acceptance"
        project_data = create_project(acceptance_root, "XCIDE Build Acceptance", ide_root,
                                      configuration="发布版", platform="x64")
        project_file = Path(project_data["project_file"])
        expected = project_file.parent / "Release64" / "XCIDE Build Acceptance.exe"
        if custom_output:
            tree = ET.parse(project_file)
            output = tree.getroot().find('./vc/setting/config[@name="发布版"]/x64/out')
            assert output is not None
            output.set("name", "Custom artifact")
            output.set("out_path", str(tmp_path / "external binaries"))
            tree.write(project_file, encoding="utf-8", xml_declaration=True)
            expected = tmp_path / "external binaries" / "Custom artifact.exe"
        assert project_data["files"] == [{"file": "main.xc", "state": "1,"}]
        assert project_data["modules"] == [{"path": "module_base.h", "name": "基础模块"}]
        expected_sources = [project_file.parent / name for name in ("main.xc", "common.xh", "exe.rc", "exe.ico")]
        assert all(path.is_file() for path in expected_sources), expected_sources
        main_source_hash = hashlib.sha256((project_file.parent / "main.xc").read_bytes()).hexdigest()
        session_file = tmp_path / "native-build-session.json"
        completed = _run(["--json", "--ide", str(ide_root), "--project", str(project_file),
                          "--session-file", str(session_file), "build", "--timeout", "240"], check=False)
        assert completed.returncode == 0, (
            f"Real CLI build returned {completed.returncode}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}")
        result = json.loads(completed.stdout)
        assert result["ok"] is True, json.dumps(result, ensure_ascii=False, indent=2)
        assert result["build_result"] == "artifact_updated"
        assert result["compiler"]["compiled"] is None
        assert result["compiler"]["errorCount"] is None
        assert result["compiler"]["diagnostics_available"] is False
        assert "无法确认" in result["compiler"]["note"]
        assert result["exe"]["architecture"] == "AMD64"
        assert Path(result["exe"]["path"]) == expected
        assert Path(result["expected_executable"]) == expected
        assert result["exe"]["machine"] == "0x8664"
        assert result["exe"]["bytes"] > 256
        assert len(result["exe"]["sha256"]) == 64
        assert result["exe"]["modified_at"]
        isolated_root = Path(result["command"][0]).parent
        assert result["isolated_plugins"] == []
        assert not isolated_root.exists()  # The temporary IDE copy is cleaned after the build.
        # The IDE can normalize native .xcproj metadata while opening/closing it.
        # The disposable acceptance checks its resulting x64 selection and keeps
        # the actual source input immutable across the native compiler run.
        compiled_project = json.loads(_run(["--json", "project", "info", str(project_file)]).stdout)
        assert compiled_project["platform"] == "x64"
        assert hashlib.sha256((project_file.parent / "main.xc").read_bytes()).hexdigest() == main_source_hash
        print(f"\n  Native IDE artifact result: {result['build_result']} (错误面板诊断不可从本地接口读取)")
        print(f"  Fresh AMD64 PE: {result['exe']['path']} ({result['exe']['bytes']:,} bytes, sha256={result['exe']['sha256']})")
@pytest.fixture(scope="module", params=["x64", "x86"])
def debug_program(request, tmp_path_factory):
    from cli_anything.xcide.utils.native_build import compile_native
    root = tmp_path_factory.mktemp("native-runtime-" + request.param)
    source = root / "runtime.cpp"
    source.write_text(r'''
#include <windows.h>
#include <stdio.h>
int main(int argc,char**argv){
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);
    if(argc>1 && argv[1][0]=='s'){Sleep(20000);return 0;}
    if(argc>1 && argv[1][0]=='c'){*(volatile int*)0=4;return 0;}
    if(argc>1 && argv[1][0]=='h'){
        __try{RaiseException(0xE0424242,0,0,nullptr);}
        __except(EXCEPTION_EXECUTE_HANDLER){OutputDebugStringW(L"handled\n");}
        return 0;
    }
    if(argc>1 && argv[1][0]=='q')return 0;
    if(argc>1 && (argv[1][0]=='o' || argv[1][0]=='e')){
        FILE* channel=argv[1][0]=='o'?stdout:stderr;
        static char block[32768];memset(block,'a',sizeof(block));
        for(int i=0;i<513;++i)if(fwrite(block,1,sizeof(block),channel)!=sizeof(block))return 9;
        fflush(channel);return 0;
    }
    OutputDebugStringW(L"中文输出\n");OutputDebugStringA("ansi message\n");
    puts("stdout-channel");fputs("stderr-channel",stderr);return 7;
}
''', encoding="utf-8-sig")
    executable = root / "runtime.exe"
    compile_native(source, executable, architecture=request.param)
    return executable


class TestRuntimeAutomation:
    @pytest.mark.parametrize("channel,mode", [("stdout", "out"), ("stderr", "err")])
    def test_runtime_output_overflow_fails_in_installed_command(self, debug_program, tmp_path, channel, mode):
        completed = _run(["--json", "runtime", "run", "--exe", str(debug_program), "--arg", mode,
                          "--output", str(tmp_path / "runs")], check=False)
        result = json.loads(completed.stdout)
        assert completed.returncode == 1 and not result["ok"]
        assert "16 MiB" in result["error"] and result["cleanup_error"] is None
        assert Path(result[channel]).stat().st_size > 16 * 1024 * 1024
        assert not result["automation"]["foreground_input"]
        assert json.loads(Path(result["report"]).read_text("utf-8")) == result

    def test_debug_unicode_ansi_channels_and_expected_exit(self, debug_program, tmp_path):
        completed = _run(["--json", "runtime", "run", "--exe", str(debug_program),
                          "--output", str(tmp_path / "reports"), "--expected-exit-code", "7"])
        result = json.loads(completed.stdout)
        assert result["ok"] and result["exit_code"] == 7 and not result["terminated"]
        assert result["debug_output"] == "中文输出\nansi message\n"
        assert Path(result["stdout"]).read_bytes().strip() == b"stdout-channel"
        assert Path(result["stderr"]).read_bytes() == b"stderr-channel"
        assert json.loads(Path(result["report"]).read_text("utf-8")) == result

    @pytest.mark.parametrize("mode", ["handled", "crash", "sleep", "quiet"])
    def test_debug_exception_and_timeout_semantics(self, debug_program, tmp_path, mode):
        completed = _run(["--json", "runtime", "run", "--exe", str(debug_program), "--arg", mode,
                          "--output", str(tmp_path / "reports"), "--timeout", "0.8" if mode == "sleep" else "10"], check=False)
        result = json.loads(completed.stdout)
        assert result["cleanup_error"] is None
        if mode == "handled":
            assert completed.returncode == 0 and result["ok"]
            assert result["debug_output"] == "handled\n"
            assert any(e["code"] == "0xe0424242" and e["first_chance"] for e in result["exceptions"])
        elif mode == "crash":
            assert completed.returncode == 1 and result["exit_code"] == 0xC0000005
            assert any(not e["first_chance"] and e["code"] == "0xc0000005" for e in result["exceptions"])
        elif mode == "quiet":
            assert completed.returncode == 0 and result["debug_output"] == ""
        else:
            assert completed.returncode == 1 and result["timed_out"] and result["terminated"]
            from cli_anything.xcide.core.build import _windows_api
            _, api = _windows_api()
            handle = api.OpenProcess(0x00100000, False, result["pid"])
            if handle:
                try:
                    assert api.WaitForSingleObject(handle, 0) == 0
                finally:
                    api.CloseHandle(handle)

    def test_runtime_dry_run_and_invalid_scenario_do_not_launch(self, tmp_path):
        examples = Path(__file__).resolve().parents[1] / "examples"
        target, session = tmp_path / "reports", tmp_path / "session.json"
        prefix = ["--json", "--dry-run", "--session-file", str(session)]
        for args in (["runtime", "run"], ["runtime", "test", str(examples / "automation_counter.json")]):
            result = json.loads(_run(prefix + args + ["--exe", str(tmp_path / "missing.exe"), "--output", str(target)]).stdout)
            assert result["dry_run"]
        assert not target.exists() and not session.exists()
        bad = tmp_path / "bad.json"
        bad.write_text('{"version":1,"steps":[{"action":"click","x":1,"y":1}]}', encoding="utf-8")
        completed = _run(prefix + ["runtime", "test", str(bad), "--exe", "missing.exe", "--output", str(target)], check=False)
        assert completed.returncode == 1 and json.loads(completed.stderr)["ok"] is False
        assert not target.exists() and not session.exists()

    @pytest.mark.parametrize("architecture", ["x64", "x86"])
    def test_background_adapter_modes_and_input_state(self, tmp_path, architecture):
        from cli_anything.xcide.utils.native_build import compile_native
        package = Path(__file__).resolve().parents[1]
        sdk = Path(r"I:\xcide\xc-plugin\炫彩IDE-插件开发\plug_test\xcgui.h")
        library = Path(r"I:\xcide\data\XC-Module\核心[官方]\炫彩界面库") / architecture
        source, executable = tmp_path / "counter.cpp", tmp_path / "counter.exe"
        source.write_text('''#include <windows.h>
#include "''' + sdk.as_posix() + '''"
#include "''' + (package / "native/automation_bridge.h").as_posix() + '''"
#pragma comment(lib,"''' + (library / "XCGUI.lib").as_posix() + '''")
static HELE edit;static HWND exitWindow;static bool exitOnClick;
int CALLBACK clicked(BOOL*){wchar_t text[256];XEdit_GetText(edit,text,256);OutputDebugStringW(L"CLICK:");OutputDebugStringW(text);
 if(exitOnClick)PostMessageW(exitWindow,WM_CLOSE,0,0);return 0;}
int main(int argc,char**argv){
 bool d2d=argc>1 && argv[1][0]=='d', noadapter=argc>1 && argv[1][0]=='n';
 XInitXCGUI(d2d);auto window=XWnd_Create(100,100,480,320,L"Background Fixture",0,window_style_default);
 exitWindow=XWnd_GetHWND(window);exitOnClick=argc>1 && argv[1][0]=='e';
 edit=XEdit_Create(30,50,300,36,window);auto button=XBtn_Create(30,115,180,50,L"Count",window);
 XEle_RegEventC(button,XE_BNCLICK,(void*)clicked);XWnd_AdjustLayout(window);XWnd_ShowWindow(window,SW_SHOW);
 if(!noadapter)xc_cli_test::install(window);OutputDebugStringW(L"READY");XRunXCGUI();XExitXCGUI();return 0;
}
''', encoding="utf-8-sig")
        compile_native(source, executable, architecture=architecture)
        shutil.copyfile(library / "XCGUI.dll", tmp_path / "XCGUI.dll")
        steps = [{"action": "wait_window", "title_contains": "Background Fixture"},
                 {"action": "assert_debug", "contains": "READY"}, {"action": "screenshot", "name": "initial"},
                 {"action": "click", "x": 150, "y": 68}, {"action": "text", "text": "中文Automation!"},
                 {"action": "key", "key": "BACKSPACE"}, {"action": "click", "x": 110, "y": 140},
                 {"action": "assert_debug", "contains": "CLICK:中文Automation"},
                 {"action": "screenshot", "name": "changed"}, {"action": "close"}]
        scenario = tmp_path / "scenario.json"
        scenario.write_text(json.dumps({"version": 1, "steps": steps}), encoding="utf-8")
        for mode in ("gdi", "d2d", "noadapter", "exit"):
            if mode == "exit":
                exit_steps = [steps[0], steps[1], {"action": "click", "x": 110, "y": 140},
                              {"action": "assert_debug", "contains": "CLICK:"}, {"action": "wait_exit"}]
                scenario.write_text(json.dumps({"version": 1, "steps": exit_steps}), encoding="utf-8")
            completed = _run(["--json", "runtime", "test", str(scenario), "--exe", str(executable),
                              "--arg", mode, "--output", str(tmp_path / "runs")], check=False)
            result = json.loads(completed.stdout)
            assert result["automation"]["foreground_input"] is False
            assert result["cleanup_error"] is None
            assert result["exit_code"] == (0 if mode in {"gdi", "exit"} else 0xE0000001)
            from cli_anything.xcide.core.build import _windows_api
            _, api = _windows_api()
            handle = api.OpenProcess(0x00100000, False, result["pid"])
            if handle:
                try:
                    assert api.WaitForSingleObject(handle, 0) == 0
                finally:
                    api.CloseHandle(handle)
            if mode == "gdi":
                assert completed.returncode == 0, result
                assert "CLICK:中文Automation!" not in result["debug_output"]
                from PIL import Image, ImageChops
                shots = [Image.open(s["screenshot"]["path"]).convert("RGB") for s in result["steps"] if "screenshot" in s]
                assert ImageChops.difference(shots[0].crop((30, 50, 330, 86)), shots[1].crop((30, 50, 330, 86))).getbbox()
            elif mode == "exit":
                assert completed.returncode == 0 and result["ok"] and not result["terminated"], result
                assert all(step["ok"] for step in result["steps"])
            else:
                assert completed.returncode == 1 and result["terminated"]
                assert "适配器" in result["error"]
                assert result["steps"][-1]["action"] == ("screenshot" if mode == "d2d" else "wait_window")

    def test_native_xc_diagnostics_and_background_workflow(self, tmp_path):
        from cli_anything.xcide.core import modules
        ide = Path(r"I:\xcide")
        config = ide / "data/config/config.config"
        baseline = hashlib.sha256(config.read_bytes()).hexdigest()
        project = Path(create_project(tmp_path, "Automation Counter", ide,
                                      configuration="调试版", platform="x64")["project_file"])
        examples = Path(__file__).resolve().parents[1] / "examples"
        modules.add_modules(project, ["module_xcgui_class.h"], ide_root=ide, with_dependencies=True)
        shutil.copyfile(examples / "automation_counter.xc", project.parent / "main.xc")
        shutil.copyfile(examples.parent / "native/automation_bridge.h", project.parent / "automation_bridge.h")
        args = ["--json", "--ide", str(ide), "--project", str(project), "build", "--diagnostics", "--timeout", "60"]
        build_process = _run(args, check=False)
        (tmp_path / "build-success.json").write_text(build_process.stdout, encoding="utf-8")
        assert build_process.returncode == 0, build_process.stdout + build_process.stderr
        built = json.loads(build_process.stdout)
        assert built["ok"] and built["build_result"] == "compiled"
        assert built["automation"]["foreground_input"] is False
        assert built["automation"]["observations"]["before"]["foreground_hwnd"] == built["automation"]["observations"]["after"]["foreground_hwnd"]
        assert built["compiler"]["compiled"] and built["compiler"]["errorCount"] == 0
        assert built["isolated_plugins"] == ["plug_cli_output.dll"]
        assert not Path(built["isolated_ide_root"]).exists()
        test_process = _run(["--json", "runtime", "test", str(examples / "automation_counter.json"),
                             "--exe", built["exe"]["path"], "--output", str(tmp_path / "runs")], check=False)
        assert test_process.returncode == 0, test_process.stdout + test_process.stderr
        tested = json.loads(test_process.stdout)
        assert tested["ok"] and tested["exit_code"] == 0 and not tested["terminated"]
        assert tested["automation"]["foreground_input"] is False
        assert tested["automation"]["before"]["foreground_hwnd"] == tested["automation"]["after"]["foreground_hwnd"]
        assert "COUNT=, 1" in tested["debug_output"] and "TEXT=, 中文Automation" in tested["debug_output"]
        screenshots = [step["screenshot"] for step in tested["steps"] if "screenshot" in step]
        assert len(screenshots) == 2 and all(s["nonblank"] for s in screenshots)
        assert all(s["method"] == "xcgui-native-gdi-offscreen" for s in screenshots)
        from PIL import Image, ImageChops
        before, after = [Image.open(s["path"]).convert("RGB") for s in screenshots]
        assert ImageChops.difference(before, after).getbbox() is not None
        # A wrong state assertion must fail even though input itself succeeds.
        scenario = json.loads((examples / "automation_counter.json").read_text("utf-8"))
        for step in scenario["steps"]:
            if step.get("contains") == "COUNT=, 1":
                step.update(contains="COUNT=, 999", timeout=0.2)
        bad_scenario = tmp_path / "wrong-state.json"
        bad_scenario.write_text(json.dumps(scenario), encoding="utf-8")
        failed_test = _run(["--json", "runtime", "test", str(bad_scenario), "--exe", built["exe"]["path"],
                            "--output", str(tmp_path / "runs")], check=False)
        bad_result = json.loads(failed_test.stdout)
        assert failed_test.returncode == 1 and not bad_result["ok"] and bad_result["terminated"]
        # The old valid EXE cannot rescue a broken source on the next build.
        (project.parent / "main.xc").write_text("函数 整型 入口函数_窗口()\n\t不存在的函数()\n\t返回 0\n", encoding="utf-8-sig")
        failed_build = _run(args, check=False)
        (tmp_path / "build-source-error.json").write_text(failed_build.stdout, encoding="utf-8")
        errors = json.loads(failed_build.stdout)
        assert failed_build.returncode == 1 and not errors["ok"]
        assert errors["compiler"]["errorCount"] >= 1 and not errors["compiler"]["compiled"]
        assert any(e.get("line") == 2 and "不存在的函数" in e["message"] for e in errors["diagnostics"])
        assert errors["exe"] is None and not Path(errors["isolated_ide_root"]).exists()
        assert hashlib.sha256(config.read_bytes()).hexdigest() == baseline

