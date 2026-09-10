#!/usr/bin/env python
"""FEAT-018 performance measurement protocol — evolution doc section 9.5.

A stdlib-only, self-contained measurement CLI implementing the six-point
protocol of ``docs/requirements/architecture-evolution-0.80.0.md`` section 9.5:

1. segmented measurement: ``python -X importtime`` (import set) + per-command
   wall clock;
2. interleaved sampling on the same machine / same interpreter / same work
   tree (A/B/A/B >= 5 rounds; this slice samples a single implementation,
   so the interleave is command-vs-command + round order preserved);
3. cold/warm reported separately (cold = the command's FIRST run in this
   session — OS caches not yet warm; warm = every later run);
4. metrics = median + P95 + environment metadata (Python version / OS /
   load class — RISK-048: parallel governance load pollutes samples, so the
   load class is a first-class COVARIATE, never an afterthought);
5. tolerances pre-agreed (initial hypothesis per section 9.5 item 5:
   median rel <= 10%, P95 rel <= 25%, plus an absolute-seconds floor for
   small baselines); breach = slice acceptance FAIL;
6. never conclude from a single sample (the 0.5s vs 4.04s lesson, facts 7.3).

Deliverables wired by this module:
- ``--sample status,summary``: interleaved dual-command baseline report
  (JSON via ``--out``), consumed by FEAT-020 / slice acceptance (R6 face);
- ``--init-tolerance``: writes the first tolerance table whose
  ``r6_threshold_fill`` block is key-compatible with
  ``core/architecture-baseline.json`` ``r6_startup_budget.threshold``
  (currently ``null``; advisory until R6 wiring consumes it — never fatal
  in v1);
- ``--baseline OLD.json``: judges a fresh sample against a stored baseline
  using the tolerance table (this is the REFACTOR slice acceptance action).

Measurement calibers (disclosed in every report):
- ``-B`` is used for every sampled subprocess (no bytecode-cache writes —
  the AUDIT-151 "measurement-safe variant"; does not change behavior);
- the importtime probe runs SEPARATELY from the wall-clock samples so the
  instrumentation overhead never pollutes the timings;
- ``sys_modules_probe`` re-implements the R6 probe verbatim
  (``python -I -B -c 'import sys,json; ...; import verify_workflow'``) so
  the command-level import face stays cross-checkable against
  ``r6_startup_budget.import_count`` (= 196 at FEAT-019 time). It is an
  independent implementation on purpose: this module must not be imported
  by the engine, and must not import sibling task modules (module boundary
  per evolution section 10 REFACTOR-perf-protocol row).

This module performs ZERO engine modifications: it only spawns the engine
as a subprocess and reads its output.

Exit codes: 0 = report produced (and, with ``--baseline``, every judged
metric within tolerance); 1 = sampling/command failure; 2 = argument or
schema-validation error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

INFRA_DIR = Path(__file__).resolve().parent
SKILL_ROOT = INFRA_DIR.parent
ENGINE = INFRA_DIR / "verify_workflow.py"
DEFAULT_TOLERANCE_FILE = SKILL_ROOT / "core" / "perf-tolerance.json"

REPORT_SCHEMA = "spg-perf-report/1"
TOLERANCE_SCHEMA = "spg-perf-tolerance/1"
TASK_ID = "FEAT-018"
PROTOCOL_REF = "docs/requirements/architecture-evolution-0.80.0.md#9.5"

DEFAULT_REPEAT = 5          # §9.5 item 2: >= 5 interleaved rounds
DEFAULT_TOP_N = 10
LOAD_CLASSES = ("serial-exclusive", "parallel-observed")

# Command registry — extend here to measure more commands (task brief:
# "可参数扩展"). argv[1] keeps -B on every sample (measurement-safe).
COMMANDS: Dict[str, List[str]] = {
    "status": [sys.executable, "-B", str(ENGINE), "status"],
    "summary": [sys.executable, "-B", str(ENGINE),
                "check-governance", "--summary-only"],
}

CALIBER_NOTES = [
    "cold = first run of this command in this session; warm = later runs "
    "(§9.5 item 3; OS file cache is the practical cold/warm boundary)",
    "-B on every sampled subprocess: no bytecode-cache writes, behavior "
    "unchanged (AUDIT-151 measurement-safe variant)",
    "importtime probe runs separately from wall-clock samples so "
    "instrumentation overhead never pollutes the timings",
    "P95 = linear interpolation on rank (n-1)*p/100 (numpy-linear caliber)",
    "decomposition is a single-process approximation: wall = import-self "
    "sum + residual (interpreter startup + business + I/O merged)",
    "load class is a covariate, not metadata decoration (AUDIT-151 / "
    "RISK-048: 0.49~0.56s serial vs 4.04s parallel-observed)",
]


# ── pure statistics face ─────────────────────────────────────────────────────


def median(values: Sequence[float]) -> float:
    """statistics.median re-exported as the protocol's median caliber."""
    return float(statistics.median(values))


