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

This module is product code (Governance Developer domain) and stays
import-cycle-free: it imports loop_gate_processor (peer) and loop_exit_bridge
(peer, pure) lazily inside the exit-refresh path.
"""

import re
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
_RESULT_RE = re.compile(
    r"^(APPROVED|APPROVED_WITH_NOTES|NEEDS_CHANGE|BLOCKED)$", re.IGNORECASE)

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
                      date_str, wiring_note, force_note=None):
    """Machine-written review record markdown (Check 30 file-scan parseable).

    ``force_note`` (FIX-289⑤) is the backup filename when this write is a
    deliberate force overwrite; it emits the ``- force_overwrite:`` marker
    line so the overwrite is traceable from the record itself. The marker is
    inert to the Check 30/30c file parsers (date/conclusion/next_round
    extraction are anchored to their own field lines).
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
    ]
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
                  review_file_name, date_str, review_id=None):
    """Evidence-log row in the Check 30 live-scan contract.

    Column shape mirrors existing rows: | id | task_ref | type | description |
    basis | artifacts | actor | date | gate | conclusion [| blocker token].
    The description intentionally carries NO ISO date and NO conclusion token
    so the live collector's first-match scan lands on the real columns.
    ``review_id`` (FIX-314) is the caller-resolved record id — the canonical
    ``REVIEW-{task}-R{n}`` for the round's first reviewer, or the mirrored
    ``REVIEW-{task}-R{n}-{SLUG}`` for a namespaced second reviewer; either
    way the Check 30/30c row scans keep matching its canonical prefix.
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
    if result == "APPROVED_WITH_NOTES":
        cells.append("unresolved_blockers=0")
    return "| " + " | ".join(cells) + " |\n"


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
):
    """Persist one review conclusion + Wire A (FIX-236.1).

    Args:
        task_id: task id of the reviewed artifact (e.g. ``FIX-236``).
        round_n: review round (0-based; R0 is the first review).
        result: ``APPROVED`` | ``APPROVED_WITH_NOTES`` | ``NEEDS_CHANGE`` |
            ``BLOCKED``.
        report_path: path of the reviewer's full report (embedded in the
            record and reused as prev_report for the R+1 revisit).
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
            ``<root>/.governance`` (RISK-040: never PLUGIN_HOME).
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

    Returns:
        dict summary: review_id, review_file, evidence_row, wiring {...},
        revisit_required / next_round / prev_report (NEEDS_CHANGE only), and
        ``error`` (fail-closed) when inputs are invalid or the task+round
        record already exists without ``force``. Never raises.
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
            "BLOCKED (got {0!r})".format(result))}
    if not report_path:
        return {"error": "report_path is required"}

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

    # 0. FIX-289⑤ overwrite guard: a task+round+reviewer review record is
    # immutable by default. Historical backfill / migrated records must never
    # be silently replaced (REL-073 same-number overwrite near-miss).
    # force=True opts in with an audit trail: the previous record is backed
    # up beside the record (microsecond timestamp — repeated forces never
    # collide) and the overwrite is marked in the new record + summary.
    force_note = None
    if review_file.exists():
        if not force:
            return {"error": (
                "review record already exists: {0} — refusing to overwrite "
                "(FIX-289⑤ task+round+reviewer record guard; historical "
                "backfill data is protected). To replace it deliberately, "
                "re-run with force=True: the previous record is backed up "
                "and the overwrite is marked in the new record.".format(
                    review_file))}
        try:
            previous_text = review_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            # P1-1 (review-FIX-314-CODE-R0): same half-face on the force
            # backup read — a non-UTF-8 record fails closed to the error
            # dict, not to a raw UnicodeDecodeError.
            return {"error": (
                "cannot read existing review record for backup: {0}".format(
                    exc))}
        backup_name = "{0}.pre-{1}.md".format(
            review_file.name[: -len(".md")],
            datetime.now().strftime("%Y%m%dT%H%M%S%f"))
        try:
            (evidence_dir / backup_name).write_text(
                previous_text, encoding="utf-8")
        except OSError as exc:
            return {"error": "cannot write overwrite backup: {0}".format(exc)}
        force_note = backup_name

    # 1. Machine-write the review record (independent of the loop wiring).
    review_text = _review_file_text(
        task_id, round_n, result_norm, reviewer, report_path, today, "pending",
        force_note=force_note)
    try:
        review_file.write_text(review_text, encoding="utf-8")
    except OSError as exc:
        return {"error": "cannot write review file: {0}".format(exc)}

    row = _evidence_row(
        task_id, round_n, result_norm, reviewer, report_path,
        review_file.name, today, review_id=review_id)
    try:
        with evidence_path.open("a", encoding="utf-8") as fh:
            fh.write("\n" + row)
    except OSError as exc:
        return {"error": "cannot append evidence row: {0}".format(exc)}

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
    }
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
    "process_gate_result",
]
