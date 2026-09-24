"""FEAT-061 — migration controller + projector (0.88.0 阶段 C1 · P1).

Layers 4/5 of the six-layer Repository boundary (see decision_repository
docstring for the full map):

    Layer 4  Projector            — the migration-time md regeneration
                                    with fencing (per-append projection
                                    attempts live in the write service;
                                    this module owns the regenerations
                                    that must survive crashes and late
                                    writers).
    Layer 5  Migration Controller — freeze / manifest gate / shadow /
                                    activate / rollback orchestration over
                                    the persisted authority state machine.

Requirement sources (consumed, never re-stated): DEC-237 (arch 复核 —
C1-ARCH-01…10), version-plan-0.88.0 §1/§2-C1 (独立性三规则 / 七步路径 /
冻结窗完整性双向摘要复核), FEAT-060 (three-phase recoverable transaction:
journal → apply → finalize, resume by judging the WORLD).

Scope fence (破坏性红线, honored by construction): this controller can
execute EVERYTHING in rehearsal sandboxes and test worlds, but the REAL
authority cutover is NOT part of this ticket — activation requires a
PASSing independent proof pack (the verifier subprocess, Layer 6) and a
Coordinator authorization recorded per arch 实施顺序第 6 步 (演练后才授权).
Nothing here writes `.governance/` records: all migration artifacts live
under ``.governance/.decision-migration/<migration_id>/`` (machine state,
same artifact class as ``governance-store-ops.json``), and every mutating
command takes an explicit ``--gov-dir`` (no default that could point at a
real host's records from a bare cwd).

C1-ARCH clause map (this module):

  * ARCH-01  persisted state machine drives every transition here via
             ``write_authority_transition`` (single linearization point =
             the atomic marker replace); activate/rollback/cancel all
             fence on epoch + owner token.
  * ARCH-02  freeze records the four closure conditions explicitly
             (writes-rejected / in-flight converged via the md target
             lock / ops classified via the ledger scan / input fixed via
             the manifest digest gate) — acquiring a lock or a timestamp
             alone is NEVER treated as "frozen".
  * ARCH-03  the origin manifest is produced by the INDEPENDENT read-only
             verifier sampler and retained; this controller only READS it
             and refuses on any mismatch — it never overwrites a
             manifest, and a re-sample means a NEW migration id.
  * ARCH-06  权威提交结果与投影结果分开持久表达: activation/rollback
             journal the commit; the projection keeps its own checkpoint;
             a committed-but-unprojected world is ``pending``, never
             silent; late projections refuse on a changed store snapshot.
  * ARCH-07  rollback export re-renders from the FROZEN FULL JSON store
             (never from the existing projection as the sole source),
             verifies reverse-representability through the independent
             old-parser, and preserves idempotency identity (operation
             markers), numbering state (max DEC id) and guard state (no
             other file is touched).  Only storage-format rollback is
             promised — never an old-binary rollback.
  * ARCH-08  nothing here updates a guard baseline; the guard's own
             consume transaction remains the only baseline writer
             (FEAT-060 R2) — recorded so the proof pack can assert it.
  * ARCH-09  lock release / cancel validates owner token + epoch; a
             cancel from a session that lost ownership refuses and never
             releases a newer holder's state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Reused primitives (single lock/atomic-write source discipline).
from contracts import ERROR_CODE_DISPOSITIONS
from governance_store import (
    StoreError,
    _TargetLock,
    _atomic_write_bytes,
    _line_ending_of,
)
import decision_repository as drepo

__all__ = [
    "COMMANDS",
    "build_parser",
    "main",
]

VERIFY_SCRIPT = Path(__file__).resolve().parent / "decision_migration_verify.py"

_JOURNAL_INTENT = "intent"
_JOURNAL_COMMITTED = "committed"
_JOURNAL_FINALIZED = "finalized"


def _fail(payload):
    raise StoreError(payload)


def _now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _migration_dir(governance_dir, migration_id) -> Path:
    return drepo.migration_root(governance_dir) / migration_id


def _read_json(path: Path, *, what: str) -> dict:
    try:
        return json.loads(path.read_bytes().decode("utf-8"))
    except FileNotFoundError:
        _fail({
            "code": "manual_intervention",
            "detail": f"{path} does not exist — {what} is required "
                      f"(crash/concurrency case ⑩: a missing gate input is "
                      f"a loud refusal, never a pass)",
        })
    except (ValueError, UnicodeDecodeError) as exc:
        _fail({
            "code": "manual_intervention",
            "detail": f"{path} is not valid UTF-8 JSON ({exc}) — {what} "
                      f"unreadable is a loud failure",
        })


def _require_authority(governance_dir, *, state=None, migration_id=None,
                       owner_token=None) -> dict:
    """Fail-closed authority gate for controller commands (ARCH-01/09)."""
    authority = drepo.load_authority(governance_dir)
    if state is not None and authority["state"] != state:
        _fail({
            "code": "illegal_transition",
            "detail": f"authority state is {authority['state']}, command "
                      f"requires {state}",
            "observed_state": authority["state"],
        })
    if migration_id is not None \
            and authority.get("migration_id") != migration_id:
        _fail({
            "code": "revision_conflict",
            "detail": f"authority migration_id {authority.get('migration_id')!r}"
                      f" != command migration_id {migration_id!r} — a "
                      f"stale or foreign migration may not act on this "
                      f"world",
        })
    if owner_token is not None:
        if authority.get("owner_token") != owner_token:
            # ARCH-09: a cancel/release whose token does not match the
            # persisted owner refuses — and does NOT release whatever a
            # newer owner now holds.
            _fail({
                "code": "operation_id_conflict",
                "detail": "owner token mismatch — this session no longer "
                          "owns the migration state; refusing without "
                          "releasing the current owner's state (ARCH-09)",
            })
    return authority


def _scan_pending_transactions(governance_dir) -> list:
    """ARCH-02 closure input: every UNRESOLVED transaction in the ops and
    guard ledgers blocks the freeze (在途事务已收敛 ∧ 未决 ops 已分类)."""
    issues = []
    ops_path = governance_dir / "governance-store-ops.json"
    if ops_path.is_file():
        doc = _read_json(ops_path, what="ops ledger (freeze scan)")
        for op_id, entry in (doc.get("operations") or {}).items():
            if isinstance(entry, dict) and entry.get("status") == "pending":
                issues.append(
                    f"ops ledger: operation {op_id} "
                    f"({entry.get('command')}) is still pending — classify "
                    f"or resolve it before freezing decision writes")
    guard_path = governance_dir / ".write-guard-violations.json"
    if guard_path.is_file():
        try:
            guard = json.loads(guard_path.read_bytes().decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            issues.append(
                "guard violations ledger (.write-guard-violations.json) is "
                "unreadable — the FEAT-060 recovery leg must resolve it "
                "before a decision-store freeze (case ⑥ interlock)")
        else:
            if isinstance(guard, dict) and guard.get("pending_txn"):
                issues.append(
                    "guard violations ledger carries a pending transaction "
                    "(FEAT-060) — resume or resolve it before freezing")
    return issues


def _frozen_md_digest(authority) -> str:
    frozen = authority.get("frozen") or {}
    digest = frozen.get("input_digest")
    if not digest:
        _fail({
            "code": "manual_intervention",
            "detail": "authority marker carries no frozen input digest — "
                      "the freeze record is incomplete; refusing",
        })
    return digest


def _run_verifier(args, *, timeout_seconds=120.0) -> dict:
    """Run the Layer-6 verifier as a SUBPROCESS (ARCH-04: the verification
    environment must not import the new implementation — in-process
    import would put the controller/repository modules into the verdict's
    own environment report, self-signing the independence declaration).
    ``-X utf8`` pins the child's stdio encoding regardless of the console
    locale — the verdict carries CJK text and a GBK console would
    otherwise mojibake it into the retained proof pack (FIX-278 caliber)."""
    cmd = [sys.executable, "-X", "utf8", str(VERIFY_SCRIPT)] + args
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        _fail({
            "code": "manual_intervention",
            "detail": f"independent verifier timed out after "
                      f"{timeout_seconds}s: {' '.join(args[:2])}…",
        })
    if proc.returncode not in (0, 1):
        _fail({
            "code": "manual_intervention",
            "detail": f"independent verifier failed to run (exit "
                      f"{proc.returncode}): {proc.stderr.strip()[:400]}",
        })
    try:
        return json.loads(proc.stdout)
    except ValueError:
        _fail({
            "code": "manual_intervention",
            "detail": f"independent verifier produced non-JSON output: "
                      f"{proc.stdout.strip()[:200]!r}",
        })


# ── freeze (C1-ARCH-02) ──────────────────────────────────────────────────────


def freeze(*, governance_dir, migration_id, timeout_seconds=10.0):
    """MD_ACTIVE → CUTOVER_FROZEN with the four closure conditions checked
    and RECORDED (not assumed)."""
    governance_dir = Path(governance_dir)
    if not migration_id or not isinstance(migration_id, str):
        _fail({"code": "schema_violation",
               "detail": "--migration-id is required"})
    authority = drepo.load_authority(governance_dir)
    if authority["state"] != drepo.STATE_MD_ACTIVE:
        _fail({
            "code": "illegal_transition",
            "detail": f"freeze requires {drepo.STATE_MD_ACTIVE}, world is "
                      f"{authority['state']}",
        })
    md_target = governance_dir / drepo.MD_FILE_NAME
    current_digest = _sha256_hex(md_target.read_bytes())

    # Closure ④ input fixed — the origin manifest was produced by the
    # independent read-only sampler and pins EXACTLY these bytes.
    manifest_path = _migration_dir(governance_dir, migration_id) \
        / "input-manifest.json"
    manifest = _read_json(manifest_path, what="origin input manifest "
                          "(produce it with decision_migration_verify.py "
                          "sample — the controller never writes it, "
                          "ARCH-03)")
    if manifest.get("migration_id") != migration_id:
        _fail({
            "code": "revision_conflict",
            "detail": f"manifest migration_id {manifest.get('migration_id')!r}"
                      f" != requested {migration_id!r} — re-sampling means "
                      f"a NEW migration id (ARCH-03)",
        })
    if manifest.get("produced_by") != "decision_migration_verify.sample":
        _fail({
            "code": "manual_intervention",
            "detail": "origin manifest was not produced by the independent "
                      "sampler — independence rule ① requires the "
                      "verification-side provenance",
        })
    manifest_files = manifest.get("files") or {}
    md_entry = manifest_files.get(drepo.MD_FILE_NAME) or {}
    if md_entry.get("sha256") != current_digest:
        _fail({
            "code": "revision_conflict",
            "detail": "decision-log.md changed since the origin manifest "
                      "was sampled — the input set is not fixed; re-sample "
                      "under a NEW migration id (双向摘要 gate, 方向 "
                      "manifest→current)",
        })

    # Closure ②∧③ — in-flight converged and ops classified.
    pending = _scan_pending_transactions(governance_dir)
    if pending:
        _fail({
            "code": "manual_intervention",
            "detail": "freeze refused — unresolved transactions: "
                      + "; ".join(pending),
        })

    owner_token = uuid.uuid4().hex
    with _TargetLock(md_target, timeout_seconds):
        # Holding the md target lock IS the convergence proof for md
        # appends: an in-flight writer holds the same lock, so acquiring
        # it means none is mid-write.  Re-check the digest INSIDE the lock.
        inside_digest = _sha256_hex(md_target.read_bytes())
        if inside_digest != current_digest:
            _fail({
                "code": "revision_conflict",
                "detail": "decision-log.md changed while acquiring the "
                          "freeze lock — retry the freeze",
            })

        def mutate(doc):
            doc["migration_id"] = migration_id
            doc["manifest_digest"] = _sha256_hex(manifest_path.read_bytes())
            doc["frozen"] = {
                "input_digest": inside_digest,
                "manifest_file": str(manifest_path),
                "closure": {
                    "writes_rejected": True,
                    "writes_rejected_mechanism":
                        "authority state CUTOVER_FROZEN — the write "
                        "service refuses before touching any file",
                    "inflight_converged": True,
                    "inflight_converged_mechanism":
                        "md target lock acquired (mutual exclusion with "
                        "in-flight appends) + ledger scan clean",
                    "ops_classified": True,
                    "ops_classified_mechanism":
                        "governance-store-ops.json + guard violations "
                        "ledger scanned: zero pending transactions",
                    "input_fixed": True,
                    "input_fixed_mechanism":
                        "origin manifest digest == frozen md bytes "
                        "(independent sampler provenance)",
                },
                "frozen_at": _now_iso(),
            }
            return doc

        doc = drepo.write_authority_transition(
            governance_dir,
            from_state=drepo.STATE_MD_ACTIVE,
            to_state=drepo.STATE_CUTOVER_FROZEN,
            expected_epoch=authority["epoch"],
            mutate=mutate, owner_token=owner_token,
            timeout_seconds=timeout_seconds)
    return {
        "code": "ok", "error": False,
        "operation": "freeze", "migration_id": migration_id,
        "state": doc["state"], "epoch": doc["epoch"],
        "owner_token": owner_token,
        "frozen_input_digest": inside_digest,
        "closure": doc["frozen"]["closure"],
        "detail": "decision writes are now FROZEN (CUTOVER_FROZEN) — "
                  "activation requires the independent proof pack (PASS) "
                  "and the owner token",
    }


# ── shadow conversion (C1 step ④) ────────────────────────────────────────────


def shadow(*, governance_dir, migration_id, accept_variants=None,
           accept_duplicates=None, timeout_seconds=10.0):
    """Convert the frozen md world into the candidate JSON store WITHOUT
    activating anything (pure format conversion — no content judgment)."""
    governance_dir = Path(governance_dir)
    authority = _require_authority(
        governance_dir, state=drepo.STATE_CUTOVER_FROZEN,
        migration_id=migration_id)
    migration_dir = _migration_dir(governance_dir, migration_id)
    md_target = governance_dir / drepo.MD_FILE_NAME
    frozen_digest = _frozen_md_digest(authority)
    md_bytes = md_target.read_bytes()
    if _sha256_hex(md_bytes) != frozen_digest:
        _fail({
            "code": "revision_conflict",
            "detail": "decision-log.md no longer matches the frozen input "
                      "digest — the freeze window was violated; restart "
                      "the migration under a NEW migration id (冻结窗截断"
                      "收敛语义 = 完整性失败重启, 不视为已切换)",
        })
    text = md_bytes.decode("utf-8")
    items = drepo.classify_md_document(text)
    acceptances = {}
    for raw in (accept_variants or []):
        dec_id, sep, note = raw.partition(":")
        if not sep or not dec_id.startswith(drepo.DEC_PREFIX):
            _fail({
                "code": "schema_violation",
                "detail": f"--accept-variant expects 'DEC-n:note', got "
                          f"{raw!r}",
            })
        acceptances[dec_id] = note
    duplicate_acceptances = {}
    for raw in (accept_duplicates or []):
        dec_id, sep, note = raw.partition(":")
        if not sep or not dec_id.startswith(drepo.DEC_PREFIX):
            _fail({
                "code": "schema_violation",
                "detail": f"--accept-duplicate expects 'DEC-n:note', got "
                          f"{raw!r}",
            })
        duplicate_acceptances[dec_id] = note
    store = drepo.build_store_from_document(
        items, variant_acceptances=acceptances,
        duplicate_acceptances=duplicate_acceptances)
    coverage = {}
    for item in items:
        coverage[item["kind"]] = coverage.get(item["kind"], 0) + 1
    shadow_dir = migration_dir / "shadow"
    shadow_dir.mkdir(parents=True, exist_ok=True)
    shadow_path = shadow_dir / drepo.JSON_STORE_FILE
    _atomic_write_bytes(
        shadow_path, (json.dumps(store, ensure_ascii=False, indent=2)
                      + "\n").encode("utf-8"))
    drepo.load_json_store(shadow_path)
    report = {
        "migration_id": migration_id,
        "frozen_input_digest": frozen_digest,
        "line_coverage": coverage,
        "record_count": len(store["records"]),
        "variant_acceptances": acceptances,
        "duplicate_acceptances": duplicate_acceptances,
        "shadow_digest": _sha256_hex(shadow_path.read_bytes()),
        "note": "历史勘正不混入格式转换 — cells/row_raw 逐字保留; 内容差异"
                "由独立校验器按旧解析器裁决 (independence rule ①)",
    }
    _atomic_write_bytes(
        migration_dir / "shadow-report.json",
        (json.dumps(report, ensure_ascii=False, indent=2)
         + "\n").encode("utf-8"))
    return {"code": "ok", "error": False, "operation": "shadow",
            "migration_id": migration_id, **report}


# ── independent verification gate (ARCH-04) ─────────────────────────────────


def verify(*, governance_dir, migration_id):
    """Run the Layer-6 verifier subprocess and RETAIN its verdict."""
    governance_dir = Path(governance_dir)
    _require_authority(governance_dir, migration_id=migration_id)
    migration_dir = _migration_dir(governance_dir, migration_id)
    verdict = _run_verifier([
        "verify", "--gov-dir", str(governance_dir),
        "--migration-id", migration_id,
        "--migration-root", str(drepo.migration_root(governance_dir)),
    ])
    verdict_path = migration_dir / "verify-verdict.json"
    verdict_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_bytes(
        verdict_path, (json.dumps(verdict, ensure_ascii=False, indent=2)
                       + "\n").encode("utf-8"))
    return {"code": "ok", "error": False, "operation": "verify",
            "migration_id": migration_id,
            "verdict": verdict.get("verdict"),
            "verdict_path": str(verdict_path)}


# ── activate (the single linearization point) ────────────────────────────────


def activate(*, governance_dir, migration_id, owner_token,
             timeout_seconds=10.0):
    """CUTOVER_FROZEN → JSON_ACTIVE.  Crash/concurrency cases ①②⑧⑩ live
    here and in the resume branches below."""
    governance_dir = Path(governance_dir)
    if not owner_token:
        _fail({"code": "schema_violation",
               "detail": "--owner-token is required (the freeze returned "
                         "it; ARCH-09)"})
    authority = drepo.load_authority(governance_dir)
    migration_dir = _migration_dir(governance_dir, migration_id)
    journal_path = migration_dir / "journal.json"
    shadow_path = migration_dir / "shadow" / drepo.JSON_STORE_FILE
    md_target = governance_dir / drepo.MD_FILE_NAME
    json_target = governance_dir / drepo.JSON_STORE_FILE

    # ── Resume judging the WORLD first (case ②: flipped but response
    #    lost; case ⑧: rolled back later — the marker/history decides).──
    if authority["state"] == drepo.STATE_JSON_ACTIVE:
        if authority.get("migration_id") == migration_id \
                and authority.get("owner_token") == owner_token:
            journal = _load_journal(journal_path)
            if journal.get("phase") == _JOURNAL_FINALIZED:
                return {"code": "ok", "error": False, "operation":
                        "activate", "migration_id": migration_id,
                        "resumed": "already_finalized",
                        "state": authority["state"],
                        "epoch": authority["epoch"]}
            _finalize_activation(governance_dir, migration_id,
                                 journal_path, timeout_seconds)
            return {"code": "ok", "error": False, "operation": "activate",
                    "migration_id": migration_id,
                    "resumed": "finalized_after_flip",
                    "state": authority["state"],
                    "epoch": authority["epoch"]}
        _fail({
            "code": "revision_conflict",
            "detail": f"world is JSON_ACTIVE under migration "
                      f"{authority.get('migration_id')!r} — this activate "
                      f"request ({migration_id!r}) is not its owner",
        })

    _require_authority(governance_dir, state=drepo.STATE_CUTOVER_FROZEN,
                       migration_id=migration_id, owner_token=owner_token)
    authority = drepo.load_authority(governance_dir)

    # Gate ⑩ — the independent proof pack must exist, PASS, and be bound
    # to THIS migration and THIS manifest.
    verdict = _read_json(migration_dir / "verify-verdict.json",
                         what="independent verify verdict")
    if verdict.get("verdict") != "PASS":
        _fail({
            "code": "manual_intervention",
            "detail": f"independent proof verdict is "
                      f"{verdict.get('verdict')!r} — activation requires "
                      f"PASS (a FAILED or missing proof never activates)",
        })
    if verdict.get("migration_id") != migration_id:
        _fail({
            "code": "revision_conflict",
            "detail": "verify verdict belongs to a different migration_id",
        })
    manifest_path = migration_dir / "input-manifest.json"
    manifest_digest = _sha256_hex(manifest_path.read_bytes())
    if verdict.get("manifest_digest") != manifest_digest:
        _fail({
            "code": "revision_conflict",
            "detail": "verify verdict was produced against a different "
                      "manifest (stale evidence — case ⑩)",
        })

    # Completeness gate (双向摘要复核, 方向 frozen→current): the md world
    # must still be exactly the frozen input.
    frozen_digest = _frozen_md_digest(authority)
    md_bytes = md_target.read_bytes()
    if _sha256_hex(md_bytes) != frozen_digest:
        _fail({
            "code": "manual_intervention",
            "detail": "decision-log.md diverged from the frozen input "
                      "digest — freeze-window completeness FAILED; per "
                      "version-plan C1⑤ this migration is NOT switched: "
                      "restart under a NEW migration id (no automatic "
                      "rollback, no continued writes)",
        })

    # Candidate identity — the shadow store is the only content source and
    # must revalidate under the pinned shadow digest.
    shadow_report = _read_json(migration_dir / "shadow-report.json",
                               what="shadow report")
    store_bytes = shadow_path.read_bytes()
    if _sha256_hex(store_bytes) != shadow_report.get("shadow_digest"):
        _fail({
            "code": "manual_intervention",
            "detail": "shadow store digest drifted from its report — "
                      "re-run the shadow conversion",
        })
    drepo.load_json_store(shadow_path)

    # Three-phase recoverable transaction (FEAT-060 pattern).
    expected_store_bytes = (json.dumps(
        json.loads(store_bytes.decode("utf-8")),
        ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    _write_journal(journal_path, {
        "phase": _JOURNAL_INTENT,
        "migration_id": migration_id,
        "store_digest": _sha256_hex(expected_store_bytes),
        "frozen_input_digest": frozen_digest,
        "manifest_digest": manifest_digest,
        "started_at": _now_iso(),
    })

    with _TargetLock(json_target, timeout_seconds):
        if json_target.is_file():
            existing = json_target.read_bytes()
            if _sha256_hex(existing) != _sha256_hex(expected_store_bytes):
                _fail({
                    "code": "manual_intervention",
                    "detail": "decision-store.json already exists with "
                              "DIFFERENT content — refusing (a candidate "
                              "store never overwrites an existing store "
                              "silently)",
                })
            # case ①: candidate already on disk — idempotent rewrite path.
        _atomic_write_bytes(json_target, expected_store_bytes)
        reread = drepo.load_json_store(json_target)
        if len(reread["records"]) != len(json.loads(
                expected_store_bytes.decode("utf-8"))["records"]):
            _fail({
                "code": "manual_intervention",
                "detail": "post-write reread: store record count "
                          "mismatch",
            })
        _write_journal(journal_path, {
            "phase": _JOURNAL_COMMITTED,
            "migration_id": migration_id,
            "store_digest": _sha256_hex(expected_store_bytes),
            "committed_at": _now_iso(),
        })
        doc = drepo.write_authority_transition(
            governance_dir,
            from_state=drepo.STATE_CUTOVER_FROZEN,
            to_state=drepo.STATE_JSON_ACTIVE,
            expected_epoch=authority["epoch"],
            mutate=lambda d: {**d,
                              "content_digest":
                                  _sha256_hex(expected_store_bytes)},
            owner_token=owner_token, timeout_seconds=timeout_seconds)
        # ── LINEARIZATION POINT REACHED: json is authoritative. ──

    _finalize_activation(governance_dir, migration_id, journal_path,
                         timeout_seconds)
    return {"code": "ok", "error": False, "operation": "activate",
            "migration_id": migration_id,
            "state": doc["state"], "epoch": doc["epoch"],
            "store_digest": _sha256_hex(expected_store_bytes),
            "resumed": False}


def _load_journal(journal_path: Path) -> dict:
    if not journal_path.is_file():
        _fail({
            "code": "manual_intervention",
            "detail": f"{journal_path} missing — the activation journal "
                      f"must exist to resume; refusing to guess",
        })
    return _read_json(journal_path, what="activation journal")


def _write_journal(journal_path: Path, doc: dict) -> None:
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_bytes(
        journal_path, (json.dumps(doc, ensure_ascii=False, indent=2)
                       + "\n").encode("utf-8"))


def _finalize_activation(governance_dir, migration_id, journal_path,
                         timeout_seconds) -> None:
    """Post-linearization completion: projection + journal finalize.
    Crash here leaves JSON_ACTIVE + unfinalized journal — the resume path
    re-judges the world and finishes (case ②)."""
    try:
        projection = drepo.project_store_to_markdown(
            governance_dir, reason=f"migration activate {migration_id}",
            timeout_seconds=timeout_seconds)
    except StoreError as exc:
        drepo.write_projection_checkpoint(governance_dir, {
            "status": "pending",
            "reason": f"migration activate {migration_id}",
            "last_error": exc.payload.get("detail"),
            "attempts": 1,
        })
        projection = {"status": "pending"}
    journal = _load_journal(journal_path)
    journal["phase"] = _JOURNAL_FINALIZED
    journal["finalized_at"] = _now_iso()
    journal["projection_status"] = projection.get("status")
    _write_journal(journal_path, journal)


# ── rollback (C1-ARCH-07) ────────────────────────────────────────────────────


def rollback_begin(*, governance_dir, reason, owner_token,
                   timeout_seconds=10.0):
    """JSON_ACTIVE → ROLLBACK_FROZEN (freeze json writes for the export
    + reverse-verification window).

    REVIEW-FEAT-061-CODE-R0 P1-F3/P2: the freeze pins the CURRENT store
    digest (under the json target lock — the same mutual exclusion the
    appends use) so rollback-activate can run the SYMMETRIC bidirectional
    completeness check to activation's frozen→current gate."""
    governance_dir = Path(governance_dir)
    if not reason:
        _fail({"code": "schema_violation",
               "detail": "--reason is required (audited rollback entry)"})
    authority = _require_authority(
        governance_dir, state=drepo.STATE_JSON_ACTIVE,
        owner_token=owner_token)
    projection = drepo.projection_freshness(governance_dir)
    json_target = governance_dir / drepo.JSON_STORE_FILE
    with _TargetLock(json_target, timeout_seconds):
        frozen_store_digest = _sha256_hex(json_target.read_bytes())
        doc = drepo.write_authority_transition(
            governance_dir,
            from_state=drepo.STATE_JSON_ACTIVE,
            to_state=drepo.STATE_ROLLBACK_FROZEN,
            expected_epoch=authority["epoch"],
            mutate=lambda d: {**d, "frozen": {
                "rollback_reason": reason,
                "projection_status_at_freeze": projection.get("status"),
                "frozen_store_digest": frozen_store_digest,
                "frozen_at": _now_iso(),
            }},
            owner_token=owner_token, timeout_seconds=timeout_seconds)
    return {"code": "ok", "error": False, "operation": "rollback-begin",
            "state": doc["state"], "epoch": doc["epoch"],
            "projection_status_at_freeze": projection.get("status"),
            "frozen_store_digest": frozen_store_digest}