def percentile(values: Sequence[float], p: float) -> float:
    """Linear-interpolation percentile (rank = (n-1)*p/100).

    Single-sample input returns the sample itself — documented degenerate
    caliber, kept deterministic for report reproducibility.
    """
    data = sorted(float(v) for v in values)
    if not data:
        raise ValueError("percentile of empty sample")
    if len(data) == 1:
        return data[0]
    rank = (len(data) - 1) * (p / 100.0)
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return data[int(rank)]
    frac = rank - lo
    return data[lo] * (1.0 - frac) + data[hi] * frac


def summarize_samples(values: Sequence[float]) -> Dict[str, float]:
    """n / min / max / median / p95 over the given samples."""
    data = [float(v) for v in values]
    return {
        "n": len(data),
        "min": min(data),
        "max": max(data),
        "median": median(data),
        "p95": percentile(data, 95),
    }


def split_cold_warm(samples_s: Sequence[float]) -> Tuple[float, List[float]]:
    """§9.5 item 3: cold = first sample, warm = the rest."""
    data = [float(v) for v in samples_s]
    if not data:
        raise ValueError("no samples to split")
    return data[0], data[1:]


# ── pure importtime face ─────────────────────────────────────────────────────


def parse_importtime(text: str, return_skipped: bool = False):
    """Parse CPython ``-X importtime`` stderr into segment dicts.

    Row shape: ``import time: <self_us> | <cumulative_us> | <indent><module>``
    (the header row and malformed rows are skipped — and disclosed via
    ``return_skipped=True``; a measurement protocol never silently drops
    data it failed to understand).
    """
    segments: List[dict] = []
    skipped = 0
    for raw in text.splitlines():
        if "|" not in raw:
            skipped += 1
            continue
        parts = raw.split("|")
        if len(parts) != 3:
            skipped += 1
            continue
        head = parts[0].strip()
        if head.startswith("import time:"):
            head = head[len("import time:"):].strip()
        try:
            self_us = int(head)
            cumulative_us = int(parts[1].strip())
        except ValueError:
            skipped += 1
            continue
        module_raw = parts[2]
        indent = len(module_raw) - len(module_raw.lstrip())
        segments.append({
            "module": module_raw.strip(),
            "self_us": self_us,
            "cumulative_us": cumulative_us,
            "depth": indent // 2,
        })
    if return_skipped:
        return segments, skipped
    return segments


def import_totals(segments: Sequence[dict]) -> Dict[str, float]:
    """Import-event count + the sum of SELF microseconds (import cost).

    self_us is the per-import exclusive time; summing it yields the total
    time spent importing (cumulative_us double-counts nested imports).
    """
    return {
        "import_events": len(segments),
        "self_total_us": sum(s["self_us"] for s in segments),
    }


def top_imports(segments: Sequence[dict], n: int = DEFAULT_TOP_N) -> List[dict]:
    """Top-N imports by SELF microseconds (the genuine per-import cost)."""
    ranked = sorted(segments, key=lambda s: s["self_us"], reverse=True)
    return [
        {"module": s["module"], "self_us": s["self_us"],
         "cumulative_us": s["cumulative_us"], "depth": s["depth"]}
        for s in ranked[:n]
    ]


