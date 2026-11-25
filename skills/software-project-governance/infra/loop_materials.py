"""Bounded, read-only material discovery using work-unit bindings and evidence registers."""
from dataclasses import dataclass, field
from heapq import nsmallest
from itertools import chain, islice
import json
from pathlib import Path
import re

from archive_indexing import evidence_archive_files, iter_evidence_family_rows
from authority_ledger import _read_events_raw, ledger_paths
from checks.loop_receipts import review_id_from_ref
from delivery_acceptance import _project_path, _project_path_parts
from governance_archive_data import expand_task_ids
from governance_readers import governance_table_cells
from loop_alignment import acceptance_successors
from loop_revalidation import coverage, owner_for
from loop_workflow import REVIEW_ID, UNIT_ID, _payload, _unit


RUNTIME = ".governance/flow-unit-runtime.json"
EVD = re.compile(r"EVD-(?:[A-Z]+-)?\d+\Z")
TYPED_REF = re.compile(r"refs\[(repo_file|git_object|governance_id|url|human_observation):(.+?)=(?:resolvable|not_yet_verifiable)\]")
MAX_ITEMS = 3
MAX_BYTES = 4096
GIT_RANGE = re.compile(r"[\w/-]+(?:[~^]\d*)*\.{2,3}[\w/-]+(?:[~^]\d*)*\Z")


def _summary(value):
    # Only the descriptive part of a ledger cell belongs in model context.
    return re.split(r"结构化事实\s*[:：]|事实依据\s*[:：]|```|[\[{]\s*[\"{]", value, maxsplit=1)[0].strip()


@dataclass
class Material:
    ref: str
    scope: str
    status: str
    purpose: str
    source: str = RUNTIME
    keywords: str = ""
    pointers: list = field(default_factory=list)
    artifacts: str = ""
    review_binding: dict = field(default_factory=dict)
    supersedes: str = ""
    default_candidate: bool = False
    review_id: str = ""
    unbound_receipt: bool = False

    def brief(self):
        summary = " ".join(self.purpose.split())
        return {"ref": self.ref, "scope": self.scope, "status": self.status,
                "summary": summary if len(summary) <= 110 else summary[:109] + "…"}


def _unit_records(unit, owner, historical, *, current_only=False):
    gate = unit["gate_state"]
    history = unit.get("gate_history", [])
    attempts = range(len(history))
    for attempt in reversed(attempts[-1:] if current_only else attempts):
        event = history[attempt]
        active = (not historical and attempt == len(history) - 1 and event["gate"] == gate["gate_id"]
                  and gate["status"] != "pending")
        receipt = event.get("evidence_ref")
        if not receipt or (current_only and not active):
            continue
        review = review_id_from_ref(receipt)
        binding = {"unit": unit["flow_unit_id"], "task": unit["task_id"], "gate": event["gate"],
                   "iteration": str(event["iteration"]), "attempt": str(attempt)} if review else {}
        pinned = re.fullmatch(r"loop-evidence/([a-f0-9]{64})\.json", receipt)
        yield Material(f"gate:{event['cas_version']}", "unit", "latest_gate_record" if active else "historical",
                       f"{event['gate']} {event['result']} · {event['actor']}",
                       keywords="gate 门禁 " + (f"{review} review 评审 审查" if review else "verification 验收"),
                       pointers=[("receipt", ".governance/" + receipt, pinned[1] if pinned else "")],
                       review_binding=binding, default_candidate=active, review_id=review or "")
    retired = set()
    for entry in reversed(unit.get("learning", [])):
        superseded = entry["id"] in retired
        if prior := entry.get("supersedes"):
            retired.add(prior)
        active = (not historical and entry["gate"] == gate["gate_id"] and entry["attempt"] == len(history)
                  and entry["iteration"] == unit["loop_state"]["loop_count"])
        candidate = active and entry["kind"] == "decision" and not superseded
        if current_only and not candidate:
            continue
        status = "this_attempt" if active else "historical"
        pointers = [("evidence", entry["evidence"], entry["sha256"])]
        if entry.get("candidate"):
            pointers.append(("candidate", entry["candidate"], entry["candidate_sha256"]))
        labels = {"decision": "decision 决策 取舍", "opportunity": "opportunity 机会", "note": "note 观察 笔记"}
        yield Material("learn:" + entry["id"], "unit", "superseded" if superseded else status,
                       _summary(entry["observation"]), keywords=" ".join([labels[entry["kind"]], entry["gate"],
                           *entry.get("criteria", []), _summary(entry["action"]), _summary(entry["validation"])]),
                       pointers=pointers, supersedes=entry.get("supersedes", ""),
                       default_candidate=candidate)
    affected = set(coverage(unit, owner))
    replaced = set()
    for entry in reversed(owner.get("contract_revisions", [])):
        shared = affected.intersection(entry["criteria"])
        if not shared:
            continue
        active = shared - replaced
        status = "historical" if historical or not active else entry["kind"]
        if active and active != shared and not historical:
            status = "partly_superseded"
        pointers = [("evidence", entry["evidence"], entry["sha256"])]
        if entry.get("response"):
            pointers.append(("response", entry["response"]["source"], entry["response"].get("sha256", "")))
        yield Material("revision:" + entry["id"], "root_contract", status, _summary(entry["reason"]),
                       keywords=" ".join(["revision 修订", "authorization 授权" if entry["kind"] == "authorization"
                                          else "counterevidence 反证", *sorted(shared), *(entry["criteria"][k] for k in sorted(shared))]),
                       pointers=pointers, default_candidate=bool(active) and not historical)
        if entry["kind"] == "authorization":
            replaced.update(shared)


