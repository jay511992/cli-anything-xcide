"""通过本机 GUI 快捷键调用真实炫语言编译器，并核验新产物。"""

from __future__ import annotations

import hashlib
import ctypes
import os
import re
import shutil
import struct
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cli_anything.xcide.core.project import inspect_project, resolve_ide_root


class BuildError(RuntimeError):
    """The real IDE/MSVC backend is missing, failed, or could not be verified."""


def _windows_api() -> Any:
    if os.name != "nt":
        raise BuildError("炫彩 IDE 的无 MCP 构建需要 Windows 登录会话和创建后台桌面的权限。")
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM), wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostMessageW.restype = wintypes.BOOL
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                     ctypes.POINTER(wintypes.DWORD)]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    return user32, kernel32


def _process_executable(kernel32: Any, pid: int) -> str | None:
    handle = kernel32.OpenProcess(0x1000, False, pid)
    if not handle:
        return None
    try:
        size = wintypes.DWORD(32768)
        value = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, value, ctypes.byref(size)):
            return None
        return value.value
    finally:
        kernel32.CloseHandle(handle)


def _make_junction(link: Path, target: Path) -> None:
    """Create a data-directory junction without altering the IDE installation."""
    link.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              creationflags=subprocess.CREATE_NO_WINDOW)
    if completed.returncode != 0:
        raise BuildError(f"无法建立隔离 IDE 数据目录链接 {link} → {target}: {completed.stderr.strip()}")


def _isolated_ide(root: Path, project: Path) -> tuple[Path, Path, Path]:
    """Prepare a compact plugin-free IDE copy with a private project config."""
    base = Path(tempfile.mkdtemp(prefix="cli-anything-xcide-"))
    data_target = base / "data"
    private_config = data_target / "config"
    executable = base / "炫彩IDE.exe"
    try:
        shutil.copy2(root / "炫彩IDE.exe", executable)
        required_dlls = {"xcgui.dll", "msdia140.dll", "msdia140x64.dll", "libgcc_s_seh-1.dll",
                         "libgfortran-5.dll", "libquadmath-0.dll", "libwinpthread-1.dll",
                         "liblapack.dll", "libcrypto-1_1-x64.dll", "libssl-1_1-x64.dll", "libcurl.dll",
                         "libssh2.dll", "openblas.dll", "onnxruntime.dll", "faiss.dll"}
        for dependency in root.glob("*.dll"):
            if dependency.name.casefold() in required_dlls:
                shutil.copy2(dependency, base / dependency.name)
        for dependency_name in ("XCGUI.dll", "msdia140.dll", "msdia140x64.dll"):
            dependency = root / dependency_name
            if dependency.is_file() and not (base / dependency.name).exists():
                shutil.copy2(dependency, base / dependency.name)
        for dependency in root.glob("*.DLL"):
            if dependency.name.casefold() in required_dlls and not (base / dependency.name).exists():
                shutil.copy2(dependency, base / dependency.name)
        original_data = root / "data"
        private_config.mkdir(parents=True)
        shutil.copytree(original_data / "config", private_config, dirs_exist_ok=True)
        if not (original_data / "XC-Module").is_dir():
            raise BuildError(f"炫彩 IDE 安装缺少模块库目录：{original_data / 'XC-Module'}")
        _make_junction(data_target / "XC-Module", original_data / "XC-Module")
        if (original_data / "XC-Module-dev").is_dir():
            _make_junction(data_target / "XC-Module-dev", original_data / "XC-Module-dev")
        for entry in original_data.iterdir():
            if entry.name.casefold() in {"config", "plug", "xc-module", "xc-module-dev"}:
                continue
            destination = data_target / entry.name
            if entry.name.casefold() in {"vc", "template"} and entry.is_dir():
                _make_junction(destination, entry)
            elif entry.is_dir() and entry.name.casefold() in {"font", "image", "theme", "svg", "xml", "tool", "skin_black", "skin_white"}:
                _make_junction(destination, entry)
            elif entry.is_file():
                shutil.copy2(entry, destination)
        (data_target / "plug").mkdir(parents=True)
        config_file = private_config / "config.config"
        if config_file.is_file():
            tree = ET.parse(config_file)
            config_root = tree.getroot()
            projects = config_root.find("projects")
            if projects is None:
                projects = ET.SubElement(config_root, "projects")
            for item in list(projects):
                projects.remove(item)
            projects.set("activate", str(project))
            ET.SubElement(projects, "item", {"path": str(project), "open": "1"})
            tree.write(config_file, encoding="utf-8", xml_declaration=True)
        (base / "user").mkdir()
        return base, executable, data_target
    except BaseException:
        _remove_isolated_ide(base)
        raise