def rollback_export(*, governance_dir, timeout_seconds=10.0):
    """Full export from the FROZEN CURRENT JSON authority (never from the
    existing projection as the sole source) + independent reverse check
    (ARCH-07 + independence rule ①)."""
    governance_dir = Path(governance_dir)
    authority = _require_authority(
        governance_dir, state=drepo.STATE_ROLLBACK_FROZEN)
    migration_id = authority.get("migration_id") or "rollback"
    migration_dir = _migration_dir(governance_dir, migration_id)
    migration_dir.mkdir(parents=True, exist_ok=True)
    json_target = governance_dir / drepo.JSON_STORE_FILE
    md_target = governance_dir / drepo.MD_FILE_NAME
    with _TargetLock(json_target, timeout_seconds):
        store_raw = json_target.read_bytes()
        store = drepo.load_json_store(json_target)
        rendered = drepo.render_markdown(store)
        md_ending = _line_ending_of(md_target.read_bytes()) \
            if md_target.is_file() else "\n"
        body = rendered.replace("\n", md_ending) if md_ending != "\n" \
            else rendered
        if not body.endswith(md_ending):
            body += md_ending
        export_path = migration_dir / "rollback-export.md"
        _atomic_write_bytes(export_path, body.encode("utf-8"))

    # Reverse-representability: the OLD parser (independent verifier
    # subprocess) must re-parse the export into the SAME records.
    reverse = _run_verifier([
        "reverse-check", "--gov-dir", str(governance_dir),
        "--migration-id", migration_id,
        "--migration-root", str(drepo.migration_root(governance_dir)),
    ])
    _atomic_write_bytes(
        migration_dir / "reverse-check-verdict.json",
        (json.dumps(reverse, ensure_ascii=False, indent=2)
         + "\n").encode("utf-8"))
    store_doc = json.loads(store_raw.decode("utf-8"))
    records = store_doc["records"]
    numbering_state = max(
        (int(r["id"][len(drepo.DEC_PREFIX):]) for r in records
         if r["id"][len(drepo.DEC_PREFIX):].isdigit()),
        default=0)
    marker_records = [r for r in records if r.get("provenance")]
    report = {
        "migration_id": migration_id,
        "store_digest": _sha256_hex(store_raw),
        "export_path": str(export_path),
        "record_count": len(records),
        "numbering_state_max_dec": numbering_state,
        "idempotency_identity_preserved": len(marker_records),
        "reverse_check_verdict": reverse.get("verdict"),
        "guard_state_note": "guard/基线/其他表文件零触碰 — 仅承诺存储格式"
                            "回退，不承诺旧二进制回退 (ARCH-07)",
    }
    _atomic_write_bytes(
        migration_dir / "rollback-report.json",
        (json.dumps(report, ensure_ascii=False, indent=2)
         + "\n").encode("utf-8"))
    if reverse.get("verdict") != "PASS":
        _fail({
            "code": "manual_intervention",
            "detail": "reverse check FAILED — the export is not "
                      "losslessly re-parseable by the old md parser; "
                      "rollback-activate will refuse (writes stay frozen)",
        })
    return {"code": "ok", "error": False, "operation": "rollback-export",
            **report}


