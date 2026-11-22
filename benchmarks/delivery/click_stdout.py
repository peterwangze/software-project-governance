"""Run the AUDIT-167 downstream journeys against an actual Click wheel."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

if not __debug__ or os.environ.get("PYTHONOPTIMIZE") not in (None, "", "0"):
    raise SystemExit("Acceptance requires Python assertions. Set PYTHONOPTIMIZE=0 and run without -O.")

EXPECTED = "invoice 17\nprinted 17\n"
DOWNSTREAM = r'''import gc
import os
from pathlib import Path
import sys
from unittest.mock import patch

if not __debug__:
    raise RuntimeError("Downstream acceptance requires Python assertions. Run without -O.")

import click
from click.testing import CliRunner

assert Path(click.__file__).resolve().is_relative_to(Path(os.environ["AUDIT_INSTALLED"]))
os.environ["PAGER"] = "audit-167-missing-program"

@click.command()
def downstream():
    borrowed = sys.stdout
    click.echo_via_pager("invoice 17")
    gc.collect()
    assert not borrowed.closed
    borrowed.write("printed 17\n")
    borrowed.flush()

if sys.argv[1] == "cli-runner":
    # Supply terminal capability while keeping the downstream command and I/O real.
    with patch("click._termui_impl.isatty", return_value=True):
        result = CliRunner().invoke(downstream)
    if result.exception is not None:
        raise result.exception
    assert result.exit_code == 0
    sys.stdout.write(result.output)
else:
    downstream(args=[])
'''


def assess(wheel: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    installed = output / "installed"
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
         "--no-index", "--no-deps", "--target", str(installed), str(wheel)],
        check=True, capture_output=True,
    )
    command = output / "downstream.py"
    command.write_text(DOWNSTREAM, encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=str(installed), AUDIT_INSTALLED=str(installed))
    scenarios = {}
    for method in ("cli-runner", "redirected-process"):
        run = subprocess.run(
            [sys.executable, str(command), method], env=env, cwd=output,
            capture_output=True, text=True, timeout=30,
        )
        scenarios[method] = {
            "exit": run.returncode,
            "stdout": run.stdout,
            "stderr": run.stderr,
            "passed": run.returncode == 0 and run.stdout == EXPECTED,
        }
    return {
        "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "scenarios": scenarios,
        "passed": all(case["passed"] for case in scenarios.values()),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("output", type=Path, help="new directory for this invocation")
    args = parser.parse_args()
    verdict = assess(args.wheel.resolve(strict=True), args.output.resolve())
    (args.output / "verdict.json").write_text(
        json.dumps(verdict, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    print("PASS" if verdict["passed"] else "FAIL")
    raise SystemExit(0 if verdict["passed"] else 1)