def decompose_wall(wall_s: float, import_self_total_us: float) -> Dict[str, object]:
    """Wall decomposition via the task-brief approximation.

    importtime self-sum approximates the import segment; the residual is
    reported MERGED (interpreter startup + business + I/O) because a single
    subprocess cannot separate them without engine instrumentation —
    disclosed instead of guessed.
    """
    import_s = import_self_total_us / 1_000_000.0
    return {
        "wall_total_s": wall_s,
        "import_self_total_s": round(import_s, 6),
        "non_import_residual_s": round(max(wall_s - import_s, 0.0), 6),
        "note": "approx: residual = interpreter startup + business + I/O "
                "merged (importtime cumulative approximation + total wall)",
    }


# ── pure tolerance face ──────────────────────────────────────────────────────


def judge_tolerance(observed_s: float, baseline_s: float, metric: str,
                    median_rel: float, p95_rel: float,
                    abs_floor_s: float) -> Dict[str, object]:
    """Judge one metric against the pre-agreed tolerance band.

    band = max(baseline * rel, abs_floor): the relative tolerance governs
    normal baselines, the absolute floor widens the band for small
    baselines so jitter cannot fake a FAIL (§9.5 item 5 + task brief
    "相对容差 + 绝对秒下限"). Verdict FAIL means the observed value is
    SLOWER than baseline beyond the band.
    """
    rel = median_rel if metric == "median" else p95_rel
    band = max(baseline_s * rel, abs_floor_s)
    delta = observed_s - baseline_s
    return {
        "metric": metric,
        "baseline_s": baseline_s,
        "observed_s": observed_s,
        "delta_s": round(delta, 6),
        "rel": rel,
        "abs_floor_s": abs_floor_s,
        "allowed_band_s": round(band, 6),
        "verdict": "FAIL" if delta > band else "PASS",
    }


def build_tolerance_table() -> Dict[str, object]:
    """First-version tolerance table — §9.5 item 5 initial hypothesis.

    Values are hypotheses to be calibrated on the first comparison slices
    (``calibration_status`` says so explicitly — never presented as
    measured fact). Load class is a per-command covariate (AUDIT-151
    lesson: the 4.04s status sample was parallel-observed, the 0.49~0.56s
    samples serial-exclusive).
    """
    serial = {"median_rel": 0.10, "p95_rel": 0.25, "abs_floor_s": 0.05}
    parallel = {
        "median_rel": 0.25, "p95_rel": 0.50, "abs_floor_s": 0.20,
        "note": "RISK-048: parallel governance load pollutes samples — "
                "observation-only caliber, never a gate",
    }
    return {
        "schema": TOLERANCE_SCHEMA,
        "task": TASK_ID,
        "source": PROTOCOL_REF + " (item 5 / P24)",
        "calibration_status": "initial-hypothesis",
        "judge_face": "warm median / warm P95; cold sample is "
                      "observed-only (never judged)",
        "environment_covariates_note":
            "AUDIT-151 / RISK-048: load class is a covariate — "
            "serial-exclusive and parallel-observed tolerances are not "
            "interchangeable",
        "commands": {
            cmd: {"repeat_min": DEFAULT_REPEAT, "judge": "warm",
                  "loads": {"serial-exclusive": dict(serial),
                            "parallel-observed": dict(parallel)}}
            for cmd in sorted(COMMANDS)
        },
        "r6_threshold_fill": {
            "wall_ms_rel_median": serial["median_rel"],
            "wall_ms_rel_p95": serial["p95_rel"],
            "abs_floor_s": serial["abs_floor_s"],
            "import_count_max_delta": 0,
            "probe": "python -I -B -c 'import verify_workflow' (isolated) "
                     "— architecture-baseline.json r6_startup_budget.probe",
            "note": "FEAT-018 initial hypothesis per §9.5 item 5; fill into "
                    "r6_startup_budget.threshold when R6 wiring consumes "
                    "it (advisory, never fatal in v1); calibrate on first "
                    "comparison slices",
        },
    }