def rollback_activate(*, governance_dir, owner_token,
                      timeout_seconds=10.0):
    """ROLLBACK_FROZEN → MD_ACTIVE (cases ⑦⑧)."""
    governance_dir = Path(governance_dir)
    authority = _require_authority(
        governance_dir, state=drepo.STATE_ROLLBACK_FROZEN,
        owner_token=owner_token)
    migration_id = authority.get("migration_id") or "rollback"
    migration_dir = _migration_dir(governance_dir, migration_id)
    report = _read_json(migration_dir / "rollback-report.json",
                        what="rollback report (run rollback-export first)")
    if report.get("reverse_check_verdict") != "PASS":
        _fail({
            "code": "manual_intervention",
            "detail": "rollback report does not carry a PASSing reverse "
                      "check — md reactivation refused (case ⑩ gate)",
        })
    export_path = Path(report["export_path"])
    export_bytes = export_path.read_bytes()
    journal_path = migration_dir / "rollback-journal.json"
    md_target = governance_dir / drepo.MD_FILE_NAME
    json_target = governance_dir / drepo.JSON_STORE_FILE
    with _TargetLock(json_target, timeout_seconds):
        # REVIEW-FEAT-061-CODE-R0 P1-F3: SYMMETRIC bidirectional digest
        # check (the rollback counterpart of activate's frozen→current
        # gate): the store under the json lock must still be EXACTLY the
        # world pinned at rollback-begin — any divergence during the
        # frozen window is a completeness failure and keeps the world
        # frozen (no md reactivation, no automatic anything).
        frozen_store_digest = (authority.get("frozen") or {}).get(
            "frozen_store_digest")
        if not frozen_store_digest:
            _fail({
                "code": "manual_intervention",
                "detail": "rollback freeze record carries no "
                          "frozen_store_digest — the freeze predates the "
                          "P1-F3 gate or is incomplete; re-run "
                          "rollback-begin",
            })
        current_store_digest = _sha256_hex(json_target.read_bytes())
        if current_store_digest != frozen_store_digest:
            _fail({
                "code": "manual_intervention",
                "detail": "decision-store.json diverged from the "
                          "rollback-frozen digest — rollback-window "
                          "completeness FAILED; the world stays frozen "
                          "(restart the rollback: rollback-begin → "
                          "rollback-export under a fresh report)",
            })
        _write_journal(journal_path, {
            "phase": _JOURNAL_INTENT,
            "migration_id": migration_id,
            "export_digest": _sha256_hex(export_bytes),
            "started_at": _now_iso(),
        })
        with _TargetLock(md_target, timeout_seconds):
            _atomic_write_bytes(md_target, export_bytes)
            doc = drepo.write_authority_transition(
                governance_dir,
                from_state=drepo.STATE_ROLLBACK_FROZEN,
                to_state=drepo.STATE_MD_ACTIVE,
                expected_epoch=authority["epoch"],
                mutate=lambda d: {**d,
                                  "content_digest":
                                      _sha256_hex(export_bytes)},
                owner_token=owner_token,
                timeout_seconds=timeout_seconds)
            # ── LINEARIZATION: md is authoritative again. ──
        _write_journal(journal_path, {
            "phase": _JOURNAL_FINALIZED,
            "migration_id": migration_id,
            "finalized_at": _now_iso(),
        })
    return {"code": "ok", "error": False, "operation": "rollback-activate",
            "state": doc["state"], "epoch": doc["epoch"],
            "md_digest": _sha256_hex(export_bytes),
            "note": "JSON store retained on disk as a non-authoritative "
                    "artifact; md world resumed (case ⑧: decision_append "
                    "replay finds markers via world recovery)"}