def _evidence_records(root, task, ref):
    gov = root / ".governance"
    try:
        directory = _project_path(root, ".governance/archive/evidence")
        archives = evidence_archive_files(directory)
    except FileNotFoundError:
        archives = []
    # Only the canonical ledger and its direct evidence volumes are read.
    for path in [gov / "evidence-log.md", *archives]:
        try:
            _project_path(root, path.relative_to(root).as_posix())
        except FileNotFoundError:
            continue
    for row in iter_evidence_family_rows(gov / "evidence-log.md", archives, "| EVD-"):
        if ref and row["row_id"] != ref:
            continue
        if not EVD.fullmatch(row["row_id"]) or (task != row["task_ids"] and task not in expand_task_ids(row["task_ids"])):
            continue
        cells = governance_table_cells(row["line"])
        if len(cells) != 10:
            continue
        source = row["file"] if row["source"] == "hot" else ".governance/" + row["file"]
        purpose = " · ".join(filter(None, (_summary(cells[9]), _summary(cells[3]))))
        yield Material(row["row_id"], "task", "recorded", purpose, source,
                       keywords=f"{cells[2]} {cells[8]}", artifacts=cells[5])


def _authority_reviews(root, unit):
    _, events_path, _ = ledger_paths(root / ".governance")
    source = events_path.relative_to(root).as_posix()
    try:
        _project_path(root, source)
    except FileNotFoundError:
        return
    events, integrity = _read_events_raw(events_path)
    if not integrity["ok"]:
        raise ValueError("review ledger integrity failure")
    for event in events:
        if event["kind"] != "review_recorded":
            continue
        row = event["payload"]
        binding = row.get("observed_loop") or row.get("loop_binding") or {}
        if binding.get("unit") == unit["flow_unit_id"] and row.get("task_id") == unit["task_id"]:
            yield row


def _bound_reviews(native, reviews):
    by_id = {}
    for row in reviews:
        by_id.setdefault(row["review_id"], []).append(row)
    for material in native:
        if material.review_id:
            expected = material.review_binding
            matches = [r for r in by_id.get(material.review_id, [])
                       if all(str(r.get("loop_binding", {}).get(k)) == expected[k]
                              for k in ("unit", "gate", "iteration", "attempt"))]
            if len(matches) == 1:
                row = matches[0]
                expected.update(report=row["report_path"], report_sha256=row["report_sha256"])
                material.pointers.append(("report", row["report_path"], row["report_sha256"]))
                material.keywords += " " + row["report_path"]
            else:
                material.unbound_receipt = True
        yield material
    for row in reviews:
        observed = row.get("observed_loop")
        if not observed:
            continue
        review_id = row["review_id"]
        match = REVIEW_ID.fullmatch(review_id)
        if not match or match[1] != row["task_id"]:
            continue
        name = f".governance/review-{match[1]}-R{match[2]}" + (f"-{match[3].lower()}" if match[3] else "") + ".md"
        binding = {"task": row["task_id"], "observed_loop": json.dumps(observed, sort_keys=True, separators=(",", ":")),
                   "report": row["report_path"], "report_sha256": row["report_sha256"]}
        yield Material(review_id, "unit", "observation", f"{row['verdict']} · {row['reviewer']}", ".governance/authority-ledger/events.jsonl",
                       keywords=f"review 评审 审查 R{row['round']}" + (" re-review 复审" if row["round"] or row.get("scope") == "delta" else ""),
                       pointers=[("receipt", name, ""), ("report", row["report_path"], row["report_sha256"])],
                       review_binding=binding)


