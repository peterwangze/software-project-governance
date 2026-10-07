"""Governance exception registry — annotation-only acceptance (FEAT-075).

FEAT-075 (DEC-278 §3.1 单元二 item 4 / M-0 prerequisite 4 of 5): the
release/aggregation layers must be able to DISTINGUISH an original check
failure from an accepted exception, WITHOUT changing any underlying check
result (DEC-278(5): 原始 FAIL 与真实字节数保留，发布聚合层标注例外接受).

Design contract (fail-closed — the exception mechanism itself must never
become a silent exemption channel):

  * Registry file: ``.governance/exceptions.json`` (host project root).
    ABSENT file → the whole mechanism is INERT (every caller's output is
    byte-identical to the pre-FEAT-075 behavior — backward compatibility).
    The actual registrations (dates/approvals) are written by the
    Coordinator after M-0; this module ships the MECHANISM only.
  * Scope: one exception = (check_id, artifact) + the original severity it
    accepts (original_status) + validity window (approved_on/expires_on) +
    approval reference + growth-control byte budget (DEC-278(5): 增长超
    250,000B 提前重评——例外增长控制量非新阈值).
  * Effective ⇔ scope matches a finding AND severity matches AND
    today ≤ expires_on AND the artifact's current bytes ≤
    growth_control_bytes. Any miss (expired / over growth control /
    status mismatch / malformed registry entry) → the annotation does NOT
    apply; the finding keeps its original severity, bytes, and counts, and
    the not-effective exception is DISCLOSED (never silently dropped).
  * PURE annotation: every function here is read-only and returns NEW
    structures; callers' findings/summaries/exit codes are never mutated.

── Check 30c provenance exemption list (FEAT-089 / DEC-146 ② / DEC-321) ──

A SECOND, structurally different registry lives here: the DEC-registered
exemption list Check 30c consumes for its WARN→FAIL escalation batch.

  * Why in this module: both registries are governance-exception carriers
    (module responsibility: 治理例外登记载体). The FEAT-075 file registry
    stays annotation-only over artifact files; the 30c list is a CODE
    constant — the plugin (not the host project) owns it, because the
    exempted rows are plugin-history facts (evidence rows written before
    the machine-path contract existed) and the list ships with the
    escalation that consumes it (0.97.0). A host-side file would put the
    escalation's own exemption baseline under host write access — the
    thing DEC-146 ④'s unforgeable side record exists to prevent.
  * Matching is (rule, task_id, record_date, face)-exact. ``record_id``
    keeps the human-readable evidence ID cell verbatim (REVIEW-FIX-256-
    CODE-R0); it is an anchor for humans, NOT a match key — the V7 row
    scanner normalizes ID cells to ``task_id`` (ROLE segments never enter
    the key), so the key must be the normalized pair.
  * Unforgeability boundary (DEC-146 ④, honest scope): the side record
    (``infra/checks/review_exemptions_30c.json``) pins this list's
    canonical sha256 and the escalation-basis snapshot. Check 30c asserts
    side-record hash == live-registry hash on every run (a drifted or
    hand-edited list → EXEMPTION-SIDE-RECORD FAIL, fail-closed). This
    makes SILENT list drift impossible; it does not make the marker text
    itself unforgeable per row (write-time receipts are a separate,
    unshipped mechanism — registered, not claimed).

Stdlib-only; no verify_workflow import (R2 reverse-dependency discipline).
"""

import hashlib
import json
from datetime import date
from pathlib import Path

#: Schema marker of the registry file (versioned; bump on breaking change).
EXCEPTIONS_SCHEMA = "governance-exceptions/1"

#: Where the registry lives, relative to the governed project root.
EXCEPTIONS_RELPATH = ".governance/exceptions.json"

#: Severities an exception may be registered against (the original status
#: it accepts — preserved, never upgraded/downgraded by annotation).
ORIGINAL_STATUSES = ("WARN", "ERROR")

_REQUIRED_FIELDS = (
    "id", "check_id", "artifact", "original_status", "approval_ref",
    "approved_on", "expires_on", "growth_control_bytes",
)


def exceptions_path(root=None):
    """The registry path under ``root`` (default: this module's host root,
    resolved the same cwd-first way the governance tools resolve it)."""
    base = Path(root) if root is not None else Path.cwd()
    return base / EXCEPTIONS_RELPATH