# ── cancel / status / repair (ARCH-09 / ARCH-06) ────────────────────────────


def cancel(*, governance_dir, migration_id, owner_token):
    """Abort a freeze that has not activated.  ARCH-09: validates owner
    token + epoch; a stale owner's cancel refuses WITHOUT releasing the
    newer owner's state."""
    governance_dir = Path(governance_dir)
    authority = drepo.load_authority(governance_dir)
    if authority["state"] == drepo.STATE_CUTOVER_FROZEN \
            and authority.get("migration_id") != migration_id:
        # A DIFFERENT migration owns the freeze — this cancel must not
        # release it.
        _fail({
            "code": "operation_id_conflict",
            "detail": f"freeze is owned by migration "
                      f"{authority.get('migration_id')!r}, not "
                      f"{migration_id!r} — cancel refuses without "
                      f"releasing another session's lock (ARCH-09)",
        })
    _require_authority(governance_dir, state=drepo.STATE_CUTOVER_FROZEN,
                       migration_id=migration_id, owner_token=owner_token)
    authority = drepo.load_authority(governance_dir)
    doc = drepo.write_authority_transition(
        governance_dir,
        from_state=drepo.STATE_CUTOVER_FROZEN,
        to_state=drepo.STATE_MD_ACTIVE,
        expected_epoch=authority["epoch"],
        mutate=lambda d: {**d, "frozen": None},
        owner_token=owner_token)
    return {"code": "ok", "error": False, "operation": "cancel",
            "migration_id": migration_id, "state": doc["state"],
            "epoch": doc["epoch"],
            "detail": "freeze aborted — md remains authoritative"}