def validate_tolerance_table(obj: object) -> List[str]:
    """Schema check for a tolerance table; empty list = valid."""
    errors: List[str] = []
    if not isinstance(obj, dict):
        return ["tolerance table is not an object"]
    if obj.get("schema") != TOLERANCE_SCHEMA:
        errors.append(f"schema != {TOLERANCE_SCHEMA!r}")
    commands = obj.get("commands")
    if not isinstance(commands, dict) or not commands:
        errors.append("commands missing/empty")
        commands = {}
    for cmd, entry in commands.items():
        if not isinstance(entry, dict):
            errors.append(f"commands.{cmd}: not an object")
            continue
        if int(entry.get("repeat_min", 0)) < DEFAULT_REPEAT:
            errors.append(f"commands.{cmd}.repeat_min < {DEFAULT_REPEAT}")
        if entry.get("judge") != "warm":
            errors.append(f"commands.{cmd}.judge != 'warm'")
        loads = entry.get("loads", {})
        for load in LOAD_CLASSES:
            load_entry = loads.get(load)
            if not isinstance(load_entry, dict):
                errors.append(f"commands.{cmd}.loads.{load} missing")
                continue
            for key in ("median_rel", "p95_rel", "abs_floor_s"):
                value = load_entry.get(key)
                if not isinstance(value, (int, float)) or value <= 0:
                    errors.append(
                        f"commands.{cmd}.loads.{load}.{key} invalid")
    fill = obj.get("r6_threshold_fill")
    if not isinstance(fill, dict):
        errors.append("r6_threshold_fill missing")
    else:
        for key in ("wall_ms_rel_median", "wall_ms_rel_p95",
                    "abs_floor_s", "import_count_max_delta"):
            if key not in fill:
                errors.append(f"r6_threshold_fill.{key} missing")
    return errors


def compare_against_baseline(current_commands: Dict[str, dict],
                             old_commands: Dict[str, dict],
                             tol_entries: Dict[str, dict]) -> Dict[str, dict]:
    """Judge warm median + warm P95 per command against a stored baseline.

    Both sides are report-``commands``-shaped dicts (each entry carries a
    ``wall`` sub-face with ``warm_median`` / ``warm_p95``) — the same shape
    the CLI actually handles, so the unit-tested contract and the real data
    flow cannot drift apart.
    """
    verdicts: Dict[str, dict] = {}
    for cmd, entry in tol_entries.items():
        if cmd not in current_commands or cmd not in old_commands:
            continue
        cur_wall = current_commands[cmd]["wall"]
        old_wall = old_commands[cmd]["wall"]
        verdicts[cmd] = {
            "median": judge_tolerance(
                cur_wall["warm_median"], old_wall["warm_median"], "median",
                entry["median_rel"], entry["p95_rel"],
                entry["abs_floor_s"]),
            "p95": judge_tolerance(
                cur_wall["warm_p95"], old_wall["warm_p95"], "p95",
                entry["median_rel"], entry["p95_rel"],
                entry["abs_floor_s"]),
        }
    return verdicts


# ── environment face ─────────────────────────────────────────────────────────


def _git_head() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30, check=False)
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "unknown"


def collect_environment(load_class: str, load_note: str,
                        git_head: Optional[str] = None) -> Dict[str, object]:
    if load_class not in LOAD_CLASSES:
        raise ValueError(f"load_class must be one of {LOAD_CLASSES}")
    return {
        "python_version": platform.python_version(),
        "python_full": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor_count": os.cpu_count(),
        "cwd": str(Path.cwd()),
        "git_head": git_head if git_head is not None else _git_head(),
        "load_class": load_class,
        "load_note": load_note,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"),
    }


# ── report face (pure given command results) ─────────────────────────────────


