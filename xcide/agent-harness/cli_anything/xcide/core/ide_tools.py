"""XC-MCP-Next tool-name migration without an MCP client/server."""
from __future__ import annotations

import json
import os
import re
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from filelock import FileLock, Timeout

from cli_anything.xcide.core import files, ide, modules, project


def _spec(description: str, properties: dict[str, str] | None = None, required: tuple[str, ...] = (),
          *, mutates: bool = False, note: str = "") -> dict[str, Any]:
    return {"description": description, "mutates": mutates, "note": note,
            "inputSchema": {"type": "object", "properties": {k: {"type": v.split("|") if "|" in v else v}
                             for k, v in (properties or {}).items()}, "required": list(required), "additionalProperties": False}}


TOOLS = {
    "xc_status": _spec("读取本会话 PID、ABI 与桥接状态"),
    "xc_get_project": _spec("读取 IDE 当前工程"),
    "xc_parse_status": _spec("读取解析计数", note="仅支持经过 SHA-256 门禁验证的 IDE 映像"),
    "xc_reset_parse_count": _spec("重置解析计数", mutates=True, note="固定偏移操作；仅支持经过 SHA-256 门禁验证的 IDE 映像"),
    "xc_server": _spec("查询/停止本地桥接会话", {"action": "string"}, mutates=True,
                       note="无 HTTP 服务；start 验证现有会话，创建会话用 ide start；stop 关闭本次私有 IDE"),
    "xc_ide_log": _spec("追加文本到 IDE 调试输出", {"text": "string"}, ("text",), mutates=True),
    "xc_build": _spec("向后台 IDE 投递 F7", mutates=True, note="仅投递，不代表编译成功；完整验收使用 build --diagnostics"),
    "xc_menu_cmd": _spec("投递 compile/recompile/compile_all", {"command": "string", "menu_id": "integer"}, mutates=True),
    "xc_get_output": _spec("读取真实输出面板", {"tailLines": "integer", "maxChars": "integer", "clear": "boolean"},
                           note="与原插件相同，不清空面板；Unicode 截断按字符"),
    "xc_get_dialogs": _spec("读取本 IDE UI 线程的原生/XCGUI 弹窗", {"maxChars": "integer"},
                            note="XMsg 正文对已验证 XCGUI 映像开放；未知布局返回 body_available=false"),
    "xc_read_file": _spec("读取磁盘文本", {"path": "string", "allowOutsideProject": "boolean"}, ("path",)),
    "xc_editor_get": _spec("读取未保存的代码编辑缓冲", {"path": "string"}),
    "xc_editor_set": _spec("保持编码写入磁盘源码", {"path": "string", "text": "string", "bom": "string|boolean", "allowOutsideProject": "boolean"},
                           ("text",), mutates=True, note="与原插件相同，不改 XEdit 内存；返回 reload_required"),
    "xc_new_file": _spec("创建 .xc/.xh 并导入 IDE", {"name": "string", "type": "string"}, ("name",), mutates=True),
    "xc_add_file": _spec("导入文件（多个路径用分号分隔）", {"path": "string", "open": "boolean"}, ("path",), mutates=True),
    "xc_add_dir_files": _spec("批量导入目录内同扩展名文件", {"dir": "string", "ext": "string", "open": "boolean"}, mutates=True),
    "xc_list_projects": _spec("递归查找工程", {"root": "string"}, ("root",)),
    "xc_open_in_ide": _spec("导入并打开文件", {"path": "string"}, ("path",), mutates=True),
    "xc_tree_probe": _spec("工程目录视图", {"action": "string", "name": "string"},
                           note="与原插件相同，不选择或删除 GUI 树节点"),
    "xc_symbol": _spec("IDE 实时符号查询", {"name": "string", "path": "string", "lineno": "integer"}),
    "xc_goto_function": _spec("打开符号所在文件并移动光标", {"name": "string", "root": "string"}, ("name",), mutates=True),
    "xc_list_functions": _spec("静态索引磁盘 .xc 函数", {"root": "string", "filter": "string"}),
    "xc_module_info": _spec("ABI 读取模块元数据", {"path": "string", "name": "string", "module": "string", "author": "string"}),
    "xc_module_list": _spec("模块目录及工程引用", {"limit": "integer", "all": "boolean", "projectOnly": "boolean", "withDeps": "boolean"}),
    "xc_module_search": _spec("模块搜索/依赖反查", {"query": "string", "dependsOn": "string", "limit": "integer", "all": "boolean"}),
    "xc_module_add": _spec("修改磁盘工程模块引用", {"file": "string", "name": "string", "project": "string"}, ("file",), mutates=True),
    "xc_module_remove": _spec("移除磁盘工程模块引用", {"file": "string", "name": "string", "project": "string"}, mutates=True),
    "xc_module_create": _spec("生成 module_*.h/.cpp 及架构/库注解", {
        **{k: "string" for k in ("name", "alias", "author", "remark", "dir", "subdir", "location", "libs", "libs86", "dlls", "dlls86", "includes")},
        "addToProject": "boolean", "force": "boolean"}, ("name",), mutates=True,
        note="默认 location=project、addToProject=true；dev/main 明确写入所选安装目录的模块库"),
    "xc_save_all": _spec("向后台 IDE 投递保存快捷键", mutates=True,
                         note="保留原工具投递语义；saved=null，不承诺保存全部标签，需回读磁盘确认"),
    "xc_probe_cmd": _spec("低层 ABI 诊断", {"cmd_id": "integer", "arg0": "integer", "allow_unsafe": "boolean", "confirm": "string"},
                          ("cmd_id",), mutates=True, note="20/21 为无指针任务；其他编号需显式风险参数，仅作用于私有 IDE"),
}