def _remove_isolated_ide(base: Path) -> None:
    """Remove only this command's temporary IDE tree, unlinking junctions first."""
    base = base.resolve()
    if base.parent != Path(tempfile.gettempdir()).resolve() or not base.name.startswith("cli-anything-xcide-"):
        raise BuildError(f"拒绝清理非本次临时 IDE 目录：{base}")
    data = base / "data"
    for root in (data, base):
        if root.is_dir():
            for child in root.iterdir():
                try:
                    is_junction = getattr(child, "is_junction", lambda: False)()
                except OSError:
                    is_junction = False
                if is_junction:
                    os.rmdir(child)
    shutil.rmtree(base, ignore_errors=True)


def _ide_windows(pid: int, expected_executable: Path, desktop: int | None = None) -> list[int]:
    user32, kernel32 = _windows_api()
    executable = _process_executable(kernel32, pid)
    if not executable or Path(executable).resolve() != expected_executable.resolve():
        raise BuildError(f"PID {pid} 不属于所选 IDE：{executable or '无法核验进程路径'}")
    windows: list[int] = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def collect(hwnd: int, _lparam: int) -> bool:
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            title = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, title, len(title))
            windows.append(int(hwnd))
        return True

    ctypes.set_last_error(0)
    if desktop is not None:
        user32.EnumDesktopWindows.argtypes = [wintypes.HANDLE, callback_type, wintypes.LPARAM]
        user32.EnumDesktopWindows.restype = wintypes.BOOL
        ok = user32.EnumDesktopWindows(desktop, callback_type(collect), 0)
    else:
        ok = user32.EnumWindows(callback_type(collect), 0)
    if not ok and ctypes.get_last_error():
        raise BuildError("枚举 IDE 顶层窗口失败。")
    return windows


def _post_f7(pid: int, executable: Path, desktop: int | None = None) -> None:
    user32, _kernel32 = _windows_api()
    windows = _ide_windows(pid, executable, desktop)
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.restype = ctypes.c_int
    candidates = []
    for window in windows:
        name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(window, name, len(name))
        if name.value == "XCGUI" and user32.GetWindowTextLengthW(window) > 0:
            candidates.append(window)
    if len(candidates) != 1:
        raise BuildError("无法唯一定位目标 IDE 的 XCGUI 主窗口，未发送 F7。")
    hwnd = candidates[0]
    # F7 key down and up are posted only to the verified IDE's own window.
    for message, state in ((0x0100, 0x00420001), (0x0101, 0xC0420001)):
        if not user32.PostMessageW(hwnd, message, 0x76, state):
            raise BuildError(f"向已核验的 IDE 窗口发送 F7 失败：Win32 {ctypes.get_last_error()}")


def _close_ide(pid: int, executable: Path, desktop: int | None = None, timeout: float = 15) -> None:
    user32, kernel32 = _windows_api()
    windows = _ide_windows(pid, executable, desktop)
    if not windows:
        return
    for hwnd in windows:
        user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        handle = kernel32.OpenProcess(0x00100000, False, pid)
        if not handle:
            return
        try:
            if kernel32.WaitForSingleObject(handle, 0) == 0:
                return
        finally:
            kernel32.CloseHandle(handle)
        time.sleep(0.2)
    raise BuildError(f"IDE 进程 {pid} 未在正常关闭请求后退出；没有强制结束该进程。")


