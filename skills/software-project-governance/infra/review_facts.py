"""Read formal review records against a single immutable staged or committed Git tree."""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from authority_ledger import _read_events_raw, ledger_paths
from checks.review_domain import _normalize_review_conclusion
from delivery_acceptance import _project_path, _regular_stat


def _original(root, path):
    relative = (root / str(path).replace("\\", "/")).relative_to(root).as_posix()
    safe = _project_path(root, relative)
    _regular_stat(safe)
    return relative, safe.read_bytes()


def _git(root, *args, env=None):
    try:
        result = subprocess.run(["git", "--no-optional-locks", "-C", str(root), *args],
                                stdin=subprocess.DEVNULL, capture_output=True, timeout=30, env=env, check=True)
        return result.stdout.decode("utf-8")
    except (OSError, UnicodeError, subprocess.SubprocessError) as exc:
        raise ValueError(f"Git could not verify {args[0]}: {exc}") from exc


def _delivery_diff(root, base, commit):
    """Capture one index image. write-tree may write objects and cache-tree data,
    so run it on a private index and object directory, including during dry runs.
    """
    if commit and not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
        raise ValueError("commit requires a full Git object ID")
    if commit:
        if _git(root, "rev-parse", "--verify", commit + "^{commit}").strip() != commit:
            raise ValueError("commit does not identify a commit object")
    initial = False
    if base is None:
        if commit:
            initial = len(_git(root, "rev-list", "--parents", "-n", "1", commit).split()) == 1
        else:
            initial = "# branch.oid (initial)" in _git(
                root, "status", "--porcelain=v2", "--branch", "--untracked-files=no").splitlines()
        base = commit + "^1" if commit else "HEAD"
    base_sha = (_git(root, "hash-object", "-t", "tree", "--stdin").strip() if initial else
                _git(root, "rev-parse", "--verify", "--end-of-options", base + "^{commit}").strip())
    with tempfile.TemporaryDirectory() as temp:
        env = os.environ.copy()
        if commit:
            if not initial:
                _git(root, "merge-base", "--is-ancestor", base_sha, commit)
            tree = _git(root, "rev-parse", commit + "^{tree}").strip()
        else:
            index = _git(root, "rev-parse", "--path-format=absolute", "--git-path", "index").strip()
            objects = _git(root, "rev-parse", "--path-format=absolute", "--git-path", "objects").strip()
            private = Path(temp)
            shutil.copyfile(index, private / "index")
            (private / "objects").mkdir()
            alternates = [objects]
            if env.get("GIT_ALTERNATE_OBJECT_DIRECTORIES"):
                alternates.append(env["GIT_ALTERNATE_OBJECT_DIRECTORIES"])
            env.update(GIT_INDEX_FILE=str(private / "index"),
                       GIT_OBJECT_DIRECTORY=str(private / "objects"),
                       GIT_ALTERNATE_OBJECT_DIRECTORIES=os.pathsep.join(alternates))
            tree = _git(root, "write-tree", env=env).strip()
        raw = _git(root, "diff-tree", "--no-commit-id", "-r", "--raw", "--no-renames",
                   "--no-abbrev", "-z", base_sha, tree, "--", env=env).split("\0")[:-1]
        summary = _git(root, "diff-tree", "--no-commit-id", "-r", "--shortstat",
                       "--no-renames", base_sha, tree, "--", env=env).strip()
    changed = {}
    for info, path in zip(raw[::2], raw[1::2]):
        old_mode, mode, _, blob, _ = info.removeprefix(":").split()
        changed[path] = (old_mode, mode, blob)
    if not changed:
        raise ValueError("the requested base and target have no changed files")
    return changed, summary, {"base": base_sha, "tree": tree, "commit": commit,
                              **({"initial": True} if initial else {})}


