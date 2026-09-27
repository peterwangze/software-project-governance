#!/usr/bin/env python3
"""
Loop-engineering migration containment — FX-191/FIX-195.

The 0.66.1 implementation is experimental scaffolding. Its current payload is
rejected by the canonical runtime validator before live writes; this module
does not activate the planned persisted Loop runtime.

Implements the ``--apply`` (ADR §7.2) and ``--rollback`` (ADR §7.3) paths for
the classic-G1-G11 → loop-engineering migration.

This is the HIGHEST-complexity slice (L): read-then-write with data-loss
risk on ``plan-tracker.md`` and ``evidence-log.md``. The safety contract is:

  1. **Backup BEFORE write** — the backup + SHA-256 hash step (step 4 of the
     apply algorithm) completes BEFORE any write (steps 6-8). No half-applied
     state is possible: either the backup is verified-on-disk and then the
     writes happen, or we abort having written nothing.
  2. **Fail-closed BEFORE write** — all 5 fail-closed cases abort before any
     write operation. There is no partial state.
  3. **Rollback totality** — rollback restores plan-tracker + evidence-log
     exactly (hash-verified against the backup), removes the runtime.json,
     and appends a ROLLBACK evidence row.

**Dual-root discipline (RISK-040 hard constraint):**
  This module imports resolve_entry DIRECTLY (NOT via verify_workflow) to get
  HOST_PROJECT_ROOT. All ``.governance/`` reads/writes use HOST_PROJECT_ROOT,
  NEVER PLUGIN_HOME. This is the 0.54.2/0.54.3 regression guard: a migration
  that accidentally read/wrote PLUGIN_HOME/.governance/ would corrupt the
  plugin's own evidence store.

  resolve_entry, flow_unit_derive, and the canonical runtime validator are
  PEERS with no verify_workflow dependency. This module never imports the CLI
  adapter; preview remains a local read-only compatibility envelope.

**Anchors (same as resolve_entry.py / loop_engine.py / flow_unit_derive.py):**
  PLUGIN_HOME = Path(__file__).resolve().parent.parent
              (= skills/software-project-governance/, where SKILL.md lives)

**Unit approval manifest (FEAT-070 — DEC-254 B-first; ADR-019 §2.6):**
  ``.governance/flow-unit-approval-manifest.json`` is the authoritative store
  of HUMAN-CONFIRMED task→unit anchoring decisions (§2.6: ambiguity → confirm
  or block, never guess). Each entry carries the four-element record required
  by DEC-254: (task_id + flow_unit_id stable identifier pair,
  confirmation_evidence, repo_version, reviewer). The ONLY sanctioned writers
  are :func:`record_unit_approval` / :func:`record_unit_block` in this
  module; consumers re-validate schema + entries digest on every load, so an
  out-of-chain edit is detected and the whole manifest fails closed (never
  partially consumed). Relationship to flow-unit-runtime.json — NO dual fact
  source: the manifest is the confirmation-side authority; the runtime is the
  machine-maintained derived face written from a confirmed plan (never a
  second mapping authority, ADR §2.2); the dry-run consumes the manifest;
  FEAT-071's structure-anchored derivation shadow consumes this SAME
  structure through the public ``load_approval_manifest`` entry point
  (FEAT-070-R0 P3-5). See the manifest section banner below the helpers
  for the full declaration and the reconnaissance decision record.

Usage:
    from loop_migration import (apply_migration, rollback_migration,
                                preview_migration, load_approval_manifest,
                                derive_structural_units_shadow)
"""

import hashlib
import json
import os
import re
import shutil
import tempfile
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

# ─── Fixed anchors ─────────────────────────────────────────────
# PLUGIN_HOME is derived from __file__ ONLY to locate the plugin's own
# registry files / SKILL.md frontmatter. Same convention as the peer
# modules. NEVER used as the facts root (RISK-040).
PLUGIN_HOME = Path(__file__).resolve().parent.parent

# Import resolve_entry as a PEER (RISK-040 constraint: HOST_PROJECT_ROOT
# must come from resolve_entry, never derived from __file__). resolve_entry
# is pure stdlib and does NOT import verify_workflow — no cycle risk.
from resolve_entry import resolve_host_root, read_active_version  # noqa: E402

# flow_unit_derive is also a peer (pure stdlib). Used for step 5 of apply.
from flow_unit_derive import derive_flow_units  # noqa: E402
from checks.flow_unit_runtime import validate_flow_unit_runtime_payload  # noqa: E402

# FEAT-003 shared migration planner (ADR §4). Both dry-run (preview_migration)
# and apply (apply_migration) call build_migration_plan — this is what makes
# the REL-059 dry-run/apply identity invariant executable: the same pure
# function derives both the preview's plan and the apply's re-derived plan, so
# they cannot disagree (the AUDIT-133 21/19 validator drift is eliminated).
# FEAT-004: confirm_decomposition is the real confirmation gate the apply path
# invokes before plan_to_payload (a v2 payload may only be written from a
# CONFIRMED plan, ADR §5.2).
from loop_migration_plan import (  # noqa: E402
    build_migration_plan,
    plan_to_payload,
    plan_as_dict,
    confirm_decomposition,
    MigrationPlanOptions,
)

# FEAT-002 v2 contract validator (the byte-frozen v1 validator above is
# preserved). The apply path validates the v2 payload via this validator
# BEFORE any write (fail-closed, preserves FIX-195 containment). Imported
# lazily inside _validate_runtime_payload (version-aware dispatch) so a
# missing/renamed v2 module cannot break the v1 containment path at import.
_V2_VALIDATOR = None  # populated lazily; see _validate_runtime_payload


# ═══════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════

MIGRATION_VERSION = "0.65.0"
WORKFLOW_MODEL_NEW = "loop-engineering"
RUNTIME_FILENAME = "flow-unit-runtime.json"
PLAN_TRACKER_FILENAME = "plan-tracker.md"
EVIDENCE_LOG_FILENAME = "evidence-log.md"

# FEAT-070: the unit approval manifest (see the manifest section banner below
# for the storage/relationship declaration). Sits next to
# flow-unit-runtime.json under .governance/ — the tool family's data-file
# pattern — as versioned JSON.
APPROVAL_MANIFEST_FILENAME = "flow-unit-approval-manifest.json"
APPROVAL_MANIFEST_SCHEMA_VERSION = "1.0"
APPROVAL_MANIFEST_ID = "flow-unit-approval-manifest/v1"

# Per-entry four-element record (DEC-254): task/unit stable identifier pair +
# confirmation evidence + repo version + reviewer. ``confirmed_at`` is the
# writer-stamped UTC instant. All required, all non-empty strings — a manifest
# entry missing any of them is corrupt (fail-closed, never partially consumed).
_MANIFEST_ENTRY_REQUIRED_FIELDS = (
    "flow_unit_id", "task_id", "confirmation_evidence",
    "repo_version", "reviewer", "confirmed_at",
)
# Blocked entries record the §2.6 fail-closed trace instead: why the unit is
# NOT confirmable and who recorded the block.
_MANIFEST_BLOCKED_REQUIRED_FIELDS = (
    "flow_unit_id", "reason", "repo_version", "recorded_by", "recorded_at",
)
# Required top-level manifest fields (a hand-written file missing any of them
# is corrupt — the writer family is the only sanctioned producer).
_MANIFEST_TOPLEVEL_REQUIRED_FIELDS = (
    "schema_version", "manifest_id", "project_id",
    "created_at", "updated_at", "revision", "entries", "blocked",
    "entries_digest",
)

# Regex for finding prior migration workflow_model in plan-tracker. Mirrors
# verify_workflow._parse_plan_workflow_model's approach but is intentionally
# lenient: it looks for the workflow_model line anywhere in the tracker and
# returns whatever value follows the separator. This is used to record the
# PRIOR model (for rollback) and for the idempotency guard.
_WORKFLOW_MODEL_LINE_RE = re.compile(
    r"(?im)^\s*[*-]?\s*(?:workflow_model|workflow\s*model|current_workflow_model|"
    r"active_workflow_model|lifecycle_model|工作流模型|当前工作流模型)"
    r"\s*[:：=]\s*(.+?)\s*$"
)

# Evidence-row prefix patterns. We mirror verify_workflow._count_evidence_rows
# (EVD-NNN or REVIEW-...-NNN) plus our own MIGRATION/ROLLBACK rows so the
# "evidence log has no parseable rows" guard treats our own rows as valid too.
_EVIDENCE_ROW_PREFIX_RE = re.compile(
    r"^(?:EVD-\d+|REVIEW-[A-Z]+-\d+|MIGRATION-\d+(?:\.\d+){0,3}|ROLLBACK-\d+(?:\.\d+){0,3})"
)


# ═══════════════════════════════════════════════════════════════════════════
# Low-level helpers
# ═══════════════════════════════════════════════════════════════════════════