def _launch_ide(command: list[str], root: Path, environment: dict[str, str], desktop: str) -> Any:
    from cli_anything.xcide.utils.win_debug import BackgroundProcess
    return BackgroundProcess(command, root, environment, desktop)


def _private_desktop() -> Any:
    from cli_anything.xcide.utils.win_desktop import PrivateDesktop
    return PrivateDesktop()


def _native_dialogs(pid: int, executable: Path, desktop: int) -> list[dict[str, Any]]:
    """Read only native dialogs of this private IDE; never confirm a button."""
    user, _ = _windows_api()
    user.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user.GetClassNameW.restype = ctypes.c_int
    callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user.EnumChildWindows.argtypes = [wintypes.HWND, callback, wintypes.LPARAM]
    user.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
                                       wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t)]
    user.SendMessageTimeoutW.restype = ctypes.c_ssize_t
    dialogs = []
    for hwnd in _ide_windows(pid, executable, desktop):
        name = ctypes.create_unicode_buffer(256)
        user.GetClassNameW(hwnd, name, len(name))
        if name.value != "#32770":
            continue
        title = ctypes.create_unicode_buffer(1024)
        user.GetWindowTextW(hwnd, title, len(title))
        texts = []

        def read(child: int, _: int) -> bool:
            if len(texts) >= 32:
                return False
            value = ctypes.create_unicode_buffer(4096)
            count = ctypes.c_size_t()
            if user.SendMessageTimeoutW(child, 0xD, len(value), ctypes.addressof(value), 2, 100, ctypes.byref(count)) and value.value:
                texts.append(value.value)
            return True

        user.EnumChildWindows(hwnd, callback(read), 0)
        dialogs.append({"hwnd": hwnd, "title": title.value, "texts": texts})
    return dialogs


