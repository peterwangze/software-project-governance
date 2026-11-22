"""Read-only product acceptance for the candidate release and goal preflights."""

from __future__ import annotations

import hashlib
import json
import ntpath
import os
import re
import stat
from pathlib import Path, PureWindowsPath


CONTRACT = ".governance/delivery-contract.json"
RECEIPT = ".governance/delivery-receipt.json"
CONTRACT_FIELDS = {"release_version", "goal_id", "artifact", "entrypoint", "producer", "verifier", "criteria"}
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
_WINDOWS_IS_RESERVED = getattr(ntpath, "isreserved", None)
_BOUNDARY = "project-authorized independent receipt and local artifact/evidence byte checks"


def _plain_stat(path: Path) -> os.stat_result:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & _REPARSE:
        raise ValueError(f"symlink or reparse point is not allowed: {path}")
    return info


def _project_path_parts(relative: str) -> list[str]:
    parts = relative.split("/")
    if (
        any(part in {"", ".", ".."} or part.endswith((".", " ")) for part in parts)
        or any(char in relative for char in '\\:\0<>"|?*')
        or (_WINDOWS_IS_RESERVED(relative) if _WINDOWS_IS_RESERVED else
            any(PureWindowsPath(part).is_reserved() for part in parts))
    ):
        raise ValueError(f"expected a project-relative POSIX path: {relative!r}")
    return parts


def _project_path(root: Path, relative: str) -> Path:
    cursor = root
    for part in _project_path_parts(relative):
        cursor /= part
        _plain_stat(cursor)
    return cursor


def _regular_stat(path: Path) -> os.stat_result:
    info = _plain_stat(path)
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"expected a regular file: {path}")
    return info


def _hash_file(path: Path, *, nonempty: bool = False) -> str:
    info = _regular_stat(path)
    if nonempty:
        if info.st_nlink != 1:
            raise ValueError(f"evidence file must not be hard-linked: {path}")
        if not info.st_size:
            raise ValueError(f"evidence file is empty: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_sha256(path: Path) -> str:
    """Hash a regular file or an entire directory without following links.

    A directory hashes ``delivery-tree-v1\n`` plus compact ASCII JSON
    ``[[relative POSIX path, kind, digest or null], ...]`` sorted by path.
    Directory entries preserve empty subdirectories. File data is streamed.
    Callers must keep the candidate immutable while checking and publishing.
    """
    path = Path(path)
    info = _plain_stat(path)
    if stat.S_ISREG(info.st_mode):
        return _hash_file(path)
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"artifact must be a regular file or directory: {path}")

    manifest = []
    pending = [path]
    while pending:
        for entry in pending.pop().iterdir():
            mode = _plain_stat(entry).st_mode
            relative = entry.relative_to(path).as_posix()
            if stat.S_ISDIR(mode):
                manifest.append((relative, "directory", None))
                pending.append(entry)
            else:
                manifest.append((relative, "file", _hash_file(entry)))
    if not manifest:
        raise ValueError(f"artifact directory is empty: {path}")
    canonical = json.dumps(sorted(manifest), ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(b"delivery-tree-v1\n" + canonical.encode("ascii")).hexdigest()


def _json_object(items: list[tuple]) -> dict:
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"duplicate JSON property: {key!r}")
        result[key] = value
    return result


def _read_record(path: Path, fields: set[str], *, max_bytes: int | None = None, optional=()) -> tuple[dict, str]:
    if _regular_stat(path).st_nlink != 1:
        raise ValueError(f"record must not be hard-linked: {path}")
    with path.open("rb") as stream:
        raw = stream.read() if max_bytes is None else stream.read(max_bytes + 1)
    if max_bytes is not None and len(raw) > max_bytes:
        raise ValueError("record is too large")
    record = json.loads(raw.decode("utf-8"), object_pairs_hook=_json_object)
    if not isinstance(record, dict) or record.keys() - set(optional) != fields | {"schema_version"}:
        raise ValueError("unexpected or missing fields")
    if type(record["schema_version"]) is not int or record["schema_version"] != 1:
        raise ValueError("schema_version must be 1")
    return record, hashlib.sha256(raw).hexdigest()