def _parse_iso_date(value):
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _normalize_artifact(value):
    if not isinstance(value, str):
        return None
    normalized = value.strip().replace("\\", "/")
    return normalized or None


def _validate_entry(raw):
    """Validate one registry entry → (entry, error).

    ``entry`` is None on any violation (fail-closed: a malformed entry is
    INERT and its error is disclosed by the callers); ``error`` is a short
    human-readable reason.
    """
    if not isinstance(raw, dict):
        return None, "entry is not an object"
    missing = [f for f in _REQUIRED_FIELDS if f not in raw or raw[f] in (None, "")]
    if missing:
        return None, f"missing/empty field(s): {', '.join(missing)}"
    if not isinstance(raw["growth_control_bytes"], int) \
            or isinstance(raw["growth_control_bytes"], bool) \
            or raw["growth_control_bytes"] <= 0:
        return None, "growth_control_bytes must be a positive int"
    status = str(raw["original_status"]).strip().upper()
    if status not in ORIGINAL_STATUSES:
        return None, (f"original_status must be one of "
                      f"{'/'.join(ORIGINAL_STATUSES)}")
    approved = _parse_iso_date(raw["approved_on"])
    expires = _parse_iso_date(raw["expires_on"])
    if approved is None or expires is None:
        return None, "approved_on/expires_on must be ISO dates (YYYY-MM-DD)"
    if expires < approved:
        return None, "expires_on predates approved_on"
    artifact = _normalize_artifact(raw["artifact"])
    if artifact is None:
        return None, "artifact is empty"
    return {
        "id": str(raw["id"]).strip(),
        "check_id": str(raw["check_id"]).strip(),
        "artifact": artifact,
        "original_status": status,
        "approval_ref": str(raw["approval_ref"]).strip(),
        "approved_on": raw["approved_on"].strip(),
        "expires_on": raw["expires_on"].strip(),
        "growth_control_bytes": int(raw["growth_control_bytes"]),
        "owner": str(raw.get("owner", "")).strip(),
        "recheck_on": (raw.get("recheck_on") or "").strip(),
        "note": str(raw.get("note", "")),
    }, None


def load_exception_registry(root=None, today=None):
    """Load + validate the registry (read-only).

    Returns ``{"exists", "schema", "exceptions", "errors"}``.
    ``exists`` False → no registry file (the mechanism is inert by design —
    the Coordinator registers the real exceptions after M-0). A malformed
    FILE (bad JSON / wrong schema marker) or malformed ENTRIES contribute
    to ``errors`` and make those entries inert — fail-closed, disclosed.
    """
    path = exceptions_path(root)
    if not path.is_file():
        return {"exists": False, "schema": None, "exceptions": [],
                "errors": [], "path": str(path)}
    errors = []
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        return {"exists": True, "schema": None, "exceptions": [],
                "errors": [f"registry unreadable: {exc}"],
                "path": str(path)}
    # No read cache on purpose: renderers consult the registry per finding
    # (a tiny file), and any cache keyed on mtime/size can serve a stale
    # registry for same-size rewrites within one filesystem tick — the
    # annotation layer must always read the registry it annotates with.
    if not isinstance(doc, dict) or doc.get("schema") != EXCEPTIONS_SCHEMA:
        errors.append(
            f"registry schema marker must be {EXCEPTIONS_SCHEMA!r}")
        return {"exists": True,
                "schema": doc.get("schema") if isinstance(doc, dict) else None,
                "exceptions": [], "errors": errors, "path": str(path)}
    raw_entries = doc.get("exceptions")
    if not isinstance(raw_entries, list):
        errors.append("'exceptions' must be a list")
        raw_entries = []
    seen_ids = set()
    entries = []
    for idx, raw in enumerate(raw_entries):
        entry, error = _validate_entry(raw)
        if entry is None:
            errors.append(f"exceptions[{idx}]: {error}")
            continue
        if entry["id"] in seen_ids:
            errors.append(f"exceptions[{idx}]: duplicate id {entry['id']!r}")
            continue
        seen_ids.add(entry["id"])
        entries.append(entry)
    return {"exists": True, "schema": doc.get("schema"),
            "exceptions": entries, "errors": errors, "path": str(path)}


def _artifact_bytes(root, artifact, finding_bytes=None):
    """The artifact's CURRENT byte size — the finding's own bytes when the
    caller provides them (the measured fact), else a fresh stat."""
    if finding_bytes is not None:
        return int(finding_bytes)
    try:
        return (Path(root) / artifact).stat().st_size
    except OSError:
        return None


