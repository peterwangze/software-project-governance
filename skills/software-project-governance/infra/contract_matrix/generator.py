"""FEAT-020 contract-matrix generator + differential harness (design §8.1/§10).

Everything in this module is extracted PROGRAMMATICALLY from the engine
itself (AST over ``verify_workflow.py`` ``main()``, source-regex over the
check banners, live invocation of representative check functions, and real
subprocess runs of ``governance-write-guard`` against deterministic
fixtures). No engine inventory is hand-copied here; the only literals are
the task-mandated freeze declarations (S6 residual-wave list, S4 dual-end
interpreter pins) and the representative sampling targets chosen by design
(§8.1 "选 3~5 个代表性命令").

Usage (explicit — snapshot updates are never implicit):

    python skills/software-project-governance/infra/contract_matrix/generator.py --regen
    python skills/software-project-governance/infra/contract_matrix/generator.py --check
    python skills/software-project-governance/infra/contract_matrix/generator.py --self-check
    python skills/software-project-governance/infra/contract_matrix/generator.py --golden

Exit codes: ``--check`` exits 1 on any contract-face drift (protection-net
semantics — drift must be reviewed, regenerated and explained, never silently
absorbed); ``--regen``/``--golden`` exit 0 on success; ``--self-check`` exits
1 if two consecutive extractions differ (determinism proof).
"""

from __future__ import annotations

import argparse
import ast
import atexit
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
_ENGINE_PATH = _INFRA_DIR / "verify_workflow.py"
_REPO_ROOT = _ENGINE_PATH.parents[2]
SNAPSHOT_PATH = _HERE / "snapshots.json"
GOLDEN_PATH = _HERE / "golden_samples.txt"
SNAPSHOT_SCHEMA = "spg-contract-matrix/1"
TASK_ID = "FEAT-020"

if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import verify_workflow as vw  # noqa: E402  (peer import; heavy but unavoidable)


# ── Freeze declarations (task-mandated literals, NOT extracted data) ─────────
# S6 冻结时点断言：快照元数据记录 0.79.0 未 released 与残余波次清单
# （版本规划对账用）。这是冻结时点的「申报事实」，与引擎提取面分开。
FREEZE_POINT = {
    "task": TASK_ID,
    "version_status": "0.79.0 未 released",
    "residual_waves": {
        "0.79.0 收尾": ["FEAT-012", "FEAT-013", "FX-195"],
        "0.80.0 P0 余项": [
            "FEAT-018", "FEAT-019", "FIX-301", "AUDIT-152", "DOC-003",
        ],
    },
    "note": "冻结基线含此清单（S6 版本规划对账用）",
}

# S4 双端 Python major.minor 版本钉：本仓库两个受支持解释器族——
# Windows 本地开发端与 GitHub Actions ubuntu CI 端（.github/workflows/ci.yml
# python-version '3.11'）。生成与比对须同解释器族（特征测试 fail-closed）。
PYTHON_FAMILY_PINS = [
    {"family": "3.14", "role": "local-dev-windows"},
    {"family": "3.11", "role": "ci-ubuntu"},
]

# 代表性 Result dict 构造点（§8.1 "选 3~5 个代表性命令"——设计选样，非引擎
# 清单手抄）：1 个 guard 核心 + 4 个 check 编排点，覆盖 verify_workflow 本体
# 与 checks/ 四个域模块的返回契约。
REPRESENTATIVE_RESULT_CALLS = (
    "check_governance_write_shapes",   # verify_workflow（guard 核心，FEAT-011）
    "check_evidence_completeness",     # checks/evidence_domain（Check 1）
    "check_risk_staleness",            # checks/risk_domain（Check 2）
    "check_loop_wiring_call_sites",    # checks/review_domain（Check 30b）
    "check_change_triage",             # checks/triage_domain（Check 32）
)

# ── Face 1: CLI dispatch key set (AST over main()) ───────────────────────────


def _engine_tree() -> ast.Module:
    return ast.parse(_ENGINE_PATH.read_text(encoding="utf-8"))