_BOUNDS = {"limit": (1, 10000), "maxChars": (128, 2 * 1024 * 1024),
           "tailLines": (0, 100000), "lineno": (0, 10000000), "cmd_id": (1, 21),
           "arg0": (-2147483648, 2147483647)}
for _tool, _definition in TOOLS.items():
    for _key, _schema in _definition["inputSchema"]["properties"].items():
        if _key in _BOUNDS:
            _low, _high = _BOUNDS[_key]
            _schema.update(minimum=_low, maximum=65536 if _tool == "xc_get_dialogs" else _high)


def catalog() -> dict[str, Any]:
    return {"ok": True, "transport": "local-files/native-abi", "mcp_required": False,
            "tools": [{"name": k, **v} for k, v in TOOLS.items()], "count": len(TOOLS)}


def validate(name: str, args: Any) -> dict[str, Any]:
    if name not in TOOLS:
        raise ide.IDEError(f"未知工具 {name}；运行 ide tools 查看可用工具。")
    if not isinstance(args, dict):
        raise ide.IDEError("工具参数必须是 JSON 对象。")
    schema = TOOLS[name]["inputSchema"]
    unknown = set(args) - set(schema["properties"])
    missing = set(schema["required"]) - set(args)
    if unknown or missing:
        raise ide.IDEError(f"参数不匹配；未知 {sorted(unknown)}，缺失 {sorted(missing)}")
    types = {str: "string", bool: "boolean", int: "integer"}
    for key, value in args.items():
        allowed = schema["properties"][key]["type"]
        if types.get(type(value)) not in (allowed if isinstance(allowed, list) else [allowed]):
            raise ide.IDEError(f"{key} 必须是 {allowed}")
        if isinstance(value, str) and ("\0" in value or len(value.encode("utf-8")) > 4 * 1024 * 1024):
            raise ide.IDEError(f"{key} 包含 NUL 或超过大小上限")
    for key, (low, high) in _BOUNDS.items():
        if key in args and not low <= args[key] <= high:
            raise ide.IDEError(f"{key} 的范围为 {low}..{high}")
    if name == "xc_get_dialogs" and args.get("maxChars", 16000) > 65536:
        raise ide.IDEError("弹窗 maxChars 不得超过 65536")
    return dict(args)


def _project_path(state: dict[str, Any], args: dict[str, Any]) -> Path:
    return Path(project.inspect_project(args.get("project") or state["project"])["project_file"])


def _path(value: str, project_file: Path, *, outside: bool = False, must_exist: bool = True) -> Path:
    candidate = Path(value).expanduser()
    path = (candidate if candidate.is_absolute() else project_file.parent / candidate).resolve()
    if not outside and not path.is_relative_to(project_file.parent.resolve()):
        raise ide.IDEError("路径位于当前工程之外")
    if any(":" in part for part in path.parts[1:]):
        raise ide.IDEError("路径不得使用 Windows 备用数据流")
    if must_exist and not path.exists():
        raise ide.IDEError(f"路径不存在：{path}")
    return path


