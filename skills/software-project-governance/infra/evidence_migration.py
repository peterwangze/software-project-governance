"""FIX-448 D1 M1 (DEC-368④): evidence hot→cold migration coordination layer.

Design source of truth: docs/architecture/evidence-hot-cold-compaction.md
(§5 A completed-task EVD segment archive; §6 invariants I1~I7; §7.1 modules /
§7.2 interface contracts / §7.3 manifest byte model; §8 apply order +
interrupted worlds; §9 resource bounds; §11 D1 path).

Authorized scope (M1 batch): implement the coordination layer with a
fully working --dry-run face (zero hot-table writes, zero archive writes)
and a HARD-GATED --execute face that refuses unless the M2 dispatch flag
(FIX448_EVD_M2_EXECUTE=1) is set by a future, separately reviewed dispatch.
The 650,000 B capacity gate stays BLOCKED per design §11 D1 — this module
REPORTS capacity_status, it never re-ladders or waives the gate (I6).

Module boundaries (§7.1, one responsibility each — no god module):
  MigrationInputs   — capture + pin the input world (hot/plan bytes)
  plan_evd_compaction — Eligibility (REUSES archive.scan_row_families as
                      the single classification source; no second verdict
                      vocabulary, I2) + RawRowPlan (raw byte slices, never
                      re-rendered rows) + byte-conservation self-checks
  apply_evd_plan    — EVDTransfer: I4 phase machine prepared → cold_publish
                      → cold_verified → hot_committed → finalized, reusing
                      the FIX-446 never-overwrite publish primitive (I5)
                      and the governance-store hot _TargetLock (§8.1
                      quiesce) + hot CAS (temp+fsync+atomic replace)
  recover_evd_transfer — world judgment from pinned inputs, staged slices
                      and the real files (never trusts the journal alone)

Invariants honored here (§6):
  I1 — instances are (input digest, byte range, row digest); original
       bytes are moved verbatim, never re-rendered or edited.
  I2 — only canonical six-condition rows with migrate=True move; every
       retained row carries its canonical reason in the manifest.
  I3 — active/missing/unknown/duplicate rows stay hot by construction
       (the classifier pins them; the planner only relocates movers).
  I4 — cold is fully published and verified BEFORE the hot CAS; any
       missing piece / identity mismatch / input drift is a loud refusal.
  I5 — cold publish goes through _write_archive_file_never_overwrite
       (O_CREAT|O_EXCL + fsync + identity check); no exists-then-replace.
  I6 — 650,000 B / 400,000 B gates are reported, never altered.
  I7 — fresh transaction_id per apply ("evdt-<utc>-<rand>"); no reuse of
       legacy op-* ids as new-write authority.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import secrets
import sys
import tempfile
from pathlib import Path

_INFRA_DIR = Path(__file__).resolve().parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import archive as _archive                      # noqa: E402
import archive_migration_engine as _engine      # noqa: E402
import governance_store as _store               # noqa: E402

# ---------------------------------------------------------------------------
# Resource bounds (design §9 — first-version budgets, NOT performance facts)
# ---------------------------------------------------------------------------
MAX_INPUT_BYTES = 8 * 1024 * 1024        # 8 MiB controlled-input ceiling
MAX_SEGMENT_BYTES = 100_000              # per cold segment payload
MAX_SEGMENT_ROWS = 128                   # per cold segment row count
MAX_SEGMENTS = 128                       # per transaction
MAX_ROW_BYTES = 100_000                  # a single original row

# Capacity gates (I6 — reported, never modified; mirrors
# core/architecture-health.json evidence override semantics).
CAPACITY_WARN_BYTES = 400_000
CAPACITY_ERROR_BYTES = 650_000

MANIFEST_SCHEMA = "evidence-evd-transfer/1"
EXECUTE_ENV_FLAG = "FIX448_EVD_M2_EXECUTE"

PHASES = ("prepared", "cold_publish", "cold_verified", "hot_committed",
          "finalized")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _sha256_bytes(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()


def _utc_now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="milliseconds")


def _refuse(code: str, detail: str, **extra):
    """Design §7.2: a Refusal is a structured dict, never a silent skip."""
    out = {"status": "refused", "code": code, "detail": detail}
    out.update(extra)
    return out


def _is_refusal(obj) -> bool:
    return isinstance(obj, dict) and obj.get("status") == "refused"


# ---------------------------------------------------------------------------
# MigrationInputs — capture + pin the input world (§7.2 plan inputs)
# ---------------------------------------------------------------------------

class MigrationInputs:
    """Pinned hot-table/plan-tracker bytes with read-twice consistency.

    Design §3.1 discipline: each input is read twice and the two reads
    must agree (guards torn reads); this pins a per-file consistent
    snapshot. It deliberately does NOT claim a cross-file transactional
    snapshot — apply revalidates both pins under the hot lock (§8.1).
    """

    def __init__(self, evidence_bytes: bytes, plan_bytes: bytes,
                 evidence_path: str, plan_path: str):
        self.evidence_bytes = evidence_bytes
        self.plan_bytes = plan_bytes
        self.evidence_path = str(evidence_path)
        self.plan_path = str(plan_path)
        self.evidence_sha256 = _sha256_bytes(evidence_bytes)
        self.plan_sha256 = _sha256_bytes(plan_bytes)

    @classmethod
    def capture(cls, evidence_path, plan_path) -> "MigrationInputs":
        ev_path, plan_path = Path(evidence_path), Path(plan_path)
        for p in (ev_path, plan_path):
            if not p.is_file():
                raise RuntimeError(
                    f"input {p} is not a readable file — fail-closed; a "
                    f"refusal world is never planned around")
        first = ev_path.read_bytes()
        second = ev_path.read_bytes()
        if first != second:
            raise RuntimeError(
                f"torn read on {ev_path}: two consecutive reads differ — "
                f"the file is being written; refuse to plan on a moving world")
        plan_first = plan_path.read_bytes()
        plan_second = plan_path.read_bytes()
        if plan_first != plan_second:
            raise RuntimeError(
                f"torn read on {plan_path}: two consecutive reads differ")
        if len(first) > MAX_INPUT_BYTES:
            raise RuntimeError(
                f"hot input {ev_path} is {len(first)} B > first-version "
                f"budget {MAX_INPUT_BYTES} B (design §9) — resource_limit")
        return cls(first, plan_first, ev_path, plan_path)

    def pins(self) -> dict:
        return {
            "evidence_path": self.evidence_path,
            "evidence_sha256": self.evidence_sha256,
            "evidence_bytes": len(self.evidence_bytes),
            "plan_path": self.plan_path,
            "plan_sha256": self.plan_sha256,
            "plan_bytes": len(self.plan_bytes),
        }


# ---------------------------------------------------------------------------
# RawRowPlan — canonical verdicts mapped onto exact raw byte slices
# ---------------------------------------------------------------------------

def _line_offsets(raw: bytes):
    """Byte offset/length of every logical line (split on LF; a CR from
    CRLF stays inside its line, the trailing LF belongs to the line).

    This is the SAME byte accounting archive.scan_row_families_impl uses
    (len(line.encode('utf-8')) + 1 for every line except a final one with
    no trailing newline) — verified by the planner's slice-decode check.
    """
    lines = raw.split(b"\n")
    offsets = []
    pos = 0
    for i, line in enumerate(lines):
        length = len(line) + (0 if i == len(lines) - 1 else 1)
        offsets.append((pos, length))
        pos += length
    return lines, offsets


def plan_evd_compaction(inputs: "MigrationInputs", policy: dict) -> dict:
    """§7.2 plan_evd_compaction → Plan | Refusal. ZERO side effects.

    policy keys:
      version_start / version_end — retention window for would_archive
      families — subset of ("EVD","REVIEW","RECO","TRIAGE") to scan
                (only "EVD" ever becomes a mover in M1: FIX-446 hardened
                 leg; other families are reported retain-only)
    """
    version_start = policy.get("version_start", "0.1.0")
    version_end = policy.get("version_end", "0.98.0")
    families = tuple(policy.get("families") or ("EVD",))
    # Injectable for deterministic fixtures; the default is the repo's
    # standalone mapping (archived tasks + FIX-235 completed-hot).
    task_versions = policy.get("task_versions")
    if task_versions is None:
        task_versions = _archive._evidence_task_versions_standalone()

    raw = inputs.evidence_bytes
    text = raw.decode("utf-8")
    lines_text, offsets = _line_offsets(raw)

    # Eligibility — the single canonical source (I2: no second vocabulary).
    # scan_row_families classifies every family row with reasons; the EVD
    # leg rides _classify_evidence_rows_impl itself (zero drift).
    scan = _archive.scan_row_families(
        version_start, version_end, families=families, content=text,
        task_versions=task_versions,
        plan_tracker_content=inputs.plan_bytes.decode("utf-8"))

    context = _archive._build_classification_context(
        inputs.plan_bytes.decode("utf-8"))
    context_digest = _archive._verdicts._evidence_classification_context_digest(
        task_versions, context)

    instances = []
    scanned_idxs = set()
    for row in scan["rows"]:
        idx = row["line_idx"]
        scanned_idxs.add(idx)
        off, length = offsets[idx]
        row_bytes = raw[off:off + length]
        # slice-decode identity check: the classifier saw this exact line
        if row_bytes.decode("utf-8") != lines_text[idx].decode("utf-8") + (
                "\n" if idx != len(lines_text) - 1 else ""):
            return _refuse(
                "byte_slice_mismatch",
                f"line {idx}: raw slice does not decode to the classified "
                f"line — planner byte model drifted from the scanner")
        family = row["family"]
        mover = bool(row["migrate"]) and family == "EVD"
        instances.append({
            "source_sha256": inputs.evidence_sha256,
            "byte_offset": off,
            "byte_length": length,
            "row_sha256": _sha256_bytes(row_bytes),
            "family": family,
            "row_id": row["id"],
            "version": row.get("version"),
            "task_refs": sorted(row.get("ref_types", {}).keys()),
            "decision": "move" if mover else "retain",
            "reason": row["reason"],
        })

    movers = [i for i in instances if i["decision"] == "move"]
    retentions = [i for i in instances if i["decision"] == "retain"]

    # §9 resource limits: an over-budget row stays hot (whole-row, no split)
    limited = []
    for inst in movers:
        if inst["byte_length"] > MAX_ROW_BYTES:
            inst["decision"] = "retain"
            inst["reason"] = "resource_limit_row_over_100kb"
            limited.append(inst["row_id"])
    movers = [i for i in instances if i["decision"] == "move"]

    # ordered segments (§7.3 outputs.segments): source order, bounded
    segments = []
    cur, cur_bytes = [], 0
    for inst in movers:
        if cur and (len(cur) >= MAX_SEGMENT_ROWS
                    or cur_bytes + inst["byte_length"] > MAX_SEGMENT_BYTES):
            segments.append(cur)
            cur, cur_bytes = [], 0
        cur.append(inst)
        cur_bytes += inst["byte_length"]
    if cur:
        segments.append(cur)
    if len(segments) > MAX_SEGMENTS:
        return _refuse(
            "resource_limit",
            f"plan needs {len(segments)} segments > budget {MAX_SEGMENTS}; "
            f"narrow the window or dispatch multiple transactions")

    # hot_after = raw bytes minus the moved slices (exact interval removal —
    # every retained byte, including non-table prose and blank lines, stays
    # in place; nothing is re-rendered or re-joined from decoded text)
    moved_ranges = sorted(
        (i["byte_offset"], i["byte_offset"] + i["byte_length"])
        for i in movers)
    hot_after = bytearray()
    cursor = 0
    for start, end in moved_ranges:
        hot_after += raw[cursor:start]
        cursor = end
    hot_after += raw[cursor:]
    hot_after = bytes(hot_after)

    # byte conservation (§7.2 plan validation): moved + retained byte spans
    # are disjoint and inside the input; every scanned row was accounted.
    covered = sorted((i["byte_offset"], i["byte_offset"] + i["byte_length"])
                     for i in instances)
    for (s1, e1), (s2, e2) in zip(covered, covered[1:]):
        if e1 > s2:
            return _refuse(
                "byte_conservation_failed",
                f"instance byte ranges overlap at {e1}/{s2} — refuse")
    moved_total = sum(i["byte_length"] for i in movers)
    retained_total = sum(i["byte_length"] for i in retentions)
    if len(hot_after) + moved_total != len(raw):
        return _refuse(
            "byte_conservation_failed",
            f"hot_after({len(hot_after)}) + moved({moved_total}) != "
            f"input({len(raw)}) — interval removal lost bytes")

    # I6: report the gates, never bend them
    if len(hot_after) < CAPACITY_ERROR_BYTES:
        capacity_status = "under_error_gate"
    elif len(hot_after) < CAPACITY_WARN_BYTES:
        capacity_status = "warn_zone"
    else:
        capacity_status = "blocked"

    plan = {
        "schema_version": MANIFEST_SCHEMA,
        "transaction_id": None,          # minted at apply time (I7)
        "planned_utc": _utc_now_iso(),
        "input": {
            "hot_sha256": inputs.evidence_sha256,
            "hot_bytes": len(raw),
            "plan_sha256": inputs.plan_sha256,
            "classification_context_sha256": context_digest,
            "version_window": [version_start, version_end],
            "families_scanned": list(families),
        },
        "instances": instances,
        "outputs": {
            "hot_after_sha256": _sha256_bytes(hot_after),
            "hot_after_bytes": len(hot_after),
            "segments": [
                {"relative_path": (
                    f"archive/evidence/evdt-segment-{n:03d}.md"),
                 "bytes": sum(i["byte_length"] for i in seg),
                 "row_count": len(seg),
                 "ordered_row_ids": [i["row_id"] for i in seg]}
                for n, seg in enumerate(segments)],
            "moved_instances": len(movers),
            "retained_instances": len(retentions),
            "moved_bytes": moved_total,
            "retained_family_bytes": retained_total,
            "resource_limited_rows": limited,
        },
        "capacity": {
            "status": capacity_status,
            "hot_after_bytes": len(hot_after),
            "error_gate_bytes": CAPACITY_ERROR_BYTES,
            "warn_gate_bytes": CAPACITY_WARN_BYTES,
            "note": ("I6: gates are reported, never modified; per design "
                     "§11 D1 the 650KB acceptance stays BLOCKED unless a "
                     "real remeasure passes — this plan does not claim it"),
        },
        "scan_coverage": scan.get("coverage"),
        "phase": "planned",
    }
    plan["_hot_after_bytes_internal"] = hot_after   # plan-local; apply re-derives
    return plan


# ---------------------------------------------------------------------------
# EVDTransfer — I4 phase machine (M1: execute face hard-gated)
# ---------------------------------------------------------------------------

def apply_evd_plan(plan: dict, inputs: "MigrationInputs",
                   governance_dir, *, lock_timeout_seconds: int = 10) -> dict:
    """§7.2 apply_evd_plan → Receipt | Refusal.

    M1 HARD GATE: refuses with execute_not_authorized unless the M2
    dispatch flag is present. The phase machine below is the real
    implementation the M2 dispatch will run (fixture-tested here on
    isolated tmp roots); enabling it against the REAL hot table is a
    separately reviewed M2 decision, not a flag flip away.
    """
    if os.environ.get(EXECUTE_ENV_FLAG) != "1":
        return _refuse(
            "execute_not_authorized",
            f"FIX-448 M1 implements the coordination layer with dry-run "
            f"only; --execute requires the M2 dispatch flag "
            f"{EXECUTE_ENV_FLAG}=1 from a separately reviewed batch "
            f"(design §11 D1 / DEC-368④). The capacity gate remains "
            f"BLOCKED; nothing was written.")

    gov = Path(governance_dir)
    ev_path = Path(inputs.evidence_path)
    transaction_id = plan.get("transaction_id") or (
        f"evdt-{_dt.datetime.now(_dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        f"-{secrets.token_hex(4)}")
    plan = dict(plan)
    plan["transaction_id"] = transaction_id

    # quiesce: the SAME hot lock the EVD writer takes (§8.1); revalidate pins
    with _store._TargetLock(ev_path, lock_timeout_seconds):
        raw_now = ev_path.read_bytes()
        if _sha256_bytes(raw_now) != inputs.evidence_sha256:
            return _refuse(
                "input_diverged",
                "hot file changed since the plan snapshot — CAS refusal; "
                "re-plan from a fresh snapshot (design §8.2 hot-append row)")
        if _sha256_bytes(Path(inputs.plan_path).read_bytes()) != \
                inputs.plan_sha256:
            return _refuse(
                "classification_context_changed",
                "plan-tracker bytes diverged — classification context pins "
                "no longer hold; re-plan")

        stage = gov / "migration-staging" / transaction_id
        stage.mkdir(parents=True, exist_ok=False)

        # -- prepared: stage manifest + before backup (§8.1 step 3) -------
        (stage / "before-evidence.md").write_bytes(raw_now)
        manifest = {k: v for k, v in plan.items()
                    if k != "_hot_after_bytes_internal"}
        manifest["phase"] = "prepared"
        (stage / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8")

        # -- cold publish + verify (§8.1 steps 4-5; I4 order, I5 primitive) --
        raw = inputs.evidence_bytes
        movers = [i for i in plan["instances"] if i["decision"] == "move"]
        seg_rows, cur, cur_bytes = [], [], 0
        for inst in movers:
            if cur and (len(cur) >= MAX_SEGMENT_ROWS
                        or cur_bytes + inst["byte_length"] > MAX_SEGMENT_BYTES):
                seg_rows.append(cur)
                cur, cur_bytes = [], 0
            cur.append(inst)
            cur_bytes += inst["byte_length"]
        if cur:
            seg_rows.append(cur)

        archive_root = gov / "archive"
        published = []
        seg_payloads = []   # (seg_index, header, payload_lines, chunks)
        for n, seg in enumerate(seg_rows):
            rel = f"evidence/evdt-segment-{n:03d}.md"
            body_lines = []
            mover_chunks = []
            for inst in seg:
                chunk = raw[inst["byte_offset"]:
                           inst["byte_offset"] + inst["byte_length"]]
                if _sha256_bytes(chunk) != inst["row_sha256"]:
                    return _refuse(
                        "identity_changed",
                        f"staged slice hash mismatch for {inst['row_id']} — "
                        f"refusing to publish an unverified segment")
                mover_chunks.append(chunk)
                # strip exactly ONE trailing LF for the text-line join (the
                # publish primitive re-appends "\n" per joined line; a CR
                # from CRLF stays inside the line — payload bytes preserved)
                text_line = chunk.decode("utf-8")
                if text_line.endswith("\n"):
                    text_line = text_line[:-1]
                body_lines.append(text_line)
            header = (f"<!-- FIX-448 EVD transfer segment {n:03d} · "
                      f"transaction {transaction_id} · schema "
                      f"{MANIFEST_SCHEMA} · payload = verbatim original "
                      f"row bytes (header is not part of the verified "
                      f"payload) -->")
            try:
                outcome = _engine._write_archive_file_never_overwrite(
                    archive_root / rel, header, body_lines)
            except _engine.BigTableMigrationError as exc:
                # CODE R0 P3-4: surface the primitive's loud conflict
                # refusal in the §7.2 structured Refusal shape — fail-loud
                # semantics preserved (hot untouched; staged state intact).
                return _refuse(
                    "archive_target_conflict",
                    f"cold publish refused for segment {n:03d}: {exc} — "
                    f"hot table untouched; staged state in {stage} allows "
                    f"reconciliation")
            published.append({"relative_path": f"archive/{rel}",
                              "outcome": outcome, "rows": len(seg)})
            seg_payloads.append((n, header, body_lines, mover_chunks))
        # cold verify (CODE R0 P1-1): READ THE DISK BACK — a "created"
        # outcome alone proves nothing about the bytes that landed. Each
        # published file must equal the primitive's own payload formula
        # byte-for-byte, and every payload line + "\n" must reproduce its
        # mover's original chunk. (Mover rows all carry a trailing LF today;
        # a no-trailing-LF mover would surface here as a 1-byte mismatch →
        # loud refusal, never a silent CAS — the M2 re-plan asserts this
        # boundary per CODE R0 P3-3.)
        for n, header, body_lines, mover_chunks in seg_payloads:
            seg_path = archive_root / f"evidence/evdt-segment-{n:03d}.md"
            on_disk = seg_path.read_bytes()
            expected = (header + "\n" + "\n".join(body_lines)
                        + "\n").encode("utf-8")
            if on_disk != expected:
                return _refuse(
                    "identity_changed",
                    f"segment {n:03d} on-disk bytes do not equal the "
                    f"publish formula — refusing the hot CAS (I4: cold "
                    f"is verified BEFORE hot commit)")
            payload_lines = on_disk.decode("utf-8").split("\n")[1:]
            for line, chunk in zip(payload_lines, mover_chunks):
                if (line + "\n").encode("utf-8") != chunk:
                    return _refuse(
                        "byte_conservation_failed",
                        f"segment {n:03d} payload line does not reproduce "
                        f"the mover's original bytes — refusing the hot CAS")
        manifest["phase"] = "cold_verified"

        # -- commit hot (§8.1 step 6): pinned postimage, temp+fsync+CAS ---
        hot_after = plan["_hot_after_bytes_internal"]
        fd, tmp_name = tempfile.mkstemp(dir=str(gov), suffix=".evdt-tmp")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(hot_after)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, str(ev_path))
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        post = ev_path.read_bytes()
        if _sha256_bytes(post) != plan["outputs"]["hot_after_sha256"]:
            return _refuse("identity_changed",
                           "hot postimage digest mismatch after replace — "
                           "staged slices + before backup allow recovery")
        manifest["phase"] = "hot_committed"

        # -- finalize (§8.1 step 7): journal the terminal state ------------
        manifest["phase"] = "finalized"
        manifest["outputs"]["published_segments"] = published
        (stage / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8")
        return {
            "status": "applied",
            "transaction_id": transaction_id,
            "phase": "finalized",
            "hot_after_bytes": len(post),
            "hot_after_sha256": plan["outputs"]["hot_after_sha256"],
            "moved_instances": len(movers),
            "published_segments": published,
            "recovery": ("before-evidence.md + manifest.json + segments in "
                         f"{stage} — recovery义务 per design §8.2"),
        }


def recover_evd_transfer(transaction_id, governance_dir,
                        evidence_path) -> dict:
    """§7.2 recover_evd_transfer → world judgment from pins + real files.

    Never trusts the journal alone: the world is decided by whether the
    live hot file matches the pinned BEFORE or AFTER digest (or neither).
    """
    gov = Path(governance_dir)
    stage = gov / "migration-staging" / transaction_id
    manifest_path = stage / "manifest.json"
    if not manifest_path.is_file():
        return _refuse("recovery_conflict",
                       f"no manifest for transaction {transaction_id}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    before = stage / "before-evidence.md"
    if not before.is_file():
        return _refuse("recovery_conflict",
                       "staged before-evidence.md missing — cannot judge "
                       "the world; refuse to guess")
    before_digest = _sha256_bytes(before.read_bytes())
    live_digest = _sha256_bytes(Path(evidence_path).read_bytes())
    after_digest = manifest["outputs"].get("hot_after_sha256")

    if live_digest == before_digest:
        world = "hot_before_intact"
        action = ("cold segments may exist as verified duplicates; resume "
                  "forward or withdraw per §8.3 — do not re-publish blind")
    elif after_digest and live_digest == after_digest:
        world = "hot_after_committed"
        action = ("verify published segments then mark finalized; any NEW "
                  "appends after this digest are a legal later world — "
                  "never roll back over them")
    else:
        world = "unknown_world"
        action = ("neither pinned digest matches — recovery_conflict; manual "
                  "reconciliation from stage/ + cold segments — never roll "
                  "back over a later world with an old digest")
    return {
        "status": "judged",
        "transaction_id": transaction_id,
        "journal_phase": manifest.get("phase"),
        "world": world,
        "action": action,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli() -> int:
    parser = argparse.ArgumentParser(
        description="FIX-448 D1 evidence EVD transfer coordination layer "
                    "(M1: dry-run face; execute hard-gated for M2)")
    parser.add_argument("--dry-run", action="store_true",
                        help="plan-only: canonical classification + byte "
                             "plan + capacity arithmetic; ZERO writes")
    parser.add_argument("--execute", action="store_true",
                        help="apply the plan (REFUSES unless the M2 "
                             "dispatch flag is set)")
    parser.add_argument("--version-start", default="0.1.0")
    parser.add_argument("--version-end", default="0.98.0")
    parser.add_argument("--evidence", default=None,
                        help="override evidence-log path (default: the "
                             "repo governance hot table)")
    parser.add_argument("--plan-tracker", default=None)
    parser.add_argument("--governance-dir", default=None)
    parser.add_argument("--out", default=None,
                        help="write the plan/report JSON here (parent must "
                             "exist); default: stdout only")
    parser.add_argument("--manifest-sample-rows", type=int, default=5)
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        parser.error("choose --dry-run or --execute")

    gov = Path(args.governance_dir) if args.governance_dir else (
        _INFRA_DIR.parent.parent.parent / ".governance")
    ev_path = Path(args.evidence) if args.evidence else gov / "evidence-log.md"
    plan_path = Path(args.plan_tracker) if args.plan_tracker else (
        gov / "plan-tracker.md")

    try:
        inputs = MigrationInputs.capture(ev_path, plan_path)
    except RuntimeError as exc:
        print(json.dumps({"status": "refused", "code": "capture_failed",
                          "detail": str(exc)}, ensure_ascii=False))
        return 2

    policy = {"version_start": args.version_start,
              "version_end": args.version_end,
              "families": ("EVD", "REVIEW", "RECO", "TRIAGE")}
    plan = plan_evd_compaction(inputs, policy)
    if _is_refusal(plan):
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 2

    report = {
        "command": "evidence_migration --dry-run" if args.dry_run
                   else "evidence_migration --execute",
        "run_utc": _utc_now_iso(),
        "inputs": inputs.pins(),
        "summary": plan["outputs"],
        "capacity": plan["capacity"],
        "coverage": plan["scan_coverage"],
        "reason_distribution": _reason_distribution(plan["instances"]),
        "manifest_sample": {
            "schema_version": plan["schema_version"],
            "transaction_id": "(minted at apply)",
            "input": plan["input"],
            "instances_sample": plan["instances"][:args.manifest_sample_rows],
            "outputs": {k: v for k, v in plan["outputs"].items()
                        if k != "resource_limited_rows"} | {
                "resource_limited_rows":
                    plan["outputs"]["resource_limited_rows"]},
            "phase": plan["phase"],
        },
    }

    if args.dry_run:
        payload = json.dumps(report, ensure_ascii=False, indent=2)
        print(payload)
        if args.out:
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(payload + "\n", encoding="utf-8")
        return 0

    # --execute: plan must be materialized then applied
    receipt = apply_evd_plan(plan, inputs, gov)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt.get("status") == "applied" else 2


def _reason_distribution(instances):
    dist = {}
    for inst in instances:
        key = (inst["family"], inst["decision"], inst["reason"])
        rows, bytes_ = dist.get(key, (0, 0))
        dist[key] = (rows + 1, bytes_ + inst["byte_length"])
    return [
        {"family": k[0], "decision": k[1], "reason": k[2],
         "rows": v[0], "bytes": v[1]}
        for k, v in sorted(dist.items(), key=lambda kv: (-kv[1][1], kv[0]))]


if __name__ == "__main__":
    raise SystemExit(_cli())