def status(*, governance_dir):
    governance_dir = Path(governance_dir)
    authority = drepo.load_authority(governance_dir)
    freshness = drepo.projection_freshness(governance_dir)
    return {
        "code": "ok", "error": False, "operation": "status",
        "authority": {k: authority.get(k) for k in (
            "state", "backend", "epoch", "generation", "migration_id",
            "manifest_digest")} | {"owner_token_present":
                                       bool(authority.get("owner_token"))},
        "projection_freshness": freshness,
        "store_present": (governance_dir / drepo.JSON_STORE_FILE).is_file(),
        "migration_root": str(drepo.migration_root(governance_dir)),
    }


def project_repair(*, governance_dir, reason, timeout_seconds=10.0):
    """ARCH-06 recovery: re-project md from the CURRENT store (audited
    limited channel — requires a reason, recorded in the checkpoint)."""
    governance_dir = Path(governance_dir)
    _require_authority(governance_dir, state=drepo.STATE_JSON_ACTIVE)
    if not reason:
        _fail({"code": "schema_violation",
               "detail": "--reason is required (audited repair channel)"})
    result = drepo.project_store_to_markdown(
        governance_dir, reason=f"repair: {reason}",
        timeout_seconds=timeout_seconds)
    return {"code": "ok", "error": False, "operation": "project-repair",
            "projection_status": result["status"],
            "md_digest": result.get("md_digest")}