def list_functions(root: Path, query: str = "") -> dict[str, Any]:
    if not root.is_dir():
        raise ide.IDEError(f"源码目录不存在：{root}")
    skip = {"debug", "debug64", "release", "release64", "obj", ".git", ".venv", "node_modules", "__pycache__"}
    functions, scanned = [], 0
    pattern = re.compile(r"(?m)^[ \t]*(?:(?:公开|私有|保护|静态)[ \t]+)*函数[ \t]+(?:[^\s(){}]+[ \t]+)?([^\s(){}]+)[ \t]*\(")
    comments = re.compile(r'/\*.*?\*/|//[^\r\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', re.DOTALL)
    for current, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d.casefold() not in skip and not Path(current, d).is_symlink()
                         and not getattr(Path(current, d), "is_junction", lambda: False)())
        for name in sorted(names):
            path = Path(current, name)
            if path.suffix.lower() != ".xc" or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
                continue
            scanned += 1
            if scanned > 2000 or path.stat().st_size > 4 * 1024 * 1024:
                raise ide.IDEError("函数索引超过文件数/文件大小限制")
            text = files._decode(path.read_bytes())[0]
            clean = comments.sub(lambda m: "".join("\n" if ch == "\n" else " " for ch in m.group()), text)
            for match in pattern.finditer(clean):
                if query.casefold() in match[1].casefold():
                    functions.append({"name": match[1], "file": str(path.relative_to(root)),
                                      "path": str(path), "line": clean.count("\n", 0, match.start()) + 1})
            if len(functions) > 20000:
                raise ide.IDEError("函数索引超过条目限制")
    return {"ok": True, "root": str(root), "functions": functions, "count": len(functions), "files_scanned": scanned,
            "source": "disk-static", "line_base": 1}


@project._project_update
def _add_local_module(project_file: Path, header: Path, alias: str) -> dict[str, Any]:
    tree = ET.parse(project_file)
    container = tree.getroot().find("modules")
    if container is None:
        container = ET.SubElement(tree.getroot(), "modules")
    relative = os.path.relpath(header, project_file.parent)
    exists = any(str(item.get("path", "")).replace("/", "\\").casefold() == relative.casefold() for item in container)
    if not exists:
        ET.SubElement(container, "item", {"name": alias, "path": relative})
        project._atomic_project_xml(project_file, tree)
    return {"ok": True, "added": not exists, "file": relative, "restartRequired": True}


@project._project_update
def _remove_reference(project_file: Path, filename: str) -> dict[str, Any]:
    """Remove an exact persisted reference, including a project-local path."""
    tree = ET.parse(project_file)
    container = tree.getroot().find("modules")
    key = filename.replace("/", "\\").casefold()
    found = [] if container is None else [item for item in container.findall("item")
                 if str(item.get("path", "")).replace("/", "\\").casefold() == key]
    for item in found:
        container.remove(item)
    if found:
        project._atomic_project_xml(project_file, tree)
    return {"ok": True, "removed": bool(found), "file": filename,
            "moduleCount": len(container.findall("item")) if container is not None else 0,
            "restartRequired": bool(found), "project": str(project_file)}