def _artifact_refs(artifacts):
    first = TYPED_REF.search(artifacts)
    plain = artifacts
    if first and (first.start() == 0 or artifacts[first.start()-1] == "；"):
        plain = artifacts[:first.start()]
        for kind, value in TYPED_REF.findall(artifacts[first.start():]):
            if kind != "human_observation":
                yield kind, value, ""
    for part in re.split(r"[;；]", plain.rstrip("； ")):
        value = part.strip().strip("`")
        if value.startswith(("https://", "http://")):
            yield "url", value, ""
        elif value:
            yield "artifact", value, ""


def _looks_like_path(value):
    # Slashes in ratios/dates and periods in amounts occur in ordinary prose.
    # Existing files and explicitly typed references do not rely on this guess.
    text = re.sub(r"(?<![A-Za-z0-9_.-])\d+(?:\s*/\s*\d+)+(?![A-Za-z0-9_.-])", "", value)
    return bool(re.search(r"(?<=\S)/(?=\S)|\.[^\W\d_][\w-]{0,20}$", text))


def _location(root, role, value, digest):
    if role in ("git_object", "governance_id", "url"):
        return {"role": role, "target": value, "availability": "not_checked"}
    if role == "delta_base" and GIT_RANGE.fullmatch(value):
        return {"role": role, "kind": "git_range", "target": value, "availability": "not_checked"}
    target = value.replace("\\", "/").removeprefix("./")
    try:
        if Path(target).is_absolute():
            target = Path(target).relative_to(root).as_posix()
        _project_path_parts(target)
        path = _project_path(root, target)
        status = "present" if path.is_file() or (role == "candidate" and path.is_dir()) else "missing"
    except FileNotFoundError:
        if role == "artifact" and not _looks_like_path(target):
            return None
        status = "missing"
    except (ValueError, OSError):
        if role == "artifact" and not _looks_like_path(target):
            return None
        status = "unverifiable"
    result = {"role": role, "target": target, "availability": status}
    if digest:
        result["recorded_sha256"] = digest
    return result


def _report_pointers(root, receipt, expected):
    # Read the selected machine receipt's bounded header, never its report/delta.
    try:
        with _project_path(root, receipt).open("rb") as stream:
            header = stream.read(16384).rsplit(b"\n", 1)[0].decode("utf-8")
    except (ValueError, OSError):
        return []
    if not header.startswith("# Review Record (machine-written by review-record)"):
        return []
    fields = dict(re.findall(r"^- (\w+): ([^\r\n]+)", header, re.MULTILINE))
    if any(fields.get(key) != value for key, value in expected.items()):
        return []
    return [(key, fields[key], fields.get("report_sha256", "") if key == "report" else "")
            for key in ("report", "delta_base") if fields.get(key)]


