"""Validation for immutable per-version release manifests."""

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

from .context import RepositoryContext
from .git_facts import commit_adding_path, is_shallow, resolve_commit, tag_facts
from .model import CheckResult
from .schema_validation import validate_schema


SCHEMA_MAJOR = 1
LIFECYCLE_STATES = {"candidate", "released"}
PROVENANCE_STATES = {"native", "historical_backfill"}
DecisionResolver = Callable[[str, str, str], bool]


def default_decision_resolver(context: RepositoryContext) -> DecisionResolver:
    sources = [context.root / ".governance/decision-log.md"]
    sources.extend(sorted((context.root / ".governance/archive/decisions").glob("*.md")))

    def resolve(decision_id: str, version: str, commit: str) -> bool:
        prefix = "HISTORICAL_TAG_AUTHORIZATION_JSON: "
        exact_keys = {"decision_id", "action", "version", "commit", "tag", "status"}
        matching_records = []
        for source in sources:
            if not source.is_file():
                continue
            for line in source.read_text(encoding="utf-8", errors="replace").splitlines():
                stripped = line.strip()
                if not stripped.startswith(prefix):
                    continue
                raw = stripped[len(prefix):]
                try:
                    record = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict) or set(record) != exact_keys:
                    continue
                if record.get("decision_id") == decision_id:
                    matching_records.append(record)
        if len(matching_records) != 1:
            return False
        record = matching_records[0]
        return record == {
            "decision_id": decision_id,
            "action": "approved",
            "version": version,
            "commit": commit,
            "tag": f"v{version}",
            "status": record.get("status"),
        } and record["status"] in {"approved", "active"}

    return resolve


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def event_integrity(event: Dict[str, Any]) -> str:
    payload = {key: value for key, value in event.items() if key != "integrity"}
    return f"sha256:{sha256(_canonical(payload)).hexdigest()}"


def _derive_ref(
    context: RepositoryContext,
    spec: object,
    manifest_rel: str,
    label: str,
) -> CheckResult:
    if isinstance(spec, str):
        result = resolve_commit(context, spec)
        if result.state == "FAIL" and is_shallow(context):
            return CheckResult("UNKNOWN", [f"{label}: commit is unavailable in shallow history"])
        return result
    if isinstance(spec, dict) and spec.get("derivation") == "git_commit_adding_path":
        result = commit_adding_path(context, manifest_rel)
        if result.state == "FAIL" and is_shallow(context):
            return CheckResult("UNKNOWN", [f"{label}: adding commit is unavailable in shallow history"])
        if result.state != "PASS":
            result.issues = [f"{label}: {issue}" for issue in result.issues]
        return result
    return CheckResult("FAIL", [f"{label}: expected a commit SHA or git_commit_adding_path derivation"])


def _validate_events(events: object) -> tuple[List[str], List[Dict[str, Any]]]:
    if not isinstance(events, list):
        return ["events must be a list"], []
    issues: List[str] = []
    normalized: List[Dict[str, Any]] = []
    ids = set()
    sort_keys = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            issues.append(f"events[{index}] must be an object")
            continue
        event_id = event.get("id")
        if not isinstance(event_id, str) or not event_id:
            issues.append(f"events[{index}].id must be non-empty")
        elif event_id in ids:
            issues.append(f"duplicate event id `{event_id}`")
        ids.add(event_id)
        if event.get("type") not in {"candidate_to_released", "amendment", "withdrawal"}:
            issues.append(f"events[{index}].type is unsupported")
        if event.get("integrity") != event_integrity(event):
            issues.append(f"events[{index}] integrity hash mismatch")
        sort_keys.append((str(event.get("recorded_at", "")), str(event_id or "")))
        normalized.append(event)
    if sort_keys != sorted(sort_keys):
        issues.append("events must use stable recorded_at/id ordering")
    return issues, normalized


def derive_effective_state(manifest: Dict[str, Any]) -> Dict[str, Any]:
    state = {
        "lifecycle_state": manifest.get("lifecycle_state"),
        "withdrawn": False,
        "amendments": [],
    }
    for event in manifest.get("events", []):
        event_type = event.get("type")
        if event_type == "candidate_to_released":
            state["lifecycle_state"] = "released"
        elif event_type == "amendment":
            state["amendments"].append(event.get("claims", {}))
        elif event_type == "withdrawal":
            state["withdrawn"] = True
    return state


