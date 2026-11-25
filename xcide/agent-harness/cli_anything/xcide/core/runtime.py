"""Launch, observe, exercise and reap only the executable selected for this run."""
from __future__ import annotations

import json
import math
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cli_anything.xcide.core.build import inspect_pe
from cli_anything.xcide.utils.win_debug import DebugProcess
from cli_anything.xcide.utils.win_desktop import Desktop, PrivateDesktop, KEYS


def load_scenario(path: Path) -> dict[str, Any]:
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("场景文件不能超过 1 MiB。")
    return validate_scenario(json.loads(path.read_text(encoding="utf-8-sig")))


def validate_scenario(value: Any) -> dict[str, Any]:
    if (not isinstance(value, dict) or set(value) - {"version", "steps", "expected_exit_code"}
            or type(value.get("version")) is not int or value["version"] != 1):
        raise ValueError("场景必须是 version=1 的 JSON 对象，只接受 steps、expected_exit_code。")
    code = value.get("expected_exit_code", 0)
    if type(code) is not int or not 0 <= code <= 0xFFFFFFFF:
        raise ValueError("expected_exit_code 必须是无符号 32 位整数。")
    steps = value.get("steps")
    if not isinstance(steps, list) or not 1 <= len(steps) <= 200:
        raise ValueError("场景必须包含 1–200 个步骤。")
    schemas = {"wait_window": {"title_contains"}, "click": {"x", "y"}, "text": {"text"},
               "key": {"key"}, "wait": {"seconds"}, "assert_debug": {"contains", "after_action"},
               "assert_title": {"contains"}, "screenshot": {"name"}, "close": set(), "wait_exit": set()}
    checks = 0
    for step in steps:
        if not isinstance(step, dict) or not isinstance(step.get("action"), str) or step["action"] not in schemas:
            raise ValueError("未知场景步骤。")
        action = step["action"]
        if set(step) - (schemas[action] | {"action", "timeout"}):
            raise ValueError(f"步骤 {action} 含未知字段。")
        timeout = step.get("timeout", 5)
        if type(timeout) not in {int, float} or not math.isfinite(timeout) or not 0 < timeout <= 120:
            raise ValueError("步骤 timeout 必须在 (0,120] 秒内。")
        if action == "click" and any(type(step.get(k)) is not int or step[k] < 0 for k in ("x", "y")):
            raise ValueError("click 需要非负整数 x、y（客户区物理像素）。")
        for field in schemas[action] & {"contains", "text", "name"}:
            if not isinstance(step.get(field), str) or not 1 <= len(step[field]) <= 4096 or "\0" in step[field]:
                raise ValueError(f"{action}.{field} 需要非空字符串（最多4096字符）。")
        if action == "wait_window" and not isinstance(step.get("title_contains", ""), str):
            raise ValueError("title_contains 必须是字符串。")
        if action == "assert_debug" and type(step.get("after_action", True)) is not bool:
            raise ValueError("after_action 必须是布尔值。")
        if action == "screenshot":
            name = step["name"]
            if len(name) > 80 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in name):
                raise ValueError("截图名称只能包含英文字母、数字、短横线、下划线（1–80字符）。")
        if action == "key" and (not isinstance(step.get("key"), str) or step["key"] not in KEYS):
            raise ValueError("不支持的按键；可用：" + ", ".join(KEYS))
        if action == "text" and len(step["text"].encode("utf-16-le")) > 8192:
            raise ValueError("文本不能超过 4096 个 UTF-16 码元。")
        if action == "wait":
            seconds = step.get("seconds")
            if type(seconds) not in {int, float} or not math.isfinite(seconds) or not 0 <= seconds <= 30:
                raise ValueError("wait.seconds 必须在 [0,30] 秒内。")
        checks += action in {"assert_debug", "assert_title"}
    if not checks:
        raise ValueError("交互场景必须包含 assert_debug 或 assert_title 状态断言。")
    if steps[-1]["action"] not in {"close", "wait_exit"}:
        raise ValueError("场景最后一步必须 close 或 wait_exit，明确验证程序退出。")
    return value


