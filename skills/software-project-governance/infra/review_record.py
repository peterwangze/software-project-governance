"""Review-record writer + Wiring A (FIX-236.1 / ADR-017 §3.2, §3.4).

The **single machine-written review-conclusion persistence path** (P1-1
anchor): ``review-record`` CLI (verify_workflow.py thin entry) delegates here.
It writes ``review-{id}-R{n}.md`` + an evidence-log row in the Check 30
(V1~V5) parseable contract, and then, when a review→unit/gate mapping
resolves, invokes :func:`loop_gate_processor.process_gate_result` as Wiring A
(thin call, ADR-014 §6.1).

Behavior contract (ADR-017 §3.4):

  - **Machine write**: review file + evidence row are written FIRST and
    independently of the loop state machine. A wiring failure (CAS conflict /
    lock / exception) must NEVER block the review record — it is recorded as a
    ``degraded`` marker in the wiring summary.
  - **Mapping is data, not logic**: review role → gate_id is a module-level
    registry-side table (:data:`REVIEW_GATE_MAPPING`, documented defaults for
    the ADR-014 §6.1 examples). When no mapping resolves (or no flow-unit id),
    wiring is SKIPPED with a WARN reason — the review record still lands.
  - **复审必达**: a NEEDS_CHANGE record carries the structured revisit fields
    ``next_round=REVIEW-{id}-R{n+1}`` + ``prev_report`` so Check 30 V6 and the
    Coordinator can verify / spawn the R+1 revisit.
  - **覆盖守卫 (FIX-289⑤ / FIX-314 three-key extension)**: a review file is
    an immutable task+round+reviewer record (key extended from task+round by
    FIX-314 so the two halves of one review round never collide — REL-076
    M-3 dual-half defect). The FIRST reviewer of a round owns the canonical
    ``review-{task}-R{n}.md`` name — legacy single-reviewer files included:
    a file without a matching owner is never rewritten, only namespaced
    around. A DIFFERENT reviewer for the same task+round lands in
    ``review-{task}-R{n}-{reviewer-slug}.md`` with the mirrored evidence id
    ``REVIEW-{task}-R{n}-{SLUG}`` (the ``REVIEW-{task}-R{n}`` canonical
    prefix stays intact for the Check 30/30c live row scans and the
    commit-msg evidence gate). Writing over a reviewer's OWN existing file
    is rejected (error dict, nothing written — no overwrite, no evidence
    row) unless ``force=True``:
    the deliberate overwrite then backs up the previous record
    (``review-{id}-R{n}.pre-<ts>.md``), marks the overwrite in the new record,
    and reports the backup in the summary (REL-073 same-number overwrite
    near-miss; historical backfill / migrated data must never be silently
    replaced).
  - **审查结论必机录 (FIX-260 / REQ-107)**: calling this CLI is a MUST for
    every Reviewer conclusion (behavior-protocol.md M7.4 step 4.6 C8; the
    M1.2 fast lane no longer exempts handwritten REVIEW rows). Check 30c
    (``check_review_machine_provenance``) WARNs on REVIEW rows/files dated
    on/after 2026-08-22 that lack the machine markers emitted here — the
    gradual-FAIL escalation path is registered in the FIX-260 decision log.
  - **loop_exit → next-unit bridge**: when the wiring outcome is ``exit``,
    :func:`loop_exit_bridge.refresh_candidates` is invoked best-effort so the
    next-unit candidate snapshot stays fresh (FIX-236.3 consumer).

FEAT-094 — 审查可信链 (five-step indivisible review transaction):

  提交报告 → 验证结构与修订 → 登记发现 → 自动生成后续义务 → 更新状态.
  The RPG long-haul session measured the three trust failures this closes
  (report §3.5): REV-009 reviewed a phantom revision (untracked +
  concurrently rewritten object); REV-001/002 declared R2 obligations in
  machine records that then evaporated; REV-009-R2's machine record said
  APPROVED while the report's own text said NEEDS_CHANGE.

  ① **Immutable snapshot binding** — every record pins the reviewed
  object: the report's byte sha256, the HEAD commit sha, a worktree
  cleanliness disclosure and optional per-file ``git hash-object`` blob
  pins (untracked-safe — a rewrite after the record is detectable via
  :func:`verify_review_trust`).
  ② **R2 obligations live in the authority ledger** — a NEEDS_CHANGE
  record registers its ``RECHECK-{task}-R{n+1}`` obligation in the SAME
  ledger ``transact`` batch as the ``review_recorded`` event (atomic;
  evaporation structurally impossible — the append-only log never drops
  events) and the key is unique (duplicate open registrations refused at
  the writer).  The ONLY discharger is the discharging round's own review
  transaction (or an explicit manual ``recheck_obligation_cleared`` event).
  ③ **CONFLICT, never the optimistic winner** — when the report clearly
  carries verdict token(s) and the claimed result disagrees, the write is
  REFUSED with a manual-resolution disposition (nothing written).
  Supervisor escalation states (BLOCKED — the T2 round≥3 escalation;
  ABORTED / UNKNOWN — agent death) are exempt: an escalation RECORDING a
  harsher state than the report is the designed trigger semantics, not an
  inconsistency.
  ⑤ **Agent death** — the supervisor records ABORTED / UNKNOWN terminal
  records (``--result ABORTED|UNKNOWN`` + ``--abort-reason``); death does
  NOT discharge an open recheck obligation (the round still owes a real
  verdict).

  Ordering (anti-evaporation): the ledger transaction commits FIRST
  (atomic review+obligation batch), then the review file and evidence row
  land; a failure between them is compensated (a file this transaction
  created is unlinked) and disclosed — never silently half-committed.  A
  ledger refusal (integrity broken / contract refused) refuses the whole
  transaction: no file, no row (异常不隐藏).

  复审必达触发器语义 UNCHANGED (non_goal): T1/T2, round+1, prev_report
  injection keep their exact semantics — the ``next_round`` /
  ``prev_report`` fields and summary keys are byte-compatible with the
  pre-FEAT-094 writer; this ticket only ADDS trust binding around them.

This module is product code (Governance Developer domain) and stays
import-cycle-free: it imports loop_gate_processor (peer) and loop_exit_bridge
(peer, pure) lazily inside the exit-refresh path.  authority_ledger (peer,
stdlib-only) is imported lazily inside the transaction path so the cold
import face of the loop-wiring consumers is unchanged.
"""