def build_report(*, repeat: int, load_class: str, load_note: str,
                 command_results: Dict[str, dict],
                 sample_order: Sequence[str],
                 tolerance_ref: Optional[str] = None,
                 environment: Optional[Dict[str, object]] = None,
                 baseline_verdicts: Optional[Dict[str, dict]] = None,
                 top_n: int = DEFAULT_TOP_N) -> Dict[str, object]:
    """Assemble the baseline report from sampled command results.

    Pure with respect to sampling: the caller (CLI or a test) supplies
    ``command_results`` — this function never spawns a subprocess.
    """
    commands: Dict[str, dict] = {}
    for cmd, result in command_results.items():
        samples = result["samples_s"]
        cold, warm = split_cold_warm(samples)
        wall = summarize_samples(samples)
        warm_stats = summarize_samples(warm) if warm else None
        wall["warm_median"] = warm_stats["median"] if warm_stats else None
        wall["warm_p95"] = warm_stats["p95"] if warm_stats else None
        segments = result.get("importtime_segments") or []
        totals = import_totals(segments)
        commands[cmd] = {
            "argv": result["argv"],
            "repeat": len(samples),
            "samples_s": samples,
            "cold_s": cold,
            "warm_s": warm,
            "wall": wall,
            "importtime": {
                "import_events": totals["import_events"],
                "self_total_ms": round(totals["self_total_us"] / 1000.0, 3),
                "top": top_imports(segments, top_n),
            },
            "sys_modules_probe": result.get("sys_modules_probe"),
            "decomposition": decompose_wall(
                wall["median"], totals["self_total_us"]),
        }
    report: Dict[str, object] = {
        "schema": REPORT_SCHEMA,
        "task": TASK_ID,
        "generated_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"),
        "protocol": {
            "ref": PROTOCOL_REF,
            "interleaved": True,
            "repeat": repeat,
            "cold_warm_split": True,
            "sample_order": list(sample_order),
            "caliber_notes": list(CALIBER_NOTES),
        },
        "environment": environment if environment is not None else
        collect_environment(load_class, load_note),
        "commands": commands,
        "tolerance_table_ref": tolerance_ref,
    }
    if baseline_verdicts is not None:
        report["baseline_comparison"] = baseline_verdicts
    return report


def validate_report(obj: object) -> List[str]:
    """Schema check for a baseline report; empty list = valid."""
    errors: List[str] = []
    if not isinstance(obj, dict):
        return ["report is not an object"]
    if obj.get("schema") != REPORT_SCHEMA:
        errors.append(f"schema != {REPORT_SCHEMA!r}")
    for key in ("task", "generated_utc", "protocol", "environment",
                "commands"):
        if key not in obj:
            errors.append(f"{key} missing")
    environment = obj.get("environment", {})
    if isinstance(environment, dict):
        for key in ("python_version", "platform", "load_class", "cwd",
                    "git_head"):
            if key not in environment:
                errors.append(f"environment.{key} missing")
    else:
        errors.append("environment is not an object")
    commands = obj.get("commands", {})
    if not isinstance(commands, dict) or not commands:
        errors.append("commands missing/empty")
        commands = {}
    for cmd, entry in commands.items():
        if not isinstance(entry, dict):
            errors.append(f"commands.{cmd}: not an object")
            continue
        for key in ("argv", "repeat", "samples_s", "cold_s", "warm_s",
                    "wall", "importtime", "decomposition"):
            if key not in entry:
                errors.append(f"commands.{cmd}.{key} missing")
        wall = entry.get("wall", {})
        if isinstance(wall, dict):
            for key in ("n", "median", "p95", "warm_median", "warm_p95"):
                if key not in wall:
                    errors.append(f"commands.{cmd}.wall.{key} missing")
        importtime = entry.get("importtime", {})
        if isinstance(importtime, dict):
            for key in ("import_events", "self_total_ms", "top"):
                if key not in importtime:
                    errors.append(
                        f"commands.{cmd}.importtime.{key} missing")
    return errors


# ── slow paths (subprocess sampling) ─────────────────────────────────────────


