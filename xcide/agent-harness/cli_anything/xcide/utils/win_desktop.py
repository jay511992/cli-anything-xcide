"""Background XCGUI input on an isolated desktop; never synthesize global input."""
from __future__ import annotations

import ctypes as C
import hashlib
import queue
import threading
import uuid
from ctypes import wintypes as W
from pathlib import Path
from typing import Any

from cli_anything.xcide.core.build import _windows_api, _process_executable

KEYS = {"ENTER": 0x0D, "TAB": 0x09, "ESC": 0x1B, "SPACE": 0x20,
        "BACKSPACE": 0x08, "DELETE": 0x2E, "LEFT": 0x25, "UP": 0x26,
        "RIGHT": 0x27, "DOWN": 0x28, "HOME": 0x24, "END": 0x23}
MAGIC = 0x58435431
CALLBACK = getattr(C, "WINFUNCTYPE", C.CFUNCTYPE)(W.BOOL, W.HWND, W.LPARAM)


class Request(C.Structure):
    _fields_ = [("version", W.DWORD), ("operation", W.DWORD), ("sequence", W.DWORD),
                ("x", C.c_int), ("y", C.c_int), ("key", W.DWORD),
                ("token", W.WCHAR * 33), ("text", W.WCHAR * 4097)]


class CopyData(C.Structure):
    _fields_ = [("tag", C.c_size_t), ("size", W.DWORD), ("data", C.c_void_p)]


class PrivateDesktop:
    def __init__(self) -> None:
        self.user, _ = _windows_api()
        self.user.CreateDesktopW.argtypes = [W.LPCWSTR, W.LPCWSTR, C.c_void_p, W.DWORD, W.DWORD, C.c_void_p]
        self.user.CreateDesktopW.restype = W.HANDLE
        self.user.CloseDesktop.argtypes = [W.HANDLE]
        self.user.CloseDesktop.restype = W.BOOL
        self.token = uuid.uuid4().hex
        self.name = "xcide-test-" + self.token
        self.handle = self.user.CreateDesktopW(self.name, None, None, 0, 0x1FF, None)
        if not self.handle:
            raise C.WinError(C.get_last_error())

    def close(self) -> None:
        if self.handle:
            if not self.user.CloseDesktop(self.handle):
                raise C.WinError(C.get_last_error())
            self.handle = None

    def observation(self) -> dict[str, Any]:
        """Read the input desktop without changing focus or cursor state."""
        self.user.GetForegroundWindow.argtypes = []
        self.user.GetForegroundWindow.restype = W.HWND
        self.user.GetCursorPos.argtypes = [C.POINTER(W.POINT)]
        self.user.GetCursorPos.restype = W.BOOL
        point = W.POINT()
        ok = self.user.GetCursorPos(C.byref(point))
        return {"foreground_hwnd": self.user.GetForegroundWindow(),
                "cursor": [point.x, point.y] if ok else None}