def evaluate_exception(entry, *, today, root=None, current_bytes=None,
                       severity=None):
    """Judge ONE registry entry against the live world (fail-closed).

    Returns ``{"state", "reason"}``; state is one of:
      effective          — scope/severity/date/growth all hold; the matched
                           finding may be annotated exception-accepted
                           (original result still stands untouched).
      expired            — today > expires_on → annotation not effective.
      over_growth_control— artifact bytes > growth_control_bytes → the
                           registered growth-control tripwire fired; not
                           effective (DEC-278(5): 提前重评).
      status_mismatch    — the finding's live severity differs from the
                           registered original_status → not effective.
      artifact_missing   — the artifact cannot be measured.
    """
    today = today or date.today()
    expires = _parse_iso_date(entry["expires_on"])
    if expires is None or today > expires:
        return {"state": "expired",
                "reason": f"validity ended {entry['expires_on']}"}
    if severity is not None and str(severity).strip().upper() != entry["original_status"]:
        return {"state": "status_mismatch",
                "reason": (f"registered for {entry['original_status']}, "
                           f"finding is {severity}")}
    size = _artifact_bytes(root if root is not None else Path.cwd(),
                           entry["artifact"], current_bytes)
    if size is None:
        return {"state": "artifact_missing",
                "reason": f"artifact {entry['artifact']} not measurable"}
    if size > entry["growth_control_bytes"]:
        return {"state": "over_growth_control",
                "reason": (f"artifact {size:,} B exceeds growth control "
                           f"{entry['growth_control_bytes']:,} B "
                           f"(DEC-278(5) 提前重评)")}
    return {"state": "effective", "reason": ""}


def annotate_findings(findings, *, root=None, today=None, check_key="check",
                      path_key="path", severity_key="severity",
                      bytes_key="bytes"):
    """Match a check-result's findings against the registry (PURE — the
    input list is never mutated; callers render the annotations themselves).

    Returns ``{"annotations", "not_effective", "registry"}``:
      annotations — [{finding_index, id, check, artifact, severity, bytes,
                      exception_id, approval_ref, expires_on, note}] for
                      every finding an EFFECTIVE exception matches (the
                      annotation layer; the underlying finding keeps its
                      original severity/bytes and the summary counts stay
                      untouched).
      not_effective — [{exception_id, check_id, artifact, state, reason}]
                      for matched-scope exceptions that did NOT take effect
                      (expired / over growth control / status mismatch) —
                      disclosed so the registry can never silently absorb
                      a failure it no longer covers.
    """
    registry = load_exception_registry(root)
    annotations = []
    not_effective = []
    if not registry["exceptions"]:
        return {"annotations": [], "not_effective": [], "registry": registry}
    today = today or date.today()
    for idx, finding in enumerate(findings or []):
        check_id = str(finding.get(check_key, "")).strip()
        artifact = _normalize_artifact(str(finding.get(path_key, "")))
        if not check_id or artifact is None:
            continue
        for entry in registry["exceptions"]:
            if entry["check_id"] != check_id or entry["artifact"] != artifact:
                continue
            verdict = evaluate_exception(
                entry, today=today, root=root,
                current_bytes=finding.get(bytes_key),
                severity=finding.get(severity_key))
            if verdict["state"] == "effective":
                annotations.append({
                    "finding_index": idx,
                    "id": finding.get("id") or artifact,
                    "check": check_id, "artifact": artifact,
                    "severity": finding.get(severity_key),
                    "bytes": finding.get(bytes_key),
                    "exception_id": entry["id"],
                    "approval_ref": entry["approval_ref"],
                    "expires_on": entry["expires_on"],
                    "note": entry["note"],
                })
            else:
                not_effective.append({
                    "exception_id": entry["id"], "check_id": check_id,
                    "artifact": artifact, "state": verdict["state"],
                    "reason": verdict["reason"],
                })
    return {"annotations": annotations, "not_effective": not_effective,
            "registry": registry}


def format_annotation(annotation):
    """The annotation text for one effective exception (标注「exception
    accepted（引用/到期）」— DEC-278(5))."""
    return (f"exception accepted ({annotation['exception_id']}, "
            f"ref={annotation['approval_ref']}, "
            f"expires={annotation['expires_on']})")


