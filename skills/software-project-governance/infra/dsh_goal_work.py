"""Read the optional project-authorized work packages for one DSH goal."""

from __future__ import annotations

from pathlib import Path

from delivery_acceptance import _ID, _SHA256, _project_path, _read_record


WORK_PACKAGES = ".governance/dsh-goal-work.json"
_FIELDS = {"id", "action", "criteria", "method", "estimated_rounds", "instruction"}
_METHODS = ("exercise-entrypoint", "build-release", "inspect-evidence", "repair-criterion")
_MAX_PACKAGES = 16
_MAX_CRITERIA = 24
_MAX_ID = 128
_MAX_INSTRUCTION = 512
_MAX_RECORD_BYTES = 64 * 1024


def _valid_id(value):
    return isinstance(value, str) and len(value) <= _MAX_ID and _ID.fullmatch(value) is not None


def _validate_package(package, required_criteria):
    if not isinstance(package, dict) or package.keys() != _FIELDS:
        raise ValueError("work package has unexpected or missing fields")
    if (not _valid_id(package["id"]) or package["action"] not in ("verify", "repair")
            or package["method"] not in _METHODS):
        raise ValueError("invalid work package identity, action or method")
    criteria = package["criteria"]
    if (not isinstance(criteria, list) or not 0 < len(criteria) <= _MAX_CRITERIA
            or not all(_valid_id(key) and key in required_criteria for key in criteria)
            or len(set(criteria)) != len(criteria)):
        raise ValueError("work package criteria must be distinct IDs in the current delivery contract")
    estimate = package["estimated_rounds"]
    if type(estimate) is not int or not 0 < estimate < 2**53:
        raise ValueError("work package estimated_rounds must be a positive integer")
    instruction = package["instruction"]
    if (not isinstance(instruction, str) or not 0 < len(instruction) <= _MAX_INSTRUCTION
            or not instruction.isprintable() or instruction.strip() != instruction):
        raise ValueError("work package instruction must be bounded single-line text")


def read_work_packages(project_root: Path, intent_sha256: str, criteria) -> tuple[tuple[dict, ...], str | None]:
    """Return validated planning guidance and its byte fingerprint, without executing it."""
    try:
        path = _project_path(Path(project_root).resolve(), WORK_PACKAGES)
    except FileNotFoundError:
        return (), None
    try:
        record, digest = _read_record(path, {"intent_sha256", "work_packages"}, max_bytes=_MAX_RECORD_BYTES)
    except RecursionError as exc:
        raise ValueError("work package profile nesting is too deep") from exc
    stamped = record["intent_sha256"]
    if not isinstance(stamped, str) or not _SHA256.fullmatch(stamped) or stamped != intent_sha256:
        raise ValueError("work packages must match the original intent SHA-256")
    packages = record["work_packages"]
    if not isinstance(packages, list) or not 0 < len(packages) <= _MAX_PACKAGES:
        raise ValueError("work_packages must be a bounded nonempty list")
    required = set(criteria)
    seen = set()
    for package in packages:
        _validate_package(package, required)
        if package["id"] in seen:
            raise ValueError("work package IDs must be distinct")
        seen.add(package["id"])
    return tuple(packages), digest