def run_command_once(argv: Sequence[str], importtime: bool = False) -> dict:
    """Run one sampled command; wall clock via perf_counter.

    ``importtime=True`` prepends ``-X importtime`` — used only by the
    separate probe, never by wall-clock samples (caliber note 3).
    """
    full = list(argv)
    if importtime:
        full = [full[0], "-X", "importtime"] + full[1:]
    started = time.perf_counter()
    result = subprocess.run(
        full, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=900, check=False)
    wall_s = time.perf_counter() - started
    return {
        "wall_s": round(wall_s, 4),
        "returncode": result.returncode,
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }


def probe_importtime(argv: Sequence[str]) -> List[dict]:
    """One ``-X importtime`` run of the command; parsed import segments.

    NOT part of the wall-clock samples — the instrumentation overhead
    would pollute them (§9.5 caliber; disclosed in every report).
    """
    full = [argv[0], "-X", "importtime"] + list(argv[1:])
    result = subprocess.run(
        full, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=900, check=False)
    return parse_importtime(result.stderr)


def probe_sys_modules(infra_dir: Path) -> Optional[dict]:
    """R6-identical import-set probe (independent implementation).

    Same shape as ``archguard_ratchet.measure_cold_import`` on purpose:
    ``import_count`` here must be cross-checkable against
    ``r6_startup_budget.import_count`` (196 at FEAT-019 time). Kept as an
    independent twin — this module must stay import-free of sibling task
    modules (engine never imports us; we never import them).
    """
    probe = (
        "import sys, json; sys.path.insert(0, {path!r}); "
        "import verify_workflow; print(json.dumps(sorted(sys.modules)))"
    ).format(path=str(infra_dir))
    started = time.perf_counter()
    try:
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-c", probe],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    wall_ms = round((time.perf_counter() - started) * 1000.0, 1)
    if result.returncode != 0:
        return None
    try:
        modules = json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None
    digest = hashlib.sha256("\n".join(modules).encode("utf-8")).hexdigest()
    return {
        "import_count": len(modules),
        "import_set_sha256": digest,
        "wall_ms": wall_ms,
        "interpreter_family":
            f"{sys.version_info.major}.{sys.version_info.minor}",
        "note": "R6-identical probe caliber (python -I -B isolated); "
                "approximates the command import face (the engine imports "
                "its full set at module load)",
    }


def interleave_sample(cmd_keys: Sequence[str], repeat: int,
                      commands: Optional[Dict[str, List[str]]] = None
                      ) -> Tuple[Dict[str, dict], List[str]]:
    """§9.5 item 2 interleaved sampling: round-robin across commands.

    Order r1: cmd1, cmd2, ...; r2: cmd1, cmd2, ... — so ambient load drift
    hits every command evenly (single-implementation self-sampling
    caliber: no old/new pair yet, the interleave is across commands and
    rounds, ready to become A/B when a comparison slice exists).
    """
    registry = commands if commands is not None else COMMANDS
    order: List[str] = []
    samples: Dict[str, List[float]] = {k: [] for k in cmd_keys}
    argvs: Dict[str, List[str]] = {}
    for _round in range(repeat):
        for key in cmd_keys:
            argv = registry[key]
            argvs[key] = argv
            run = run_command_once(argv)
            if run["returncode"] != 0:
                raise RuntimeError(
                    f"sampled command {key!r} exited "
                    f"{run['returncode']}: {run['stderr_tail'][-400:]}")
            order.append(key)
            samples[key].append(run["wall_s"])
    results: Dict[str, dict] = {}
    for key in cmd_keys:
        results[key] = {
            "argv": argvs[key],
            "samples_s": samples[key],
            "importtime_segments": probe_importtime(registry[key]),
            "sys_modules_probe": probe_sys_modules(INFRA_DIR),
        }
    return results, order


def sample_command(cmd_key: str, repeat: int = DEFAULT_REPEAT,
                   commands: Optional[Dict[str, List[str]]] = None) -> dict:
    """Single-command convenience wrapper over interleave_sample."""
    results, _ = interleave_sample([cmd_key], repeat, commands)
    return results[cmd_key]