import hashlib
import re
import subprocess
from datetime import date, datetime
from pathlib import Path

from loop_gate_processor import process_gate_result  # noqa: F401 (re-exported)


# Registry-side mapping data (not logic): review role → default gate_id.
# Only the ADR-014 §6.1 documented mappings are declared; other roles require
# explicit --unit/--gate (mapping-missing → WARN skip). Promoted to
# core/loop-engineering-registry.json in a later phase.
REVIEW_GATE_MAPPING = {
    "CODE": "G6",      # code-review → G6 (inner-loop exit)
    "DESIGN": "G5",    # design-review → G5 (middle-loop entry)
    "RELEASE": "G9",   # release-review → G9 (middle-loop exit)
}

# Wiring B data (FIX-236.2 / ADR-017 §3.4): gate-engine verdict → review
# conclusion. Lives here (registry-side data), NOT in verify_workflow.py —
# the auto_judge_gate wiring is a thin call over this mapping. "needs_human"
# is deliberately absent: no verdict is rendered, so no wiring happens.
GATE_VERDICT_TO_RESULT = {
    "passed": "APPROVED",
    "passed-with-conditions": "APPROVED_WITH_NOTES",
    "blocked": "NEEDS_CHANGE",
}

_ROLE_TOKEN_RE = re.compile(r"(?:^|[_-])(CODE|DESIGN|RELEASE)(?:[_-]|$)")
_TASK_ID_RE = re.compile(r"^[A-Z]+-\d+$")
# FEAT-094: ABORTED/UNKNOWN = supervisor-recorded agent-death terminal
# states (never trigger a revisit, never discharge an open obligation).
_RESULT_RE = re.compile(
    r"^(APPROVED|APPROVED_WITH_NOTES|NEEDS_CHANGE|BLOCKED|ABORTED|UNKNOWN)$",
    re.IGNORECASE)
# FEAT-094 ③: verdict tokens a report may clearly carry (bold span or
# 审查结论-line); free-form reports without either shape are NOT
# conflict-judged (the byte-hash pin still applies).
_VERDICT_BOLD_RE = re.compile(
    r"\*\*(APPROVED_WITH_NOTES|APPROVED|NEEDS_CHANGE|BLOCKED)\*\*")
_VERDICT_LINE_RE = re.compile(
    r"审查结论[：:]\s*\**\s*"
    r"(APPROVED_WITH_NOTES|APPROVED|NEEDS_CHANGE|BLOCKED)")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
# FEAT-094 ③: conflict-check exemptions — BLOCKED is the T2 round≥3
# escalation verdict (recording ABOVE the report's NEEDS_CHANGE is
# designed trigger semantics); ABORTED/UNKNOWN are supervisor facts about
# the agent. No optimistic uplift is possible through this set.
_CONFLICT_EXEMPT_RESULTS = frozenset(("BLOCKED", "ABORTED", "UNKNOWN"))
# FEAT-094: results that DISCHARGE an open recheck obligation for their
# own round (agent death deliberately does not discharge the owed recheck).
_OBLIGATION_DISCHARGING_RESULTS = frozenset(
    ("APPROVED", "APPROVED_WITH_NOTES", "NEEDS_CHANGE", "BLOCKED"))
# FEAT-094 grep anchors: the pinned-field line shapes emitted into the
# review record (accessibility budget — no implicit knowledge needed).
_REPORT_SHA_FIELD_RE = re.compile(
    r"^- report_sha256: ([0-9a-f]{64})\s*$", re.MULTILINE)
_COMMIT_FIELD_RE = re.compile(
    r"^- snapshot_commit: ([0-9a-f]{40}|git:unavailable)\s*$", re.MULTILINE)
_BIND_FIELD_RE = re.compile(
    r"^- snapshot_bind: (.+)=([0-9a-f]{40})\s*$", re.MULTILINE)
_REPORT_FIELD_RE = re.compile(
    r"^- report: (.+?)\s*$", re.MULTILINE)

# FIX-314: the reviewer name namespaces the record key (task, round,
# reviewer). The slug is deliberately ASCII-only (cross-platform filename
# safety); a name that normalizes to nothing fails closed at the caller.
_REVIEWER_SLUG_RE = re.compile(r"[^a-z0-9]+")

# FIX-314: the ``- reviewer:`` field line of an existing record — the owner
# probe that decides whether an incoming record matches the canonical slot
# or must be namespaced beside it.
_RECORD_REVIEWER_RE = re.compile(
    r"^[-*][ \t]*reviewer:[ \t]*(.+?)[ \t]*$", re.MULTILINE | re.IGNORECASE)


def _reviewer_slug(reviewer):
    """Normalize a reviewer name into a filename-safe slug (FIX-314).

    Lower-case ASCII alnum runs joined by single dashes, e.g.
    ``"Code Reviewer"`` → ``"code-reviewer"``. Returns ``""`` when nothing
    survives (the caller fails closed — a reviewer that cannot name a file
    must never silently collapse into another reviewer's slot).
    """
    return _REVIEWER_SLUG_RE.sub("-", str(reviewer or "").lower()).strip("-")


def _read_record_reviewer(review_file):
    """Return the ``- reviewer:`` owner of an existing record (FIX-314).

    ``None`` when the field is absent (pre-FIX-314 single-reviewer
    convention / handwritten record) — an unnamed owner is never treated as
    a match, so the incoming reviewer is namespaced beside the legacy file
    instead of claiming it. Read errors propagate: the caller fails closed
    rather than guessing the owner of an unreadable record.
    """
    text = review_file.read_text(encoding="utf-8")
    m = _RECORD_REVIEWER_RE.search(text)
    return m.group(1).strip() if m else None