def extract_cli_dispatch() -> dict:
    """Extract the ``commands`` dispatch dict from ``main()`` via AST.

    Keys are taken from the literal dict only; a non-literal key or value
    (future engine change) fails loudly so the snapshot must be regenerated
    deliberately.
    """
    tree = _engine_tree()
    main_fn = next(
        (node for node in tree.body
         if isinstance(node, ast.FunctionDef) and node.name == "main"),
        None,
    )
    if main_fn is None:
        raise RuntimeError("verify_workflow.main() not found — engine drift")
    commands_node = None
    for node in ast.walk(main_fn):
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(t, ast.Name) and t.id == "commands"
               for t in node.targets):
            commands_node = node.value
            break
    if not isinstance(commands_node, ast.Dict):
        raise RuntimeError(
            "main().commands is no longer a literal dict — engine drift")
    keys_by_handler: dict[str, list[str]] = {}
    total_keys = 0
    for key_node, value_node in zip(commands_node.keys, commands_node.values):
        if not isinstance(key_node, ast.Constant) or not isinstance(
                key_node.value, str):
            raise RuntimeError(
                f"non-literal dispatch key at line {key_node.lineno}")
        if not isinstance(value_node, ast.Name):
            raise RuntimeError(
                f"non-Name handler for {key_node.value!r} — engine drift")
        keys_by_handler.setdefault(value_node.id, []).append(key_node.value)
        total_keys += 1
    alias_groups = {
        handler: sorted(keys)
        for handler, keys in sorted(keys_by_handler.items())
        if len(keys) > 1
    }
    return {
        "key_count": total_keys,
        "handler_count": len(keys_by_handler),
        "keys": sorted(k for ks in keys_by_handler.values() for k in ks),
        "alias_groups": alias_groups,
    }


# ── Face 2: Check ID segment list (banners ∪ product-gate registries) ────────

_BANNER_RE = re.compile(
    r"┌─ Check ([0-9]+[a-z]?)[：:]\s*(.*?)\s*─*\s*┐")
_REGISTRY_ASSIGNS = ("_PLUGIN_PRODUCT_CHECK_IDS", "_PRODUCT_GATE_LABELS")


def _segment_sort_key(segment_id: str):
    match = re.match(r"([0-9]+)([a-z]?)$", segment_id)
    if match is None:
        return (10 ** 9, segment_id)
    return (int(match.group(1)), match.group(2))


def extract_check_segments() -> dict:
    """Union of banner Check ids and product-gate registry Check ids.

    Banners (``┌─ Check NN: Title ─┐``) carry 69 ids; ``Check 30b`` prints
    its SKIP line inside Check 30c's box (no own banner) and is only
    declared in the two product-gate registries — the union is the real
    70-segment contract surface.
    """
    source = _ENGINE_PATH.read_text(encoding="utf-8")
    titles: dict[str, str] = {}
    for match in _BANNER_RE.finditer(source):
        titles[match.group(1)] = match.group(2).strip()
    registry_ids: set[str] = set()
    registry_labels: dict[str, str] = {}
    tree = _engine_tree()
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id in _REGISTRY_ASSIGNS
                   for t in node.targets):
            continue
        constants = []
        if isinstance(node.value, ast.Call) and isinstance(
                node.value.func, ast.Name) and node.value.func.id == "frozenset":
            constants = node.value.args
        elif isinstance(node.value, ast.Dict):
            constants = node.value.keys
        for item in constants:
            if isinstance(item, ast.Constant) and isinstance(
                    item.value, str) and item.value.startswith("Check "):
                registry_ids.add(item.value[len("Check "):])
        if isinstance(node.value, ast.Dict):
            for key_node, value_node in zip(node.value.keys, node.value.values):
                if (isinstance(key_node, ast.Constant)
                        and isinstance(key_node.value, str)
                        and isinstance(value_node, ast.Constant)
                        and isinstance(value_node.value, str)
                        and key_node.value.startswith("Check ")):
                    registry_labels[key_node.value[len("Check "):]] = \
                        value_node.value
    for segment_id in registry_ids:
        titles.setdefault(segment_id, registry_labels.get(segment_id, ""))
    ordered = sorted(titles, key=_segment_sort_key)
    return {
        "count": len(ordered),
        "ids": ordered,
        "titles": {sid: titles[sid] for sid in ordered},
    }


