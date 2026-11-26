"""Bounded inspection and single-member export of local native UI ZIP files."""

from __future__ import annotations

import hashlib
import json
import lzma
import os
import re
import stat
import tempfile
import zipfile
import zlib
from collections import Counter
from io import BytesIO
from pathlib import Path
from typing import Any

from cli_anything.xcide.core.files import _decode, validate_path
from cli_anything.xcide.core.project import ProjectError, resolve_ide_root


MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_MEMBER_BYTES = 8 * 1024 * 1024
MAX_ENTRIES = 10000


class ArchiveError(ValueError):
    """A ZIP or selected member cannot be handled without ambiguity."""


def page(items: list[dict], *, query: str = "", limit: int = 100, offset: int = 0) -> dict[str, Any]:
    if not 1 <= limit <= 2000 or offset < 0:
        raise ValueError("limit 必须为 1..2000，offset 不能为负数。")
    needle = query.strip().casefold()
    matches = [item for item in items if not needle or needle in json.dumps(item, ensure_ascii=False).casefold()]
    selected = matches[offset:offset + limit]
    following = offset + len(selected)
    return {"items": selected, "query": query, "count": len(selected), "total": len(matches),
            "offset": offset, "next_offset": following if following < len(matches) else None,
            "truncated": following < len(matches)}


def bounded_file(path, *, project=None, ide_root=None, limit=MAX_ARCHIVE_BYTES) -> tuple[bytes, dict]:
    target = validate_path(path, project=project, ide_root=ide_root)
    with target.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ArchiveError(f"文件超过 {limit} 字节读取上限：{target}")
    return raw, {"path": str(target), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def path_issues(name: str) -> list[str]:
    normalized = name.replace("\\", "/").rstrip("/")
    parts = normalized.split("/")
    problems = []
    if not normalized or normalized.startswith("/") or any(p in {"", ".", ".."} for p in parts):
        problems.append("unsafe-path")
    if re.search(r'[<>:"|?*\x00-\x1f]', normalized):
        problems.append("invalid-windows-path")
    if any(p.endswith((" ", ".")) or re.fullmatch(r"(?i)(?:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?", p)
           for p in parts):
        problems.append("reserved-windows-path")
    return problems


def _index(bundle: zipfile.ZipFile) -> list[dict]:
    infos = bundle.infolist()
    if len(infos) > MAX_ENTRIES:
        raise ArchiveError(f"归档条目数超过 {MAX_ENTRIES} 上限。")
    keys = [i.filename.replace("\\", "/").rstrip("/").casefold() for i in infos]
    counts = Counter(keys)
    records = []
    for info, key in zip(infos, keys):
        problems = path_issues(info.orig_filename)
        if "\x00" in info.orig_filename:
            problems.append("truncated-name")
        if counts[key] > 1:
            problems.append("ambiguous-name")
        if stat.S_ISLNK(info.external_attr >> 16):
            problems.append("symlink")
        if info.flag_bits & 1:
            problems.append("encrypted")
        if info.file_size > MAX_MEMBER_BYTES:
            problems.append("member-too-large")
        directory = info.is_dir() or info.filename.endswith("\\")
        records.append({"id": info.filename.replace("\\", "/"), "original_name": info.orig_filename,
                        "normalized_path": info.filename.replace("\\", "/"),
                        "bytes": info.file_size, "compressed_bytes": info.compress_size,
                        "crc32": f"{info.CRC:08x}", "compression": info.compress_type,
                        "directory": directory, "problems": problems,
                        "readable": not directory and not problems, "crc_verified": False})
    return records


def _open(path, *, project=None, ide_root=None):
    raw, source = bounded_file(path, project=project, ide_root=ide_root, limit=MAX_ARCHIVE_BYTES)
    try:
        bundle = zipfile.ZipFile(BytesIO(raw))
    except (zipfile.BadZipFile, OSError) as exc:
        raise ArchiveError(f"无法读取 ZIP：{exc}") from exc
    return bundle, source


def list_archive(path, *, project=None, ide_root=None, query="", limit=100, offset=0) -> dict:
    bundle, source = _open(path, project=project, ide_root=ide_root)
    with bundle:
        records = _index(bundle)
    return {"ok": True, "source": source, "entry_count": len(records),
            "problem_count": sum(bool(r["problems"]) for r in records),
            "crc_verified": False, **page(records, query=query, limit=limit, offset=offset)}


def member_bytes(path, member: str, *, project=None, ide_root=None) -> tuple[bytes, dict]:
    bundle, source = _open(path, project=project, ide_root=ide_root)
    with bundle:
        records = _index(bundle)
        matches = [(i, item) for i, item in zip(bundle.infolist(), records) if item["id"] == member]
        if len(matches) != 1:
            raise ArchiveError(f"ZIP 成员不存在或不唯一，请使用 list 返回的准确 ID：{member}")
        info, item = matches[0]
        if not item["readable"]:
            raise ArchiveError(f"ZIP 成员不能读取：{member}，问题：{item['problems'] or ['directory']}")
        raw = _read_member(bundle, info)
    return raw, {"archive": source, "member": member, "original_name": info.orig_filename, "bytes": len(raw),
                 "sha256": hashlib.sha256(raw).hexdigest(), "crc_verified": True}


def _read_member(bundle: zipfile.ZipFile, info: zipfile.ZipInfo) -> bytes:
    """Bound decompression and verify CRC using the original member identity."""
    if info.file_size > MAX_MEMBER_BYTES:
        raise ArchiveError(f"ZIP 成员超过 {MAX_MEMBER_BYTES} 字节读取上限：{info.filename}")
    try:
        with bundle.open(info) as stream:
            raw = stream.read(MAX_MEMBER_BYTES + 1)
            if len(raw) > MAX_MEMBER_BYTES or len(raw) != info.file_size:
                raise ArchiveError(f"ZIP 成员解压大小异常：{info.filename}")
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, OSError, EOFError, zlib.error, lzma.LZMAError) as exc:
        raise ArchiveError(f"无法解压或校验 ZIP 成员 {info.filename}：{exc}") from exc
    return raw