def _transition_commits(context: RepositoryContext, manifest_rel: str) -> CheckResult:
    rc, stdout, stderr = context.run_git("log", "--format=%H", "--", manifest_rel)
    if rc in {124, 125}:
        return CheckResult("UNKNOWN", [stderr or "transition history unavailable"])
    commits = [line for line in stdout.splitlines() if line]
    transitions = []
    for commit in commits:
        rc, parents, _ = context.run_git("show", "-s", "--format=%P", commit)
        if rc != 0:
            continue
        parent_list = parents.split()
        if len(parent_list) != 1:
            continue
        rc_now, now_text, _ = context.run_git("show", f"{commit}:{manifest_rel}")
        rc_before, before_text, _ = context.run_git("show", f"{parent_list[0]}:{manifest_rel}")
        if rc_now != 0 or rc_before != 0:
            continue
        try:
            now = json.loads(now_text)
            before = json.loads(before_text)
        except json.JSONDecodeError:
            continue
        if before.get("lifecycle_state") == "candidate" and now.get("lifecycle_state") == "released":
            transitions.append({"commit": commit, "parent": parent_list[0]})
    if len(transitions) != 1:
        return CheckResult(
            "FAIL",
            [f"expected one candidate-to-released Git transition, found {len(transitions)}"],
            {"transitions": transitions},
        )
    return CheckResult("PASS", facts=transitions[0])


def _is_ancestor(context: RepositoryContext, ancestor: str, descendant: str) -> Optional[bool]:
    rc, _stdout, _stderr = context.run_git("merge-base", "--is-ancestor", ancestor, descendant)
    if rc == 0:
        return True
    if rc == 1:
        return False
    return None