def _detect_role(task_id, report_path):
    """Best-effort review-role detection from the task id / report filename.

    Returns an upper-case role token (e.g. ``CODE``) or None. Only used when
    the caller did not pass an explicit ``--unit``/``--gate``; the mapping is
    registry-side data, so an undetected role is NOT an error.
    """
    blob = " ".join([task_id or "", Path(report_path).name if report_path else ""])
    m = _ROLE_TOKEN_RE.search(blob.upper())
    return m.group(1) if m else None


# ── FEAT-094 trust-chain helpers ─────────────────────────────────────────────


def _resolve_report_face(report_path, root=None):
    """Locate + read the reviewer's report for trust pinning.

    Absolute paths and cwd-relative paths resolve as-is; a repo-relative
    spelling is additionally tried against ``root`` (the CLI's host-project
    face records paths like ``docs/reviews/...`` while running from the
    repo root). Returns ``(path, data_bytes, text)`` or ``None`` when the
    report cannot be read (fail-closed at the caller — no report, no
    binding, no record).
    """
    candidates = [Path(report_path)]
    if root is not None and not Path(report_path).is_absolute():
        candidates.append(Path(root) / report_path)
    for candidate in candidates:
        if candidate.is_file():
            try:
                data = candidate.read_bytes()
            except OSError:
                return None
            # Verdict-token scanning is ASCII-anchored — a tolerant decode
            # keeps a non-UTF-8 report scannable while the byte hash (the
            # actual pin) stays encoding-independent.
            return candidate, data, data.decode("utf-8", errors="replace")
    return None


def _report_verdict_tokens(text):
    """Distinct verdict tokens the report clearly carries (FEAT-094 ③)."""
    tokens = set(_VERDICT_BOLD_RE.findall(text or ""))
    tokens.update(_VERDICT_LINE_RE.findall(text or ""))
    return tokens


