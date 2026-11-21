"""Evidence-backed route decisions and improvement proposals belonging to a work unit."""
from pathlib import Path
import re

from delivery_acceptance import _hash_file, _project_path, _project_path_parts


_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,159}")


def entry_issue(entry, unit_id):
    """Check the stored shape without opening evidence or changing an old unit."""
    if not isinstance(entry, dict) or entry.get("unit") != unit_id:
        return "learning record must belong to its work unit"
    if not isinstance(entry.get("id"), str) or not _ID.fullmatch(entry["id"]):
        return "invalid learning id"
    if entry.get("kind") not in ("decision", "opportunity"):
        return "learning kind must be decision or opportunity"
    for field in ("observation", "action", "validation", "evidence"):
        if not isinstance(entry.get(field), str) or not entry[field].strip():
            return f"learning {field} requires nonempty text"
    if not isinstance(entry.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
        return "invalid learning evidence SHA-256"
    if (not isinstance(entry.get("gate"), str) or not re.fullmatch(r"G(?:[1-9]|10|11)", entry["gate"])
            or any(type(entry.get(k)) is not int or entry[k] < 0 for k in ("iteration", "attempt"))):
        return "learning requires its original gate, iteration and attempt"
    try:
        _project_path_parts(entry["evidence"])
    except ValueError as exc:
        return str(exc)
    return None


def _fingerprint(root, evidence):
    if not isinstance(evidence, str) or not evidence.strip():
        raise ValueError("learning requires an evidence file")
    root = Path(root).resolve()
    path = _project_path(root, evidence)
    if path == root / ".governance" / "flow-unit-runtime.json":
        raise ValueError("learning evidence must be separate from the work-unit runtime")
    return _hash_file(path, nonempty=True)


def learning_evidence_issue(root, entry):
    """Recheck the source bytes independently of the work unit's gate result."""
    try:
        actual = _fingerprint(root, entry["evidence"])
    except (KeyError, OSError, TypeError, ValueError) as exc:
        return f"learning evidence unavailable: {exc}"
    if actual != entry.get("sha256"):
        return f"learning evidence SHA-256 mismatch: {entry['evidence']}"
    return None


def record(root, unit_id, learning_id, kind, observation, action, validation, evidence):
    """Append once under the same locks as normal unit intake and gate updates."""
    import loop_event_log
    import loop_paro_engine
    from loop_workflow import _payload, _unit, runtime_path

    path = runtime_path(root)
    _project_path(Path(root).resolve(), path.relative_to(root).as_posix())
    digest = _fingerprint(root, evidence)
    with loop_event_log._cross_process_lock(path), loop_paro_engine._commit_lock(path):
        state = _payload(path)
        unit = _unit(state, unit_id)
        content = dict(unit=unit_id, id=learning_id, kind=kind, observation=observation, action=action,
                       validation=validation, evidence=evidence, sha256=digest)
        entries = unit.setdefault("learning", [])
        for prior in entries:
            if prior["id"] == learning_id:
                if all(prior[k] == v for k, v in content.items()):
                    return prior
                raise ValueError(f"learning {learning_id} already exists with different content or evidence")
        entry = dict(content, gate=unit["gate_state"]["gate_id"], iteration=unit["loop_state"]["loop_count"],
                     attempt=len(unit.get("gate_history", [])))
        if issue := entry_issue(entry, unit_id):
            raise ValueError(issue)
        entries.append(entry)
        loop_paro_engine._atomic_replace_bytes(path, loop_paro_engine._serialize(state))
        return entry


def opportunity(root, previous, learning_id):
    """Resolve a candidate from its validated source unit and recheck its evidence."""
    for entry in previous.get("learning", []):
        if entry["id"] == learning_id and entry["kind"] == "opportunity":
            issue = entry_issue(entry, previous["flow_unit_id"]) or learning_evidence_issue(root, entry)
            if issue:
                raise ValueError(issue)
            return entry
    raise ValueError(f"{previous['flow_unit_id']}: unknown opportunity {learning_id}")