# ── Face 3: Result dict shapes (live invocation, key surface + types) ────────


def type_signature(value, depth: int = 0):
    """Recursive key-surface + type-name signature of a Result dict.

    Sequences collapse to a ``list``/``tuple``/``set`` marker (element
    payloads are state-dependent — e.g. a stale-risk list is empty or not
    with governance state, and the guard issue ELEMENT shape is pinned by
    the guard output face instead). Dict key surfaces are pinned at any
    depth because check functions build them from literals.
    """
    if isinstance(value, bool):  # bool is an int subclass — test first
        return "bool"
    if isinstance(value, dict):
        if depth >= 4:
            return "dict"
        return {
            "$dict": {
                str(key): type_signature(item, depth + 1)
                for key, item in value.items()
            },
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return {"$seq": type(value).__name__}
    return type(value).__name__


def _call_representative(name: str):
    function = getattr(vw, name, None)
    if function is None or not callable(function):
        raise RuntimeError(
            f"representative Result constructor {name!r} missing — "
            "engine drift")
    return function()


def extract_result_shapes() -> dict:
    """Invoke each representative check function and sign its Result dict."""
    shapes = {}
    for name in REPRESENTATIVE_RESULT_CALLS:
        shapes[name] = type_signature(_call_representative(name))
    return shapes


# ── Face 4: governance-write-guard output pin (FEAT-017 R0 F-2 收编) ────────
#
# Deterministic fixtures (temp dirs, zero real-environment contact):
#   A empty host        → all four faces SKIPPED → ``Result: PASS`` exit 0
#   B malformed tracker → FAIL face with issue lines + 期望列形 → exit 1
# Markers below are DERIVED from the observed output (prefixes cut from real
# lines), so any wording/format drift regenerates a different pin and the
# differential harness reports it.

_MALFORMED_TRACKER = (
    "# Plan Tracker (contract-matrix fixture)\n"
    "\n"
    "## 当前活跃事项\n"
    "\n"
    "| ID | 优先级 | 任务 | 状态 |\n"
    "|---|---|---|---|\n"
    "| **P0** | **P0** | FIX-999 | 演示用畸形行 | |\n"
)

_WELLFORMED_TRACKER = (
    "# Plan Tracker (contract-matrix fixture)\n"
    "\n"
    "## 当前活跃事项\n"
    "\n"
    "| ID | 优先级 | 任务 | 状态 |\n"
    "|---|---|---|---|\n"
    "| **P1** | FX-800 | 合规演示行 | ✅ 完成 (演示) |\n"
)

_GUARD_FIXTURE_BASE = Path(tempfile.gettempdir()) / "spg-contract-matrix-guard"


def _ensure_guard_fixtures() -> tuple[Path, Path, Path]:
    pass_fixture = _GUARD_FIXTURE_BASE / "pass-host"
    fail_fixture = _GUARD_FIXTURE_BASE / "fail-host"
    wellformed_fixture = _GUARD_FIXTURE_BASE / "wellformed-host"
    shutil.rmtree(_GUARD_FIXTURE_BASE, ignore_errors=True)
    pass_fixture.mkdir(parents=True)
    (fail_fixture / ".governance").mkdir(parents=True)
    (fail_fixture / ".governance" / "plan-tracker.md").write_text(
        _MALFORMED_TRACKER, encoding="utf-8")
    (wellformed_fixture / ".governance").mkdir(parents=True)
    (wellformed_fixture / ".governance" / "plan-tracker.md").write_text(
        _WELLFORMED_TRACKER, encoding="utf-8")
    return pass_fixture, fail_fixture, wellformed_fixture


def run_guard(project_root: Path) -> dict:
    """Real subprocess run of governance-write-guard against a fixture."""
    completed = subprocess.run(
        [sys.executable, str(_ENGINE_PATH),
         "--project-root", str(project_root),
         "governance-write-guard"],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=120, check=False, cwd=str(_REPO_ROOT),
    )
    return {
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _count_free(fragment: str) -> str:
    """Escape a literal fragment and free its digit runs (``2`` → ``\\d+``)."""
    return re.sub(r"\d+", lambda _m: r"\d+", re.escape(fragment))


def derive_guard_output_pin() -> dict:
    """Run all three fixtures and derive the guard's output contract markers."""
    pass_fixture, fail_fixture, wellformed_fixture = _ensure_guard_fixtures()
    pass_run = run_guard(pass_fixture)
    fail_run = run_guard(fail_fixture)
    wellformed_run = run_guard(wellformed_fixture)

    pass_lines = [line for line in pass_run["stdout"].splitlines() if line]
    fail_lines = [line for line in fail_run["stdout"].splitlines() if line]
    wellformed_lines = [
        line for line in wellformed_run["stdout"].splitlines() if line
    ]
    header = next(
        (line for line in pass_lines
         if line.startswith("=== Governance Write Guard")), None)
    if header is None:
        raise RuntimeError("guard header line not found — engine drift")
    face_re = re.compile(r"^  \[(PASS|FAIL|SKIPPED)\] (.+) — \d+ issue\(s\)$")
    pass_faces = [face_re.match(line) for line in pass_lines]
    face_labels = [m.group(2) for m in pass_faces if m]
    if not face_labels:
        raise RuntimeError("guard face lines not parseable — engine drift")
    result_pass = next(
        (line for line in pass_lines if line.startswith("Result: PASS")), None)
    result_fail = next(
        (line for line in fail_lines if line.startswith("Result: FAIL")), None)
    if result_pass is None or result_fail is None:
        raise RuntimeError("guard Result lines not found — engine drift")
    fail_prefix_match = re.match(r"^(Result: FAIL — )\d+", result_fail)
    if fail_prefix_match is None:
        raise RuntimeError("guard FAIL Result format drifted")
    issue_match = re.match(r"^(    - )", next(
        line for line in fail_lines if line.startswith("    - ")))
    expected_match = re.match(r"^(      期望列形: )", next(
        line for line in fail_lines if "期望列形: " in line))
    all_face_lines = pass_lines + fail_lines + wellformed_lines
    statuses = sorted({
        m.group(1)
        for m in (face_re.match(line) for line in all_face_lines) if m
    })
    if "PASS" not in statuses or "FAIL" not in statuses or \
            "SKIPPED" not in statuses:
        raise RuntimeError(
            f"guard fixtures must elicit all three face statuses, saw "
            f"{statuses} — fixture or engine drift")
    face_regex = (
        "^  \\[(" + "|".join(statuses) + ")\\] .+"
        + _count_free(" — 0 issue(s)") + "$"
    )
    return {
        "command": "verify_workflow.py governance-write-guard",
        "fixture_strategy": (
            "deterministic temp-dir fixtures: empty host (all SKIPPED → "
            "PASS/exit 0) + malformed plan-tracker row (FAIL/exit 1) + "
            "well-formed plan-tracker (PASS face/exit 0)"),
        "header_line": header,
        "face_line_regex": face_regex,
        "face_labels": face_labels,
        "issue_line_prefix": issue_match.group(1),
        "issue_line_regex": r"^    - (?:L\d+ )?.+$",
        "expected_line_prefix": expected_match.group(1),
        "result_pass_line": result_pass,
        "result_fail_prefix": fail_prefix_match.group(1),
        "result_fail_regex": "^" + re.escape(fail_prefix_match.group(1))
        + r"\d+ issue\(s\)。[\s\S]*$",
        "exit_codes": {
            "pass_fixture": pass_run["exit_code"],
            "fail_fixture": fail_run["exit_code"],
            "wellformed_fixture": wellformed_run["exit_code"],
        },
    }


# ── Face assembly, snapshot build/load, differential harness ─────────────────


def extract_contract_faces() -> dict:
    """All four contract faces — deterministic, metadata-free."""
    return {
        "cli_dispatch": extract_cli_dispatch(),
        "check_segments": extract_check_segments(),
        "result_shapes": extract_result_shapes(),
        "guard_output_pin": derive_guard_output_pin(),
    }


def _git_head() -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(_REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=15, check=False,
        )
        if completed.returncode == 0:
            return completed.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "unknown"


def build_snapshot() -> dict:
    """Contract faces + generation provenance (metadata is never compared)."""
    return {
        "schema": SNAPSHOT_SCHEMA,
        "task": TASK_ID,
        "generated": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(
                timespec="seconds"),
            "git_head": _git_head(),
            "python": {
                "family": f"{sys.version_info.major}.{sys.version_info.minor}",
                "implementation": sys.implementation.name,
                "version": sys.version.split()[0],
                "platform": sys.platform,
            },
            "generator_relpath": "skills/software-project-governance/infra/"
                                 "contract_matrix/generator.py",
        },
        "python_family_pins": PYTHON_FAMILY_PINS,
        "freeze_point": FREEZE_POINT,
        "faces": extract_contract_faces(),
        "reference": {
            "description": (
                "Non-asserted human-review material: raw guard fixture "
                "samples are regenerated into golden_samples.txt via "
                "--golden; snapshot equality covers faces/ only."),
        },
    }


def load_snapshot(path: Path = SNAPSHOT_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_snapshot(snapshot: dict, path: Path = SNAPSHOT_PATH) -> None:
    path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8", newline="\n",
    )


def _dict_drift(path: str, current, stored, drifts: list[str]) -> None:
    if type(current) is not type(stored):
        drifts.append(f"{path}: type {type(current).__name__} != "
                      f"{type(stored).__name__}")
        return
    if isinstance(current, dict):
        for key in sorted(set(current) | set(stored)):
            if key not in current:
                drifts.append(f"{path}.{key}: missing in current "
                              "(engine removed a contract entry)")
            elif key not in stored:
                drifts.append(f"{path}.{key}: not in snapshot "
                              "(engine added a contract entry)")
            else:
                _dict_drift(f"{path}.{key}", current[key], stored[key],
                            drifts)
    elif isinstance(current, list):
        if current != stored:
            drifts.append(f"{path}: list changed "
                          f"(current={current!r}, snapshot={stored!r})")
    elif current != stored:
        drifts.append(f"{path}: {current!r} != snapshot {stored!r}")


def diff_faces(current: dict, stored: dict) -> list[str]:
    """Differential harness core — list every contract-face drift."""
    drifts: list[str] = []
    _dict_drift("faces", current, stored, drifts)
    return drifts


def check_against_snapshot(path: Path = SNAPSHOT_PATH) -> list[str]:
    """Extract now and diff against the stored faces (harness entry)."""
    stored = load_snapshot(path)
    if stored.get("schema") != SNAPSHOT_SCHEMA:
        return [f"snapshot schema drift: {stored.get('schema')!r} != "
                f"{SNAPSHOT_SCHEMA!r}"]
    return diff_faces(extract_contract_faces(), stored.get("faces", {}))


# ── Golden samples (human-review sidecar, §10 acceptance ③) ─────────────────

_GOLDEN_COMMANDS = (
    ("guard fixture A — empty host (deterministic)",
     ["--project-root", "<pass-fixture>", "governance-write-guard"]),
    ("guard fixture B — malformed plan-tracker (deterministic)",
     ["--project-root", "<fail-fixture>", "governance-write-guard"]),
    ("verify — plugin asset verification (deterministic)",
     ["verify"]),
    ("stages — stage catalog listing (deterministic)",
     ["stages"]),
    ("check-governance summary — empty host fixture (deterministic)",
     ["--project-root", "<pass-fixture>", "check-governance",
      "--summary-only", "--level", "lightweight"]),
)


def write_golden_samples(path: Path = GOLDEN_PATH) -> list[str]:
    """Run the representative sample commands, record outputs for review."""
    pass_fixture, fail_fixture, _wellformed = _ensure_guard_fixtures()
    fixture_map = {"<pass-fixture>": str(pass_fixture),
                   "<fail-fixture>": str(fail_fixture)}
    sections = []
    for title, argv in _GOLDEN_COMMANDS:
        resolved = [fixture_map.get(part, part) for part in argv]
        completed = subprocess.run(
            [sys.executable, str(_ENGINE_PATH)] + resolved,
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=300, check=False, cwd=str(_REPO_ROOT),
        )
        sections.append(
            f"### {title}\n"
            f"command: python verify_workflow.py "
            f"{' '.join(resolved[1:] if resolved[0].endswith('.py') else resolved)}\n"
            f"exit_code: {completed.returncode}\n"
            f"--- stdout ---\n{completed.stdout.rstrip()}\n"
        )
    header = (
        f"FEAT-020 golden samples — {TASK_ID} contract matrix human-review\n"
        f"sidecar (acceptance ③). Generated by generator.py --golden at\n"
        f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}.\n"
        "All five samples run against deterministic fixtures or static\n"
        "plugin assets (no live .governance state) — rerun --golden to\n"
        "compare. Tests do NOT byte-assert this file.\n\n"
    )
    path.write_text(header + "\n".join(sections), encoding="utf-8",
                    newline="\n")
    return sections


