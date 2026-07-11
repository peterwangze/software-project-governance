"""Optional quality-tool probes without runtime dependency claims."""

import shutil
import subprocess
from typing import Callable, Dict, Optional, Sequence


def probe_quality_tools(
    which: Callable[[str], Optional[str]] = shutil.which,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    timeout: int = 15,
) -> Dict[str, object]:
    tools = {}
    for name in ("ruff", "mypy"):
        executable = which(name)
        if not executable:
            tools[name] = {"state": "NOT_RUN", "reason": "not installed"}
            continue
        try:
            result = runner(
                [executable, "--version"], capture_output=True, text=True, encoding="utf-8",
                errors="replace", check=False, timeout=timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            tools[name] = {"state": "FAIL", "reason": type(exc).__name__}
            continue
        if result.returncode == 0:
            tools[name] = {"state": "PASS", "version": result.stdout.strip() or result.stderr.strip()}
        else:
            tools[name] = {"state": "FAIL", "reason": f"exit {result.returncode}"}
    states = {item["state"] for item in tools.values()}
    overall = "FAIL" if "FAIL" in states else ("NOT_RUN" if states == {"NOT_RUN"} else "PASS")
    return {"state": overall, "tools": tools, "runtime_dependency": False}
