"""ArchGuard ratchet gate — rules R1~R7 vs core/architecture-baseline.json.

FEAT-019 / AUDIT-150 §4 (REFACTOR-archguard-ratchet, evolution doc §4). This
module is the FATAL counterpart of the advisory Check 28 family: any ratchet
violation exits non-zero, so slice-merge regressions (main-file growth, new
reverse dependencies, print-orchestration growth, registration drift) break
the gate instead of merely being reported.

Bootstrap discipline (design review S5/BR-1): the ratchet command and the
baseline generator live HERE, in an independent module — never inside
verify_workflow.py. The engine only wires the dispatch entry; R1's anchor is
generated AFTER that wiring so the gate is born green (no day-one red CI),
and the self-inclusion is registered as an expiring exemption.

Machine-judged rules (each has a negative-control test):

  R1  main-file LOC budget        physical lines (ReadAllLines caliber) ≤
                                  baseline anchor; only-down (fatal)
  R2  reverse-dependency ban      zero NEW ``import verify_workflow`` /
                                  ``_vw()`` sites; legacy sites ride in a
                                  per-(file, kind) count inventory whose
                                  entries only ever shrink (fatal)
  R3  layer dependency matrix     §3.2 enumeration (12 edges — the count is
                                  a derived assertion, W1 guard) + no cycle
                                  (iterative Tarjan SCC) + no forbidden edge
                                  among managed modules (fatal)
  R4  print orchestration         engine Call(print) attributed to the
                                  enclosing function; per-function and total
                                  counts only-down (fatal)
  R5  registration integrity      live CLI dispatch keys and Check segment
                                  IDs == FEAT-020 contract-matrix snapshot
                                  (consumed via its own extractors — never
                                  copied); snapshot missing → SKIP+disclose
  R6  startup budget              cold-import module count + import-set hash
                                  recorded; wall clock reported; NO threshold
                                  in this slice (FEAT-018 tolerance table
                                  fills it, then the face tightens)
  R7  reproducible generation     baseline regeneration is deterministic —
                                  double regen is byte-identical AND the
                                  committed baseline equals a fresh regen
                                  (git_head excluded). A stale/hand-edited
                                  baseline fails until ``--regen`` reruns.

Ratchet flow (evolution §4.3): after any engine change, rerun
``--regen`` — the baseline auto-shrinks and only ever shrinks; hand-editing
the extraction zone is a violation (R7 catches it). The authored zone
(exemptions + r3 managed_modules) is carried over verbatim by regen.

Exit codes: ``archguard-ratchet`` exits 1 on any violation (fatal gate);
``--regen`` exits 0 after writing the baseline. A MISSING baseline is
fail-closed (exit 1 with a regen hint) — the R5 SKIP+disclose policy covers
only the FEAT-020 snapshot, not the baseline itself.

Usage:
    python skills/software-project-governance/infra/verify_workflow.py archguard-ratchet
    python skills/software-project-governance/infra/verify_workflow.py archguard-ratchet --regen

stdlib-only (facts §9.4); no ``verify_workflow`` import (R2 applies to this
module too — it is scanned like every other infra module).
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SCHEMA = "spg-architecture-baseline/1"
TASK_ID = "FEAT-019"
RULES_VERSION = 1

_HERE = Path(__file__).resolve().parent          # .../infra
_SKILL_ROOT = _HERE.parent                        # .../software-project-governance
ENGINE_REL = "infra/verify_workflow.py"
BASELINE_REL = "core/architecture-baseline.json"
CONTRACT_SNAPSHOT_REL = "infra/contract_matrix/snapshots.json"
SKILL_MD_REL = "SKILL.md"

# ── R3 layer matrix (evolution doc §3.2 — enumeration set is authoritative) ──

LAYERS: Tuple[str, ...] = ("L0", "L2", "L3", "L4", "L5", "L6")

# {L6→L5,L4,L3,L2,L0; L5→L4,L0; L4→L3,L2,L0; L3→L0; L2→L0} — exactly 12
# directed edges. 15 would be the complete 6-code-layer DAG (C(6,2)) and
# would wrongly admit L5→L3, L5→L2, L3→L2 (W1 — design-review AUDIT-150).
ALLOWED_EDGES: Tuple[Tuple[str, str], ...] = (
    ("L6", "L5"), ("L6", "L4"), ("L6", "L3"), ("L6", "L2"), ("L6", "L0"),
    ("L5", "L4"), ("L5", "L0"),
    ("L4", "L3"), ("L4", "L2"), ("L4", "L0"),
    ("L3", "L0"),
    ("L2", "L0"),
)
ASSERTED_EDGE_COUNT = 12

# Managed modules enter R3 scope at their slice's 接入日 (evolution §4.1 R3
# 存量政策). v1 admits only the ratchet itself; legacy modules stay on the
# R2 inventory until their strangler slice lands.
DEFAULT_MANAGED_MODULES: Dict[str, Dict[str, str]] = {
    "infra/archguard_ratchet.py": {
        "layer": "L5",
        "admitted_by": "FEAT-019",
        "note": "cross-cutting guard; CLI surface ≈ L5; internal imports: "
                "stdlib only + lazy contract_matrix consumer edge (unmanaged "
                "until REFACTOR-contract-layer admits it)",
    },
}

# Owner-task placeholders for the R2 inventory (design §4.3: every legacy
# violation carries a responsible-task placeholder name).
_OWNER_TASK_MAP: Tuple[Tuple[str, str], ...] = (
    ("checks/review_domain.py", "REFACTOR-migrate-review-domain"),
    ("checks/loop_runtime_claims", "REFACTOR-migrate-review-domain"),
    ("checks/", "REFACTOR-domains-batch1"),
    ("release/", "REFACTOR-domains-batch1"),
    ("loop_", "REFACTOR-domains-batch1"),
    ("contract_matrix/", "REFACTOR-contract-layer"),
)


def _owner_task_placeholder(rel_path: str) -> str:
    for needle, task in _OWNER_TASK_MAP:
        if needle in rel_path:
            return task
    return "REFACTOR-remaining"


# ── shared helpers ───────────────────────────────────────────────────────────


def physical_line_count(text: str) -> int:
    """Count physical lines the way .NET ReadAllLines does (facts §1.1).

    Splits on CRLF / LF / CR only; a trailing newline does not produce a
    phantom last line; an empty text is 0 lines. ``str.splitlines`` differs
    (it also splits on \\x0b, \\x0c, \\u2028 …), so the caliber is pinned
    here explicitly.
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if normalized.endswith("\n"):
        normalized = normalized[:-1]
    if normalized == "":
        return 0
    return len(normalized.split("\n"))