# ── proof pack assembly (ARCH-10) ────────────────────────────────────────────


def proof_pack(*, governance_dir, migration_id, crash_test_report=None):
    """Assemble the minimum proof-pack content (ARCH-10) from the
    retained verifier verdict + controller facts."""
    governance_dir = Path(governance_dir)
    migration_dir = _migration_dir(governance_dir, migration_id)
    verdict = _read_json(migration_dir / "verify-verdict.json",
                         what="verify verdict (run the verify command)")
    authority = drepo.load_authority(governance_dir)
    pack = {
        "migration_id": migration_id,
        "assembled_at": _now_iso(),
        "authority_after": {k: authority.get(k) for k in (
            "state", "backend", "epoch", "generation", "manifest_digest")},
        "independent_verifier_verdict": verdict,
        "controller_facts": {
            "freeze_closure": (authority.get("frozen") or {}).get(
                "closure"),
            "journals": sorted(
                p.name for p in migration_dir.glob("*journal.json")),
            "verdicts": sorted(
                p.name for p in migration_dir.glob("*verdict.json")),
        },
        "crash_test_results": None,
        "independence_declaration_note": "见 verify-verdict 的 "
                                         "independence_declaration 节 — "
                                         "列出共享依赖与残余风险，非只填"
                                         "「独立：是」(ARCH-10)",
    }
    if crash_test_report:
        pack["crash_test_results"] = _read_json(
            Path(crash_test_report),
            what="crash/concurrency validation report")
    pack_path = migration_dir / "proof-pack.json"
    _atomic_write_bytes(
        pack_path, (json.dumps(pack, ensure_ascii=False, indent=2)
                    + "\n").encode("utf-8"))
    return {"code": "ok", "error": False, "operation": "proof-pack",
            "proof_pack_path": str(pack_path),
            "verdict": verdict.get("verdict")}