def execute(executable: Path, *, arguments: list[str] | None = None, cwd: Path | None = None,
            output: Path, timeout: float = 30, scenario: dict[str, Any] | None = None,
            expected_exit_code: int = 0) -> dict[str, Any]:
    if not 0 < timeout <= 1200 or not math.isfinite(timeout):
        raise ValueError("运行超时必须在 (0,1200] 秒内。")
    if scenario is not None:
        validate_scenario(scenario)
        # Check before creating a process or output directory.
        try:
            import PIL.Image  # noqa: F401
        except ImportError as exc:
            raise RuntimeError("交互截图需要 Pillow；运行 pip install cli-anything-xcide[automation]。") from exc
        expected_exit_code = scenario.get("expected_exit_code", 0)
    if type(expected_exit_code) is not int or not 0 <= expected_exit_code <= 0xFFFFFFFF:
        raise ValueError("expected_exit_code 必须是无符号 32 位整数。")
    executable = executable.expanduser().resolve(strict=True)
    artifact = inspect_pe(executable)
    working = (cwd or executable.parent).expanduser().resolve(strict=True)
    if not working.is_dir():
        raise ValueError("工作目录不存在。")
    directory = output.expanduser().resolve() / ("run-" + uuid.uuid4().hex)
    directory.mkdir(parents=True, exist_ok=False)
    report: dict[str, Any] = {"ok": False, "run_id": directory.name, "directory": str(directory),
                              "started_at": datetime.now(timezone.utc).isoformat(), "exe": artifact,
                              "arguments": arguments or [], "cwd": str(working), "steps": [],
                              "expected_exit_code": expected_exit_code, "timed_out": False,
                              "scenario": scenario, "report": str(directory / "report.json")}
    child = None
    desktop = None
    isolated = None
    deadline = time.monotonic() + timeout
    hwnd = None
    cursor = 0
    last_check = 0.0

    def pump() -> None:
        nonlocal last_check
        if time.monotonic() >= deadline:
            report["timed_out"] = True
            raise TimeoutError("运行超过总超时。")
        assert child is not None
        child.poll(20)
        if time.monotonic() - last_check > 0.2:
            child.check_stream_limit()
            last_check = time.monotonic()
        if child.truncated:
            raise RuntimeError("运行调试输出超过记录上限，不能完成可靠断言。")

    def wait_for(predicate: Any, seconds: float, description: str, allow_exit: bool = False) -> Any:
        until = min(deadline, time.monotonic() + seconds)
        while True:
            pump()
            result = predicate()
            if result:
                return result
            if child.exit_code is not None and not allow_exit:
                raise RuntimeError(f"程序在 {description} 前已退出：{child.exit_code}")
            if time.monotonic() >= until:
                if until == deadline:
                    report["timed_out"] = True
                raise TimeoutError(f"等待超时：{description}")
            if child.exit_code is not None:
                time.sleep(0.01)

    try:
        isolated = PrivateDesktop()
        report["automation"] = {"desktop": isolated.name, "input": "xcgui-ui-thread-message",
                                 "foreground_input": False, "screen_capture": False,
                                 "before": isolated.observation()}
        child = DebugProcess(executable, arguments or [], working, directory,
                             desktop_name=isolated.name, test_token=isolated.token if scenario else None)
        report["pid"] = child.pid
        if scenario is not None:
            desktop = Desktop(child.pid, executable, isolated, directory)
            for index, step in enumerate(scenario["steps"]):
                row = {"index": index, "action": step["action"], "ok": False}
                report["steps"].append(row)
                row["desktop_before"] = isolated.observation()
                action, limit = step["action"], step.get("timeout", 5)
                pump()
                if action == "wait_window":
                    def choose() -> int | None:
                        windows = desktop.windows(step.get("title_contains", ""))
                        if len(windows) > 1:
                            raise RuntimeError("有多个目标窗口，请用 title_contains 缩小范围。")
                        return windows[0] if windows else None
                    hwnd = wait_for(choose, limit, "目标窗口")
                    row["window"] = desktop.geometry(hwnd)
                    desktop.request(hwnd, 1, pump, min(limit, max(0.001, deadline - time.monotonic())))
                elif action in {"click", "text", "key", "assert_title", "screenshot", "close"}:
                    if hwnd is None:
                        raise ValueError("输入/截图/关闭前需要 wait_window。")
                    desktop.verify(hwnd)
                    remaining = min(limit, max(0.001, deadline - time.monotonic()))
                    if action in {"click", "text", "key"}:
                        # Flush already queued debug events before establishing
                        # the post-input assertion boundary. Never wait forever
                        # for a program that continuously emits messages.
                        for _ in range(1000):
                            if not child.poll(0):
                                break
                            if time.monotonic() >= deadline or child.truncated:
                                raise RuntimeError("输入前无法建立稳定的调试输出边界。")
                        else:
                            raise RuntimeError("输入前调试事件持续涌入，无法可靠关联动作。")
                        cursor = len(child.messages)
                    if action == "click":
                        row["input"] = desktop.click(hwnd, step["x"], step["y"], pump, remaining)
                    elif action == "text":
                        desktop.type_text(hwnd, step["text"], pump, remaining)
                    elif action == "key":
                        desktop.key(hwnd, step["key"], pump, remaining)
                    elif action == "assert_title":
                        wait_for(lambda: step["contains"] in desktop.title(hwnd), limit, "窗口标题断言")
                        row["title"] = desktop.title(hwnd)
                    elif action == "screenshot":
                        row["screenshot"] = desktop.screenshot(hwnd, directory / f"{index:03d}-{step['name']}.png", pump, remaining)
                        if not row["screenshot"]["nonblank"]:
                            raise RuntimeError("截图为空白/黑帧，不能证明界面完成绘制。")
                    else:
                        desktop.request_close(hwnd)
                        wait_for(lambda: child.exit_code is not None, limit, "正常退出", allow_exit=True)
                    if action in {"click", "text", "key"}:
                        settle = time.monotonic() + 0.15
                        wait_for(lambda: time.monotonic() >= settle, limit, "输入消息处理")
                elif action == "assert_debug":
                    start = cursor if step.get("after_action", True) else 0
                    wait_for(lambda: step["contains"] in "".join(child.messages[start:]), limit, "调试输出断言")
                    row["matched"] = step["contains"]
                elif action == "wait":
                    until = time.monotonic() + step["seconds"]
                    wait_for(lambda: time.monotonic() >= until, step["seconds"] + 0.1, "等待")
                elif action == "wait_exit":
                    wait_for(lambda: child.exit_code is not None, limit, "程序退出", allow_exit=True)
                row["ok"] = True
                row["desktop_after"] = isolated.observation()
        else:
            wait_for(lambda: child.exit_code is not None, timeout, "程序退出", allow_exit=True)
        report["ok"] = child.exit_code == expected_exit_code and not any(not e["first_chance"] for e in child.exceptions)
        if not report["ok"]:
            report["error"] = "程序退出码不符合预期或存在未处理异常。"
    except (OSError, RuntimeError, ValueError, TimeoutError) as exc:
        report["error"] = str(exc)
        report["error_type"] = type(exc).__name__
        report["step_timed_out"] = isinstance(exc, TimeoutError)
    finally:
        if desktop is not None:
            desktop.close()
        if child is not None:
            child.close()
            report.update({"exit_code": child.exit_code, "terminated": child.terminated,
                           "debug_output": "".join(child.messages), "debug_events": child.events,
                           "exceptions": child.exceptions, "output_truncated": child.truncated,
                           "cleanup_error": child.cleanup_error,
                           "stdout": str(directory / "stdout.bin"), "stderr": str(directory / "stderr.bin")})
            if child.cleanup_error or child.terminated or child.truncated:
                report["ok"] = False
        if isolated is not None:
            report["automation"]["after"] = isolated.observation()
            try:
                isolated.close()
            except OSError as exc:
                report["desktop_cleanup_error"] = str(exc)
                report["ok"] = False
        (directory / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
