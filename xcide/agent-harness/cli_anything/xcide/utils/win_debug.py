"""Windows debug events for an owned child process, with bounded output."""
from __future__ import annotations

import ctypes as C
import os
import subprocess
import time
from ctypes import wintypes as W
from pathlib import Path
from typing import Any


class ExceptionRecord(C.Structure):
    _fields_ = [("code", W.DWORD), ("flags", W.DWORD), ("record", C.c_void_p),
                ("address", C.c_void_p), ("count", W.DWORD), ("info", C.c_size_t * 15)]


class ExceptionInfo(C.Structure):
    _fields_ = [("record", ExceptionRecord), ("first", W.DWORD)]


class CreateInfo(C.Structure):
    _fields_ = [("file", W.HANDLE), ("process", W.HANDLE), ("thread", W.HANDLE),
                ("base", C.c_void_p), ("offset", W.DWORD), ("size", W.DWORD),
                ("tls", C.c_void_p), ("start", C.c_void_p), ("image", C.c_void_p), ("unicode", W.WORD)]


class DebugString(C.Structure):
    _fields_ = [("address", C.c_void_p), ("unicode", W.WORD), ("length", W.WORD)]


class DebugUnion(C.Union):
    _fields_ = [("exception", ExceptionInfo), ("create", CreateInfo), ("string", DebugString),
                ("handle", W.HANDLE), ("exit_code", W.DWORD)]


class DebugEvent(C.Structure):
    _fields_ = [("code", W.DWORD), ("pid", W.DWORD), ("tid", W.DWORD), ("data", DebugUnion)]


class JobBasic(C.Structure):
    _fields_ = [("process_time", C.c_int64), ("job_time", C.c_int64), ("flags", W.DWORD),
                ("min_working", C.c_size_t), ("max_working", C.c_size_t), ("active_limit", W.DWORD),
                ("affinity", C.c_size_t), ("priority", W.DWORD), ("scheduling", W.DWORD)]


class JobExtended(C.Structure):
    _fields_ = [("basic", JobBasic), ("io", C.c_uint64 * 6), ("process_memory", C.c_size_t),
                ("job_memory", C.c_size_t), ("peak_process", C.c_size_t), ("peak_job", C.c_size_t)]


class StartupInfo(C.Structure):
    _fields_ = [("size", W.DWORD), ("reserved", W.LPWSTR), ("desktop", W.LPWSTR),
                ("title", W.LPWSTR), ("x", W.DWORD), ("y", W.DWORD),
                ("width", W.DWORD), ("height", W.DWORD), ("chars_x", W.DWORD),
                ("chars_y", W.DWORD), ("fill", W.DWORD), ("flags", W.DWORD),
                ("show", W.WORD), ("reserved_size", W.WORD), ("reserved_data", C.c_void_p),
                ("stdin", W.HANDLE), ("stdout", W.HANDLE), ("stderr", W.HANDLE)]


class StartupInfoEx(C.Structure):
    _fields_ = [("info", StartupInfo), ("attributes", C.c_void_p)]


class ProcessInfo(C.Structure):
    _fields_ = [("process", W.HANDLE), ("thread", W.HANDLE), ("pid", W.DWORD), ("tid", W.DWORD)]


def _create_suspended(api: Any, executable: Path, arguments: list[str], cwd: Path,
                      handles: list[int], desktop: str | None, environment: dict[str, str],
                      debug: bool = True) -> ProcessInfo:
    """Use native lpDesktop; CPython's STARTUPINFO does not forward it."""
    startup = StartupInfoEx()
    startup.info.size = C.sizeof(startup)
    startup.info.desktop = desktop
    startup.info.flags = 0x100 | 0x1  # STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW
    startup.info.show = 4  # SW_SHOWNOACTIVATE, also isolated from the input desktop
    startup.info.stdin, startup.info.stdout, startup.info.stderr = handles
    size = C.c_size_t()
    api.InitializeProcThreadAttributeList(None, 1, 0, C.byref(size))
    if not size.value:
        raise C.WinError(C.get_last_error())
    storage = C.create_string_buffer(size.value)
    startup.attributes = C.cast(storage, C.c_void_p)
    if not api.InitializeProcThreadAttributeList(startup.attributes, 1, 0, C.byref(size)):
        raise C.WinError(C.get_last_error())
    try:
        inherited = list(dict.fromkeys(handles))
        values = (W.HANDLE * len(inherited))(*inherited)
        if not api.UpdateProcThreadAttribute(startup.attributes, 0, 0x20002, values,
                                             C.sizeof(values), None, None):
            raise C.WinError(C.get_last_error())
        info = ProcessInfo()
        command = C.create_unicode_buffer(subprocess.list2cmdline([str(executable), *arguments]))
        env = C.create_unicode_buffer("\0".join(f"{k}={v}" for k, v in sorted(environment.items())) + "\0\0")
        if not api.CreateProcessW(str(executable), command, None, None, True,
                                   (0x2 if debug else 0) | 0x4 | 0x08000000 | 0x80000 | 0x400, env, str(cwd),
                                   C.byref(startup), C.byref(info)):
            raise C.WinError(C.get_last_error())
        return info
    finally:
        api.DeleteProcThreadAttributeList(startup.attributes)


