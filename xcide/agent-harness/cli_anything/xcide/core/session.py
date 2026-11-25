"""Locked, durable IDE-target sessions with undo, redo, and mutation history."""

from __future__ import annotations

import copy
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from filelock import FileLock


def default_session_path() -> Path:
    """Return a session location that does not depend on the current directory."""
    root = os.environ.get("CLI_ANYTHING_XCIDE_HOME")
    if root:
        return Path(root).expanduser() / "session.json"
    local = os.environ.get("LOCALAPPDATA")
    return (Path(local) if local else Path.home()) / ".cli-anything" / "xcide" / "session.json"


class Session:
    """持久保存本地 CLI 所选工程和 IDE 安装位置，支持撤销与重做。"""

    VERSION = 1
    MAX_HISTORY = 50
    MAX_REDO = 20

    def __init__(self, path: str | os.PathLike[str] | None = None) -> None:
        self.path = Path(path).expanduser().resolve() if path else default_session_path().resolve()
        self.modified = False
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8")) if self.path.is_file() else {}
        except (OSError, ValueError):
            raw = {}
        self.state = raw if isinstance(raw, dict) and raw.get("schema_version") == self.VERSION else self._empty()
        self.state.setdefault("project", None)
        self.state.setdefault("ide_root", None)
        for obsolete in ("instance", "url", "instance_dir"):
            self.state.pop(obsolete, None)
        self.state.setdefault("history", [])
        self.state.setdefault("audit", [])
        try:
            self.revision = max(0, int(self.state.get("revision", 0)))
        except (TypeError, ValueError):
            self.revision = 0
        self._undo: list[dict[str, Any] | None] = [entry for entry in self.state.get("undo", [])
                                                     if entry is None or isinstance(entry, dict)]
        self._redo: list[dict[str, Any] | None] = [entry for entry in self.state.get("redo", [])
                                                     if entry is None or isinstance(entry, dict)]
        if self._undo:
            self._undo = self._undo[-self.MAX_REDO:]
        if self._redo:
            self._redo = self._redo[-self.MAX_REDO:]

    @staticmethod
    def _empty() -> dict[str, Any]:
        return {"schema_version": Session.VERSION, "revision": 0, "project": None, "ide_root": None,
                "history": [], "audit": [], "undo": [], "redo": []}

    @property
    def project(self) -> str | None:
        return self.state.get("project")

    def _snapshot(self) -> dict[str, Any]:
        return {key: copy.deepcopy(self.state.get(key)) for key in ("project", "ide_root")}

    def select(
        self,
        *,
        project: str | os.PathLike[str] | None = None,
        ide_root: str | os.PathLike[str] | None = None,
        action: str = "select",
    ) -> None:
        """Select or clear a project target and retain a reversible audit entry."""
        before = self._snapshot()
        new = {
            "project": str(Path(project).expanduser().resolve()) if project else before["project"],
            "ide_root": str(Path(ide_root).expanduser().resolve()) if ide_root else before["ide_root"],
        }
        if not any(new.values()):
            raise ValueError("Select a project with --project before updating the IDE session.")
        if new == before:
            return
        self._undo.append(before)
        self._undo = self._undo[-self.MAX_REDO:]
        self._redo.clear()
        self.state["undo"] = copy.deepcopy(self._undo)
        self.state["redo"] = []
        self.state.update(new)
        entry = {"action": action, "at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), **new}
        entry["revision"] = self.revision + 1
        self.state["history"] = (self.state.get("history", []) + [entry])[-self.MAX_HISTORY:]
        entry["revision"] = self.revision + 1
        self.state["audit"] = (self.state.get("audit", []) + [entry])[-self.MAX_HISTORY:]
        self.modified = True

    def undo(self) -> dict[str, Any]:
        if not self._undo:
            raise ValueError("There is no IDE target selection to undo.")
        self._redo.append(self._snapshot())
        target = self._undo.pop()
        if target is not None:
            self.state.update(target)
        self.modified = True
        self.state["undo"] = copy.deepcopy(self._undo)
        self.state["redo"] = copy.deepcopy(self._redo)
        return self.summary()

    def redo(self) -> dict[str, Any]:
        if not self._redo:
            raise ValueError("There is no IDE target selection to redo.")
        self._undo.append(self._snapshot())
        self.state.update(self._redo.pop())
        self.modified = True
        self.state["undo"] = copy.deepcopy(self._undo)
        self.state["redo"] = copy.deepcopy(self._redo)
        return self.summary()

    def summary(self) -> dict[str, Any]:
        return {**self._snapshot(), "history_count": len(self.state.get("history", [])),
                "undo_available": bool(self._undo), "redo_available": bool(self._redo),
                "session_file": str(self.path)}

    def history(self, limit: int = 20) -> list[dict[str, Any]]:
        if not 1 <= limit <= self.MAX_HISTORY:
            raise ValueError(f"History limit must be between 1 and {self.MAX_HISTORY}.")
        return list(self.state.get("history", []))[-limit:]

    def record_action(self, action: str, **details: Any) -> None:
        """Record a successfully completed, file-backed native IDE operation."""
        entry = {"action": action, "at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), **details}
        entry["revision"] = self.revision + 1
        self.state["audit"] = (self.state.get("audit", []) + [entry])[-self.MAX_HISTORY:]
        self.modified = True

    def save(self) -> None:
        """Serialize under a cross-process lock and atomically replace the JSON file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(str(self.path) + ".lock", timeout=15):
            existing: dict[str, Any] = {}
            try:
                if self.path.is_file():
                    parsed = json.loads(self.path.read_text(encoding="utf-8"))
                    if isinstance(parsed, dict) and parsed.get("schema_version") == self.VERSION:
                        existing = parsed
            except (OSError, ValueError):
                pass
            try:
                existing_revision = max(0, int(existing.get("revision", 0)))
            except (TypeError, ValueError):
                existing_revision = 0
            if existing_revision != self.revision:
                raise RuntimeError(
                    f"The XCIDE session changed concurrently (revision {self.revision} → {existing_revision}); "
                    "reload the session and retry your update."
                )
            merged = {**existing, **self.state}
            next_revision = existing_revision + 1
            for collection in ("history", "audit"):
                existing_entries = [entry for entry in existing.get(collection, [])
                                    if not isinstance(entry, dict) or entry.get("revision") != next_revision]
                additions = [entry for entry in self.state.get(collection, [])
                             if not isinstance(entry, dict) or entry.get("revision") is None
                             or entry.get("revision") == next_revision]
                merged[collection] = (existing_entries + additions)[-self.MAX_HISTORY:]
            merged["revision"] = next_revision
            fd, temp_name = tempfile.mkstemp(prefix=".xcide-session-", suffix=".json", dir=self.path.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                    json.dump(merged, handle, ensure_ascii=False, indent=2)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, self.path)
            except BaseException:
                try:
                    os.unlink(temp_name)
                except FileNotFoundError:
                    pass
                raise
        self.revision = next_revision
        self.state = merged
        self.modified = False