class Desktop:
    def __init__(self, pid: int, executable: Path, isolated: PrivateDesktop, directory: Path):
        self.pid, self.executable = pid, executable
        self.isolated, self.directory = isolated, directory
        self.sequence = 0
        self.user, self.kernel = _windows_api()
        signatures = {
            "GetClientRect": ([W.HWND, C.POINTER(W.RECT)], W.BOOL),
            "GetDpiForWindow": ([W.HWND], W.UINT),
            "IsIconic": ([W.HWND], W.BOOL),
            "EnumDesktopWindows": ([W.HANDLE, CALLBACK, W.LPARAM], W.BOOL),
            "SendMessageTimeoutW": ([W.HWND, W.UINT, W.WPARAM, W.LPARAM, W.UINT,
                                      W.UINT, C.POINTER(C.c_size_t)], C.c_ssize_t),
            "SetThreadDpiAwarenessContext": ([C.c_void_p], C.c_void_p),
        }
        for name, (args, result) in signatures.items():
            fn = getattr(self.user, name)
            fn.argtypes, fn.restype = args, result
        self.old_dpi = self.user.SetThreadDpiAwarenessContext(C.c_void_p(-4))
        if not self.old_dpi:
            raise C.WinError(C.get_last_error())

    def close(self) -> None:
        if self.old_dpi:
            self.user.SetThreadDpiAwarenessContext(self.old_dpi)
            self.old_dpi = None

    def owner(self, hwnd: int) -> int:
        pid = W.DWORD()
        self.user.GetWindowThreadProcessId(hwnd, C.byref(pid))
        return pid.value

    def verify(self, hwnd: int) -> None:
        if self.owner(hwnd) != self.pid:
            raise RuntimeError("目标窗口已失效或不属于本次启动的进程。")
        path = _process_executable(self.kernel, self.pid)
        if not path or Path(path).resolve() != self.executable:
            raise RuntimeError("目标进程路径与本次启动的程序不一致。")

    def title(self, hwnd: int) -> str:
        self.verify(hwnd)
        text = C.create_unicode_buffer(self.user.GetWindowTextLengthW(hwnd) + 1)
        self.user.GetWindowTextW(hwnd, text, len(text))
        return text.value

    def windows(self, contains: str = "") -> list[int]:
        found = []

        def collect(hwnd: int, _: int) -> bool:
            if self.owner(hwnd) == self.pid and self.user.IsWindowVisible(hwnd):
                rect = W.RECT()
                self.user.GetClientRect(hwnd, C.byref(rect))
                if rect.right > 0 and rect.bottom > 0 and contains in self.title(hwnd):
                    found.append(int(hwnd))
            return True

        C.set_last_error(0)
        if not self.user.EnumDesktopWindows(self.isolated.handle, CALLBACK(collect), 0) and C.get_last_error():
            raise C.WinError(C.get_last_error())
        return found

    def geometry(self, hwnd: int) -> dict[str, Any]:
        self.verify(hwnd)
        if self.user.IsIconic(hwnd):
            raise RuntimeError("目标窗口在测试桌面内已最小化。")
        rect = W.RECT()
        if not self.user.GetClientRect(hwnd, C.byref(rect)):
            raise C.WinError(C.get_last_error())
        return {"size": [rect.right, rect.bottom], "dpi": self.user.GetDpiForWindow(hwnd),
                "hwnd": hwnd, "title": self.title(hwnd), "desktop": self.isolated.name}

    def request(self, hwnd: int, operation: int, pump: Any, timeout: float,
                **values: Any) -> int:
        self.verify(hwnd)
        self.sequence += 1
        request = Request(version=1, operation=operation, sequence=self.sequence,
                          token=self.isolated.token, **values)
        data = CopyData(MAGIC, C.sizeof(request), C.cast(C.pointer(request), C.c_void_p))
        result: queue.Queue = queue.Queue()

        def send() -> None:
            try:
                answer = C.c_size_t()
                if not self.user.SendMessageTimeoutW(hwnd, 0x4A, 0, C.addressof(data), 0x2 | 0x20,
                                                    max(1, int(timeout * 1000)), C.byref(answer)):
                    result.put(C.WinError(C.get_last_error()))
                else:
                    result.put(answer.value)
            except Exception as exc:
                result.put(exc)

        # Debug events pause all target threads. Keep the launching thread
        # pumping while the bounded worker waits for the UI-thread response.
        worker = threading.Thread(target=send, daemon=True)
        worker.start()
        while worker.is_alive():
            pump()
        answer = result.get_nowait()
        if isinstance(answer, Exception):
            raise answer
        if answer != (MAGIC if operation == 1 else 1):
            raise RuntimeError("后台 XCGUI 测试适配器未就绪或操作不受支持；请接入 automation_bridge.h。截图需要 GDI 渲染。")
        return self.sequence

    def click(self, hwnd: int, x: int, y: int, pump: Any, timeout: float) -> dict[str, Any]:
        geometry = self.geometry(hwnd)
        width, height = geometry["size"]
        if not (0 <= x < min(width, 32768) and 0 <= y < min(height, 32768)):
            raise ValueError("点击坐标超出当前客户区或 Win32 有符号坐标范围。")
        self.request(hwnd, 2, pump, timeout, x=x, y=y)
        return {**geometry, "client_point": [x, y], "method": "xcgui-ui-thread-message"}

    def type_text(self, hwnd: int, text: str, pump: Any, timeout: float) -> None:
        if len(text.encode("utf-16-le")) > 8192:
            raise ValueError("文本不能超过 4096 个 UTF-16 码元。")
        self.request(hwnd, 3, pump, timeout, text=text)

    def key(self, hwnd: int, key: str, pump: Any, timeout: float) -> None:
        self.request(hwnd, 4, pump, timeout, key=KEYS[key])

    def screenshot(self, hwnd: int, path: Path, pump: Any, timeout: float) -> dict[str, Any]:
        from PIL import Image, ImageStat
        geometry = self.geometry(hwnd)
        sequence = self.request(hwnd, 5, pump, timeout)
        bitmap = self.directory / f"capture-{sequence}.bmp"
        if bitmap.stat().st_size > 64 * 1024 * 1024 + 54:
            raise RuntimeError("后台截图超过大小限制。")
        with Image.open(bitmap) as source:
            if list(source.size) != geometry["size"]:
                raise RuntimeError("截图尺寸与当前客户区不一致。")
            image = source.convert("RGB")
        image.save(path)
        stats = ImageStat.Stat(image)
        return {**geometry, "path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "method": "xcgui-native-gdi-offscreen", "mean": stats.mean, "variance": stats.var,
                "nonblank": max(stats.var) > 1 and max(stats.mean) > 1}

    def request_close(self, hwnd: int) -> None:
        self.verify(hwnd)
        if not self.user.PostMessageW(hwnd, 0x10, 0, 0):
            raise C.WinError(C.get_last_error())