# ── CLI ──────────────────────────────────────────────────────────────────────


def _cmd_regen(_args: argparse.Namespace) -> int:
    save_snapshot(build_snapshot())
    print(f"snapshot regenerated: {SNAPSHOT_PATH}")
    return 0


def _cmd_check(_args: argparse.Namespace) -> int:
    drifts = check_against_snapshot()
    if drifts:
        print(f"CONTRACT MATRIX DRIFT — {len(drifts)} difference(s):")
        for drift in drifts:
            print(f"  - {drift}")
        print("Regenerate deliberately (generator.py --regen) and explain "
              "the contract change.")
        return 1
    print("contract matrix: current implementation matches snapshot "
          "(4 faces, zero drift)")
    return 0


def _cmd_self_check(_args: argparse.Namespace) -> int:
    first = extract_contract_faces()
    second = extract_contract_faces()
    first_bytes = json.dumps(first, ensure_ascii=False, sort_keys=True)
    second_bytes = json.dumps(second, ensure_ascii=False, sort_keys=True)
    if first != second or first_bytes != second_bytes:
        print("SELF-CHECK FAIL — two consecutive extractions differ")
        for drift in diff_faces(second, first):
            print(f"  - {drift}")
        return 1
    print(f"self-check: two consecutive extractions identical "
          f"({len(first_bytes)} bytes each, zero diff)")
    return 0


def _cmd_golden(_args: argparse.Namespace) -> int:
    sections = write_golden_samples()
    print(f"golden samples written: {GOLDEN_PATH} ({len(sections)} samples)")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="contract-matrix-generator",
        description="FEAT-020 contract matrix extractor / differential "
                    "harness (snapshot updates are explicit)",
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--regen", action="store_true",
        help="Regenerate snapshots.json from the current implementation "
             "(explicit update)")
    modes.add_argument(
        "--check", action="store_true",
        help="Diff current implementation against the stored snapshot "
             "(default mode; exit 1 on drift)")
    modes.add_argument(
        "--self-check", action="store_true",
        help="Extract twice and prove zero difference (determinism)")
    modes.add_argument(
        "--golden", action="store_true",
        help="Regenerate the golden_samples.txt human-review sidecar")
    args = parser.parse_args(argv)
    if args.regen:
        return _cmd_regen(args)
    if args.self_check:
        return _cmd_self_check(args)
    if args.golden:
        return _cmd_golden(args)
    return _cmd_check(args)


atexit.register(lambda: shutil.rmtree(_GUARD_FIXTURE_BASE, ignore_errors=True))


if __name__ == "__main__":
    raise SystemExit(main())