def _git_output(repo_root, *argv):
    """One argv-list git invocation → stripped stdout, or None (git
    unavailable / non-repo / failure — disclosed, never faked). Zero
    shell, zero network; same posture as governance_store's git_object
    reference check."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), *argv],
            capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", errors="replace").strip()


def snapshot_binding(repo_root, bind_files=()):
    """FEAT-094 ① — the immutable snapshot of the reviewed object.

    ``git rev-parse HEAD`` (the commit being reviewed) + a
    ``git status --porcelain`` worktree disclosure + one
    ``git hash-object`` blob pin per ``bind_files`` path (content hash
    that stays meaningful for UNTRACKED files — the REV-009 phantom
    revision anchored untracked bytes that were rewritten underneath the
    review). git unavailable / not a repo → disclosed markers
    (``git:unavailable`` / ``unavailable``), never a fabricated hash.
    """
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    commit = _git_output(root, "rev-parse", "HEAD")
    status = _git_output(root, "status", "--porcelain")
    worktree = "unavailable" if status is None else (
        "clean" if not status else "dirty({0})".format(
            len([ln for ln in status.splitlines() if ln.strip()])))
    bindings = []
    for raw in bind_files or ():
        spec = str(raw)
        blob = _git_output(root, "hash-object", "--", spec)
        bindings.append({
            "path": spec.replace("\\", "/"),
            "hash": blob if blob and _HEX40_RE.match(blob) else "unavailable",
        })
    return {
        "commit": commit if commit and _HEX40_RE.match(commit)
        else "git:unavailable",
        "commit_status": "resolved" if commit and _HEX40_RE.match(commit)
        else "unavailable",
        "worktree": worktree,
        "bindings": bindings,
    }


def _pin_check(checks, kind, pinned, current, note=""):
    """Append one standardized pin-check record (single literal site)."""
    state = "unverified" if current is None else (
        "match" if current == pinned else "mismatch")
    record = {"check": kind, "pinned": pinned, "state": state}
    if current is not None:
        record["current"] = current
    if note:
        record["detail"] = note
    checks.append(record)
    return state


def verify_review_trust(review_file, repo_root=None):
    """FEAT-094 — re-verify a record's trust pins (tamper detection face).

    Re-reads the pinned report bytes and re-hashes them against the
    record's ``- report_sha256:`` pin; resolves the pinned commit and any
    ``- snapshot_bind:`` blob pins against the repo. Returns a structured
    verdict dict — never raises:

    * ``CLEAN`` — every pin re-verified;
    * ``CONFLICT`` — a pin no longer matches (the report was rewritten
      after the record / the bound file drifted / the commit vanished);
      disposition is MANUAL (re-review or supersede — the record itself is
      immutable, provenance honest);
    * ``UNKNOWN`` — a pin exists but cannot be re-verified now (report
      unreadable / git unavailable);
    * ``UNPINNED`` — a legacy pre-FEAT-094 record (no pins by design;
      deliberately NOT a conflict — assumption_record compatibility).
    """
    face = {
        "review_file": str(review_file),
        "verdict": "UNKNOWN",
        "checks": [],
        "reason": "",
    }
    try:
        text = Path(review_file).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        face["reason"] = "record unreadable: {0}".format(exc)
        return face
    sha_match = _REPORT_SHA_FIELD_RE.search(text)
    if sha_match is None:
        face["verdict"] = "UNPINNED"
        face["reason"] = (
            "legacy record (pre-FEAT-094): no report_sha256 pin — "
            "not conflict-judged by design")
        return face
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    conflict = unknown = False

    # 1. report bytes vs the pinned hash
    current = None
    report_match = _REPORT_FIELD_RE.search(text)
    if report_match is not None:
        report_face = _resolve_report_face(report_match.group(1), repo_root)
        if report_face is not None:
            current = hashlib.sha256(report_face[1]).hexdigest()
    state = _pin_check(
        face["checks"], "report_sha256", sha_match.group(1), current,
        "report bytes changed AFTER the record was written "
        "(phantom-revision family) — MANUAL disposition: re-review the "
        "current object or supersede; never edit the record"
        if current is not None else
        "report unreadable — cannot re-hash")
    conflict |= state == "mismatch"
    unknown |= state == "unverified"

    # 2. pinned commit resolvability (git itself down → UNKNOWN; git up
    # but the commit gone → CONFLICT, the history-rewrite family)
    commit_match = _COMMIT_FIELD_RE.search(text)
    if commit_match is not None and commit_match.group(1) != "git:unavailable":
        resolved = _git_output(root, "rev-parse", "--verify", "--quiet",
                               commit_match.group(1) + "^{commit}")
        git_alive = _git_output(root, "rev-parse", "--verify", "--quiet",
                                "HEAD") is not None
        current = None
        if resolved is not None:
            current = resolved
        elif git_alive:
            current = ""
        state = _pin_check(
            face["checks"], "snapshot_commit", commit_match.group(1),
            current,
            "pinned commit no longer resolves — history rewritten? "
            "MANUAL disposition")
        conflict |= state == "mismatch"
        unknown |= state == "unverified"

    # 3. per-file blob pins (the untracked-safe bindings)
    for bind_match in _BIND_FIELD_RE.finditer(text):
        spec, pinned_blob = bind_match.group(1), bind_match.group(2)
        blob = _git_output(root, "hash-object", "--", spec)
        state = _pin_check(
            face["checks"], "snapshot_bind", pinned_blob, blob,
            "bound file content drifted after the review (REV-009 "
            "phantom-revision family) — MANUAL disposition: re-review")
        face["checks"][-1]["path"] = spec
        conflict |= state == "mismatch"
        unknown |= state == "unverified"

    if conflict:
        face["verdict"] = "CONFLICT"
        face["reason"] = (
            "trust pins no longer match — 禁乐观者胜出: the conflicting "
            "half must be re-adjudicated manually (FEAT-094 ③)")
    elif unknown:
        face["verdict"] = "UNKNOWN"
        face["reason"] = "pins present but not fully re-verifiable right now"
    else:
        face["verdict"] = "CLEAN"
        face["reason"] = "all trust pins re-verified"
    return face


def resolve_wiring(task_id, report_path=None, *, unit_id=None, gate_id=None):
    """Resolve the review→unit/gate wiring (data-driven, never raises).

    Explicit ``unit_id`` + ``gate_id`` win. Otherwise the role token (from
    task id / report filename) is looked up in :data:`REVIEW_GATE_MAPPING`.

    Returns a dict: ``{"resolved": bool, "unit_id": ..., "gate_id": ...,
    "role": ..., "reason": str}``. ``resolved=False`` → the caller skips the
    wiring with a WARN (the review record still lands).
    """
    if unit_id and gate_id:
        return {
            "resolved": True,
            "unit_id": unit_id,
            "gate_id": gate_id,
            "role": _detect_role(task_id, report_path),
            "reason": "explicit --unit/--gate",
        }
    role = _detect_role(task_id, report_path)
    if not role:
        return {
            "resolved": False,
            "unit_id": None,
            "gate_id": None,
            "role": None,
            "reason": (
                "no review→gate mapping resolved (role token not found in "
                "task id / report path; registry data missing — pass "
                "--unit/--gate to wire)"
            ),
        }
    gate_id = REVIEW_GATE_MAPPING.get(role)
    if not gate_id:
        return {
            "resolved": False,
            "unit_id": None,
            "gate_id": None,
            "role": role,
            "reason": (
                "no review→gate mapping for role {0!r} (registry data missing "
                "— pass --unit/--gate to wire)".format(role)
            ),
        }
    if not unit_id:
        return {
            "resolved": False,
            "unit_id": None,
            "gate_id": gate_id,
            "role": role,
            "reason": (
                "role {0!r} maps to gate {1} but no flow-unit id is available "
                "(pass --unit or register a unit mapping)".format(role, gate_id)
            ),
        }
    return {
        "resolved": True,
        "unit_id": unit_id,
        "gate_id": gate_id,
        "role": role,
        "reason": "registry role→gate mapping",
    }


def wiring_summary(outcome):
    """Normalize a :class:`GateOutcome` into the wiring summary dict shape.

    P2-1 (Code Review R1): ``wired`` reflects whether the CAS write actually
    committed (``outcome.success``), NOT merely that process_gate_result was
    invoked. A v1/classic no-op (status=illegal) or a missing-runtime error
    (status=error) is therefore NOT ``wired`` — the status/reason are still
    preserved for diagnosis.
    """
    return {
        "wired": bool(outcome.success),
        "degraded": False,
        "decision": outcome.decision,
        "status": outcome.status,
        "reason": outcome.reason,
        "loop_count": outcome.new_loop_count,
    }


def _wire_to_loop(task_id, round_n, result, review_file, reviewer, report_path,
                  unit_id, gate_id, root, runtime_file, plugin_home):
    """Wiring A (ADR-017 §3.4): thin process_gate_result invocation, best-effort.

    Thin delegation (ADR-014 §6 principle). Never raises; every failure mode
    (mapping missing / process_gate_result error / exception) is reported in
    the returned dict and must NOT block the review record.
    """
    evidence_ref = review_file.name if review_file is not None else (
        "review-{0}-R{1}.md".format(task_id, round_n))
    actor = reviewer or "review-record"
    mapping = resolve_wiring(task_id, report_path,
                             unit_id=unit_id, gate_id=gate_id)
    if not mapping["resolved"]:
        return {
            "wired": False,
            "degraded": False,
            "unit_id": mapping["unit_id"],
            "gate_id": mapping["gate_id"],
            "reason": mapping["reason"],
        }
    try:
        outcome = process_gate_result(
            mapping["unit_id"], mapping["gate_id"], result,
            evidence_ref=evidence_ref, actor=actor,
            root=root, runtime_file=runtime_file, plugin_home=plugin_home,
        )
        summary = wiring_summary(outcome)
        summary["unit_id"] = mapping["unit_id"]
        summary["gate_id"] = mapping["gate_id"]
        return summary
    except Exception as exc:  # noqa: BLE001 — best-effort degrade, never raise
        return {
            "wired": False,
            "degraded": True,
            "unit_id": mapping["unit_id"],
            "gate_id": mapping["gate_id"],
            "reason": "process_gate_result raised: {0}".format(exc),
        }


def _review_file_text(task_id, round_n, result, reviewer, report_path,
                      date_str, wiring_note, force_note=None,
                      scope="full", delta_base=None, trust_fields=None,
                      abort_reason=None):
    """Machine-written review record markdown (Check 30 file-scan parseable).

    ``force_note`` (FIX-289⑤) is the backup filename when this write is a
    deliberate force overwrite; it emits the ``- force_overwrite:`` marker
    line so the overwrite is traceable from the record itself. The marker is
    inert to the Check 30/30c file parsers (date/conclusion/next_round
    extraction are anchored to their own field lines). ``scope`` /
    ``delta_base`` (FEAT-091) record the review injection face the same
    way — additive field lines, inert to the anchored parsers.
    ``trust_fields`` (FEAT-094) are pre-rendered pin lines
    (``- report_sha256:`` / ``- snapshot_commit:`` / ``- snapshot_worktree:``
    / ``- snapshot_bind:``) and ``abort_reason`` rides the same additive
    field-line convention for supervisor terminal records.
    """
    lines = [
        "# Review Record (machine-written by review-record)",
        "",
        "- task: {0}".format(task_id),
        "- round: R{0}".format(round_n),
        "- date: {0}".format(date_str),
        "- reviewer: {0}".format(reviewer or "unknown"),
        "- report: {0}".format(report_path),
        "- wiring: {0}".format(wiring_note),
        "- scope: {0}".format(scope),
    ]
    if delta_base:
        lines.append("- delta_base: {0}".format(delta_base))
    if trust_fields:
        lines.extend(trust_fields)
    if abort_reason:
        lines.append("- abort_reason: {0}".format(abort_reason))
    if force_note:
        lines.append(
            "- force_overwrite: previous record preserved at {0}".format(
                force_note))
    lines += [
        "",
        "**审查结论**: **{0}**".format(result),
    ]
    if result == "APPROVED_WITH_NOTES":
        lines.append("")
        lines.append("unresolved_blockers=0")
    if result == "NEEDS_CHANGE":
        lines.append("")
        lines.append("## 复审必达（NEEDS_CHANGE）")
        lines.append("")
        lines.append("- next_round: REVIEW-{0}-R{1}".format(task_id, round_n + 1))
        lines.append("- prev_report: {0}".format(report_path))
    lines.append("")
    return "\n".join(lines)


def _evidence_row(task_id, round_n, result, reviewer, report_path,
                  review_file_name, date_str, review_id=None, pins=None):
    """Evidence-log row in the Check 30 live-scan contract.

    Column shape mirrors existing rows: | id | task_ref | type | description |
    basis | artifacts | actor | date | gate | conclusion [| blocker token].
    The description intentionally carries NO ISO date and NO conclusion token
    so the live collector's first-match scan lands on the real columns.
    ``review_id`` (FIX-314) is the caller-resolved record id — the canonical
    ``REVIEW-{task}-R{n}`` for the round's first reviewer, or the mirrored
    ``REVIEW-{task}-R{n}-{SLUG}`` for a namespaced second reviewer; either
    way the Check 30/30c row scans keep matching its canonical prefix.
    ``pins`` (FEAT-094) appends short grep-able trust pins to the artifacts
    cell (full hashes live in the review record; the row carries the
    12-char identification prefix).
    """
    cells = [
        review_id or "REVIEW-{0}-R{1}".format(task_id, round_n),
        task_id,
        "治理记录",
        "review-record CLI 机器写入 review 结论记录（round {0}）".format(round_n),
        "事实依据：review-record 输出摘要（机器写入）",
        "{0}; {1}".format(report_path, review_file_name),
        reviewer or "unknown",
        date_str,
        "G11",
        result,
    ]
    if pins:
        cells[5] = "{0}; {1}".format(cells[5], pins)
    if result == "APPROVED_WITH_NOTES":
        cells.append("unresolved_blockers=0")
    return "| " + " | ".join(cells) + " |\n"


def _review_ledger_transaction(evidence_dir, *, task_id, round_n,
                               result_norm, review_id, reviewer,
                               report_path, report_sha256, binding,
                               scope_norm):
    """FEAT-094 steps 3+4 — the ATOMIC ledger core of the review
    transaction: the ``review_recorded`` event and the recheck-obligation
    lifecycle events land in ONE ``transact`` batch (validation atomicity,
    single sequential append — a NEEDS_CHANGE record can never exist
    without its R{n+1} obligation, and an obligation can never be
    double-registered or phantom-cleared; the writer's batch contract
    enforces both).

    Returns ``(ledger_face, obligations_face)``; raises
    ``authority_ledger.LedgerError`` on refusal (caller converts to the
    structured error dict — the whole five-step transaction is refused,
    nothing written).
    """
    from authority_ledger import LedgerWriter, obligation_key
    writer = LedgerWriter(evidence_dir, actor="review_record")
    open_keys = {
        obligation_key(item) for item in
        writer.state.get("open_recheck_obligations", ())}
    this_key = "RECHECK-{0}-R{1}".format(task_id, round_n)
    next_key = "RECHECK-{0}-R{1}".format(task_id, round_n + 1)
    review_payload = {
        "review_id": review_id,
        "task_id": task_id,
        "round": round_n,
        "verdict": result_norm,
        "reviewer": reviewer or "unknown",
        "report_path": str(report_path),
        "report_sha256": report_sha256,
        "commit": binding["commit"],
        "worktree": binding["worktree"],
        "scope": scope_norm,
    }
    batch = [("review_recorded", review_payload)]
    obligations = []
    if result_norm in _OBLIGATION_DISCHARGING_RESULTS \
            and this_key in open_keys:
        batch.append(("recheck_obligation_cleared", {
            "obligation_id": this_key,
            "task_id": task_id,
            "round": round_n,
            "cleared_by": review_id,
            "verdict": result_norm,
        }))
        obligations.append({"id": this_key, "state": "cleared",
                            "by": review_id})
    if result_norm == "NEEDS_CHANGE":
        if next_key in open_keys:
            obligations.append({"id": next_key, "state": "already_open",
                                "by": review_id})
        else:
            batch.append(("recheck_obligation_registered", {
                "obligation_id": next_key,
                "task_id": task_id,
                "round": round_n + 1,
                "created_by": review_id,
                "prev_report": str(report_path),
                "prev_report_sha256": report_sha256,
                "commit": binding["commit"],
            }))
            obligations.append({"id": next_key, "state": "registered",
                                "by": review_id})
    outcome = writer.transact(batch)
    ledger_face = {
        "transaction_id": outcome.get("transaction_id"),
        "events": [kind for kind, _ in batch],
        "event_count": outcome.get("event_count"),
        "last_seq": outcome.get("last_seq"),
    }
    return ledger_face, obligations


def write_review_record(
    *,
    task_id,
    round_n,
    result,
    report_path,
    reviewer=None,
    unit_id=None,
    gate_id=None,
    root=None,
    evidence_dir=None,
    runtime_file=None,
    plugin_home=None,
    actor=None,
    force=False,
    scope="full",
    delta_base=None,
    bind_files=(),
    abort_reason=None,
):
    """Persist one review conclusion + Wire A (FIX-236.1) — as the FEAT-094
    five-step indivisible review transaction (提交报告→验证结构与修订→登记
    发现→自动生成后续义务→更新状态).

    Args:
        task_id: task id of the reviewed artifact (e.g. ``FIX-236``).
        round_n: review round (0-based; R0 is the first review).
        result: ``APPROVED`` | ``APPROVED_WITH_NOTES`` | ``NEEDS_CHANGE`` |
            ``BLOCKED`` | ``ABORTED`` | ``UNKNOWN`` (the last two are
            supervisor-recorded agent-death terminal states, FEAT-094 ⑤ —
            they never trigger a revisit and never discharge an open
            recheck obligation).
        report_path: path of the reviewer's full report (embedded in the
            record, hashed into the trust pin, and reused as prev_report
            for the R+1 revisit). MUST be readable — no report, no binding,
            no record (fail-closed).
        reviewer: reviewer/agent name (also the loop actor when given).
            FIX-314: part of the record key — the FIRST reviewer of a
            task+round keeps the canonical ``review-{task}-R{n}.md`` name, a
            DIFFERENT reviewer is namespaced to
            ``review-{task}-R{n}-{reviewer-slug}.md`` (mirrored evidence id
            ``REVIEW-{task}-R{n}-{SLUG}``). A name that does not normalize
            to an ASCII slug fails closed.
        unit_id / gate_id: explicit flow-unit wiring (overrides the registry
            mapping).
        root: host project root — review file + evidence row land under
            ``<root>/.governance`` (RISK-040: never PLUGIN_HOME); also the
            repo root for the FEAT-094 snapshot binding.
        evidence_dir: explicit governance dir override (tests); defaults to
            ``root/.governance``.
        runtime_file: explicit flow-unit-runtime.json path forwarded to the
            wiring (tests / hosts where the runtime is not under root).
        plugin_home: forwarded to registry reads in process_gate_result.
        actor: loop actor override (defaults to reviewer or "review-record").
        force: FIX-289⑤ overwrite opt-in (FIX-314: the guard key is the full
            task+round+reviewer triple). When the reviewer's own record
            already exists, the default (``force=False``) fails closed: an
            error dict is returned and nothing is written (no overwrite, no
            evidence row). ``force=True`` overwrites deliberately WITH an
            audit trail — the previous record is backed up to
            ``review-{id}-R{n}.pre-<ts>.md`` beside the record, the new record
            carries a ``- force_overwrite:`` marker naming the backup, and the
            summary reports ``force_overwrite`` + ``previous_record_backup``.
        scope / delta_base: FEAT-091 injection-scope record (unchanged).
        bind_files: FEAT-094 ① — repo paths to pin with ``git hash-object``
            blob hashes (untracked-safe immutable binding of the reviewed
            object's files).
        abort_reason: FEAT-094 ⑤ — supervisor's reason for an ABORTED /
            UNKNOWN terminal record (agent death); rides the record as an
            additive ``- abort_reason:`` field line.

    Returns:
        dict summary: review_id, review_file, evidence_row, wiring {...},
        revisit_required / next_round / prev_report (NEEDS_CHANGE only),
        trust {...} / ledger {...} / obligations [...] (FEAT-094 additive),
        and ``error`` (fail-closed) when inputs are invalid, the report is
        unreadable, the report clearly contradicts the claimed result
        (CONFLICT — manual disposition), or the authority ledger refused
        the transaction (integrity broken / obligation contract). Never
        raises.
    """
    # Input validation (fail-closed).
    if not _TASK_ID_RE.match(str(task_id or "")):
        return {"error": "task_id must match PREFIX-NNN (e.g. FIX-236)"}
    try:
        round_n = int(round_n)
    except (TypeError, ValueError):
        return {"error": "round_n must be an integer"}
    if round_n < 0:
        return {"error": "round_n must be >= 0"}
    result_norm = str(result or "").strip().upper()
    if not _RESULT_RE.match(result_norm):
        return {"error": (
            "result must be APPROVED | APPROVED_WITH_NOTES | NEEDS_CHANGE | "
            "BLOCKED | ABORTED | UNKNOWN (got {0!r})".format(result))}
    if not report_path:
        return {"error": "report_path is required"}
    if abort_reason is not None and result_norm not in ("ABORTED", "UNKNOWN"):
        return {"error": (
            "abort_reason requires result ABORTED|UNKNOWN (FEAT-094 ⑤ "
            "supervisor terminal states; got {0})".format(result_norm))}
    # FEAT-091: review injection-scope record (delta revisit). Default
    # "full" keeps every pre-FEAT-091 caller byte-compatible; "delta"
    # requires an anchor (prev-round report path or diff anchor).
    scope_norm = str(scope or "full").strip().lower()
    if scope_norm not in ("full", "delta"):
        return {"error": (
            "scope must be full | delta (FEAT-091; got {0!r})".format(scope))}
    if delta_base is not None and not str(delta_base).strip():
        return {"error": "delta_base must be a non-empty path/anchor"}
    if delta_base is not None and scope_norm != "delta":
        return {"error": (
            "delta_base requires scope=delta (FEAT-091; scope={0})".format(
                scope_norm))}

    # Resolve destinations.
    if evidence_dir is None:
        if root is None:
            return {"error": "root or evidence_dir is required"}
        evidence_dir = Path(root) / ".governance"
    evidence_dir = Path(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    # FIX-314 key-face resolution: the record key is (task, round, reviewer).
    # The canonical name stays the FIRST reviewer's slot — backward
    # compatible with every pre-FIX-314 record (a reviewer-less legacy file
    # is an unnamed owner that is never rewritten); a DIFFERENT reviewer for
    # the same task+round is namespaced beside it. The FIX-289⑤ guard below
    # then protects each reviewer's OWN file: three identical keys are still
    # refused without force, while the two halves of one review round
    # (REL-076 M-3) never overwrite each other.
    canonical_name = "review-{0}-R{1}.md".format(task_id, round_n)
    review_file = evidence_dir / canonical_name
    reviewer_slug = None
    if reviewer:
        reviewer_slug = _reviewer_slug(reviewer)
        if not reviewer_slug:
            return {"error": (
                "reviewer does not normalize to a filename-safe slug "
                "(ASCII alnum runs joined by dashes): {0!r}".format(reviewer))}
        if review_file.exists():
            try:
                owner = _read_record_reviewer(review_file)
            except (OSError, UnicodeDecodeError) as exc:
                # UnicodeDecodeError is a ValueError, NOT an OSError: a
                # non-UTF-8 record (the Windows GBK/ANSI mojibake family)
                # must fail closed to the same error dict — review-FIX-314-
                # CODE-R0 P1-1 — never escape as a raw traceback.
                return {"error": (
                    "cannot read existing review record to resolve the "
                    "(task, round, reviewer) key: {0}".format(exc))}
            if owner != str(reviewer).strip():
                review_file = evidence_dir / (
                    "review-{0}-R{1}-{2}.md".format(
                        task_id, round_n, reviewer_slug))
    review_id = "REVIEW-{0}-R{1}".format(task_id, round_n)
    if reviewer_slug is not None and review_file.name != canonical_name:
        review_id = "REVIEW-{0}-R{1}-{2}".format(
            task_id, round_n, reviewer_slug.upper())
    evidence_path = evidence_dir / "evidence-log.md"
    today = date.today().isoformat()

    # 0. FIX-289⑤ overwrite guard (READ-ONLY face; the backup itself is
    # deferred to the file-write phase so a refused transaction leaves no
    # stray artifacts): a task+round+reviewer review record is immutable by
    # default. Historical backfill / migrated records must never be silently
    # replaced (REL-073 same-number overwrite near-miss). force=True opts in
    # with an audit trail.
    file_preexisted = review_file.exists()
    if file_preexisted and not force:
        return {"error": (
            "review record already exists: {0} — refusing to overwrite "
            "(FIX-289⑤ task+round+reviewer record guard; historical "
            "backfill data is protected). To replace it deliberately, "
            "re-run with force=True: the previous record is backed up "
            "and the overwrite is marked in the new record.".format(
                review_file))}

    # ── FEAT-094 step 1 — 提交报告: read the report + pin its bytes ──
    report_face = _resolve_report_face(report_path, root)
    if report_face is None:
        return {"error": (
            "report not readable: {0} — FEAT-094 trust chain requires the "
            "reviewed report's bytes (sha256 pin); no report, no record "
            "(fail-closed)".format(report_path))}
    report_resolved, report_bytes, report_text = report_face
    report_sha256 = hashlib.sha256(report_bytes).hexdigest()

    # ── FEAT-094 step 2 — 验证结构与修订: conflict check + snapshot ──
    report_verdicts = _report_verdict_tokens(report_text)
    if (report_verdicts
            and result_norm not in _CONFLICT_EXEMPT_RESULTS
            and result_norm not in report_verdicts):
        return {
            "error": (
                "CONFLICT: report {0} clearly carries verdict token(s) "
                "{1} but the claimed result is {2} — refused (FEAT-094 ③ "
                "禁乐观者胜出: report/machine-record divergence is never "
                "auto-resolved). Disposition (manual): align the two (fix "
                "the report's conclusion or the --result claim) and re-run; "
                "a supervisor escalation may instead record BLOCKED / "
                "ABORTED / UNKNOWN without a matching token".format(
                    report_path, sorted(report_verdicts), result_norm)),
            "code": "conflict_report_vs_record",
            "conflict": {"report_verdicts": sorted(report_verdicts),
                         "claimed": result_norm},
        }
    repo_root = root if root is not None else evidence_dir.parent
    binding = snapshot_binding(repo_root, bind_files)

    # ── FEAT-094 steps 3+4 — the atomic ledger core (登记发现 event +
    # 自动生成后续义务, one transact batch; anti-evaporation ordering:
    # the ledger commits FIRST, files follow) ──
    try:
        ledger_face, obligations = _review_ledger_transaction(
            evidence_dir, task_id=task_id, round_n=round_n,
            result_norm=result_norm, review_id=review_id, reviewer=reviewer,
            report_path=report_path, report_sha256=report_sha256,
            binding=binding, scope_norm=scope_norm)
    except Exception as exc:  # LedgerError family — structured, never raise
        return {
            "error": (
                "authority ledger refused the review transaction — the "
                "five-step transaction is refused wholesale (nothing "
                "written; FEAT-094 fail-closed): {0}".format(exc)),
            "code": "ledger_refused",
            "ledger_detail": str(exc),
        }

    # ── FEAT-094 step 3 (file faces) + step 5 (状态) ──
    force_note = None
    if file_preexisted:
        try:
            previous_text = review_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            # P1-1 (review-FIX-314-CODE-R0): same half-face on the force
            # backup read — a non-UTF-8 record fails closed to the error
            # dict, not to a raw UnicodeDecodeError. The ledger transaction
            # already committed — disclosed via ledger_face.
            return {
                "error": (
                    "cannot read existing review record for backup: {0} "
                    "(ledger transaction {1} already committed — the "
                    "review events are durable, re-run with force after "
                    "repairing the record encoding)".format(
                        exc, ledger_face.get("transaction_id"))),
                "code": "backup_unreadable",
                "ledger": ledger_face,
            }
        backup_name = "{0}.pre-{1}.md".format(
            review_file.name[: -len(".md")],
            datetime.now().strftime("%Y%m%dT%H%M%S%f"))
        try:
            (evidence_dir / backup_name).write_text(
                previous_text, encoding="utf-8")
        except OSError as exc:
            return {
                "error": "cannot write overwrite backup: {0} (ledger "
                         "transaction {1} already committed)".format(
                             exc, ledger_face.get("transaction_id")),
                "code": "backup_unwritable",
                "ledger": ledger_face,
            }
        force_note = backup_name

    trust_fields = [
        "- report_sha256: {0}".format(report_sha256),
        "- snapshot_commit: {0}".format(binding["commit"]),
        "- snapshot_worktree: {0}".format(binding["worktree"]),
    ]
    for bound in binding["bindings"]:
        trust_fields.append("- snapshot_bind: {0}={1}".format(
            bound["path"], bound["hash"]))
    review_text = _review_file_text(
        task_id, round_n, result_norm, reviewer, report_path, today, "pending",
        force_note=force_note, scope=scope_norm, delta_base=delta_base,
        trust_fields=trust_fields,
        abort_reason=str(abort_reason) if abort_reason else None)
    try:
        review_file.write_text(review_text, encoding="utf-8")
    except OSError as exc:
        return {
            "error": "cannot write review file: {0} (ledger transaction "
                     "{1} already committed — the review events are "
                     "durable; re-running this command converges: the "
                     "obligation is already_open so no duplicate "
                     "registers)".format(
                         exc, ledger_face.get("transaction_id")),
            "code": "review_file_unwritable",
            "ledger": ledger_face,
        }

    pins = "report_sha256={0}; commit={1}".format(
        report_sha256[:12],
        binding["commit"][:12] if binding["commit_status"] == "resolved"
        else "none")
    registered = [ob for ob in obligations
                  if ob["state"] in ("registered", "already_open")]
    if registered:
        pins = "{0}; obligation={1}".format(
            pins, ",".join(ob["id"] for ob in registered))
    row = _evidence_row(
        task_id, round_n, result_norm, reviewer, report_path,
        review_file.name, today, review_id=review_id, pins=pins)
    try:
        with evidence_path.open("a", encoding="utf-8") as fh:
            fh.write("\n" + row)
    except OSError as exc:
        # Compensation (five-step atomicity, no half-commit window): a
        # review file THIS transaction created is removed again; a forced
        # overwrite keeps the new record + backup (the previous record is
        # preserved at the backup path — disclosed, never destroyed).
        if not file_preexisted:
            try:
                review_file.unlink()
            except OSError:
                pass
        return {
            "error": (
                "cannot append evidence row: {0} — review file "
                "{1}was removed again (transaction compensated); the "
                "ledger transaction {2} already committed (durable, "
                "disclosed — re-run to converge)".format(
                    exc,
                    "" if not file_preexisted else
                    "kept (force overwrite; previous record preserved at "
                    "{0}) ".format(force_note),
                    ledger_face.get("transaction_id"))),
            "code": "evidence_row_unwritable",
            "ledger": ledger_face,
        }

    # 2. Wiring A (best-effort; never blocks the record).
    wiring = _wire_to_loop(
        task_id, round_n, result_norm, review_file, reviewer or actor,
        report_path,
        unit_id, gate_id, root, runtime_file, plugin_home)

    # 3. loop_exit → next-unit bridge (best-effort consumer).
    if wiring.get("wired") and wiring.get("decision") == "exit" and root is not None:
        try:
            from loop_exit_bridge import refresh_candidates  # deferred (peer)
            refresh_candidates(Path(root))
        except Exception:  # noqa: BLE001 — bridge refresh must never block
            pass

    summary = {
        "review_id": review_id,
        "task_id": task_id,
        "round": round_n,
        "reviewer": reviewer,
        "result": result_norm,
        "review_file": str(review_file),
        "evidence_row_written": True,
        "wiring": wiring,
        "revisit_required": result_norm == "NEEDS_CHANGE",
        "scope": scope_norm,
        "trust": {
            "report_path": str(report_resolved),
            "report_sha256": report_sha256,
            "report_bytes": len(report_bytes),
            "commit": binding["commit"],
            "commit_status": binding["commit_status"],
            "worktree": binding["worktree"],
            "bindings": binding["bindings"],
        },
        "ledger": ledger_face,
        "obligations": obligations,
    }
    if delta_base is not None:
        summary["delta_base"] = str(delta_base)
    if result_norm == "NEEDS_CHANGE":
        summary["next_round"] = "REVIEW-{0}-R{1}".format(task_id, round_n + 1)
        summary["prev_report"] = str(report_path)
    if force_note is not None:
        summary["force_overwrite"] = True
        summary["previous_record_backup"] = str(evidence_dir / force_note)
    return summary


__all__ = [
    "REVIEW_GATE_MAPPING",
    "GATE_VERDICT_TO_RESULT",
    "resolve_wiring",
    "wiring_summary",
    "write_review_record",
    "snapshot_binding",
    "verify_review_trust",
    "process_gate_result",
]
