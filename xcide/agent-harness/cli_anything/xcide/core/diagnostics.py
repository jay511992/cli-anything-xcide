"""Read private IDE output snapshots and interpret native compiler messages."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from cli_anything.xcide.utils.native_build import compile_native


def prepare_bridge(base: Path, architecture: str) -> Path:
    source = Path(__file__).resolve().parents[1] / "native/output_bridge.cpp"
    output = base / "data/plug/plug_cli_output.dll"
    compile_native(source, output, dll=True, architecture=architecture)
    return base / "compiler-output.json"


def read_snapshot(path: Path, pid: int, project: Path) -> dict[str, Any] | None:
    try:
        if path.stat().st_size > 16 * 1024 * 1024:
            raise RuntimeError("IDE output snapshot exceeded 16 MiB.")
        snapshot = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, PermissionError, json.JSONDecodeError):
        return None  # Atomic replacement can briefly race a Windows reader.
    if not isinstance(snapshot, dict):
        raise RuntimeError("Invalid IDE output snapshot object.")
    if (snapshot.get("pid") != pid or snapshot.get("version") != 3
            or not snapshot.get("ready") or not snapshot.get("project")):
        return None
    if snapshot.get("truncated"):
        raise RuntimeError("IDE output exceeded the 2 Mi-character bridge limit.")
    if not isinstance(snapshot.get("text"), str) or not isinstance(snapshot.get("project"), str):
        raise RuntimeError("Invalid IDE output snapshot fields.")
    if Path(snapshot["project"]).resolve() != project:
        raise RuntimeError("Output bridge is reporting a different project.")
    return snapshot


def parse_output(text: str) -> dict[str, Any]:
    """Keep raw output; only explicit summaries can establish zero errors."""
    entries: list[dict[str, Any]] = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        native = re.search(r"(解析|检查)错误:\s*(.+?)\((\d+)\),\s*列\((\d+)-(\d+)\)", line)
        if native:
            kind, file, row, col1, col2 = native.groups()
            entries.append({"kind": "parse" if kind == "解析" else "check", "severity": "error",
                            "file": file, "line": int(row), "column": int(col1), "end_column": int(col2),
                            "message": lines[i + 1].strip() if i + 1 < len(lines) else line})
            continue
        cpp = re.search(r"^\s*(.*?)\s*:\s*(fatal error|error|warning|致命错误|错误|警告)\s+([A-Z]+\d+)\s*:\s*(.*)$", line)
        if cpp:
            location, severity, code, message = cpp.groups()
            position = re.match(r"^(.*?)\((\d+)(?:,(\d+))?\)$", location)
            entries.append({"kind": "native", "severity": "warning" if severity in {"warning", "警告"} else "error",
                            "file": position[1] if position else location,
                            "line": int(position[2]) if position else None, "code": code, "message": message})
        elif "⚠" in line:
            entries.append({"kind": "ide", "severity": "warning", "message": line.strip()})
    totals = re.findall(r"错误列表:\s*(?:共有\((\d+)\)个错误|错误\((\d+)\))", text)
    reported = int(totals[-1][0] or totals[-1][1]) if totals else None
    errors = sum(item["severity"] == "error" for item in entries)
    failure = re.search(r"编译失败.*?错误码:\s*(-?\d+)", text)
    failed = bool(failure or "编译失败" in text or errors or (reported is not None and reported > 0))
    compiled = bool(re.search(r"编译完成,\s*耗时", text))
    skipped = "跳过编译" in text
    count = max(reported or 0, errors) if reported is not None or errors else None
    return {"compiled": compiled, "skipped": skipped, "failed": failed,
            "errorCount": count, "warningCount": sum(e["severity"] == "warning" for e in entries),
            "reportedTotal": reported, "failCode": int(failure[1]) if failure else None,
            "diagnostics_available": True, "diagnostics": entries,
            "ok": compiled and not failed and not skipped and count == 0,
            "terminal": compiled or failed or skipped, "output": text}