def kernel_api() -> Any:
    if os.name != "nt" or C.sizeof(C.c_void_p) != 8:
        raise RuntimeError("运行调试需要 Windows 64 位 Python。")
    api = C.WinDLL("kernel32", use_last_error=True)
    definitions = {
        "WaitForDebugEventEx": ([C.POINTER(DebugEvent), W.DWORD], W.BOOL),
        "ContinueDebugEvent": ([W.DWORD, W.DWORD, W.DWORD], W.BOOL),
        "ReadProcessMemory": ([W.HANDLE, C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_size_t)], W.BOOL),
        "CloseHandle": ([W.HANDLE], W.BOOL),
        "ResumeThread": ([W.HANDLE], W.DWORD),
        "CreateJobObjectW": ([C.c_void_p, W.LPCWSTR], W.HANDLE),
        "SetInformationJobObject": ([W.HANDLE, C.c_int, C.c_void_p, W.DWORD], W.BOOL),
        "AssignProcessToJobObject": ([W.HANDLE, W.HANDLE], W.BOOL),
        "TerminateJobObject": ([W.HANDLE, W.UINT], W.BOOL),
        "GetExitCodeProcess": ([W.HANDLE, C.POINTER(W.DWORD)], W.BOOL),
        "WaitForSingleObject": ([W.HANDLE, W.DWORD], W.DWORD),
        "InitializeProcThreadAttributeList": ([C.c_void_p, W.DWORD, W.DWORD, C.POINTER(C.c_size_t)], W.BOOL),
        "UpdateProcThreadAttribute": ([C.c_void_p, W.DWORD, C.c_size_t, C.c_void_p,
                                       C.c_size_t, C.c_void_p, C.c_void_p], W.BOOL),
        "DeleteProcThreadAttributeList": ([C.c_void_p], None),
        "CreateProcessW": ([W.LPCWSTR, W.LPWSTR, C.c_void_p, C.c_void_p, W.BOOL, W.DWORD,
                            C.c_void_p, W.LPCWSTR, C.POINTER(StartupInfoEx), C.POINTER(ProcessInfo)], W.BOOL),
    }
    for name, (args, result) in definitions.items():
        function = getattr(api, name)
        function.argtypes, function.restype = args, result
    return api