def _canonical_json_bytes(data) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n").encode("utf-8")


def _parse_semver(text: Optional[str]) -> Optional[Tuple[int, int, int]]:
    if not text:
        return None
    parts = text.strip().split(".")
    if len(parts) != 3:
        return None
    try:
        return tuple(int(p) for p in parts)  # type: ignore[return-value]
    except ValueError:
        return None


def read_skill_version(skill_root: Path) -> Optional[str]:
    """Plugin version from SKILL.md frontmatter (DEC-096 authority)."""
    path = skill_root / SKILL_MD_REL
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    in_front = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "---":
            if in_front:
                break
            in_front = True
            continue
        if in_front and stripped.startswith("version:"):
            return stripped.split(":", 1)[1].strip()
    return None


def _git_head(skill_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(skill_root), "rev-parse", "HEAD"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    if result.returncode != 0:
        return "unknown"
    head = result.stdout.strip()
    return head if head else "unknown"


# ── R1: main-file LOC budget ─────────────────────────────────────────────────


def measure_mainfile_loc(engine_path: Path) -> int:
    return physical_line_count(engine_path.read_text(encoding="utf-8"))


def check_r1(engine_path: Path, anchor_loc: int) -> List[dict]:
    current = measure_mainfile_loc(engine_path)
    if current <= anchor_loc:
        return []
    return [{
        "rule": "R1", "scope": "mainfile",
        "message": f"main-file LOC {current} > anchor {anchor_loc} "
                   f"(+{current - anchor_loc}) — ratchet is only-down; "
                   f"shrink the engine or regen after a sanctioned shrink",
        "excess_lines": current - anchor_loc,
        "current": current, "anchor": anchor_loc,
    }]


# ── R2: reverse-dependency ban ───────────────────────────────────────────────

R2_SCAN_EXCLUSIONS: Tuple[str, ...] = (
    "tests", "__pycache__", ".pytest_cache", "e2e",
)


def scan_reverse_dependencies(infra_dir: Path) -> Dict[Tuple[str, str], dict]:
    """AST-scan infra/**/*.py for engine back-references.

    Returns {(relpath, kind): {"count": n, "lines": [...]}} with kinds
    ``import_vw`` (both ``import verify_workflow`` and ``from
    verify_workflow import``), ``vw_def`` (``def _vw``) and ``vw_call``.
    Unparseable files surface as kind ``parse_error`` (fail-closed: an
    unscannable file could hide imports).
    """
    findings: Dict[Tuple[str, str], dict] = {}
    for py in sorted(infra_dir.rglob("*.py")):
        rel = py.relative_to(infra_dir)
        parts = rel.parts
        if rel.as_posix() == "verify_workflow.py":
            continue
        if any(part in R2_SCAN_EXCLUSIONS for part in parts):
            continue

        def _add(kind: str, line: int, key=rel.as_posix()) -> None:
            slot = findings.setdefault((key, kind), {"count": 0, "lines": []})
            slot["count"] += 1
            slot["lines"].append(line)

        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError) as exc:
            _add("parse_error", 0)
            findings[(rel.as_posix(), "parse_error")]["error"] = str(exc)
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "verify_workflow":
                        _add("import_vw", node.lineno)
            elif isinstance(node, ast.ImportFrom):
                if node.module == "verify_workflow":
                    _add("import_vw", node.lineno)
            elif isinstance(node, ast.FunctionDef) and node.name == "_vw":
                _add("vw_def", node.lineno)
            elif (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "_vw"):
                _add("vw_call", node.lineno)
    return findings


