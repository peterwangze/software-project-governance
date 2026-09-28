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

Stdlib-only; no verify_workflow import (R2 reverse-dependency discipline).
"""

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