def _size(data):
    return len(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")) + 1


def locations_for(root, material):
    """Resolve the selected metadata only. Shared with the optional integrity check."""
    pointers = list(material.pointers)
    seen = set()
    for role, value, digest in chain(pointers, _artifact_refs(material.artifacts)):
        location = _location(root, role, value, digest)
        if not location:
            continue
        if role == "receipt" and material.review_binding and location["availability"] == "present":
            reports = [] if material.unbound_receipt else _report_pointers(root, location["target"], material.review_binding)
            if reports:
                pointers.extend(reports)
            else:
                location["availability"] = "binding_unconfirmed"
        if location["target"] in seen:
            continue
        seen.add(location["target"])
        yield location


def _detail(root, result, material, offset):
    item = result["items"][0]
    item["source"] = material.source
    if material.supersedes:
        item["supersedes"] = "learn:" + material.supersedes
    item["locations"] = []
    for index, location in enumerate(locations_for(root, material)):
        if index < offset:
            continue
        if index - offset == MAX_ITEMS:
            result["next_offset"] = index
            result["next"] = "Use the same --ref with --offset next_offset only if another original is needed."
            item["locations_omitted"] = True
            break
        item["locations"].append(location)
        if _size(result) > MAX_BYTES - 200:
            item["locations"].pop()
            item["locations_omitted"] = True
            if item["locations"]:
                result["next_offset"] = index
                result["next"] = "Use the same --ref with --offset next_offset only if another original is needed."
                break
            # One indivisible locator cannot fit even on an empty page. Keep its
            # ordinal and the exact ledger source; never advertise a partial path.
            item.setdefault("oversize_offsets", []).append(index)
            result["next"] = "The full locator at oversize_offsets is in the selected source record."


def records_for_unit(root, state, unit, *, include_task=True):
    """All unit-bound records and separately identified task-level evidence."""
    historical = unit["flow_unit_id"] in acceptance_successors(state["flow_units"])
    native = _unit_records(unit, owner_for(state, unit), historical)
    yield from _bound_reviews(native, list(_authority_reviews(root, unit)))
    if include_task:
        yield from _evidence_records(root, unit["task_id"], None)


def _matches_alias(record, ref):
    return record.ref == ref or record.review_id == ref


def _rank(record, query, words):
    paths = [value for _, value, _ in record.pointers]
    paths.extend(value for kind, value, _ in _artifact_refs(record.artifacts)
                 if kind != "artifact" or _looks_like_path(value))
    haystack = " ".join((record.ref, record.purpose, record.keywords, *paths)).casefold()
    if all(word in haystack for word in words):
        return (record.ref.casefold() != query.casefold(), record.status in ("historical", "superseded"),
                not record.default_candidate, record.scope == "task", record.ref)
    return None


def _find(root, unit_id, query, ref, check, offset):
    path = _project_path(root, RUNTIME)
    state = _payload(path)
    unit = _unit(state, unit_id)
    if check:
        from loop_material_check import check_materials
        return check_materials(root, state, unit)
    historical = unit_id in acceptance_successors(state["flow_units"])
    native = _unit_records(unit, owner_for(state, unit), historical, current_only=query is None and ref is None)
    result = {"unit": unit_id, "state": "empty", "verification": "metadata_only", "items": [],
              "next": "Use --query with a specific criterion or keyword only if the task needs more evidence."}
    if ref is not None:
        if EVD.fullmatch(ref):
            source = _evidence_records(root, unit["task_id"], ref)
        elif REVIEW_ID.fullmatch(ref):
            source = _bound_reviews(native, list(_authority_reviews(root, unit)))
        elif ref.startswith("gate:"):
            selected = [record for record in native if record.ref == ref]
            source = _bound_reviews(selected, list(_authority_reviews(root, unit))) if any(
                record.review_id for record in selected) else selected
        else:
            source = native
        hits = list(islice((record for record in source if _matches_alias(record, ref)), 2))
        if len(hits) > 1:
            return dict(result, state="ambiguous", next="Conflicting scoped records share that reference. Check the ledger.")
    elif query is not None:
        words = query.casefold().split()
        records = records_for_unit(root, state, unit)
        matches = ((key, record) for record in records if (key := _rank(record, query, words)) is not None)
        chosen = nsmallest(MAX_ITEMS + 1, matches, key=lambda pair: pair[0])
        hits = [record for _, record in chosen[:MAX_ITEMS]]
        if len(chosen) > MAX_ITEMS:
            result["more_matches"] = True
    else:
        chosen = {}
        for record in native:
            kind = record.ref.partition(":")[0]
            if record.default_candidate:
                # Several concurrent choices require a question to distinguish them.
                chosen[kind] = None if kind in chosen else record
        hits = [record for record in chosen.values() if record]
    if hits:
        result.update(state="found", items=[record.brief() for record in hits],
                      next="Stop if sufficient. Resolve a listed --ref only when its source is needed.")
        if result.get("more_matches"):
            result["next"] = "Stop if sufficient. Otherwise narrow --query to the missing criterion or resolve an exact --ref."
        if ref is not None:
            result["next"] = "Open only a needed location. This lookup does not verify content or grant gate approval."
            _detail(root, result, hits[0], offset or 0)
    return result


def lookup(root, unit_id, *, query=None, ref=None, check=False, offset=None):
    if offset is not None and (not ref or offset < 0):
        return {"state": "invalid", "error": "--offset requires an exact --ref and a nonnegative location index."}
    if not UNIT_ID.fullmatch(unit_id) or any(value is not None and
            (not value.strip() or len(value) > 256) for value in (query, ref)):
        return {"state": "invalid", "error": "Supply a valid unit and a nonempty query or reference (up to 256 characters)."}
    try:
        return _find(Path(root), unit_id, query, ref, check, offset)
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        return {"unit": unit_id, "state": "invalid", "error": "Unknown unit or unreadable material metadata. Check the registered unit and its records."}