def check_r2(current: Dict[Tuple[str, str], dict], inventory: List[dict],
             version: Optional[Tuple[int, int, int]] = None) -> List[dict]:
    """Current sites must not exceed the per-(file, kind) baseline budget.

    Line-number drift inside a file is tolerated (edits above a legacy site
    shift its line); the ratchet semantic is the count monotone-non-increase
    (evolution §4.3 “基线清单长度单调不增”). Inventory entries carrying an
    already-expired ``expire_version`` contribute a zero budget.
    """
    violations: List[dict] = []
    for entry in inventory:
        if _entry_expired(entry, version):
            violations.append({
                "rule": "R2",
                "scope": f"reverse-dep:{entry['path']}:{entry['kind']}",
                "message": f"inventory exemption for {entry['path']} "
                           f"({entry['kind']}) expired at "
                           f"{entry.get('expire_version')} — sites are now "
                           f"unbudgeted; clean them up",
                "path": entry["path"], "kind": entry["kind"],
            })
    budget: Dict[Tuple[str, str], int] = {}
    for entry in inventory:
        if _entry_expired(entry, version):
            continue
        budget[(entry["path"], entry["kind"])] = int(entry["count"])
    for (path, kind), observed in sorted(current.items()):
        allowed = budget.get((path, kind), 0)
        if observed["count"] > allowed:
            violations.append({
                "rule": "R2", "scope": f"reverse-dep:{path}:{kind}",
                "message": f"{path}: {kind} sites {observed['count']} > "
                           f"budget {allowed} (+{observed['count'] - allowed}) "
                           f"at lines {observed['lines']}",
                "path": path, "kind": kind,
                "excess": observed["count"] - allowed,
                "lines": observed["lines"],
            })
    return violations


# ── R3: layer dependency matrix ──────────────────────────────────────────────


def check_r3(managed_modules: Dict[str, Dict[str, str]], infra_dir: Path) -> Tuple[List[dict], dict]:
    """Matrix integrity + forbidden edges + cycles among managed modules.

    Returns (violations, report). Edges targeting modules outside the
    managed set are disclosed (report only) — they become judged when their
    owning slice admits them (接入日).
    """
    violations: List[dict] = []
    if len(ALLOWED_EDGES) != ASSERTED_EDGE_COUNT:
        violations.append({
            "rule": "R3", "scope": "layer-matrix:integrity",
            "message": f"allowed-edge enumeration has {len(ALLOWED_EDGES)} "
                       f"entries, asserted {ASSERTED_EDGE_COUNT} (evolution "
                       f"§3.2 W1 guard)",
        })
    allowed = set(ALLOWED_EDGES)

    def _module_name(rel: str) -> str:
        """Rel-to-skill-root path → importable dotted name (infra-relative).

        ``infra/archguard_ratchet.py`` → ``archguard_ratchet``;
        ``infra/checks/review_domain.py`` → ``checks.review_domain``.
        """
        no_ext = rel[:-3] if rel.endswith(".py") else rel
        parts = [p for p in no_ext.replace("\\", "/").split("/")]
        if parts and parts[0] == "infra":
            parts = parts[1:]
        return ".".join(parts)

    rel_to_module = {rel: _module_name(rel) for rel in managed_modules}
    edges: List[Tuple[str, str, int]] = []
    unmanaged_targets: List[str] = []
    for rel, info in sorted(managed_modules.items()):
        layer = info.get("layer", "")
        if layer not in LAYERS:
            violations.append({
                "rule": "R3", "scope": f"layer-assign:{rel}",
                "message": f"{rel} assigned unknown layer {layer!r} "
                           f"(expected one of {LAYERS})",
            })
            continue
        path = infra_dir.parent / rel
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError) as exc:
            violations.append({
                "rule": "R3", "scope": f"layer-scan:{rel}",
                "message": f"{rel}: cannot parse for import scan: {exc}",
            })
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                targets = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                targets = [node.module] if node.module else []
            else:
                continue
            for name in targets:
                if not name:
                    continue
                target_rel = None
                for m_rel, m_mod in rel_to_module.items():
                    if name == m_mod or name.startswith(m_mod + "."):
                        target_rel = m_rel
                        break
                if target_rel is None:
                    root_pkg = name.split(".")[0]
                    if root_pkg not in sys.stdlib_module_names:
                        unmanaged_targets.append(f"{rel}:{node.lineno}:{name}")
                    continue
                if target_rel == rel:
                    continue
                edges.append((rel, target_rel, node.lineno))

    for src, dst, line in edges:
        src_layer = managed_modules[src].get("layer", "")
        dst_layer = managed_modules[dst].get("layer", "")
        if (src_layer, dst_layer) not in allowed:
            violations.append({
                "rule": "R3", "scope": f"layer-edge:{src}->{dst}",
                "message": f"forbidden layer edge {src_layer}→{dst_layer}: "
                           f"{src} imports {dst} (line {line}) — allowed "
                           f"matrix is §3.2's 12-edge enumeration",
                "src": src, "dst": dst, "line": line,
            })

    # Iterative Tarjan SCC over the managed-module graph.
    graph: Dict[str, List[str]] = {rel: [] for rel in managed_modules}
    for src, dst, _ in edges:
        graph[src].append(dst)
    index_of: Dict[str, int] = {}
    lowlink: Dict[str, int] = {}
    on_stack: Dict[str, bool] = {}
    stack: List[str] = []
    counter = [0]
    sccs: List[List[str]] = []

    for start in sorted(graph):
        if start in index_of:
            continue
        work = [(start, iter(graph[start]))]
        index_of[start] = lowlink[start] = counter[0]
        counter[0] += 1
        stack.append(start)
        on_stack[start] = True
        while work:
            node, it = work[-1]
            advanced = False
            for nxt in it:
                if nxt not in graph:
                    continue
                if nxt not in index_of:
                    index_of[nxt] = lowlink[nxt] = counter[0]
                    counter[0] += 1
                    stack.append(nxt)
                    on_stack[nxt] = True
                    work.append((nxt, iter(graph[nxt])))
                    advanced = True
                    break
                if on_stack.get(nxt):
                    lowlink[node] = min(lowlink[node], index_of[nxt])
            if advanced:
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                lowlink[parent] = min(lowlink[parent], lowlink[node])
            if lowlink[node] == index_of[node]:
                component = []
                while True:
                    member = stack.pop()
                    on_stack[member] = False
                    component.append(member)
                    if member == node:
                        break
                sccs.append(sorted(component))

    for component in sccs:
        if len(component) > 1:
            violations.append({
                "rule": "R3", "scope": "layer-cycle",
                "message": "import cycle among managed modules: "
                           + " -> ".join(component + [component[0]])
                           + " (DAG assertion, evolution §3.2)",
                "modules": component,
            })

    report = {
        "managed_modules": len(managed_modules),
        "managed_edges": len(edges),
        "scc_count": len(sccs),
        "max_scc_size": max((len(c) for c in sccs), default=0),
        "unmanaged_target_refs": sorted(set(unmanaged_targets)),
    }
    return violations, report