def exception_note(check_id, artifact, severity=None, root=None, today=None,
                   bytes_value=None):
    """A one-line annotation SUFFIX for renderers that print findings as
    single lines (empty string when nothing matches — the pre-FEAT-075
    output stays byte-identical). Exposed for verify_workflow's shared
    ArchGuard renderer and the Check 28s block."""
    findings = [{ "check": check_id, "path": artifact, "severity": severity,
                  "bytes": bytes_value }]
    matched = annotate_findings(findings, root=root, today=today)
    if matched["annotations"]:
        return " — " + format_annotation(matched["annotations"][0])
    return ""


def registry_error_note(root=None):
    """FEAT-075 R0 F-2: file-level registry errors (malformed entries /
    wrong schema marker / unreadable file) as a one-line disclosure; ""
    when the registry is clean or absent. Per-finding suffixes cannot carry
    this (an entry-level error is registry-scoped, not finding-scoped), so
    both aggregation render paths attach it once — fail-closed disclosure:
    a scope-matching but malformed exception NEVER annotates silently."""
    registry = load_exception_registry(root)
    if not registry["errors"]:
        return ""
    count = len(registry["errors"])
    return ("registry-error: " + str(count)
            + (" entry" if count == 1 else " entries")
            + " malformed/unreadable — annotations not effective "
              "(fail-closed); see release disclosure")


def release_disclosure_block(root=None, today=None):
    """The release-aggregate disclosure block (FEAT-075: check-release 区分
    原始失败与例外接受). Returns a ``details``-shaped dict for
    check_release_readiness, or None when no registry exists (backward
    compatibility: no registry → no block → output identical to before).

    Semantics: ``pass`` is ALWAYS True — an exception can annotate, never
    flip, a release verdict; ``issues`` carries one DISCLOSURE line per
    registered exception (effective or not) plus registry load errors.
    """
    registry = load_exception_registry(root)
    if not registry["exists"]:
        return None
    today = today or date.today()
    lines = []
    for error in registry["errors"]:
        lines.append(f"registry error (entries inert, fail-closed): {error}")
    for entry in registry["exceptions"]:
        verdict = evaluate_exception(entry, today=today, root=root)
        size = _artifact_bytes(root, entry["artifact"])
        if verdict["state"] == "effective":
            lines.append(
                f"{entry['id']} ({entry['check_id']}, {entry['artifact']}): "
                f"effective — matching failures stay FAIL and are annotated "
                f"exception accepted (ref={entry['approval_ref']}, "
                f"expires={entry['expires_on']}); "
                f"artifact now {size:,} B / growth control "
                f"{entry['growth_control_bytes']:,} B")
        else:
            lines.append(
                f"{entry['id']} ({entry['check_id']}, {entry['artifact']}): "
                f"NOT effective ({verdict['state']}: {verdict['reason']}) — "
                f"fail-closed, original failures stand unannotated")
    return {
        "pass": True,
        "issues": lines,
        "registry_path": registry["path"],
        "exception_count": len(registry["exceptions"]),
        "error_count": len(registry["errors"]),
        "boundary": (
            "annotation-only: exceptions distinguish original failures "
            "from accepted exceptions in the aggregate output; they never "
            "change an underlying check result, byte count, or exit code "
            "(DEC-278(5): 原始 FAIL 与真实字节数保留)"
        ),
    }


# ── Check 30c provenance exemption list (FEAT-089 / DEC-146 ② / DEC-321) ──
# The DEC-registered exemptions Check 30c consumes in its WARN→FAIL
# escalation batch (0.97.0). Two rows, both written ON the effective date
# (2026-08-22) itself — the day the rule went live — and both preemptively
# registered by DEC-321 (first cohort). Registration = list entry ONLY:
# the historical rows are never rewritten, backfilled, or "re-persisted"
# through review-record (DEC-321 方法勘正: a backfill would counterfeit the
# persistence timepoint and push coverage to 100% ahead of the gradual
# design — forbidden).
REVIEW_PROVENANCE_EXEMPTIONS = (
    {
        "id": "EXEMPT-30C-001",
        "check": "30c",
        "record_id": "REVIEW-FIX-256-CODE-R0",
        "task_id": "FIX-256",
        "record_date": "2026-08-22",
        "rule": "V7",
        "face": "row",
        "approved_by": "DEC-146(2) + DEC-321",
        "registered_in": "FEAT-089 (0.97.0)",
        "note": (
            "生效日当日残留手写行（规则上线首日的真实缺口证据，DEC-146 ③ "
            "诚实代价）；不回写不改写历史行、不走 review-record 补录"
            "（DEC-321 禁补录）"
        ),
    },
    {
        "id": "EXEMPT-30C-002",
        "check": "30c",
        "record_id": "REVIEW-FIX-258-CODE-R0",
        "task_id": "FIX-258",
        "record_date": "2026-08-22",
        "rule": "V7",
        "face": "row",
        "approved_by": "DEC-146(2) + DEC-321",
        "registered_in": "FEAT-089 (0.97.0)",
        "note": (
            "同上——2026-08-22 生效日当日第二行；首批入册（DEC-321 预登记）"
        ),
    },
)

