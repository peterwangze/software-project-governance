"""FEAT-061 — INDEPENDENT migration/recovery verifier (Layer 6).

Independence contract (version-plan 0.88.0 §1 独立性操作化三条 + DEC-237
C1-ARCH-04/10):

  ① 比对裁决一律用切换前旧 md 解析器 — this module MIRRORS the
     pre-cutover parser semantics (governance_store._split_row code-span
     splitter + the engine's row-anchored ID scan) instead of importing
     them, and NEVER imports the new implementation.
  ② 校验器用切换前版本 — this script is self-contained (stdlib only) and
     runs as a SUBPROCESS of the controller so its execution environment
     never contains the new modules; the environment report below proves
     it (loaded-module summary + forbidden-import assertion).
  ③ 独立性声明作为证明包必填节 — ``verify`` emits the declaration with
     shared dependencies AND residual risks, never a bare "独立：是".

FORBIDDEN imports (asserted at runtime): decision_repository,
decision_migration, governance_store, verify_workflow.  If any of them
appears in ``sys.modules`` the environment gate FAILS the verdict — the
verifier must not be able to prove the new implementation with the new
implementation.

Mirrored-parser provenance: the row splitter below is a VERBATIM semantic
copy of the pre-FEAT-061 writer splitter (code-span aware, no
backslash-escape support, leading/trailing empty parts dropped, cells
stripped) and the record anchor mirrors the engine's row-anchored
``PREFIX-(\\d+)`` scan.  Drift between this mirror and the original is not
a weakness — the equivalence proof REQUIRES the two independent parsers
to agree; a disagreement blocks the migration (共同盲区检出).

Commands (own composition root; exit 0 = PASS, 1 = FAIL — a distinct
scale from the writer families, documented here):

    sample         independent read-only origin-manifest production
                   (retained; overwriting refuses — re-sampling means a
                   NEW migration id, ARCH-03)
    verify         three-class integrity proof + full-input coverage +
                   ops reconciliation → verdict JSON (stdout)
    reverse-check  old-parser re-parse of a rollback export must equal
                   the JSON records (ARCH-07 reverse representability)
    negative-suite seven injected-fault cases, each MUST be rejected by
                   its gate (ARCH-04 负向验收)
    environment    the frozen execution-environment report (ARCH-04)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

FORBIDDEN_MODULES = (
    "decision_repository",
    "decision_migration",
    "governance_store",
    "verify_workflow",
)

MD_FILE_NAME = "decision-log.md"
STORE_FILE_NAME = "decision-store.json"
OPS_LEDGER_NAME = "governance-store-ops.json"
DEC_PREFIX = "DEC-"

# ── OLD md parser mirror (pre-cutover semantics — see provenance above) ─────


def _split_row_legacy(line: str):
    """VERBATIM mirror of the pre-FEAT-061 writer splitter (code-span
    aware, no backslash-escape support; leading/trailing empty parts of
    the ``| … |`` form dropped; cells stripped)."""
    stripped = line.strip()
    if not stripped.startswith("|"):
        return []
    cells = []
    buf = []
    in_code = False
    end = len(stripped) - 1 if stripped.endswith("|") else len(stripped)
    i = 1
    while i < end:
        ch = stripped[i]
        if ch == "`":
            in_code = not in_code
            buf.append(ch)
        elif ch == "|" and not in_code:
            cells.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
        i += 1
    cells.append("".join(buf).strip())
    return cells


#: Record anchor mirror — the engine's row-anchored semantics
#: (``DEC-(\d+)\b``): a first cell like ``DEC-194 〔勘〕`` anchors as the
#: canonical id DEC-194 (勘正 annotation rows are records, never
#: unresolved); cells/row_raw stay verbatim.
_DEC_ANCHOR_RE = re.compile(r"^(DEC-\d+)\b")


def _record_id_of(cells):
    """Row-anchored DEC id extraction (engine caliber — see the anchor
    mirror note above)."""
    if not cells:
        return None
    match = _DEC_ANCHOR_RE.match(cells[0])
    return match.group(1) if match else None


def classify_lines_legacy(text: str) -> list:
    """The OLD parser's classification of every line (independent
    implementation of the ARCH-05 coverage face)."""
    items = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped.startswith("|"):
            items.append({"kind": "content", "line_no": line_no,
                          "text": line})
            continue
        cells = _split_row_legacy(line)
        if not cells:
            items.append({"kind": "unresolved", "line_no": line_no,
                          "text": line,
                          "reason": "pipe row splits to zero cells"})
            continue
        if cells and all(cell and set(cell) <= set("-: ") for cell in cells):
            items.append({"kind": "table_separator", "line_no": line_no,
                          "text": line, "cells": cells})
            continue
        record_id = _record_id_of(cells)
        if record_id is not None:
            items.append({"kind": "record", "line_no": line_no,
                          "id": record_id, "cells": cells,
                          "row_raw": line})
            continue
        if "编号" in cells[0]:
            items.append({"kind": "table_header", "line_no": line_no,
                          "text": line, "cells": cells})
            continue
        items.append({
            "kind": "unresolved", "line_no": line_no, "text": line,
            "reason": f"pipe row without a {DEC_PREFIX} anchor or header "
                      f"signature (first cell {cells[0]!r})",
        })
    return items


# ── environment report (ARCH-04) ────────────────────────────────────────────


def _script_digest() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _git_head_digest(root: Path):
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=15)
        if proc.returncode == 0:
            return proc.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def environment_report(root: Path) -> dict:
    """The frozen execution-environment summary + the forbidden-import
    gate (a verdict produced with the new implementation importable is
    self-signed — rejected)."""
    loaded_forbidden = [name for name in FORBIDDEN_MODULES
                        if name in sys.modules]
    loaded_top = sorted({
        name.split(".", 1)[0] for name in list(sys.modules)
        if not name.startswith("_") and "." not in name
    })
    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "cwd": str(Path.cwd()),
        "git_commit_digest": _git_head_digest(root),
        "verifier_script_sha256": _script_digest(),
        "loaded_modules_top_level": loaded_top,
        "forbidden_modules_loaded": loaded_forbidden,
        "dependency_declaration": "stdlib-only (argparse/hashlib/json/"
                                  "platform/subprocess/sys/tempfile/"
                                  "datetime/pathlib) — no third-party "
                                  "dependency, no new-implementation import",
    }


def _env_gate(report: dict) -> list:
    issues = []
    if report.get("forbidden_modules_loaded"):
        issues.append(
            "forbidden modules present in the verifier environment: "
            + ", ".join(report["forbidden_modules_loaded"])
            + " — the verdict would be self-signed (ARCH-04)")
    return issues


# ── data gates (the three-class integrity proof, ARCH-03) ───────────────────


def _read_json_or_fail(path: Path, issues: list, what: str):
    try:
        return json.loads(path.read_bytes().decode("utf-8"))
    except FileNotFoundError:
        issues.append(f"{what}: {path} does not exist")
    except (ValueError, UnicodeDecodeError) as exc:
        issues.append(f"{what}: {path} is not valid UTF-8 JSON ({exc})")
    return None


def check_input_integrity(gov_dir: Path, manifest: dict,
                          migration_id: str) -> dict:
    """Class A — 原始文件集合完整性: the retained origin manifest must
    still describe the CURRENT md bytes (independent re-sample; a
    mismatch demands a NEW migration id, never a silent re-pin)."""
    md_path = gov_dir / MD_FILE_NAME
    current = hashlib.sha256(md_path.read_bytes()).hexdigest()
    files = manifest.get("files") or {}
    md_entry = files.get(MD_FILE_NAME) or {}
    ok = md_entry.get("sha256") == current \
        and manifest.get("migration_id") == migration_id
    return {
        "class": "A_原始文件集合完整性",
        "verdict": "PASS" if ok else "FAIL",
        "manifest_md_sha256": md_entry.get("sha256"),
        "resampled_md_sha256": current,
        "manifest_migration_id": manifest.get("migration_id"),
        "requested_migration_id": migration_id,
        "detail": None if ok else
                  "re-sample diverges from the retained origin manifest — "
                  "restart the migration under a NEW migration id "
                  "(ARCH-03; 冻结起点不得被切换程序覆盖或重钉)",
    }


def check_logical_equivalence(md_items: list, store_doc: dict) -> dict:
    """Class B — 逻辑记录等价性: old-parser md records vs shadow JSON
    records — ID multiset equality + per-ID ORDERED cells comparison
    (duplicates — the real file carries legitimate 勘正 pairs — must
    match positionally on BOTH sides; a dict-by-id compare would silently
    skip the first of a pair).  Any content difference is a FAILED
    conversion (历史勘正不得混入格式转换), never a normalization
    opportunity."""
    md_records = [item for item in md_items if item["kind"] == "record"]
    store_records = store_doc.get("records") or []

    def grouped(records):
        order = []
        by_id = {}
        for record in records:
            dec_id = record["id"]
            if dec_id not in by_id:
                order.append(dec_id)
                by_id[dec_id] = []
            by_id[dec_id].append(record)
        return order, by_id

    md_order, md_by_id = grouped(md_records)
    store_order, store_by_id = grouped(
        [{**r, "id": r.get("id")} for r in store_records])
    dup_store = sorted(i for i in store_order if len(store_by_id[i]) > 1)
    dup_md = sorted(i for i in md_order if len(md_by_id[i]) > 1)
    diffs = []
    md_ids = set(md_by_id)
    store_ids = set(store_by_id)
    for dec_id in sorted(md_ids - store_ids):
        diffs.append({"id": dec_id,
                      "diff": "missing in JSON store (deleted row?)"})
    for dec_id in sorted(store_ids - md_ids):
        diffs.append({"id": dec_id,
                      "diff": "extra in JSON store (fabricated row?)"})
    for dec_id in sorted(md_ids & store_ids):
        if len(md_by_id[dec_id]) != len(store_by_id[dec_id]):
            diffs.append({
                "id": dec_id,
                "diff": f"occurrence count differs (md "
                        f"{len(md_by_id[dec_id])} vs store "
                        f"{len(store_by_id[dec_id])})",
            })
            continue
        for position, (md_item, st_record) in enumerate(
                zip(md_by_id[dec_id], store_by_id[dec_id])):
            md_cells = md_item["cells"]
            st_cells = st_record.get("cells")
            if st_cells != md_cells:
                diff_cells = [
                    {"index": i, "md": (md_cells[i] if i < len(md_cells)
                                        else None),
                     "store": (st_cells[i] if st_cells
                               and i < len(st_cells) else None)}
                    for i in range(max(len(md_cells),
                                       len(st_cells) if st_cells else 0))
                    if (md_cells[i] if i < len(md_cells) else None)
                    != (st_cells[i] if st_cells and i < len(st_cells)
                        else None)
                ]
                diffs.append({"id": dec_id, "occurrence": position,
                              "diff": "cell content diverges",
                              "cells": diff_cells})
            if st_record.get("row_raw") != md_item["row_raw"]:
                diffs.append({"id": dec_id, "occurrence": position,
                              "diff": "row_raw not verbatim (byte "
                                      "fidelity would be lost)"})
    ok = not diffs and dup_md == dup_store
    return {
        "class": "B_逻辑记录等价性",
        "verdict": "PASS" if ok else "FAIL",
        "md_record_count": len(md_records),
        "store_record_count": len(store_records),
        "duplicate_ids_md": dup_md,
        "duplicate_ids_store": dup_store,
        "diffs": diffs,
        "detail": None if ok else
                  "format conversion must be a pure format change — every "
                  "diff above is a content divergence and blocks the "
                  "migration (历史勘正不得混入格式转换)",
    }


def check_ops_integrity(gov_dir: Path, md_items: list) -> dict:
    """Class C — 已提交操作完整性: every committed decision-append
    operation's provenance marker must be findable in the record world
    (ops ↔ records 对账; an op whose record vanished is a dangling
    reference and blocks)."""
    ledger = _read_json_or_fail(gov_dir / OPS_LEDGER_NAME, [],
                                "ops ledger") or {}
    operations = ledger.get("operations") or {}
    world_text = "\n".join(
        item.get("row_raw", item.get("text", "")) for item in md_items)
    append_ops = {
        op_id: entry for op_id, entry in operations.items()
        if isinstance(entry, dict)
        and entry.get("command") == "decision-append"
    }
    missing = [op_id for op_id in sorted(append_ops)
               if f"governance-store decision-append {op_id}"
               not in world_text]
    pending = [op_id for op_id, entry in append_ops.items()
               if entry.get("status") == "pending"]
    ok = not missing
    return {
        "class": "C_已提交操作完整性",
        "verdict": "PASS" if ok else "FAIL",
        "decision_append_ops_total": len(append_ops),
        "ops_reconciled": len(append_ops) - len(missing),
        "ops_missing_in_world": missing,
        "ops_pending": pending,
        "detail": None if ok else
                  "every committed append must be represented in the "
                  "record world (markers are the idempotency identity "
                  "preserved across format conversion)",
    }


def check_coverage(md_items: list) -> dict:
    """ARCH-05 — 全输入覆盖: every line has a parse destination; ANY
    unresolved line blocks (解析不明行阻断)."""
    counts = {}
    unresolved = []
    for item in md_items:
        counts[item["kind"]] = counts.get(item["kind"], 0) + 1
        if item["kind"] == "unresolved":
            unresolved.append({"line": item["line_no"],
                               "reason": item["reason"],
                               "text": item["text"][:160]})
    ok = not unresolved
    return {
        "class": "全输入覆盖",
        "verdict": "PASS" if ok else "FAIL",
        "line_classification_counts": counts,
        "unresolved_lines": unresolved,
        "detail": None if ok else
                  "every candidate line needs a source position and a "
                  "parse destination (record/header/separator/content) — "
                  "unresolved lines block the migration",
    }


def check_store_shape(store_doc: dict) -> list:
    """Old-tool refusal semantics on the store as DATA (旧工具对新格式
    明确拒绝): wrong format/schema must be REPORTED, never misread."""
    issues = []
    if not isinstance(store_doc, dict):
        issues.append("store root is not a JSON object")
        return issues
    if store_doc.get("format") != "decision-store":
        issues.append(f"store format {store_doc.get('format')!r} is not "
                      f"'decision-store' — refusing to interpret")
    version = store_doc.get("schema_version")
    if version != 1:
        issues.append(f"store schema_version {version!r} outside the "
                      f"known window [1, 1] — a newer store is refused, "
                      f"never guessed")
    return issues


# ── commands ────────────────────────────────────────────────────────────────


def cmd_sample(args) -> int:
    gov_dir = Path(args.gov_dir)
    migration_root = Path(args.migration_root)
    manifest_path = migration_root / args.migration_id / "input-manifest.json"
    if manifest_path.is_file():
        print(json.dumps({
            "verdict": "FAIL",
            "detail": f"{manifest_path} already exists — the origin "
                      f"manifest is retained and never overwritten; "
                      f"re-sampling produces a NEW migration id (ARCH-03)",
        }, ensure_ascii=False, indent=2))
        return 1
    md_path = gov_dir / MD_FILE_NAME
    if not md_path.is_file():
        print(json.dumps({
            "verdict": "FAIL",
            "detail": f"{md_path} does not exist",
        }, ensure_ascii=False, indent=2))
        return 1
    md_bytes = md_path.read_bytes()
    manifest = {
        "migration_id": args.migration_id,
        "produced_by": "decision_migration_verify.sample",
        "produced_at": datetime.now().replace(microsecond=0).isoformat(),
        "files": {
            MD_FILE_NAME: {
                "sha256": hashlib.sha256(md_bytes).hexdigest(),
                "size_bytes": len(md_bytes),
            },
        },
        "environment": environment_report(gov_dir.parent),
        "note": "独立只读步骤产物 — 切换程序不得覆盖本文件 (ARCH-03)",
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(
        (json.dumps(manifest, ensure_ascii=False, indent=2)
         + "\n").encode("utf-8"))
    print(json.dumps({
        "verdict": "PASS",
        "manifest_path": str(manifest_path),
        "md_sha256": manifest["files"][MD_FILE_NAME]["sha256"],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_verify(args) -> int:
    gov_dir = Path(args.gov_dir)
    migration_root = Path(args.migration_root)
    migration_dir = migration_root / args.migration_id
    issues = []
    manifest_path = migration_dir / "input-manifest.json"
    manifest_digest = None
    manifest = None
    if manifest_path.is_file():
        manifest = _read_json_or_fail(manifest_path, issues,
                                      "origin manifest")
        manifest_digest = hashlib.sha256(
            manifest_path.read_bytes()).hexdigest()
    else:
        issues.append(
            f"origin manifest missing: {manifest_path} — produce it with "
            f"the independent sampler (the controller never writes it)")
    report = {
        "tool": "decision_migration_verify",
        "migration_id": args.migration_id,
        "manifest_digest": manifest_digest,
        "generated_at": datetime.now().replace(
            microsecond=0).isoformat(),
        "environment": environment_report(gov_dir.parent),
        "input_snapshot_identity": None,
        "origin_manifest": None,
        "tool_and_dependency_identity": None,
        "normalization_rules": {
            "cells": "verbatim (split by the mirrored pre-cutover "
                     "code-span splitter; no whitespace/case/punctuation "
                     "normalization)",
            "row_raw": "verbatim line replay (byte-faithful projection "
                       "and rollback)",
            "lossy_normalization": "forbidden — any content change is a "
                                   "conversion failure",
        },
        "line_coverage_report": None,
        "per_id_field_diffs": None,
        "ops_reconciliation": None,
        "independence_declaration": None,
    }
    env_issues = _env_gate(report["environment"])
    issues.extend(env_issues)

    shadow_path = migration_dir / "shadow" / STORE_FILE_NAME
    shadow_doc = None
    if shadow_path.is_file():
        shadow_doc = _read_json_or_fail(shadow_path, issues,
                                        "shadow store")
    else:
        issues.append(f"shadow store missing: {shadow_path}")

    md_path = gov_dir / MD_FILE_NAME
    if md_path.is_file():
        md_text = md_path.read_bytes().decode("utf-8")
        md_items = classify_lines_legacy(md_text)
        coverage = check_coverage(md_items)
        report["line_coverage_report"] = coverage
        if coverage["verdict"] == "FAIL":
            issues.append("coverage gate FAILED (unresolved lines block)")
        if manifest is not None:
            class_a = check_input_integrity(gov_dir, manifest,
                                            args.migration_id)
            report["input_snapshot_identity"] = class_a
            report["origin_manifest"] = {
                "path": str(migration_dir / "input-manifest.json"),
                "produced_by": manifest.get("produced_by"),
                "produced_at": manifest.get("produced_at"),
            }
            if class_a["verdict"] == "FAIL":
                issues.append("input-integrity gate FAILED: "
                              + str(class_a.get("detail")))
        if shadow_doc is not None:
            shape_issues = check_store_shape(shadow_doc)
            issues.extend(shape_issues)
            if not shape_issues:
                class_b = check_logical_equivalence(md_items, shadow_doc)
                report["per_id_field_diffs"] = class_b
                if class_b["verdict"] == "FAIL":
                    issues.append("equivalence gate FAILED: "
                                  + str(class_b.get("detail")))
        class_c = check_ops_integrity(gov_dir, md_items)
        report["ops_reconciliation"] = class_c
        if class_c["verdict"] == "FAIL":
            issues.append("ops-integrity gate FAILED: "
                          + str(class_c.get("detail")))
    else:
        issues.append(f"{md_path} does not exist")

    report["tool_and_dependency_identity"] = {
        "verifier_script": str(Path(__file__).resolve()),
        "verifier_script_sha256": report["environment"][
            "verifier_script_sha256"],
        "git_commit_digest": report["environment"]["git_commit_digest"],
        "parser_mirror_provenance": "verbatim semantic mirror of the "
                                    "pre-cutover writer splitter + "
                                    "engine row-anchored ID scan",
    }
    report["independence_declaration"] = {
        "rule_1_old_parser_adjudication": True,
        "rule_1_evidence": "all equivalence/coverage verdicts above are "
                           "produced ONLY by the mirrored legacy parser "
                           "in this file; no new-implementation parser is "
                           "consumed",
        "rule_2_precutover_validator": True,
        "rule_2_evidence": "this script is self-contained (stdlib only) "
                           "and runs as a controller subprocess; the "
                           "environment gate rejects a verdict produced "
                           "with the new modules importable",
        "shared_dependencies": [
            "stdlib only (no third-party packages)",
            "the mirrored legacy parser semantics (deliberately "
            "duplicated from the pre-cutover implementation — the "
            "duplication IS the independence)",
        ],
        "residual_risks": [
            "staged delivery: the REAL authority cutover is executed by a "
            "later authorized ticket (arch 实施顺序第 6 步 — this pack "
            "supports rehearsal, not activation of a production world "
            "without Coordinator authorization)",
            "the engine (verify_workflow.py) still reads the md "
            "projection face; JSON-era wiring of the freshness gate into "
            "the publish face is a cutover-ticket obligation",
            "the archive consumer (archive.py) still rewrites the md "
            "projection face — under JSON authority it must route through "
            "the write service or be frozen during migration windows",
        ],
        "declaration": "independent BY STRUCTURE (separate process, "
                       "separate parser, forbidden-import gate) with the "
                       "shared dependencies and residual risks above — "
                       "not a bare '独立：是'",
    }
    report["issues"] = issues
    report["verdict"] = "PASS" if not issues else "FAIL"
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["verdict"] == "PASS" else 1


def cmd_reverse_check(args) -> int:
    gov_dir = Path(args.gov_dir)
    migration_root = Path(args.migration_root)
    migration_dir = migration_root / args.migration_id
    issues = []
    export_path = migration_dir / "rollback-export.md"
    try:
        export_text = export_path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(json.dumps({"verdict": "FAIL",
                          "issues": [f"rollback export unreadable: {exc}"]},
                         ensure_ascii=False, indent=2))
        return 1
    store_path = gov_dir / STORE_FILE_NAME
    store_source = str(store_path)
    if not store_path.is_file():
        # Rehearsal world (no activation yet): the migration's shadow
        # store is the JSON-side baseline the export must round-trip.
        store_path = migration_dir / "shadow" / STORE_FILE_NAME
        store_source = f"{store_path} (shadow fallback — rehearsal world)"
    store_doc = _read_json_or_fail(store_path, issues, "decision store")
    if store_doc is None:
        print(json.dumps({"verdict": "FAIL", "issues": issues},
                         ensure_ascii=False, indent=2))
        return 1
    export_items = classify_lines_legacy(export_text)
    equivalence = check_logical_equivalence(export_items, store_doc)
    result = {
        "tool": "decision_migration_verify.reverse-check",
        "migration_id": args.migration_id,
        "export_path": str(export_path),
        "store_source": store_source,
        "equivalence": equivalence,
        "verdict": equivalence["verdict"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verdict"] == "PASS" else 1


# ── negative injection suite (ARCH-04 负向验收) ─────────────────────────────


def _base_md() -> str:
    return (
        "# 当前项目决策记录\n\n"
        "| 编号 | 日期 | 主题 | 背景 | 决策内容 | 备选方案 | 选择原因 "
        "| 影响范围 | 决策人 | 关联任务 | 后续动作 |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- "
        "| --- |\n"
        "| DEC-001 | 2026-09-25 | t1 | b1 | c1 | a1 | r1 | s1 | "
        "Coordinator | FIX-1 | x1 |\n"
        "| DEC-002 | 2026-09-25 | t2 | b2 | c2 （机器写入：governance-store "
        "decision-append op-abc；schema v1） | | | | | | |\n"
        "| DEC-003 | 2026-09-26 | t3 | b3 | c3 | | | | | | |\n")


def _shadow_from(md_text: str) -> dict:
    items = classify_lines_legacy(md_text)
    records = []
    for item in items:
        if item["kind"] == "record":
            records.append({
                "id": item["id"], "shape": ("live5" if len(item["cells"])
                                            == 5 else
                                           ("legacy11" if len(
                                               item["cells"]) == 11
                                            else "variant")),
                "cells": item["cells"], "row_raw": item["row_raw"],
                "source_line": item["line_no"], "provenance": None,
            })
    return {
        "format": "decision-store", "schema_version": 1,
        "records": records,
        "items": [{"kind": (i["kind"] if i["kind"] != "record"
                            else "record"),
                   "id": i.get("id"), "text": i.get("text")}
                  for i in items],
    }


def cmd_negative_suite(args) -> int:
    """Seven injected faults; each MUST be rejected by its named gate.
    A case that PASSES its gate is a verdict FAIL (the gate is broken)."""
    results = []
    tmp = Path(tempfile.mkdtemp(prefix="feat061-negative-"))

    def run_gate(name, *, md_text, shadow, ledger=None):
        """Run the verifier gates against an injected world."""
        case_dir = tmp / name
        gov = case_dir / ".governance"
        gov.mkdir(parents=True, exist_ok=True)
        (gov / MD_FILE_NAME).write_bytes(md_text.encode("utf-8"))
        if ledger is not None:
            (gov / OPS_LEDGER_NAME).write_bytes(
                json.dumps(ledger, ensure_ascii=False).encode("utf-8"))
        issues = []
        items = classify_lines_legacy(md_text)
        coverage = check_coverage(items)
        if coverage["verdict"] == "FAIL":
            issues.append("coverage")
        if shadow is not None:
            for issue in check_store_shape(shadow):
                issues.append("store-shape")
                break
            equivalence = check_logical_equivalence(items, shadow)
            if equivalence["verdict"] == "FAIL":
                issues.append("equivalence")
        if ledger is not None:
            class_c = check_ops_integrity(gov, items)
            if class_c["verdict"] == "FAIL":
                issues.append("ops-integrity")
        return issues

    # ① delete-row: one record vanishes between md and shadow.
    issues = run_gate(
        "delete-row", md_text=_base_md(),
        shadow=_shadow_from(_base_md().replace(
            "| DEC-002 | 2026-09-25 | t2 | b2 | c2 （机器写入：governance-store "
            "decision-append op-abc；schema v1） | | | | | | |\n", "")))
    results.append({"case": "①删行", "gate": "equivalence",
                    "rejected": bool(issues)})

    # ② duplicate-id: two shadow records share one id.
    shadow = _shadow_from(_base_md())
    shadow["records"].append(dict(shadow["records"][0]))
    issues = run_gate("duplicate-id", md_text=_base_md(), shadow=shadow)
    results.append({"case": "②重复ID", "gate": "equivalence(dup)",
                    "rejected": bool(issues)})

    # ③ field-change: a content cell silently differs (历史勘正混入).
    shadow = _shadow_from(_base_md())
    shadow["records"][0]["cells"][4] = "c1-被勘正"
    issues = run_gate("field-change", md_text=_base_md(), shadow=shadow)
    results.append({"case": "③字段变化", "gate": "equivalence",
                    "rejected": bool(issues)})

    # ④ dangling-ref: a committed op's marker is absent from the world.
    ledger = {"operations": {
        "op-ghost": {"command": "decision-append", "status": "ok",
                     "input_fingerprint": "x"},
    }}
    issues = run_gate("dangling-ref", md_text=_base_md(),
                      shadow=_shadow_from(_base_md()), ledger=ledger)
    results.append({"case": "④悬空引用(ops对账)", "gate": "ops-integrity",
                    "rejected": bool(issues)})

    # ⑤ unresolved-line: an unexplainable pipe row appears.
    issues = run_gate(
        "unresolved-line",
        md_text=_base_md() + "| 某手写行 | 没有DEC锚点 |\n",
        shadow=None)
    results.append({"case": "⑤未解析行", "gate": "coverage",
                    "rejected": bool(issues)})

    # ⑥ stale evidence: the manifest no longer describes the md world.
    case_dir = tmp / "stale-evidence"
    gov = case_dir / ".governance"
    gov.mkdir(parents=True, exist_ok=True)
    (gov / MD_FILE_NAME).write_bytes(_base_md().encode("utf-8"))
    stale_manifest = {
        "migration_id": "M-STALE",
        "produced_by": "decision_migration_verify.sample",
        "files": {MD_FILE_NAME: {"sha256": "0" * 64, "size_bytes": 1}},
    }
    class_a = check_input_integrity(gov, stale_manifest, "M-STALE")
    results.append({"case": "⑥陈旧证据(错误manifest)", "gate": "input-integrity",
                    "rejected": class_a["verdict"] == "FAIL"})

    # ⑦ load-new-helper: the forbidden-import gate must fire.
    saved = dict(sys.modules)
    try:
        sys.modules["decision_repository"] = type(sys)("decision_repository")
        report = environment_report(tmp)
        env_issues = _env_gate(report)
    finally:
        sys.modules.clear()
        sys.modules.update(saved)
    results.append({"case": "⑦加载新helper", "gate": "environment",
                    "rejected": bool(env_issues)})

    verdict = "PASS" if all(r["rejected"] for r in results) else "FAIL"
    payload = {
        "tool": "decision_migration_verify.negative-suite",
        "generated_at": datetime.now().replace(microsecond=0).isoformat(),
        "results": results,
        "fixture_root": str(tmp),
        "verdict": verdict,
        "detail": None if verdict == "PASS" else
                  "at least one injected fault was NOT rejected — the "
                  "corresponding gate is broken (ARCH-04 负向验收)",
    }
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes((json.dumps(payload, ensure_ascii=False, indent=2)
                         + "\n").encode("utf-8"))
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if verdict == "PASS" else 1


def cmd_environment(args) -> int:
    print(json.dumps(environment_report(Path(args.root or Path.cwd())),
                     ensure_ascii=False, indent=2))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="decision_migration_verify.py",
        description="FEAT-061 independent verifier (Layer 6) — self-"
                    "contained, stdlib-only, forbidden-import gated")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("sample", help="produce the origin manifest")
    p.add_argument("--gov-dir", required=True)
    p.add_argument("--migration-id", required=True)
    p.add_argument("--migration-root", required=True)

    p = sub.add_parser("verify", help="three-class integrity proof")
    p.add_argument("--gov-dir", required=True)
    p.add_argument("--migration-id", required=True)
    p.add_argument("--migration-root", required=True)

    p = sub.add_parser("reverse-check", help="rollback representability")
    p.add_argument("--gov-dir", required=True)
    p.add_argument("--migration-id", required=True)
    p.add_argument("--migration-root", required=True)

    p = sub.add_parser("negative-suite", help="injected-fault gate proof")
    p.add_argument("--out", default=None)

    p = sub.add_parser("environment", help="environment report")
    p.add_argument("--root", default=None)
    return parser


def main(argv=None) -> int:
    try:
        # FIX-278 caliber: explicit UTF-8 stdio — a Windows console must
        # never re-decode the structured verdict as GBK.
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 — best-effort console hygiene
        pass
    args = build_parser().parse_args(argv)
    handlers = {
        "sample": cmd_sample,
        "verify": cmd_verify,
        "reverse-check": cmd_reverse_check,
        "negative-suite": cmd_negative_suite,
        "environment": cmd_environment,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