# ── R4: print orchestration budget ───────────────────────────────────────────


def count_print_calls(engine_path: Path) -> Dict[str, object]:
    """Count Call(print) attributed to the enclosing (qualified) function.

    Module-level calls are attributed to ``<module>``. Nested functions get
    ``outer.inner`` names (evolution §4.1 R4: 巨石内 print 按来源计数).
    """
    tree = ast.parse(engine_path.read_text(encoding="utf-8"))
    counts: Dict[str, int] = {}

    def visit(node: ast.AST, owner: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = child.name if owner == "<module>" else f"{owner}.{child.name}"
                counts.setdefault(name, 0)
                visit(child, name)
                continue
            if (isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Name)
                    and child.func.id == "print"):
                counts[owner] = counts.get(owner, 0) + 1
            visit(child, owner)

    visit(tree, "<module>")
    counts = {k: v for k, v in counts.items() if v > 0 or k == "<module>"}
    return {"total": sum(counts.values()), "per_function": counts}


def check_r4(current: Dict[str, object], baseline: Dict[str, object]) -> List[dict]:
    violations: List[dict] = []
    base_total = int(baseline.get("total", 0))
    cur_total = int(current["total"])  # type: ignore[arg-type]
    if cur_total > base_total:
        violations.append({
            "rule": "R4", "scope": "print:total",
            "message": f"engine print total {cur_total} > baseline "
                       f"{base_total} (+{cur_total - base_total}) — "
                       f"orchestration output belongs to the render layer",
            "current": cur_total, "baseline": base_total,
        })
    base_fn = baseline.get("per_function", {}) or {}
    cur_fn = current["per_function"]  # type: ignore[assignment]
    for fn, count in sorted(cur_fn.items()):  # type: ignore[union-attr]
        allowed = int(base_fn.get(fn, 0))
        if count > allowed:
            violations.append({
                "rule": "R4", "scope": f"print:{fn}",
                "message": f"{fn}: print calls {count} > baseline {allowed} "
                           f"(+{count - allowed})",
                "current": count, "baseline": allowed,
            })
    return violations


# ── R5: registration integrity (consumes the FEAT-020 snapshot) ─────────────


def r5_live_faces(infra_dir: Path) -> Dict[str, List[str]]:
    """Live CLI dispatch keys + Check segment IDs via FEAT-020's extractors.

    Lazy import keeps this module light (and avoids an import cycle when
    verify_workflow imports this module at engine start). Consuming the
    generator's extractors — not copying them — is the packet contract.
    """
    if str(infra_dir) not in sys.path:
        sys.path.insert(0, str(infra_dir))
    from contract_matrix import generator as cmg  # noqa: PLC0415 (deliberate)

    dispatch = cmg.extract_cli_dispatch()
    segments = cmg.extract_check_segments()
    return {"cli_keys": list(dispatch["keys"]),
            "segment_ids": list(segments["ids"])}