# ── CLI face ─────────────────────────────────────────────────────────────────


def parse_sample_arg(value: str) -> Tuple[Optional[List[str]], Optional[int]]:
    """Dual semantics (both contract faces stay runnable):

    - ``--sample status,summary`` → command-key list (execution-packet
      acceptance command);
    - ``--sample 5`` → pure digits = repeat count (task-brief caliber).

    Unknown command keys raise ValueError; the CLI turns that into exit 2.
    """
    text = (value or "").strip()
    if not text:
        return None, None
    if text.isdigit():
        return None, int(text)
    keys = [part.strip() for part in text.split(",") if part.strip()]
    unknown = [k for k in keys if k not in COMMANDS]
    if unknown:
        raise ValueError(
            f"unknown command key(s) {unknown}; registered: "
            f"{sorted(COMMANDS)}")
    return keys, None


def resolve_plan(sample_value: Optional[str],
                 repeat_value: Optional[int],
                 default_cmds: Optional[List[str]] = None,
                 default_repeat: int = DEFAULT_REPEAT
                 ) -> Tuple[List[str], int]:
    """Merge --sample (dual semantics) + --repeat into the sampling plan."""
    cmds_from_sample, repeat_from_sample = parse_sample_arg(sample_value or "")
    cmds = cmds_from_sample or default_cmds or list(COMMANDS.keys())
    repeat = repeat_from_sample
    if repeat_value is not None:
        repeat = repeat_value
    if repeat is None:
        repeat = default_repeat
    if repeat < DEFAULT_REPEAT:
        raise ValueError(
            f"repeat={repeat} violates §9.5 item 2 (>= {DEFAULT_REPEAT} "
            f"interleaved rounds)")
    return cmds, repeat