def text_content(raw: bytes) -> dict:
    try:
        text, encoding, bom, crlf = _decode(raw)
    except UnicodeError as exc:
        raise ArchiveError(f"文件不是可解码文本：{exc}") from exc
    if any(ord(c) < 32 and c not in "\t\r\n" for c in text):
        raise ArchiveError("拒绝将含二进制控制字符的成员作为文本读取；可使用 export 原样导出。")
    return {"content": text, "encoding": encoding, "bom": bom, "crlf": crlf}


def read_member(path, member: str, *, project=None, ide_root=None) -> dict:
    raw, source = member_bytes(path, member, project=project, ide_root=ide_root)
    return {"ok": True, "source": source, **text_content(raw)}


def export_member(path, member: str, output, *, project=None, ide_root=None, dry_run=False) -> dict:
    raw, source = member_bytes(path, member, project=project, ide_root=ide_root)
    requested = Path(output).expanduser().absolute()
    target = requested.resolve()
    try:
        install = resolve_ide_root(ide_root)
    except ProjectError:
        install = None
    if install is not None and target.is_relative_to(install):
        raise ArchiveError("导出目标不能位于正式 IDE 安装目录中。")
    if requested.is_symlink() or os.path.lexists(requested) or target.exists():
        raise ArchiveError(f"导出目标已经存在，拒绝覆盖：{requested}")
    if not target.parent.is_dir():
        raise ArchiveError(f"导出目录不存在：{target.parent}")
    result = {"ok": True, "source": source, "destination": str(target), "bytes": len(raw),
              "sha256": source["sha256"], "dry_run": dry_run, "created": False}
    if dry_run:
        return result
    descriptor, temporary = tempfile.mkstemp(prefix=".xcide-export-", dir=target.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if Path(temporary).read_bytes() != raw:
            raise ArchiveError("导出暂存文件回读不一致，已取消发布。")
        # Publish a complete file without replacing a target created by another
        # process after validation. Both paths are on the same filesystem.
        os.link(temporary, target)
    finally:
        try:
            Path(temporary).unlink(missing_ok=True)
        except OSError as exc:
            result["cleanup_warning"] = str(exc)
    return {**result, "created": True, "verified": True}