# ── CLI composition root (module-owned; the engine dispatch face is not
#    grown by this ticket — FEAT-046 precedent) ────────────────────────────


def _emit(payload) -> int:
    import json as _json
    print(_json.dumps(payload, ensure_ascii=False, indent=2))
    if payload.get("error"):
        return 3 if payload.get("disposition") == "retryable" else 2
    return 0


def _run(fn, kwargs):
    try:
        return fn(**kwargs)
    except StoreError as exc:
        payload = dict(exc.payload)
        payload.setdefault("error", True)
        payload.setdefault(
            "disposition", ERROR_CODE_DISPOSITIONS.get(payload.get("code")))
        return payload


def build_parser():
    parser = argparse.ArgumentParser(
        prog="decision_migration.py",
        description="FEAT-061 migration controller — freeze/shadow/verify/"
                    "activate/rollback over the persisted decision-store "
                    "authority state (real cutover requires an authorized "
                    "proof pack; rehearsals run on explicit --gov-dir)")
    parser.add_argument("--gov-dir", required=True,
                        help="governance directory (explicit — no silent "
                             "default touches a host's .governance)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("freeze", help="MD_ACTIVE → CUTOVER_FROZEN")
    p.add_argument("--migration-id", required=True)

    p = sub.add_parser("shadow", help="convert frozen md → candidate JSON")
    p.add_argument("--migration-id", required=True)
    p.add_argument("--accept-variant", action="append", default=[],
                   help="explicit per-ID acceptance for a variant row "
                        "(DEC-n:note)")
    p.add_argument("--accept-duplicate", action="append", default=[],
                   help="explicit per-ID acceptance for a duplicated id "
                        "(DEC-n:note) — BOTH rows are carried verbatim, "
                        "never aggregated")

    p = sub.add_parser("verify", help="run the independent verifier")
    p.add_argument("--migration-id", required=True)

    p = sub.add_parser("activate", help="CUTOVER_FROZEN → JSON_ACTIVE")
    p.add_argument("--migration-id", required=True)
    p.add_argument("--owner-token", required=True)

    p = sub.add_parser("rollback-begin", help="JSON_ACTIVE → ROLLBACK_FROZEN")
    p.add_argument("--owner-token", required=True)
    p.add_argument("--reason", required=True)

    p = sub.add_parser("rollback-export",
                       help="export md from the frozen JSON authority")
    p = sub.add_parser("rollback-activate", help="ROLLBACK_FROZEN → MD_ACTIVE")
    p.add_argument("--owner-token", required=True)

    p = sub.add_parser("cancel", help="abort a freeze (owner token gated)")
    p.add_argument("--migration-id", required=True)
    p.add_argument("--owner-token", required=True)

    sub.add_parser("status", help="authority + freshness report")

    p = sub.add_parser("project-repair",
                       help="re-project md from the current store")
    p.add_argument("--reason", required=True)

    p = sub.add_parser("proof-pack", help="assemble the ARCH-10 pack")
    p.add_argument("--migration-id", required=True)
    p.add_argument("--crash-test-report", default=None)
    return parser


COMMANDS = {
    "freeze": freeze,
    "shadow": shadow,
    "verify": verify,
    "activate": activate,
    "rollback-begin": rollback_begin,
    "rollback-export": rollback_export,
    "rollback-activate": rollback_activate,
    "cancel": cancel,
    "status": status,
    "project-repair": project_repair,
    "proof-pack": proof_pack,
}


def main(argv=None) -> int:
    try:
        # FIX-278 caliber: explicit UTF-8 stdio — a Windows console must
        # never re-decode the structured payloads as GBK.
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 — best-effort console hygiene
        pass
    parser = build_parser()
    args = parser.parse_args(argv)
    gov_dir = Path(args.gov_dir)
    kwargs = {"governance_dir": gov_dir}
    if args.command in ("freeze", "shadow", "verify", "activate", "cancel",
                        "proof-pack"):
        kwargs["migration_id"] = args.migration_id
    if args.command in ("activate", "rollback-begin", "rollback-activate",
                        "cancel"):
        kwargs["owner_token"] = args.owner_token
    if args.command == "shadow":
        kwargs["accept_variants"] = list(args.accept_variant or [])
        kwargs["accept_duplicates"] = list(args.accept_duplicate or [])
    if args.command == "rollback-begin":
        kwargs["reason"] = args.reason
    if args.command == "project-repair":
        kwargs["reason"] = args.reason
    if args.command == "proof-pack":
        kwargs["crash_test_report"] = args.crash_test_report
    return _emit(_run(COMMANDS[args.command], kwargs))


if __name__ == "__main__":
    sys.exit(main())