def _print_summary(report: Dict[str, object]) -> None:
    env = report["environment"]
    print(f"[perf-protocol {TASK_ID}] schema={report['schema']} "
          f"repeat={report['protocol']['repeat']}")  # type: ignore[index]
    print(f"  env: python {env['python_version']} | {env['platform']} "
          f"| load={env['load_class']} | head={str(env['git_head'])[:12]}")
    for cmd, entry in report["commands"].items():
        wall = entry["wall"]
        imp = entry["importtime"]
        dec = entry["decomposition"]
        print(f"  [{cmd}] n={wall['n']} cold={entry['cold_s']:.3f}s "
              f"median={wall['median']:.3f}s p95={wall['p95']:.3f}s "
              f"warm_median={wall['warm_median']:.3f}s "
              f"warm_p95={wall['warm_p95']:.3f}s")
        print(f"        import_events={imp['import_events']} "
              f"self_total={imp['self_total_ms']:.1f}ms | approx split: "
              f"import {dec['import_self_total_s']:.3f}s / residual "
              f"{dec['non_import_residual_s']:.3f}s")
        probe = entry.get("sys_modules_probe")
        if probe:
            print(f"        sys_modules_probe: count="
                  f"{probe['import_count']} ({probe['wall_ms']:.0f}ms, "
                  f"R6 caliber)")
    comparison = report.get("baseline_comparison")
    if comparison:
        for cmd, verdicts in comparison.items():
            for metric, verdict in verdicts.items():
                print(f"  [judge:{cmd}.{metric}] "
                      f"{verdict['verdict']} "
                      f"(baseline {verdict['baseline_s']:.3f}s -> observed "
                      f"{verdict['observed_s']:.3f}s, band "
                      f"{verdict['allowed_band_s']:.3f}s)")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="FEAT-018 performance measurement protocol "
                    "(evolution §9.5): interleaved sampling + importtime "
                    "segmentation + median/P95 tolerance judging.")
    parser.add_argument(
        "--sample", default=None,
        help="command keys to sample, comma-separated (default: "
             "status,summary) — OR a pure number to set the repeat count "
             "(e.g. --sample 5)")
    parser.add_argument(
        "--repeat", type=int, default=None,
        help=f"samples per command (default {DEFAULT_REPEAT}; minimum "
             f"{DEFAULT_REPEAT} per §9.5 item 2)")
    parser.add_argument("--out", default=None,
                        help="write the JSON baseline report to this path")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP_N,
                        help="importtime top-N in the report "
                             f"(default {DEFAULT_TOP_N})")
    parser.add_argument("--load", default="serial-exclusive",
                        choices=LOAD_CLASSES,
                        help="load class covariate (RISK-048; default "
                             "serial-exclusive)")
    parser.add_argument("--load-note", default=None,
                        help="free-text load observation note")
    parser.add_argument("--init-tolerance", action="store_true",
                        help=f"write the initial tolerance table to "
                             f"--tolerance path and exit")
    parser.add_argument("--tolerance", default=str(DEFAULT_TOLERANCE_FILE),
                        help="tolerance table path (default: "
                             "core/perf-tolerance.json)")
    parser.add_argument("--baseline", default=None,
                        help="previous baseline report JSON to judge "
                             "against (slice acceptance action)")
    args = parser.parse_args(argv)

    tolerance_path = Path(args.tolerance)
    if args.init_tolerance:
        table = build_tolerance_table()
        errors = validate_tolerance_table(table)
        if errors:
            print("[init-tolerance] internal table invalid: "
                  + "; ".join(errors), file=sys.stderr)
            return 2
        tolerance_path.parent.mkdir(parents=True, exist_ok=True)
        tolerance_path.write_text(
            json.dumps(table, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        print(f"[init-tolerance] wrote {tolerance_path} "
              f"(schema {TOLERANCE_SCHEMA}, initial hypothesis per §9.5)")
        return 0

    try:
        cmds, repeat = resolve_plan(args.sample, args.repeat)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    load_note = args.load_note or (
        "串行独占——采样期间零并行治理负载（RISK-048 纪律，AUDIT-151 口径）"
        if args.load == "serial-exclusive" else
        "parallel governance load observed — tolerance judging uses the "
        "parallel-observed band (observation-only)")
    print(f"[perf-protocol] sampling {cmds} x {repeat} rounds "
          f"(interleaved, load={args.load}) ...")
    try:
        command_results, order = interleave_sample(cmds, repeat)
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"error: sampling failed: {exc}", file=sys.stderr)
        return 1

    report = build_report(
        repeat=repeat, load_class=args.load, load_note=load_note,
        command_results=command_results, sample_order=order,
        tolerance_ref=str(tolerance_path), top_n=args.top)

    if args.baseline:
        baseline_path = Path(args.baseline)
        try:
            old_report = json.loads(
                baseline_path.read_text(encoding="utf-8"))
            tolerance_table = json.loads(
                tolerance_path.read_text(encoding="utf-8"))
            errors = validate_tolerance_table(tolerance_table)
            if errors:
                print("error: tolerance table invalid: "
                      + "; ".join(errors), file=sys.stderr)
                return 2
            load = args.load
            tol_entries = {
                cmd: entry["loads"][load] for cmd, entry in
                tolerance_table["commands"].items()}
            report["baseline_comparison"] = compare_against_baseline(
                report["commands"], old_report["commands"], tol_entries)
        except (OSError, ValueError, KeyError) as exc:
            print(f"error: baseline judging failed: {exc}", file=sys.stderr)
            return 2

    errors = validate_report(report)
    if errors:
        print("error: report schema invalid: " + "; ".join(errors),
              file=sys.stderr)
        return 2

    _print_summary(report)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        print(f"[perf-protocol] report written: {out_path}")

    comparison = report.get("baseline_comparison")
    if comparison:
        failed = [f"{cmd}.{metric}"
                  for cmd, verdicts in comparison.items()
                  for metric, verdict in verdicts.items()
                  if verdict["verdict"] == "FAIL"]
        if failed:
            print("[perf-protocol] TOLERANCE BREACH: " + ", ".join(failed),
                  file=sys.stderr)
            return 1
        print("[perf-protocol] all judged metrics within tolerance")
    return 0


if __name__ == "__main__":
    sys.exit(main())
