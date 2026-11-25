"""Compile small local helpers with the installed MSVC toolchain."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def msvc_environment(architecture: str = "x64") -> dict[str, str]:
    if os.name != "nt" or architecture not in {"x64", "x86"}:
        raise RuntimeError("Native helpers require Windows MSVC (x64 or x86).")
    candidates: list[Path] = []
    current = shutil.which("cl.exe")
    if current:
        candidates.extend(p / "Auxiliary/Build/vcvarsall.bat" for p in Path(current).parents)
    vswhere = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Microsoft Visual Studio/Installer/vswhere.exe"
    if vswhere.is_file():
        result = subprocess.run([str(vswhere), "-latest", "-products", "*", "-requires",
                                 "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"],
                                capture_output=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
        installation = result.stdout.decode("utf-8-sig", errors="replace").strip()
        if installation:
            candidates.append(Path(installation) / "VC/Auxiliary/Build/vcvarsall.bat")
    batch = next((p.resolve() for p in candidates if p.is_file()), None)
    if batch is None:
        raise RuntimeError("找不到 MSVC vcvarsall.bat；请安装 Visual Studio C++ 桌面工具。")
    if any(char in str(batch) for char in '\"%\r\n'):
        raise RuntimeError("Unsupported characters in MSVC installation path.")
    # Only this discovered toolchain batch is interpreted by cmd, never user
    # program arguments or output paths. All compiler inputs use an argv list.
    result = subprocess.run(f'cmd.exe /d /u /s /c ""{batch}" {architecture} >nul && set"',
                            capture_output=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError("初始化 MSVC 环境失败：" + result.stderr.decode("mbcs", errors="replace"))
    env = {key.upper(): value for key, value in os.environ.items()}
    for line in result.stdout.decode("utf-16-le", errors="replace").splitlines():
        key, sep, value = line.partition("=")
        if sep and key:
            env[key.upper()] = value
    if not shutil.which("cl.exe", path=env.get("PATH")):
        raise RuntimeError("MSVC environment has no cl.exe.")
    return env


def compile_native(source: Path, output: Path, *, dll: bool = False, architecture: str = "x64") -> None:
    env = msvc_environment(architecture)
    compiler = shutil.which("cl.exe", path=env.get("PATH"))
    arguments = [str(compiler), "/nologo", "/utf-8", "/EHsc", "/MT", "/O2", str(source),
                 f"/Fo{output.with_suffix('.obj')}", f"/Fe{output}"]
    if dll:
        arguments.append("/LD")
    arguments += ["/link", "user32.lib", f"/IMPLIB:{output.with_suffix('.lib')}"]
    result = subprocess.run(arguments, cwd=output.parent, env=env, capture_output=True, timeout=90,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode or not output.is_file():
        raw = result.stdout + result.stderr
        try:
            diagnostic = raw.decode("utf-8")
        except UnicodeDecodeError:
            diagnostic = raw.decode("mbcs", errors="replace")
        raise RuntimeError("Native helper compilation failed: " +
                           diagnostic[-6000:])
