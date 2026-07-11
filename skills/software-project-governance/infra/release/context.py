"""Injected repository services for deterministic release checks."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import os
import subprocess
from typing import Callable, Mapping, Optional, Sequence


GitRunner = Callable[[Sequence[str], Path, int], tuple[int, str, str]]


def run_git(args: Sequence[str], root: Path, timeout: int) -> tuple[int, str, str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return 124, "", f"git command timed out after {timeout}s"
    except OSError as exc:
        return 125, "", f"git command could not be started ({type(exc).__name__})"
    return result.returncode, result.stdout.strip(), result.stderr.strip()


@dataclass(frozen=True)
class RepositoryContext:
    root: Path
    git: GitRunner = run_git
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    timeout: int = 15
    env: Optional[Mapping[str, str]] = None

    def run_git(self, *args: str) -> tuple[int, str, str]:
        return self.git(args, self.root, self.timeout)
