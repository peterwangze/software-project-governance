"""Read-only reconciliation of one unit's retained materials at handoff."""

import json
from pathlib import Path

from delivery_acceptance import _hash_file, _project_path
from dsh_walk import CompositionScanOverflow, walk


class _Findings:
    def __init__(self):
        self.counts = dict.fromkeys(("missing", "changed", "unregistered", "unverifiable"), 0)
        self.examples = []
        self.seen = set()

    def add(self, kind, path, ref=None, *, count=1):
        key = (kind, Path(path))
        if key in self.seen:
            return
        self.seen.add(key)
        self.counts[kind] += count
        if len(self.examples) < 3:
            example = {"kind": kind}
            if len(json.dumps(path, ensure_ascii=True)) <= 384:
                example["path"] = path
            else:
                example["path_omitted"] = True
            if ref and len(ref.encode("utf-8")) <= 200:
                example["ref"] = ref
            self.examples.append(example)


def _managed_files(root, relative, findings):
    """Inspect only the named directory. A skipped or unreadable tree is disclosed."""
    try:
        directory = _project_path(root, relative)
    except FileNotFoundError:
        return set()
    except (OSError, ValueError):
        findings.add("unverifiable", relative)
        return set()

    report = {}
    try:
        files = walk(directory, patterns=("*",), report=report)
    except (CompositionScanOverflow, OSError):
        findings.add("unverifiable", relative)
        return set()
    skipped = report["skipped_errors"] + report["skipped_reparse_points"]
    if skipped:
        findings.add("unverifiable", relative, count=skipped)
    return set(files)


def _check_location(root, location, ref, findings, hashes):
    role = location["role"]
    # Candidate paths belong to product acceptance and may be mutable trees.
    if role in {"git_object", "governance_id", "url", "candidate"}:
        return
    target = location["target"]
    availability = location["availability"]
    if location.get("kind") == "git_range" and availability == "not_checked":
        return
    if availability != "present":
        findings.add("missing" if availability == "missing" else "unverifiable", target, ref)
        return
    digest = location.get("recorded_sha256")
    if not digest:
        if role == "report":
            findings.add("unverifiable", target, ref)
        return
    try:
        path = _project_path(root, target)
        if path not in hashes:
            hashes[path] = _hash_file(path)
        if hashes[path] != digest:
            findings.add("changed", target, ref)
    except FileNotFoundError:
        findings.add("missing", target, ref)
    except (OSError, ValueError):
        findings.add("unverifiable", target, ref)


def _registered_locations(root, state, unit, findings, *, include_task):
    from loop_materials import locations_for, records_for_unit

    try:
        for record in records_for_unit(root, state, unit, include_task=include_task):
            try:
                for location in locations_for(root, record):
                    yield record.ref, location
            except (OSError, ValueError):
                findings.add("unverifiable", record.source, record.ref)
    except (OSError, ValueError):
        findings.add("unverifiable", ".governance", unit["flow_unit_id"])


def check_materials(root, state, unit):
    """Check registered local originals and the unit/task's managed directories."""
    root = Path(root).resolve()
    findings = _Findings()
    unregistered = set()
    for owner in dict.fromkeys((unit["flow_unit_id"], unit["task_id"])):
        unregistered.update(_managed_files(root, f".governance/materials/{owner}", findings))

    hashes = {}
    for ref, location in _registered_locations(root, state, unit, findings, include_task=True):
        if location["availability"] != "not_checked":
            unregistered.discard(root / location["target"])
        _check_location(root, location, ref, findings, hashes)

    # A task may own several units. Shared originals registered by a sibling
    # are accounted for, without incorporating its conclusions into this check.
    for sibling in state["flow_units"]:
        if not unregistered:
            break
        if sibling["task_id"] != unit["task_id"] or sibling["flow_unit_id"] == unit["flow_unit_id"]:
            continue
        for _, location in _registered_locations(root, state, sibling, findings, include_task=False):
            if location["availability"] == "present":
                unregistered.discard(root / location["target"])

    for path in sorted(unregistered):
        findings.add("unregistered", path.relative_to(root).as_posix())
    invalid = any(findings.counts.values())
    return {"unit": unit["flow_unit_id"], "state": "invalid" if invalid else "ok",
            "counts": findings.counts, "examples": findings.examples,
            "next": ("Register unlinked originals, restore missing or changed evidence, or verify skipped paths. "
                     "Rerun this check after resolving the finding."
                     if invalid else "Stop. The checked materials are accounted for.")}