def inspect_pe(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Read and verify a new compiler output's actual Windows PE machine type."""
    file_path = Path(path).resolve()
    with file_path.open("rb") as handle:
        header = handle.read(64)
        if len(header) < 64 or header[:2] != b"MZ":
            raise BuildError(f"The compiler output has no valid DOS/PE header: {file_path}")
        offset = struct.unpack_from("<I", header, 0x3C)[0]
        handle.seek(offset)
        signature = handle.read(6)
    if len(signature) != 6 or signature[:4] != b"PE\0\0":
        raise BuildError(f"The compiler output has no valid PE signature: {file_path}")
    machine = struct.unpack_from("<H", signature, 4)[0]
    return {
        "path": str(file_path),
        "machine": f"0x{machine:04x}",
        "architecture": {0x8664: "AMD64", 0x014C: "x86", 0xAA64: "ARM64"}.get(machine, "unknown"),
        "bytes": file_path.stat().st_size,
        "modified_at": datetime.fromtimestamp(file_path.stat().st_mtime, timezone.utc).isoformat(),
        "sha256": hashlib.sha256(file_path.read_bytes()).hexdigest(),
    }


def _expected_executable(project: Path, info: dict[str, Any]) -> Path:
    """Resolve the selected native output instead of accepting arbitrary EXEs."""
    platform = info["platform"]
    if platform not in {"x64", "x86"}:
        raise BuildError(f"无法核验工程目标架构：{platform!r}")
    settings = ET.parse(project).getroot().find("./vc/setting")
    configs = [node for node in settings.findall("config")
               if node.get("name") == info["configuration"]] if settings is not None else []
    if len(configs) != 1 or configs[0].find(platform) is None:
        raise BuildError("无法唯一确定当前工程的输出配置。")
    selected = configs[0].find(platform)
    common, output = selected.find("common"), selected.find("out")
    kind = common.get("type", "exe") if common is not None else "exe"
    if kind not in {"exe", "应用程序(.exe)"}:
        raise BuildError(f"当前构建核验仅支持 EXE 工程，实际输出类型：{kind}")
    name = (output.get("name", "") if output is not None else "").strip() or project.stem
    directory = (output.get("out_path", "") if output is not None else "").strip()
    if re.search(r"\$\(|\$\{|%[^%]+%", name + directory):
        raise BuildError("输出名称或目录含有无法解析的变量，无法确定目标 EXE。")
    if Path(name).name != name or any(char in name for char in '/\\:<>"|?*'):
        raise BuildError(f"输出名称不是有效的 EXE 文件名：{name!r}")
    if not name.casefold().endswith(".exe"):
        name += ".exe"
    if not directory:
        debug = common.get("debug") if common is not None else None
        if debug is None:
            debug = {"调试版": "1", "发布版": "0"}.get(info["configuration"])
        if debug not in {"0", "1"}:
            raise BuildError("无法从当前配置确定 Debug/Release 输出目录。")
        directory = ("Debug" if debug == "1" else "Release") + ("64" if platform == "x64" else "")
    output_dir = Path(directory.replace("\\", "/"))
    if output_dir.drive and not output_dir.is_absolute():
        raise BuildError(f"输出目录不能使用盘符相对路径：{directory}")
    return (project.parent / output_dir / name).resolve()


def _artifact_stamp(path: Path) -> tuple[int, int] | None:
    try:
        stat = path.stat()
        return stat.st_mtime_ns, stat.st_size
    except FileNotFoundError:
        return None


def build_project(
    project_file: str | os.PathLike[str],
    *,
    ide_root: str | os.PathLike[str] | None = None,
    timeout: int = 240,
    diagnostics: bool = False,
) -> dict[str, Any]:
    """用炫彩 IDE 的真实编译器构建工程，不连接 MCP。

    IDE 通过文件关联打开目标工程，按 F7 发起构建。成功仅表示检测到本轮新
    生成或更新的架构正确 PE 文件。diagnostics=True 额外加载私有输出桥接，
    要求真实编译完成、错误为零以及新 PE 同时成立。
    """
    if not 30 <= timeout <= 1200:
        raise BuildError("Compiler timeout must be between 30 and 1200 seconds.")
    project = Path(project_file).expanduser().resolve()
    project_info = inspect_project(project)
    root = resolve_ide_root(ide_root)
    executable = root / "炫彩IDE.exe"
    if os.name != "nt":
        raise BuildError("炫彩 IDE 构建只能在 Windows 上运行。")
    expected = _expected_executable(project, project_info)
    before = _artifact_stamp(expected)
    isolated_root, executable, isolated_data = _isolated_ide(root, project)
    plugin_directory = isolated_data / "plug"
    isolated_plugins = sorted(path.name for path in plugin_directory.iterdir()) if plugin_directory.is_dir() else []
    if isolated_plugins:
        _remove_isolated_ide(isolated_root)
        raise BuildError(f"隔离 IDE 插件目录必须为空；发现：{', '.join(isolated_plugins)}")
    command = [str(executable), str(project)]
    started_at_ns = time.time_ns()
    process = None
    stable_stamp: tuple[int, int] | None = None
    stable_since = 0.0
    stability_verified = False
    snapshot_path = None
    compiler_result = None
    baseline_output = ""
    last_output = ""
    observed_output = ""
    output_since = 0.0
    desktop = None
    failure_message = None
    cleanup_error = None
    terminated = False
    dialogs: list[dict[str, Any]] = []
    desktop_observations: dict[str, Any] = {}
    try:
        desktop = _private_desktop()
        desktop_observations["before"] = desktop.observation()
        if diagnostics:
            from cli_anything.xcide.core import diagnostics as output_reader
            host_arch = inspect_pe(executable)["architecture"]
            if host_arch != "AMD64":
                raise BuildError("输出桥接当前仅支持 AMD64 炫彩 IDE 宿主。")
            snapshot_path = output_reader.prepare_bridge(isolated_root, "x64")
            isolated_plugins = ["plug_cli_output.dll"]
        child_env = dict(os.environ)
        child_env.pop("CLI_ANYTHING_XCIDE_OUTPUT", None)
        if snapshot_path:
            child_env["CLI_ANYTHING_XCIDE_OUTPUT"] = str(snapshot_path)
        child_env["LOCALAPPDATA"] = str(isolated_root / "user")
        for key in ("XC_MCP_PROJECT", "XC_MCP_INSTANCE", "XC_MCP_URL", "XC_MCP_TOKEN", "XC_MCP_INSTANCE_DIR"):
            child_env.pop(key, None)
        process = _launch_ide(command, isolated_root, child_env, desktop.name)
        time.sleep(2)
        if process.poll() is not None:
            raise BuildError(f"炫彩 IDE 启动失败，退出码：{process.returncode}")
        if snapshot_path:
            ready_deadline = time.monotonic() + min(timeout, 30)
            ready_text = None
            ready_since = time.monotonic()
            bridge_ready = False
            while time.monotonic() < ready_deadline:
                dialogs = _native_dialogs(process.pid, executable, desktop.handle)
                if dialogs:
                    raise BuildError("隔离 IDE 弹出原生对话框；详情见 ide_dialogs。")
                snapshot = output_reader.read_snapshot(snapshot_path, process.pid, project)
                if snapshot:
                    observed_output = snapshot["text"]
                    user32, _ = _windows_api()
                    threads = {user32.GetWindowThreadProcessId(hwnd, None)
                               for hwnd in _ide_windows(process.pid, executable, desktop.handle)}
                    if snapshot["ui_thread"] not in threads:
                        raise BuildError("输出桥接未在目标 IDE 的 UI 线程中运行。")
                    if snapshot["text"] != ready_text:
                        ready_text, ready_since = snapshot["text"], time.monotonic()
                    if "错误列表:" in ready_text and time.monotonic() - ready_since >= 1:
                        baseline_output = ready_text
                        bridge_ready = True
                        break
                if process.poll() is not None:
                    break
                time.sleep(0.1)
            else:
                raise BuildError("等待私有 IDE 输出桥接就绪超时。")
            if not bridge_ready:
                raise BuildError("IDE 在输出桥接就绪前退出。")
        _post_f7(process.pid, executable, desktop.handle)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if process.poll() is None:
                dialogs = _native_dialogs(process.pid, executable, desktop.handle)
                if dialogs:
                    raise BuildError("隔离 IDE 弹出原生对话框；详情见 ide_dialogs。")
            if snapshot_path:
                snapshot = output_reader.read_snapshot(snapshot_path, process.pid, project)
                if snapshot:
                    observed_output = snapshot["text"]
                if snapshot and snapshot["text"] != baseline_output:
                    text = snapshot["text"]
                    # This IDE resets the output pane on F7. Require a build
                    # marker, so background startup diagnostics are not reused.
                    if any(marker in text for marker in ("检查文件依赖", "开始编译代码", "跳过编译")):
                        compiler_result = output_reader.parse_output(text)
                        if text != last_output:
                            last_output, output_since = text, time.monotonic()
                        if compiler_result["terminal"] and not compiler_result["ok"] and time.monotonic() - output_since >= 0.6:
                            break
            stamp = _artifact_stamp(expected)
            if stamp and stamp != before and stamp[0] >= started_at_ns and stamp[1] > 256:
                if stamp == stable_stamp:
                    now = time.monotonic()
                    if now < deadline and now - stable_since >= 2 and (not diagnostics or (compiler_result and compiler_result["ok"])):
                        stability_verified = True
                        break
                else:
                    stable_stamp, stable_since = stamp, time.monotonic()
            else:
                stable_stamp, stable_since = None, 0.0
            if process.poll() is not None:
                break
            time.sleep(0.4)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        failure_message = f"启动或控制炫彩 IDE 失败：{exc}"
    finally:
        if process is not None and process.poll() is None:
            try:
                _close_ide(process.pid, executable, desktop.handle, timeout=3 if dialogs else 15)
            except (OSError, RuntimeError) as exc:
                cleanup_error = str(exc)
            if process.poll() is None:
                # Only this suspended-created, job-owned private IDE tree.
                terminated = True
                try:
                    process.terminate_tree()
                except (OSError, subprocess.SubprocessError) as exc:
                    cleanup_error = str(exc)
        if process is None or process.poll() is not None:
            _remove_isolated_ide(isolated_root)
        if process is not None:
            process.close()
        desktop_name = desktop.name if desktop else None
        if desktop is not None:
            desktop_observations["after"] = desktop.observation()
            try:
                desktop.close()
            except OSError as exc:
                cleanup_error = str(exc)
    artifact = None
    if stability_verified and _artifact_stamp(expected) == stable_stamp:
        artifact = inspect_pe(expected)
        if _artifact_stamp(expected) != stable_stamp:
            artifact = None
    architecture = project_info["platform"]
    success = bool(artifact and (architecture not in ("x64", "x86") or artifact["architecture"] ==
                                 ("AMD64" if architecture == "x64" else "x86")))
    if diagnostics:
        success = bool(success and compiler_result and compiler_result["ok"])
    success = success and not failure_message and not cleanup_error and not terminated
    result: dict[str, Any] = {
        "ok": success,
        "backend": "本机炫彩IDE GUI + 定向 F7 + Windows PE 产物核验",
        "project": project_info,
        "ide_executable": str(root / "炫彩IDE.exe"),
        "command": command,
        "ide_pid": process.pid if process else None,
        "isolated_ide_root": str(isolated_root),
        "isolated_data_dir": str(isolated_data),
        "isolated_plugins": isolated_plugins,
        "automation": {"desktop": desktop_name, "foreground_input": False,
                       "observations": desktop_observations},
        "ide_dialogs": dialogs,
        "cleanup_error": cleanup_error,
        "terminated": terminated,
        "started_at_ns": started_at_ns,
        "expected_executable": str(expected),
        "build_result": "artifact_updated" if success else "unverified",
        "compiler": {"compiled": None, "skipped": None,
                     "errorCount": None, "diagnostics_available": False,
                     "note": "未启用 --diagnostics 输出桥接；普通构建只核验新 PE，无法确认编译诊断或零错误。"},
        "diagnostics": None,
        "exe": artifact,
    }
    if diagnostics:
        result["backend"] += " + 私有 IDE 输出桥接"
        result["compiler"] = ({key: value for key, value in compiler_result.items()
                               if key not in {"output", "diagnostics", "terminal", "ok"}} if compiler_result else
                              {"compiled": None, "skipped": None, "errorCount": None,
                               "diagnostics_available": False})
        result["diagnostics"] = compiler_result["diagnostics"] if compiler_result else None
        result["compiler_output"] = compiler_result["output"] if compiler_result else observed_output
        result["build_result"] = "compiled" if success else "failed" if compiler_result and compiler_result["failed"] else "unverified"
    if not success:
        result["error"] = failure_message or cleanup_error or ("编译诊断未通过或未确认本轮稳定产物；请检查 compiler、diagnostics 和 compiler_output。" if diagnostics else
                           f"未在超时前确认目标 EXE 已更新且稳定：{expected}；未开启输出桥接诊断。"
                            if artifact is None else
                            f"项目目标架构为 {architecture}，实际产物架构为 {artifact['architecture']}。")
        return result
    return result
