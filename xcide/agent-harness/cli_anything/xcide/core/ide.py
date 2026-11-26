"""Persistent, owned XCIDE sessions. Local files + native ABI, never MCP."""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
import struct
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from filelock import FileLock, Timeout

from cli_anything.xcide.core import build
from cli_anything.xcide.core.project import inspect_project, resolve_ide_root

MAX_MESSAGE = 8 * 1024 * 1024
MAGIC = b"XCIDE02\0"
# The fixed parse-counter location comes from XC-MCP-Next. Never apply it to
# an arbitrary ABI-v3 executable; the exact host image must also match.
PARSE_HOST_SHA256 = "896fb8c8a9c2c26ee70668fc3691bc982358434ec6257f267f0d26a89cffb891"


class IDEError(RuntimeError):
    pass


def _write_json(path: Path, value: Any) -> None:
    pending = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        pending.write_text(json.dumps(value, ensure_ascii=True), encoding="utf-8")
        os.replace(pending, path)
    finally:
        pending.unlink(missing_ok=True)


def _read_json(path: Path) -> dict[str, Any]:
    if path.stat().st_size > MAX_MESSAGE:
        raise IDEError(f"IDE 消息超过大小限制：{path.name}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise IDEError(f"IDE 消息必须是对象：{path.name}")
    return value


def instance_root() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "cli-anything-xcide/ide"


def load_instance(directory: str | os.PathLike[str]) -> tuple[Path, dict[str, Any]]:
    base = Path(directory).expanduser().resolve()
    state = _read_json(base / "instance.json")
    if (state.get("schema") != "xcide-instance/v1" or state.get("directory") != str(base)
            or not isinstance(state.get("token"), str) or len(state["token"]) != 32
            or any(c not in "0123456789abcdef" for c in state["token"])):
        raise IDEError("无效的 IDE 会话描述文件。")
    return base, state


def _ticks() -> int:
    if os.name != "nt":
        raise IDEError("IDE 会话需要 Windows。")
    fn = ctypes.WinDLL("kernel32").GetTickCount64
    fn.argtypes, fn.restype = [], ctypes.c_uint64
    return int(fn())


def _encode_request(token: str, request_id: str, method: str, arguments: dict[str, Any],
                    expires: int) -> bytes:
    values = [token, request_id, method]
    for key, value in arguments.items():
        if not isinstance(key, str) or not isinstance(value, (str, bool, int)):
            raise IDEError("原生桥接参数仅支持字符串、布尔值和整数。")
        values += [key, str(int(value)) if isinstance(value, bool) else str(value)]
    raw = bytearray(MAGIC + struct.pack("<QI", expires, len(values)))
    for value in values:
        if "\0" in value:
            raise IDEError("IDE 参数不得包含 NUL。")
        encoded = value.encode("utf-16-le")
        raw += struct.pack("<I", len(encoded)) + encoded
    if len(raw) > MAX_MESSAGE or len(values) > 67:
        raise IDEError("IDE 请求超过大小或参数数量限制。")
    return bytes(raw)


def _alive(state: dict[str, Any]) -> bool:
    if (state.get("status") != "running" or type(state.get("pid")) is not int
            or state["pid"] <= 0 or not isinstance(state.get("executable"), str) or not state["executable"]):
        return False
    _, kernel = build._windows_api()
    actual = build._process_executable(kernel, state["pid"])
    return bool(actual and Path(actual).resolve() == Path(state["executable"]).resolve())


def request(directory: str | os.PathLike[str], method: str, arguments: dict[str, Any] | None = None,
            *, timeout: float = 15) -> dict[str, Any]:
    if not 0.1 <= timeout <= 180:
        raise IDEError("IDE 请求超时必须在 0.1 到 180 秒之间。")
    base, state = load_instance(directory)
    deadline = time.monotonic() + timeout
    try:
        with FileLock(str(base / "request.lock"), timeout=timeout):
            _, state = load_instance(base)
            if not _alive(state):
                raise IDEError("IDE 会话已停止或进程身份不匹配。")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise IDEError("IDE 请求在等待锁时超时；未执行。")
            identity = uuid.uuid4().hex
            raw = _encode_request(state["token"], identity, method, arguments or {},
                                  _ticks() + int(remaining * 1000))
            _write_json(base / "activity.json", {"time": time.time()})
            pending = base / f"request-{identity}.tmp"
            answer = base / f"response-{identity}.json"
            pending.write_bytes(raw)
            os.replace(pending, base / "request.bin")
            while time.monotonic() < deadline:
                if answer.exists():
                    response = _read_json(answer)
                    answer.unlink()
                    if (response.get("id") != identity or response.get("token") != state["token"]
                            or response.get("pid") != state["pid"] or not isinstance(response.get("result"), dict)):
                        raise IDEError("IDE 响应身份不匹配。")
                    return response["result"]
                if not _alive(state):
                    raise IDEError("IDE 在执行期间退出；操作结果未知，请检查文件后再决定是否重试。")
                time.sleep(0.04)
            raise IDEError("IDE 请求超时；已过期的待处理请求不会执行。已开始的操作结果未知，勿自动重试。")
    except Timeout as exc:
        raise IDEError("IDE 会话繁忙；未提交本次请求。") from exc


def start(project_file: str | os.PathLike[str], *, ide_root: str | os.PathLike[str] | None = None,
          directory: str | os.PathLike[str] | None = None, timeout: float = 120,
          idle_timeout: float = 1800) -> dict[str, Any]:
    if os.name != "nt" or ctypes.sizeof(ctypes.c_void_p) != 8:
        raise IDEError("原生 IDE 会话需要 Windows 64 位 Python。")
    if not 5 <= timeout <= 180 or not 10 <= idle_timeout <= 86400:
        raise IDEError("启动超时范围 5..180 秒，空闲回收范围 10..86400 秒。")
    project = inspect_project(project_file)["project_file"]
    root = resolve_ide_root(ide_root)
    if build.inspect_pe(root / "炫彩IDE.exe")["architecture"] != "AMD64":
        raise IDEError("原生 IDE 会话仅支持 AMD64 ABI-v3 宿主。")
    base = Path(directory).expanduser().resolve() if directory else instance_root() / uuid.uuid4().hex
    base.mkdir(parents=True, exist_ok=False)
    state = {"schema": "xcide-instance/v1", "directory": str(base), "token": uuid.uuid4().hex,
             "project": project, "ide_root": str(root), "idle_timeout": idle_timeout,
             "status": "starting", "created_at": time.time()}
    _write_json(base / "instance.json", state)
    try:
        with (base / "worker.log").open("wb") as log:
            worker = subprocess.Popen([sys.executable, "-m", "cli_anything.xcide.core.ide", "--worker", str(base)],
                                      stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                      creationflags=subprocess.CREATE_NO_WINDOW, close_fds=True)
    except OSError as exc:
        state.update(status="failed", error=str(exc), stopped_at=time.time())
        _write_json(base / "instance.json", state)
        raise IDEError(f"无法创建后台 IDE 工作进程：{exc}") from exc
    deadline = time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            current = _read_json(base / "instance.json")
            if current.get("status") == "running":
                status = request(base, "status", timeout=min(15, max(.1, deadline - time.monotonic())))
                if not status.get("ok"):
                    raise IDEError(str(status))
                return {"ok": True, **public_state(current), "native": status}
            if current.get("status") in {"failed", "stopped"} or worker.poll() is not None:
                raise IDEError(current.get("error") or f"后台 IDE 未能启动；见 {base / 'worker.log'}")
            time.sleep(.1)
        raise IDEError(f"IDE 启动超时；后台清理已请求。会话：{base}")
    except BaseException:
        (base / "stop").write_text(state["token"], encoding="ascii")
        raise


def public_state(state: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in state.items() if k != "token"}


def instances(root: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    directory = Path(root).expanduser().resolve() if root else instance_root()
    entries = []
    for path in sorted(directory.glob("*/instance.json")):
        try:
            _, value = load_instance(path.parent)
            value = public_state(value)
            value["alive"] = _alive(value)
        except (OSError, ValueError, RuntimeError) as exc:
            value = {"directory": str(path.parent), "error": str(exc), "alive": False}
        entries.append(value)
    return {"ok": True, "instances": entries, "count": len(entries)}


def stop(directory: str | os.PathLike[str], *, timeout: float = 20) -> dict[str, Any]:
    if not .1 <= timeout <= 180:
        raise IDEError("停止超时必须在 0.1 到 180 秒之间")
    base, state = load_instance(directory)
    if state.get("status") in {"stopped", "failed"}:
        return {"ok": not state.get("cleanup_error"), **public_state(state)}
    (base / "stop").write_text(state["token"], encoding="ascii")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = _read_json(base / "instance.json")
        if state.get("status") in {"stopped", "failed"}:
            return {"ok": not state.get("cleanup_error"), **public_state(state)}
        time.sleep(.05)
    raise IDEError("IDE 停止尚未完成；已请求清理，勿按 PID 终止其他 IDE。")


def _worker(directory: str) -> None:
    from cli_anything.xcide.utils.native_build import compile_native
    from cli_anything.xcide.utils.win_debug import BackgroundProcess
    from cli_anything.xcide.utils.win_desktop import PrivateDesktop
    base, state = load_instance(directory)
    isolated = process = desktop = None
    state["worker_pid"] = os.getpid()
    try:
        isolated, executable, _ = build._isolated_ide(Path(state["ide_root"]), Path(state["project"]))
        compile_native(Path(__file__).resolve().parents[1] / "native/ide_bridge.cpp",
                       isolated / "data/plug/plug_cli_ide.dll", dll=True)
        if (base / "stop").exists():
            return
        desktop = PrivateDesktop()
        state["observations"] = {"before": desktop.observation()}
        environment = {k: v for k, v in os.environ.items()
                       if not k.upper().startswith(("XC_MCP_", "CLI_ANYTHING_XCIDE_"))}
        environment.update(CLI_ANYTHING_XCIDE_IPC=str(base), CLI_ANYTHING_XCIDE_IPC_TOKEN=state["token"],
                           CLI_ANYTHING_XCIDE_PARSE_VERIFIED="1" if hashlib.sha256(executable.read_bytes()).hexdigest() == PARSE_HOST_SHA256 else "0")
        process = BackgroundProcess([str(executable), state["project"]], isolated, environment, desktop.name)
        state.update(pid=process.pid, executable=str(executable), desktop=desktop.name,
                     foreground_input=False, transport="local-files/native-abi", isolated_root=str(isolated))
        ready_deadline = time.monotonic() + 60
        while not (base / "bridge-ready.json").exists():
            if process.poll() is not None or time.monotonic() > ready_deadline:
                raise IDEError("IDE 原生桥接未就绪（需要 ABI v3）。")
            if (base / "stop").exists():
                return
            time.sleep(.05)
        ready = _read_json(base / "bridge-ready.json")
        if ready.get("token") != state["token"] or ready.get("pid") != process.pid:
            raise IDEError("IDE 桥接就绪身份不匹配。")
        state["status"] = "running"
        _write_json(base / "instance.json", state)
        active = time.monotonic()
        stamp = None
        while process.poll() is None:
            if (base / "stop").exists() and (base / "stop").read_text("ascii") == state["token"]:
                break
            current = (base / "activity.json").stat().st_mtime_ns if (base / "activity.json").exists() else None
            if current != stamp:
                stamp, active = current, time.monotonic()
            if time.monotonic() - active >= state["idle_timeout"]:
                state["reason"] = "idle_timeout"
                break
            time.sleep(.1)
    except BaseException as exc:
        state.update(status="failed", error=str(exc))
    finally:
        errors = []
        if process:
            try:
                if process.poll() is None:
                    build._close_ide(process.pid, Path(state.get("executable", str(isolated / "炫彩IDE.exe"))), desktop.handle, timeout=3)
                    if process.poll() is None:
                        process.terminate_tree()
                state["exit_code"] = process.poll()
            except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
                errors.append(str(exc))
            finally:
                try:
                    process.close()
                except OSError as exc:
                    errors.append(str(exc))
        if desktop:
            state["observations"]["after"] = desktop.observation()
            try:
                desktop.close()
            except OSError as exc:
                errors.append(str(exc))
        if isolated:
            try:
                build._remove_isolated_ide(isolated)
            except (OSError, RuntimeError) as exc:
                errors.append(str(exc))
        if state.get("status") != "failed":
            state["status"] = "stopped"
        state.update(stopped_at=time.time(), cleanup_error="; ".join(errors) or None)
        _write_json(base / "instance.json", state)


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "--worker":
        raise SystemExit("Internal IDE worker; use cli-anything-xcide ide start.")
    _worker(sys.argv[2])