class DebugProcess:
    """CreateProcess and the entire debug loop must run on this same thread."""

    def __init__(self, executable: Path, arguments: list[str], cwd: Path, directory: Path,
                 desktop_name: str | None = None, test_token: str | None = None):
        self.api = kernel_api()
        self.process: Any = None
        self.job = None
        self.debug_handle = None
        self.started = time.monotonic()
        self.exit_code: int | None = None
        self.initial_breakpoint = False
        self.events: list[dict[str, Any]] = []
        self.exceptions: list[dict[str, Any]] = []
        self.messages: list[str] = []
        self.total_characters = 0
        self.truncated = False
        self.terminated = False
        self.cleanup_error: str | None = None
        self.streams = []
        self.directory = directory
        try:
            self.job = self.api.CreateJobObjectW(None, None)
            if not self.job:
                raise C.WinError(C.get_last_error())
            info = JobExtended()
            info.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not self.api.SetInformationJobObject(self.job, 9, C.byref(info), C.sizeof(info)):
                raise C.WinError(C.get_last_error())
            for name in ("stdout.bin", "stderr.bin"):
                self.streams.append((directory / name).open("wb"))
            import msvcrt
            with open(os.devnull, "rb") as input_stream:
                handles = [msvcrt.get_osfhandle(s.fileno()) for s in [input_stream, *self.streams]]
                try:
                    for handle in handles:
                        os.set_handle_inheritable(handle, True)
                    environment = {k: v for k, v in os.environ.items()
                                   if k.upper() not in {"CLI_ANYTHING_XCIDE_TEST_TOKEN", "CLI_ANYTHING_XCIDE_TEST_DIR"}}
                    if test_token:
                        environment.update(CLI_ANYTHING_XCIDE_TEST_TOKEN=test_token,
                                           CLI_ANYTHING_XCIDE_TEST_DIR=str(directory))
                    info = _create_suspended(self.api, executable, arguments, cwd, handles, desktop_name, environment)
                    process_handle, thread_handle, pid = info.process, info.thread, info.pid
                finally:
                    for handle in handles:
                        os.set_handle_inheritable(handle, False)
            self.process = _OwnedProcess(process_handle, pid)
            # Suspended creation prevents user code from spawning descendants
            # before it belongs to this command's kill-on-close job.
            try:
                if not self.api.AssignProcessToJobObject(self.job, process_handle):
                    raise C.WinError(C.get_last_error())
                if self.api.ResumeThread(thread_handle) == 0xFFFFFFFF:
                    raise C.WinError(C.get_last_error())
            finally:
                self.api.CloseHandle(thread_handle)
        except BaseException:
            if self.process is not None:
                self.process.kill()
            self.close()
            raise

    @property
    def pid(self) -> int:
        assert self.process is not None
        return self.process.pid

    def poll(self, milliseconds: int = 20) -> bool:
        if self.exit_code is not None:
            return False
        event = DebugEvent()
        if not self.api.WaitForDebugEventEx(C.byref(event), milliseconds):
            error = C.get_last_error()
            if error == 121:  # ERROR_SEM_TIMEOUT
                return False
            raise C.WinError(error)
        status = 0x00010002  # DBG_CONTINUE
        try:
            if event.pid != self.pid:
                raise RuntimeError("Unexpected debug event from an unowned process.")
            if event.code == 3:  # CREATE_PROCESS_DEBUG_EVENT
                self.debug_handle = event.data.create.process
                if event.data.create.file:
                    self.api.CloseHandle(event.data.create.file)
                # Debug-event thread/process handles are closed by Windows at
                # EXIT_THREAD/EXIT_PROCESS; only hFile is caller-owned.
            elif event.code == 6:  # LOAD_DLL_DEBUG_EVENT, first union member hFile
                if event.data.handle:
                    self.api.CloseHandle(event.data.handle)
            elif event.code == 8:
                info = event.data.string
                # OUTPUT_DEBUG_STRING_INFO.nDebugStringLength is bytes,
                # including the terminator (also for Unicode events).
                size = info.length
                data = C.create_string_buffer(size)
                read = C.c_size_t()
                if size and not self.api.ReadProcessMemory(self.debug_handle, info.address, data, size, C.byref(read)):
                    raise C.WinError(C.get_last_error())
                text = data.raw[:read.value].decode("utf-16-le" if info.unicode else "mbcs", errors="replace").split("\0", 1)[0]
                if self.total_characters + len(text) <= 2 * 1024 * 1024 and len(self.events) < 10000:
                    self.messages.append(text)
                    self.total_characters += len(text)
                    self.events.append({"time": round(time.monotonic() - self.started, 4),
                                        "channel": "OutputDebugString", "unicode": bool(info.unicode), "text": text})
                else:
                    self.truncated = True
            elif event.code == 1:
                info = event.data.exception
                # Only the first loader breakpoint is consumed. Application
                # exceptions, including later breakpoints, get normal SEH.
                loader = info.first and info.record.code in {0x80000003, 0x4000001F} and not self.initial_breakpoint
                if loader:
                    self.initial_breakpoint = True
                else:
                    status = 0x80010001  # DBG_EXCEPTION_NOT_HANDLED
                    if len(self.exceptions) < 10000:
                        self.exceptions.append({"code": f"0x{info.record.code:08x}",
                                                "address": f"0x{info.record.address or 0:x}",
                                                "first_chance": bool(info.first), "thread": event.tid})
                    else:
                        self.truncated = True
            elif event.code == 5:
                self.exit_code = int(event.data.exit_code)
        finally:
            if not self.api.ContinueDebugEvent(event.pid, event.tid, status):
                raise C.WinError(C.get_last_error())
        return True

    def check_stream_limit(self) -> None:
        if any((self.directory / name).stat().st_size > 16 * 1024 * 1024 for name in ("stdout.bin", "stderr.bin")):
            raise RuntimeError("程序 stdout/stderr 超过单通道 16 MiB 限制。")

    def close(self) -> None:
        # EXIT_PROCESS_DEBUG_EVENT (even after ContinueDebugEvent) can precede
        # the process handle becoming signaled. Share one bounded budget across
        # debug-event draining and the final OS teardown wait, including D2D.
        deadline = time.monotonic() + 10

        def failed(message: str) -> None:
            self.cleanup_error = f"{self.cleanup_error}; {message}" if self.cleanup_error else message

        if self.job and self.process and self.exit_code is None:
            self.terminated = True
            if not self.api.TerminateJobObject(self.job, 0xE0000001):
                failed(str(C.WinError(C.get_last_error())))
            try:
                while self.exit_code is None and time.monotonic() < deadline:
                    self.poll(50)
            except (OSError, RuntimeError) as exc:
                failed(str(exc))
            if self.exit_code is None:
                failed("Owned process debug exit was not observed before cleanup stopped.")
        if self.job:
            self.api.CloseHandle(self.job)
            self.job = None
        for stream in self.streams:
            stream.close()
        self.streams = []
        if self.process:
            try:
                self.process.wait(timeout=max(0.0, deadline - time.monotonic()))
            except (OSError, subprocess.TimeoutExpired) as exc:
                failed(str(exc))
            finally:
                self.process.close()