def _record(root, task, review_id, event, changed=()):
    from review_record import _MODE_FIELD_RE, _conflicting_blocker_fields, _report_verdict_tokens

    match = re.fullmatch(r"REVIEW-([A-Za-z0-9][A-Za-z0-9_.-]*)-R(0|[1-9][0-9]*)(?:-([A-Z0-9]+(?:-[A-Z0-9]+)*))?", review_id)
    if not match or match[1] != task or not event:
        raise ValueError(f"{review_id}: no formal record for task {task}")
    name = f"review-{task}-R{match[2]}" + ("-" + match[3].lower() if match[3] else "") + ".md"
    record = root / ".governance" / name
    record_rel, data = _original(root, record)
    text = data.decode("utf-8-sig")

    def field(key):
        values = re.findall(r"^- " + key + r": ([^\r\n]+)", text, re.MULTILINE)
        if len(values) != 1:
            raise ValueError(f"{review_id}: missing or ambiguous {key}")
        return values[0]

    verdicts = re.findall(r"^\*\*审查结论\*\*: \*\*([A-Z_]+)\*\*\s*$", text, re.MULTILINE)
    verdict = _normalize_review_conclusion(verdicts[0]) if len(verdicts) == 1 else ""
    reviewer, report, digest = field("reviewer"), field("report"), field("report_sha256")
    if not reviewer.strip() or reviewer.strip().lower() == "unknown":
        raise ValueError(f"{review_id}: reviewer identity is unavailable")
    declared = (field("task"), field("round"), reviewer, report, digest, field("snapshot_commit"), verdict)
    recorded = (event["task_id"], "R" + str(event["round"]), event["reviewer"], event["report_path"],
                event["report_sha256"], event["commit"], _normalize_review_conclusion(event["verdict"]))
    if not verdict or declared != recorded or declared[:2] != (task, "R" + match[2]):
        raise ValueError(f"{review_id}: record conflicts with its ledger event")
    report_rel, report_bytes = _original(root, report)
    if hashlib.sha256(report_bytes).hexdigest() != digest:
        raise ValueError(f"{review_id}: report SHA-256 mismatch")
    report_text = report_bytes.decode("utf-8", errors="replace")
    tokens = _report_verdict_tokens(report_text)
    if ((tokens and verdict not in {"BLOCKED", "ABORTED", "UNKNOWN"} and verdict not in tokens)
            or (verdict == "APPROVED_WITH_NOTES" and _conflicting_blocker_fields(report_text))):
        raise ValueError(f"{review_id}: report contradicts its recorded verdict")
    pairs = re.findall(r"^- snapshot_bind: (.+)=([^=\s]+)\s*$", text, re.MULTILINE)
    pins = dict(pairs)
    if len(pins) != len(pairs):
        raise ValueError(f"{review_id}: duplicate file binding")
    bindings = event.get("bindings")
    if bindings is not None and pins != {item["path"]: item["hash"] for item in bindings}:
        raise ValueError(f"{review_id}: record file bindings differ from the ledger")
    modes = {item["path"]: item.get("mode") for item in bindings or []}
    signed_modes = {path: mode for path, mode in modes.items() if mode}
    if bindings is not None and dict(_MODE_FIELD_RE.findall(text)) != signed_modes:
        raise ValueError(f"{review_id}: record file modes differ from the ledger")
    if event.get("observed_loop") is not None and json.loads(field("observed_loop")) != event["observed_loop"]:
        raise ValueError(f"{review_id}: observed unit scope differs from the ledger")
    tree = event.get("tree")
    if tree is not None:
        if (not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", tree) or field("snapshot_tree") != tree
                or tree not in report_text or _git(root, "cat-file", "-t", tree).strip() != "tree"):
            raise ValueError(f"{review_id}: invalid or unavailable reviewed tree")
        entries = _git(root, "ls-tree", "-r", "-z", "--full-tree", tree).split("\0")
        by_path = {}
        for entry in filter(None, entries):
            header, name = entry.split("\t", 1)
            mode, _, blob = header.split()
            by_path[name] = (blob, mode)
        for path in changed:
            blob, mode = by_path.get(path, ("0" * len(tree), "000000"))
            if path in pins and (pins[path] != blob or modes.get(path) != mode):
                raise ValueError(f"{review_id}: file pin disagrees with reviewed tree at {path}")
            pins[path], modes[path] = blob, mode
    origin = {"id": review_id, "path": record_rel,
              "sha256": hashlib.sha256(data).hexdigest(), "report": report_rel, "report_sha256": digest,
              "conclusion": verdict, "reviewer": reviewer, "round": int(match[2]),
              "binding_source": "ledger" if bindings is not None else "historical record"}
    if tree:
        origin["tree"] = tree
    return origin, pins, modes


