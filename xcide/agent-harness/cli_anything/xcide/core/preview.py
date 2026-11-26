"""基于本地 .xcproj 与 EXE 产物发布真实检查预览包。"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cli_anything.xcide.core.build import inspect_pe
from cli_anything.xcide.core.project import inspect_project
from cli_anything.xcide.utils.preview_bundle import (
    PROTOCOL_VERSION,
    artifact_record,
    build_cache_key,
    finalize_bundle,
    find_cached_manifest,
    find_latest_manifest,
    fingerprint_data,
    prepare_bundle,
    write_json,
)


RECIPES: dict[str, dict[str, str]] = {
    "project": {"description": "本地工程 XML、入口源码与模块引用状态。", "kind": "capture"},
    "executable": {"description": "检查工程中新生成的 Windows PE 架构、大小与 SHA-256。", "kind": "capture"},
}


def recipe_names() -> list[dict[str, str]]:
    return [{"recipe": name, **metadata} for name, metadata in RECIPES.items()]


def _read_executable(project: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    directory = Path(project["directory"])
    candidates = [candidate for candidate in directory.rglob("*.exe")
                  if candidate.is_file() and "obj" not in candidate.parts
                  and ".cli-anything" not in candidate.parts]
    if len(candidates) == 1:
        return inspect_pe(candidates[0]), {"candidate_count": 1}
    if not candidates:
        return None, {"candidate_count": 0, "reason": "尚未发现工程可执行文件。"}
    candidates.sort(key=lambda candidate: candidate.stat().st_mtime_ns, reverse=True)
    return None, {"candidate_count": len(candidates), "newest_candidates": [str(path) for path in candidates[:8]],
                  "reason": "工程中存在多个 EXE，无法安全判断目标产物。"}


def capture(
    *,
    recipe: str,
    project_path: str,
    ide_root: str | None = None,
    root_dir: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """读取本地工程并发布缓存可用的不可变预览包。"""
    if recipe not in RECIPES:
        raise ValueError(f"不支持的 XCIDE 预览配方 {recipe!r}，请选择 {', '.join(RECIPES)}。")
    local = inspect_project(project_path)
    project_file = Path(local["project_file"])
    manifest_bytes = project_file.read_bytes()
    source_fingerprint = {"project_sha256": hashlib.sha256(manifest_bytes).hexdigest(), "recipe": recipe,
                          "project_path": os.path.normcase(str(project_file.resolve())),
                          "entrypoints": local["entrypoints"]}
    binary, binary_info = _read_executable(local) if recipe == "executable" else (None, {})
    if binary:
        source_fingerprint["executable_sha256"] = binary["sha256"]
    fingerprint = fingerprint_data(source_fingerprint)
    options = {"recipe": recipe, "source_file_fingerprint": fingerprint, "scope": "local project files"}
    cache_key = build_cache_key("xcide", recipe, "capture", fingerprint, options, "1.0.0", PROTOCOL_VERSION)
    if not force:
        cached = find_cached_manifest("xcide", recipe, "capture", cache_key,
                                      project_path=local["project_file"], root_dir=root_dir)
        if cached:
            return {"ok": True, "cached": True, **cached}

    data: dict[str, Any] = {
        "captured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "recipe": recipe,
        "backend": "本地文件系统，无 MCP",
        "project": {key: local[key] for key in
                    ("name", "project_file", "configuration", "platform", "platform_toolset", "sdk", "modules", "files", "entrypoints")},
    }
    if recipe == "executable":
        data["executable"] = binary
        data["executable_info"] = binary_info
    bundle = prepare_bundle("xcide", recipe, "capture", fingerprint, options, "1.0.0",
                            project_path=local["project_file"], root_dir=root_dir, force=force)
    artifact_path = str(Path(bundle["artifacts_dir"]) / "ide-state.json")
    write_json(artifact_path, data)
    facts = {"project": local["name"], "configuration": local["configuration"],
             "platform": local["platform"], "recipe": recipe}
    if binary:
        facts["executable_architecture"] = binary["architecture"]
        facts["executable_bytes"] = binary["bytes"]
    partial = recipe == "executable" and binary is None
    warnings = [binary_info["reason"]] if partial else []
    artifact = artifact_record(bundle["bundle_dir"], artifact_path, "native-project-state", "inspection",
                               "json", f"XCIDE 本地 {recipe} 检查数据", "application/json")
    manifest = finalize_bundle(
        bundle_dir=bundle["bundle_dir"], bundle_id=bundle["bundle_id"], bundle_kind="capture",
        software="xcide", recipe=recipe,
        source={"project_path": local["project_file"], "project_fingerprint": fingerprint},
        artifacts=[artifact],
        summary={"headline": f"已从本地文件读取 XCIDE {recipe} 检查数据。", "facts": facts,
                 "warnings": warnings,
                 "next_actions": (["运行 build 后再检查 EXE。"] if partial else
                                  ["在 artifacts/ide-state.json 查看完整检查数据。"])},
        cache_key=cache_key,
        generator={"entry_point": "cli-anything-xcide", "harness_version": "1.0.0",
                   "backend": "local filesystem"},
        status="partial" if partial else "ok", warnings=warnings,
        context={"capture_method": "直接读取 .xcproj 和磁盘产物，不连接 IDE；无 GUI 截图",
                 "reads_ide_output": False, "compiles_project": False},
        metrics={"artifact_count": 1}, labels=["native-state", recipe],
    )
    return {"ok": True, "cached": False, **manifest}


def latest(*, recipe: str | None, project_path: str, root_dir: str | None = None) -> dict[str, Any]:
    inspect_project(project_path)
    manifest = find_latest_manifest("xcide", recipe=recipe, bundle_kind="capture",
                                    project_path=project_path, root_dir=root_dir)
    if not manifest:
        raise FileNotFoundError(f"本地工程 {project_path} 没有配方 {recipe or '*'} 的 XCIDE 预览包。")
    return {"ok": True, **manifest}
