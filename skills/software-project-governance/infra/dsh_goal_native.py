"""JSON preflight for an opted-in DSH native goal. The host owns all native mutations."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
from pathlib import Path

import delivery_acceptance as acceptance
import goal_bridge as bridge
from dsh_goal_work import read_work_packages
from goal_planning import _read_locks, plan_goal_candidates
from governance_store import LOCK_DIR_NAME, LOCKS_FILE_NAME, StoreError, _TargetLock


PROFILE = ".governance/dsh-goal.json"
MAX_REQUEST = 64 * 1024
MAX_PACKETS = 4 * 1024 * 1024
_MAX_NUMBER = 2**53 - 1
_REQUEST_FIELDS = {"schema_version", "action", "session_id", "goal_id", "revision", "objective", "max_rounds", "usage"}
_PROFILE_FIELDS = {"intent_sha256", "budget", "contract"}
_LIMIT_FIELDS = {"rounds": "max_rounds", "tokens": "max_tokens", "wall_clock": "max_seconds"}
_TREE_ACTIONS = ("tree-stop", "tree-settle")
_DIRECT_FIELDS = {"workspace", "sessionId", "intentSha256", "criterionId", "workPackageId", "receipt",
                  "receiptSha256", "preflightWorkspace", "preflightSessionId", "recipeSha256",
                  "sourceSha256", "sourceRoot", "reproducer", "reproducerSha256", "profileSha256"}


def _number(value, dimension, *, positive=False):
    if dimension != "wall_clock" and type(value) is not int:
        raise ValueError("expected integer budget measurement or limit")
    bridge._budget_number(value, dimension, positive=positive)
    if value > _MAX_NUMBER:
        raise ValueError("budget measurement or limit is too large")
    return value


def _request(stream):
    raw = stream.read(MAX_REQUEST + 1)
    if len(raw) > MAX_REQUEST:
        raise ValueError("request is too large")
    request = json.loads(raw.decode("utf-8"), object_pairs_hook=acceptance._json_object)
    action = request.get("action") if isinstance(request, dict) else None
    tree = action in _TREE_ACTIONS
    fields = _REQUEST_FIELDS | {"tree"} if tree else _REQUEST_FIELDS
    if action == "admit" and "direct_repair" in request:
        fields |= {"direct_repair"}
    if (not isinstance(request, dict) or request.keys() != fields
            or type(request["schema_version"]) is not int or request["schema_version"] != 1
            or action not in ("admit", "complete", *_TREE_ACTIONS)
            or not bridge._valid_native_session_id(request["session_id"])
            or not isinstance(request["goal_id"], str)
            or not bridge._GOAL_ID_RE.fullmatch(request["goal_id"])
            or not bridge._valid_native_revision(request["revision"])
            or not isinstance(request["objective"], str) or not request["objective"].strip()):
        raise ValueError("invalid native goal request")
    acceptance._project_path_parts(request["goal_id"] + ".json")
    request["objective"].encode("utf-8")
    _number(request["max_rounds"], "rounds", positive=True)
    usage = request["usage"]
    if not isinstance(usage, dict) or "rounds" not in usage or usage.keys() - {"rounds", "tokens", "seconds"}:
        raise ValueError("invalid native goal usage")
    for field, value in usage.items():
        _number(value, "wall_clock" if field == "seconds" else field)
    if tree:
        branch = request["tree"]
        if (not isinstance(branch, dict) or branch.keys() != {"id", "observation"}
                or not isinstance(branch["id"], str)
                or len(branch["id"]) != 32 or any(c not in "0123456789abcdef" for c in branch["id"])
                or usage.keys() != {"rounds", "tokens", "seconds"}):
            raise ValueError("invalid DSH goal tree request")
        bridge._validate_tree_observation(branch["observation"])
    return request


def _reply(request, status, code, **details):
    result = {"schema_version": 1, "status": status, "code": code}
    if request is not None:
        result.update({key: request[key] for key in ("session_id", "goal_id", "revision")})
    return {**result, **details}


def _optional_path(path: Path, *, directory=False):
    try:
        info = acceptance._plain_stat(path)
    except FileNotFoundError:
        return False
    if directory:
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError("expected governance directory")
    elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("expected a regular governance record with one link")
    return True


def _profile(root, request):
    path = root / PROFILE
    record, _ = acceptance._read_record(path, _PROFILE_FIELDS, max_bytes=MAX_REQUEST)
    if (not isinstance(record["intent_sha256"], str)
            or not acceptance._SHA256.fullmatch(record["intent_sha256"])):
        raise ValueError("invalid profile intent hash")
    draft = record["contract"]
    budget = record["budget"]
    if (not isinstance(draft, dict) or draft.keys() != acceptance.CONTRACT_FIELDS - {"goal_id"}
            or not isinstance(budget, dict) or budget.keys() != set(_LIMIT_FIELDS.values())):
        raise ValueError("invalid profile contract or budget")
    contract = {**draft, "goal_id": request["goal_id"], "schema_version": 1}
    acceptance._validate_contract(contract)
    parts = acceptance._project_path_parts(contract["artifact"])
    if parts == [".governance"] or contract["artifact"] in (acceptance.CONTRACT, acceptance.RECEIPT):
        raise ValueError("artifact must be separate from the acceptance records")
    config = {
        name: {"limit": _number(budget[field], name, positive=True),
               "warn_ratio": bridge.DEFAULT_BUDGET_CONFIG["rounds"]["warn_ratio"], "danger_ratio": 1.0}
        for name, field in _LIMIT_FIELDS.items()
    }
    packages, work_hash = read_work_packages(root, record["intent_sha256"], contract["criteria"])
    frozen = {**record, "work_sha256": work_hash} if work_hash is not None else record
    profile_hash = hashlib.sha256(_encode(frozen)).hexdigest()
    return record["intent_sha256"], profile_hash, contract, config, packages


def _encode(record):
    return (json.dumps(record, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")


def _absolute_record_path(value):
    path = Path(value)
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise ValueError("expected a canonical absolute native repair path")
    return path


def _source_sha256(root, relative):
    source = acceptance._project_path(root, relative)
    if not _optional_path(source, directory=True):
        raise ValueError("missing native repair source root")
    rows, pending, entries, size = {}, [source], 0, 0
    while pending:
        for item in pending.pop().iterdir():
            if item.parent == source and item.name in {"node_modules", "dist"}:
                continue
            entries += 1
            info = acceptance._plain_stat(item)
            size += info.st_size if stat.S_ISREG(info.st_mode) else 0
            if entries > 4096 or size > 128 * 1024 * 1024:
                raise ValueError("native repair source exceeds attestation bounds")
            if stat.S_ISDIR(info.st_mode):
                pending.append(item)
            elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                rows[item.relative_to(source).as_posix()] = acceptance._hash_file(item)
            else:
                raise ValueError("native repair source is not a plain tree")
    if not rows:
        raise ValueError("native repair source is empty")
    payload = json.dumps(rows, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _direct_repair(root, request, packages, scope, contract_sha256, profile_sha256):
    hint = request.get("direct_repair")
    if not isinstance(hint, dict) or hint.keys() not in (_DIRECT_FIELDS, _DIRECT_FIELDS | {"contractSha256"}):
        raise ValueError("invalid native repair entry")
    if any(not isinstance(value, str) or not value or len(value) > 4096 for value in hint.values()):
        raise ValueError("invalid native repair field")
    for field in ("intentSha256", "recipeSha256", "receiptSha256", "sourceSha256", "reproducerSha256"):
        if not acceptance._SHA256.fullmatch(hint[field]):
            raise ValueError("invalid native repair fingerprint")
    if (_absolute_record_path(hint["workspace"]) != root or hint["sessionId"] != request["session_id"]
            or hint["profileSha256"] != profile_sha256
            or hint["intentSha256"] != hashlib.sha256(request["objective"].encode("utf-8")).hexdigest()):
        raise ValueError("native repair scope mismatch")
    claim = hint.get("contractSha256")
    if scope and claim is None:
        return None  # A process restart or later opt-in cannot grant a first-admission exception.
    if (scope and claim != contract_sha256) or (scope is None and claim is not None):
        raise ValueError("native repair claim does not match admission")
    criterion, package = hint["criterionId"], hint["workPackageId"]
    if not any(item["id"] == package and item["criteria"] == [criterion]
               and (item["action"], item["method"]) == ("repair", "repair-criterion") for item in packages):
        raise ValueError("native repair must select one typed repair work package for one criterion")
    receipt_path = _absolute_record_path(hint["receipt"])
    canary = _absolute_record_path(hint["preflightWorkspace"])
    if (root.is_relative_to(canary) or canary.is_relative_to(root)
            or receipt_path.is_relative_to(root) or receipt_path.is_relative_to(canary)
            or not bridge._valid_native_session_id(hint["preflightSessionId"])
            or hint["preflightSessionId"] == request["session_id"]):
        raise ValueError("native repair receipt is not independently hosted")
    receipt, digest = acceptance._read_record(receipt_path, {
        "session_id", "workspace", "recipe_sha256", "status", "browser", "build",
    }, max_bytes=MAX_REQUEST)
    if (digest != hint["receiptSha256"] or receipt["session_id"] != hint["preflightSessionId"]
            or _absolute_record_path(receipt["workspace"]) != canary
            or receipt["recipe_sha256"] != hint["recipeSha256"] or receipt["status"] != "PASS"):
        raise ValueError("native repair receipt does not match the preflight identity")
    browser, build = receipt["browser"], receipt["build"]
    if (not isinstance(browser, dict) or not isinstance(build, dict)
            or (browser.get("status"), browser.get("code"), browser.get("journey")) != ("PASS", "BROWSER_EXECUTED", "FAIL")
            or type(browser.get("exit_code")) is not int or browser["exit_code"] != 1
            or (build.get("status"), build.get("code")) != ("PASS", "BUILD_EXECUTED")
            or type(build.get("exit_code")) is not int or build["exit_code"] != 0
            or browser.get("mode") != "workspace-write" or build.get("mode") != "workspace-write"
            or browser.get("enforcement") not in ("partial", "full")
            or build.get("enforcement") != browser["enforcement"]
            or not isinstance(build.get("artifact_sha256"), str)
            or not acceptance._SHA256.fullmatch(build["artifact_sha256"])):
        raise ValueError("native repair requires an executed browser failure and a fresh build")
    if scope is None:
        for workspace in {root, canary}:
            proof = acceptance._project_path(workspace, hint["reproducer"])
            if (acceptance._hash_file(proof, nonempty=True) != hint["reproducerSha256"]
                    or _source_sha256(workspace, hint["sourceRoot"]) != hint["sourceSha256"]):
                raise ValueError("native repair input differs from the frozen preflight")
    return {"criterionId": criterion, "workPackageId": package}


def _publish_contract(path, contract):
    """Publish the full bytes atomically and never replace an existing record."""
    descriptor, scratch = tempfile.mkstemp(prefix="delivery-contract.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(_encode(contract))
            stream.flush()
            os.fsync(stream.fileno())
        try:
            if os.name == "nt":
                os.rename(scratch, path)
            else:
                os.link(scratch, path)
        except FileExistsError:
            pass  # The caller verifies the winner before binding.
    finally:
        Path(scratch).unlink(missing_ok=True)


def _load_packets(governance_dir):
    path = governance_dir / "execution-packets.json"
    if not _optional_path(path):
        return {}, "missing execution packets"
    with path.open("rb") as stream:
        raw = stream.read(MAX_PACKETS + 1)
    if len(raw) > MAX_PACKETS:
        raise ValueError("execution packets are too large")
    data = json.loads(raw.decode("utf-8"), object_pairs_hook=acceptance._json_object)
    packets = data.get("packets", data) if isinstance(data, dict) else None
    if not isinstance(packets, dict):
        raise ValueError("invalid execution packets")
    return packets, ""


def _active_goal_work(governance_dir, request, task_ref):
    if not _optional_path(governance_dir / LOCKS_FILE_NAME):
        return False
    active = _read_locks(governance_dir)
    if task_ref in active or any(item["coordinator_session"] == request["session_id"] for item in active.values()):
        return True
    if not active:
        return False
    packets, _ = _load_packets(governance_dir)
    for task_id in active:
        packet = packets.get(task_id, {})
        link = packet.get("goal_link") if isinstance(packet, dict) else None
        if isinstance(link, dict) and link.get("goal_id") == request["goal_id"]:
            return True
    return False


def _snapshot(artifact):
    used = bridge._bound_usage(artifact)
    zones = bridge._judge_bound_usage(used, artifact["budget_config"])["zones"]
    return {
        "contract_sha256": artifact["contract_sha256"], "goal_state": artifact["state"],
        "checkpoint_materialized": artifact["checkpoint_materialized"],
        "open_obligations": len(artifact["obligations"]),
        "budget": {"zones": zones, "unmeasured_dimensions": sorted(artifact["budget_config"].keys() - used.keys())},
        **({"tree_stop": artifact["tree_stop"]} if "tree_stop" in artifact else {}),
    }


def _short_plan(project_root, goal, packages, direct_repair=None):
    governance_dir = project_root / ".governance"
    try:
        result = plan_goal_candidates(project_root, goal, load_packets=lambda: _load_packets(governance_dir),
                                      work_packages=packages, direct_repair=direct_repair)
    except (OSError, ValueError, RecursionError, StoreError):
        return {"state": "ERROR"}
    return {
        "state": result["state"],
        "criterion_gaps": {key: value for key, value in list(result.get("criterion_gaps", {}).items())[:32]
                           if len(key) <= 128},
        "recommendations": [
            {"task_id": item["task_id"], "action": item["action"], "mode": item["mode"],
             "estimated_rounds": item["estimated_rounds"]}
            for item in result["recommended_top_n"] if len(item["task_id"]) <= 128
        ],
        "in_flight_count": len(result["in_flight"]),
        "work_packages": result.get("work_packages", [])[:3],
        **({"direct_repair": True} if result.get("direct_repair") else {}),
    }


def _checkpoint_reply(request, target, config, governance_dir, code):
    goal = request["goal_id"]
    checkpoint = bridge._write_checkpoint_locked(goal, target, task_ref="", obligations=None,
                                                  governance_dir=governance_dir, config=config,
                                                  rules_version=None)
    if checkpoint.get("error"):
        return _reply(request, "HOLD", "CHECKPOINT_INVALID")
    artifact, error = bridge._load_artifact(target, goal, config)
    if error:
        return _reply(request, "HOLD", "STATE_INVALID")
    return _reply(request, "HOLD", code, **_snapshot(artifact))


def _tree_report(request, target, artifact, governance_dir):
    branch = request["tree"]
    stop = artifact.get("tree_stop")
    same_stop = stop is not None and stop["id"] == branch["id"] and stop["revision"] == request["revision"]
    state = artifact["state"]
    settling = request["action"] == "tree-settle"
    if settling:
        if not same_stop or state not in ("CHECKPOINTED", "BLOCKED"):
            return _reply(request, "HOLD", "TREE_STOP_MISMATCH")
        if stop["status"] != "PENDING":
            return _reply(request, "HOLD", "TREE_TAIL_RECORDED", **_snapshot(artifact))
    elif state not in ("RUNNING", "DRAINING", "CHECKPOINTED") or (
        stop is not None and stop["revision"] >= request["revision"]
    ):
        code = "TREE_BUDGET_STOPPED" if same_stop else "TREE_STOP_MISMATCH"
        return _reply(request, "HOLD", code, **_snapshot(artifact))

    config = artifact["budget_config"]
    used = bridge._bound_usage(artifact)
    usage = request["usage"]
    measured = {"rounds": usage["rounds"], "tokens": usage["tokens"], "wall_clock": usage["seconds"]}
    zones = bridge._judge_bound_usage({key: max(used.get(key, 0), value)
                                      for key, value in measured.items()}, config)["zones"]
    if settling:
        observation = dict(branch["observation"])
        observation["sessions"] = max(observation["sessions"], stop["observation"]["sessions"])
        if branch["observation"]["sessions"] < stop["observation"]["sessions"]:
            observation["missing_sessions"] += stop["observation"]["sessions"] - branch["observation"]["sessions"]
        if any(measured[key] < used.get(key, 0) for key in ("tokens", "wall_clock")):
            observation["flush_failures"] += 1
        stop["observation"] = observation
        stop["status"] = ("INCOMPLETE" if any(observation[key] for key in bridge._TREE_COUNTS - {"sessions"})
                          else "SETTLED")
        artifact["budget_consumption"] = zones
        bridge._save(target, artifact)
        return _reply(request, "HOLD", "TREE_TAIL_RECORDED", **_snapshot(artifact))

    dimensions = [key for key in ("tokens", "wall_clock") if measured[key] >= config[key]["limit"]]
    if not dimensions:
        return _reply(request, "HOLD", "TREE_BUDGET_NOT_REACHED", **_snapshot(artifact))
    artifact["tree_stop"] = {"id": branch["id"], "revision": request["revision"], "status": "PENDING",
                             "dimensions": dimensions, "observation": branch["observation"]}
    artifact["budget_consumption"] = zones
    if state == "CHECKPOINTED" and artifact["checkpoint_materialized"]:
        bridge._save(target, artifact)
    else:
        bridge._write_checkpoint_locked(request["goal_id"], target, task_ref="", obligations=None,
                                       governance_dir=governance_dir, config=config, rules_version=None,
                                       artifact=artifact)
    return _reply(request, "HOLD", "TREE_BUDGET_STOPPED", **_snapshot(artifact))


def _run_locked(root, target, request):
    goal = request["goal_id"]
    governance_dir = root / ".governance"
    action = request["action"]
    existing = _optional_path(target)
    artifact, error = bridge._load_artifact(target, goal, bridge.DEFAULT_BUDGET_CONFIG)
    if error:
        return _reply(request, "HOLD", "STATE_INVALID")
    scope = artifact.get("native_dsh")
    if not _optional_path(root / PROFILE):
        return (_reply(request, "HOLD", "CONFIG_MISSING") if scope
                else _reply(request, "NOT_CONFIGURED", "NO_PROFILE"))
    if bridge.bridge_disabled():
        return _reply(request, "HOLD", "BRIDGE_DISABLED")
    intent_hash, profile_hash, contract, config, packages = _profile(root, request)
    intent = request["objective"]
    if hashlib.sha256(intent.encode("utf-8")).hexdigest() != intent_hash:
        return _reply(request, "HOLD", "INTENT_MISMATCH")
    if scope is not None:
        if (scope["session_id"] != request["session_id"] or artifact["original_intent"] != intent):
            return _reply(request, "HOLD", "SCOPE_MISMATCH")
        if request["revision"] < scope["revision"] and action != "tree-settle":
            return _reply(request, "HOLD", "STALE_REVISION")
        if profile_hash != scope["profile_sha256"]:
            return _reply(request, "HOLD", "PROFILE_CHANGED")
        config = artifact["budget_config"]
    elif existing or action != "admit":
        return _reply(request, "HOLD", "NATIVE_BINDING_REQUIRED")
    if request["max_rounds"] != config["rounds"]["limit"]:
        return _reply(request, "HOLD", "ROUND_LIMIT_MISMATCH")

    direct_repair = None
    direct_error = False
    if "direct_repair" in request:
        try:
            direct_repair = _direct_repair(root, request, packages, scope, artifact.get("contract_sha256"),
                                           profile_hash)
        except (OSError, ValueError, TypeError, RecursionError):
            direct_error = True  # An invalid optional hint cannot change ordinary native admission.

    contract_path = root / acceptance.CONTRACT
    if scope is None and not _optional_path(contract_path):
        _publish_contract(contract_path, contract)
    try:
        current_contract, digest = acceptance._contract(contract_path, max_bytes=MAX_REQUEST * 2)
    except (OSError, ValueError, RecursionError):
        return _reply(request, "HOLD", "CONTRACT_INVALID")
    if current_contract != contract or (scope is not None and digest != artifact["contract_sha256"]):
        return _reply(request, "HOLD", "CONTRACT_CHANGED")

    if action in _TREE_ACTIONS:
        if action == "tree-stop" and request["revision"] != scope["revision"]:
            return _reply(request, "HOLD", "STALE_REVISION")
        return _tree_report(request, target, artifact, governance_dir)

    if scope is None:
        artifact["budget_config"] = config
        artifact.update(bridge._intent_fields(intent, digest), checkpoint_materialized=False)
    artifact["native_dsh"] = {"session_id": request["session_id"], "revision": request["revision"],
                              "profile_sha256": profile_hash}
    if artifact["state"] != "RUNNING":
        if artifact["state"] == "DRAINING" or not artifact["checkpoint_materialized"]:
            bridge._save(target, artifact)
            return _checkpoint_reply(request, target, config, governance_dir, "AUTHORIZED_RESUME_REQUIRED")
        if scope != artifact["native_dsh"]:
            bridge._save(target, artifact)
        return _reply(request, "HOLD", "AUTHORIZED_RESUME_REQUIRED", **_snapshot(artifact))

    stop = artifact.get("tree_stop")
    awaiting_native_resume = stop is not None and "resumed_revision" not in stop
    if awaiting_native_resume and (action != "admit" or request["revision"] <= stop["revision"]):
        return _reply(request, "HOLD", "AUTHORIZED_RESUME_REQUIRED", **_snapshot(artifact))

    record = bridge._record_execution_locked(goal, target, in_flight=False, task_ref="", cost=None,
                                             governance_dir=governance_dir, config=config, artifact=artifact,
                                             rounds=request["usage"]["rounds"], tokens=request["usage"].get("tokens"),
                                             seconds=request["usage"].get("seconds"))
    if record.get("error"):
        return _reply(request, "HOLD", "BUDGET_RECORD_INVALID")
    if record["state"] == "DRAINING":
        return _checkpoint_reply(request, target, config, governance_dir, "BUDGET_LIMIT_REACHED")

    state = _snapshot(artifact)
    if action == "admit":
        plan = _short_plan(root, goal, packages, direct_repair)
        if plan["state"] in ("AWAIT_CONTRACT", "CONTRACT_CHANGED", "HOLD"):
            return _reply(request, "HOLD", "PLAN_GATE_CHANGED", **state, plan=plan)
        if awaiting_native_resume:
            stop["resumed_revision"] = request["revision"]
            bridge._save(target, artifact)
        attested = {"direct_repair_attested": True} if direct_repair else {}
        if direct_error:
            attested["direct_repair_code"] = "DIRECT_REPAIR_EVIDENCE_INVALID"
        return _reply(request, "ALLOW", "ADMITTED", **state, plan=plan, **attested)
    verdict = bridge._check_completion(goal, governance_dir)
    if not verdict["pass"]:
        return _reply(request, "HOLD", "DELIVERY_ACCEPTANCE_FAILED", **state,
                      acceptance_state=verdict["state"])
    if artifact["obligations"]:
        return _reply(request, "HOLD", "OPEN_OBLIGATIONS", **state, acceptance_state=verdict["state"])
    if _active_goal_work(governance_dir, request, artifact["task_ref"]):
        return _reply(request, "HOLD", "ACTIVE_GOAL_WORK", **state, acceptance_state=verdict["state"])
    return _reply(request, "ALLOW", "DELIVERY_ACCEPTED", **state, acceptance_state=verdict["state"])


def run(root, request):
    try:
        gov = root / ".governance"
        if not _optional_path(gov, directory=True):
            return _reply(request, "NOT_CONFIGURED", "NO_PROFILE")
        target = bridge._artifact_path(gov, request["goal_id"])
        if _optional_path(target.parent, directory=True):
            locks = target.parent / LOCK_DIR_NAME
            if _optional_path(locks, directory=True):
                _optional_path(locks / (target.name + ".lock"))
        profile_exists = _optional_path(root / PROFILE)
        state_exists = _optional_path(target)
        if not profile_exists:
            if state_exists:
                artifact, error = bridge._load_artifact(target, request["goal_id"], bridge.DEFAULT_BUDGET_CONFIG)
                if error:
                    return _reply(request, "HOLD", "STATE_INVALID")
                if "native_dsh" in artifact:
                    return _reply(request, "HOLD", "CONFIG_MISSING")
            return _reply(request, "NOT_CONFIGURED", "NO_PROFILE")
        if not state_exists and request["action"] != "admit":
            return _reply(request, "HOLD", "NATIVE_BINDING_REQUIRED")
        with _TargetLock(target):
            return _run_locked(root, target, request)
    except StoreError as exc:
        code = "LOCK_CONTENTION" if exc.payload.get("code") == "lock_contention" else "GOVERNANCE_RECORD_INVALID"
        return _reply(request, "HOLD", code)
    except (OSError, ValueError, RecursionError, OverflowError):
        return _reply(request, "HOLD", "GOVERNANCE_RECORD_INVALID")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if not args.project_root.is_absolute():
            raise ValueError("project root must be absolute")
        root = args.project_root.resolve(strict=True)
        if not root.is_dir():
            raise ValueError("project root must be a directory")
        request = _request(sys.stdin.buffer)
    except (OSError, ValueError, RecursionError, OverflowError):
        print(json.dumps(_reply(None, "HOLD", "INVALID_REQUEST")))
        return 2
    verdict = run(root, request)
    print(json.dumps(verdict, allow_nan=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