def validate_manifest(
    path: Path,
    context: RepositoryContext,
    remote: object = "origin",
    verify_remote: bool = True,
    decision_resolver: Optional[DecisionResolver] = None,
) -> CheckResult:
    issues: List[str] = []
    facts: Dict[str, Any] = {"path": path.relative_to(context.root).as_posix()}
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return CheckResult("FAIL", [f"cannot read release manifest: {type(exc).__name__}"], facts)

    schema_version = manifest.get("schema_version")
    if not isinstance(schema_version, int) or schema_version != SCHEMA_MAJOR:
        return CheckResult("BLOCKED", [f"unsupported release schema major `{schema_version}`"], facts)

    schema_path = context.root / "skills/software-project-governance/core/release-ledger.schema.json"
    if not schema_path.is_file():
        schema_path = Path(__file__).resolve().parents[2] / "core/release-ledger.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schema_issues = validate_schema(manifest, schema)
    except (OSError, json.JSONDecodeError, ValueError, KeyError) as exc:
        return CheckResult("BLOCKED", [f"release schema validation unavailable: {exc}"], facts)
    if schema_issues:
        return CheckResult("FAIL", schema_issues, facts)

    version = manifest.get("version")
    lifecycle = manifest.get("lifecycle_state")
    provenance = manifest.get("provenance")
    if path.stem != version:
        issues.append(f"manifest filename `{path.stem}` must equal version `{version}`")
    if lifecycle not in LIFECYCLE_STATES:
        issues.append("lifecycle_state must be candidate or released")
    if provenance not in PROVENANCE_STATES:
        issues.append("provenance must be native or historical_backfill")
    event_issues, events = _validate_events(manifest.get("events"))
    issues.extend(event_issues)
    effective = derive_effective_state(manifest)
    if manifest.get("effective_state") != effective:
        issues.append("effective_state does not match append-only events")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        issues.append("artifacts must be an object")
    else:
        for key in ("changelog", "release_docs", "review_evidence"):
            value = artifacts.get(key)
            paths = value if isinstance(value, list) else [value]
            if not paths or any(not isinstance(item, str) or not (context.root / item).is_file() for item in paths):
                issues.append(f"artifacts.{key} contains a missing or invalid path")

    manifest_rel = path.relative_to(context.root).as_posix()
    trust = manifest.get("trust", {})
    if provenance == "historical_backfill":
        if lifecycle != "released":
            issues.append("historical_backfill manifests must describe a released lifecycle")
        original = _derive_ref(context, trust.get("original_release_commit"), manifest_rel, "original_release_commit")
        backfill = _derive_ref(context, trust.get("backfill_commit"), manifest_rel, "backfill_commit")
        for result in (original, backfill):
            if result.state == "UNKNOWN":
                return CheckResult("UNKNOWN", result.issues, facts)
            issues.extend(result.issues)
        original_commit = original.facts.get("commit")
        facts["original_release_commit"] = original_commit
        facts["backfill_commit"] = backfill.facts.get("commit")
        docs = trust.get("document_contemporaneity")
        if docs not in {"contemporaneous", "backfilled_after_release"}:
            issues.append("historical manifest requires document_contemporaneity")
        elif original_commit and isinstance(artifacts, dict):
            for doc_path in artifacts.get("release_docs", []):
                added = commit_adding_path(context, doc_path)
                if added.state != "PASS":
                    issues.append(f"release document commit cannot be derived: {doc_path}")
                    continue
                doc_commit = added.facts["commit"]
                if docs == "contemporaneous" and _is_ancestor(context, doc_commit, original_commit) is not True:
                    issues.append(f"release document is not contemporaneous with the original release: {doc_path}")
                if docs == "backfilled_after_release":
                    after = _is_ancestor(context, original_commit, doc_commit)
                    if after is not True or doc_commit == original_commit:
                        issues.append(f"release document is not a post-release backfill: {doc_path}")
        disposition = trust.get("tag_disposition")
        if disposition not in {"verified_present", "missing_requires_decision", "created_by_decision"}:
            issues.append("historical manifest requires a tag_disposition")
        decision = trust.get("tag_decision")
        if disposition in {"verified_present", "missing_requires_decision"} and decision is not None:
            issues.append(f"{disposition} requires tag_decision to be null")
        if disposition == "created_by_decision":
            if not isinstance(decision, str) or not decision.startswith("DEC-"):
                issues.append("created_by_decision requires a DEC id")
            elif original_commit:
                resolver = decision_resolver or default_decision_resolver(context)
                if not resolver(decision, version, original_commit):
                    issues.append(f"tag decision `{decision}` does not prove version/commit/tag mapping")
        if original_commit and disposition in {"verified_present", "missing_requires_decision", "created_by_decision"}:
            local_tag = resolve_commit(context, f"refs/tags/v{version}")
            if disposition in {"verified_present", "created_by_decision"}:
                if local_tag.state != "PASS" or local_tag.facts.get("commit") != original_commit:
                    issues.append(f"historical tag disposition says verified_present but local tag v{version} does not match")
                elif verify_remote:
                    remote_result = tag_facts(context, f"v{version}", original_commit, remote)
                    facts["tag_facts"] = remote_result.as_dict()
                    if remote_result.state == "UNKNOWN":
                        return CheckResult("UNKNOWN", remote_result.issues, facts)
                    if remote_result.state == "BLOCKED":
                        return CheckResult("BLOCKED", remote_result.issues, facts)
                    issues.extend(remote_result.issues)
            elif local_tag.state == "PASS":
                issues.append(f"historical tag disposition is stale: local tag v{version} now exists")
        facts["trust_level"] = "HISTORICAL_ONLY"
    elif provenance == "native":
        candidate = _derive_ref(context, trust.get("candidate_commit"), manifest_rel, "candidate_commit")
        if candidate.state == "UNKNOWN":
            return CheckResult("UNKNOWN", candidate.issues, facts)
        issues.extend(candidate.issues)
        candidate_commit = candidate.facts.get("commit")
        facts["candidate_commit"] = candidate_commit
        if lifecycle == "candidate":
            if any(event.get("type") == "candidate_to_released" for event in events):
                issues.append("candidate manifest cannot contain a release transition")
        elif lifecycle == "released" and candidate_commit:
            transition_events = [event for event in events if event.get("type") == "candidate_to_released"]
            if len(transition_events) != 1:
                issues.append("released native manifest requires exactly one transition event")
            transition = _transition_commits(context, manifest_rel)
            if transition.state in {"UNKNOWN", "FAIL"} and is_shallow(context):
                return CheckResult("UNKNOWN", ["candidate-to-released transition cannot be proven from shallow history"], facts)
            if transition.state == "UNKNOWN":
                issues.extend(transition.issues)
            elif transition.state != "PASS":
                issues.extend(transition.issues)
            else:
                if transition.facts.get("parent") != candidate_commit:
                    issues.append("release transition parent must equal the committed candidate commit")
                facts["release_commit"] = transition.facts.get("commit")
                if verify_remote:
                    tag_result = tag_facts(context, f"v{version}", transition.facts["commit"], remote)
                    facts["tag_facts"] = tag_result.as_dict()
                    if tag_result.state == "UNKNOWN":
                        return CheckResult("UNKNOWN", tag_result.issues, facts)
                    if tag_result.state == "BLOCKED":
                        return CheckResult("BLOCKED", tag_result.issues, facts)
                    issues.extend(tag_result.issues)

    return CheckResult("FAIL" if issues else "PASS", issues, facts)


def validate_release_ledger(
    context: RepositoryContext,
    manifests_dir: Optional[Path] = None,
    version: Optional[str] = None,
    remote: object = "origin",
    verify_remote: bool = True,
    decision_resolver: Optional[DecisionResolver] = None,
) -> CheckResult:
    manifests_dir = manifests_dir or context.root / "skills/software-project-governance/core/releases"
    paths = [manifests_dir / f"{version}.json"] if version else sorted(manifests_dir.glob("*.json"))
    if not paths:
        return CheckResult("FAIL", ["no release manifests found"])
    results = [validate_manifest(path, context, remote, verify_remote, decision_resolver) for path in paths]
    state_order = {"PASS": 0, "FAIL": 1, "UNKNOWN": 2, "BLOCKED": 3}
    state = max((result.state for result in results), key=state_order.get)
    return CheckResult(
        state,
        [f"{result.facts.get('path', '<unknown>')}: {issue}" for result in results for issue in result.issues],
        {"manifests": [result.as_dict() for result in results]},
    )