def _valid_text(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _validate_contract(record: dict) -> None:
    for field in ("release_version", "goal_id", "artifact", "entrypoint", "producer", "verifier"):
        if not _valid_text(record[field]):
            raise ValueError(f"{field} must be nonempty text")
    if not _ID.fullmatch(record["goal_id"]):
        raise ValueError("invalid goal_id")
    if record["producer"].casefold() == record["verifier"].casefold():
        raise ValueError("producer and verifier must be independent")
    if "authority" in record and not _valid_text(record["authority"]):
        raise ValueError("the product contract's designated revision authority must be named")
    criteria = record["criteria"]
    if not isinstance(criteria, dict) or not criteria or not all(
        _ID.fullmatch(key) and _valid_text(label) for key, label in criteria.items()
    ):
        raise ValueError("criteria must be a nonempty mapping of IDs to labels")


def _contract(path: Path, *, max_bytes: int | None = None) -> tuple[dict, str]:
    record, digest = _read_record(path, CONTRACT_FIELDS, max_bytes=max_bytes, optional=("authority",))
    _validate_contract(record)
    return record, digest


def _contract_facts(contract: dict, digest: str) -> dict:
    return {"contract_sha256": digest, "required_criteria": sorted(contract["criteria"])}


def contract_for_goal(project_root: Path, goal_id: str) -> dict:
    """Read and bind the current contract without examining receipts or artifacts."""
    root = Path(project_root).resolve()
    try:
        contract, digest = _contract(_project_path(root, CONTRACT))
    except RecursionError as exc:
        raise ValueError("delivery contract nesting is too deep") from exc
    if contract["goal_id"] != goal_id:
        raise ValueError(f"goal_id must match the delivery contract ({contract['goal_id']!r})")
    return _contract_facts(contract, digest)


def _result(
    state: str, issues: list[str] | None = None, *, skip_reason: str | None = None, **facts
) -> dict:
    output = {
        "state": state,
        "pass": state == "PASS",
        "issues": issues or [],
        "boundary": _BOUNDARY,
        **facts,
    }
    if skip_reason is not None:
        output.update(skipped=True, skip_reason=skip_reason)
    return output


def _criterion_result(root: Path, criterion: dict, artifact: Path) -> dict:
    if not isinstance(criterion, dict) or criterion.keys() - {
        "status", "evidence", "evidence_sha256", "detail",
    }:
        raise ValueError("unexpected result fields")
    status = criterion.get("status")
    if status not in ("PASS", "FAIL", "NOT_RUN", "BLOCKED"):
        raise ValueError("status must be PASS, FAIL, NOT_RUN or BLOCKED")
    if "detail" in criterion and not _valid_text(criterion["detail"]):
        raise ValueError("detail must be nonempty text when supplied")

    if status in ("PASS", "FAIL") or {"evidence", "evidence_sha256"} & criterion.keys():
        evidence = criterion.get("evidence")
        expected = criterion.get("evidence_sha256")
        if not _valid_text(evidence) or not isinstance(expected, str) or not _SHA256.fullmatch(expected):
            raise ValueError("result requires an evidence path and a lowercase evidence_sha256")
        path = _project_path(root, evidence)
        if path in (root / CONTRACT, root / RECEIPT, artifact) or artifact in path.parents:
            raise ValueError("evidence must be separate from the contract, receipt and artifact")
        if _hash_file(path, nonempty=True) != expected:
            raise ValueError("evidence SHA-256 mismatch")
    return criterion


def evaluate_delivery_acceptance(
    project_root: Path, *, release_version: str | None = None, goal_id: str | None = None,
    required: bool = False, released_history: bool = False, acceptance_context=None, _prerequisites=True,
) -> dict:
    """Check an explicitly selected release or goal against the same receipt."""
    if released_history and not required:
        return _result("NOT_APPLICABLE", skip_reason="released-history lineage audit")

    root = Path(project_root).resolve()
    try:
        contract_path = _project_path(root, CONTRACT)
    except FileNotFoundError:
        if required or goal_id is not None:
            return _result("FAIL", [f"missing {CONTRACT}"])
        return _result("NOT_CONFIGURED", skip_reason=f"no project delivery contract ({CONTRACT})")
    except (OSError, ValueError) as exc:
        return _result("FAIL", [f"delivery contract: {exc}"])

    try:
        contract, contract_hash = _contract(contract_path)
        field, requested = ("goal_id", goal_id) if goal_id is not None else (
            "release_version", release_version,
        )
        if not _valid_text(requested) or contract[field] != requested:
            raise ValueError(f"{field} must match the delivery contract ({contract[field]!r})")
    except (OSError, ValueError, RecursionError) as exc:
        return _result("FAIL", [f"delivery contract: {exc}"])

    if acceptance_context and (acceptance_context.get("product_goal") != contract["goal_id"]
            or acceptance_context.get("product_contract_sha256") != contract_hash):
        return _result("FAIL", ["delivery scope: product goal or contract digest does not match the frozen root"])
    from loop_alignment import product_context
    try:
        acceptance_context = product_context(root, contract["goal_id"], contract_hash, contract["artifact"],
                                             release=release_version is not None, prerequisites=_prerequisites) or acceptance_context
    except (OSError, ValueError, RecursionError) as exc:
        return _result("FAIL", [f"delivery scope: {exc}"], **_contract_facts(contract, contract_hash))
    if acceptance_context and acceptance_context.get("contract_revisions"):
        from loop_alignment import current_criteria, evidence_issue
        if issue := evidence_issue(root, acceptance_context):
            return _result("FAIL", [issue])
        contract = dict(contract, criteria=current_criteria(acceptance_context))
    contract_facts = _contract_facts(contract, contract_hash)
    try:
        receipt, receipt_hash = _read_record(_project_path(root, RECEIPT), {
            "contract_sha256", "artifact_sha256", "entrypoint", "verifier", "results",
        }, optional=("revisions",))
        revisions = (acceptance_context or {}).get("contract_revisions", [])
        expected_revisions = [event["sha256"] for event in revisions]
        if receipt.get("revisions", []) != expected_revisions:
            raise ValueError("receipt must acknowledge the applicable root revisions and retest their affected criteria")
        for field, expected in (
            ("contract_sha256", contract_hash), ("entrypoint", contract["entrypoint"]),
            ("verifier", contract["verifier"]),
        ):
            if receipt[field] != expected:
                raise ValueError(f"{field} does not match the delivery contract")
        results = receipt["results"]
        if not isinstance(results, dict):
            raise ValueError("results must be a mapping of criterion IDs")

        artifact = _project_path(root, contract["artifact"])
        if artifact in (contract_path, root / RECEIPT) or artifact in contract_path.parents:
            raise ValueError("artifact must be separate from the contract and receipt")
        fingerprint = artifact_sha256(artifact)
        if fingerprint != receipt["artifact_sha256"]:
            raise ValueError("artifact SHA-256 mismatch")
    except (OSError, ValueError, RecursionError) as exc:
        return _result("FAIL", [f"delivery receipt: {exc}"], **contract_facts)

    verified = {}
    issues = [f"unexpected criterion {key!r}" for key in sorted(results.keys() - contract["criteria"].keys())]
    for key in sorted(contract["criteria"]):
        if key not in results:
            issues.append(f"{key}: missing result")
            continue
        try:
            criterion = _criterion_result(root, results[key], artifact)
            if criterion.get("status") == "PASS" and any(
                criterion["evidence_sha256"] in change.get("prior_evidence", {}).get(key, ())
                for change in revisions if key in change["criteria"]
            ):
                raise ValueError("revision requires fresh observation from the original sample")
        except (OSError, ValueError) as exc:
            issues.append(f"{key}: {exc}")
            continue
        verified[key] = criterion
        status = criterion["status"]
        if status != "PASS":
            detail = criterion.get("detail")
            issues.append(f"{key}: {status}" + (f" — {detail}" if detail else ""))

    terminal = {}
    if results.keys() == verified.keys() == contract["criteria"].keys() and all(
        item["status"] in {"PASS", "FAIL"} for item in verified.values()
    ):
        terminal = {"receipt_sha256": receipt_hash, "receipt_verdict": "FAIL" if issues else "PASS"}
    return _result(
        "FAIL" if issues else "PASS", issues, **contract_facts, **terminal,
        artifact=contract["artifact"], artifact_sha256=fingerprint, entrypoint=contract["entrypoint"], criteria_results=verified,
    )