def create_module(args: dict[str, Any], project_file: Path, ide_root: Path) -> dict[str, Any]:
    name = args["name"]
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,95}", name):
        raise ide.IDEError("模块 name 必须是有效 C++ 英文标识符（最多 96 字符）")
    stem = name if name.startswith("module_") else "module_" + name
    symbol = stem.removeprefix("module_")
    location = args.get("location", "project")
    if location not in {"project", "dev", "main"}:
        raise ide.IDEError("location 必须是 project/dev/main")
    parent = project_file.parent if location == "project" else ide_root / "data" / ("XC-Module-dev" if location == "dev" else "XC-Module")
    destination = Path(args["dir"]) if args.get("dir") else parent / args.get("subdir", stem)
    if not destination.is_absolute():
        destination = parent / destination
    destination = destination.resolve()
    if not destination.is_relative_to(parent.resolve()):
        raise ide.IDEError("模块目录必须位于所选 location 中")
    alias = args.get("alias") or name
    for key in ("alias", "author", "remark"):
        if any(ch in args.get(key, "") for ch in "\r\n"):
            raise ide.IDEError(f"{key} 不能包含换行（防止破坏模块注解）")
    metadata = ["#pragma once", f"//@模块名称 {alias}", "//@版本 1.0.0",
                f"//@作者 {args.get('author', '')}", f"//@模块备注 {args.get('remark', '')}",
                "//@依赖 module_base.h"]
    missing = []

    def paths(key: str, annotation: str) -> list[str]:
        entries = [item.strip() for item in re.split(r"[;|]", args.get(key, "")) if item.strip()]
        result = []
        for entry in entries:
            if any(c in entry for c in '"\r\n'):
                raise ide.IDEError(f"{key} 中路径不得含引号或换行")
            candidate = Path(entry)
            if candidate.is_absolute() or ".." in candidate.parts or ":" in entry:
                raise ide.IDEError(f"{key} 必须相对于模块目录")
            if not (destination / candidate).exists():
                missing.append(entry)
            result.append(f'//@{annotation} "{entry}"')
        return result

    x64 = paths("libs", "lib") + paths("dlls", "复制文件 @当前模块路径")
    x86 = paths("libs86", "lib") + paths("dlls86", "复制文件 @当前模块路径")
    if x64 or x86:
        metadata += ["#ifdef _WIN64", *x64, "#else", *x86, "#endif"]
    metadata += paths("includes", "包含目录 @当前模块路径")
    metadata += [f'//@src "{stem}.cpp"', "//@模块信息结束", "#if defined(XC_MOUDLE) || defined(XC_MODULE)",
                 '#include "module_base.h"', "#endif", f"//@别名 {alias}_初始化()", f"int xcl_{symbol}_init();", ""]
    header, source = destination / (stem + ".h"), destination / (stem + ".cpp")
    content = ["\r\n".join(metadata), f'#include "{stem}.h"\r\nint xcl_{symbol}_init() {{ return 1; }}\r\n']
    lock = project_file.parent / ".cli-module-create.lock"
    with FileLock(str(lock), timeout=15):
        if any(p.is_symlink() or (p.exists() and not p.is_file()) for p in (header, source)):
            raise ide.IDEError("模块目标必须是普通文件，不得使用符号链接或目录")
        if any(p.exists() for p in (header, source)) and not args.get("force", False):
            raise ide.IDEError("模块头文件或源文件已存在；未修改。覆盖须显式 force=true")
        destination.mkdir(parents=True, exist_ok=True)
        before = {p: p.read_bytes() if p.exists() else None for p in (header, source)}
        written = []
        try:
            for p, body in zip((header, source), content):
                raw = b"\xef\xbb\xbf" + body.encode("utf-8")
                fd, temp = tempfile.mkstemp(prefix=".cli-module-", dir=destination)
                try:
                    with os.fdopen(fd, "wb") as handle:
                        handle.write(raw)
                    if before[p] is None:
                        os.link(temp, p)  # no overwrite in a creation race
                    else:
                        if p.read_bytes() != before[p]:
                            raise ide.IDEError("模块在生成期间被外部修改，已取消")
                        os.replace(temp, p)
                    written.append((p, raw))
                finally:
                    Path(temp).unlink(missing_ok=True)
        except BaseException:
            for p, raw in reversed(written):
                if p.read_bytes() == raw:
                    if before[p] is None:
                        p.unlink()
                    else:
                        p.write_bytes(before[p])
            raise
    result = {"ok": True, "header": str(header), "source": str(source), "moduleDir": str(destination),
              "module": alias, "location": location, "missing": missing, "addedToProject": False}
    if args.get("addToProject", True):
        try:
            result["addResult"] = (_add_local_module(project_file, header, alias) if location == "project"
                                   else modules.add_module(project_file, header.name, ide_root=ide_root, name=alias))
            result.update(addedToProject=True, restartRequired=True)
        except (OSError, RuntimeError, ValueError) as exc:
            result.update(ok=False, filesCreated=True, addError=str(exc))
    return result


def call(directory: str | os.PathLike[str], name: str, arguments: Any, *, timeout: float = 15) -> dict[str, Any]:
    args = validate(name, arguments)
    if not 0.1 <= timeout <= 180:
        raise ide.IDEError("工具超时必须在 0.1 到 180 秒之间")
    base, state = ide.load_instance(directory)
    deadline = time.monotonic() + timeout
    try:
        with FileLock(str(base / "tools.lock"), timeout=timeout):
            remaining = deadline - time.monotonic()
            if remaining < .1:
                raise ide.IDEError("工具在等待锁时超时；未执行")
            result = _call(base, state, name, args, remaining)
    except Timeout as exc:
        raise ide.IDEError("IDE 会话繁忙；未提交本次工具调用") from exc
    return {**result, "tool": name, "transport": "local-files/native-abi"}


