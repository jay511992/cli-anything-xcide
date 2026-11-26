"""本地源码读写与工程目录访问控制。"""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Any

from cli_anything.xcide.core.project import ProjectError, inspect_project, resolve_ide_root


class FileOperationError(RuntimeError):
    """本地工程文件操作失败。"""


def _within(path: Path, root: Path) -> bool:
    try:
        common = os.path.commonpath((str(path), str(root)))
        return os.path.normcase(common) == os.path.normcase(str(root))
    except ValueError:
        return False


def validate_path(
    path: str | os.PathLike[str],
    *,
    project: str | os.PathLike[str] | None = None,
    ide_root: str | os.PathLike[str] | None = None,
    allow_outside: bool = False,
) -> Path:
    """将文件限制在选定工程、IDE 安装和模块库中。"""
    resolved = Path(path).expanduser().resolve()
    if allow_outside:
        return resolved
    roots: list[Path] = []
    if project:
        project_info = inspect_project(project)
        roots.append(Path(project_info["directory"]).resolve())
    try:
        install = resolve_ide_root(ide_root)
    except ProjectError:
        install = None
    if install:
        roots.extend((install, install / "data" / "XC-Module", install / "data" / "XC-Module-dev"))
    if any(_within(resolved, root.resolve()) for root in roots):
        return resolved
    raise FileOperationError(
        "路径位于当前工程和 IDE 安装目录之外；请检查 --project/--ide，"
        "或明确使用 --allow-outside-project 访问其他本地文件。"
    )


def _decode(raw: bytes) -> tuple[str, str, bool, bool]:
    """识别常见源码编码、BOM 和换行格式。"""
    bom = raw.startswith(b"\xef\xbb\xbf")
    if bom:
        text = raw[3:].decode("utf-8")
        encoding = "utf-8"
    elif raw.startswith(b"\xff\xfe"):
        text = raw.decode("utf-16")
        encoding = "utf-16-le"
        bom = True
    elif raw.startswith(b"\xfe\xff"):
        text = raw.decode("utf-16")
        encoding = "utf-16-be"
        bom = True
    else:
        try:
            text = raw.decode("utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            text = raw.decode("gb18030")
            encoding = "gb18030"
    crlf = "\r\n" in text
    return text, encoding, bom, crlf


def read_file(
    path: str | os.PathLike[str],
    *,
    project: str | os.PathLike[str] | None = None,
    ide_root: str | os.PathLike[str] | None = None,
    allow_outside: bool = False,
) -> dict[str, Any]:
    """在本机直接读取文本文件并返回原始格式信息。"""
    target = validate_path(path, project=project, ide_root=ide_root, allow_outside=allow_outside)
    if not target.is_file():
        raise FileOperationError(f"文本文件不存在：{target}")
    raw = target.read_bytes()
    text, encoding, bom, crlf = _decode(raw)
    if "\x00" in text:
        raise FileOperationError(f"拒绝把二进制文件作为文本读取：{target}")
    return {"path": str(target), "content": text, "encoding": encoding,
            "bom": bom, "crlf": crlf, "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def write_file(
    path: str | os.PathLike[str],
    text: str,
    *,
    project: str | os.PathLike[str] | None = None,
    ide_root: str | os.PathLike[str] | None = None,
    allow_outside: bool = False,
    no_bom: bool = False,
    force_bom: bool = False,
) -> dict[str, Any]:
    """本地写入 UTF 文本，默认保留既有编码、BOM 与换行格式。"""
    target = validate_path(path, project=project, ide_root=ide_root, allow_outside=allow_outside)
    if not target.parent.is_dir():
        raise FileOperationError(f"目标目录不存在：{target.parent}")
    existed = target.is_file()
    if existed:
        _old_text, encoding, bom, crlf = _decode(target.read_bytes())
    else:
        source_ext = target.suffix.lower() in {".xc", ".xh", ".xcs", ".h", ".hpp", ".cpp", ".cc"}
        encoding, bom, crlf = "utf-8", source_ext and not no_bom, source_ext
    if no_bom:
        encoding, bom = "utf-8", False
    if force_bom:
        if no_bom:
            raise FileOperationError("不能同时要求添加和移除 BOM。")
        if encoding not in {"utf-16-le", "utf-16-be"}:
            encoding = "utf-8"
        bom = True
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if crlf:
        normalized = normalized.replace("\n", "\r\n")
    codec = {"utf-16-le": "utf-16-le", "utf-16-be": "utf-16-be"}.get(encoding, encoding)
    raw = normalized.encode(codec)
    if encoding == "utf-8" and bom:
        raw = b"\xef\xbb\xbf" + raw
    elif encoding == "utf-16-le" and bom:
        raw = b"\xff\xfe" + raw
    elif encoding == "utf-16-be" and bom:
        raw = b"\xfe\xff" + raw
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.cli-anything-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        if existed:
            try:
                os.chmod(temporary, target.stat().st_mode)
            except OSError:
                pass
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    verified = target.read_bytes()
    if verified != raw:
        raise FileOperationError(f"本地写入后的回读验证失败：{target}")
    return {"path": str(target), "bytes": len(raw), "encoding": encoding,
            "bom": bom, "crlf": crlf, "sha256": hashlib.sha256(raw).hexdigest(),
            "created": not existed, "verified": True}
