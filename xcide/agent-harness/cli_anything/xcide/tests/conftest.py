"""Shared helpers for package and installed-console-script tests."""

from __future__ import annotations

import os
import shutil
import sys


def _resolve_cli(name: str) -> list[str]:
    """Locate the installed command or use the namespace package during development."""
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    executable = shutil.which(name)
    if executable:
        print(f"[_resolve_cli] Using installed command: {executable}")
        return [executable]
    if force:
        raise RuntimeError(f"{name} is not installed in PATH. Install the harness with pip install -e .")
    module = name.replace("cli-anything-", "cli_anything.") + "." + name.split("-")[-1] + "_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]