#: Structural contract of one exemption entry (validated by
#: ``load_review_provenance_exemptions``; a malformed entry is INERT —
#: fail-closed, disclosed by Check 30c's side-record assertion).
_REVIEW_PROVENANCE_EXEMPTION_FIELDS = (
    "id", "check", "record_id", "task_id", "record_date", "rule", "face",
    "approved_by", "registered_in",
)


def load_review_provenance_exemptions(exemptions=None):
    """Validate the 30c exemption list (read-only, fail-closed per entry).

    Returns ``(entries, errors)``: malformed entries are dropped (an entry
    missing required fields or carrying an unparsable record_date can never
    match — it must not silently absorb a violation) and reported in
    ``errors``. ``exemptions`` overrides the module constant (tests, and
    Check 30c's tamper-probe path).
    """
    raw = exemptions if exemptions is not None else REVIEW_PROVENANCE_EXEMPTIONS
    entries, errors = [], []
    for idx, entry in enumerate(raw or ()):
        if not isinstance(entry, dict):
            errors.append(f"exemptions[{idx}]: not an object")
            continue
        missing = [f for f in _REVIEW_PROVENANCE_EXEMPTION_FIELDS
                   if not str(entry.get(f, "")).strip()]
        if missing:
            errors.append(
                f"exemptions[{idx}] ({entry.get('id', '?')}): "
                f"missing/empty field(s) {', '.join(missing)}")
            continue
        if entry.get("rule") not in ("V7", "V8"):
            errors.append(
                f"exemptions[{idx}] ({entry['id']}): rule must be V7/V8")
            continue
        if entry.get("face") not in ("row", "file", "any"):
            errors.append(
                f"exemptions[{idx}] ({entry['id']}): face must be "
                f"row/file/any")
            continue
        try:
            date.fromisoformat(str(entry["record_date"]).strip())
        except ValueError:
            errors.append(
                f"exemptions[{idx}] ({entry['id']}): record_date must be "
                f"ISO YYYY-MM-DD")
            continue
        entries.append(entry)
    return entries, errors


def review_provenance_exemptions_sha256(exemptions=None):
    """Canonical sha256 of the exemption list (the side record pins THIS).

    Canonical serialization: JSON, sort_keys, ensure_ascii=False, compact
    separators — byte-stable across runs/platforms for the same list.
    """
    raw = exemptions if exemptions is not None else REVIEW_PROVENANCE_EXEMPTIONS
    canonical = json.dumps(
        list(raw or ()), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def match_review_provenance_exemption(rule, task_id, record_date,
                                      face="row", exemptions=None):
    """Match ONE exemption entry for a Check 30c finding (exact keys).

    Args:
      rule: "V7" or "V8" (the finding's rule).
      task_id: the V7/V8 scanner's normalized task id (e.g. "FIX-256" —
        ROLE segments like the "-CODE-R0" tail never enter the key).
      record_date: ``datetime.date`` of the row/file (exact equality —
        an exemption registered for 2026-08-22 never absorbs 2026-08-23).
      face: "row" | "file" (the finding's channel).

    Returns the matching entry dict, or None. Malformed entries were
    already dropped by ``load_review_provenance_exemptions`` — an entry
    that cannot prove its scope never matches (fail-closed).
    """
    if record_date is None or not task_id:
        return None
    entries, _errors = load_review_provenance_exemptions(exemptions)
    for entry in entries:
        if entry["rule"] != rule:
            continue
        if entry["task_id"] != task_id:
            continue
        if str(entry["record_date"]).strip() != record_date.isoformat():
            continue
        if entry["face"] not in (face, "any"):
            continue
        return entry
    return None