def check_r5(skill_root: Path,
             snapshot_path: Optional[Path] = None) -> Tuple[List[dict], dict]:
    if snapshot_path is None:
        snapshot_path = skill_root / CONTRACT_SNAPSHOT_REL
    if not snapshot_path.is_file():
        return [], {
            "status": "SKIP",
            "reason": f"{CONTRACT_SNAPSHOT_REL} missing — FEAT-020 face is "
                      f"not frozen in this tree; disclosed, not failed "
                      f"(packet: 缺失时 SKIP+披露，不误报)",
        }
    live = r5_live_faces(skill_root / "infra")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    frozen_keys = set(snapshot["faces"]["cli_dispatch"]["keys"])
    frozen_ids = set(snapshot["faces"]["check_segments"]["ids"])
    live_keys = set(live["cli_keys"])
    live_ids = set(live["segment_ids"])
    violations: List[dict] = []
    removed = sorted(frozen_keys - live_keys)
    added = sorted(live_keys - frozen_keys)
    if removed:
        violations.append({
            "rule": "R5", "scope": "cli_dispatch",
            "message": "frozen CLI keys missing from live dispatch: "
                       f"{removed} — removal is a contract break",
            "keys": removed,
        })
    if added:
        violations.append({
            "rule": "R5", "scope": "cli_dispatch",
            "message": "live dispatch keys not in the frozen snapshot: "
                       f"{added} — deliberate contract changes must "
                       f"regenerate the FEAT-020 snapshot (its generator "
                       f"--regen) and bump the frozen count in review",
            "keys": added,
        })
    removed_ids = sorted(frozen_ids - live_ids)
    added_ids = sorted(live_ids - frozen_ids)
    if removed_ids or added_ids:
        violations.append({
            "rule": "R5", "scope": "check_segments",
            "message": "Check segment drift vs frozen snapshot: "
                       f"missing={removed_ids} added={added_ids}",
            "missing": removed_ids, "added": added_ids,
        })
    report = {
        "status": "PASS" if not violations else "FAIL",
        "live_cli_keys": len(live_keys), "frozen_cli_keys": len(frozen_keys),
        "live_segments": len(live_ids), "frozen_segments": len(frozen_ids),
    }
    return violations, report


# ── R6: startup budget (collection + comparison frame, no threshold yet) ─────


@lru_cache(maxsize=4)
def measure_cold_import(infra_dir_str: str) -> Optional[dict]:
    """Cold-import the engine in an isolated subprocess; deterministic faces.

    Persisted faces (import_count / import_set_sha256) are same-interpreter
    deterministic; wall_ms is report-only (FEAT-018 fills the tolerance
    table, then this face tightens — never fatal in this slice).
    """
    probe = (
        "import sys, json; sys.path.insert(0, {path!r}); "
        "import verify_workflow; print(json.dumps(sorted(sys.modules)))"
    ).format(path=infra_dir_str)
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
        "interpreter_family": f"{sys.version_info.major}.{sys.version_info.minor}",
    }


# ── exemptions ───────────────────────────────────────────────────────────────


def _entry_expired(entry: dict,
                   version: Optional[Tuple[int, int, int]] = None) -> bool:
    """An exemption/inventory entry is expired once current ≥ expire_version.

    A missing/unparseable ``expire_version`` never expires. An unreadable
    current version keeps the entry ACTIVE (suppression fail-safe; the
    unreadability itself is disclosed by apply_exemptions).
    """
    expire = _parse_semver(entry.get("expire_version"))
    if expire is None:
        return False
    if version is None:
        return False
    return version >= expire


def apply_exemptions(violations: List[dict], exemptions: List[dict],
                     skill_root: Path) -> Tuple[List[dict], List[dict]]:
    """Suppress violations covered by ACTIVE exemptions; tag expired ones.

    R1 exemptions may carry ``allowance_lines``: the finding is suppressed
    only while the excess stays within the allowance (teeth). Returns
    (effective_violations, disclosures).
    """
    version = _parse_semver(read_skill_version(skill_root))
    disclosures: List[dict] = []
    if version is None:
        disclosures.append({
            "kind": "version-unreadable",
            "message": "SKILL.md frontmatter version unreadable — "
                       "exemption expiry cannot be judged; all exemptions "
                       "treated as ACTIVE (disclosed, fail-safe for "
                       "suppression but never silently fatal)",
        })
    effective: List[dict] = []
    for violation in violations:
        matched: Optional[dict] = None
        expired_match: Optional[dict] = None
        for entry in exemptions:
            if entry.get("rule") != violation.get("rule"):
                continue
            if entry.get("scope") != violation.get("scope"):
                continue
            if _entry_expired(entry, version):
                expired_match = entry
                break
            matched = entry
            break
        if expired_match is not None:
            violation = dict(violation)
            violation["exemption"] = "EXPIRED:{}".format(
                expired_match.get("expire_version"))
            effective.append(violation)
            continue
        if matched is not None:
            allowance = matched.get("allowance_lines")
            excess = violation.get("excess_lines")
            if allowance is not None and excess is not None:
                if excess <= int(allowance):
                    disclosures.append({
                        "kind": "exemption-applied",
                        "message": f"{violation['rule']}:{violation['scope']} "
                                   f"suppressed by active exemption "
                                   f"(dec {matched.get('dec')}, expires "
                                   f"{matched.get('expire_version')}, "
                                   f"allowance {allowance})",
                    })
                    continue
                violation = dict(violation)
                violation["exemption"] = (
                    f"OVER-ALLOWANCE:{excess}>{allowance}")
            else:
                disclosures.append({
                    "kind": "exemption-applied",
                    "message": f"{violation['rule']}:{violation['scope']} "
                               f"suppressed by active exemption "
                               f"(dec {matched.get('dec')}, expires "
                               f"{matched.get('expire_version')})",
                })
                continue
        effective.append(violation)
    return effective, disclosures


# ── baseline build / load / check / regen ────────────────────────────────────

R1_DESIGN_ANCHOR_NOTE = (
    "facts-0.80.0 §3.1 design anchor was 24,252 (2026-09-09 HEAD); FEAT-019 "
    "packet mandates 实测为准 at regen time (intervening engine deltas: "
    "FIX-300 + FEAT-019 dispatch wiring). 只降不升 semantics unchanged; the "
    "wiring lines are registered as the R1 self-bootstrap exemption."
)