def _file_sha256(path):
    """Chunked SHA-256 hex digest of a file.

    Identical algorithm to verify_workflow._file_sha256 (lines 3580-3585):
    read in 64KiB chunks, update the hasher, return hexdigest. Defined
    locally (5 lines) rather than importing verify_workflow, to preserve
    the no-top-level-verify_workflow-import constraint.
    """
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_text(path):
    """Read a file as UTF-8 text. Returns the text or None on read failure."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _resolve_host_root(target_root, plugin_home=None):
    """Resolve HOST_PROJECT_ROOT via resolve_entry (RISK-040).

    Priority: explicit target_root -> resolve_entry.resolve_host_root(None)
    (which tries os.getcwd()). Never falls back to PLUGIN_HOME — if neither
    resolves, we fail-closed (return None).

    Args:
        target_root: Optional explicit path (str/Path). If given and does not
            exist, fail-closed (return None) — we never silently rewrite it.
        plugin_home: Reserved for test injection; currently unused but kept
            for signature symmetry with the public functions.

    Returns:
        A resolved Path, or None if unresolvable (RISK-040 C4 fail-closed).
    """
    if target_root is not None:
        candidate = Path(str(target_root)).expanduser()
        try:
            candidate = candidate.resolve(strict=True)
        except (OSError, RuntimeError):
            return None
        if not candidate.is_dir():
            return None
        return candidate
    # No explicit target: delegate to resolve_entry (which tries cwd).
    return resolve_host_root(None)


def _validate_runtime_payload(state, display):
    """Version-aware runtime payload validation (FEAT-002 routing).

    Routes on ``state.schema_version``: ``"2.0"`` → the FEAT-002 v2 validator;
    ``"1.0"`` / absent → the byte-frozen v1 validator (unchanged). Mirrors
    :func:`checks.flow_unit_runtime.validate_flow_unit_runtime_payload_dispatch`
    but is used here as the post-write readback validator inside the FIX-195
    compensating transaction primitive, so a confirmed v2 payload written by
    FEAT-004 is validated by the v2 contract (not rejected by the v1 shape).

    Returns a list of failure strings (empty ⇒ valid), never raises. The v2
    validator is imported lazily so a v2-module import failure cannot break the
    v1 containment path at module-load time.
    """
    if isinstance(state, dict) and state.get("schema_version") == "2.0":
        global _V2_VALIDATOR
        if _V2_VALIDATOR is None:
            try:
                from checks.flow_unit_runtime_v2 import (
                    validate_flow_unit_runtime_payload_v2,
                )
                _V2_VALIDATOR = validate_flow_unit_runtime_payload_v2
            except ImportError:
                # v2 validator unavailable — fail-closed (the payload claims v2
                # but we cannot validate it). This never silently passes.
                return [
                    "{0}: v2 schema_version claimed but v2 validator unavailable".format(
                        display
                    )
                ]
        return _V2_VALIDATOR(state, display)
    return validate_flow_unit_runtime_payload(state, display)


def _gov_dir(host_root):
    """Return the ``host_root / .governance`` Path."""
    return Path(host_root) / ".governance"


def _plan_tracker_path(host_root):
    return _gov_dir(host_root) / PLAN_TRACKER_FILENAME


def _evidence_log_path(host_root):
    return _gov_dir(host_root) / EVIDENCE_LOG_FILENAME


def _runtime_path(host_root):
    return _gov_dir(host_root) / RUNTIME_FILENAME


def _parse_workflow_model(plan_text):
    """Extract the workflow_model value from a plan-tracker.

    Returns the matched value (lowercased, stripped) or ``"unknown"`` if no
    workflow_model line is found. Used to record the PRIOR model for rollback
    and to guard idempotency (a tracker already claiming loop-engineering
    blocks re-apply).
    """
    if not plan_text:
        return "unknown"
    m = _WORKFLOW_MODEL_LINE_RE.search(plan_text)
    if not m:
        # Heuristic: presence of a Gate tracking table implies classic.
        if "## Gate 状态跟踪" in plan_text or "## gate 状态跟踪" in plan_text:
            return "classic-phase-gate"
        return "unknown"
    value = m.group(1).strip().lower()
    # Strip trailing inline-comment / list markers.
    value = re.split(r"[;；#]", value, maxsplit=1)[0].strip()
    return value or "unknown"


def _count_evidence_rows(evidence_text):
    """Count parseable evidence rows. Mirrors verify_workflow._count_evidence_rows
    but also counts our MIGRATION-/ROLLBACK- rows as valid."""
    if not evidence_text:
        return 0
    count = 0
    for line in evidence_text.splitlines():
        stripped = line.strip()
        # Extract the first cell of a markdown table row.
        first_cell = stripped
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.split("|")]
            # split on '|' yields '' at both ends for bordered rows; the first
            # non-empty cell is the id cell.
            first_cell = next((c for c in cells if c), "")
        if _EVIDENCE_ROW_PREFIX_RE.match(first_cell):
            count += 1
    return count


def _now_utc():
    """Return a timezone-aware UTC datetime (avoids the deprecated utcnow)."""
    return datetime.now(timezone.utc)


def _now_timestamp():
    """Return a filesystem-safe timestamp string (UTC, microsecond precision).

    Microsecond precision (not second) so that two applies within the same
    second — e.g. a fast re-apply right after a rollback — do NOT collide on
    the same backup dir name. The collision is also handled explicitly in
    :func:`_backup_governance_files` via a suffix counter as a belt-and-
    braces guard.
    """
    return _now_utc().strftime("%Y%m%dT%H%M%S%fZ")


def _now_iso():
    """Return an ISO-8601 UTC timestamp."""
    return _now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")


def _archive_dir(host_root, version, timestamp=None):
    """Return the backup dir path: ``.governance/archive/migration-{v}-{ts}/``."""
    ts = timestamp or _now_timestamp()
    return _gov_dir(host_root) / "archive" / "migration-{0}-{1}".format(version, ts)


def _list_migration_backups(host_root):
    """Return all migration backup dirs under .governance/archive/, newest last.

    Each entry is ``(backup_dir, version, timestamp)``. Used by rollback to
    find the most recent (or a specific --version) backup. Returns ``[]`` if
    the archive dir does not exist.

    The timestamp regex accepts EITHER second-precision (legacy, ``%SZ``) or
    microsecond-precision (current, ``%fZ``) names, so backups written by
    older code remain discoverable.
    """
    archive = _gov_dir(host_root) / "archive"
    if not archive.is_dir():
        return []
    found = []
    # Accept: 8-digit date + 6-digit time + optional 6-digit micros + Z,
    # followed by an OPTIONAL collision suffix ("-2", "-3", ...). The suffix
    # is emitted by _backup_governance_files when a microsecond-collision
    # occurs on rapid re-apply.
    pattern = re.compile(
        r"^migration-(?P<ver>\d+\.\d+\.\d+)-(?P<ts>\d{8}T\d{6}(?:\d{6})?Z)(?:-(?P<seq>\d+))?$"
    )
    for entry in sorted(archive.iterdir()):
        if not entry.is_dir():
            continue
        m = pattern.match(entry.name)
        if m:
            found.append((entry, m.group("ver"), m.group("ts")))
    # Sort by the full dir NAME (lexicographic == chronological for this
    # format, with collision suffixes naturally ordering after their base)
    # so the newest is reliably last regardless of FS iteration order.
    found.sort(key=lambda triple: triple[0].name)
    return found


# ═══════════════════════════════════════════════════════════════════════════
# Backup + hash verification
# ═══════════════════════════════════════════════════════════════════════════


def _backup_governance_files(host_root, version):
    """Create a timestamped backup of plan-tracker + evidence-log.

    Creates ``.governance/archive/migration-{version}-{timestamp}/`` and
    copies BOTH plan-tracker.md and evidence-log.md into it. Then computes
    the SHA-256 of each COPIED file (reading from the backup, not the
    source) so the recorded hash provably matches the on-disk backup that
    rollback will later restore from.

    Args:
        host_root: The host project root (already validated).
        version: The migration version (e.g. ``"0.65.0"``).

    Returns:
        ``(backup_dir, hashes)`` where hashes is::

            {
                "plan_tracker_sha256": "<hex>",
                "evidence_log_sha256": "<hex>",
            }

    Raises:
        OSError if the copy fails (the caller treats this as a fail-closed
        abort — the apply algorithm runs this BEFORE any write to the live
        files, so a backup failure means nothing has been mutated yet).
    """
    timestamp = _now_timestamp()
    backup_dir = _archive_dir(host_root, version, timestamp)
    # Collision retry: even with microsecond timestamps, a pathological fast
    # re-apply could collide. Try the base name, then append -2, -3, ... up to
    # a sane cap. This guarantees a unique backup dir (and never overwrites an
    # existing backup — overwriting a backup would defeat the whole safety model).
    collision = 1
    while True:
        try:
            backup_dir.mkdir(parents=True, exist_ok=False)
            break  # success — dir is exclusively ours
        except FileExistsError:
            collision += 1
            if collision > 1000:  # pragma: no cover - defensive cap
                raise OSError(
                    "could not allocate a unique backup dir after 1000 attempts"
                )
            backup_dir = _gov_dir(host_root) / "archive" / "{0}-{1}".format(
                "migration-{0}-{1}".format(version, timestamp), collision
            )

    plan_src = _plan_tracker_path(host_root)
    evidence_src = _evidence_log_path(host_root)
    plan_dst = backup_dir / PLAN_TRACKER_FILENAME
    evidence_dst = backup_dir / EVIDENCE_LOG_FILENAME

    shutil.copy2(plan_src, plan_dst)
    shutil.copy2(evidence_src, evidence_dst)

    # Hash the COPIED files (read from the backup) so the recorded hash is
    # provably the hash of exactly what rollback will restore.
    hashes = {
        "plan_tracker_sha256": _file_sha256(plan_dst),
        "evidence_log_sha256": _file_sha256(evidence_dst),
    }

    # Write a manifest.json into the backup dir. This is the TRUSTED integrity
    # record: rollback reads the manifest (not the files themselves) to get
    # the expected hashes, then verifies the files still match. A tampered
    # file would mismatch the manifest. (Computing expected hashes from the
    # files being verified would be tautological and catch nothing.)
    manifest = {
        "migration_version": version,
        "timestamp": timestamp,
        "created_by": "loop_migration._backup_governance_files",
        "files": {
            PLAN_TRACKER_FILENAME: hashes["plan_tracker_sha256"],
            EVIDENCE_LOG_FILENAME: hashes["evidence_log_sha256"],
        },
    }
    (backup_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return backup_dir, hashes


def _verify_backup_hashes(backup_dir, expected_hashes):
    """Verify that the backed-up files still match the expected SHA-256.

    Reads each backed-up file, recomputes its SHA-256, and compares against
    the expected hashes. This is the integrity check rollback performs BEFORE
    restoring — a tampered/corrupt backup is never silently restored.

    Args:
        backup_dir: The backup directory Path.
        expected_hashes: dict with ``plan_tracker_sha256`` and
            ``evidence_log_sha256`` keys.

    Returns:
        ``(True, [])`` if all hashes match, else ``(False, [mismatch_descriptions])``.
    """
    mismatches = []
    plan_dst = backup_dir / PLAN_TRACKER_FILENAME
    evidence_dst = backup_dir / EVIDENCE_LOG_FILENAME

    for filename, hash_key in (
        (PLAN_TRACKER_FILENAME, "plan_tracker_sha256"),
        (EVIDENCE_LOG_FILENAME, "evidence_log_sha256"),
    ):
        target = backup_dir / filename
        expected = expected_hashes.get(hash_key)
        if not target.is_file():
            mismatches.append(
                "{0}: missing from backup".format(filename)
            )
            continue
        actual = _file_sha256(target)
        if expected is None:
            mismatches.append(
                "{0}: no expected hash recorded".format(filename)
            )
        elif actual != expected:
            mismatches.append(
                "{0}: hash mismatch (expected {1}, got {2})".format(
                    filename, expected, actual
                )
            )
    return (len(mismatches) == 0), mismatches


# ═══════════════════════════════════════════════════════════════════════════
# Commit-window self-heal + orphan backup hygiene (FIX-398 E-4/E-5, RISK-060)
# ═══════════════════════════════════════════════════════════════════════════
#
# The compensating transaction in _commit_runtime_and_evidence restores
# byte-exactly when an exception is raised — but a hard kill (SIGKILL-class)
# between the runtime replace and the evidence replace leaves NO exception
# path: the runtime has landed while the evidence MIGRATION row has not
# (FEAT-068 scenario ⑥ wc6d, 240ms — RISK-060). Re-apply used to hit the
# idempotency guard and refuse without compensating, making a manual
# rollback the only recovery. The heal path below detects that interrupted
# state on re-entry and compensates (remove the half-committed runtime +
# the interrupted attempt's now-orphaned backup dir), after which apply
# proceeds as a fresh, fully-validated 9-step apply.
#
# Reconnaissance decision record (FIX-398 assumption_record, 2026-09-27):
#   - Form chosen: SELF-HEAL RE-ENTRY (interrupted-state detection +
#     compensation), NOT commit-order adjustment. Swapping the order
#     (evidence row first, runtime second) merely relocates the partial
#     state: a kill between the writes would leave a MIGRATION row with no
#     runtime, and re-apply would append a SECOND MIGRATION row for a
#     migration that never completed — a false audit trail, arguably worse
#     than the runtime-without-row window it replaces. Detection+heal keeps
#     the completed-apply marker unambiguous (runtime + row together) and
#     makes every interrupted window point converge to zero partial state
#     or an explicit fail-closed guidance (never an idempotent-refusal
#     deadlock).
#   - Write face (P7 red line): the heal only ever REMOVES the interrupted
#     transaction's own artifacts (the runtime payload this tool family
#     wrote at MIGRATION_VERSION, its scoped mkstemp leftovers, and the
#     interrupted attempt's backup dir whose pre-state snapshots were
#     hash-verified equal to the live files). It never rewrites live
#     plan-tracker/evidence bytes. Ambiguous states (live evidence differing
#     from the transaction's pre-state snapshot) fail closed with explicit
#     guidance instead of guessing. MIGRATION_VERSION is never touched
#     (DEC-257).

# Evidence-row references to backup dirs: apply's MIGRATION row carries
# ``backup=<dir-name>`` and rollback's ROLLBACK row carries
# ``restored_from=<dir-name>``. A backup dir referenced by NEITHER is an
# orphan of a killed/failed apply (E-5). Parsing is restricted to table rows
# whose first cell is one of our row ids so prose mentions never bind.
_BACKUP_REF_ROW_RE = re.compile(
    r"^\|\s*(?:MIGRATION-\d+(?:\.\d+){0,3}|ROLLBACK-\d+(?:\.\d+){0,3})\b"
)
_BACKUP_REF_NAME_RE = re.compile(r"(?:backup|restored_from)=([^\|\s]+)")

# Scoped mkstemp leftovers of an interrupted _atomic_replace_bytes (the temp
# file is only unlinked on the exception path — a hard kill leaves it).
_COMMIT_TEMP_GLOBS = (
    "flow-unit-runtime.json.*.tmp",
    "evidence-log.md.*.tmp",
)


def _referenced_backup_names(evidence_text):
    """Backup dir names referenced by MIGRATION/ROLLBACK evidence rows."""
    names = set()
    if not evidence_text:
        return names
    for line in evidence_text.splitlines():
        stripped = line.strip()
        if not _BACKUP_REF_ROW_RE.match(stripped):
            continue
        m = _BACKUP_REF_NAME_RE.search(stripped)
        if m:
            names.add(m.group(1))
    return names


def _read_runtime_migration_version(runtime_path):
    """Best-effort ``(parses, migration_version)`` read of the runtime face.

    Never raises: an unreadable/unparseable runtime returns ``(False, None)``
    (a runtime this module wrote via _atomic_replace_bytes is always complete
    valid JSON, so an unparseable file is NOT an interrupted-commit artifact
    and must not be healed/touched by this module).
    """
    try:
        data = json.loads(runtime_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return (False, None)
    if isinstance(data, dict) and isinstance(data.get("migration_version"), str):
        return (True, data["migration_version"])
    return (True, None)


def _evidence_has_migration_row(evidence_text, version):
    """True iff evidence-log carries the ``| MIGRATION-<version>`` table row.

    Mirrors the C-10 Face 3 anchor (checks/evidence_domain.py): the stamp
    must be followed by a delimiter, and the row must START the line so prose
    mentions of the stamp never count as the binding row.
    """
    if not evidence_text:
        return False
    marker = re.compile(
        r"^\|\s*MIGRATION-" + re.escape(version) + r"(?=\s*\||\s|$)"
    )
    return any(marker.match(line.strip()) for line in evidence_text.split("\n"))


def _heal_interrupted_commit(host_root, evidence_text):
    """Detect + compensate an interrupted commit window (FIX-398 E-4).

    Detected state: flow-unit-runtime.json parses and claims
    ``migration_version == MIGRATION_VERSION`` while evidence-log.md carries
    NO ``| MIGRATION-<version>`` row. That exact state is only producible by
    a kill inside _commit_runtime_and_evidence between the two atomic
    replaces (the evidence write either fully lands or never lands).

    Compensation (all subtractive, P7-safe):
      1. locate the interrupted attempt's commit-window backup (newest
         MIGRATION_VERSION dir holding an ``evidence.before`` snapshot —
         _commit_runtime_and_evidence always writes the snapshots BEFORE the
         first replace, so the wc6d window guarantees it exists);
      2. verify the live evidence-log is byte-identical to that pre-state
         snapshot (proving the interrupted apply never touched evidence);
         on ANY difference the state is ambiguous (post-kill legal writes vs
         an out-of-chain row deletion) → fail-closed guidance, no auto-heal;
      3. remove the half-committed runtime.json + the interrupted commit's
         scoped .tmp leftovers, then remove the attempt's backup dir (its
         pre-state equals live — zero information loss; E-5).

    Returns a dict:
      ``{"detected": False}`` — not an interrupted commit (heal not armed);
      ``{"detected": True, "healed": True, ...}`` — compensated, apply may
      proceed fresh;
      ``{"detected": True, "healed": False, "guidance": ...}`` — fail-closed:
      the caller must abort with this guidance (rollback is the manual path).
    """
    runtime_path = _runtime_path(host_root)
    if not runtime_path.is_file():
        return {"detected": False}
    parses, version = _read_runtime_migration_version(runtime_path)
    if not parses or version != MIGRATION_VERSION:
        # Not an artifact of this module's commit window (unparseable or a
        # foreign stamp) — never touched here (existing apply semantics
        # govern those states; DEC-257: the stamp contract is not ours to
        # reinterpret in the heal path).
        return {"detected": False}
    if _evidence_has_migration_row(evidence_text, MIGRATION_VERSION):
        # runtime + row = a COMPLETED apply — the idempotency guard's domain.
        return {"detected": False}
    record = {"detected": True, "healed": False, "runtime_version": version}

    snapshot_backups = [
        (entry, ver) for entry, ver, _ts in _list_migration_backups(host_root)
        if ver == MIGRATION_VERSION and (entry / "evidence.before").is_file()
    ]
    if not snapshot_backups:
        record["guidance"] = (
            "interrupted migration commit detected: flow-unit-runtime.json "
            "claims migration_version {0} but evidence-log.md has no "
            "MIGRATION-{0} row, and no commit-window backup with a pre-state "
            "snapshot (evidence.before) exists to verify compensation against. "
            "Auto-heal refused (fail-closed). Recovery: run --rollback "
            "(restores from the newest backup), or resolve the runtime/"
            "evidence state manually. No write performed.".format(MIGRATION_VERSION)
        )
        return record

    backup_dir = snapshot_backups[-1][0]
    record["snapshot_backup"] = backup_dir.name
    live_hash = _file_sha256(_evidence_log_path(host_root))
    snapshot_hash = _file_sha256(backup_dir / "evidence.before")
    record["evidence_matches_pre_state"] = (live_hash == snapshot_hash)
    if live_hash != snapshot_hash:
        record["guidance"] = (
            "interrupted migration commit detected: flow-unit-runtime.json "
            "claims migration_version {0} but evidence-log.md has no "
            "MIGRATION-{0} row; however the live evidence-log differs from "
            "the interrupted transaction's pre-state snapshot ({1}). The "
            "state is ambiguous (post-interruption legal evidence writes vs "
            "an out-of-chain edit) — auto-heal refused (fail-closed; P7: no "
            "guessing with user data). Recovery: run --rollback, or resolve "
            "manually. No write performed.".format(
                MIGRATION_VERSION, backup_dir.name)
        )
        return record

    # Compensate: remove the interrupted commit's scoped temp leftovers,
    # then the half-committed runtime, then the attempt's orphaned backup.
    removed_temps = []
    temp_failures = []
    for pattern in _COMMIT_TEMP_GLOBS:
        for temp in sorted(_gov_dir(host_root).glob(pattern)):
            try:
                temp.unlink()
                removed_temps.append(temp.name)
            except OSError as exc:
                temp_failures.append(
                    "{0}: {1}".format(temp.name, type(exc).__name__)
                )
    try:
        runtime_path.unlink()
    except OSError as exc:
        record["guidance"] = (
            "interrupted migration commit detected but the half-committed "
            "runtime.json could not be removed ({0}: {1}). Recovery: run "
            "--rollback, or remove {2} manually, then re-apply. No other "
            "write performed.".format(type(exc).__name__, exc, runtime_path)
        )
        record["temp_files_removed"] = removed_temps
        record["temp_removal_failures"] = temp_failures
        return record
    record.update({
        "healed": True,
        "runtime_removed": True,
        "temp_files_removed": removed_temps,
        "temp_removal_failures": temp_failures,
    })
    cleaned = _remove_backup_dir_best_effort(backup_dir)
    record["backup_dir_removed"] = backup_dir.name if cleaned else None
    if not cleaned:
        record["backup_dir_removal_failure"] = (
            "orphan backup dir {0} could not be removed; it holds no "
            "unique state (pre-state snapshots equal live files) and will "
            "be swept by the next apply's orphan sweep".format(backup_dir.name)
        )
    return record


def _remove_backup_dir_best_effort(backup_dir):
    """rmtree a backup dir; True on success, False on any OSError (never raises)."""
    try:
        shutil.rmtree(backup_dir)
        return True
    except OSError:
        return False


def _sweep_orphan_migration_backups(host_root, evidence_text):
    """Remove unreferenced, safety-verified orphan backup dirs (FIX-398 E-5).

    An orphan is a MIGRATION_VERSION backup dir referenced by NEITHER a
    MIGRATION row (``backup=``) NOR a ROLLBACK row (``restored_from=``) —
    i.e. an apply that was killed after creating its backup but before
    committing, or whose commit failed and was compensated. Orphans shadow
    rollback's newest-backup selection and accumulate (FEAT-068 scenario ⑦:
    3 residue dirs).

    P7 safety verification (a dir is removed ONLY if provably
    information-free): its manifest parses at this version, its plan-tracker
    copy hash-equals the live plan-tracker (apply never writes the tracker),
    its evidence pre-state (``evidence.before`` snapshot, else the
    ``evidence-log.md`` copy) hash-equals the live evidence-log, and any
    ``runtime.before`` snapshot is empty (a non-empty pre-existing runtime
    snapshot means the pre-apply state had a runtime — manual review, not
    auto-deletion). The sweep is skipped entirely while ANY live runtime
    file exists (foreign/corrupt-runtime hosts keep today's semantics).
    Anything unverifiable is NOT deleted — it is disclosed as skipped.

    Runs immediately before apply creates its new backup, so an apply that
    reaches the write phase always starts from a zero-orphan archive.

    Returns ``{"cleaned": [names], "skipped": [{"name", "reason"}]}``.
    """
    result = {"cleaned": [], "skipped": []}
    if _runtime_path(host_root).is_file():
        result["skipped"].append({
            "name": "*",
            "reason": "sweep skipped: a live flow-unit-runtime.json exists "
                      "(non-fresh host state) — orphan hygiene deferred",
        })
        return result
    referenced = _referenced_backup_names(evidence_text)
    live_plan_hash = _file_sha256(_plan_tracker_path(host_root))
    live_evidence_hash = _file_sha256(_evidence_log_path(host_root))
    for entry, ver, _ts in _list_migration_backups(host_root):
        name = entry.name
        if name in referenced:
            continue  # referenced by a completed migration/rollback — kept
        if ver != MIGRATION_VERSION:
            result["skipped"].append({
                "name": name, "reason": "foreign migration version — untouched",
            })
            continue
        manifest = None
        manifest_path = entry / "manifest.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                manifest = None
        if not isinstance(manifest, dict) or manifest.get("migration_version") != MIGRATION_VERSION:
            result["skipped"].append({
                "name": name,
                "reason": "manifest missing/unreadable/wrong version — "
                          "cannot prove it is information-free",
            })
            continue
        plan_copy = entry / PLAN_TRACKER_FILENAME
        if not plan_copy.is_file() or _file_sha256(plan_copy) != live_plan_hash:
            result["skipped"].append({
                "name": name,
                "reason": "backup plan-tracker differs from live (apply never "
                          "writes the tracker) — not a provable no-write orphan",
            })
            continue
        snapshot = entry / "evidence.before"
        if not snapshot.is_file():
            snapshot = entry / EVIDENCE_LOG_FILENAME
        if (not snapshot.is_file()
                or _file_sha256(snapshot) != live_evidence_hash):
            result["skipped"].append({
                "name": name,
                "reason": "backup evidence pre-state differs from live "
                          "evidence-log — cannot prove zero information loss",
            })
            continue
        runtime_before = entry / "runtime.before"
        if runtime_before.is_file() and runtime_before.stat().st_size > 0:
            result["skipped"].append({
                "name": name,
                "reason": "non-empty runtime.before snapshot (a runtime "
                          "existed pre-apply) — manual review required",
            })
            continue
        if _remove_backup_dir_best_effort(entry):
            result["cleaned"].append(name)
        else:
            result["skipped"].append({
                "name": name, "reason": "rmtree failed (OSError)",
            })
    return result


# ═══════════════════════════════════════════════════════════════════════════
# Evidence-row writers
# ═══════════════════════════════════════════════════════════════════════════


def _append_evidence_row(host_root, row_text):
    """Append a single line to evidence-log.md (creating the file if absent).

    Ensures the row ends with exactly one newline. Does NOT validate the row
    format — callers build the canonical row text.
    """
    evidence_path = _evidence_log_path(host_root)
    line = row_text.rstrip("\n") + "\n"
    if evidence_path.exists():
        existing = _read_text(evidence_path) or ""
        # Ensure exactly one blank-line separator if the file doesn't end in newline.
        if existing and not existing.endswith("\n"):
            existing += "\n"
        evidence_path.write_text(existing + line, encoding="utf-8")
    else:
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(line, encoding="utf-8")


def _atomic_replace_bytes(path, content):
    """Replace one file atomically with prebuilt bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _commit_runtime_and_evidence(runtime_path, runtime_bytes, evidence_path,
                                 evidence_bytes, backup_dir):
    """Commit runtime then evidence, compensating byte-exactly on failure."""
    runtime_existed = runtime_path.is_file()
    runtime_before = runtime_path.read_bytes() if runtime_existed else None
    evidence_before = evidence_path.read_bytes()
    try:
        (backup_dir / "runtime.before").write_bytes(runtime_before or b"")
        (backup_dir / "evidence.before").write_bytes(evidence_before)
    except OSError as exc:
        return {
            "state": "FAIL",
            "issues": ["transaction snapshot failed: {0}".format(type(exc).__name__)],
        }
    try:
        _atomic_replace_bytes(runtime_path, runtime_bytes)
        _atomic_replace_bytes(evidence_path, evidence_bytes)
        runtime_readback = runtime_path.read_bytes()
        evidence_readback = evidence_path.read_bytes()
        post_issues = []
        if runtime_readback != runtime_bytes:
            post_issues.append("runtime post-write readback differs from committed bytes")
        if evidence_readback != evidence_bytes:
            post_issues.append("evidence post-write readback differs from committed bytes")
        try:
            runtime_state = json.loads(runtime_readback.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as readback_exc:
            runtime_state = None
            post_issues.append(
                "runtime post-write readback is invalid JSON: {0}".format(
                    type(readback_exc).__name__
                )
            )
        if runtime_state is not None:
            post_issues.extend(_validate_runtime_payload(runtime_state, str(runtime_path)))
        try:
            evidence_text = evidence_readback.decode("utf-8")
        except UnicodeDecodeError as readback_exc:
            post_issues.append(
                "evidence post-write readback is invalid UTF-8: {0}".format(
                    type(readback_exc).__name__
                )
            )
        else:
            if _count_evidence_rows(evidence_text) == 0:
                post_issues.append("evidence post-write validation found no parseable rows")
        if post_issues:
            raise RuntimeError("post-write validation failed: " + "; ".join(post_issues))
        return {"state": "PASS"}
    except Exception as exc:
        recovery_issues = []
        try:
            if runtime_existed:
                _atomic_replace_bytes(runtime_path, runtime_before)
            elif runtime_path.exists():
                runtime_path.unlink()
        except Exception as recovery_exc:
            recovery_issues.append(
                "runtime recovery failed: {0}".format(type(recovery_exc).__name__)
            )
        try:
            _atomic_replace_bytes(evidence_path, evidence_before)
        except Exception as recovery_exc:
            recovery_issues.append(
                "evidence recovery failed: {0}".format(type(recovery_exc).__name__)
            )
        if recovery_issues:
            journal = backup_dir / "recovery-journal.json"
            journal_payload = {
                "state": "BLOCKED",
                "runtime_path": str(runtime_path),
                "runtime_existed": runtime_existed,
                "evidence_path": str(evidence_path),
                "commit_error": type(exc).__name__,
                "recovery_issues": recovery_issues,
                "runtime_backup": "runtime.before",
                "evidence_backup": "evidence.before",
            }
            result = {
                "state": "BLOCKED",
                "issues": recovery_issues,
                "backup_dir": str(backup_dir),
                "available_backups": ["runtime.before", "evidence.before"],
            }
            try:
                journal.write_text(
                    json.dumps(journal_payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
            except OSError as journal_exc:
                result["journal"] = None
                result["journal_persisted"] = False
                result["issues"] = recovery_issues + [
                    "recovery journal write failed: {0}".format(type(journal_exc).__name__)
                ]
            else:
                result["journal"] = str(journal)
                result["journal_persisted"] = True
            return result
        return {
            "state": "FAIL",
            "issues": [
                "commit failed: {0}: {1}".format(type(exc).__name__, str(exc))
            ],
        }


# ═══════════════════════════════════════════════════════════════════════════
# UNIT APPROVAL MANIFEST (FEAT-070 — DEC-254 B-first; ADR-019 §2.6)
# ═══════════════════════════════════════════════════════════════════════════
#
# Storage decision record (FEAT-070 reconnaissance 2026-09-27, validating the
# execution-packet assumption_record):
#   - CLI form: this CLI family is FLAG-based (argparse with exclusive action
#     flags --dry-run/--apply/--rollback); no peer module uses a subcommand
#     grammar. The approval chain therefore extends the flag family
#     (--record-unit-approval / --record-unit-block + companion flags) and
#     reuses the existing --approve-unit flag as the unit designator.
#   - Storage: the manifest sits NEXT TO flow-unit-runtime.json under
#     .governance/ (the tool family's existing data-file pattern) as JSON
#     with a manifest-level schema_version field.
#
# UNIFIED STORAGE DECLARATION (single-fact-source rule — load-bearing):
#   .governance/flow-unit-approval-manifest.json is the authoritative store of
#   HUMAN-CONFIRMED task→unit anchoring decisions (ADR-019 §2.6: ambiguity →
#   confirm or block, never guess; wrong anchoring is worse than missing).
#   Every entry carries the DEC-254 four-element record. Relationship to
#   flow-unit-runtime.json (NO dual fact source):
#     - the manifest is the CONFIRMATION-side authority (human decisions);
#     - flow-unit-runtime.json is the machine-maintained runtime state the
#       migration tool writes from a confirmed plan — a DERIVED face, never a
#       second mapping authority (ADR-019 §2.2);
#     - preview_migration (dry-run) CONSUMES the manifest and reports the
#       per-unit anchoring status; a derived unit with NO confirmed entry
#       stays §2.6 fail-closed blocked (no prose guessing);
#     - FEAT-071's structure-anchored derivation shadow MUST consume THIS
#       SAME manifest structure (same schema fields, same writer family);
#       a second mapping format would be a dual-fact-source violation.
#
#   The ONLY sanctioned writers are record_unit_approval / record_unit_block
#   below. The consumer re-validates schema + entries digest on every load:
#   an out-of-chain (hand) edit is detected and the WHOLE manifest fails
#   closed — it is never partially consumed.
#
#   DIGEST BOUNDARY NOTE (FEAT-070-R0 P3-4): the entries digest is computed
#   over NFC-NORMALIZED UTF-8 (_sha_text_nfc). Two byte strings that are
#   NFC-equivalent (differing only in Unicode normalization form) hash
#   identically, so an NFC-equivalent rewrite of an entry does NOT trip the
#   out-of-chain-edit detector. This is a deliberate cross-platform
#   consistency trade-off: the digest is an ACCIDENTAL-CHANGE detector
#   (hand edits, schema violations, corruption), NOT an adversarial
#   tamper-proof seal. Byte-exact integrity against an active adversary is
#   outside this manifest's threat model.


def _approval_manifest_path(host_root):
    """Return the ``host_root/.governance/flow-unit-approval-manifest.json`` Path."""
    return _gov_dir(host_root) / APPROVAL_MANIFEST_FILENAME


def _sha_text_nfc(text):
    """SHA-256 hexdigest of the NFC-normalized UTF-8 encoding of ``text``.

    Mirrors the canonical idiom used by loop_migration_plan._sha_text and
    checks/loop_runtime_claims._sha_text so every hash surface in the
    migration family normalizes identically.
    """
    return hashlib.sha256(
        unicodedata.normalize("NFC", text).encode("utf-8")
    ).hexdigest()


def _manifest_entries_digest(entries, blocked):
    """Digest over the manifest's decision payload (entries + blocked only).

    Canonical JSON (sorted keys, compact separators) of ``{"entries": ...,
    "blocked": ...}`` → NFC → SHA-256. Timestamps and revision are EXCLUDED:
    they are bookkeeping, not decisions; the digest guards exactly the
    content a bypass write would have to alter (entries/blocked), which is
    what the consumer re-checks to detect out-of-chain edits.
    """
    canonical = json.dumps(
        {"entries": entries, "blocked": blocked},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )
    return _sha_text_nfc(canonical)


def _validate_approval_manifest_data(data):
    """Validate an approval-manifest dict. Returns a list of issues (empty ⇒ valid).

    Fail-closed contract: ANY issue makes the manifest corrupt, and a corrupt
    manifest is never partially consumed (the caller treats every derived
    unit as unanchored and reports the issues). Checks, in order:
      1. top-level must be a dict;
      2. all required top-level fields present;
      3. schema_version == APPROVAL_MANIFEST_SCHEMA_VERSION and manifest_id
         == APPROVAL_MANIFEST_ID (an unknown schema is refused, not guessed);
      4. entries/blocked are lists of dicts whose required fields are all
         present, non-empty strings;
      5. no duplicate flow_unit_id within entries; none within blocked; no
         unit both confirmed and blocked;
      6. recorded entries_digest equals a recompute over entries+blocked —
         the out-of-chain-edit detector.
    """
    issues = []
    if not isinstance(data, dict):
        return ["unit_manifest_corrupt: top-level JSON value is not an object"]
    for field in _MANIFEST_TOPLEVEL_REQUIRED_FIELDS:
        if field not in data:
            issues.append(
                "unit_manifest_corrupt: missing required top-level field {0!r}".format(field)
            )
    if issues:
        return issues
    if data.get("schema_version") != APPROVAL_MANIFEST_SCHEMA_VERSION:
        issues.append(
            "unit_manifest_corrupt: schema_version {0!r} != supported {1!r}".format(
                data.get("schema_version"), APPROVAL_MANIFEST_SCHEMA_VERSION
            )
        )
    if data.get("manifest_id") != APPROVAL_MANIFEST_ID:
        issues.append(
            "unit_manifest_corrupt: manifest_id {0!r} != {1!r}".format(
                data.get("manifest_id"), APPROVAL_MANIFEST_ID
            )
        )
    revision = data.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        issues.append(
            "unit_manifest_corrupt: revision must be a positive integer, got {0!r}".format(
                revision
            )
        )
    entries = data.get("entries")
    blocked = data.get("blocked")
    if not isinstance(entries, list):
        issues.append("unit_manifest_corrupt: entries is not a list")
        entries = None
    if not isinstance(blocked, list):
        issues.append("unit_manifest_corrupt: blocked is not a list")
        blocked = None
    if entries is not None:
        for entry in entries:
            if not isinstance(entry, dict):
                issues.append(
                    "unit_manifest_corrupt: entries contains a non-object item"
                )
                continue
            for field in _MANIFEST_ENTRY_REQUIRED_FIELDS:
                value = entry.get(field)
                if not isinstance(value, str) or not value.strip():
                    issues.append(
                        "unit_manifest_corrupt: entry {0!r} missing/empty required field {1!r}".format(
                            entry.get("flow_unit_id"), field
                        )
                    )
    if blocked is not None:
        for item in blocked:
            if not isinstance(item, dict):
                issues.append(
                    "unit_manifest_corrupt: blocked contains a non-object item"
                )
                continue
            for field in _MANIFEST_BLOCKED_REQUIRED_FIELDS:
                value = item.get(field)
                if not isinstance(value, str) or not value.strip():
                    issues.append(
                        "unit_manifest_corrupt: blocked entry {0!r} missing/empty required field {1!r}".format(
                            item.get("flow_unit_id"), field
                        )
                    )
    # Duplicate / overlap detection on the id sets (only when shapes allow).
    if isinstance(entries, list) and all(isinstance(e, dict) for e in entries):
        entry_ids = [e.get("flow_unit_id") for e in entries]
        duplicate_entries = sorted({
            fid for fid in entry_ids
            if isinstance(fid, str) and entry_ids.count(fid) > 1
        })
        if duplicate_entries:
            issues.append(
                "unit_manifest_corrupt: duplicate confirmed flow_unit_id(s) {0}".format(
                    duplicate_entries
                )
            )
    if isinstance(blocked, list) and all(isinstance(b, dict) for b in blocked):
        blocked_ids = [b.get("flow_unit_id") for b in blocked]
        duplicate_blocked = sorted({
            fid for fid in blocked_ids
            if isinstance(fid, str) and blocked_ids.count(fid) > 1
        })
        if duplicate_blocked:
            issues.append(
                "unit_manifest_corrupt: duplicate blocked flow_unit_id(s) {0}".format(
                    duplicate_blocked
                )
            )
    if (isinstance(entries, list) and isinstance(blocked, list)
            and all(isinstance(e, dict) for e in entries)
            and all(isinstance(b, dict) for b in blocked)):
        entry_id_set = {e.get("flow_unit_id") for e in entries}
        overlap = sorted(
            fid for fid in (b.get("flow_unit_id") for b in blocked)
            if fid in entry_id_set
        )
        if overlap:
            issues.append(
                "unit_manifest_corrupt: flow_unit_id(s) {0} are both confirmed and blocked".format(
                    overlap
                )
            )
    # Digest verification — the out-of-chain-edit detector. Only meaningful
    # when both decision lists are structurally intact.
    if isinstance(entries, list) and isinstance(blocked, list):
        recomputed = _manifest_entries_digest(entries, blocked)
        recorded = data.get("entries_digest")
        if recorded != recomputed:
            issues.append(
                "unit_manifest_corrupt: entries_digest mismatch (recorded {0!r}, "
                "recomputed {1!r}) — manifest was modified outside the approval "
                "chain".format(recorded, recomputed)
            )
    return issues


def _load_approval_manifest(host_root):
    """Load + validate the approval manifest at host_root.

    Returns ``(state, data, issues)`` where state is one of:
      - ``"absent"``  — no manifest file (data None, issues empty);
      - ``"corrupt"`` — unreadable/invalid/fail-closed (data None, issues set);
      - ``"valid"``   — schema + digest verified (data the parsed dict).

    A corrupt manifest is NEVER partially consumed: data is returned as None
    so callers cannot accidentally consume a subset of a tampered manifest.
    """
    path = _approval_manifest_path(host_root)
    if not path.is_file():
        return ("absent", None, [])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return ("corrupt", None, [
            "unit_manifest_corrupt: manifest at {0} is unreadable/invalid JSON "
            "({1}: {2})".format(path, type(exc).__name__, exc)
        ])
    issues = _validate_approval_manifest_data(data)
    if issues:
        return ("corrupt", None, issues)
    return ("valid", data, [])


def load_approval_manifest(host_root):
    """PUBLIC consumption API for the unit approval manifest (P3-5, FEAT-071).

    Stable entry point for downstream consumers — FEAT-071's structure-
    anchored shadow derivation consumes the manifest THROUGH THIS NAME (no
    private-name imports), and any future reader must do the same so the
    consumption contract has exactly one load-bearing seam.

    Consumption contract (changing it requires a change-triage'd ticket):
      - Returns ``(state, data, issues)`` where ``state`` is:
          "absent"  — no manifest file (``data is None``, ``issues == []``);
          "corrupt" — unreadable/invalid/failed validation (``data is
                      None``; a corrupt manifest is NEVER partially
                      consumed — fail-closed per ADR-019 §2.6);
          "valid"   — schema + entries digest verified (``data`` the dict).
      - Validation covers schema_version/manifest_id, required fields,
        duplicate/overlapping id sets, and the entries_digest
        out-of-chain-edit detector (NFC boundary — see the manifest section
        banner).
      - STRICTLY READ-ONLY. The only sanctioned writers remain
        :func:`record_unit_approval` / :func:`record_unit_block`; the
        manifest is the confirmation-side authority and this loader never
        mutates it.
    """
    return _load_approval_manifest(host_root)


def _empty_approval_manifest(project_id, repo_version):
    """Return a fresh manifest skeleton (schema-versioned, empty decisions)."""
    now = _now_iso()
    return {
        "schema_version": APPROVAL_MANIFEST_SCHEMA_VERSION,
        "manifest_id": APPROVAL_MANIFEST_ID,
        "project_id": project_id,
        "repo_version": repo_version,
        "created_at": now,
        "updated_at": now,
        "revision": 0,  # the writer bumps to 1 on the first recorded decision
        "entries": [],
        "blocked": [],
        "entries_digest": "",
    }


def _write_approval_manifest(host_root, manifest):
    """Digest-stamp, revision-bump, and atomically persist the manifest.

    Called ONLY by the record chain (single-source-writer discipline). The
    digest is recomputed over the final entries+blocked payload, the revision
    is incremented, then the file is replaced atomically. Returns (True, [])
    on success or (False, issues) if the post-write readback fails validation
    (reported honestly — never silently swallowed).
    """
    manifest["revision"] = int(manifest.get("revision", 0)) + 1
    manifest["updated_at"] = _now_iso()
    manifest["entries_digest"] = _manifest_entries_digest(
        manifest["entries"], manifest["blocked"]
    )
    path = _approval_manifest_path(host_root)
    payload = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    _atomic_replace_bytes(path, payload)
    # Post-write readback: reload from disk and re-run the full validator so
    # a failed/tampered write is detected immediately, not on next consume.
    state, readback, readback_issues = _load_approval_manifest(host_root)
    if state != "valid":
        return (False, [
            "manifest post-write readback failed validation (state={0})".format(state)
        ] + readback_issues)
    return (True, [])


def record_unit_approval(target_root=None, flow_unit_id=None, task_id=None,
                         confirmation_evidence=None, reviewer=None,
                         repo_version=None, project_type=None, plugin_home=None):
    """Record ONE human-confirmed task→unit mapping (FEAT-070 confirm chain).

    This is the §2.6 confirmation writer: it validates the inputs, checks the
    unit against the CURRENTLY DERIVED candidate set (an operator cannot
    approve a unit the planner never derived), applies idempotent semantics
    (re-confirming the same unit with the same task REFRESHES the entry in
    place — it never forks a second entry), and persists the versioned
    manifest through the single sanctioned writer.

    Fail-closed refusals (recorded=False, nothing written):
      - unresolvable host root / unknown flow_unit_id / any empty field;
      - existing manifest corrupt (a tampered manifest is never overwritten —
        resolving it is an explicit human action);
      - the unit is already confirmed with a DIFFERENT task_id (a conflicting
        mapping must be adjudicated explicitly, not silently overwritten).

    A unit currently in the blocked list MAY be approved: that is exactly the
    §2.6 adjudication outcome — the block is lifted and the entry records
    ``supersedes_block_reason`` for the trace.

    Returns a structured result dict: ``recorded: True`` with the manifest
    revision and the stored entry, or ``recorded: False`` with a
    ``refused_reason`` (and ``validation_issues`` when the refusal was caused
    by a corrupt manifest).
    """
    started = time.monotonic()
    base = {
        "command": "loop-engineering-migration",
        "mode": "record-unit-approval",
        "recorded": False,
        "target": None,
    }
    # ── Input validation (before any I/O) ───────────────────────────────
    for name, value in (
        ("flow_unit_id", flow_unit_id), ("task_id", task_id),
        ("confirmation_evidence", confirmation_evidence),
        ("reviewer", reviewer), ("repo_version", repo_version),
    ):
        if not isinstance(value, str) or not value.strip():
            return dict(base, refused_reason=(
                "{0} must be a non-empty string (four-element record requires: "
                "task/unit stable identifiers, confirmation evidence, repo "
                "version, reviewer)".format(name)
            ))
    flow_unit_id = flow_unit_id.strip()
    task_id = task_id.strip()

    # ── Resolve host root (RISK-040) ────────────────────────────────────
    host_root = _resolve_host_root(target_root, plugin_home)
    if host_root is None:
        return dict(base, refused_reason=(
            "HOST_PROJECT_ROOT unresolvable (RISK-040 C4 fail-closed): "
            "target_root={0!r}. No manifest write performed.".format(target_root)
        ))
    base["target"] = str(host_root)

    # ── Derive the candidate set: only derived units are approvable ─────
    chosen_project_type = project_type or "ai-agent-plugin"
    try:
        plan = build_migration_plan(
            str(host_root), chosen_project_type, plugin_home=plugin_home,
        )
    except Exception as exc:
        return dict(base, refused_reason=(
            "candidate unit derivation failed ({0}); refusing to record an "
            "approval against an underivable unit set.".format(exc)
        ))
    derived_ids = set(plan.unit_ids)
    if flow_unit_id not in derived_ids:
        return dict(base, refused_reason=(
            "unknown flow_unit_id {0!r}: not in the derived candidate set for "
            "this target (ADR §2.6 — an operator cannot approve a unit the "
            "planner never derived; derived units: {1})".format(
                flow_unit_id, sorted(derived_ids)
            )
        ))

    # ── Load existing manifest (corrupt → refuse, never overwrite) ──────
    state, manifest, issues = _load_approval_manifest(host_root)
    if state == "corrupt":
        return dict(base, refused_reason=(
            "existing approval manifest at {0} is corrupt; refusing to "
            "overwrite it via the approval chain (resolve it explicitly "
            "first)".format(_approval_manifest_path(host_root))
        ), validation_issues=issues)
    if state == "absent":
        manifest = _empty_approval_manifest(plan.project_id, repo_version.strip())

    # ── Apply the decision (idempotent / conflict-checked) ──────────────
    entries = manifest["entries"]
    blocked = manifest["blocked"]
    existing = next((e for e in entries if e.get("flow_unit_id") == flow_unit_id), None)
    if existing is not None and existing.get("task_id") != task_id:
        return dict(base, refused_reason=(
            "conflicting mapping: {0!r} is already confirmed for task {1!r}; "
            "re-mapping it to {2!r} requires explicit adjudication (not a "
            "silent overwrite)".format(
                flow_unit_id, existing.get("task_id"), task_id
            )
        ))
    blocked_entry = next(
        (b for b in blocked if b.get("flow_unit_id") == flow_unit_id), None)
    if blocked_entry is not None:
        blocked.remove(blocked_entry)  # §2.6 adjudication outcome: unblock
    entry = {
        "flow_unit_id": flow_unit_id,
        "task_id": task_id,
        "confirmation_evidence": confirmation_evidence.strip(),
        "repo_version": repo_version.strip(),
        "reviewer": reviewer.strip(),
        "confirmed_at": _now_iso(),
    }
    if blocked_entry is not None:
        entry["supersedes_block_reason"] = blocked_entry.get("reason", "")
    if existing is not None:
        entries[entries.index(existing)] = entry  # idempotent in-place refresh
    else:
        entries.append(entry)
    manifest["repo_version"] = repo_version.strip()

    ok, write_issues = _write_approval_manifest(host_root, manifest)
    if not ok:
        return dict(base, refused_reason=(
            "manifest post-write validation failed; the record was NOT "
            "confirmed reliably"
        ), validation_issues=write_issues)
    base["recorded"] = True
    base["manifest_path"] = str(_approval_manifest_path(host_root))
    base["manifest_revision"] = manifest["revision"]
    base["entry"] = entry
    base["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    return base


def record_unit_block(target_root=None, flow_unit_id=None, reason=None,
                      recorded_by=None, repo_version=None, project_type=None,
                      plugin_home=None):
    """Record ONE §2.6 fail-closed block for a derived unit (FEAT-070 chain).

    The blocking path is the honest half of the confirm chain: a unit the
    operator cannot uniquely interpret is RECORDED as blocked (with the
    ambiguity reason) instead of being silently guessed. Blocked units remain
    §2.6-blocked for every consumer (dry-run reports them as unconfirmed).

    Fail-closed refusals (recorded=False, nothing written):
      - unresolvable root / unknown flow_unit_id / any empty field;
      - existing manifest corrupt (never overwritten);
      - the unit is already CONFIRMED — overturning a confirmation is an
        adjudication decision that must not pass through the block recorder.

    Re-blocking an already-blocked unit refreshes the existing blocked entry
    in place (no fork).

    Returns a structured result dict (mirrors :func:`record_unit_approval`).
    """
    started = time.monotonic()
    base = {
        "command": "loop-engineering-migration",
        "mode": "record-unit-block",
        "recorded": False,
        "target": None,
    }
    for name, value in (
        ("flow_unit_id", flow_unit_id), ("reason", reason),
        ("recorded_by", recorded_by), ("repo_version", repo_version),
    ):
        if not isinstance(value, str) or not value.strip():
            return dict(base, refused_reason=(
                "{0} must be a non-empty string (blocked trace requires: unit, "
                "reason, repo version, recorder)".format(name)
            ))
    flow_unit_id = flow_unit_id.strip()

    host_root = _resolve_host_root(target_root, plugin_home)
    if host_root is None:
        return dict(base, refused_reason=(
            "HOST_PROJECT_ROOT unresolvable (RISK-040 C4 fail-closed): "
            "target_root={0!r}. No manifest write performed.".format(target_root)
        ))
    base["target"] = str(host_root)

    chosen_project_type = project_type or "ai-agent-plugin"
    try:
        plan = build_migration_plan(
            str(host_root), chosen_project_type, plugin_home=plugin_home,
        )
    except Exception as exc:
        return dict(base, refused_reason=(
            "candidate unit derivation failed ({0}); refusing to record a "
            "block against an underivable unit set.".format(exc)
        ))
    if flow_unit_id not in set(plan.unit_ids):
        return dict(base, refused_reason=(
            "unknown flow_unit_id {0!r}: not in the derived candidate set for "
            "this target".format(flow_unit_id)
        ))

    state, manifest, issues = _load_approval_manifest(host_root)
    if state == "corrupt":
        return dict(base, refused_reason=(
            "existing approval manifest at {0} is corrupt; refusing to "
            "overwrite it via the approval chain (resolve it explicitly "
            "first)".format(_approval_manifest_path(host_root))
        ), validation_issues=issues)
    if state == "absent":
        manifest = _empty_approval_manifest(plan.project_id, repo_version.strip())

    entries = manifest["entries"]
    blocked = manifest["blocked"]
    if any(e.get("flow_unit_id") == flow_unit_id for e in entries):
        return dict(base, refused_reason=(
            "flow_unit_id {0!r} is already CONFIRMED in the manifest; "
            "overturning a confirmation is an adjudication decision and cannot "
            "pass through the block recorder".format(flow_unit_id)
        ))
    blocked_entry = {
        "flow_unit_id": flow_unit_id,
        "reason": reason.strip(),
        "repo_version": repo_version.strip(),
        "recorded_by": recorded_by.strip(),
        "recorded_at": _now_iso(),
    }
    existing_block = next(
        (b for b in blocked if b.get("flow_unit_id") == flow_unit_id), None)
    if existing_block is not None:
        blocked[blocked.index(existing_block)] = blocked_entry  # refresh, no fork
    else:
        blocked.append(blocked_entry)
    manifest["repo_version"] = repo_version.strip()

    ok, write_issues = _write_approval_manifest(host_root, manifest)
    if not ok:
        return dict(base, refused_reason=(
            "manifest post-write validation failed; the block was NOT "
            "recorded reliably"
        ), validation_issues=write_issues)
    base["recorded"] = True
    base["manifest_path"] = str(_approval_manifest_path(host_root))
    base["manifest_revision"] = manifest["revision"]
    base["blocked_entry"] = blocked_entry
    base["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    return base


def _build_unit_manifest_face(plan, target_root=None, plugin_home=None):
    """Build the dry-run's unit-approval-manifest consumption face (FEAT-070).

    The face reports, per derived unit, whether its anchoring is human-
    confirmed (manifest entry), explicitly blocked (§2.6 trace), or MISSING
    (no human decision — fail-closed, never prose-guessed). ``ambiguity_count``
    counts derived units WITHOUT a confirmed entry: 0 is the state in which
    dry-run consumes the manifest with zero prose-anchoring ambiguity. When
    the per-unit comparison cannot run (plan derivation failed),
    ``status`` is "indeterminate" and ``ambiguity_count`` is None —
    "not measured", never a misleading zero (FEAT-070-R0 P2-2).

    Fail-closed behavior:
      - manifest absent  → status "absent"; every unit unconfirmed (missing);
      - manifest corrupt → status "corrupt"; NOT partially consumed; every
        unit unconfirmed + the corruption issues surfaced;
      - entries referencing non-derived ids → reported as stale (derivation
        drift against human decisions);
      - manifest project_id ≠ derived project_id → explicit issue.
    """
    face = {
        "status": "consumed",
        "path": None,
        "schema_version": None,
        "revision": None,
        "derived_unit_count": 0,
        "confirmed_count": 0,
        "blocked_count": 0,
        "missing_count": 0,
        "ambiguity_count": 0,
        "confirmed_units": [],
        "unconfirmed_units": [],
        "stale_manifest_entries": [],
        "issues": [],
    }
    derived_ids = list(plan.unit_ids) if plan is not None else None
    face["derived_unit_count"] = len(derived_ids) if derived_ids is not None else 0

    host_root = plan.target_root if plan is not None else None
    if host_root is None:
        resolved = _resolve_host_root(target_root, plugin_home)
        host_root = str(resolved) if resolved else None
    if host_root is None:
        face["status"] = "unresolvable_target"
        face["issues"].append(
            "unit_manifest: target root unresolvable; manifest face skipped"
        )
        return face
    face["path"] = str(_approval_manifest_path(host_root))

    state, data, issues = _load_approval_manifest(host_root)
    face["issues"].extend(issues)
    if derived_ids is None:
        # Plan derivation failed upstream; no unit comparison is possible
        # without a derived set. FEAT-070-R0 P2-2: report this honestly as
        # status "indeterminate" with ambiguity_count None — the former
        # ("consumed", 0) pair was misleading: a consumer reading only
        # ambiguity_count saw a false "zero anchoring ambiguity" although no
        # per-unit comparison had run at all (the skipped note only lived in
        # issues). None = "not measured", never "zero".
        face["status"] = "indeterminate" if state == "valid" else state
        face["ambiguity_count"] = None
        if state == "valid":
            face["schema_version"] = data.get("schema_version")
            face["revision"] = data.get("revision")
        face["issues"].append(
            "unit_manifest: plan derivation failed; per-unit anchoring "
            "comparison skipped (ambiguity_count is None — not measured, "
            "not zero)"
        )
        return face

    if state == "absent":
        face["status"] = "absent"
        face["ambiguity_count"] = len(derived_ids)
        face["unconfirmed_units"] = [
            {"flow_unit_id": uid, "state": "missing",
             "detail": "no approval manifest at this target; prose anchoring "
                       "unresolved (ADR §2.6 fail-closed)"}
            for uid in derived_ids
        ]
        return face
    if state == "corrupt":
        face["status"] = "corrupt"
        face["ambiguity_count"] = len(derived_ids)
        face["unconfirmed_units"] = [
            {"flow_unit_id": uid, "state": "missing",
             "detail": "approval manifest corrupt; not consumed (fail-closed)"}
            for uid in derived_ids
        ]
        return face

    # Valid manifest → exact-id consumption.
    face["schema_version"] = data.get("schema_version")
    face["revision"] = data.get("revision")
    if data.get("project_id") != plan.project_id:
        face["issues"].append(
            "unit_manifest_project_mismatch: manifest project_id {0!r} != "
            "derived {1!r}".format(data.get("project_id"), plan.project_id)
        )
    confirmed = {e["flow_unit_id"]: e for e in data["entries"]}
    blocked = {b["flow_unit_id"]: b for b in data["blocked"]}
    for uid in derived_ids:
        if uid in confirmed:
            face["confirmed_count"] += 1
            face["confirmed_units"].append(uid)
        elif uid in blocked:
            face["blocked_count"] += 1
            face["unconfirmed_units"].append({
                "flow_unit_id": uid, "state": "blocked",
                "detail": blocked[uid].get("reason", ""),
            })
        else:
            face["missing_count"] += 1
            face["unconfirmed_units"].append({
                "flow_unit_id": uid, "state": "missing",
                "detail": "no human decision recorded (ADR §2.6 fail-closed)",
            })
    face["ambiguity_count"] = face["blocked_count"] + face["missing_count"]
    face["stale_manifest_entries"] = sorted(
        (set(confirmed) | set(blocked)) - set(derived_ids)
    )
    if face["stale_manifest_entries"]:
        face["issues"].append(
            "unit_manifest_stale_entries: manifest records decision(s) for "
            "flow_unit_id(s) {0} which the current derivation no longer "
            "produces (derivation drift vs human decisions)".format(
                face["stale_manifest_entries"]
            )
        )
    return face


# ═══════════════════════════════════════════════════════════════════════════
# STRUCTURE-ANCHORED UNIT DERIVATION — SHADOW MODE (FEAT-071; DEC-254 A-after)
# ═══════════════════════════════════════════════════════════════════════════
#
# Design contract (DEC-254 A / ADR-019 §2.6 / FEAT-071 execution packet):
#   - ANCHORING INPUT IS STRUCTURE ONLY. Machine-recorded file evidence from
#     three sources (change-triage ``files``, agent-locks
#     ``files``/``target_files``, plan-tracker task-row path tokens) is
#     mapped onto a FILESYSTEM-DERIVED structural unit universe. Prose
#     descriptions are DISPLAY-LAYER ONLY: they never produce, filter, or
#     rank anchoring candidates (the legacy prose-token derivation is
#     reported as a count/sample only, so its output can be compared — not
#     consumed).
#   - UNIQUENESS (§2.6): a task yields an auto-derivable candidate ONLY when
#     its structural evidence maps to EXACTLY ONE structural unit. Multiple
#     candidates → escalate to the human confirmation chain. Zero evidence →
#     fail-closed (never prose-guessed; historical tasks that predate
#     machine-recorded evidence stay with the human manifest).
#   - SHADOW ZERO-SIDE-EFFECT: this pipeline is strictly READ-ONLY. It
#     writes no manifest, no runtime, no evidence row, no archive, no temp
#     file. Tests pin this with whole-.governance byte snapshots and a
#     determinism/idempotency check. It flips NO authority: the human
#     manifest stays the confirmation-side authority (ADR §2.2); the B→A
#     switch is a separately authorized ticket (DEC-254).
#   - UNIFIED STORAGE (no dual fact source): the human decision list is
#     consumed through the PUBLIC :func:`load_approval_manifest` API
#     (FEAT-070-R0 P3-5) — same schema, same structure, one store.

# Unit-bearing surfaces: first path segment selects the surface, the second
# names the unit (filesystem rule, not prose).
_SHADOW_UNIT_BEARING_SURFACES = (
    ("adapters", "adapter"),
    ("skills", "skill"),
)

# Slash-bearing path tokens (repo-relative files or directories), e.g.
# "skills/x/SKILL.md", "adapters/chrys", ".governance/change-triage/A.json".
_SHADOW_SLASH_PATH_RE = re.compile(
    r"(?<![\w.\-/])"
    r"[A-Za-z0-9._\-]+(?:/[A-Za-z0-9._\-]+)+/?"
    r"(?![\w.\-/])"
)
# Bare filename tokens (no slash), e.g. "test_evidence_binding_drift.py".
# Resolved against the live tree: UNIQUE basename hit → that path (structural
# evidence); MULTIPLE hits → recorded as ambiguous and never anchoring;
# zero hits → unresolved (no evidence).
_SHADOW_BARE_FILENAME_RE = re.compile(
    r"(?<![\w.\-/])"
    r"[A-Za-z0-9][A-Za-z0-9._\-]*\."
    r"(?:py|md|json|txt|toml|yml|yaml|cfg|ini|sh|ps1|bat|cmd)\b"
)
# Task-id shape for plan-tracker table rows (ID cell), e.g. FEAT-071,
# FIX-398, AUDIT-153, TRIAGE-FEAT-068.
_SHADOW_TASK_ID_RE = re.compile(r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+")

_SHADOW_WALK_EXCLUDED_DIRS = frozenset((
    ".git", "node_modules", "__pycache__", ".pytest_cache",
))


def _shadow_project_id(host_root):
    """Sanitized project id fallback (mirrors flow_unit_derive's rule).

    Kept local on purpose: the peer's helper is private and the shadow must
    not import private names from peers. Only used when plan derivation
    fails (the normal path takes project_id from the plan).
    """
    name = Path(str(host_root)).name
    sanitized = re.sub(r"[^a-z0-9.\-]+", "-", name.lower())
    sanitized = re.sub(r"-{2,}", "-", sanitized).strip("-")
    return sanitized or "unknown-project"


def _shadow_normalize_token(raw):
    """Clean one candidate path token; return a repo-relative POSIX path or None.

    Strips wrapping backticks/quotes and trailing punctuation, normalizes
    separators, and rejects non-repo-relative forms (URLs, absolute paths,
    drive letters).
    """
    if not isinstance(raw, str):
        return None
    token = raw.strip().strip("`\"'“”«»").rstrip(".,;:!?、。」』）)]}。")
    token = token.strip("`\"'")
    if not token or token.lower().startswith(("http://", "https://")):
        return None
    if "://" in token or re.match(r"^[A-Za-z]:[\\/]", token):
        return None
    token = token.replace("\\", "/")
    while token.startswith("./"):
        token = token[2:]
    if not token or token.endswith("/"):
        token = token.rstrip("/")
    if not token or "/" not in token and "." not in token.rsplit("/", 1)[-1]:
        return None
    return token


def _shadow_basename_index(root):
    """One-time basename → [relative paths] index of the host tree (read-only)."""
    index = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames if d not in _SHADOW_WALK_EXCLUDED_DIRS
        ]
        for fn in filenames:
            rel = os.path.relpath(
                os.path.join(dirpath, fn), str(root)
            ).replace("\\", "/")
            index.setdefault(fn, []).append(rel)
    return index


def _shadow_add_evidence_path(target, root, raw_token, basename_index=None):
    """Add one raw token's structural evidence to ``target`` (a per-task dict).

    Existing file/dir path → recorded verbatim (structural evidence). Bare
    filename with EXACTLY ONE live hit → resolved to that path. Multiple
    hits → recorded under ``ambiguous_basenames`` and NEVER anchoring (§2.6).
    Anything else → ``unresolved_tokens`` (no evidence implied).
    """
    rel = _shadow_normalize_token(raw_token)
    if rel is None:
        return
    candidate = root / rel
    try:
        if candidate.is_file() or candidate.is_dir():
            target["files"].add(rel)
            return
    except OSError:  # pragma: no cover - defensive (unreadable path component)
        pass
    if basename_index is not None and "/" not in rel:
        hits = sorted(basename_index.get(rel, []))
        if len(hits) == 1:
            target["files"].add(hits[0])
            return
        if len(hits) > 1:
            target["ambiguous_basenames"].setdefault(rel, hits[:5])
            return
    target["unresolved_tokens"].append(rel)


def _shadow_collect_structural_evidence(host_root):
    """Collect machine-recorded task→file evidence from the THREE sources.

    Sources (all read-only, all machine-recorded — no prose):
      S1 ``change_triage_files`` — ``.governance/change-triage/*.json``
         ``task_id`` + ``files`` fields (the change-triage tool's record);
      S2 ``agent_lock_files``    — ``.governance/agent-locks.json``
         ``active_tasks[<id>].files`` + ``target_files`` union;
      S3 ``task_row_paths``      — plan-tracker ACTIVE-task table rows: path
         tokens extracted from the row text (the 任务行修改列 evidence —
         paths appearing in the row's own text, resolved against the tree).

    Returns ``(sources, tasks)``: ``sources`` maps source-key → availability
    detail; ``tasks`` maps task_id → {"files": set of existing repo-relative
    paths, "ambiguous_basenames", "unresolved_tokens", "sources": set}.
    """
    root = Path(host_root)
    tasks = {}
    sources = {}

    def _task(task_id):
        return tasks.setdefault(task_id, {
            "files": set(),
            "ambiguous_basenames": {},
            "unresolved_tokens": [],
            "sources": set(),
        })

    # ── S1: change-triage machine records ────────────────────────────────
    ct_dir = root / ".governance" / "change-triage"
    triage_ok = triage_bad = triage_records = 0
    if ct_dir.is_dir():
        for p in sorted(ct_dir.glob("*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                triage_bad += 1
                continue
            if not isinstance(data, dict):
                triage_bad += 1
                continue
            tid = data.get("task_id")
            files = data.get("files")
            if (not isinstance(tid, str) or not tid.strip()
                    or not isinstance(files, list)):
                triage_bad += 1
                continue
            triage_ok += 1
            record = _task(tid.strip())
            record["sources"].add("change_triage_files")
            for f in files:
                if isinstance(f, str) and f.strip():
                    _shadow_add_evidence_path(record, root, f.strip())
        triage_records = triage_ok
    sources["change_triage_files"] = {
        "available": triage_records > 0,
        "records_with_files_field": triage_records,
        "unreadable_or_malformed": triage_bad,
        "path": str(ct_dir),
    }

    # ── S2: agent-locks machine records ──────────────────────────────────
    locks_path = root / ".governance" / "agent-locks.json"
    lock_records = 0
    if locks_path.is_file():
        try:
            data = json.loads(locks_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            data = None
        if isinstance(data, dict) and isinstance(data.get("active_tasks"), dict):
            for tid, spec in sorted(data["active_tasks"].items()):
                if not isinstance(spec, dict):
                    continue
                record = _task(str(tid))
                touched = False
                for field in ("files", "target_files"):
                    value = spec.get(field)
                    if isinstance(value, list):
                        for f in value:
                            if isinstance(f, str) and f.strip():
                                touched = True
                                _shadow_add_evidence_path(record, root, f.strip())
                if touched:
                    lock_records += 1
                    record["sources"].add("agent_lock_files")
    sources["agent_lock_files"] = {
        "available": lock_records > 0,
        "records_with_file_fields": lock_records,
        "path": str(locks_path),
    }

    # ── S3: plan-tracker active-task rows ────────────────────────────────
    pt_path = root / ".governance" / PLAN_TRACKER_FILENAME
    row_count = 0
    if pt_path.is_file():
        try:
            text = pt_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            text = ""
        basename_index = None
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("|"):
                continue
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) < 3:
                continue
            id_cell = cells[1]
            task_id = id_cell.strip("* ")
            if not _SHADOW_TASK_ID_RE.fullmatch(task_id):
                continue
            row_count += 1
            record = _task(task_id)
            record["sources"].add("task_row_paths")
            if basename_index is None:
                basename_index = _shadow_basename_index(root)
            row_without_id = line.replace(id_cell, " ", 1)
            slash_spans = [
                (m.start(), m.end())
                for m in _SHADOW_SLASH_PATH_RE.finditer(row_without_id)
            ]

            def _in_slash_span(pos, end):
                return any(s <= pos < e for s, e in slash_spans)

            for m in _SHADOW_SLASH_PATH_RE.finditer(row_without_id):
                _shadow_add_evidence_path(record, root, m.group(0),
                                          basename_index)
            for m in _SHADOW_BARE_FILENAME_RE.finditer(row_without_id):
                if not _in_slash_span(m.start(), m.end()):
                    _shadow_add_evidence_path(record, root, m.group(0),
                                              basename_index)
    sources["task_row_paths"] = {
        "available": row_count > 0,
        "task_rows_scanned": row_count,
        "path": str(pt_path),
    }
    return sources, tasks


def _shadow_structural_universe(host_root):
    """Filesystem-derived structural units — the ONLY anchoring targets.

    - adapter unit = a directory under ``adapters/``;
    - skill unit   = a directory under ``skills/`` containing ``SKILL.md``;
    - manifest units: NO structural unit rule exists in this repo layout.
      The manifest-surface FILES are inventoried (skill-core manifests +
      plugin/marketplace surfaces + adapter facets) for reporting, but
      whether they form units — and at what granularity — is undecidable
      from structure alone; §2.6: no unit is generated, adjudication is
      human. Prose names never conjure units into existence.
    """
    root = Path(host_root)
    adapters = {}
    adapters_dir = root / "adapters"
    if adapters_dir.is_dir():
        for child in sorted(adapters_dir.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                adapters[child.name] = {
                    "unit_type": "adapter",
                    "path": "adapters/" + child.name,
                }
    skills = {}
    skills_dir = root / "skills"
    if skills_dir.is_dir():
        for child in sorted(skills_dir.iterdir()):
            if child.is_dir() and (child / "SKILL.md").is_file():
                skills[child.name] = {
                    "unit_type": "skill",
                    "path": "skills/" + child.name,
                }
    manifest_surfaces = []
    for pattern in ("skills/*/core/manifest.json",
                    ".claude-plugin/plugin.json",
                    ".claude-plugin/marketplace.json",
                    "adapters/*/adapter-manifest.json"):
        for p in sorted(root.glob(pattern)):
            if p.is_file():
                manifest_surfaces.append(
                    p.relative_to(root).as_posix()
                )
    return {
        "adapters": adapters,
        "skills": skills,
        "adapter_count": len(adapters),
        "skill_count": len(skills),
        "manifest_surfaces": manifest_surfaces,
        "manifest_unit_rule": (
            "no structural unit rule — manifest-surface files inventoried "
            "only; unit granularity requires human adjudication (ADR §2.6)"
        ),
    }


def _shadow_map_path_to_unit(rel_path):
    """Map one repo-relative path onto its structural unit key (or None).

    Prefix rule (structural, not prose): ``adapters/<name>/…`` →
    ``adapter.<name>``; ``skills/<name>/…`` → ``skill.<name>`` (the adapter
    facet ``adapters/<name>/adapter-manifest.json`` anchors the PARENT
    adapter unit — a facet, not a separate unit). Everything else (docs/,
    .governance/, agents/, root files, .claude-plugin/) is cross-cutting and
    anchors no unit by itself.
    """
    parts = rel_path.split("/")
    for surface, utype in _SHADOW_UNIT_BEARING_SURFACES:
        if len(parts) >= 2 and parts[0] == surface and parts[1]:
            return "{0}.{1}".format(utype, parts[1])
    return None


def _shadow_task_candidates(evidence_tasks):
    """task→unit candidate generation + the §2.6 uniqueness check.

    Per task: candidates = the sorted set of structural units its evidence
    paths map onto. Verdict:
      "unique" — exactly one candidate (auto-derivable; DEC-254 切换判据
                 "仅唯一可解释项转自动");
      "multi"  — two or more candidates (escalate to the confirm chain);
      "none"   — evidence exists but maps to no unit-bearing surface
                 (cross-cutting task) or no structural evidence at all
                 (fail-closed — never prose-guessed).
    Returns rows sorted by task_id (deterministic output).
    """
    rows = []
    for task_id in sorted(evidence_tasks):
        info = evidence_tasks[task_id]
        mapped = set()
        for rel in info["files"]:
            unit_key = _shadow_map_path_to_unit(rel)
            if unit_key is not None:
                mapped.add(unit_key)
        candidates = sorted(mapped)
        if not candidates:
            verdict = "none"
        elif len(candidates) == 1:
            verdict = "unique"
        else:
            verdict = "multi"
        rows.append({
            "task_id": task_id,
            "evidence_sources": sorted(info["sources"]),
            "evidence_files": sorted(info["files"]),
            "ambiguous_basenames": sorted(info["ambiguous_basenames"].items()),
            "unresolved_tokens": sorted(info["unresolved_tokens"]),
            "candidate_units": candidates,
            "verdict": verdict,
        })
    return rows


def _shadow_normalize_name(name):
    """Join-key normalization: NFC + casefold (display variance is not
    anchoring signal — e.g. a human-written ``adapter.Chrys`` joins the
    structural ``adapters/chrys``; the case difference is reported, never
    guessed into the anchor)."""
    return unicodedata.normalize("NFC", name).casefold()


def _shadow_find_structural_unit(universe, unit_type, name):
    """Exact structural-unit lookup by (type, NFC+casefold name)."""
    if unit_type == "adapter":
        bucket = universe["adapters"]
    elif unit_type == "skill":
        bucket = universe["skills"]
    else:
        # No structural rule for other unit types (see the universe docstring).
        return None
    norm = _shadow_normalize_name(name)
    for sname in sorted(bucket):
        if _shadow_normalize_name(sname) == norm:
            return {"name": sname, **bucket[sname]}
    return None


def _shadow_compare_with_manifest(manifest_data, universe,
                                  candidate_rows):
    """28-row shadow comparison: structural pipeline vs the human list.

    Joins each manifest unit (entries = confirmed, blocked = blocked) against
    the structural universe by (unit_type, NFC+casefold name) and reports the
    pipeline verdict, the human decision, and a per-row agreement attribution
    (证据类型 × 唯一性结果 × 与人工决策一致性). DIVERGENCE rows are flagged
    loudly and NEVER auto-resolved — authority stays with the human list.
    A manifest that is not "valid" yields NO rows at all (its data is None —
    fail-closed, never partially consumed); the manifest face reports that
    state separately.
    """
    unique_anchors = {}
    ambiguous_mentions = {}
    for row in candidate_rows:
        for key in row["candidate_units"]:
            if row["verdict"] == "unique":
                unique_anchors.setdefault(key, []).append(row["task_id"])
            else:
                ambiguous_mentions.setdefault(key, []).append(row["task_id"])

    rows = []
    if isinstance(manifest_data, dict):
        decision_sets = (
            [("confirmed", e) for e in manifest_data.get("entries", [])
             if isinstance(e, dict)],
            [("blocked", b) for b in manifest_data.get("blocked", [])
             if isinstance(b, dict)],
        )
    else:
        decision_sets = ((), ())

    for decision, item in decision_sets[0] + decision_sets[1]:
        unit_id = item.get("flow_unit_id", "")
        parts = unit_id.split(".")
        unit_type = parts[-2] if len(parts) >= 2 else ""
        name = parts[-1] if parts else unit_id
        structural = _shadow_find_structural_unit(universe, unit_type, name)
        row = {
            "manifest_unit_id": unit_id,
            "unit_type": unit_type,
            "manifest_name": name,
            "human_decision": decision,
            "human_task": item.get("task_id") if decision == "confirmed" else None,
            "structural_unit": structural,
            "name_normalization_applied": bool(
                structural is not None and structural["name"] != name
            ),
            "unique_anchor_tasks": [],
            "ambiguous_mention_tasks": [],
        }
        if structural is None:
            row["pipeline_verdict"] = "no_structural_unit"
            row["evidence_types"] = []
            if unit_type not in ("adapter", "skill"):
                row["agreement_note"] = (
                    "unit_type has no structural unit rule in this repo "
                    "layout (manifest-surface family inventoried only)"
                )
        else:
            key = "{0}.{1}".format(unit_type, structural["name"])
            row["unique_anchor_tasks"] = sorted(unique_anchors.get(key, []))
            row["ambiguous_mention_tasks"] = sorted(
                ambiguous_mentions.get(key, []))
            row["evidence_types"] = sorted({
                src for r in candidate_rows
                if key in r["candidate_units"]
                for src in r["evidence_sources"]
            })
            if row["unique_anchor_tasks"]:
                row["pipeline_verdict"] = "reproducible"
            elif row["ambiguous_mention_tasks"]:
                row["pipeline_verdict"] = "structural_match_multi_candidate"
            else:
                row["pipeline_verdict"] = "structural_match_no_evidence"

        # Agreement attribution (§2.6 discipline — authority stays human).
        if decision == "confirmed":
            if row["pipeline_verdict"] == "reproducible":
                row["agreement"] = "consistent_reproduction"
                row["agreement_note"] = (
                    "structural evidence independently reproduces the human "
                    "confirmation"
                )
            elif row["pipeline_verdict"] == "structural_match_no_evidence":
                row["agreement"] = "consistent_no_evidence"
                row["agreement_note"] = (
                    "structural unit exists; current machine evidence cannot "
                    "re-derive the confirmation (historical predates "
                    "machine-recorded evidence) — human entry stands, no "
                    "prose fallback (ADR §2.6)"
                )
            elif row["pipeline_verdict"] == "structural_match_multi_candidate":
                row["agreement"] = "consistent_block_multi_candidate"
                row["agreement_note"] = (
                    "structural unit exists but evidence is multi-candidate; "
                    "the human confirmation stays the authority"
                )
            else:
                row["agreement"] = "DIVERGENCE"
                row["agreement_note"] = (
                    "human CONFIRMED a unit the structural universe cannot "
                    "see — escalate; never auto-resolve"
                )
        else:  # blocked
            if row["pipeline_verdict"] == "no_structural_unit":
                row["agreement"] = "consistent_absence"
                row["agreement_note"] = (
                    "structure-only input produces no such unit — the prose "
                    "token never enters anchoring (DEC-258: 此类项自然消失)"
                )
            elif row["pipeline_verdict"] == "structural_match_no_evidence":
                row["agreement"] = "consistent_block_no_evidence"
                row["agreement_note"] = (
                    "structural unit exists but no machine evidence anchors "
                    "it — block stands (§2.6 fail-closed)"
                )
            elif row["pipeline_verdict"] == "structural_match_multi_candidate":
                row["agreement"] = "consistent_block_multi_candidate"
                row["agreement_note"] = (
                    "multi-candidate evidence — stays on the human "
                    "confirmation chain (§2.6 escalate)"
                )
            else:
                row["agreement"] = "DIVERGENCE"
                row["agreement_note"] = (
                    "structure derives a unique anchor the human BLOCKED — "
                    "escalate; never auto-flip a human decision"
                )
        rows.append(row)

    counts = {}
    for row in rows:
        counts[row["agreement"]] = counts.get(row["agreement"], 0) + 1
    verdict_counts = {}
    for row in rows:
        verdict_counts[row["pipeline_verdict"]] = (
            verdict_counts.get(row["pipeline_verdict"], 0) + 1
        )
    return {
        "rows": rows,
        "agreement_counts": counts,
        "pipeline_verdict_counts": verdict_counts,
        "row_count": len(rows),
    }


def derive_structural_units_shadow(target_root=None, project_type=None,
                                   plugin_home=None):
    """Run the structure-anchored derivation pipeline in SHADOW mode.

    FEAT-071 (DEC-254 A-after): structural evidence from three machine
    sources → task→unit candidates → §2.6 uniqueness check → comparison
    against the human approval manifest. STRICTLY READ-ONLY (zero writes —
    pinned by tests) and DETERMINISTIC (no wall-clock in the result, so
    repeated runs are byte-identical). Authority is NOT flipped: the human
    manifest remains the confirmation-side authority; the B→A switch is a
    separately authorized decision.

    Args:
        target_root: Host project root (str/Path), or None (resolve_entry).
        project_type: Optional project type for the legacy prose plan face
            (display only). Defaults to ``"ai-agent-plugin"``.
        plugin_home: Optional plugin-home override (mainly for tests).

    Returns:
        A JSON-serializable dict (``mode: "shadow-derive"``) with:
        ``evidence_sources``, ``structural_universe``,
        ``prose_face_display_only``, ``task_candidates``,
        ``anchor_candidates`` (unique-verdict rows only), ``manifest_face``,
        ``comparison`` (rows + agreement counts), ``switch_judgment_inputs``
        (machine-checkable counts feeding the B→A criteria), and
        ``zero_side_effect``. On an unresolvable target: fail-closed with
        ``shadow_derived: False``.
    """
    base = {
        "command": "loop-engineering-migration",
        "mode": "shadow-derive",
        "target": None,
    }
    host_root = _resolve_host_root(target_root, plugin_home)
    if host_root is None:
        return dict(base, shadow_derived=False, aborted_reason=(
            "HOST_PROJECT_ROOT unresolvable (RISK-040 C4 fail-closed): "
            "target_root={0!r}. No read or write performed.".format(target_root)
        ))
    host_root = Path(host_root)
    base["target"] = str(host_root)

    # Legacy prose face — DISPLAY ONLY (count/sample, never an anchor input).
    chosen_project_type = project_type or "ai-agent-plugin"
    prose_face = {
        "note": ("legacy prose-token derivation — display layer only; its "
                 "units are reported for comparison and are NOT anchoring "
                 "inputs (DEC-254 A)"),
        "derived_unit_count": None,
        "prose_unit_ids": [],
        "workflow_model_prior": None,
        "plan_hash": None,
    }
    project_id = _shadow_project_id(host_root)
    try:
        plan = build_migration_plan(
            str(host_root), chosen_project_type, plugin_home=plugin_home,
        )
        prose_face["derived_unit_count"] = plan.unit_count
        prose_face["prose_unit_ids"] = sorted(plan.unit_ids)
        prose_face["workflow_model_prior"] = plan.workflow_model_prior
        prose_face["plan_hash"] = plan.plan_hash
        project_id = plan.project_id
    except Exception as exc:  # planner fail-closed → report, never guess
        prose_face["plan_derivation_error"] = str(exc)

    universe = _shadow_structural_universe(host_root)
    sources, evidence_tasks = _shadow_collect_structural_evidence(host_root)
    candidate_rows = _shadow_task_candidates(evidence_tasks)
    anchor_rows = [r for r in candidate_rows if r["verdict"] == "unique"]

    state, manifest_data, issues = load_approval_manifest(host_root)
    manifest_face = {
        "state": state,
        "path": str(_approval_manifest_path(host_root)),
        "project_id": None,
        "revision": None,
        "confirmed_count": 0,
        "blocked_count": 0,
        "issues": list(issues),
    }
    if state == "valid":
        manifest_face["project_id"] = manifest_data.get("project_id")
        manifest_face["revision"] = manifest_data.get("revision")
        manifest_face["confirmed_count"] = len(manifest_data.get("entries", []))
        manifest_face["blocked_count"] = len(manifest_data.get("blocked", []))
        if manifest_data.get("project_id") != project_id:
            manifest_face["issues"].append(
                "unit_manifest_project_mismatch: manifest project_id {0!r} != "
                "derived {1!r}".format(manifest_data.get("project_id"), project_id)
            )

    comparison = _shadow_compare_with_manifest(
        manifest_data, universe, candidate_rows,
    )

    structural_keys = sorted(
        ["adapter.{0}".format(n) for n in universe["adapters"]]
        + ["skill.{0}".format(n) for n in universe["skills"]]
    )
    # Membership uses the SAME NFC+casefold join as the comparison: a human
    # decision written as "…adapter.Chrys" (project-prefixed, display case)
    # covers the structural "adapter.chrys".
    decided_keys = set()
    if state == "valid":
        for item in manifest_data.get("entries", []) + manifest_data.get("blocked", []):
            if isinstance(item, dict):
                parts = item.get("flow_unit_id", "").split(".")
                if len(parts) >= 2:
                    decided_keys.add("{0}.{1}".format(
                        parts[-2], _shadow_normalize_name(parts[-1])))
    structural_by_norm = {
        "{0}.{1}".format(k.split(".", 1)[0],
                         _shadow_normalize_name(k.split(".", 1)[1])): k
        for k in structural_keys
    }
    switch_inputs = {
        "confirmed_units_reproduced_by_structure": comparison[
            "agreement_counts"].get("consistent_reproduction", 0),
        "confirmed_units_without_machine_evidence": comparison[
            "agreement_counts"].get("consistent_no_evidence", 0),
        "divergence_count": comparison["agreement_counts"].get("DIVERGENCE", 0),
        "rows_without_agreement_attribution": comparison["agreement_counts"].get(
            "not_comparable", 0),
        "unique_anchor_candidate_count": len(anchor_rows),
        "multi_candidate_task_count": sum(
            1 for r in candidate_rows if r["verdict"] == "multi"),
        "no_candidate_task_count": sum(
            1 for r in candidate_rows if r["verdict"] == "none"),
        "structural_units_total": len(structural_keys),
        "structural_units_without_human_decision": sorted(
            structural_by_norm[nk] for nk in structural_by_norm
            if nk not in decided_keys),
        "manifest_project_id": manifest_face["project_id"],
        "derived_project_id": project_id,
    }

    return dict(base, shadow_derived=True,
                project_id=project_id,
                evidence_sources=sources,
                structural_universe={
                    "adapter_count": universe["adapter_count"],
                    "skill_count": universe["skill_count"],
                    "adapters": sorted(universe["adapters"]),
                    "skills": sorted(universe["skills"]),
                    "manifest_surfaces": universe["manifest_surfaces"],
                    "manifest_unit_rule": universe["manifest_unit_rule"],
                },
                prose_face_display_only=prose_face,
                task_candidates=candidate_rows,
                anchor_candidates=anchor_rows,
                manifest_face=manifest_face,
                comparison=comparison,
                switch_judgment_inputs=switch_inputs,
                zero_side_effect={
                    "write_operations": 0,
                    "note": ("strictly read-only shadow: no manifest/runtime/"
                             "evidence/archive/temp writes; pinned by "
                             "test_loop_structural_derivation zero-write arms"),
                })


# ═══════════════════════════════════════════════════════════════════════════
# APPLY (ADR §7.2 — 9 steps)
# ═══════════════════════════════════════════════════════════════════════════


def apply_migration(target_root=None, project_type=None, plugin_home=None,
                    expected_plan_hash=None, approved_unit_ids=None):
    """Execute the classic → loop-engineering migration (ADR §7.2, 9 steps).

    This is a read-then-write operation with data-loss risk. The safety
    ordering is strict:

      Steps 1-4 are READS + BACKUP only — no live file is mutated.
      Step 4 (backup) completes and its hashes are recorded BEFORE any write.
      Steps 5-8 are WRITES, and only run if every fail-closed check (steps
      1-3, 5) passed AND the backup succeeded.
      Step 9 is the structured result print (caller's responsibility).

    Fail-closed cases (abort BEFORE any write, returning ``applied: False``):
      - Missing plan-tracker / evidence-log
      - Evidence log has no parseable rows
      - HOST_PROJECT_ROOT unresolvable (RISK-040 C4)
      - Target already claims loop-engineering active (idempotency)
      - Derived flow units = 0 (FX-190 fallback prevents this; guarded anyway)
      - plan_hash mismatch (expected_plan_hash supplied and disagrees)
      - FEAT-004: decomposition confirmation fails (bad candidate set, or
        approved_unit_ids references unknown ids) — abort BEFORE any write

    On fail-closed, NOTHING is written — no backup dir, no runtime.json, no
    evidence row. The caller (cmd_*) inspects ``result["applied"]`` and
    exits non-zero when False.

    FEAT-004 (ADR §5.2): apply CONFIRMS the decomposition before building the
    payload. With ``approved_unit_ids=None`` the full derived set is confirmed
    wholesale; with an explicit list only those units are written. Confirmation
    runs AFTER the plan-hash verification (so the hash check still anchors the
    candidate plan) and BEFORE ``plan_to_payload`` (so the persisted payload is
    always built from a CONFIRMED plan and passes the v2 validator).

    Args:
        target_root: Explicit host project root (str/Path). If None, resolved
            from os.getcwd() via resolve_entry.
        project_type: Project type for flow-unit derivation
            (game/cli-tool/library/...). If None, defaults to
            ``"ai-agent-plugin"`` (the plugin's own type — a safe fallback
            that always yields at least one unit via flow_unit_derive's
            fallback path).
        plugin_home: Optional override for the flow_unit_derive registry
            lookup. Mainly for tests.
        expected_plan_hash: Optional 64-hex plan hash for apply-path hash
            verification (FEAT-003, ADR §4.4). When supplied, the apply path
            re-derives the plan via :func:`build_migration_plan` and asserts the
            re-derived ``plan_hash`` equals this value; a mismatch fail-closes
            BEFORE any write (no backup, no runtime, no evidence row). This is
            the executable REL-059 invariant: the dry-run's serialized plan and
            the apply's re-derived plan MUST have identical structure. NOTE:
            this hash is the CANDIDATE plan's hash (pre-confirmation); a subset
            ``approved_unit_ids`` produces a DIFFERENT confirmed plan_hash, which
            is reported in the result but is not subject to this check (the
            operator approves a subset, deliberately changing the structure).
        approved_unit_ids: Optional iterable of operator-approved
            ``flow_unit_id`` strings (FEAT-004). When ``None`` the full derived
            set is confirmed wholesale; when supplied only those units are
            written (dependencies filtered to the remaining set). Unknown ids
            or an empty list fail-closed before any write.

    Returns:
        A result dict. On success::

            {
                "command": "loop-engineering-migration",
                "mode": "apply",
                "applied": True,
                "target": str(host_root),
                "workflow_model": {"prior": "...", "new": "loop-engineering"},
                "backup_dir": str(backup_path),
                "hashes": {"plan_tracker_before": ..., "plan_tracker_after": ...,
                           "evidence_log_before": ..., "evidence_log_after": ...},
                "flow_units_derived": N,
                "evidence_row": "MIGRATION-{version}",
                "plan_hash": "<confirmed plan hash>",
                "no_overclaim_boundary": "..."
            }

        On fail-closed::

            {"applied": False, "aborted_reason": "...", "target": str_or_None, ...}
    """
    base_result = {
        "command": "loop-engineering-migration",
        "mode": "apply",
        "applied": False,
        "target": None,
    }

    # ── Step 1: resolve HOST_PROJECT_ROOT (RISK-040 C1-C5) ──────────────
    host_root = _resolve_host_root(target_root, plugin_home)
    if host_root is None:
        return dict(base_result, aborted_reason=(
            "HOST_PROJECT_ROOT unresolvable (RISK-040 C4 fail-closed): "
            "target_root={0!r} did not resolve to an existing directory and "
            "cwd fallback failed. No write performed.".format(target_root)
        ))
    base_result["target"] = str(host_root)

    plan_path = _plan_tracker_path(host_root)
    evidence_path = _evidence_log_path(host_root)

    # ── Fail-closed: missing plan-tracker ───────────────────────────────
    if not plan_path.is_file():
        return dict(base_result, aborted_reason=(
            "missing {0} at {1}; migration requires an existing classic "
            "plan-tracker. No write performed.".format(
                PLAN_TRACKER_FILENAME, plan_path
            )
        ))
    # ── Fail-closed: missing evidence-log ───────────────────────────────
    if not evidence_path.is_file():
        return dict(base_result, aborted_reason=(
            "missing {0} at {1}; migration requires an existing evidence "
            "log with parseable rows. No write performed.".format(
                EVIDENCE_LOG_FILENAME, evidence_path
            )
        ))

    # ── Step 2 + 3: read + hash (BEFORE any write) ──────────────────────
    plan_text = _read_text(plan_path)
    if plan_text is None:
        return dict(base_result, aborted_reason=(
            "could not read {0} (UTF-8 decode/IO error). No write performed.".format(
                plan_path
            )
        ))
    evidence_text = _read_text(evidence_path)
    if evidence_text is None:
        return dict(base_result, aborted_reason=(
            "could not read {0} (UTF-8 decode/IO error). No write performed.".format(
                evidence_path
            )
        ))

    plan_tracker_before_hash = _file_sha256(plan_path)
    evidence_log_before_hash = _file_sha256(evidence_path)

    # ── Fail-closed: evidence log has no parseable rows ─────────────────
    if _count_evidence_rows(evidence_text) == 0:
        return dict(base_result, aborted_reason=(
            "evidence-log has no parseable evidence rows; migration requires "
            "at least one row to anchor the migration record. No write performed."
        ))

    # ── FIX-398 E-4: interrupted-commit detection + self-heal (RISK-060) ──
    # A kill between the runtime replace and the evidence replace leaves the
    # runtime landed with no MIGRATION row; without this heal, re-apply hit
    # the idempotency guard below and refused without compensating (the wc6d
    # partial state — rollback was the only recovery). Healed state must be
    # resolved BEFORE the guard so re-entry converges to a fresh, fully
    # validated apply instead of a refusal deadlock. On any fail-closed arm
    # the heal returns explicit guidance and apply aborts without writing.
    heal = _heal_interrupted_commit(host_root, evidence_text)
    if heal.get("detected") and not heal.get("healed"):
        return dict(base_result, aborted_reason=heal["guidance"],
                    interrupted_commit=heal)

    # ── Fail-closed: idempotency (runtime.json already at target version) ──
    # A future contract-valid runtime.json is the idempotency marker. The
    # current proposal is not contract-valid and cannot reach this state.
    # The plan-tracker is NOT consulted here: apply NEVER modifies the
    # plan-tracker, so a plan-tracker-based guard could never fire on
    # double-apply (the tracker retains its original "classic-phase-gate"
    # value forever). Only a runtime.json whose migration_version matches
    # the version being applied proves a prior apply completed. This runs
    # BEFORE the backup step so a double-apply attempt does NOT create a
    # spurious backup dir or a duplicate MIGRATION row.
    prior_model = _parse_workflow_model(plan_text)
    runtime_path = _runtime_path(host_root)
    if runtime_path.is_file():
        try:
            existing_runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing_runtime = None
        if (isinstance(existing_runtime, dict)
                and existing_runtime.get("migration_version") == MIGRATION_VERSION):
            return dict(base_result, aborted_reason=(
                "idempotency: target already migrated to loop-engineering "
                "version {0}; use --rollback first if you need to re-apply".format(
                    MIGRATION_VERSION
                )
            ))

    # ── Step 4: build the migration plan via the PURE planner (FEAT-003) ──
    # ADR §4.4: apply RE-DERIVES the plan via build_migration_plan (the same
    # pure function the dry-run uses). The plan-derivation interior (resolve
    # root, read plan-tracker, derive units, build payload) is extracted into
    # the planner; the backup/commit/compensation scaffolding below (steps 5+)
    # is UNCHANGED. This is what eliminates the AUDIT-133 dry-run/apply drift:
    # both paths call the same function, so they cannot disagree.
    chosen_project_type = project_type or "ai-agent-plugin"
    apply_options = MigrationPlanOptions(expected_plan_hash=expected_plan_hash)
    try:
        plan = build_migration_plan(
            str(host_root), chosen_project_type,
            plan_tracker_text=plan_text, plugin_home=plugin_home,
            options=apply_options,
        )
    except Exception as exc:  # defensive: the planner must not raise
        return dict(base_result, aborted_reason=(
            "migration plan derivation raised ({0}); aborting before any host "
            "write. No backup, runtime, or evidence file was created.".format(exc)
        ))

    # ── Fail-closed: derived flow units = 0 ─────────────────────────────
    # (FX-190's fallback prevents this in practice, but we guard anyway so a
    # future regression can never produce an empty runtime.)
    if plan.unit_count == 0:
        return dict(base_result, aborted_reason=(
            "derived flow units = 0; refusing to write an empty runtime. "
            "No host write performed."
        ))

    # ── FEAT-003: apply-path hash verification (ADR §4.4) ───────────────
    # If a hash was supplied (the dry-run's serialized plan_hash), assert the
    # re-derived plan's hash equals it. A mismatch means the dry-run and apply
    # disagree on structure → fail-closed BEFORE any write. This is the
    # executable REL-059 dry-run/apply identity invariant. This anchors the
    # CANDIDATE plan (pre-confirmation); the confirmed plan's hash may differ
    # when approved_unit_ids filters the set, and is reported in the result.
    if expected_plan_hash is not None and plan.plan_hash != expected_plan_hash:
        return dict(base_result, aborted_reason=(
            "plan_hash mismatch: expected {0} but re-derived {1}; the dry-run "
            "and apply plans disagree on structure. No write performed.".format(
                expected_plan_hash, plan.plan_hash
            )
        ))

    # ── FEAT-004: confirm the decomposition (ADR §5.2) ──────────────────
    # The apply path MUST confirm the plan before building the payload — a v2
    # payload may only be written from a CONFIRMED plan (the v2 validator's
    # decomposition_confirmed requirement is the executable containment guard).
    # With approved_unit_ids=None the full derived set is confirmed wholesale;
    # with an explicit list only those units survive. Any confirmation failure
    # (bad candidate set, unknown approved ids, empty set) fail-closes BEFORE
    # any write — no backup, no runtime, no evidence row. FIX-195 containment
    # is preserved: the backup/commit/compensation scaffolding below is
    # UNCHANGED; this confirmation sits between the hash check and
    # plan_to_payload, both of which precede the backup step.
    try:
        confirmed_plan = confirm_decomposition(
            plan, approved_unit_ids=approved_unit_ids,
        )
    except ValueError as exc:
        return dict(base_result, aborted_reason=(
            "decomposition confirmation failed ({0}); the candidate set is "
            "invalid or the approved_unit_ids are inconsistent. No host write "
            "performed.".format(exc)
        ), workflow_model={"prior": plan.workflow_model_prior, "new": WORKFLOW_MODEL_NEW},
           flow_units_derived=plan.unit_count, plan_hash=plan.plan_hash)

    # ── Build the v2 runtime payload from the CONFIRMED plan (ADR §5.3) ─
    # plan_to_payload bridges the confirmed plan → v2 contract payload. The v2
    # validator then enforces the FEAT-002 contract §3.2/3.3/3.4 invariants.
    # Because the plan is confirmed, the payload's decomposition_confirmed is
    # true and the v2 validator passes (the containment guard is satisfied).
    runtime_payload = plan_to_payload(
        confirmed_plan, migration_version=MIGRATION_VERSION,
        migration_timestamp=_now_iso(), plugin_home=plugin_home,
    )
    runtime_path = _runtime_path(host_root)
    validation_issues = _validate_runtime_payload(
        runtime_payload, str(runtime_path)
    )
    if validation_issues:
        return dict(
            base_result,
            aborted_reason=(
                "planned loop-engineering runtime is incompatible with the "
                "v2 Loop Runtime Contract; no host write performed "
                "(decomposition was confirmed but the v2 validator rejected "
                "the payload)"
            ),
            validation_issues=validation_issues,
            workflow_model={"prior": plan.workflow_model_prior, "new": WORKFLOW_MODEL_NEW},
            flow_units_derived=confirmed_plan.unit_count,
            plan_hash=confirmed_plan.plan_hash,
        )

    # The flow_units count used downstream (audit trail) comes from the plan.
    flow_units = runtime_payload["flow_units"]

    # ── FIX-398 E-5: orphan backup sweep (before creating the new backup) ──
    # Any apply that reaches the write phase first removes provably
    # information-free, unreferenced backup dirs left by killed/failed
    # attempts, so the archive never accumulates roll-back-shadowing orphans
    # (FEAT-068 scenario ⑦). Unverifiable dirs are kept and disclosed.
    orphan_sweep = _sweep_orphan_migration_backups(host_root, evidence_text)

    # ── Step 5: backup live governance facts after validation ───────────
    try:
        backup_dir, backup_hashes = _backup_governance_files(
            host_root, MIGRATION_VERSION
        )
    except OSError as exc:
        return dict(base_result, aborted_reason=(
            "backup failed ({0}); aborting before live commit. "
            "Live files untouched.".format(exc)
        ))
    hashes = {
        "plan_tracker_before": backup_hashes["plan_tracker_sha256"],
        "evidence_log_before": backup_hashes["evidence_log_sha256"],
    }

    # ── Steps 6-8: compensating runtime + evidence transaction ──────────
    migration_row = (
        "| MIGRATION-{ver} | FX-191 | migrated {prior} -> {new_model} | "
        "backup={backup} |".format(
            ver=MIGRATION_VERSION,
            prior=prior_model,
            new_model=WORKFLOW_MODEL_NEW,
            backup=backup_dir.name,
        )
    )
    evidence_after_text = evidence_text
    if evidence_after_text and not evidence_after_text.endswith("\n"):
        evidence_after_text += "\n"
    evidence_after_text += migration_row.rstrip("\n") + "\n"
    transaction = _commit_runtime_and_evidence(
        runtime_path,
        (json.dumps(runtime_payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        evidence_path,
        evidence_after_text.encode("utf-8"),
        backup_dir,
    )
    if transaction["state"] != "PASS":
        fail_result = dict(
            base_result,
            state=transaction["state"],
            aborted_reason="migration commit failed; compensation attempted",
            recovery_issues=transaction.get("issues", []),
            recovery_journal=transaction.get("journal"),
            backup_dir=str(backup_dir),
            hashes=hashes,
            workflow_model={"prior": prior_model, "new": WORKFLOW_MODEL_NEW},
            plan_hash=confirmed_plan.plan_hash,
        )
        if heal.get("healed"):
            fail_result["healed_interrupted_commit"] = heal
        if orphan_sweep["cleaned"] or orphan_sweep["skipped"]:
            fail_result["orphan_backup_sweep"] = orphan_sweep
        if transaction["state"] == "FAIL":
            # FIX-398 E-5: the commit failed but compensation succeeded, so
            # the backup dir created for THIS attempt is an orphan (no
            # MIGRATION row will ever reference it; the live files were
            # restored byte-exactly). Remove it so it cannot shadow a later
            # rollback's newest-backup selection. Defensive gate: only when
            # the post-compensation live evidence hash still equals the
            # attempt's pre-state snapshot. BLOCKED keeps everything — the
            # recovery journal references the backup dir.
            snapshot = backup_dir / "evidence.before"
            if (snapshot.is_file()
                    and _file_sha256(evidence_path) == _file_sha256(snapshot)
                    and _remove_backup_dir_best_effort(backup_dir)):
                fail_result["orphan_backup_removed"] = backup_dir.name
            else:
                fail_result["orphan_backup_removed"] = None
                fail_result["orphan_backup_cleanup"] = (
                    "kept: post-compensation evidence hash differs from the "
                    "pre-state snapshot, or removal failed — manual review"
                )
        return fail_result

    # Record the AFTER hashes (post-write) for the audit trail.
    hashes["plan_tracker_after"] = _file_sha256(plan_path)
    hashes["evidence_log_after"] = _file_sha256(evidence_path)

    # ── Step 9: structured result ───────────────────────────────────────
    success_result = {
        "command": "loop-engineering-migration",
        "mode": "apply",
        "applied": True,
        "target": str(host_root),
        "workflow_model": {"prior": prior_model, "new": WORKFLOW_MODEL_NEW},
        "backup_dir": str(backup_dir),
        "hashes": hashes,
        "flow_units_derived": len(flow_units),
        "evidence_row": "MIGRATION-{0}".format(MIGRATION_VERSION),
        "plan_hash": confirmed_plan.plan_hash,
        "decomposition_confirmed": True,
        "no_overclaim_boundary": (
            "runtime visibility only; classic G1-G11 remains compatible via rollback"
        ),
    }
    if heal.get("healed"):
        success_result["healed_interrupted_commit"] = heal
    if orphan_sweep["cleaned"] or orphan_sweep["skipped"]:
        success_result["orphan_backup_sweep"] = orphan_sweep
    return success_result


# ═══════════════════════════════════════════════════════════════════════════
# ROLLBACK (ADR §7.3 — 6 steps)
# ═══════════════════════════════════════════════════════════════════════════


def rollback_migration(target_root=None, version=None, plugin_home=None):
    """Execute the loop-engineering → classic rollback (ADR §7.3, 6 steps).

    Rollback is TOTAL: it restores plan-tracker.md + evidence-log.md exactly
    (hash-verified against the backup BEFORE restore), removes the
    runtime.json, and appends a ROLLBACK evidence row.

    Steps:
      1. operator: ``loop-engineering-migration --rollback --target <path>``
      2. verify backup hashes match (fail-closed if tampered)
      3. restore plan-tracker.md + evidence-log.md from backup
      4. set workflow_model back to prior (via the restored plan-tracker)
      5. remove ``.governance/flow-unit-runtime.json``
      6. write rollback record to evidence-log: ``ROLLBACK-{version}``

    Args:
        target_root: Host project root (str/Path). If None, resolved from cwd.
        version: Optional migration version to select a specific backup
            (e.g. ``"0.65.0"``). If None, the NEWEST backup is used.
        plugin_home: Reserved for symmetry; currently unused.

    Returns:
        Result dict with ``rolled_back: True`` on success, or
        ``rolled_back: False, aborted_reason: ...`` on fail-closed.
    """
    base_result = {
        "command": "loop-engineering-migration",
        "mode": "rollback",
        "rolled_back": False,
        "target": None,
    }

    # ── Step 1: resolve host root ───────────────────────────────────────
    host_root = _resolve_host_root(target_root, plugin_home)
    if host_root is None:
        return dict(base_result, aborted_reason=(
            "HOST_PROJECT_ROOT unresolvable (RISK-040 C4 fail-closed): "
            "target_root={0!r}. No write performed.".format(target_root)
        ))
    base_result["target"] = str(host_root)

    # Locate the backup dir to restore from.
    backups = _list_migration_backups(host_root)
    if not backups:
        return dict(base_result, aborted_reason=(
            "no migration backup found under {0}/archive/; nothing to roll "
            "back. No write performed.".format(_gov_dir(host_root))
        ))

    selected = None
    if version is not None:
        # Pick the newest backup matching the requested version.
        for entry in reversed(backups):
            if entry[1] == version:
                selected = entry
                break
        if selected is None:
            return dict(base_result, aborted_reason=(
                "no migration backup found for version {0!r} under {1}/archive/. "
                "Available versions: {2}. No write performed.".format(
                    version, _gov_dir(host_root),
                    sorted({v for _, v, _ in backups}),
                )
            ))
    else:
        selected = backups[-1]  # newest

    backup_dir, backup_version, backup_timestamp = selected

    # Read the migration row we wrote to recover the prior model. The backup's
    # plan-tracker is the authoritative pre-migration state — its workflow_model
    # IS the prior model. We read it from the backup to determine what we're
    # restoring to.
    backup_plan_path = backup_dir / PLAN_TRACKER_FILENAME
    backup_plan_text = _read_text(backup_plan_path)
    prior_model = (
        _parse_workflow_model(backup_plan_text) if backup_plan_text else "unknown"
    )

    # Read the trusted hashes from the backup's manifest.json. This is the
    # integrity record written at apply time. We do NOT compute expected
    # hashes from the backup files themselves (that would be tautological —
    # a tampered file would hash to its own tampered value). The manifest is
    # the ground truth; the files are verified against it.
    manifest_path = backup_dir / "manifest.json"
    expected_hashes = {}
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            manifest = None
        if isinstance(manifest, dict):
            files = manifest.get("files", {})
            if isinstance(files, dict):
                pt_hash = files.get(PLAN_TRACKER_FILENAME)
                ev_hash = files.get(EVIDENCE_LOG_FILENAME)
                if isinstance(pt_hash, str):
                    expected_hashes["plan_tracker_sha256"] = pt_hash
                if isinstance(ev_hash, str):
                    expected_hashes["evidence_log_sha256"] = ev_hash
    if not expected_hashes:
        return dict(base_result, aborted_reason=(
            "backup at {0} has no usable manifest.json (missing/corrupt/no "
            "file hashes). Refusing to restore an unverified backup. No "
            "write performed.".format(backup_dir)
        ), backup_dir=str(backup_dir))

    # ── Step 2: verify backup integrity (files vs manifest) ─────────────
    ok, mismatches = _verify_backup_hashes(backup_dir, expected_hashes)
    if not ok:
        return dict(base_result, aborted_reason=(
            "backup hash verification FAILED for {0}: {1}. Refusing to "
            "restore a tampered/corrupt backup. No write performed.".format(
                backup_dir, "; ".join(mismatches)
            )
        ), backup_dir=str(backup_dir))

    # ── Step 3: restore plan-tracker + evidence-log from backup ─────────
    # Copy the backup files over the live ones. This is the inverse of apply's
    # step 4 — total restore. (Hashes were already verified in step 2.)
    plan_dst = backup_dir / PLAN_TRACKER_FILENAME
    evidence_dst = backup_dir / EVIDENCE_LOG_FILENAME
    try:
        gov = _gov_dir(host_root)
        gov.mkdir(parents=True, exist_ok=True)
        if plan_dst.is_file():
            shutil.copy2(plan_dst, _plan_tracker_path(host_root))
        if evidence_dst.is_file():
            shutil.copy2(evidence_dst, _evidence_log_path(host_root))
    except OSError as exc:
        return dict(base_result, aborted_reason=(
            "restore copy failed ({0}); the backup at {1} is intact. "
            "Manual restore required. No runtime.json removal performed.".format(
                exc, backup_dir
            )
        ), backup_dir=str(backup_dir))

    # ── Step 5: remove the runtime.json ─────────────────────────────────
    # (Step 4 — workflow_model reset — is achieved by the restored plan-tracker,
    # which carries the prior model. We do not separately rewrite the tracker.)
    runtime_path = _runtime_path(host_root)
    runtime_existed = runtime_path.is_file()
    if runtime_existed:
        try:
            runtime_path.unlink()
        except OSError as exc:
            return dict(base_result, aborted_reason=(
                "plan-tracker + evidence-log restored, but runtime.json removal "
                "failed ({0}). Partial rollback — runtime.json remains at {1}. "
                "Backup at {2} is intact.".format(exc, runtime_path, backup_dir)
            ), backup_dir=str(backup_dir),
               workflow_model={"prior": WORKFLOW_MODEL_NEW, "new": prior_model},
               runtime_removed=False)

    # ── Step 6: write ROLLBACK evidence row ─────────────────────────────
    # Note: the evidence-log was just restored from backup (pre-migration
    # state), so it does NOT yet contain the MIGRATION row. We append the
    # ROLLBACK row to the restored log so the audit trail shows the rollback
    # happened.
    rollback_row = (
        "| ROLLBACK-{ver} | FX-191 | rolled back {new_model} -> {prior} | "
        "restored_from={backup} |".format(
            ver=backup_version,
            new_model=WORKFLOW_MODEL_NEW,
            prior=prior_model,
            backup=backup_dir.name,
        )
    )
    try:
        _append_evidence_row(host_root, rollback_row)
    except OSError as exc:
        return dict(base_result, aborted_reason=(
            "plan-tracker + evidence-log restored and runtime.json removed, "
            "but ROLLBACK evidence row could not be appended ({0}). The "
            "restoration is otherwise complete. Backup at {1} is intact.".format(
                exc, backup_dir
            )
        ), backup_dir=str(backup_dir),
           workflow_model={"prior": WORKFLOW_MODEL_NEW, "new": prior_model},
           runtime_removed=True)

    return {
        "command": "loop-engineering-migration",
        "mode": "rollback",
        "rolled_back": True,
        "target": str(host_root),
        "backup_dir": str(backup_dir),
        "workflow_model": {"prior": WORKFLOW_MODEL_NEW, "new": prior_model},
        "runtime_removed": runtime_existed,
        "evidence_row": "ROLLBACK-{0}".format(backup_version),
        "restored_from": str(backup_dir),
    }


# ═══════════════════════════════════════════════════════════════════════════
# PREVIEW (read-only compatibility envelope)
# ═══════════════════════════════════════════════════════════════════════════


def preview_migration(target_root=None, plugin_home=None, project_type=None):
    """Return the read-only migration preview (ADR §4.4 dry-run path).

    FEAT-003 (ADR §4.4): the dry-run now derives the migration plan via the
    SAME pure :func:`build_migration_plan` the apply path uses, serializes it
    (including ``plan_hash``), and validates the resulting v2 payload via the
    v2 validator. This is the REL-059 dry-run/apply identity invariant made
    executable: the preview's plan_hash is the hash apply re-derives and
    verifies (when ``expected_plan_hash`` is supplied).

    The plan + plan_hash + v2 validation are attached to the preview result
    alongside the legacy ``verify_workflow`` preview shape (preserved for
    backward compatibility with the CLI adapter + existing callers). The dry
    run performs NO writes.

    Args:
        target_root: Host project root (str/Path), or None.
        plugin_home: Reserved for symmetry; forwarded to the planner.
        project_type: Optional project type for unit derivation. If None,
            defaults to ``"ai-agent-plugin"`` inside the planner.

    Returns:
        A preview dict. The legacy shape (``command``, ``mode``, ``dry_run``,
        ``write_operations``, ``validation_issues``, ``no_overclaim_boundaries``)
        is preserved; FEAT-003 adds ``migration_plan`` (the serialized plan
        including ``plan_hash``), ``plan_hash``, and ``v2_validation_issues``
        (the v2 validator's verdict on the plan-derived payload). FEAT-070
        adds ``unit_manifest`` (the per-unit anchoring face consumed from
        ``flow-unit-approval-manifest.json``) and
        ``unit_manifest_ambiguity_count`` (derived units without a confirmed
        entry — 0 means the dry-run consumes the manifest with zero
        prose-anchoring ambiguity).
    """
    from verify_workflow import (  # deferred to keep module import acyclic
        build_dynamic_lifecycle_migration_preview,
        check_dynamic_lifecycle_migration_preview,
    )
    preview = build_dynamic_lifecycle_migration_preview(target_root)
    issues = check_dynamic_lifecycle_migration_preview(target_root)
    preview["validation_issues"] = issues
    if issues:
        preview["status"] = "BLOCKED"

    # ── FEAT-003: derive the migration plan (the SAME pure function apply uses)
    # and attach the serialized plan + plan_hash + v2 validation verdict. This
    # is the dry-run/apply identity surface: the operator can read plan_hash
    # from the dry-run and pass it to apply as expected_plan_hash (ADR §4.4).
    migration_plan = None
    plan_hash = None
    v2_validation_issues = []
    plan = None
    try:
        plan = build_migration_plan(
            target_root, project_type, plugin_home=plugin_home,
        )
        migration_plan = plan_as_dict(plan)
        plan_hash = plan.plan_hash
        # Validate the plan-derived v2 payload (advisory here — no writes).
        payload = plan_to_payload(plan, plugin_home=plugin_home)
        v2_validation_issues = _validate_runtime_payload(
            payload, ".governance/flow-unit-runtime.json"
        )
    except Exception as exc:  # planner fail-closed → report (P3-6: the former
        # ``except (ValueError, Exception)`` tuple was redundant — Exception
        # subsumes ValueError; semantics unchanged, noise removed)
        preview["plan_derivation_error"] = str(exc)

    # ── FEAT-070: consume the unit approval manifest (ADR §2.6 B-first) ──
    # The dry-run prefers the human-confirmed manifest: a derived unit with a
    # confirmed entry is anchored; a unit WITHOUT one stays §2.6 fail-closed
    # blocked (never prose-guessed). Read-only: the face performs no writes.
    unit_manifest_face = _build_unit_manifest_face(
        plan, target_root=target_root, plugin_home=plugin_home,
    )
    preview["unit_manifest"] = unit_manifest_face
    preview["unit_manifest_ambiguity_count"] = unit_manifest_face["ambiguity_count"]

    preview["migration_plan"] = migration_plan
    preview["plan_hash"] = plan_hash
    preview["v2_validation_issues"] = v2_validation_issues
    return preview


if __name__ == "__main__":  # pragma: no cover - manual CLI smoke
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Loop-engineering migration (FX-191). Apply classic -> loop-engineering "
            "with SHA-256 backup, or roll back to the pre-migration state."
        )
    )
    parser.add_argument(
        "--target", default=None,
        help="Host project root (defaults to cwd).",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Apply the migration (writes runtime.json + evidence row; backs up first).",
    )
    parser.add_argument(
        "--rollback", action="store_true",
        help="Roll back the most recent migration (or --version).",
    )
    parser.add_argument(
        "--version", default=None,
        help="Select a specific migration version to roll back.",
    )
    parser.add_argument(
        "--project-type", default=None,
        help="Project type for flow-unit derivation (apply only).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print a read-only preview (no writes).",
    )
    parser.add_argument(
        "--shadow-derive", action="store_true",
        help=("FEAT-071 (DEC-254 A): run the structure-anchored unit "
              "derivation pipeline in SHADOW mode — read-only derivation + "
              "comparison report against the approval manifest; zero writes, "
              "zero authority flip."),
    )
    parser.add_argument(
        "--expected-plan-hash", default=None,
        help="Apply-path plan hash verification (FEAT-003, ADR §4.4). Fail-closed on mismatch.",
    )
    parser.add_argument(
        "--approve-unit", dest="approved_unit_ids", action="append", default=None,
        help=("FEAT-004: restrict the applied plan to this operator-approved "
              "flow_unit_id (repeatable). Omit to confirm the full derived set. "
              "FEAT-070: with --record-unit-approval, names the ONE unit whose "
              "task→unit mapping is being confirmed into the manifest."),
    )
    parser.add_argument(
        "--record-unit-approval", action="store_true",
        help=("FEAT-070 (ADR §2.6 confirm chain): record ONE human-confirmed "
              "task→unit mapping into .governance/flow-unit-approval-manifest.json. "
              "Requires --approve-unit <flow_unit_id> --approve-task <task_id> "
              "--approve-evidence <text> --approve-reviewer <who> --repo-version <v>. "
              "No migration is performed."),
    )
    parser.add_argument(
        "--record-unit-block", action="store_true",
        help=("FEAT-070 (§2.6 fail-closed trace): record ONE unit as blocked "
              "(not uniquely interpretable — no guessing). Requires "
              "--approve-unit <flow_unit_id> --block-reason <text> "
              "--approve-reviewer <who> --repo-version <v>. "
              "No migration is performed."),
    )
    parser.add_argument(
        "--approve-task", default=None,
        help="FEAT-070: task_id of the mapping being confirmed (stable identifier).",
    )
    parser.add_argument(
        "--approve-evidence", default=None,
        help="FEAT-070: confirmation evidence for the mapping (structural facts).",
    )
    parser.add_argument(
        "--approve-reviewer", default=None,
        help="FEAT-070: reviewer/recorder identity for the manifest entry.",
    )
    parser.add_argument(
        "--block-reason", default=None,
        help="FEAT-070: why the unit is NOT uniquely interpretable (block trace).",
    )
    parser.add_argument(
        "--repo-version", default=None,
        help="FEAT-070: repository version the confirmation is made against.",
    )
    args = parser.parse_args()

    # ── FEAT-070-R0 P2-1: record-flag combination mutex ──────────────────
    # The record family used to be resolved by SILENT PRECEDENCE: giving both
    # record flags quietly ran the approval branch, and a record flag next to
    # --apply was dropped in favor of the migration. Operator intent must
    # never be silently discarded — every impossible combination fails
    # loudly here (argparse convention: exit 2) BEFORE any file is touched.
    # Pre-existing mode-flag precedence (rollback > apply > preview) is NOT
    # part of this fix and stays untouched (backward compatibility).
    _RECORD_MODE_FLAGS = ("record_unit_approval", "record_unit_block")
    _MIGRATION_MODE_FLAGS = ("dry_run", "apply", "rollback", "shadow_derive")
    _RECORD_ONLY_FLAGS = (
        "approve_task", "approve_evidence", "approve_reviewer",
        "block_reason", "repo_version",
    )
    record_modes = [f for f in _RECORD_MODE_FLAGS if getattr(args, f)]
    migration_modes = [f for f in _MIGRATION_MODE_FLAGS if getattr(args, f)]
    if len(record_modes) > 1:
        parser.error(
            "--record-unit-approval and --record-unit-block are mutually "
            "exclusive (exactly ONE decision per invocation)"
        )
    if record_modes and migration_modes:
        parser.error(
            "record flags are mutually exclusive with migration modes; got "
            "--{0} together with {1}".format(
                record_modes[0].replace("_", "-"),
                ", ".join("--" + f.replace("_", "-") for f in migration_modes),
            )
        )
    if not record_modes:
        for f in _RECORD_ONLY_FLAGS:
            if getattr(args, f, None) is not None:
                parser.error(
                    "--{0} is only valid together with --record-unit-approval "
                    "or --record-unit-block".format(f.replace("_", "-"))
                )

    try:
        import sys
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

    if args.rollback:
        result = rollback_migration(
            target_root=args.target, version=args.version,
        )
    elif args.apply:
        result = apply_migration(
            target_root=args.target, project_type=args.project_type,
            expected_plan_hash=args.expected_plan_hash,
            approved_unit_ids=args.approved_unit_ids,
        )
    elif args.record_unit_approval or args.record_unit_block:
        # Record mode takes EXACTLY ONE --approve-unit per invocation (逐条
        # confirmation discipline); the append-flag yields a list, so unwrap
        # and reject multi-unit record attempts before touching the manifest.
        unit_arg = args.approved_unit_ids
        if isinstance(unit_arg, list):
            if len(unit_arg) != 1:
                print(json.dumps({
                    "command": "loop-engineering-migration",
                    "mode": "record-unit-approval" if args.record_unit_approval
                            else "record-unit-block",
                    "recorded": False,
                    "refused_reason": (
                        "record mode confirms exactly ONE unit per invocation "
                        "(--approve-unit given {0} times)".format(len(unit_arg))
                    ),
                }, ensure_ascii=False, indent=2))
                raise SystemExit(1)
            unit_arg = unit_arg[0]
        if args.record_unit_approval:
            result = record_unit_approval(
                target_root=args.target, flow_unit_id=unit_arg,
                task_id=args.approve_task,
                confirmation_evidence=args.approve_evidence,
                reviewer=args.approve_reviewer,
                repo_version=args.repo_version,
                project_type=args.project_type,
            )
        else:
            result = record_unit_block(
                target_root=args.target, flow_unit_id=unit_arg,
                reason=args.block_reason,
                recorded_by=args.approve_reviewer,
                repo_version=args.repo_version,
                project_type=args.project_type,
            )
        if not result.get("recorded"):
            print(json.dumps(result, ensure_ascii=False, indent=2))
            raise SystemExit(1)
    elif args.shadow_derive:
        result = derive_structural_units_shadow(
            target_root=args.target, project_type=args.project_type,
        )
    else:
        result = preview_migration(
            target_root=args.target, project_type=args.project_type,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if ((args.apply and not result.get("applied"))
            or (args.rollback and not result.get("rolled_back"))
            or (args.shadow_derive and not result.get("shadow_derived"))
            or (not args.apply and not args.rollback
                and result.get("validation_issues"))):
        raise SystemExit(1)
