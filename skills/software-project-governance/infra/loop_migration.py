#!/usr/bin/env python3
"""
Loop-engineering migration — FX-191 (0.65.0 loop-engineering, slice 4).

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

Usage:
    from loop_migration import apply_migration, rollback_migration, preview_migration
"""

import hashlib
import json
import os
import re
import shutil
import tempfile
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


# ═══════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════

MIGRATION_VERSION = "0.65.0"
WORKFLOW_MODEL_NEW = "loop-engineering"
RUNTIME_FILENAME = "flow-unit-runtime.json"
PLAN_TRACKER_FILENAME = "plan-tracker.md"
EVIDENCE_LOG_FILENAME = "evidence-log.md"

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
            post_issues.extend(validate_flow_unit_runtime_payload(runtime_state, str(runtime_path)))
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
# APPLY (ADR §7.2 — 9 steps)
# ═══════════════════════════════════════════════════════════════════════════


def apply_migration(target_root=None, project_type=None, plugin_home=None):
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

    On fail-closed, NOTHING is written — no backup dir, no runtime.json, no
    evidence row. The caller (cmd_*) inspects ``result["applied"]`` and
    exits non-zero when False.

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

    # ── Fail-closed: idempotency (runtime.json already at target version) ──
    # The runtime.json is the AUTHORITATIVE marker of a completed migration.
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

    # ── Step 4: derive and validate the complete payload in memory ──────
    chosen_project_type = project_type or "ai-agent-plugin"
    try:
        flow_units = derive_flow_units(
            str(host_root), chosen_project_type,
            plan_tracker_text=plan_text, plugin_home=plugin_home,
        )
    except Exception as exc:  # defensive: derive_flow_units must not raise
        return dict(base_result, aborted_reason=(
            "flow-unit derivation raised ({0}); aborting before any host write. "
            "No backup, runtime, or evidence file was created.".format(exc)
        ))

    # ── Fail-closed: derived flow units = 0 ─────────────────────────────
    # (FX-190's fallback prevents this in practice, but we guard anyway so a
    # future regression can never produce an empty runtime.)
    if not flow_units:
        return dict(base_result, aborted_reason=(
            "derived flow units = 0; refusing to write an empty runtime. "
            "No host write performed."
        ))

    runtime_payload = {
        "workflow_model": WORKFLOW_MODEL_NEW,
        "migration_version": MIGRATION_VERSION,
        "migration_timestamp": _now_iso(),
        "source": "runtime-activation",
        "flow_units": flow_units,
        "no_overclaim_boundary": (
            "runtime visibility only; classic G1-G11 remains compatible via rollback"
        ),
    }
    runtime_path = _runtime_path(host_root)
    validation_issues = validate_flow_unit_runtime_payload(
        runtime_payload, str(runtime_path)
    )
    if validation_issues:
        return dict(
            base_result,
            aborted_reason=(
                "planned loop-engineering runtime is incompatible with the "
                "current canonical visibility-v1 contract; no host write performed"
            ),
            validation_issues=validation_issues,
            workflow_model={"prior": prior_model, "new": WORKFLOW_MODEL_NEW},
            flow_units_derived=len(flow_units),
        )

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
        return dict(
            base_result,
            state=transaction["state"],
            aborted_reason="migration commit failed; compensation attempted",
            recovery_issues=transaction.get("issues", []),
            recovery_journal=transaction.get("journal"),
            backup_dir=str(backup_dir),
            hashes=hashes,
            workflow_model={"prior": prior_model, "new": WORKFLOW_MODEL_NEW},
        )

    # Record the AFTER hashes (post-write) for the audit trail.
    hashes["plan_tracker_after"] = _file_sha256(plan_path)
    hashes["evidence_log_after"] = _file_sha256(evidence_path)

    # ── Step 9: structured result ───────────────────────────────────────
    return {
        "command": "loop-engineering-migration",
        "mode": "apply",
        "applied": True,
        "target": str(host_root),
        "workflow_model": {"prior": prior_model, "new": WORKFLOW_MODEL_NEW},
        "backup_dir": str(backup_dir),
        "hashes": hashes,
        "flow_units_derived": len(flow_units),
        "evidence_row": "MIGRATION-{0}".format(MIGRATION_VERSION),
        "no_overclaim_boundary": (
            "runtime visibility only; classic G1-G11 remains compatible via rollback"
        ),
    }


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


def preview_migration(target_root=None, plugin_home=None):
    """Return the same read-only preview authority exposed by the CLI adapter.

    Args:
        target_root: Host project root (str/Path), or None.
        plugin_home: Reserved for symmetry; currently unused.

    Returns:
        A compatibility-shaped preview. Apply performs the authoritative
        canonical payload validation before any host write.
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
    args = parser.parse_args()

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
        )
    else:
        result = preview_migration(target_root=args.target)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if ((args.apply and not result.get("applied"))
            or (args.rollback and not result.get("rolled_back"))
            or (not args.apply and not args.rollback and result.get("validation_issues"))):
        raise SystemExit(1)