DEFAULT_EXEMPTIONS: List[dict] = [
    {
        "rule": "R1",
        "scope": "mainfile",
        "allowance_lines": 0,
        "reason": "FEAT-019 self-bootstrap RECORD: the anchor was generated "
                  "AFTER the ratchet's own dispatch wiring (18 lines: import "
                  "+ argparse registration + commands-dict entry), so the "
                  "wiring is already inside the anchor and the allowance is "
                  "deliberately ZERO — this entry is the DEC-tracked "
                  "disclosure, not a growth license (any excess still fails)",
        "dec": "DEC-183 / DEC-184 (FEAT-019 packet; evolution §4 S5)",
        "expire_version": "0.81.0",
    },
]


def build_baseline(skill_root: Path,
                   existing: Optional[dict] = None) -> dict:
    """Compute the full baseline from the current tree (deterministic).

    ``generated.git_head`` is the only commit-varying field (R7 strips it
    before comparing). The authored zone (exemptions, r3 managed_modules)
    is carried over from ``existing`` verbatim so regen never silently
    drops governance data.
    """
    existing = existing or {}
    infra_dir = skill_root / "infra"
    engine_path = skill_root / ENGINE_REL
    loc = measure_mainfile_loc(engine_path)
    r2_scan = scan_reverse_dependencies(infra_dir)
    prior_inventory = {
        (e["path"], e["kind"]): e
        for e in existing.get("r2_reverse_dependency", {}).get("inventory", [])
        if isinstance(e, dict) and "path" in e and "kind" in e
    }
    inventory = []
    for (path, kind), slot in sorted(r2_scan.items()):
        entry = {
            "path": path,
            "kind": kind,
            "count": slot["count"],
            "lines": sorted(slot["lines"]),
            "owner_task": _owner_task_placeholder(path),
        }
        prior = prior_inventory.get((path, kind))
        if prior and prior.get("expire_version") is not None:
            # Governance annotation (expiry fuse) survives regen — the
            # extraction zone may refresh counts/lines, never drop fuses.
            entry["expire_version"] = prior["expire_version"]
        inventory.append(entry)
    r4 = count_print_calls(engine_path)
    snapshot_present = (skill_root / CONTRACT_SNAPSHOT_REL).is_file()
    r6 = measure_cold_import(str(infra_dir))
    return {
        "schema": SCHEMA,
        "task": TASK_ID,
        "rules_version": RULES_VERSION,
        "generated": {
            "git_head": _git_head(skill_root),
            "loc_caliber": "physical lines (ReadAllLines equivalent — see "
                           "physical_line_count docstring, facts §1.1)",
        },
        "r1_mainfile_budget": {
            "path": ENGINE_REL,
            "anchor_loc": loc,
            "design_anchor_note": R1_DESIGN_ANCHOR_NOTE,
        },
        "r2_reverse_dependency": {
            "scan_root": "infra/",
            "scan_exclusions": list(R2_SCAN_EXCLUSIONS) + ["verify_workflow.py"],
            "inventory": inventory,
        },
        "r3_layer_matrix": {
            "source": "docs/requirements/architecture-evolution-0.80.0.md §3.2 "
                      "(enumeration set authoritative; count derived — W1)",
            "layers": list(LAYERS),
            "allowed_edges": [list(e) for e in ALLOWED_EDGES],
            "asserted_edge_count": ASSERTED_EDGE_COUNT,
            "managed_modules": dict(
                existing.get("r3_layer_matrix", {}).get("managed_modules")
                or DEFAULT_MANAGED_MODULES),
            "legacy_note": "verify_workflow.py + checks/* + release/* + "
                           "loop_* enter R3 at their slice's 接入日; until "
                           "then their reverse edges ride the R2 inventory",
        },
        "r4_print_orchestration": {
            "path": ENGINE_REL,
            "total": r4["total"],
            "per_function": r4["per_function"],
        },
        "r5_registration_integrity": {
            "consumes": CONTRACT_SNAPSHOT_REL + " (FEAT-020)",
            "faces": ["cli_dispatch.keys", "check_segments.ids"],
            "missing_snapshot_policy": "SKIP+disclose",
            "snapshot_present_at_regen": snapshot_present,
        },
        "r6_startup_budget": {
            "probe": "python -I -B -c 'import verify_workflow' (isolated)",
            "import_count": r6["import_count"] if r6 else None,
            "import_set_sha256": r6["import_set_sha256"] if r6 else None,
            "threshold": None,
            "note": "collection + comparison frame only; FEAT-018's "
                    "tolerance table fills threshold, then the face "
                    "tightens — advisory until then, never fatal in v1",
        },
        "exemptions": list(existing.get("exemptions") or DEFAULT_EXEMPTIONS),
    }