def derive_review_facts(root, task, review_ids, *, base=None, commit=None, path_filter=None):
    """Reuse signed rounds only when their per-file pins cover the delivery diff."""
    refs = list(review_ids)
    if not refs or len(set(refs)) != len(refs):
        raise ValueError("provide one or more distinct formal review IDs")
    root = Path(root).resolve()
    try:
        _, events_file, _ = ledger_paths(root / ".governance")
        safe_events = _project_path(root, events_file.relative_to(root).as_posix())
        _regular_stat(safe_events)
        events, integrity = _read_events_raw(safe_events)
        if not integrity["ok"]:
            raise ValueError("review ledger integrity check failed")
        reviews = {e["payload"]["review_id"]: e["payload"] for e in events
                   if e["kind"] == "review_recorded" and e.get("actor") == "review_record"
                   and e["payload"]["task_id"] == task}
        changed, summary, git = _delivery_diff(root, base, commit)
        if path_filter is not None:
            changed = {p: entry for p, entry in changed.items() if path_filter(p)}
            if not changed:
                raise ValueError("no staged changes in the requested review scope")
        rounds = sorted((_record(root, task, ref, reviews.get(ref), changed) for ref in refs),
                        key=lambda item: (item[0]["round"], item[0]["id"]))
        target = commit or "HEAD"
        revisions = {git["base"], *(reviews[ref]["commit"] for ref in refs)}
        if git.get("initial"):
            if (any(reviews[ref]["commit"] != "git:unborn" for ref in refs) or
                    not any(reviews[ref].get("tree") == git["tree"] for ref in refs)):
                raise ValueError("the first product commit requires review of its exact complete Git tree")
            revisions.clear()
        for revision in revisions:
            if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", revision):
                raise ValueError(f"review has no verifiable Git commit: {revision}")
            _git(root, "merge-base", "--is-ancestor", revision, target)
    except (OSError, KeyError, UnicodeError) as exc:
        raise ValueError(f"review evidence unavailable: {exc}") from exc
    outcomes = set()
    latest_by_path = {}
    for path, (old_mode, mode, blob) in changed.items():
        applicable = [(record, pins[path], modes.get(path)) for record, pins, modes in rounds if path in pins]
        if not applicable:
            raise ValueError(f"unreviewed change: {path}")
        latest = max(item[0]["round"] for item in applicable)
        latest_by_path[path] = latest
        for record, pin, signed_mode in applicable:
            if record["round"] != latest:
                continue
            if record.get("tree") and record["tree"] != git["tree"]:
                raise ValueError(f"{record['id']}: staged or committed tree differs from the reviewed tree")
            if pin != blob or (signed_mode != mode and not (
                    signed_mode is None and mode == "100644" and old_mode in ("100644", "000000"))):
                raise ValueError(f"{record['id']}: reviewed content or mode differs at {path}")
            outcomes.add(record["conclusion"])
    final_round = rounds[-1][0]["round"]
    outcomes.update(record["conclusion"] for record, _, _ in rounds if record["round"] == final_round)
    for ref, event in reviews.items():
        if ref in refs or _normalize_review_conclusion(event["verdict"]) == "APPROVED":
            continue
        if event["round"] < min(latest_by_path.values()):
            continue
        # Earlier ledger versions did not carry bindings. Only a later round
        # covering every affected path can discharge an omitted disposition.
        bindings = event.get("bindings")
        guarded = {item["path"] for item in bindings or []}
        if not guarded and bindings is None:
            try:
                _, pins, _ = _record(root, task, ref, event)
                guarded = set(pins)
            except (OSError, KeyError, UnicodeError) as exc:
                raise ValueError(f"cannot verify omitted disposition {ref}: {exc}") from exc
        if any(n <= event["round"] for path, n in latest_by_path.items() if not guarded or path in guarded):
            raise ValueError(f"unaccounted review disposition: {ref}")
    precedence = ("BLOCKED", "NEEDS_CHANGE", "ABORTED", "UNKNOWN", "APPROVED_WITH_NOTES", "APPROVED")
    conclusion = next(value for value in precedence if value in outcomes)
    records = [record for record, _, _ in rounds]
    reviewers = ", ".join(dict.fromkeys(record["reviewer"] for record in records))
    return {"files_changed": list(changed), "diff_summary": summary,
            "review": {"conclusion": conclusion, "reviewer": reviewers, "records": records}, "git": git}
