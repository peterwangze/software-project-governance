"""FEAT-096 — execution isolation &amp; recovery, conservative surface.

arch 盲区裁定 (DEC-330 复盘分析批): 锁可绕过 = 锁未控制实际写入能力;
无法隔离的共享文件宁可限制写并发, 不用可绕过软锁假装安全.  RPG session
实测 (报告 §3.4): 36 文件锁悬挂 20h 至 TTL 过期未释放 / 后段 ~45 子代理
完全绕开锁与账本 / REV-009 并发重写域破坏可审计性.

Delivered conservative four-piece set (0.98.0):

  1. 共享文件写并发限制 — ``begin_write`` / ``end_write`` grant an
     exclusive per-domain WRITE SLOT: an O_EXCL lockfile (the real
     cross-process primitive, holder info written INTO the lockfile) plus
     a mirrored record in ``execution-isolation.json`` (greppability +
     expiry).  A second writer on the same domain is REFUSED with the
     holder and the expected release time (ux contract); distinct domains
     never conflict (无冲突路径零感知).
  2. 同文件域「被审/在写」互斥 — a domain with an ACTIVE review snapshot
     refuses writes (Reviewer reads immutable state, never a file being
     rewritten mid-review — the REV-009 auditability break); a domain
     with a live write slot refuses snapshot creation.
  3. 审查快照只读化 — snapshot files are copied under
     ``.governance/review-snapshots/`` with sha256 digests and chmod
     read-only; the write gate additionally refuses any sanctioned write
     under the snapshot root (``snapshot_immutable``).
  4. 租约失权回收 — a writer whose ``agent-locks.json`` lease
     (``locked_at`` + ``ttl_seconds``) has expired is REFUSED
     (``lease_expired`` — authority lost) AND the refusal TRIGGERS the
     reclaim: expired entries are removed and audited in
     ``reclaim_log`` (the 36-lock-20h-suspension root face).  The
     standalone ``reclaim_expired_leases`` reclaims without a write
     attempt.  Loss-of-authority is verified against the live locks file
     (查世界不信日志): reclaimed writers lose their lease AND any
     residual write slot.

Capability honesty (acceptance ① — 引用已落盘 FEAT-095 调研报告,
U1 未证实不得声称已验证):

  Host worktree/sandbox isolation is NOT a plugin-available surface
  today — the FEAT-095 report
  (``docs/research/feat-095-harness-enforcement-capability-2026-10-10.md``
  §5 matrix / §7 U1-U7) shows host-level interception unwired on all
  six platforms and the dsh guard PoC UNVERIFIED.  FEAT-096 therefore
  ships the CLI-level conservative surface only and does NOT claim
  host-level isolation.  Blocking semantics AFTER a mutex trigger on
  the dispatch side belong to FEAT-095 (non_goal here); likewise
  lease→write identity binding (a leaseless retry is governed by the
  dispatch protocol, not by this gate — disclosed boundary).

Slot and review recovery (FIX-517):

  * New write grants bind a task and a worker (session, writer label and
    workspace). The read-only judge, snapshot creator and release operation
    inspect both state and marker; a writer interrupted before publishing
    its state still blocks conflicting work. A stale worker cannot release
    a successor's slot. Anonymous legacy grants remain reserved until expiry.
  * New reviews have a lease. After interruption, an explicit recovery uses
    the task, snapshot ID and reason to release only the expired binding.
    Original bytes, digests and snapshot artifacts remain available. Legacy
    reviews use their stored beginning plus the default review lease.
  * The short-lived state mutation guard is kernel-held and released on
    process exit. A legacy state.lock marker retains its prior grace period.

Cross-process lock protocol (review R0 P1-1): the lease reclaim is the
only ``agent-locks.json`` writer OUTSIDE governance_store, so it joins
that file's established protocol — the read-modify-write runs under
``governance_store._TargetLock`` (``.governance-store-locks/
agent-locks.json.lock``) with the decisions computed against a FRESH
read taken under the lock (never the caller's earlier snapshot).  Lock
order is one-way (isolation state lock → agent-locks target lock);
governance_store writers never take the isolation state lock, so the
nesting is acyclic.  The import is function-local: the module stays
stdlib-only at import time (R6 cold face unchanged).

Domain canonicality (review R0 P2-2): every public entry point
validates its file list through :func:`_domains_or_error` — ``..`` /
``.`` segments, empty segments, absolute paths, ``:`` and control
characters are refused fail-closed.  Over CANONICAL domains the
snapshot-root prefix gate is exactly the containment test, and the
snapshot copy additionally asserts resolved containment
(``is_relative_to``) as defense-in-depth.

Rollback (execution-packet rollback_plan): ``GOVERNANCE_ISOLATION=off``
(or ``GOVERNANCE_ISOLATION_DISABLED=1``) disables the concurrency gate —
``begin_write`` degrades to a pass-through (legacy soft-lock behavior,
``gate_disabled: true`` in the result, zero state writes).  Lease
reclaim stays functional (explicit recovery action, not a gate).

Schema discipline: this module adds NO new required fields to
``agent-locks.json`` (non_goal) — old-format lock files (pre-FEAT-013
shape) stay readable and reclaimable.  Its own state file
(``.governance/execution-isolation.json``) is module-owned, exactly like
the write-guard's ``.write-guard-state.json`` precedent.

Composition root: the engine (verify_workflow.py) wires dispatch only
(RISK-039 thin-entry discipline); this module keeps its own parser +
``main`` so ``python execution_isolation.py …`` works standalone.  Both
paths share one option fact source (``add_*_arguments``) and one
Namespace executor (``cmd_*`` — no argv re-parse).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

__all__ = [
    "CAPABILITY_REPORT_REF",
    "CODE_LEASE_EXPIRED",
    "CODE_LOCK_CONTENTION",
    "CODE_MANUAL_INTERVENTION",
    "CODE_NOT_HOLDER",
    "CODE_SNAPSHOT_IMMUTABLE",
    "CODE_UNDER_REVIEW",
    "CODE_WRITE_CONFLICT",
    "CODE_WRITE_IN_PROGRESS",
    "DISABLE_ENV_VAR",
    "SNAPSHOT_DIR_NAME",
    "STATE_FILE_NAME",
    "add_capability_arguments",
    "add_lease_reclaim_arguments",
    "add_snapshot_arguments",
    "add_status_arguments",
    "add_write_arguments",
    "begin_write",
    "build_parser",
    "capability_disclosure",
    "cmd_isolation_capability",
    "cmd_isolation_lease_reclaim",
    "cmd_isolation_snapshot",
    "cmd_isolation_status",
    "cmd_isolation_write",
    "create_review_snapshot",
    "end_write",
    "isolation_disabled",
    "isolation_status",
    "judge_write",
    "main",
    "reclaim_expired_leases",
    "release_review",
    "recover_review",
    "render_status_text",
]

# ── constants ────────────────────────────────────────────────────────────────

GOVERNANCE_DIR_NAME = ".governance"
LOCKS_FILE_NAME = "agent-locks.json"
STATE_FILE_NAME = "execution-isolation.json"
LOCK_DIR_NAME = ".execution-isolation-locks"
SNAPSHOT_DIR_NAME = "review-snapshots"
SNAPSHOT_MANIFEST_NAME = "snapshot.json"

#: Rollback switch (execution-packet rollback_plan): any of these values
#: disables the concurrency gate (pass-through, zero state writes).
DISABLE_ENV_VAR = "GOVERNANCE_ISOLATION"
_DISABLE_VALUES = {"off", "disabled", "0", "false", "no"}

CAPABILITY_REPORT_REF = (
    "https://github.com/peterwangze/software-project-governance/blob/"
    "7b9fd3720376549c53b06d4fc362f5fb0c96e40b/docs/research/"
    "feat-095-harness-enforcement-capability-2026-10-10.md")

DEFAULT_WRITE_SLOT_TTL_SECONDS = 600
DEFAULT_REVIEW_TTL_SECONDS = 3600
_STALE_LOCKFILE_SECONDS = 600
_LOCK_POLL_SECONDS = 0.05
_MAX_WAITERS = 50
_MAX_RECLAIM_LOG = 200
_MAX_SNAPSHOT_RECORDS = 100

_TASK_ID_RE = re.compile(r"^[A-Z]+-\d+$")

#: Closed error-code vocabulary with disposition classes (mirrors the
#: contracts.py closed-enum discipline as a PLAIN dict — extending the
#: frozen M0 contract is out of this ticket's file surface).
CODE_WRITE_CONFLICT = "write_conflict"
CODE_UNDER_REVIEW = "under_review"
CODE_WRITE_IN_PROGRESS = "write_in_progress"
CODE_SNAPSHOT_IMMUTABLE = "snapshot_immutable"
CODE_LEASE_EXPIRED = "lease_expired"
CODE_NOT_HOLDER = "not_holder"
CODE_MANUAL_INTERVENTION = "manual_intervention"
CODE_SCHEMA_VIOLATION = "schema_violation"
CODE_LOCK_CONTENTION = "lock_contention"

ERROR_DISPOSITIONS = {
    CODE_WRITE_CONFLICT: "conflict",
    CODE_UNDER_REVIEW: "conflict",
    CODE_WRITE_IN_PROGRESS: "conflict",
    CODE_SNAPSHOT_IMMUTABLE: "validation",
    CODE_LEASE_EXPIRED: "conflict",
    CODE_NOT_HOLDER: "validation",
    CODE_MANUAL_INTERVENTION: "manual",
    CODE_SCHEMA_VIOLATION: "validation",
    CODE_LOCK_CONTENTION: "retryable",
}




# ── small helpers ───────────────────────────────────────────────────────────


def isolation_disabled() -> bool:
    """True when the concurrency gate is switched off (rollback face)."""
    for name in (DISABLE_ENV_VAR, DISABLE_ENV_VAR + "_DISABLED"):
        raw = (os.environ.get(name) or "").strip().lower()
        if raw in _DISABLE_VALUES:
            return True
        if name.endswith("_DISABLED") and raw == "1":
            return True
    return False


def _domain(file_path):
    """Normalize a repo-relative domain key (same convention as the
    acquire pipeline's lock-file keys: backslashes folded, trimmed).
    Only a leading ``./`` is folded — leading dots of real segments
    (``.governance/…``) are significant for the snapshot-root check.

    P2-2 (review R0): returns ``""`` for a NON-CANONICAL input (the
    caller fails closed via :func:`_domains_or_error`) — ``..``/``.``
    segments, empty segments (``//``), absolute paths (leading ``/``),
    ``:`` (Windows drive/ADS — also an aliasing hazard for the lockfile
    name fold), and NUL/control characters are all refused: a ``..``
    segment could otherwise escape the review-snapshot root on copy AND
    smuggle a path that resolves inside the snapshot root past the
    literal ``snapshot_immutable`` prefix gate."""
    text = str(file_path or "").replace("\\", "/").strip()
    while text.startswith("./"):
        text = text[2:]
    if not text or text.startswith("/"):
        return ""
    if ":" in text or "\x00" in text:
        return ""
    if any(char in text for char in "\r\n\t"):
        return ""
    for segment in text.split("/"):
        if segment in ("", ".", ".."):
            return ""
    return text


def _directory_case_sensitive(parent, inherited):
    """Observe this directory's lookup rules without creating a probe file."""
    try:
        with os.scandir(parent) as entries:
            for entry in entries:
                variant = entry.name.swapcase()
                if variant == entry.name:
                    continue
                try:
                    return not os.path.samefile(entry.path, parent / variant)
                except FileNotFoundError:
                    if not entry.is_symlink():
                        return True
    except (FileNotFoundError, NotADirectoryError):
        return inherited
    if os.name == "nt":
        # An empty NTFS directory can independently enable case sensitivity.
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        open_dir = kernel.CreateFileW
        open_dir.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                             wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
        open_dir.restype = wintypes.HANDLE
        handle = open_dir(str(parent), 0x80, 7, None, 3, 0x02000000, None)
        if handle != ctypes.c_void_p(-1).value:
            try:
                flags = wintypes.DWORD()
                if kernel.GetFileInformationByHandleEx(wintypes.HANDLE(handle), 23,
                                                       ctypes.byref(flags), ctypes.sizeof(flags)):
                    return bool(flags.value & 1)
            finally:
                kernel.CloseHandle(wintypes.HANDLE(handle))
    return inherited


def _domain_key(governance_dir, domain):
    """Canonical directory-entry identity, stable across atomic file replacement."""
    parent = Path(governance_dir).parent
    sensitive = os.name != "nt"
    parts = []
    for name in domain.split("/"):
        sensitive = _directory_case_sensitive(parent, sensitive)
        if not sensitive:
            folded = os.path.normcase(name) if os.name == "nt" else name.lower()
        else:
            folded = name
        parts.append(folded)
        parent = parent / name
    return "/".join(parts)


def _record_key(governance_dir, records, domain):
    """Keep the original spelling of a stored slot, lease or review."""
    if domain in records or not records:
        return domain
    identity = _domain_key(governance_dir, domain)
    for name, record in records.items():
        existing = record.get("domain_key") if isinstance(record, dict) else None
        if (existing or _domain_key(governance_dir, name)) == identity:
            return name
    return domain


def _domains_or_error(files, governance_dir):
    """Validate+normalize a file list → ``(domains, None)`` on success or
    ``(None, error_dict)`` fail-closed listing every offending input
    (P2-2: one bad domain refuses the WHOLE call — a partial grant on a
    non-canonical path set would be worse than a refusal)."""
    raw = [str(f or "") for f in (files or [])]
    bad = [f for f in raw if not _domain(f)]
    if bad:
        return None, _error(
            CODE_SCHEMA_VIOLATION,
            "non-canonical file domain(s): {0!r} — repo-relative domains "
            "must not contain '..'/'.' segments, empty segments, "
            "absolute paths, ':' or control characters (FEAT-096 P2-2: "
            "snapshot-root containment and the snapshot_immutable gate "
            "are only sound over canonical domains)".format(bad))
    domains = [d for d in (_domain(f) for f in raw) if d]
    if not domains:
        return None, _error(
            CODE_SCHEMA_VIOLATION,
            "files is required and must be non-empty")
    by_key = {}
    for name in domains:
        by_key.setdefault(_domain_key(governance_dir, name), name)
    return list(by_key.values()), None


def _snapshot_root_prefix() -> str:
    return "{0}/{1}/".format(GOVERNANCE_DIR_NAME, SNAPSHOT_DIR_NAME)


def _now(now=None) -> datetime:
    return now if now is not None else datetime.now()


def _iso(moment: datetime) -> str:
    return moment.replace(microsecond=0).isoformat()


def _parse_iso(value):
    """Parse a lock timestamp; aware values fold to naive local.

    The acquire pipeline writes naive local ISO stamps; Check 26's own
    expiry face tolerates the ``Z``/offset spellings — same tolerance
    here so an old lock file never fails the lease judgment."""
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def _lease_expiry(entry: dict):
    """Expiry datetime of a file_locks entry, or None if unknowable."""
    if not isinstance(entry, dict):
        return None
    locked_at = _parse_iso(entry.get("locked_at"))
    try:
        ttl = float(entry.get("ttl_seconds", 0))
    except (TypeError, ValueError):
        return None
    if locked_at is None or ttl <= 0:
        return None
    return locked_at + timedelta(seconds=ttl)


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """Same-directory temp file + os.replace (atomic, explicit UTF-8
    bytes in — the governance_store persistence caliber)."""
    handle, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(handle, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _write_json(path: Path, payload) -> None:
    _atomic_write_bytes(
        path, (json.dumps(payload, ensure_ascii=False, indent=2)
               + "\n").encode("utf-8"))


def _error(code: str, detail: str, **extra) -> dict:
    result = {"error": True, "code": code,
              "disposition": ERROR_DISPOSITIONS[code], "detail": detail}
    result.update(extra)
    return result


def _require_task(task_id: str):
    task_id = str(task_id or "").strip()
    if not _TASK_ID_RE.match(task_id):
        return None
    return task_id


# ── state file ──────────────────────────────────────────────────────────────


def _state_path(governance_dir, state_path=None) -> Path:
    return Path(state_path) if state_path is not None \
        else Path(governance_dir) / STATE_FILE_NAME


def _new_state() -> dict:
    return {
        "schema_version": 1,
        "writers": {},
        "reviews": {},
        "waiters": [],
        "reclaim_log": [],
        "snapshots": {},
    }


def _load_state(path: Path, governance_dir=None):
    """Load the isolation state; tolerant of absence, fail-closed on
    corruption (returns ``(state, None)`` / ``(None, error_dict)``)."""
    if not path.is_file():
        return _new_state(), None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, _error(
            CODE_MANUAL_INTERVENTION,
            "{0} is unreadable ({1}) — refusing fail-closed; fix or "
            "remove the file first".format(path, exc))
    if not isinstance(loaded, dict):
        return None, _error(
            CODE_MANUAL_INTERVENTION,
            "{0} root must be a JSON object — refusing fail-closed"
            .format(path))
    state = _new_state()
    for key in ("writers", "reviews", "snapshots"):
        value = loaded.get(key, {})
        if not isinstance(value, dict) or any(not isinstance(v, dict) for v in value.values()):
            return None, _error(CODE_MANUAL_INTERVENTION,
                                "{0}: invalid {1} inventory".format(path, key))
        # Old ledgers could hold two spellings for one file. Never silently
        # discard a historical owner's slot when writing the new state.
        if key == "writers" and len(value) > 1:
            keys = {row.get("domain_key") or _domain_key(governance_dir or path.parent, name)
                    for name, row in value.items()}
            if len(keys) != len(value):
                return None, _error(CODE_MANUAL_INTERVENTION,
                                    "multiple stored writers identify the same file; preserve and reconcile")
        state[key] = value
    for key in ("waiters", "reclaim_log"):
        value = loaded.get(key, [])
        if not isinstance(value, list) or any(not isinstance(v, dict) for v in value):
            return None, _error(CODE_MANUAL_INTERVENTION,
                                "{0}: invalid {1} history".format(path, key))
        state[key] = value
    state["schema_version"] = loaded.get("schema_version", 1)
    return state, None


def _trim_state(state: dict) -> None:
    state["waiters"] = state["waiters"][-_MAX_WAITERS:]
    state["reclaim_log"] = state["reclaim_log"][-_MAX_RECLAIM_LOG:]
    snapshots = state["snapshots"]
    if len(snapshots) > _MAX_SNAPSHOT_RECORDS:
        ordered = sorted(
            ((key, value) for key, value in snapshots.items() if value.get("released_at")),
            key=lambda kv: kv[1].get("released_at")
            or kv[1].get("created_at", ""))
        for key, _ in ordered[:len(snapshots) - _MAX_SNAPSHOT_RECORDS]:
            del snapshots[key]


# ── lockfiles (the cross-process primitive) ─────────────────────────────────


class _StateLock:
    """Use a kernel lock for crash recovery and retain the old O_EXCL marker."""

    def __init__(self, governance_dir, timeout_seconds=10.0):
        self.path = Path(governance_dir) / LOCK_DIR_NAME / "state.lock"
        self.timeout_seconds = timeout_seconds
        self._guard = None
        self._marker = "kernel-guard:{0}".format(os.getpid())

    def __enter__(self):
        from closure_chain import LockContention, _RunLock

        deadline = time.monotonic() + self.timeout_seconds
        self._guard = _RunLock(self.path.with_name("state.guard"), self.timeout_seconds)
        try:
            self._guard.__enter__()
        except LockContention as exc:
            raise IsolationLockTimeout(self.path) from exc
        try:
            while True:
                try:
                    with self.path.open("x", encoding="ascii") as marker:
                        marker.write(self._marker)
                    return self
                except FileExistsError:
                    try:
                        value = self.path.read_text(encoding="ascii")
                        old = time.time() - self.path.stat().st_mtime > _STALE_LOCKFILE_SECONDS
                        if value.startswith("kernel-guard:") or old:
                            # Holding state.guard proves the previous new-format
                            # owner is gone. Old numeric markers retain their grace.
                            self.path.unlink(missing_ok=True)
                            continue
                    except FileNotFoundError:
                        continue
                    if time.monotonic() >= deadline:
                        raise IsolationLockTimeout(self.path)
                    time.sleep(_LOCK_POLL_SECONDS)
        except BaseException:
            self._guard.__exit__(*sys.exc_info())
            raise

    def __exit__(self, *exc_info):
        try:
            if self.path.exists() and self.path.read_text(encoding="ascii") == self._marker:
                self.path.unlink(missing_ok=True)
        finally:
            self._guard.__exit__(*exc_info)


class IsolationLockTimeout(RuntimeError):
    """Retryable contention on the isolation state lock."""

    def __init__(self, path):
        super().__init__(str(path))
        self.path = path


def _domain_lockfile(governance_dir, domain: str) -> Path:
    key = _domain_key(governance_dir, domain)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    # A versioned directory keeps even a digest-shaped legacy filename distinct.
    return Path(governance_dir) / LOCK_DIR_NAME / "domains-v2" / (digest + ".write.lock")


def _legacy_filename(domain):
    return domain.replace("/", "__") + ".write.lock"


def _legacy_marker(governance_dir, state, domain):
    """Identify an older flat marker without guessing which original path it held."""
    folder = Path(governance_dir) / LOCK_DIR_NAME
    stored = _record_key(governance_dir, state["writers"], domain)
    marker = folder / _legacy_filename(stored)
    if not marker.is_file():
        return None, False
    # The old filename is ambiguous. Match the marker and recorded writer
    # using original fields before assigning it to either legal domain.
    holder = _read_lockfile(marker)
    matches = []
    for name, slot in state["writers"].items():
        old = folder / _legacy_filename(name)
        if (not slot.get("domain_key") and isinstance(holder, dict) and
                all(slot.get(k) == holder.get(k) for k in ("task_id", "writer", "began_at", "expires_at"))
                and old.is_file() and old.samefile(marker)):
            matches.append(name)
    if len(matches) == 1:
        if _domain_key(governance_dir, matches[0]) != _domain_key(governance_dir, domain):
            return None, False
        return marker, True
    if not matches and "__" not in marker.name:
        # Only a root-level spelling has an unambiguous reverse encoding.
        actual = marker.resolve().name[:-len(".write.lock")]
        if _domain_key(governance_dir, actual) != _domain_key(governance_dir, domain):
            return None, False
        return marker, True
    return marker, False


def _worker(writer="", session_id=None):
    # CLI invocations inherit the shell/session; API calls default to this process.
    session = (session_id or os.environ.get("GOVERNANCE_SESSION_ID")
               or os.environ.get("CODEX_THREAD_ID") or "pid:{0}".format(os.getpid()))
    cwd = Path.cwd().resolve()
    workspace = next((p for p in (cwd, *cwd.parents)
                      if (p / ".git").exists() or (p / GOVERNANCE_DIR_NAME).is_dir()), cwd)
    return {"session": str(session), "writer": str(writer or ""),
            "workspace": os.path.normcase(str(workspace))}


def _owns(record, task, worker):
    if record.get("ambiguous_legacy") or record.get("task_id") != task:
        return False
    if "worker" in record:
        return record["worker"] == worker
    # The old format only recorded a writer label (the marker also carried a
    # PID). An anonymous legacy slot cannot safely be claimed by task ID alone.
    return bool(record.get("writer") and record["writer"] == worker["writer"])


def _claims(governance_dir, state, domain):
    rows = []
    slot = state["writers"].get(_record_key(governance_dir, state["writers"], domain))
    if isinstance(slot, dict):
        rows.append(slot)
    legacy, identified = _legacy_marker(governance_dir, state, domain)
    markers = [(_domain_lockfile(governance_dir, domain), True), (legacy, identified)]
    for marker, identified in markers:
        if marker is None or not marker.exists():
            continue
        holder = _read_lockfile(marker)
        if not isinstance(holder, dict):
            try:
                modified = marker.stat().st_mtime
            except FileNotFoundError:
                continue
            expires = datetime.fromtimestamp(modified) + timedelta(seconds=_STALE_LOCKFILE_SECONDS)
            holder = {"task_id": "unknown", "expires_at": _iso(expires)}
        if not identified:
            holder = dict(holder, ambiguous_legacy=True)
        rows.append(holder)
    return rows


def _live(record, moment):
    deadline = _parse_iso(record.get("expires_at"))
    return deadline is None or deadline > moment


def _create_domain_lockfile(path, payload):
    blob = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("xb")
    try:
        with handle:
            handle.write(blob)
    except OSError:
        path.unlink(missing_ok=True)
        raise


def _read_lockfile(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ── locks file reading (lease face — READ ONLY, old-format tolerant) ───────


def _load_locks(governance_dir, locks_path=None):
    """Load agent-locks.json for lease judgment.

    Backward compatibility (hard gate): the OLD pre-FEAT-013 field shape
    parses unchanged — only ``file_locks[*].locked_at/ttl_seconds`` are
    consumed and they are mandatory in EVERY historical schema version.
    Missing file → ``({}, None)``; corrupt file → fail-closed error
    (a lease judgment over an unreadable registry would be fiction)."""
    path = Path(locks_path) if locks_path is not None \
        else Path(governance_dir) / LOCKS_FILE_NAME
    if not path.is_file():
        return {"file_locks": {}, "active_tasks": {}}, None
    try:
        raw = path.read_text(encoding="utf-8")
        loaded = json.loads(raw) if raw.strip() else {}
    except (OSError, ValueError) as exc:
        return None, _error(
            CODE_MANUAL_INTERVENTION,
            "{0} is unreadable ({1}) — lease judgment refused "
            "fail-closed; fix the file first".format(path, exc))
    if not isinstance(loaded, dict):
        return None, _error(
            CODE_MANUAL_INTERVENTION,
            "{0} root must be a JSON object — lease judgment refused "
            "fail-closed".format(path))
    file_locks = loaded.get("file_locks", {})
    active_tasks = loaded.get("active_tasks", {})
    if not isinstance(file_locks, dict):
        file_locks = {}
    if not isinstance(active_tasks, dict):
        active_tasks = {}
    return {"file_locks": file_locks, "active_tasks": active_tasks}, None


# ── piece ①+②+③ gate: judgment ────────────────────────────────────────────


def judge_write(task_id, files, *, governance_dir, locks_path=None,
                state_path=None, now=None, writer="", session_id=None) -> dict:
    """PURE judgment — no side effects, no lockfiles (≤10ms budget face).

    Refusal order per domain (first hit wins, all disclosed in result):
      1. ``snapshot_immutable`` — path under the review-snapshot root;
      2. ``lease_expired`` — the WRITER's own lease for the domain has
         expired (authority lost; reclaim candidate attached);
      3. ``under_review`` — an active review snapshot binds the domain;
      4. ``write_conflict`` — another worker holds a live write slot.

    A lease held by ANOTHER task is a disclosed NOTICE, never a refusal
    (dispatch-side blocking semantics are FEAT-095's scope — non_goal).
    """
    moment = _now(now)
    task = _require_task(task_id)
    if task is None:
        return _error(CODE_SCHEMA_VIOLATION,
                      "task_id must match PREFIX-NNN (got {0!r})"
                      .format(task_id))
    domains, err = _domains_or_error(files, governance_dir)
    if err is not None:
        return err

    spath = _state_path(governance_dir, state_path)
    state, err = _load_state(spath, governance_dir)
    if err is not None:
        return err
    locks, err = _load_locks(governance_dir, locks_path)
    if err is not None:
        return err

    worker = _worker(writer, session_id)
    refusals = []
    warnings = []
    reclaim_candidates = []
    # P2-2: domains are CANONICAL (no '..'/'.'/empty segments — see
    # _domain), so this literal prefix test IS the containment test: a
    # canonical domain starting with the snapshot root prefix cannot
    # resolve anywhere else, and a canonical domain resolving INSIDE the
    # root necessarily carries the prefix.
    snapshot_prefix = _snapshot_root_prefix()
    for domain in domains:
        if _domain_key(governance_dir, domain).startswith(
                _domain_key(governance_dir, snapshot_prefix.rstrip("/")) + "/"):
            refusals.append({
                "file": domain,
                "reason": CODE_SNAPSHOT_IMMUTABLE,
                "holder": "",
                "detail": "审查快照只读（FEAT-096 ③）：{0} 位于 "
                          "{1} 快照根下——快照不可变，写入被拒；如需修改"
                          "源文件请对源域操作".format(domain, snapshot_prefix),
            })
            continue
        lease_key = _record_key(governance_dir, locks["file_locks"], domain)
        entry = locks["file_locks"].get(lease_key)
        expiry = _lease_expiry(entry) if entry else None
        if (entry and entry.get("locked_by") == task
                and expiry is not None and expiry <= moment):
            refusals.append({
                "file": domain,
                "reason": CODE_LEASE_EXPIRED,
                "holder": task,
                "expired_at": _iso(expiry),
                "detail": "租约失权（FEAT-096 ④）：任务 {0} 对 {1} 的租约"
                          "已于 {2} 过期——写入权限已失效（authority "
                          "lost）；过期条目将被回收，重新写入须先经派发"
                          "重新取得租约（agent-locks-acquire）".format(
                              task, domain, _iso(expiry)),
            })
            reclaim_candidates.append(lease_key)
            continue
        if (entry and expiry is not None and expiry <= moment):
            # someone ELSE's expired lease — reclaim candidate, not a
            # refusal for this writer.
            reclaim_candidates.append(lease_key)
        review = state["reviews"].get(_record_key(governance_dir, state["reviews"], domain))
        if isinstance(review, dict) and review.get("task_id"):
            review_deadline = _review_deadline(review)
            refusals.append({
                "file": domain,
                "reason": CODE_UNDER_REVIEW,
                "holder": review.get("task_id"),
                "snapshot_id": review.get("snapshot_id"),
                "holder_worker": review.get("worker"),
                "expires_at": _iso(review_deadline) if review_deadline else None,
                "recoverable": bool(review_deadline and review_deadline <= moment),
                "began_at": review.get("began_at"),
                "detail": "同文件域被审互斥（FEAT-096 ②）：{0} 正被 "
                          "{1} 审查（快照 {2}，始于 {3}）——审查期间该域"
                          "禁止写入；预计释放：审查结束执行 "
                          "isolation-snapshot --action release；到期后可指定快照 ID 与原因执行 recover".format(
                              domain, review.get("task_id"),
                              review.get("snapshot_id"),
                              review.get("began_at")),
            })
            continue
        for claim in _claims(governance_dir, state, domain):
            if _live(claim, moment) and not _owns(claim, task, worker):
                refusals.append({
                    "file": domain, "reason": CODE_WRITE_CONFLICT,
                    "holder": claim.get("task_id", "unknown"),
                    "holder_worker": claim.get("worker"),
                    "expires_at": claim.get("expires_at"),
                    "detail": "{0} 正由 {1} 写入，预计释放 {2}".format(
                        domain, claim.get("task_id"), claim.get("expires_at")),
                })
                break
        if (entry and expiry is not None and expiry > moment
                and entry.get("locked_by") not in (None, "", task)):
            warnings.append(
                "WARN: {0} 的活性租约属于任务 {1}（至 {2}）——本门不阻断"
                "（派发侧阻断语义归 FEAT-095），差异需被看见".format(
                    domain, entry.get("locked_by"), _iso(expiry)))

    return {
        "task_id": task,
        "allowed": not refusals,
        "refusals": refusals,
        "warnings": warnings,
        "reclaim_candidates": sorted(set(reclaim_candidates)),
        "judged_at": _iso(moment),
    }


# ── piece ①: begin / end exclusive write ──────────────────────────────────


def begin_write(task_id, files, *, writer="", session_id=None, purpose="",
                ttl_seconds=DEFAULT_WRITE_SLOT_TTL_SECONDS,
                governance_dir, locks_path=None, state_path=None,
                now=None, timeout_seconds=10.0) -> dict:
    """Acquire the exclusive write slot for each file domain.

    Fail-closed: on ANY refusal nothing is granted (the refusal detail
    carries holder + expected release — ux contract); an own-expired
    lease refusal TRIGGERS the reclaim (piece ④) before returning.
    The rollback switch turns this into a pass-through.
    """
    if isolation_disabled():
        domains = [d for d in (_domain(f) for f in (files or [])) if d]
        return {"task_id": str(task_id or ""), "granted": domains,
                "gate_disabled": True,
                "note": "isolation gate disabled ({0}) — legacy soft-lock "
                        "behavior".format(DISABLE_ENV_VAR)}
    task = _require_task(task_id)
    if task is None:
        return _error(CODE_SCHEMA_VIOLATION,
                      "task_id must match PREFIX-NNN (got {0!r})"
                      .format(task_id))
    domains, err = _domains_or_error(files, governance_dir)
    if err is not None:
        return err
    try:
        ttl_seconds = int(ttl_seconds)
    except (TypeError, ValueError):
        return _error(CODE_SCHEMA_VIOLATION, "ttl_seconds must be an int")
    if ttl_seconds <= 0:
        return _error(CODE_SCHEMA_VIOLATION,
                      "ttl_seconds must be positive (got {0})"
                      .format(ttl_seconds))

    spath = _state_path(governance_dir, state_path)
    try:
        with _StateLock(governance_dir, timeout_seconds):
            moment = _now(now)
            state, err = _load_state(spath, governance_dir)
            if err is not None:
                return err
            # Keep the existing lease preflight; judgment and any reclaim
            # re-read once their own synchronization boundary is in effect.
            _, err = _load_locks(governance_dir, locks_path)
            if err is not None:
                return err

            judgment = judge_write(
                task, domains, governance_dir=governance_dir,
                locks_path=locks_path, state_path=spath, now=moment,
                writer=writer, session_id=session_id)
            if judgment.get("error"):
                return judgment

            if judgment["refusals"]:
                reclaim_report = None
                if judgment["reclaim_candidates"]:
                    reclaim_report = _reclaim_locked(
                        governance_dir, state, spath,
                        domains=set(judgment["reclaim_candidates"]),
                        moment=moment, trigger="write-refused",
                        locks_path=locks_path,
                        timeout_seconds=timeout_seconds)
                # waiters face (accessibility budget): the refused
                # writer is recorded machine-readably — never queued
                # (advisory, no priority arbitration).
                at = _iso(moment)
                for refusal in judgment["refusals"]:
                    state["waiters"].append({
                        "domain": refusal["file"],
                        "task_id": task,
                        "holder": refusal.get("holder", ""),
                        "reason": refusal["reason"],
                        "at": at,
                    })
                _trim_state(state)
                _write_json(spath, state)
                refusal_codes = sorted({
                    r["reason"] for r in judgment["refusals"]})
                return _error(
                    refusal_codes[0] if len(refusal_codes) == 1
                    else CODE_WRITE_CONFLICT,
                    "；".join(r["detail"] for r in judgment["refusals"]),
                    refusals=judgment["refusals"],
                    reclaim=reclaim_report)

            # StateLock serializes sanctioned marker mutations. A failed write
            # restores prior markers, including an existing owner's renewal.
            expires_at = _iso(moment + timedelta(seconds=ttl_seconds))
            worker = _worker(writer, session_id)
            payload = {"task_id": task, "writer": worker["writer"], "worker": worker,
                       "began_at": _iso(moment), "expires_at": expires_at}
            changed = {}
            try:
                for domain in domains:
                    stored = _record_key(governance_dir, state["writers"], domain)
                    legacy, identified = _legacy_marker(governance_dir, state, domain)
                    marker = _domain_lockfile(governance_dir, domain)
                    payload = dict(payload, domain=stored, domain_key=_domain_key(governance_dir, stored))
                    previous = marker.read_bytes() if marker.exists() else None
                    if previous is None:
                        _create_domain_lockfile(marker, payload)
                    else:
                        _write_json(marker, payload)
                    changed[marker] = previous
                    if legacy and identified:
                        before = legacy.read_bytes()
                        legacy.unlink()
                        changed[legacy] = before
                    state["writers"][stored] = dict(payload, purpose=str(purpose or ""))
                _trim_state(state)
                _write_json(spath, state)
            except OSError as exc:
                for marker, previous in reversed(list(changed.items())):
                    if previous is None:
                        marker.unlink(missing_ok=True)
                    else:
                        _atomic_write_bytes(marker, previous)
                return _error(CODE_MANUAL_INTERVENTION,
                              "write slot could not be recorded: {0}".format(exc))
            if judgment["reclaim_candidates"]:
                _reclaim_locked(
                    governance_dir, state, spath,
                    domains=set(judgment["reclaim_candidates"]),
                    moment=moment, trigger="begin-write",
                    locks_path=locks_path,
                    timeout_seconds=timeout_seconds)
            return {
                "task_id": task,
                "granted": domains, "worker": worker,
                "expires_at": expires_at,
                "warnings": judgment["warnings"],
                "began_at": _iso(moment),
            }
    except IsolationLockTimeout as exc:
        return _error(
            CODE_LOCK_CONTENTION,
            "isolation state lock busy: {0} — retry the same operation "
            "(transient, disposition retryable)".format(exc.path))


def end_write(task_id, files, *, governance_dir, state_path=None,
              now=None, timeout_seconds=10.0, writer="", session_id=None) -> dict:
    """Release the write slots held by ``task_id`` (fail-closed on a
    non-holder; idempotent no-op for already-free domains)."""
    if isolation_disabled():
        return {"task_id": str(task_id or ""), "released": [],
                "gate_disabled": True}
    task = _require_task(task_id)
    if task is None:
        return _error(CODE_SCHEMA_VIOLATION,
                      "task_id must match PREFIX-NNN (got {0!r})"
                      .format(task_id))
    domains, err = _domains_or_error(files, governance_dir)
    if err is not None:
        return err

    spath = _state_path(governance_dir, state_path)
    try:
        with _StateLock(governance_dir, timeout_seconds):
            moment = _now(now)
            state, err = _load_state(spath, governance_dir)
            if err is not None:
                return err
            released = []
            absent = []
            worker = _worker(writer, session_id)
            for domain in domains:
                claims = _claims(governance_dir, state, domain)
                if not claims:
                    absent.append(domain)
                elif all(_owns(c, task, worker) or
                         (c.get("ambiguous_legacy") and not _live(c, moment)) for c in claims):
                    released.append(domain)
                else:
                    return _error(CODE_NOT_HOLDER, "only the owner may release {0}".format(domain),
                                  holders=claims)
            for domain in released:
                legacy, identified = _legacy_marker(governance_dir, state, domain)
                if legacy and identified:
                    legacy.unlink(missing_ok=True)
                _domain_lockfile(governance_dir, domain).unlink(missing_ok=True)
                stored = _record_key(governance_dir, state["writers"], domain)
                state["writers"].pop(stored, None)
            _trim_state(state)
            _write_json(spath, state)
            return {"task_id": task, "released": released,
                    "absent": absent, "ended_at": _iso(moment)}
    except IsolationLockTimeout as exc:
        return _error(
            CODE_LOCK_CONTENTION,
            "isolation state lock busy: {0} — retry the same operation "
            "(transient, disposition retryable)".format(exc.path))


# ── piece ②+③: review snapshots ───────────────────────────────────────────


def create_review_snapshot(task_id, files, *, review_round=0,
                            reviewer="", session_id=None, ttl_seconds=DEFAULT_REVIEW_TTL_SECONDS,
                            governance_dir, repo_root=None,
                            state_path=None, now=None,
                            timeout_seconds=10.0) -> dict:
    """Freeze the file domains into a READ-ONLY review snapshot.

    Mutual exclusion (piece ②): a domain with a live write slot refuses
    the snapshot (Reviewer must not read a mid-write file); a domain
    already under review refuses a second snapshot (freshness — release
    first).  Immutability (piece ③): copies + manifest are chmod
    read-only and the write gate refuses writes under the snapshot root.
    """
    task = _require_task(task_id)
    if task is None:
        return _error(CODE_SCHEMA_VIOLATION,
                      "task_id must match PREFIX-NNN (got {0!r})"
                      .format(task_id))
    domains, err = _domains_or_error(files, governance_dir)
    if err is not None:
        return err
    try:
        review_round = int(review_round)
    except (TypeError, ValueError):
        return _error(CODE_SCHEMA_VIOLATION, "review_round must be an int")
    if review_round < 0:
        return _error(CODE_SCHEMA_VIOLATION,
                      "review_round must be >= 0 (got {0})"
                      .format(review_round))
    try:
        ttl = int(ttl_seconds)
        if ttl <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return _error(CODE_SCHEMA_VIOLATION, "review ttl_seconds must be a positive integer")
    worker = _worker(reviewer, session_id)
    root = Path(repo_root) if repo_root is not None else Path.cwd()

    spath = _state_path(governance_dir, state_path)
    try:
        with _StateLock(governance_dir, timeout_seconds):
            moment = _now(now)
            state, err = _load_state(spath, governance_dir)
            if err is not None:
                return err

            missing = [d for d in domains if not (root / d).is_file()]
            if missing:
                return _error(
                    CODE_SCHEMA_VIOLATION,
                    "snapshot target(s) do not exist under {0}: {1} — a "
                    "review snapshot freezes REAL files".format(
                        root, "; ".join(missing)))

            refusals = []
            for domain in domains:
                claim = next((c for c in _claims(governance_dir, state, domain)
                              if _live(c, moment)), None)
                if claim is not None:
                    refusals.append({"file": domain, "reason": CODE_WRITE_IN_PROGRESS,
                                     "holder": claim.get("task_id"),
                                     "holder_worker": claim.get("worker"),
                                     "expires_at": claim.get("expires_at"),
                                     "detail": "{0} 正在写入，待释放后创建快照".format(domain)})
                    continue
                review = state["reviews"].get(_record_key(governance_dir, state["reviews"], domain))
                if isinstance(review, dict) and review.get("task_id"):
                    refusals.append({
                        "file": domain,
                        "reason": CODE_UNDER_REVIEW,
                        "holder": review.get("task_id"),
                        "snapshot_id": review.get("snapshot_id"),
                        "detail": "{0} 已在审（快照 {1}，任务 {2}）——"
                                  "新一轮快照须先 release（快照新鲜度）"
                                  .format(domain,
                                          review.get("snapshot_id"),
                                          review.get("task_id")),
                    })
            if refusals:
                return _error(
                    refusals[0]["reason"],
                    "；".join(r["detail"] for r in refusals),
                    refusals=refusals)

            stamp = moment.strftime("%Y%m%dT%H%M%S")
            snapshot_id = "SNAP-{0}-R{1}-{2}".format(task, review_round,
                                                     stamp)
            snapshot_root = (Path(governance_dir) / SNAPSHOT_DIR_NAME
                             / snapshot_id)
            if snapshot_root.exists():
                return _error(
                    CODE_SCHEMA_VIOLATION,
                    "snapshot id {0} already exists ({1}) — a re-create "
                    "within the same second must not overwrite an "
                    "immutable snapshot; wait a second or release first"
                    .format(snapshot_id, snapshot_root))
            snapshot_root.mkdir(parents=True, exist_ok=True)

            # P2-2 defense-in-depth: the canonical-domain gate already
            # refuses '..'/absolute/empty-segment inputs, and this
            # resolved-containment assertion makes the invariant itself
            # load-bearing — a snapshot file may NEVER land outside the
            # snapshot root, whatever the input path spelled.
            resolved_root = snapshot_root.resolve()

            records = []
            try:
                for domain in domains:
                    source = root / domain
                    data = source.read_bytes()
                    target = snapshot_root / domain
                    resolved_target = target.resolve()
                    if not resolved_target.is_relative_to(resolved_root):
                        return _error(
                            CODE_SCHEMA_VIOLATION,
                            "snapshot target {0} resolves outside the "
                            "snapshot root {1} — containment refused "
                            "(FEAT-096 P2-2)".format(domain, resolved_root))
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                    os.chmod(target, stat.S_IREAD)
                    records.append({
                        "source": domain,
                        "snapshot": domain,
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "bytes": len(data),
                    })
            except OSError as exc:
                # a read-only prior artifact or a mid-copy failure must
                # surface as a clean refusal, never a traceback
                return _error(
                    CODE_MANUAL_INTERVENTION,
                    "snapshot copy failed for {0}: {1} — partial snapshot "
                    "left on disk for inspection; fix and re-run with a "
                    "fresh id".format(snapshot_id, exc))

            deadline = _iso(moment + timedelta(seconds=ttl))
            manifest = {
                "schema_version": 1,
                "snapshot_id": snapshot_id,
                "task_id": task, "worker": worker, "expires_at": deadline,
                "review_round": review_round,
                "created_at": _iso(moment),
                "files": records,
                "immutability": "read-only chmod + write-gate refusal "
                                "(FEAT-096 ③)",
            }
            manifest_path = snapshot_root / SNAPSHOT_MANIFEST_NAME
            _write_json(manifest_path, manifest)
            os.chmod(manifest_path, stat.S_IREAD)

            for domain in domains:
                state["reviews"][domain] = {
                    "domain_key": _domain_key(governance_dir, domain), "task_id": task, "worker": worker, "expires_at": deadline,
                    "snapshot_id": snapshot_id,
                    "round": review_round,
                    "began_at": _iso(moment),
                }
            state["snapshots"][snapshot_id] = {
                "task_id": task, "worker": worker, "expires_at": deadline,
                "review_round": review_round,
                "created_at": _iso(moment),
                "files": [r["source"] for r in records],
                "released_at": None,
            }
            _trim_state(state)
            _write_json(spath, state)
            return {
                "task_id": task, "worker": worker, "expires_at": deadline,
                "snapshot_id": snapshot_id,
                "snapshot_root": str(snapshot_root),
                "files": records,
                "domains": list(domains),
                "created_at": _iso(moment),
            }
    except IsolationLockTimeout as exc:
        return _error(
            CODE_LOCK_CONTENTION,
            "isolation state lock busy: {0} — retry the same operation "
            "(transient, disposition retryable)".format(exc.path))


def _review_deadline(review):
    if "expires_at" in review:
        return _parse_iso(review["expires_at"])
    # Old bindings recorded began_at but did not record a lease length.
    started = _parse_iso(review.get("began_at"))
    return started + timedelta(seconds=DEFAULT_REVIEW_TTL_SECONDS) if started else None


def recover_review(task_id, snapshot_id, *, governance_dir, reason, state_path=None,
                   now=None, timeout_seconds=10.0, reviewer="", session_id=None):
    """Release only an expired, explicitly named snapshot. Record the recovery."""
    if not snapshot_id or not str(reason or "").strip():
        return _error(CODE_SCHEMA_VIOLATION, "recovery requires a snapshot_id and reason")
    return _finish_review(task_id, snapshot_id, governance_dir, state_path, now,
                          timeout_seconds, _worker(reviewer, session_id), str(reason).strip())


def release_review(task_id, *, governance_dir, state_path=None, now=None, snapshot_id=None,
                   timeout_seconds=10.0, reviewer="", session_id=None) -> dict:
    """Release the caller's review bindings and retain all snapshot artifacts."""
    return _finish_review(task_id, snapshot_id, governance_dir, state_path, now,
                          timeout_seconds, _worker(reviewer, session_id), None)


def _finish_review(task_id, snapshot_id, governance_dir, state_path, now, timeout_seconds,
                   worker, recovery_reason):
    task = _require_task(task_id)
    if task is None:
        return _error(CODE_SCHEMA_VIOLATION, "task_id must match PREFIX-NNN")
    spath = _state_path(governance_dir, state_path)
    try:
        with _StateLock(governance_dir, timeout_seconds):
            moment = _now(now)
            state, err = _load_state(spath, governance_dir)
            if err is not None:
                return err
            requested = {d: r for d, r in state["reviews"].items()
                         if isinstance(r, dict) and r.get("task_id") == task
                         and (not snapshot_id or r.get("snapshot_id") == snapshot_id)}
            if recovery_reason:
                for review in requested.values():
                    expires = _review_deadline(review)
                    if not expires or expires > moment:
                        return _error(CODE_UNDER_REVIEW, "snapshot is still leased or its expiry "
                                      "is unknown", snapshot_id=snapshot_id,
                                      expires_at=_iso(expires) if expires else None)
                if not requested:
                    record = state["snapshots"].get(snapshot_id, {})
                    if record.get("task_id") != task or not record.get("released_at"):
                        return _error(CODE_NOT_HOLDER, "no matching review to recover")
                selected = requested
            else:
                # Legacy snapshots were owned by task. New snapshots also bind
                # a reviewer; other reviewers of the same task remain active.
                selected = {d: r for d, r in requested.items()
                            if "worker" not in r or r["worker"] == worker}
                if requested and not selected:
                    return _error(CODE_NOT_HOLDER, "only the reviewer may release this snapshot")

            for review in selected.values():
                record = state["snapshots"].get(review.get("snapshot_id"), {})
                if record.get("task_id", task) != task:
                    return _error(CODE_MANUAL_INTERVENTION,
                                  "review binding and snapshot inventory disagree on ownership")
            snapshots = set()
            for domain, review in selected.items():
                del state["reviews"][domain]
                sid = review.get("snapshot_id")
                if sid:
                    # Older retention could trim an active snapshot's catalogue
                    # entry. Retain its binding and disposition in the audit trail.
                    if sid not in state["snapshots"]:
                        state["snapshots"][sid] = {
                            "task_id": task, "created_at": review.get("began_at"),
                            "review_round": review.get("round"),
                            "files": [d for d, r in selected.items() if r.get("snapshot_id") == sid],
                        }
                    record = state["snapshots"][sid]
                    record.update(released_at=_iso(moment), released_by=worker)
                    if recovery_reason:
                        record["recovery_reason"] = recovery_reason
                    snapshots.add(sid)
            if selected:
                _trim_state(state)
                _write_json(spath, state)
            return {"task_id": task, "released": list(selected), "snapshots": sorted(snapshots),
                    "released_at": _iso(moment), "recovery_reason": recovery_reason}
    except IsolationLockTimeout as exc:
        return _error(CODE_LOCK_CONTENTION, "isolation state lock busy: {0}".format(exc.path))


# ── piece ④: lease reclaim with loss-of-authority verification ────────────


def _reclaim_locked(governance_dir, state, spath, *, domains,
                    moment, trigger, locks_path=None,
                    timeout_seconds=10.0) -> dict:
    """Reclaim expired leases from ``agent-locks.json`` under BOTH locks.

    P1-1 (review R0): ``agent-locks.json`` has an established cross-
    process write protocol — every governance_store writer (acquire /
    amend / release) mutates it under ``governance_store._TargetLock``
    (``.governance-store-locks/agent-locks.json.lock``).  This module's
    reclaim is the ONLY other writer, so it MUST take the same lock —
    lock order is state.lock (OUTER, already held by the caller) →
    target-lock (INNER, taken here): one-way, acyclic — governance_store
    writers never take the isolation state lock, so no deadlock is
    possible.

    Lost-update closure: the reclaim decisions are computed against a
    FRESH read taken under the target lock (never the caller's earlier
    snapshot) — a lease committed by a concurrent ``agent-locks-acquire``
    between the caller's read and this lock is therefore preserved, and
    a lease extended by ``locks-extend`` in that window is no longer
    judged expired.  ``domains`` only limits the candidate scope.

    ``governance_store`` is imported FUNCTION-LOCALLY (the
    authority_ledger peer-leaf pattern): the module stays stdlib-only at
    import time (R6 cold-face unchanged) — the dependency exists only
    on the reclaim path, where the lock protocol demands it.
    """
    from governance_store import StoreError, _TargetLock

    target = Path(locks_path) if locks_path is not None \
        else Path(governance_dir) / LOCKS_FILE_NAME
    try:
        with _TargetLock(target, timeout_seconds):
            # authoritative fresh read under BOTH locks (查世界不信快照)
            locks, err = _load_locks(governance_dir, locks_path)
            if err is not None:
                return err
            reclaimed = []
            revoked_slots = []
            for domain in sorted(domains):
                entry = locks["file_locks"].get(domain)
                expiry = _lease_expiry(entry) if entry else None
                if expiry is None or expiry > moment:
                    continue
                task = entry.get("locked_by", "unknown") \
                    if entry else "unknown"
                # loss-of-authority verification: the expired lease AND
                # any residual write slot of the same task are revoked
                # together.
                stored = _record_key(governance_dir, state["writers"], domain)
                slot = state["writers"].get(stored)
                if (isinstance(slot, dict)
                        and slot.get("task_id") == task):
                    legacy, identified = _legacy_marker(governance_dir, state, domain)
                    markers = [_domain_lockfile(governance_dir, domain)]
                    if legacy and identified:
                        markers.append(legacy)
                    for marker in markers:
                        holder = _read_lockfile(marker)
                        if (isinstance(holder, dict) and holder.get("task_id") == task
                                and holder.get("worker") == slot.get("worker")
                                and holder.get("writer") == slot.get("writer")):
                            marker.unlink(missing_ok=True)
                    del state["writers"][stored]
                    revoked_slots.append(domain)
                del locks["file_locks"][domain]
                state["reclaim_log"].append({
                    "domain": domain,
                    "task_id": task,
                    "expired_at": _iso(expiry),
                    "reclaimed_at": _iso(moment),
                    "trigger": trigger,
                })
                reclaimed.append({
                    "domain": domain,
                    "task_id": task,
                    "expired_at": _iso(expiry),
                })
            removed_tasks = []
            if reclaimed:
                holders = {e.get("locked_by") for e in
                           locks["file_locks"].values()
                           if isinstance(e, dict) and e.get("locked_by")}
                for task_id in list(locks["active_tasks"].keys()):
                    if task_id not in holders:
                        del locks["active_tasks"][task_id]
                        removed_tasks.append(task_id)
                _write_json(target, locks)
                _trim_state(state)
                _write_json(spath, state)
            return {
                "reclaimed": reclaimed,
                "revoked_slots": revoked_slots,
                "removed_active_tasks": removed_tasks,
                "trigger": trigger,
                "unchanged": not reclaimed,
            }
    except StoreError as exc:
        # _TargetLock contention/timeout refusal — surfaced as this
        # module's retryable lock_contention code, never a raw traceback
        return _error(
            CODE_LOCK_CONTENTION,
            "agent-locks target lock busy during reclaim ({0}) — retry "
            "the same operation (transient, disposition retryable)"
            .format(exc.payload.get("detail", str(exc))))


def reclaim_expired_leases(*, governance_dir, locks_path=None,
                           state_path=None, now=None,
                           timeout_seconds=10.0) -> dict:
    """Reclaim EVERY expired lease (standalone recovery face — works
    even when the concurrency gate is switched off).

    Fail-closed: a corrupt locks file refuses with nothing written; a
    missing locks file is an empty-world no-op.  Old-format lock files
    parse unchanged (backward-compatibility hard gate).
    """
    moment = _now(now)
    spath = _state_path(governance_dir, state_path)
    try:
        with _StateLock(governance_dir, timeout_seconds):
            locks, err = _load_locks(governance_dir, locks_path)
            if err is not None:
                return err
            state, err = _load_state(spath, governance_dir)
            if err is not None:
                return err
            return _reclaim_locked(
                governance_dir, state, spath,
                domains=set(locks["file_locks"].keys()),
                moment=moment, trigger="manual-reclaim",
                locks_path=locks_path,
                timeout_seconds=timeout_seconds)
    except IsolationLockTimeout as exc:
        return _error(
            CODE_LOCK_CONTENTION,
            "isolation state lock busy: {0} — retry the same operation "
            "(transient, disposition retryable)".format(exc.path))


# ── status / capability faces ──────────────────────────────────────────────


def isolation_status(*, governance_dir, locks_path=None, state_path=None,
                     now=None) -> dict:
    """Machine-readable isolation world: 谁持锁 / 租约到期时间 / 等待者 /
    回收史 / 快照账 — the accessibility face (greppable via
    :func:`render_status_text`)."""
    moment = _now(now)
    spath = _state_path(governance_dir, state_path)
    state, err = _load_state(spath, governance_dir)
    if err is not None:
        return err
    locks, err = _load_locks(governance_dir, locks_path)
    if err is not None:
        return err

    writers = {}
    for domain, slot in state["writers"].items():
        if isinstance(slot, dict):
            writers[domain] = dict(slot, domain_key=_domain_key(governance_dir, domain))
    folder = Path(governance_dir) / LOCK_DIR_NAME
    unidentified = []
    for marker in (folder / "domains-v2").glob("*.write.lock"):
        holder = _read_lockfile(marker)
        domain = _domain(holder.get("domain")) if isinstance(holder, dict) else ""
        if not domain or _domain_lockfile(governance_dir, domain) != marker:
            unidentified.append(marker.name)
            continue
        stored = _record_key(governance_dir, writers, domain)
        if stored not in writers:
            writers[domain] = dict(holder, marker_only=True)
    for marker in folder.glob("*.write.lock"):
        if any(_legacy_marker(governance_dir, state, name) == (marker, True)
               for name in state["writers"]):
            continue
        # A marker-only root name is reversible; flattened names are not.
        name = marker.name[:-len(".write.lock")]
        holder = _read_lockfile(marker)
        if "__" not in name and isinstance(holder, dict) and _domain(name):
            writers.setdefault(_record_key(governance_dir, writers, name),
                               dict(holder, domain_key=_domain_key(governance_dir, name),
                                    marker_only=True))
        else:
            unidentified.append(marker.name)
    leases = {}
    for domain, entry in locks["file_locks"].items():
        if not isinstance(entry, dict):
            continue
        expiry = _lease_expiry(entry)
        leases[domain] = {
            "task_id": entry.get("locked_by", ""),
            "locked_at": entry.get("locked_at", ""),
            "ttl_seconds": entry.get("ttl_seconds"),
            "lease_expiry": _iso(expiry) if expiry else "",
            "expired": bool(expiry and expiry <= moment),
        }
    reviews = {}
    for domain, review in state["reviews"].items():
        if isinstance(review, dict):
            deadline = _review_deadline(review)
            reviews[domain] = dict(review, domain_key=_domain_key(governance_dir, domain),
                                   expires_at=_iso(deadline) if deadline else None,
                                   recoverable=bool(deadline and deadline <= moment))
    return {
        "generated_at": _iso(moment),
        "gate_disabled": isolation_disabled(),
        "writers": writers,
        "unattributed_markers": sorted(unidentified),
        "leases": leases,
        "reviews": reviews,
        "waiters": state["waiters"][-20:],
        "reclaim_log": state["reclaim_log"][-20:],
        "snapshots": {
            sid: {"task_id": rec.get("task_id"),
                  "review_round": rec.get("review_round"),
                  "created_at": rec.get("created_at"),
                  "released_at": rec.get("released_at"),
                  "recovery_reason": rec.get("recovery_reason"),
                  "released_by": rec.get("released_by"),
                  "files": rec.get("files", [])}
            for sid, rec in list(state["snapshots"].items())[-20:]
            if isinstance(rec, dict)},
        "capability": {
            "report": CAPABILITY_REPORT_REF,
            "host_isolation_level": "unverified",
        },
    }


def render_status_text(status: dict) -> str:
    """Grep-anchor rendering of :func:`isolation_status` (accessibility
    quality budget: 谁持锁 / 租约到期时间 / 等待者 机器可 grep)."""
    lines = [
        "isolation_disabled={0}".format(
            1 if status.get("gate_disabled") else 0),
        "capability report={0} host_isolation={1}".format(
            status.get("capability", {}).get("report",
                                             CAPABILITY_REPORT_REF),
            status.get("capability", {}).get("host_isolation_level",
                                             "unverified")),
        "generated_at={0}".format(status.get("generated_at", "")),
    ]
    for domain in sorted(status.get("writers", {})):
        slot = status["writers"][domain]
        lines.append(
            "writer domain={0} task={1} began_at={2} expires_at={3} worker={4}"
            .format(domain, slot.get("task_id"),
                    slot.get("began_at"), slot.get("expires_at"), slot.get("worker")))
    for domain in sorted(status.get("leases", {})):
        lease = status["leases"][domain]
        lines.append(
            "lease domain={0} task={1} lease_expiry={2} expired={3}"
            .format(domain, lease.get("task_id"),
                    lease.get("lease_expiry"),
                    1 if lease.get("expired") else 0))
    for domain in sorted(status.get("reviews", {})):
        review = status["reviews"][domain]
        lines.append(
            "review domain={0} task={1} snapshot={2} round={3} worker={4} expires_at={5} recoverable={6}".format(
                domain, review.get("task_id"),
                review.get("snapshot_id"), review.get("round"), review.get("worker"),
                review.get("expires_at"), review.get("recoverable")))
    for waiter in status.get("waiters", []):
        lines.append(
            "waiter domain={0} task={1} holder={2} at={3}".format(
                waiter.get("domain"), waiter.get("task_id"),
                waiter.get("holder"), waiter.get("at")))
    for entry in status.get("reclaim_log", []):
        lines.append(
            "reclaimed domain={0} task={1} expired_at={2}".format(
                entry.get("domain"), entry.get("task_id"),
                entry.get("expired_at")))
    for sid in sorted(status.get("snapshots", {})):
        rec = status["snapshots"][sid]
        lines.append(
            "snapshot id={0} task={1} files={2} released={3}".format(
                sid, rec.get("task_id"), len(rec.get("files", [])),
                rec.get("released_at") or "-"))
    return "\n".join(lines) + "\n"


def capability_disclosure() -> dict:
    """FEAT-096 capability honesty face (acceptance ①).

    References the ON-DISK FEAT-095 research report; claims NOTHING the
    report has not verified (U1 未证实 → no host-level claim).
    """
    return {
        "report": CAPABILITY_REPORT_REF,
        "report_conclusions": [
            "host-level interception is unwired on all six platforms "
            "(§5 matrix: every boundary 宿主级 = 未证实 or 原语存在未接线)",
            "dsh pre-execute guard PoC is UNVERIFIED (§7 U1) — no "
            "host-level claim is made anywhere in this module",
            "worktree-per-task isolation is therefore NOT a "
            "plugin-enforced surface today (§6 发现1)",
        ],
        "host_isolation_level": "unverified",
        "delivered_surface": "cli-level conservative four-piece set",
        "conservative_surface": [
            "shared-file write concurrency limit",
            "same-file-domain under-review/being-written mutex",
            "read-only review snapshots",
            "lease reclaim with loss-of-authority verification",
        ],
        "non_goals": [
            "no heavyweight virtualization/container dependency",
            "dispatch-side blocking semantics after a mutex trigger "
            "belong to FEAT-095",
            "agent-locks.json field format unchanged (old lock files "
            "stay readable and reclaimable)",
        ],
        "rollback": "{0}=off disables the concurrency gate (pass-through "
                    "legacy behavior); lease reclaim stays functional"
                    .format(DISABLE_ENV_VAR),
    }


# ── CLI (module composition root + engine thin-entry handlers) ────────────


def _configure_stdio() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 — best-effort console hygiene
        pass


def _split_cli_list(raw):
    return [item.strip()
            for item in str(raw or "").replace(";", ",").split(",")
            if item.strip()]


def _emit(payload, *, refused=None) -> int:
    """Print the JSON payload; exit 0 ok / 2 refusal (fail-closed).

    ``refused`` lets a NON-error gate verdict (judge's
    ``allowed: false``) still exit 2 — callers branch on the code, the
    JSON carries the reasons."""
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if payload.get("error") or refused:
        return 2
    return 0


def add_write_arguments(parser: argparse.ArgumentParser) -> None:
    """Option fact source for ``isolation-write`` (single definition
    shared by the module parser and the engine subparser)."""
    parser.add_argument("--action", required=True,
                        choices=("begin", "end", "judge"),
                        help="begin = acquire the exclusive write slot / "
                             "end = release it / judge = pure permission "
                             "check (no side effects)")
    parser.add_argument("--task", required=True,
                        help="writer task id (PREFIX-NNN)")
    parser.add_argument("--files", required=True,
                        help="comma/semicolon-separated repo-relative "
                             "file domains")
    parser.add_argument("--session", help="stable session ID (default: environment / parent process)")
    parser.add_argument("--writer", default="",
                        help="writer identity (session/agent label)")
    parser.add_argument("--purpose", default="",
                        help="one-line write purpose (recorded on the "
                             "slot)")
    parser.add_argument("--ttl", type=int,
                        default=DEFAULT_WRITE_SLOT_TTL_SECONDS,
                        help="write-slot TTL seconds (default {0})"
                        .format(DEFAULT_WRITE_SLOT_TTL_SECONDS))
    parser.add_argument("--timeout", type=float, default=10.0,
                        help="state-lock wait seconds (default 10)")


def add_snapshot_arguments(parser: argparse.ArgumentParser) -> None:
    """Option fact source for ``isolation-snapshot``."""
    parser.add_argument("--action", required=True,
                        choices=("create", "release", "recover"))
    parser.add_argument("--task", required=True,
                        help="task id UNDER REVIEW (PREFIX-NNN)")
    parser.add_argument("--files", default="",
                        help="comma/semicolon-separated domains (create "
                             "only; release frees the caller's matching domains)")
    parser.add_argument("--reviewer", default="", help="reviewer identity")
    parser.add_argument("--session", help="stable session ID (default: environment / parent process)")
    parser.add_argument("--snapshot-id", help="exact snapshot for release or expired recovery")
    parser.add_argument("--reason", help="recorded reason for recovery")
    parser.add_argument("--ttl", type=int, default=DEFAULT_REVIEW_TTL_SECONDS,
                        help="review lease in seconds before explicit recovery is allowed")
    parser.add_argument("--round", type=int, default=0,
                        help="review round stamped into the snapshot id")
    parser.add_argument("--timeout", type=float, default=10.0)


def add_lease_reclaim_arguments(parser: argparse.ArgumentParser) -> None:
    """Option fact source for ``isolation-lease-reclaim``."""
    parser.add_argument("--timeout", type=float, default=10.0)


def add_status_arguments(parser: argparse.ArgumentParser) -> None:
    """Option fact source for ``isolation-status``."""
    parser.add_argument("--text", action="store_true",
                        help="grep-anchor text rendering instead of JSON")


def add_capability_arguments(parser: argparse.ArgumentParser) -> None:
    """Option fact source for ``isolation-capability``."""
    parser.add_argument("--text", action="store_true",
                        help="human-readable rendering instead of JSON")


def _cli_session(args):
    return (getattr(args, "session", None) or os.environ.get("GOVERNANCE_SESSION_ID")
            or os.environ.get("CODEX_THREAD_ID") or "pid:{0}".format(os.getppid()))


def cmd_isolation_write(args, *, governance_dir,
                        repo_root=None) -> int:
    """Engine dispatch face — ``isolation-write`` (begin/end/judge)."""
    _configure_stdio()
    files = _split_cli_list(getattr(args, "files", ""))
    action = getattr(args, "action", "begin")
    owner = {"writer": getattr(args, "writer", ""), "session_id": _cli_session(args)}
    if action == "judge":
        payload = judge_write(
            getattr(args, "task", ""), files,
            governance_dir=governance_dir, **owner)
        return _emit(payload, refused=payload.get("allowed") is False)
    if action == "end":
        return _emit(end_write(
            getattr(args, "task", ""), files,
            governance_dir=governance_dir, **owner,
            timeout_seconds=getattr(args, "timeout", 10.0)))
    return _emit(begin_write(
        getattr(args, "task", ""), files,
        **owner,
        purpose=getattr(args, "purpose", "") or "",
        ttl_seconds=getattr(args, "ttl", DEFAULT_WRITE_SLOT_TTL_SECONDS),
        governance_dir=governance_dir,
        timeout_seconds=getattr(args, "timeout", 10.0)))


def cmd_isolation_snapshot(args, *, governance_dir,
                           repo_root=None) -> int:
    """Engine dispatch face — ``isolation-snapshot`` (create/release)."""
    _configure_stdio()
    owner = {"reviewer": getattr(args, "reviewer", ""), "session_id": _cli_session(args)}
    common = dict(governance_dir=governance_dir, timeout_seconds=getattr(args, "timeout", 10.0),
                  **owner)
    task = getattr(args, "task", "")
    action = getattr(args, "action", "create")
    if action == "recover":
        return _emit(recover_review(task, getattr(args, "snapshot_id", None),
                                    reason=getattr(args, "reason", None), **common))
    if action == "release":
        return _emit(release_review(task, snapshot_id=getattr(args, "snapshot_id", None), **common))
    return _emit(create_review_snapshot(
        task, _split_cli_list(getattr(args, "files", "")), repo_root=repo_root,
        review_round=getattr(args, "round", 0), ttl_seconds=getattr(args, "ttl", DEFAULT_REVIEW_TTL_SECONDS),
        **common))


def cmd_isolation_lease_reclaim(args, *, governance_dir,
                                repo_root=None) -> int:
    """Engine dispatch face — ``isolation-lease-reclaim``."""
    _configure_stdio()
    return _emit(reclaim_expired_leases(
        governance_dir=governance_dir,
        timeout_seconds=getattr(args, "timeout", 10.0)))


def cmd_isolation_status(args, *, governance_dir,
                         repo_root=None) -> int:
    """Engine dispatch face — ``isolation-status``."""
    _configure_stdio()
    status = isolation_status(governance_dir=governance_dir)
    if getattr(args, "text", False):
        if status.get("error"):
            return _emit(status)
        print(render_status_text(status), end="")
        return 0
    return _emit(status)


def cmd_isolation_capability(args, *, governance_dir=None,
                             repo_root=None) -> int:
    """Engine dispatch face — ``isolation-capability``."""
    _configure_stdio()
    disclosure = capability_disclosure()
    if getattr(args, "text", False):
        for key, value in disclosure.items():
            if isinstance(value, list):
                for item in value:
                    print("{0}: {1}".format(key, item))
            else:
                print("{0}: {1}".format(key, value))
        return 0
    print(json.dumps(disclosure, ensure_ascii=False, indent=2))
    return 0


def build_parser():
    """Module-owned composition root (the engine wires dispatch only)."""
    parser = argparse.ArgumentParser(
        prog="execution_isolation.py",
        description="FEAT-096 execution isolation conservative surface — "
                    "write concurrency limit + review/write mutex + "
                    "read-only snapshots + lease reclaim with "
                    "loss-of-authority verification")
    parser.add_argument("--project-root", default=".",
                        help="host project root (default: cwd); the "
                             "governance dir is <root>/.governance")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser(
        "isolation-write",
        help="exclusive write slot per file domain (begin/end/judge)")
    add_write_arguments(p)

    p = sub.add_parser(
        "isolation-snapshot",
        help="read-only review snapshot (create/release)")
    add_snapshot_arguments(p)

    p = sub.add_parser(
        "isolation-lease-reclaim",
        help="reclaim expired agent-locks leases (loss-of-authority "
             "verified)")
    add_lease_reclaim_arguments(p)

    p = sub.add_parser(
        "isolation-status",
        help="machine-readable isolation world (writers/leases/reviews/"
             "waiters)")
    add_status_arguments(p)

    p = sub.add_parser(
        "isolation-capability",
        help="capability disclosure (references the FEAT-095 report; "
             "no host-level claim)")
    add_capability_arguments(p)
    return parser


def main(argv=None) -> int:
    """CLI entry — JSON on stdout; exit 0 ok / 2 refusal (fail-closed)."""
    _configure_stdio()
    args = build_parser().parse_args(argv)
    governance_dir = (Path(getattr(args, "project_root", ".") or ".")
                      / GOVERNANCE_DIR_NAME)
    repo_root = Path(getattr(args, "project_root", ".") or ".")
    handlers = {
        "isolation-write": cmd_isolation_write,
        "isolation-snapshot": cmd_isolation_snapshot,
        "isolation-lease-reclaim": cmd_isolation_lease_reclaim,
        "isolation-status": cmd_isolation_status,
        "isolation-capability": cmd_isolation_capability,
    }
    return handlers[args.command](args, governance_dir=governance_dir,
                                  repo_root=repo_root)


if __name__ == "__main__":
    sys.exit(main())