def _call(base: Path, state: dict[str, Any], name: str, args: dict[str, Any], timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    def native(method: str, values: dict[str, Any] | None = None) -> dict[str, Any]:
        remaining = deadline - time.monotonic()
        if remaining < .1:
            raise ide.IDEError("工具调用已超时，未提交下一项操作；已完成的步骤保留")
        return ide.request(base, method, values, timeout=remaining)

    if name == "xc_server":
        action = args.get("action", "status")
        if action not in {"start", "stop", "status"}:
            raise ide.IDEError("action 必须是 start/stop/status")
        if action == "stop":
            return ide.stop(base, timeout=max(5, timeout))
        return {**native("status"), "running": True, "port": None, "note": "本地原生会话，无 MCP/HTTP 服务"}
    direct = {"xc_status": "status", "xc_get_project": "project", "xc_parse_status": "parse",
              "xc_reset_parse_count": "reset-parse", "xc_ide_log": "log", "xc_get_dialogs": "dialogs",
              "xc_probe_cmd": "probe", "xc_save_all": "save"}
    if name in direct:
        return native(direct[name], args)
    if name == "xc_get_output":
        result = native("output")
        if not result.get("ok"):
            return result
        text = result["text"]
        total = len(text)
        lines = args.get("tailLines", 200)
        if lines:
            text = "".join(text.splitlines(keepends=True)[-lines:])
        text = text[-args.get("maxChars", 60000):]
        return {**result, "text": text, "length": total, "truncated": len(text) < total, "cleared": False,
                "clearNote": "不清空原生输出面板" if args.get("clear") else ""}
    if name in {"xc_build", "xc_menu_cmd"}:
        mapping = {0x171: "compile", 0x174: "recompile", 0x172: "compile_all"}
        if "menu_id" in args and args["menu_id"] not in mapping:
            raise ide.IDEError("仅支持已知编译菜单 ID 0x171/0x174/0x172")
        command = args.get("command", mapping.get(args.get("menu_id"), "compile"))
        if command not in mapping.values() or ("menu_id" in args and command != mapping[args["menu_id"]]):
            raise ide.IDEError("编译命令无效或与 menu_id 冲突")
        return native("menu", {"command": command})
    # Obtain the actual live project; never silently use stale selection after
    # xc_open_in_ide switches projects. Explicit project is a disk-only override.
    current = native("project")
    if not current.get("ok"):
        return current
    state = {**state, "project": current["project_file"]}
    project_file = _project_path(state, args)
    install = Path(state["ide_root"])
    if name == "xc_editor_get":
        return native("editor", {"path": str(_path(args["path"], project_file))} if args.get("path") else {})
    if name == "xc_read_file":
        path = _path(args["path"], project_file, outside=args.get("allowOutsideProject", False))
        return {"ok": True, **files.read_file(path, project=project_file, allow_outside=args.get("allowOutsideProject", False))}
    if name == "xc_editor_set":
        path = args.get("path")
        if not path:
            current = native("editor")
            if not current.get("ok"):
                return current
            path = current["file"]
        bom = args.get("bom")
        if isinstance(bom, str):
            if bom.lower() not in {"true", "false", "1", "0", "yes", "no", "on", "off"}:
                raise ide.IDEError("bom 必须为 true/false")
            bom = bom.lower() in {"true", "1", "yes", "on"}
        target = _path(path, project_file, outside=args.get("allowOutsideProject", False), must_exist=False)
        result = files.write_file(target, args["text"], project=project_file,
                                  allow_outside=args.get("allowOutsideProject", False), no_bom=bom is False,
                                  force_bom=bom is True)
        return {"ok": True, **result, "channel": "disk", "reload_required": True}
    if name in {"xc_symbol", "xc_goto_function"}:
        values = {k: v for k, v in args.items() if k != "root"}
        if values.get("path"):
            values["path"] = str(_path(values["path"], project_file))
        if args.get("root"):
            _path(args["root"], project_file)
        return native("goto" if name == "xc_goto_function" else "symbol", values)
    if name == "xc_module_info":
        if not any(args.get(k) for k in ("path", "name", "module")):
            raise ide.IDEError("需要 path/name/module 之一")
        if args.get("path"):
            args["path"] = str(Path(args["path"]).expanduser().resolve())
        return native("module-info", args)
    if name == "xc_new_file":
        project._valid_name(args["name"])
        kind = args.get("type", "xc")
        if kind not in {"xc", "xh"}:
            raise ide.IDEError("type 只能是 xc/xh")
        target = project_file.parent / (args["name"] + "." + kind)
        raw = b"\xef\xbb\xbf" + ("//预编译头文件\r\n" if kind == "xh" else "\r\n").encode("utf-8")
        with target.open("xb") as handle:
            handle.write(raw)
        try:
            result = native("import", {"path": str(target), "open": True})
        except (OSError, RuntimeError, ValueError) as exc:
            return {"ok": False, "file": str(target), "created": True, "imported": None,
                    "error": str(exc), "retry_safe": False}
        return {**result, "file": str(target), "created": True, "imported": result.get("ok", False)}
    if name in {"xc_add_file", "xc_open_in_ide", "xc_add_dir_files"}:
        if name == "xc_add_dir_files":
            root = _path(args.get("dir") or str(project_file.parent), project_file)
            ext = args.get("ext", "xc").lstrip(".")
            if not re.fullmatch(r"[A-Za-z0-9]{1,12}", ext):
                raise ide.IDEError("ext 必须是单个文件扩展名")
            paths = [_path(str(p), project_file) for p in sorted(root.iterdir()) if p.is_file() and p.suffix.casefold() == "." + ext.casefold()]
        else:
            values = args["path"].split(";") if name == "xc_add_file" else [args["path"]]
            # Explicit opening of an external project/file is supported, but
            # bulk imports stay within the active project.
            paths = [_path(p, project_file, outside=name == "xc_open_in_ide") for p in values if p]
        if not paths or len(paths) > 2000 or any(not p.is_file() for p in paths):
            raise ide.IDEError("导入需要 1..2000 个真实文件")
        results = []
        for p in paths:
            try:
                results.append(native("import", {"path": str(p), "open": args.get("open", name != "xc_add_dir_files")}))
            except (OSError, RuntimeError, ValueError) as exc:
                results.append({"ok": False, "path": str(p), "error": str(exc), "imported": None})
                break
        return {"ok": len(results) == len(paths) and all(r.get("ok") for r in results), "total": len(paths),
                "attempted": len(results), "imported": sum(bool(r.get("ok")) for r in results), "results": results}
    if name == "xc_list_projects":
        entries = project.list_projects(args["root"], recursive=True)
        return {"ok": True, "projects": entries, "count": len(entries)}
    if name == "xc_list_functions":
        root = _path(args.get("root") or str(project_file.parent), project_file)
        return list_functions(root, args.get("filter", ""))
    if name == "xc_tree_probe":
        if args.get("action", "dump") not in {"dump", "select", "clean"}:
            raise ide.IDEError("action 必须是 dump/select/clean")
        entries = [{"text": p.name, "dir": p.is_dir(), "size": p.stat().st_size if p.is_file() else 0}
                   for p in sorted(project_file.parent.iterdir()) if args.get("name", "") in p.name]
        return {"ok": True, "root": str(project_file.parent), "entries": entries, "count": len(entries),
                "selected": False, "cleaned": False, "note": "文件系统视图；不选择或删除 GUI 树节点"}
    if name in {"xc_module_list", "xc_module_search"}:
        if name == "xc_module_list":
            result = modules.list_modules(ide_root=install, project_file=project_file, limit=10000,
                                          project_only=args.get("projectOnly", False))
            key = "modules"
        else:
            result = modules.search_modules(args.get("query", ""), depends_on=args.get("dependsOn"),
                                            ide_root=install, project_file=project_file, limit=10000)
            key = "hits"
        entries = result[key]
        if args.get("all") is False:
            entries = [entry for entry in entries if entry.get("library") != "XC-Module-dev"]
        result[key] = entries[:args.get("limit", 80)]
        result["count"] = len(result[key])
        if args.get("withDeps") is False:
            result[key] = [{k: v for k, v in entry.items() if k != "deps"} for entry in result[key]]
        return result
    if name == "xc_module_add":
        if Path(args["file"]).name != args["file"]:
            header = _path(args["file"], project_file)
            if not header.is_file() or header.suffix.lower() != ".h":
                raise ide.IDEError("本地模块必须是实际 .h 文件")
            return _add_local_module(project_file, header, args.get("name") or header.stem)
        return modules.add_module(project_file, args["file"], ide_root=install, name=args.get("name"))
    if name == "xc_module_remove":
        filename = args.get("file")
        if not filename and args.get("name"):
            hits = [m for m in project.inspect_project(project_file)["modules"] if m.get("name") == args["name"]]
            if len(hits) == 1:
                filename = hits[0]["path"]
        if not filename:
            raise ide.IDEError("需要 file 或唯一的工程模块 name")
        return _remove_reference(project_file, filename)
    if name == "xc_module_create":
        return create_module(args, project_file, install)
    raise ide.IDEError(f"未实现工具：{name}")