def load_baseline(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _strip_volatile(data: dict) -> dict:
    """Drop commit/platform-varying faces before the R7 stale comparison.

    ``generated.git_head`` varies per commit; ``r6_startup_budget``'s
    import_count/import_set_sha256 vary per interpreter family (CI 3.11 vs
    local 3.14) — R6 stays an advisory per-platform observation, so it is
    excluded from the reproducibility comparison rather than pinned
    (FEAT-020 pins interpreter families for its frozen faces; the ratchet
    does not need to freeze an advisory face).
    """
    stripped = json.loads(json.dumps(data))
    stripped.get("generated", {}).pop("git_head", None)
    stripped.pop("r6_startup_budget", None)
    return stripped


def check_r7(skill_root: Path, committed: Optional[dict]) -> Tuple[List[dict], dict]:
    """Generation reproducibility: double-regen identical + committed == fresh.

    A stale baseline (engine changed without --regen) or a hand-edited
    extraction zone fails here — this is the “机器生成禁手编” enforcement.
    """
    fresh_a = build_baseline(skill_root, committed)
    fresh_b = build_baseline(skill_root, committed)
    violations: List[dict] = []
    bytes_a = _canonical_json_bytes(fresh_a)
    bytes_b = _canonical_json_bytes(fresh_b)
    if bytes_a != bytes_b:
        violations.append({
            "rule": "R7", "scope": "baseline-determinism",
            "message": "two consecutive baseline regens differ — generator "
                       "has a nondeterministic face (R6 timing must never "
                       "be persisted)",
        })
    report = {"deterministic": bytes_a == bytes_b, "committed_compared": committed is not None}
    if committed is not None:
        committed_stripped = _strip_volatile(committed)
        fresh_stripped = _strip_volatile(fresh_a)
        if committed_stripped != fresh_stripped:
            violations.append({
                "rule": "R7", "scope": "baseline-stale",
                "message": "committed baseline differs from a fresh regen "
                           "(git_head excluded) — engine changed without "
                           "regen, or the extraction zone was hand-edited; "
                           "run: verify_workflow.py archguard-ratchet --regen",
            })
        report["committed_matches_fresh"] = (
            committed_stripped == fresh_stripped)
    return violations, report


def run_check(skill_root: Path, baseline_path: Path) -> dict:
    """Full R1~R7 evaluation. Returns a report; caller decides exit code."""
    committed = load_baseline(baseline_path)
    rules: Dict[str, dict] = {}
    all_violations: List[dict] = []
    if committed is None:
        return {
            "fatal": True,
            "baseline_missing": str(baseline_path),
            "violations": [{
                "rule": "R0", "scope": "baseline-missing",
                "message": f"baseline {baseline_path} missing — fail-closed; "
                           f"bootstrap with: verify_workflow.py "
                           f"archguard-ratchet --regen",
            }],
        }

    infra_dir = skill_root / "infra"
    engine_path = skill_root / ENGINE_REL

    v1 = check_r1(engine_path, int(committed["r1_mainfile_budget"]["anchor_loc"]))
    rules["R1"] = {"status": "PASS" if not v1 else "FAIL",
                   "anchor": committed["r1_mainfile_budget"]["anchor_loc"],
                   "current": measure_mainfile_loc(engine_path)}
    all_violations += v1

    current_r2 = scan_reverse_dependencies(infra_dir)
    version_now = _parse_semver(read_skill_version(skill_root))
    v2 = check_r2(current_r2,
                  committed["r2_reverse_dependency"]["inventory"],
                  version_now)
    rules["R2"] = {"status": "PASS" if not v2 else "FAIL",
                   "files": len(current_r2),
                   "sites": sum(s["count"] for s in current_r2.values()),
                   "inventory_sites": sum(int(e["count"]) for e in
                                          committed["r2_reverse_dependency"]["inventory"]
                                          if not _entry_expired(e, version_now))}
    all_violations += v2

    managed = committed["r3_layer_matrix"]["managed_modules"]
    v3, r3_report = check_r3(managed, infra_dir)
    rules["R3"] = {"status": "PASS" if not v3 else "FAIL", **r3_report}
    all_violations += v3

    r4_current = count_print_calls(engine_path)
    v4 = check_r4(r4_current, committed["r4_print_orchestration"])
    rules["R4"] = {"status": "PASS" if not v4 else "FAIL",
                   "total": r4_current["total"],
                   "baseline_total": committed["r4_print_orchestration"]["total"]}
    all_violations += v4

    v5, r5_report = check_r5(skill_root)
    rules["R5"] = {"status": r5_report.get("status", "PASS" if not v5 else "FAIL"),
                   **{k: v for k, v in r5_report.items() if k != "status"}}
    all_violations += v5

    r6_live = measure_cold_import(str(infra_dir))
    r6_base = committed.get("r6_startup_budget", {})
    if r6_live is None:
        rules["R6"] = {"status": "SKIP",
                       "reason": "cold-import probe failed in this "
                                 "environment — disclosed, not failed"}
    else:
        delta = r6_live["import_count"] - int(r6_base.get("import_count") or 0)
        rules["R6"] = {
            "status": "INFO",
            "import_count": r6_live["import_count"],
            "baseline_import_count": r6_base.get("import_count"),
            "delta": delta,
            "wall_ms": r6_live["wall_ms"],
            "threshold": r6_base.get("threshold"),
            "note": "advisory face — threshold lands with FEAT-018",
        }

    v7, r7_report = check_r7(skill_root, committed)
    rules["R7"] = {"status": "PASS" if not v7 else "FAIL", **r7_report}
    all_violations += v7

    effective, disclosures = apply_exemptions(
        all_violations, committed.get("exemptions", []), skill_root)

    return {
        "fatal": True,
        "baseline": str(baseline_path),
        "schema": committed.get("schema"),
        "rules_version": committed.get("rules_version"),
        "git_head": committed.get("generated", {}).get("git_head"),
        "rules": rules,
        "violations": effective,
        "raw_violations": len(all_violations),
        "disclosures": disclosures,
    }


def regen_baseline(skill_root: Path, baseline_path: Path) -> dict:
    existing = load_baseline(baseline_path) or {}
    data = build_baseline(skill_root, existing)
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _canonical_json_bytes(data)
    with open(baseline_path, "wb") as handle:
        handle.write(payload.replace(b"\r\n", b"\n"))
    return {"written": str(baseline_path), "bytes": len(payload),
            "data": data}


# ── CLI entry (dispatched from verify_workflow.py) ──────────────────────────


def cmd_archguard_ratchet(args) -> None:
    """``verify_workflow.py archguard-ratchet`` — fatal ratchet gate."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    skill_root = Path(getattr(args, "skill_root", None) or _SKILL_ROOT)
    baseline_arg = getattr(args, "baseline", None)
    baseline_path = (Path(baseline_arg) if baseline_arg
                     else skill_root / BASELINE_REL)
    print("\n=== ArchGuard Ratchet (FEAT-019 — fatal gate R1~R7) ===")
    if getattr(args, "regen", False):
        result = regen_baseline(skill_root, baseline_path)
        data = result["data"]
        print(f"  baseline regenerated: {result['written']} "
              f"({result['bytes']} bytes)")
        print(f"  R1 anchor loc      : {data['r1_mainfile_budget']['anchor_loc']}")
        print(f"  R2 inventory sites : "
              f"{sum(e['count'] for e in data['r2_reverse_dependency']['inventory'])}"
              f" across {len(data['r2_reverse_dependency']['inventory'])} "
              f"(path, kind) entries")
        print(f"  R4 print total     : {data['r4_print_orchestration']['total']}")
        print(f"  git head           : {data['generated']['git_head']}")
        print("  exemptions carried : "
              f"{len(data['exemptions'])} (authored zone preserved)")
        print("\nResult: REGENERATED (ratchet anchor re-anchored — only-down from here)\n")
        return

    report = run_check(skill_root, baseline_path)
    if report.get("baseline_missing"):
        print(f"  [R0] FAIL {report['violations'][0]['message']}")
        print("\nResult: FAIL (fatal — baseline missing)\n")
        sys.exit(1)

    for disclosure in report.get("disclosures", []):
        print(f"  [note] {disclosure['message']}")
    order = ("R1", "R2", "R3", "R4", "R5", "R6", "R7")
    for rule_id in order:
        info = report["rules"].get(rule_id, {})
        status = info.get("status", "?")
        if rule_id == "R1":
            detail = (f"mainfile loc {info.get('current')} ≤ anchor "
                      f"{info.get('anchor')} (only-down)")
        elif rule_id == "R2":
            detail = (f"reverse-dep sites {info.get('sites')} ≤ inventory "
                      f"{info.get('inventory_sites')} across {info.get('files')} "
                      f"files (monotone non-increase)")
        elif rule_id == "R3":
            detail = (f"matrix {len(ALLOWED_EDGES)} edges; managed "
                      f"{info.get('managed_modules')} modules, "
                      f"{info.get('managed_edges')} edges, SCC max "
                      f"{info.get('max_scc_size')}; unmanaged refs "
                      f"{len(info.get('unmanaged_target_refs', []))} disclosed")
        elif rule_id == "R4":
            detail = (f"print total {info.get('total')} ≤ baseline "
                      f"{info.get('baseline_total')} (per-function ratchet)")
        elif rule_id == "R5":
            detail = (f"cli keys {info.get('live_cli_keys')}/"
                      f"{info.get('frozen_cli_keys')} frozen, segments "
                      f"{info.get('live_segments')}/"
                      f"{info.get('frozen_segments')} frozen "
                      f"(consumes FEAT-020 snapshot)")
            if status == "SKIP":
                detail = info.get("reason", "snapshot unavailable")
        elif rule_id == "R6":
            if status == "SKIP":
                detail = info.get("reason", "cold-import probe unavailable")
            else:
                detail = (f"cold import {info.get('import_count')} modules "
                          f"(baseline {info.get('baseline_import_count')}, "
                          f"Δ{info.get('delta')}) wall {info.get('wall_ms')}ms "
                          f"— advisory; threshold lands with FEAT-018")
        else:
            detail = (f"regen deterministic={info.get('deterministic')}; "
                      f"committed==fresh {info.get('committed_matches_fresh', 'n/a')}")
        print(f"  [{rule_id}] {status}  {detail}")
    violations = report["violations"]
    for violation in violations[:40]:
        tag = ""
        if violation.get("exemption"):
            tag = f" [{violation['exemption']}]"
        print(f"  [VIOLATION] {violation['rule']} "
              f"{violation.get('scope', '')}: {violation['message']}{tag}")
    if len(violations) > 40:
        print(f"    ... and {len(violations) - 40} more")
    if violations:
        print(f"\nResult: FAIL ({len(violations)} violation(s)) — fatal ratchet gate\n")
        sys.exit(1)
    print(f"\nResult: PASS (0 violations; raw findings before exemptions: "
          f"{report.get('raw_violations', 0)}) — fatal gate green\n")