class _OwnedProcess:
    """Retain CreateProcess identity without closing its primary thread early."""
    def __init__(self, handle: int, pid: int):
        self._handle, self.pid = handle, pid

    def kill(self) -> None:
        import _winapi
        _winapi.TerminateProcess(self._handle, 0xE0000001)

    def wait(self, timeout: float) -> None:
        import _winapi
        result = _winapi.WaitForSingleObject(self._handle, int(timeout * 1000))
        if result == 258:  # WAIT_TIMEOUT; _winapi raises OSError on WAIT_FAILED.
            raise subprocess.TimeoutExpired(str(self.pid), timeout)
        if result != 0:
            raise OSError(f"Unexpected process wait result: {result}")

    def close(self) -> None:
        import _winapi
        if self._handle:
            _winapi.CloseHandle(self._handle)
            self._handle = None


class BackgroundProcess:
    """Owned non-debug process tree for the IDE, on a private desktop."""
    def __init__(self, command: list[str], cwd: Path, environment: dict[str, str], desktop: str):
        import msvcrt
        self.api = kernel_api()
        self.process = None
        self.job = self.api.CreateJobObjectW(None, None)
        self.returncode = None
        if not self.job:
            raise C.WinError(C.get_last_error())
        try:
            info = JobExtended()
            info.basic.flags = 0x2000
            if not self.api.SetInformationJobObject(self.job, 9, C.byref(info), C.sizeof(info)):
                raise C.WinError(C.get_last_error())
            with open(os.devnull, "rb") as stdin, open(os.devnull, "wb") as stdout:
                handles = [msvcrt.get_osfhandle(f.fileno()) for f in (stdin, stdout)]
                try:
                    for handle in handles:
                        os.set_handle_inheritable(handle, True)
                    native = _create_suspended(self.api, Path(command[0]), command[1:], cwd,
                                               [handles[0], handles[1], handles[1]], desktop, environment, debug=False)
                finally:
                    for handle in handles:
                        os.set_handle_inheritable(handle, False)
            self.pid = native.pid
            self.process = _OwnedProcess(native.process, native.pid)
            try:
                if not self.api.AssignProcessToJobObject(self.job, native.process):
                    raise C.WinError(C.get_last_error())
                if self.api.ResumeThread(native.thread) == 0xFFFFFFFF:
                    raise C.WinError(C.get_last_error())
            finally:
                self.api.CloseHandle(native.thread)
        except BaseException:
            if self.process:
                self.process.kill()
            self.close()
            raise

    def poll(self) -> int | None:
        if self.returncode is not None:
            return self.returncode
        if self.api.WaitForSingleObject(self.process._handle, 0) == 0:
            code = W.DWORD()
            if not self.api.GetExitCodeProcess(self.process._handle, C.byref(code)):
                raise C.WinError(C.get_last_error())
            self.returncode = code.value
        return self.returncode

    def terminate_tree(self) -> None:
        if self.job and not self.api.TerminateJobObject(self.job, 0xE0000001):
            raise C.WinError(C.get_last_error())
        if self.process:
            self.process.wait(5)
            self.poll()

    def close(self) -> None:
        if self.job:
            self.api.CloseHandle(self.job)
            self.job = None
        if self.process:
            self.process.close()
