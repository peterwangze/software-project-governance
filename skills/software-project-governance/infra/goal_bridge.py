"""FEAT-097 — goal 与预算桥接 (goal↔budget bridge).

RPG session 实测 (报告 §3.1/§3.8): goal 60 轮 6h 撞线 blocked 后静默
续跑 21 轮、38h 仅 2 次 ask — the intent break (意图断层) between the
harness goal mechanism and the governance budget.  This module BRIDGES
the two (it never replaces the harness goal — non_goal):

  ① 状态映射 — ``RUNNING → DRAINING → CHECKPOINTED → BLOCKED`` as a
     DATA table (:data:`STATE_TRANSITIONS`, grep-able via
     :func:`render_mapping_text`); the harness goal state is an INPUT,
     the governance state is the bridge's own projection;
  ② 多维权预算危险区收口 — four dimensions (轮次 rounds / token /
     墙钟 wall clock / 成本 cost), each ``{limit, warn_ratio,
     danger_ratio}`` config data (assumption_record 首轮保守值: rounds
     70% / tokens 70% / 墙钟与成本按基线倍数 1.5×); ANY dimension
     entering its danger zone collects the goal (DRAINING, then
     CHECKPOINTED) — the old 70%-rounds-only trigger was necessary but
     NOT sufficient (it watched one dimension and let the other three
     blow through);
  ③ checkpoint 工件 — ``.governance/goal-bridge/<goal_id>.json``
     carrying 账本 (authority-ledger best-effort summary) + 义务
     (obligations) + 修订 (revision) + 规则版本 (rules_version) + 预算
     消耗 (per-dimension usage); cross-session recovery is idempotent;
     a resume under a DIFFERENT rules version is LOUD (disclosure +
     history row — mid-session hot upgrade stays forbidden per
     DEC-330, and a mixed version can never pass silently);
  ④ blocked 后禁未授权续跑 — every execution/resume attempt from
     BLOCKED without a recorded user ruling is REFUSED and appended to
     ``unauthorized_attempts`` (fault injection: 未授权新增执行 = 0);
     CHECKPOINTED likewise refuses execution until a scope ruling is
     recorded — the ambition-infeasible case MUST bring the ruling to
     the user (禁静默续跑).

Boundaries (non_goals): no harness-goal replacement (mapping only), no
mid-session hot upgrade (rules changes take effect via checkpoint + a
NEW session), no FEAT-095 six-boundary enforcement face (this module
SUPPLIES state mapping + budget signals; the resume-authorization
check rides inside boundary ⑥ as a protocol+CLI gate).

Rollback (execution-packet rollback_plan): ``GOVERNANCE_GOAL_BRIDGE=off``
disables the bridge gate — ``record_execution`` degrades to a
pass-through (legacy harness-goal behavior, zero state writes).

Composition root: the engine (verify_workflow.py) wires dispatch only
(RISK-039 thin-entry discipline); this module keeps its own parser +
``main``.  stdlib-only at import time (authority_ledger is imported
function-locally for the checkpoint's ledger face — the authority_ledger
peer-leaf pattern).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import time
from pathlib import Path

__all__ = [
    "CODE_BLOCKED",
    "CODE_DRAINING",
    "CODE_ILLEGAL_TRANSITION",
    "CODE_SCOPE_RULING_REQUIRED",
    "CODE_SCHEMA_VIOLATION",
    "CODE_UNAUTHORIZED_RESUME",
    "DEFAULT_BUDGET_CONFIG",
    "DISABLE_ENV_VAR",
    "STATES",
    "STATE_TRANSITIONS",
    "add_goal_bridge_arguments",
    "bind_intent",
    "build_parser",
    "cmd_goal_bridge",
    "goal_status",
    "judge_budget",
    "main",
    "record_execution",
    "record_ruling",
    "render_mapping_text",
    "render_status_text",
    "render_thresholds_text",
    "write_checkpoint",
]

# ── constants ────────────────────────────────────────────────────────────────

GOVERNANCE_DIR_NAME = ".governance"
STATE_DIR_NAME = "goal-bridge"

#: Rollback switch (execution-packet rollback_plan): any of these values
#: disables the bridge gate (pass-through, zero state writes).
DISABLE_ENV_VAR = "GOVERNANCE_GOAL_BRIDGE"
_DISABLE_VALUES = {"off", "disabled", "0", "false", "no"}

#: The governed goal states (① 状态映射 vocabulary — closed set).
STATES = ("RUNNING", "DRAINING", "CHECKPOINTED", "BLOCKED")

#: The state-transition table — DATA, not code forks (assumption_record:
#: 映射与阈值=配置面数据，调整不动状态机).  Greppable via
#: :func:`render_mapping_text`.
STATE_TRANSITIONS = {
    ("RUNNING", "danger_zone"): "DRAINING",
    ("RUNNING", "block_decision"): "BLOCKED",
    ("DRAINING", "drained"): "CHECKPOINTED",
    ("DRAINING", "danger_zone"): "CHECKPOINTED",
    ("CHECKPOINTED", "scope_ruling"): "RUNNING",
    ("CHECKPOINTED", "block_decision"): "BLOCKED",
    ("BLOCKED", "authorized_resume"): "RUNNING",
}

#: ② 多维权预算危险区阈值 — 首轮保守值 (assumption_record: 轮次 70% /
#: token 70% / 墙钟与成本按基线倍数 1.5×).  Config DATA: callers may
#: pass a custom table (``new_limits`` patches ``limit`` only); the
#: state machine never branches on which dimension fired.
DEFAULT_BUDGET_CONFIG = {
    "rounds": {"limit": 60, "warn_ratio": 0.60, "danger_ratio": 0.70},
    "tokens": {"limit": 2_000_000, "warn_ratio": 0.60,
               "danger_ratio": 0.70},
    "wall_clock": {"limit": 21_600, "warn_ratio": 1.00,
                   "danger_ratio": 1.50},   # 6h baseline × 1.5
    "cost": {"limit": 100, "warn_ratio": 1.00, "danger_ratio": 1.50},
}

#: Dimension CLI spellings (``--rounds`` feeds ``rounds`` etc.).
DIMENSION_FIELDS = {
    "rounds": ("rounds", int),
    "tokens": ("tokens", int),
    "wall_clock": ("seconds", float),
    "cost": ("cost", float),
}

#: ④ 续跑授权与范围裁决词表 (closed sets).
RULING_DECISIONS = ("reduce-scope", "extend-budget", "continue", "abort")
AUTHORIZED_DECISIONS = ("reduce-scope", "extend-budget", "continue")

#: ③ CHECKPOINTED 呈现的范围裁决选项 (禁静默续跑 — the presentation
#: MUST carry these to the user; ux quality budget).
SCOPE_RULING_OPTIONS = (
    {"id": "reduce-scope",
     "description": "缩小目标范围：把不可行的野心裁剪为可行子集，"
                    "剩余部分拆票后续执行"},
    {"id": "extend-budget",
     "description": "扩预算续跑：提高轮次/token/墙钟/成本上限，"
                    "需明示新预算与理由"},
    {"id": "continue",
     "description": "按现预算继续（已确认风险：可能再次收口）"},
    {"id": "abort",
     "description": "终止目标：进入 BLOCKED，未授权不再续跑"},
)

#: The ask contract carried by every CHECKPOINTED presentation.
ASK_CONTRACT = {
    "must_ask": True,
    "channel": "AskUserQuestion",
    "rule": "预算入危险区即收口为 CHECKPOINTED 并 MUST 带范围裁决回用户"
            "（禁静默续跑——意图断层修复，FEAT-097）",
}

#: Closed error-code vocabulary with disposition classes (plain-dict
#: mirror of the contracts closed-enum discipline — same caliber as
#: execution_isolation).
CODE_SCHEMA_VIOLATION = "schema_violation"
CODE_DRAINING = "draining_new_work_refused"
CODE_SCOPE_RULING_REQUIRED = "scope_ruling_required"
CODE_BLOCKED = "blocked_unauthorized"
CODE_UNAUTHORIZED_RESUME = "unauthorized_resume"
CODE_ILLEGAL_TRANSITION = "illegal_transition"
CODE_LOCK_CONTENTION = "lock_contention"
ERROR_DISPOSITIONS = {
    CODE_SCHEMA_VIOLATION: "validation",
    CODE_DRAINING: "conflict",
    CODE_SCOPE_RULING_REQUIRED: "conflict",
    CODE_BLOCKED: "conflict",
    CODE_UNAUTHORIZED_RESUME: "conflict",
    CODE_ILLEGAL_TRANSITION: "validation",
    CODE_LOCK_CONTENTION: "retryable",
}

_GOAL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_INTENT_FIELDS = ("original_intent", "intent_sha256", "contract_sha256")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")

_MAX_HISTORY = 100
_MAX_UNAUTHORIZED = 200

ARTIFACT_SCHEMA_VERSION = 1


# ── small helpers ───────────────────────────────────────────────────────────


def bridge_disabled() -> bool:
    """True when the bridge gate is switched off (rollback face)."""
    for name in (DISABLE_ENV_VAR, DISABLE_ENV_VAR + "_DISABLED"):
        raw = (os.environ.get(name) or "").strip().lower()
        if raw in _DISABLE_VALUES:
            return True
        if name.endswith("_DISABLED") and raw == "1":
            return True
    return False


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _error(code, detail, **extra):
    result = {"error": True, "code": code,
              "disposition": ERROR_DISPOSITIONS[code], "detail": detail}
    result.update(extra)
    return result


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    handle, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(handle, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _write_json(path: Path, payload) -> None:
    _atomic_write_bytes(
        path, (json.dumps(payload, ensure_ascii=False, indent=2)
               + "\n").encode("utf-8"))


def _artifact_path(governance_dir, goal_id, state_dir=None) -> Path:
    base = Path(state_dir) if state_dir is not None \
        else Path(governance_dir) / STATE_DIR_NAME
    return base / ("{0}.json".format(goal_id))


def _require_goal_id(goal_id):
    goal_id = str(goal_id or "").strip()
    if not _GOAL_ID_RE.match(goal_id):
        return None
    return goal_id


def _default_rules_version() -> str:
    """The plugin's own skill version (checkpoint 规则版本 face).

    Read from the SKILL.md frontmatter next to this module (the live
    key is ``metadata.version``; historical ``version`` and checkpoint-only
    ``active_version`` are supported); unreadable → ``"unknown"`` (disclosed, never
    fabricated)."""
    skill = Path(__file__).resolve().parents[1] / "SKILL.md"
    from resolve_entry import read_skill_version
    return read_skill_version(skill, allow_active_version=True) or "unknown"


def _ledger_summary(governance_dir):
    """Best-effort 账本 face (③): the authority ledger's real status
    keys.  authority_ledger is imported FUNCTION-LOCALLY (the peer-leaf
    pattern — the bridge stays stdlib-only at import time); an
    absent/unreadable ledger is DISCLOSED, never faked.

    P2-3 (review R0): the keys below are the ones ``authority_ledger.
    status`` actually returns (``integrity.lines`` / ``integrity.
    last_seq`` / ``integrity.ok`` — ``status`` has NO ``events_total``
    key; the earlier spelling was a hallucinated constant-null)."""
    try:
        from authority_ledger import status as ledger_status
    except Exception:  # noqa: BLE001 — absence is a disclosed state
        return {"available": False,
                "note": "authority_ledger not importable — checkpoint "
                        "carries no ledger face"}
    try:
        summary = ledger_status(governance_dir)
    except Exception as exc:  # noqa: BLE001 — best-effort face
        return {"available": False, "note": "ledger status failed: {0}"
                                             .format(exc)}
    integrity = summary.get("integrity", {})
    return {
        "available": True,
        "events_lines": integrity.get("lines"),
        "last_seq": integrity.get("last_seq"),
        "integrity_ok": integrity.get("ok"),
        "open_recheck_obligations":
            summary.get("open_recheck_obligations"),
        "open_recheck_obligation_keys":
            summary.get("open_recheck_obligation_keys", []),
    }


# ── ② budget judgment (pure, ≤10ms budget face) ────────────────────────────


def judge_budget(*, rounds=0, tokens=0, seconds=0.0, cost=0.0,
                 config=None) -> dict:
    """Pure multi-dimension budget classification (no I/O).

    Returns per-dimension zones + ``any_danger`` + the recommended
    transition FROM RUNNING (``("RUNNING", "DRAINING")`` when any
    dimension is in its danger zone, else ``None``).  70%-rounds alone
    is necessary but NOT sufficient: only a DANGER zone (any dimension)
    collects — a warning band is a disclosed signal, never a trigger.
    """
    config = config or DEFAULT_BUDGET_CONFIG
    usage = {"rounds": float(rounds or 0), "tokens": float(tokens or 0),
             "wall_clock": float(seconds or 0.0),
             "cost": float(cost or 0.0)}
    zones = {}
    any_danger = False
    for dimension in ("rounds", "tokens", "wall_clock", "cost"):
        spec = config.get(dimension)
        if not isinstance(spec, dict):
            continue
        limit = float(spec.get("limit", 0) or 0)
        if limit <= 0:
            continue
        share = usage[dimension] / limit
        if share >= float(spec.get("danger_ratio", 1.0)):
            zone = "danger"
            any_danger = True
        elif share >= float(spec.get("warn_ratio", 1.0)):
            zone = "warning"
        else:
            zone = "safe"
        zones[dimension] = {
            "used": usage[dimension], "limit": limit,
            "share": round(share, 4), "zone": zone,
        }
    return {
        "zones": zones,
        "any_danger": any_danger,
        "recommended_transition":
            ("RUNNING", "DRAINING") if any_danger else None,
        "judged_at": _now_iso(),
    }


def render_thresholds_text(config=None) -> str:
    """Grep-anchor rendering of the danger-zone thresholds."""
    config = config or DEFAULT_BUDGET_CONFIG
    lines = ["# FEAT-097 goal-bridge danger-zone thresholds "
             "(config data — 调整不动状态机)"]
    for dimension in ("rounds", "tokens", "wall_clock", "cost"):
        spec = config.get(dimension, {})
        lines.append(
            "dimension={0} limit={1} warn_ratio={2} danger_ratio={3}"
            .format(dimension, spec.get("limit"),
                    spec.get("warn_ratio"), spec.get("danger_ratio")))
    lines.append("rule=any-dimension-danger -> DRAINING (收口); "
                 "warning=signal-only")
    return "\n".join(lines) + "\n"


def _budget_number(value, label, *, integral=False, positive=False):
    try:
        valid = (type(value) in (int, float) and math.isfinite(value)
                 and (value > 0 if positive else value >= 0)
                 and (not integral or value == int(value)))
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f"invalid budget value for {label}: expected a finite "
                         "nonnegative measurement or a positive limit")
    return value


def _bound_usage(artifact):
    consumption = artifact["budget_consumption"]
    if not isinstance(consumption, dict):
        raise ValueError("invalid budget_consumption")
    used = {}
    for dimension, record in consumption.items():
        if dimension not in artifact["budget_config"] or not isinstance(record, dict):
            raise ValueError(f"invalid budget dimension: {dimension!r}")
        used[dimension] = _budget_number(
            record.get("used"), dimension, integral=DIMENSION_FIELDS[dimension][1] is int)
    return used


def _judge_bound_usage(used, config):
    judged = judge_budget(**{DIMENSION_FIELDS[key][0]: value for key, value in used.items()},
                          config=config)
    zones = {}
    for key, value in used.items():
        zone = judged["zones"][key]
        _budget_number(zone["share"], f"{key} share")
        danger_at = float(config[key]["limit"]) * float(config[key]["danger_ratio"])
        zones[key] = {**zone, "used": value, "remaining_until_danger": max(0, danger_at - value)}
    judged["zones"] = zones
    return judged


def _intent_fields(intent, contract_sha256):
    if not isinstance(intent, str) or not intent.strip():
        raise ValueError("original intent must be nonempty text")
    if not isinstance(contract_sha256, str) or not _SHA256_RE.fullmatch(contract_sha256):
        raise ValueError("invalid delivery contract SHA-256")
    return {"original_intent": intent,
            "intent_sha256": hashlib.sha256(intent.encode("utf-8")).hexdigest(),
            "contract_sha256": contract_sha256}


def _validate_obligations(obligations):
    if not isinstance(obligations, list) or any(
        not isinstance(item, dict) or not isinstance(item.get("obligation_id"), str)
        or not item["obligation_id"].strip() for item in obligations
    ):
        raise ValueError("obligations must be a list of records with nonempty obligation IDs")


def _valid_native_session_id(value):
    return (isinstance(value, str) and 0 < len(value) <= 256
            and value.isprintable() and value == value.strip())


def _valid_native_revision(value):
    return type(value) is int and 1 <= value < 2**53


def _validate_native_dsh(scope):
    if (not isinstance(scope, dict) or scope.keys() != {"session_id", "revision", "profile_sha256"}
            or not _valid_native_session_id(scope["session_id"])
            or not _valid_native_revision(scope["revision"])
            or not isinstance(scope["profile_sha256"], str)
            or not _SHA256_RE.fullmatch(scope["profile_sha256"])):
        raise ValueError("invalid DSH native goal binding")


def _validate_direct_work(work):
    if not isinstance(work, dict) or work.keys() != {
        "work_package_id", "criterion_id", "preflight_receipt_sha256",
    }:
        raise ValueError("invalid DSH direct work reference")
    for field in ("work_package_id", "criterion_id"):
        if not isinstance(work[field], str) or not _GOAL_ID_RE.fullmatch(work[field]):
            raise ValueError("invalid DSH direct work identity")
    fingerprint = work["preflight_receipt_sha256"]
    if not isinstance(fingerprint, str) or not _SHA256_RE.fullmatch(fingerprint):
        raise ValueError("invalid DSH direct work receipt SHA-256")


_TREE_COUNTS = {"sessions", "open_steps", "missing_sessions", "missing_usage", "flush_failures"}


def _validate_tree_observation(observation):
    if (not isinstance(observation, dict) or observation.keys() != _TREE_COUNTS
            or any(type(value) is not int or not 0 <= value < 2**53 for value in observation.values())
            or observation["sessions"] < 1):
        raise ValueError("invalid DSH goal tree observation")


def _validate_tree_stop(stop):
    if (not isinstance(stop, dict)
            or stop.keys() not in ({"id", "revision", "status", "dimensions", "observation"},
                                   {"id", "revision", "status", "dimensions", "observation", "resumed_revision"})
            or not isinstance(stop["id"], str) or not re.fullmatch(r"[0-9a-f]{32}", stop["id"])
            or not _valid_native_revision(stop["revision"])
            or stop["status"] not in ("PENDING", "SETTLED", "INCOMPLETE")
            or stop["dimensions"] not in (["tokens"], ["wall_clock"], ["tokens", "wall_clock"])):
        raise ValueError("invalid DSH goal tree stop")
    if "resumed_revision" in stop and (stop["status"] == "PENDING"
            or not _valid_native_revision(stop["resumed_revision"]) or stop["resumed_revision"] <= stop["revision"]):
        raise ValueError("invalid DSH goal tree resume revision")
    _validate_tree_observation(stop["observation"])
    unknown = any(stop["observation"][name] for name in _TREE_COUNTS - {"sessions"})
    if ((stop["status"] == "SETTLED" and unknown)
            or (stop["status"] == "INCOMPLETE" and not unknown)):
        raise ValueError("tree settlement status disagrees with observation")


def _validate_bound_artifact(artifact):
    if type(artifact["revision"]) is not int or artifact["revision"] < 0:
        raise ValueError("invalid goal revision")
    if not isinstance(artifact["task_ref"], str) or not all(
        isinstance(artifact[key], list) for key in ("transition_history", "unauthorized_attempts")
    ):
        raise ValueError("invalid goal task reference or history")
    _validate_obligations(artifact["obligations"])
    config = artifact["budget_config"]
    if not isinstance(config, dict) or not config or config.keys() - DIMENSION_FIELDS.keys():
        raise ValueError("invalid goal budget configuration")
    _bound_usage(artifact)
    for dimension, spec in config.items():
        if not isinstance(spec, dict):
            raise ValueError(f"invalid budget configuration for {dimension}")
        limit = _budget_number(spec.get("limit"), dimension, positive=True)
        warn = _budget_number(spec.get("warn_ratio"), f"{dimension} warn_ratio")
        danger = _budget_number(spec.get("danger_ratio"), f"{dimension} danger_ratio")
        if danger <= warn:
            raise ValueError(f"danger ratio must exceed warning ratio for {dimension}")
        _budget_number(float(limit) * float(danger), f"{dimension} danger threshold", positive=True)


# ── artifact load/init ──────────────────────────────────────────────────────


def _new_artifact(goal_id, config) -> dict:
    return {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "goal_id": goal_id,
        "task_ref": "",
        "state": "RUNNING",
        "revision": 0,
        "rules_version": _default_rules_version(),
        "budget_config": json.loads(json.dumps(config)),
        "budget_consumption": {},
        "ledger": {"available": False},
        "obligations": [],
        "scope_ruling": None,
        "transition_history": [],
        "unauthorized_attempts": [],
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }


def _load_artifact(path: Path, goal_id, config):
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        if not path.is_symlink():
            return _new_artifact(goal_id, config), None
        return None, _error(CODE_SCHEMA_VIOLATION, f"checkpoint artifact link is unreadable: {exc}")
    except (OSError, ValueError, RecursionError) as exc:
        return None, _error(
            CODE_SCHEMA_VIOLATION,
            "checkpoint artifact unreadable ({0}): {1} — refusing "
            "fail-closed; fix or remove the file".format(path, exc))
    if not isinstance(loaded, dict) or loaded.get("goal_id") != goal_id:
        return None, _error(
            CODE_SCHEMA_VIOLATION,
            "checkpoint artifact at {0} is not goal {1!r} — refusing "
            "fail-closed".format(path, goal_id))
    if loaded.get("state") not in STATES:
        return None, _error(
            CODE_SCHEMA_VIOLATION,
            "checkpoint artifact carries unknown state {0!r} (closed "
            "set: {1})".format(loaded.get("state"), list(STATES)))
    artifact = _new_artifact(goal_id,
                             loaded.get("budget_config") or config)
    for key in ("task_ref", "state", "revision", "rules_version",
                "budget_config", "budget_consumption", "ledger",
                "obligations", "scope_ruling", "transition_history",
                "unauthorized_attempts", "created_at"):
        if key in loaded:
            artifact[key] = loaded[key]
    if any(key in loaded for key in (*_INTENT_FIELDS, "native_dsh", "tree_stop", "direct_work")):
        try:
            if type(loaded.get("schema_version")) is not int or loaded["schema_version"] != ARTIFACT_SCHEMA_VERSION:
                raise ValueError("invalid goal artifact schema version")
            if artifact.keys() - loaded.keys():
                raise ValueError("bound goal artifact is missing required state fields")
            fields = _intent_fields(loaded.get("original_intent"), loaded.get("contract_sha256"))
            if fields["intent_sha256"] != loaded.get("intent_sha256"):
                raise ValueError("original intent SHA-256 mismatch")
            saved_checkpoint = loaded.get("checkpoint_materialized")
            if type(saved_checkpoint) is not bool:
                raise ValueError("invalid checkpoint_materialized flag")
            _validate_bound_artifact(artifact)
            if "native_dsh" in loaded:
                _validate_native_dsh(loaded["native_dsh"])
                artifact["native_dsh"] = loaded["native_dsh"]
            if "direct_work" in loaded:
                if "native_dsh" not in artifact:
                    raise ValueError("direct work requires a native goal binding")
                _validate_direct_work(loaded["direct_work"])
                artifact["direct_work"] = loaded["direct_work"]
            if "tree_stop" in loaded:
                stop = loaded["tree_stop"]
                _validate_tree_stop(stop)
                if ("native_dsh" not in artifact
                        or stop.get("resumed_revision", stop["revision"]) > artifact["native_dsh"]["revision"]
                        or (stop["status"] == "PENDING" and artifact["state"] == "RUNNING")):
                    raise ValueError("tree stop does not match native goal state")
                artifact["tree_stop"] = stop
        except ValueError as exc:
            return None, _error(CODE_SCHEMA_VIOLATION, f"invalid bound goal artifact: {exc}")
        artifact.update(fields)
        artifact["checkpoint_materialized"] = saved_checkpoint
    return artifact, None


def _trim(artifact) -> None:
    artifact["transition_history"] = \
        artifact["transition_history"][-_MAX_HISTORY:]
    artifact["unauthorized_attempts"] = \
        artifact["unauthorized_attempts"][-_MAX_UNAUTHORIZED:]


def _save(path: Path, artifact) -> None:
    artifact["updated_at"] = _now_iso()
    path.parent.mkdir(parents=True, exist_ok=True)
    _trim(artifact)
    _write_json(path, artifact)


def _current_contract_sha256(governance_dir, goal):
    from delivery_acceptance import contract_for_goal

    return contract_for_goal(Path(governance_dir).parent, goal)["contract_sha256"]


def bind_delivery_unit(governance_dir, goal, intent, contract, digest):
    """Use the native goal identity and the independently verifiable delivery criteria."""
    from loop_workflow import start

    if contract["goal_id"] != goal:
        raise ValueError("delivery contract belongs to a different goal")
    criteria = "\n".join(f"{key}: {label}" for key, label in sorted(contract["criteria"].items()))
    return start(Path(governance_dir).parent, unit_id=goal, task=goal, goal=intent,
                 acceptance=criteria, tier="middle", gate="G9", delivery_goal=goal,
                 delivery_contract_sha256=digest)


def bind_intent(goal_id, *, intent, governance_dir, state_dir=None, timeout_seconds=10.0):
    """Freeze the exact user intent and current delivery contract for this goal."""
    if bridge_disabled():
        return _error(CODE_SCHEMA_VIOLATION, "goal bridge is disabled; intent binding is unavailable",
                      gate_disabled=True)
    goal = _require_goal_id(goal_id)
    if goal is None:
        return _error(CODE_SCHEMA_VIOLATION, f"invalid goal_id: {goal_id!r}")
    from governance_store import StoreError, _TargetLock

    path = _artifact_path(governance_dir, goal, state_dir)
    try:
        with _TargetLock(path, timeout_seconds):
            artifact, err = _load_artifact(path, goal, DEFAULT_BUDGET_CONFIG)
            if err is not None:
                return err
            import delivery_acceptance as acceptance

            project_root = Path(governance_dir).parent
            contract, digest = acceptance._contract(acceptance._project_path(project_root, acceptance.CONTRACT))
            fields = _intent_fields(intent, digest)
            already_bound = "intent_sha256" in artifact
            if already_bound:
                if any(artifact[key] != fields[key] for key in _INTENT_FIELDS):
                    return _error(CODE_SCHEMA_VIOLATION,
                                  "goal intent or contract changed; bind an explicitly new goal")
            if not already_bound:
                _validate_bound_artifact(artifact)
            unit = bind_delivery_unit(governance_dir, goal, intent, contract, digest)
            if not already_bound:
                artifact.update(fields)
                artifact["checkpoint_materialized"] = artifact["state"] in ("CHECKPOINTED", "BLOCKED")
                _save(path, artifact)
            return {"goal_id": goal, "unit_id": unit["flow_unit_id"], "state": artifact["state"],
                    "revision": artifact["revision"], "idempotent": already_bound, **fields}
    except StoreError as exc:
        return _error(CODE_LOCK_CONTENTION,
                      f"goal artifact lock busy: {exc.payload.get('detail', str(exc))}")
    except (OSError, ValueError) as exc:
        return _error(CODE_SCHEMA_VIOLATION, f"cannot bind goal intent: {exc}")


def _transition(artifact, trigger, *, note="") -> str:
    """Apply the DATA-table transition (fail-closed on unknown edges)."""
    edge = (artifact["state"], trigger)
    target = STATE_TRANSITIONS.get(edge)
    if target is None:
        raise LookupError(edge)
    artifact["transition_history"].append({
        "from": artifact["state"], "to": target,
        "trigger": trigger, "at": _now_iso(), "note": note,
    })
    artifact["state"] = target
    return target


# ── ①/②/④ the gate: record execution ─────────────────────────────────────


def _rules_version_disclosure(artifact) -> bool:
    """P2-2 (review R0): loud rules-version comparison on EVERY mutating
    path (record included, not just rulings).  A mismatch appends a
    ``rules_version_changed`` history row and re-pins the stored version
    — disclosure, never blocking (DEC-330: rules changes take effect via
    checkpoint + a NEW session, and a mixed version can never pass
    silently).  Returns True when a disclosure row was added."""
    current = _default_rules_version()
    if current == artifact["rules_version"]:
        return False
    artifact["transition_history"].append({
        "from": artifact["state"], "to": artifact["state"],
        "trigger": "rules_version_changed", "at": _now_iso(),
        "note": "{0} -> {1} (loud disclosure — mid-session hot upgrade "
                "stays forbidden, DEC-330; rules changes take effect "
                "via checkpoint + a NEW session)".format(
                    artifact["rules_version"], current),
        "rules_version_changed": True,
    })
    artifact["rules_version"] = current
    return True


def record_execution(goal_id, *, rounds=None, tokens=None, seconds=None,
                     cost=None, in_flight=False, task_ref="", governance_dir,
                     state_dir=None, config=None,
                     timeout_seconds=10.0) -> dict:
    """Record one execution attempt + fresh usage measurements — the
    ④ gate face (called before/with every round of new work).

    RUNNING: allowed; judge refreshes zones and auto-transitions to
    DRAINING the moment ANY dimension enters its danger zone (the
    triggering round itself completes — 收口 begins with the NEXT new
    work).
    DRAINING: in-flight continuation allowed; NEW work refused
    (checkpoint next).  Persistent danger on an in-flight record
    transitions to CHECKPOINTED.
    CHECKPOINTED: refused until a scope ruling is recorded
    (禁静默续跑).
    BLOCKED: refused and AUDITED (未授权新增执行 = 0 by construction —
    the gate never returns allowed=True without authorization).

    P1-1 (review R0): the whole load→mutate→save runs under the
    artifact's ``governance_store._TargetLock`` protocol lock — a
    racing writer can never interleave its stale snapshot between this
    read and write (function-local import keeps the R6 cold face at
    208; per-goal lock ⇒ zero contention).
    """
    if bridge_disabled():
        return {"goal_id": str(goal_id or ""), "allowed": True,
                "gate_disabled": True,
                "note": "goal bridge disabled ({0}) — legacy harness "
                        "goal behavior".format(DISABLE_ENV_VAR)}
    goal = _require_goal_id(goal_id)
    if goal is None:
        return _error(CODE_SCHEMA_VIOLATION,
                      "goal_id must match [A-Za-z0-9][A-Za-z0-9._-]* "
                      "(got {0!r})".format(goal_id))
    path = _artifact_path(governance_dir, goal, state_dir)
    from governance_store import StoreError, _TargetLock
    try:
        with _TargetLock(path, timeout_seconds):
            return _record_execution_locked(
                goal, path, rounds=rounds, tokens=tokens,
                seconds=seconds, cost=cost, in_flight=in_flight,
                task_ref=task_ref, governance_dir=governance_dir, config=config)
    except StoreError as exc:
        return _error(
            CODE_LOCK_CONTENTION,
            "goal artifact lock busy ({0}) — retry the same operation "
            "(transient, disposition retryable)".format(
                exc.payload.get("detail", str(exc))))


def _record_execution_locked(goal, path, *, rounds, tokens, seconds,
                             cost, in_flight, task_ref, governance_dir, config, artifact=None):
    """P1-1: the record body — caller holds the artifact target lock."""
    if artifact is None:
        artifact, err = _load_artifact(path, goal, config or DEFAULT_BUDGET_CONFIG)
        if err is not None:
            return err
    _rules_version_disclosure(artifact)  # P2-2: loud on every path

    def refuse(code, kind):
        artifact["unauthorized_attempts"].append({
            "kind": kind, "state": artifact["state"],
            "at": _now_iso(), "in_flight": bool(in_flight),
        })
        _save(path, artifact)
        detail = {
            CODE_DRAINING: "收口中（DRAINING）：预算危险区已触发——新工作"
                           "被拒；完成在途任务后执行 checkpoint（"
                           "goal-bridge --action checkpoint）",
            CODE_SCOPE_RULING_REQUIRED:
                "已收口（CHECKPOINTED）：继续执行需先记录范围裁决"
                "（goal-bridge --action ruling --decision …）——"
                "禁静默续跑（FEAT-097 意图断层修复）",
            CODE_BLOCKED: "目标已 BLOCKED：未授权续跑被拒并已留痕——"
                          "恢复需用户裁决（--decision reduce-scope/"
                          "extend-budget --authorized-by …）",
        }[code]
        return _error(code, detail)

    bound = "intent_sha256" in artifact
    if bound:
        try:
            if not isinstance(task_ref, str) or (task_ref and not task_ref.strip()):
                raise ValueError("invalid task reference")
            used = _bound_usage(artifact)
            measurements = {"rounds": rounds, "tokens": tokens, "wall_clock": seconds, "cost": cost}
            for dimension, value in measurements.items():
                if value is not None:
                    if dimension not in artifact["budget_config"]:
                        raise ValueError(f"budget dimension is not configured: {dimension}")
                    measure = _budget_number(
                        value, dimension, integral=DIMENSION_FIELDS[dimension][1] is int)
                    used[dimension] = max(used.get(dimension, 0), measure)
            if not used:
                raise ValueError("bound goal has no budget measurements; record current usage first")
            judged = _judge_bound_usage(used, artifact["budget_config"])
        except ValueError as exc:
            return _error(CODE_SCHEMA_VIOLATION, str(exc))
    else:
        judged = judge_budget(rounds=rounds, tokens=tokens, seconds=seconds,
                              cost=cost, config=artifact["budget_config"])

    state = artifact["state"]
    if state == "DRAINING" and not in_flight:
        return refuse(CODE_DRAINING, "execution")
    if state == "CHECKPOINTED":
        return refuse(CODE_SCOPE_RULING_REQUIRED, "execution")
    if state == "BLOCKED":
        return refuse(CODE_BLOCKED, "execution")

    if bound and in_flight and task_ref and task_ref != artifact["task_ref"]:
        return _error(CODE_SCHEMA_VIOLATION, "in-flight task reference differs from the accepted task")
    if bound and state == "RUNNING":
        try:
            if _current_contract_sha256(governance_dir, goal) != artifact["contract_sha256"]:
                raise ValueError("contract changed; bind an explicitly new goal")
        except (OSError, ValueError) as exc:
            return _error(CODE_SCHEMA_VIOLATION, f"cannot start work for bound goal: {exc}")

    artifact["budget_consumption"] = judged["zones"]
    if bound and task_ref and not in_flight:
        artifact["task_ref"] = task_ref

    if state == "RUNNING":
        if judged["any_danger"]:
            danger_dims = sorted(d for d, z in judged["zones"].items()
                                 if z["zone"] == "danger")
            _transition(artifact, "danger_zone",
                        note="danger: {0}".format(",".join(danger_dims)))
            # the triggering round completes; the NEXT new work drains
            _save(path, artifact)
            return {"goal_id": goal, "allowed": True, "state": "DRAINING",
                    "collected": True, "danger_dimensions": danger_dims,
                    "ask_contract": ASK_CONTRACT,
                    "scope_ruling_options":
                        list(SCOPE_RULING_OPTIONS)}
        _save(path, artifact)
        return {"goal_id": goal, "allowed": True, "state": "RUNNING",
                "zones": judged["zones"]}

    if judged["any_danger"]:
        danger_dims = sorted(d for d, z in judged["zones"].items() if z["zone"] == "danger")
        _transition(artifact, "danger_zone",
                    note="persistent danger: {0}".format(",".join(danger_dims)))
        if bound:
            artifact["checkpoint_materialized"] = False
        _save(path, artifact)
        return {"goal_id": goal, "allowed": True,
                "state": "CHECKPOINTED", "collected": True,
                "danger_dimensions": danger_dims, "ask_contract": ASK_CONTRACT,
                "scope_ruling_options": list(SCOPE_RULING_OPTIONS)}
    _save(path, artifact)
    return {"goal_id": goal, "allowed": True, "state": "DRAINING"}


# ── ③ checkpoint ───────────────────────────────────────────────────────────


def write_checkpoint(goal_id, *, task_ref="", obligations=None,
                     governance_dir, state_dir=None, config=None,
                     rules_version=None, timeout_seconds=10.0) -> dict:
    """Materialize the CHECKPOINTED artifact (schema ③ faces).

    From RUNNING the mapping's linear chain applies (RUNNING →
    DRAINING → CHECKPOINTED — 收口 then drain); from DRAINING the
    ``drained`` edge applies; an ALREADY-CHECKPOINTED goal is an
    idempotent face refresh (faces update, no new history row, no
    revision bump — 重复恢复状态一致).

    P1-1 (review R0): the whole load→mutate→save runs under the
    artifact's ``_TargetLock`` protocol lock (see record_execution).
    """
    goal = _require_goal_id(goal_id)
    if goal is None:
        return _error(CODE_SCHEMA_VIOLATION,
                      "goal_id must match [A-Za-z0-9][A-Za-z0-9._-]* "
                      "(got {0!r})".format(goal_id))
    path = _artifact_path(governance_dir, goal, state_dir)
    from governance_store import StoreError, _TargetLock
    try:
        with _TargetLock(path, timeout_seconds):
            return _write_checkpoint_locked(
                goal, path, task_ref=task_ref, obligations=obligations,
                governance_dir=governance_dir, config=config,
                rules_version=rules_version)
    except StoreError as exc:
        return _error(
            CODE_LOCK_CONTENTION,
            "goal artifact lock busy ({0}) — retry the same operation "
            "(transient, disposition retryable)".format(
                exc.payload.get("detail", str(exc))))


def _write_checkpoint_locked(goal, path, *, task_ref, obligations,
                             governance_dir, config, rules_version, artifact=None):
    """P1-1: the checkpoint body — caller holds the artifact lock."""
    if artifact is None:
        artifact, err = _load_artifact(path, goal, config or DEFAULT_BUDGET_CONFIG)
        if err is not None:
            return err
    already = artifact["state"] == "CHECKPOINTED"
    bound = "intent_sha256" in artifact
    retry = (bound and artifact["state"] in ("CHECKPOINTED", "BLOCKED")
             and artifact["checkpoint_materialized"])
    if bound:
        try:
            if obligations is not None:
                obligations = list(obligations)
                _validate_obligations(obligations)
        except (TypeError, ValueError) as exc:
            return _error(CODE_SCHEMA_VIOLATION, str(exc))
        if retry and ((task_ref and task_ref != artifact["task_ref"])
                      or (obligations is not None and obligations != artifact["obligations"])):
            return _error(CODE_SCOPE_RULING_REQUIRED,
                          "checkpoint already saved with different task or obligations; "
                          "obtain an authorized resume before creating a new checkpoint")
    if not retry:
        if task_ref:
            artifact["task_ref"] = str(task_ref)
        if obligations is not None:
            artifact["obligations"] = list(obligations)
        artifact["ledger"] = _ledger_summary(governance_dir)
        if rules_version:
            artifact["rules_version"] = str(rules_version)
        if artifact["state"] == "RUNNING":
            _transition(artifact, "danger_zone", note="explicit checkpoint")
        if artifact["state"] == "DRAINING":
            _transition(artifact, "drained", note="explicit checkpoint")
        if bound or (artifact["state"] == "CHECKPOINTED" and not already):
            artifact["revision"] = int(artifact.get("revision", 0)) + 1
        if bound:
            artifact["checkpoint_materialized"] = True
        _save(path, artifact)
    return {
        "goal_id": goal,
        "state": artifact["state"],
        "revision": artifact["revision"],
        "artifact_path": str(path),
        "scope_ruling_options": list(SCOPE_RULING_OPTIONS),
        "ask_contract": ASK_CONTRACT,
        "budget_consumption": artifact["budget_consumption"],
    }


# ── ④ ruling / resume authorization ───────────────────────────────────────


def _apply_new_limits(artifact, new_limits):
    if not new_limits:
        return
    config = artifact["budget_config"]
    bound = "intent_sha256" in artifact
    if bound:
        if not isinstance(new_limits, dict) or new_limits.keys() - config.keys():
            raise ValueError("new budget limits must name configured dimensions")
        for dimension, limit in new_limits.items():
            _budget_number(limit, dimension,
                           integral=DIMENSION_FIELDS[dimension][1] is int, positive=True)
    for dimension, limit in new_limits.items():
        if dimension in config:
            config[dimension]["limit"] = limit
    if bound:
        _validate_bound_artifact(artifact)
        artifact["budget_consumption"] = _judge_bound_usage(_bound_usage(artifact), config)["zones"]


def record_ruling(goal_id, *, decision, authorized_by="",
                  new_limits=None, governance_dir, state_dir=None,
                  rules_version=None, timeout_seconds=10.0) -> dict:
    """Record a scope ruling (CHECKPOINTED) or an authorized resume
    (BLOCKED).  Without a recorded ruling every later execution/resume
    attempt stays refused (fault-injection face).

    P2-1 (review R0): authorization is SYMMETRIC — a RESUME-direction
    ruling (reduce-scope / extend-budget / continue) requires a
    non-empty ``authorized_by`` from CHECKPOINTED just as from BLOCKED
    (the option descriptions themselves promise user confirmation —
    禁静默续跑); only ``abort`` is exempt (the safe direction —
    resuming FROM abort still needs authorization).

    P1-1 (review R0): the whole load→mutate→save runs under the
    artifact's ``_TargetLock`` protocol lock (see record_execution).
    """
    goal = _require_goal_id(goal_id)
    if goal is None:
        return _error(CODE_SCHEMA_VIOLATION,
                      "goal_id must match [A-Za-z0-9][A-Za-z0-9._-]* "
                      "(got {0!r})".format(goal_id))
    decision = str(decision or "").strip()
    if decision not in RULING_DECISIONS:
        return _error(CODE_SCHEMA_VIOLATION,
                      "decision must be one of {0} (got {1!r})"
                      .format(list(RULING_DECISIONS), decision))
    path = _artifact_path(governance_dir, goal, state_dir)
    from governance_store import StoreError, _TargetLock
    try:
        with _TargetLock(path, timeout_seconds):
            return _record_ruling_locked(
                goal, path, decision=decision,
                authorized_by=authorized_by, new_limits=new_limits,
                rules_version=rules_version)
    except StoreError as exc:
        return _error(
            CODE_LOCK_CONTENTION,
            "goal artifact lock busy ({0}) — retry the same operation "
            "(transient, disposition retryable)".format(
                exc.payload.get("detail", str(exc))))


def _record_ruling_locked(goal, path, *, decision, authorized_by,
                          new_limits, rules_version):
    """P1-1: the ruling body — caller holds the artifact lock."""
    artifact, err = _load_artifact(path, goal, None)
    if err is not None:
        return err

    rules_changed = False
    if rules_version and str(rules_version) != artifact["rules_version"]:
        rules_changed = True

    state = artifact["state"]
    if decision != "abort" and artifact.get("tree_stop", {}).get("status") == "PENDING":
        return _error(CODE_SCOPE_RULING_REQUIRED, "finish recording the stopped DSH goal tree's settled tail")
    if "intent_sha256" in artifact and decision == "reduce-scope" and str(authorized_by or "").strip():
        return _error(CODE_SCHEMA_VIOLATION, "bound intent cannot change; bind an explicitly new goal")
    if state == "CHECKPOINTED":
        if (decision != "abort"
                and not str(authorized_by or "").strip()):
            # P2-1: resume-direction rulings need the user, exactly as
            # the BLOCKED face does (symmetric authorization).
            artifact["unauthorized_attempts"].append({
                "kind": "resume", "state": "CHECKPOINTED",
                "at": _now_iso(), "decision": decision,
            })
            _save(path, artifact)
            return _error(
                CODE_UNAUTHORIZED_RESUME,
                "CHECKPOINTED 恢复方向裁决（{0}）未获授权——authorized_by "
                "为空；范围裁决 MUST 经用户（AskUserQuestion 呈现四选项后"
                "带 --authorized-by 记录——禁静默续跑，与 BLOCKED 面对称；"
                "未授权尝试已留痕）".format(decision))
        if ("intent_sha256" in artifact and decision != "abort"
                and not artifact["checkpoint_materialized"]):
            return _error(CODE_SCOPE_RULING_REQUIRED,
                          "materialize the current checkpoint before resuming the goal")
        try:
            _apply_new_limits(artifact, new_limits)
        except ValueError as exc:
            return _error(CODE_SCHEMA_VIOLATION, str(exc))
        artifact["scope_ruling"] = {
            "decision": decision,
            "authorized_by": str(authorized_by or ""),
            "decided_at": _now_iso(),
            "new_limits": dict(new_limits or {}),
        }
        if decision == "abort":
            _transition(artifact, "block_decision",
                        note="user ruling: abort")
        else:
            _transition(artifact, "scope_ruling",
                        note="user ruling: {0}".format(decision))
            artifact["revision"] = int(artifact.get("revision", 0)) + 1
            if "intent_sha256" in artifact:
                artifact["checkpoint_materialized"] = False
        if rules_changed:
            artifact["transition_history"].append({
                "from": artifact["state"], "to": artifact["state"],
                "trigger": "rules_version_changed", "at": _now_iso(),
                "note": "{0} -> {1} (loud disclosure — mid-session hot "
                        "upgrade stays forbidden, DEC-330)".format(
                            artifact["rules_version"], rules_version),
                "rules_version_changed": True,
            })
            artifact["rules_version"] = str(rules_version)
        _save(path, artifact)
        return {"goal_id": goal, "state": artifact["state"],
                "decision": decision,
                "rules_version_changed": rules_changed,
                "revision": artifact["revision"]}

    if state == "BLOCKED":
        if (decision not in AUTHORIZED_DECISIONS
                or not str(authorized_by or "").strip()):
            artifact["unauthorized_attempts"].append({
                "kind": "resume", "state": "BLOCKED",
                "at": _now_iso(), "decision": decision,
            })
            _save(path, artifact)
            return _error(
                CODE_UNAUTHORIZED_RESUME,
                "BLOCKED 目标的续跑未获授权——decision={0!r} "
                "authorized_by={1!r}；合法路径：--decision "
                "reduce-scope/extend-budget --authorized-by <用户> "
                "（未授权尝试已留痕）".format(decision, authorized_by))
        if "intent_sha256" in artifact and not artifact["checkpoint_materialized"]:
            return _error(CODE_SCOPE_RULING_REQUIRED,
                          "materialize the current checkpoint before resuming the goal")
        try:
            _apply_new_limits(artifact, new_limits)
        except ValueError as exc:
            return _error(CODE_SCHEMA_VIOLATION, str(exc))
        artifact["scope_ruling"] = {
            "decision": decision,
            "authorized_by": str(authorized_by),
            "decided_at": _now_iso(),
            "new_limits": dict(new_limits or {}),
        }
        _transition(artifact, "authorized_resume",
                    note="user ruling: {0} by {1}".format(
                        decision, authorized_by))
        artifact["revision"] = int(artifact.get("revision", 0)) + 1
        if "intent_sha256" in artifact:
            artifact["checkpoint_materialized"] = False
        if rules_changed:
            artifact["transition_history"].append({
                "from": "RUNNING", "to": "RUNNING",
                "trigger": "rules_version_changed", "at": _now_iso(),
                "note": "{0} -> {1} (loud disclosure)".format(
                    artifact["rules_version"], rules_version),
                "rules_version_changed": True,
            })
            artifact["rules_version"] = str(rules_version)
        _save(path, artifact)
        return {"goal_id": goal, "state": "RUNNING",
                "decision": decision,
                "rules_version_changed": rules_changed,
                "revision": artifact["revision"]}

    return _error(
        CODE_ILLEGAL_TRANSITION,
        "goal {0!r} is {1} — a ruling applies to CHECKPOINTED (scope "
        "ruling) or BLOCKED (authorized resume) states only".format(
            goal, state))


# ── status / mapping faces ─────────────────────────────────────────────────


def goal_status(goal_id, *, governance_dir, state_dir=None,
                config=None) -> dict:
    """Machine-readable bridge state for one goal."""
    goal = _require_goal_id(goal_id)
    if goal is None:
        return _error(CODE_SCHEMA_VIOLATION,
                      "goal_id must match [A-Za-z0-9][A-Za-z0-9._-]* "
                      "(got {0!r})".format(goal_id))
    path = _artifact_path(governance_dir, goal, state_dir)
    artifact, err = _load_artifact(path, goal, config
                                   or DEFAULT_BUDGET_CONFIG)
    if err is not None:
        return err
    return _status_from_artifact(artifact)


def _status_from_artifact(artifact) -> dict:
    """Project a loaded or just-persisted goal artifact without rereading it."""
    result = {
        "goal_id": artifact["goal_id"],
        "state": artifact["state"],
        "revision": artifact["revision"],
        "rules_version": artifact["rules_version"],
        "task_ref": artifact["task_ref"],
        "zones": artifact["budget_consumption"],
        "scope_ruling": artifact["scope_ruling"],
        "open_unauthorized_attempts":
            len(artifact["unauthorized_attempts"]),
        "generated_at": _now_iso(),
    }
    if "intent_sha256" in artifact:
        try:
            used = _bound_usage(artifact)
            zones = _judge_bound_usage(used, artifact["budget_config"])["zones"]
        except ValueError as exc:
            return _error(CODE_SCHEMA_VIOLATION, str(exc))
        unmeasured = sorted(artifact["budget_config"].keys() - used.keys())
        signals = {zone["zone"] for zone in zones.values()}
        signal = "unknown" if unmeasured else "safe"
        for candidate in ("warning", "danger"):
            if candidate in signals:
                signal = candidate
        result.update({key: artifact[key] for key in _INTENT_FIELDS},
                      obligations=artifact["obligations"], zones=zones,
                      checkpoint_materialized=artifact["checkpoint_materialized"],
                      budget_signal=signal, unmeasured_dimensions=unmeasured)
        if "native_dsh" in artifact:
            result["native_dsh"] = artifact["native_dsh"]
        if "tree_stop" in artifact:
            result["tree_stop"] = artifact["tree_stop"]
        if "direct_work" in artifact:
            result["execution_packet"] = {"goal_id": artifact["goal_id"],
                                          "contract_sha256": artifact["contract_sha256"],
                                          **artifact["direct_work"]}
    return result


def render_status_text(status: dict) -> str:
    lines = ["state={0}".format(status.get("state")),
             "goal_id={0}".format(status.get("goal_id")),
             "revision={0}".format(status.get("revision")),
             "rules_version={0}".format(status.get("rules_version"))]
    for dimension in sorted(status.get("zones") or {}):
        zone = status["zones"][dimension]
        lines.append("dimension={0} used={1} limit={2} zone={3}".format(
            dimension, zone.get("used"), zone.get("limit"),
            zone.get("zone")))
    return "\n".join(lines) + "\n"


def render_mapping_text() -> str:
    """Grep-anchor rendering of the ① state-transition table."""
    lines = ["# FEAT-097 goal-bridge state mapping (data table)"]
    for (source, trigger), target in sorted(STATE_TRANSITIONS.items()):
        lines.append("{0} --{1}--> {2}".format(source, trigger, target))
    lines.append("rule=any-dimension-danger collects; blocked resume "
                 "requires an authorized ruling")
    return "\n".join(lines) + "\n"


# ── CLI (module composition root + engine thin-entry handler) ─────────────


def _configure_stdio() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 — best-effort console hygiene
        pass


def add_goal_bridge_arguments(parser: argparse.ArgumentParser) -> None:
    """Option fact source for ``goal-bridge`` (single definition shared
    by the module parser and the engine subparser)."""
    parser.add_argument("--action", required=True,
                        choices=("record", "checkpoint", "ruling",
                                 "status", "judge", "thresholds",
                                 "mapping", "check-completion", "bind-intent", "accept-delivery"))
    parser.add_argument("--goal", default="",
                        help="goal id ([A-Za-z0-9][A-Za-z0-9._-]*)")
    parser.add_argument("--intent", help="exact original user objective for bind-intent")
    parser.add_argument("--task", default="",
                        help="task ref stamped into the artifact")
    parser.add_argument("--rounds", type=int)
    parser.add_argument("--tokens", type=int)
    parser.add_argument("--seconds", type=float,
                        help="wall-clock seconds consumed")
    parser.add_argument("--cost", type=float)
    parser.add_argument("--in-flight", dest="in_flight",
                        action="store_true",
                        help="record tags an IN-FLIGHT continuation "
                             "(allowed while DRAINING)")
    parser.add_argument("--decision", default="",
                        help="scope ruling: reduce-scope / "
                             "extend-budget / continue / abort")
    parser.add_argument("--authorized-by", dest="authorized_by",
                        default="",
                        help="who authorized the ruling/resume (user)")
    parser.add_argument("--new-limit", dest="new_limits", default="",
                        help="comma list dimension=limit (e.g. "
                             "rounds=100,wall_clock=43200)")
    parser.add_argument("--rules-version", dest="rules_version",
                        default="")
    obligations = parser.add_mutually_exclusive_group()
    obligations.add_argument("--obligations", default="",
                             help="comma list of open obligation ids stamped into the checkpoint")
    obligations.add_argument("--clear-obligations", action="store_true",
                             help="checkpoint with an explicitly reconciled empty obligation list")
    parser.add_argument("--text", action="store_true",
                        help="grep-anchor text rendering (thresholds/"
                             "mapping/status)")


def _parse_new_limits(raw):
    limits = {}
    for item in str(raw or "").split(","):
        item = item.strip()
        if not item or "=" not in item:
            continue
        key, value = item.split("=", 1)
        try:
            limits[key.strip()] = float(value)
        except ValueError:
            continue
    return limits


def _emit(payload, *, refused=None) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if payload.get("error") or refused:
        return 2
    return 0


def _check_completion(goal_id, governance_dir):
    from delivery_acceptance import evaluate_delivery_acceptance

    verdict = evaluate_delivery_acceptance(Path(governance_dir).parent, goal_id=goal_id, required=True)
    if verdict["pass"]:
        goal = _require_goal_id(goal_id)
        if goal is None:
            return verdict  # a legacy P0 contract ID outside the bridge's bindable vocabulary
        artifact, err = _load_artifact(_artifact_path(governance_dir, goal), goal, DEFAULT_BUDGET_CONFIG)
        if err is not None:
            return {**err, "pass": False, "state": "FAIL"}
        if "contract_sha256" in artifact and artifact["contract_sha256"] != verdict["contract_sha256"]:
            return {**_error(CODE_SCHEMA_VIOLATION, "contract changed; bind an explicitly new goal"),
                    "pass": False, "state": "FAIL"}
    return verdict


def accept_bound_delivery(goal_id, governance_dir):
    """Close a non-DSH bound delivery under the same goal lock as its budget and obligations."""
    from governance_store import StoreError, _TargetLock
    from loop_workflow import accept_delivery
    from goal_planning import has_active_goal_work

    goal = _require_goal_id(goal_id)
    if not goal or bridge_disabled():
        return _error(CODE_SCHEMA_VIOLATION, "an enabled goal binding is required")
    path = _artifact_path(governance_dir, goal)
    try:
        with _TargetLock(path):
            artifact, error = _load_artifact(path, goal, DEFAULT_BUDGET_CONFIG)
            if error:
                return error
            if "native_dsh" in artifact:
                raise ValueError("complete this DSH goal through its native host")
            if "contract_sha256" not in artifact or artifact["state"] != "RUNNING" or artifact["obligations"]:
                raise ValueError("goal is unbound, paused, or has open obligations")
            if has_active_goal_work(Path(governance_dir), goal, artifact["task_ref"]):
                raise ValueError("goal has active work")

            return accept_delivery(Path(governance_dir).parent, goal)
    except (StoreError, OSError, ValueError) as exc:
        return _error(CODE_SCHEMA_VIOLATION, str(exc))


def cmd_goal_bridge(args, *, governance_dir) -> int:
    """Engine dispatch face — ``goal-bridge`` (all actions)."""
    _configure_stdio()
    action = getattr(args, "action", "status")
    goal = getattr(args, "goal", "") or ""
    clear_obligations = getattr(args, "clear_obligations", False)
    if clear_obligations and action != "checkpoint":
        return _emit(_error(CODE_SCHEMA_VIOLATION, "--clear-obligations requires --action checkpoint"))
    if action == "bind-intent":
        return _emit(bind_intent(goal, intent=getattr(args, "intent", None),
                                 governance_dir=governance_dir))
    if action == "accept-delivery":
        outcome = accept_bound_delivery(goal, governance_dir)
        return _emit(outcome, refused=outcome.get("decision") != "exit")
    if action == "check-completion":
        verdict = _check_completion(goal, governance_dir)
        return _emit(verdict, refused=not verdict["pass"])
    if action == "thresholds":
        if getattr(args, "text", False):
            print(render_thresholds_text(), end="")
            return 0
        return _emit({"config": DEFAULT_BUDGET_CONFIG})
    if action == "mapping":
        if getattr(args, "text", False):
            print(render_mapping_text(), end="")
            return 0
        return _emit({"transitions": {
            "{0}--{1}".format(k[0], k[1]): v for k, v in
            sorted(STATE_TRANSITIONS.items())}})
    if action == "judge":
        judged = judge_budget(
            rounds=getattr(args, "rounds", 0),
            tokens=getattr(args, "tokens", 0),
            seconds=getattr(args, "seconds", 0.0),
            cost=getattr(args, "cost", 0.0))
        return _emit(judged, refused=judged.get("any_danger"))
    if action == "record":
        return _emit(record_execution(
            goal, rounds=getattr(args, "rounds", None),
            tokens=getattr(args, "tokens", None),
            seconds=getattr(args, "seconds", None),
            cost=getattr(args, "cost", None),
            in_flight=bool(getattr(args, "in_flight", False)),
            task_ref=getattr(args, "task", ""),
            governance_dir=governance_dir),
            refused=False)
    if action == "checkpoint":
        obligations = [
            {"obligation_id": item.strip()}
            for item in str(getattr(args, "obligations", "")).split(",")
            if item.strip()]
        payload = write_checkpoint(
            goal, task_ref=getattr(args, "task", ""),
            obligations=[] if clear_obligations else obligations or None,
            governance_dir=governance_dir,
            rules_version=getattr(args, "rules_version", "") or None)
        return _emit(payload, refused=bool(payload.get("error")))
    if action == "ruling":
        payload = record_ruling(
            goal, decision=getattr(args, "decision", ""),
            authorized_by=getattr(args, "authorized_by", ""),
            new_limits=_parse_new_limits(
                getattr(args, "new_limits", "")),
            governance_dir=governance_dir,
            rules_version=getattr(args, "rules_version", "") or None)
        return _emit(payload, refused=bool(payload.get("error")))
    # status
    payload = goal_status(goal, governance_dir=governance_dir)
    if getattr(args, "text", False) and not payload.get("error"):
        print(render_status_text(payload), end="")
        return 0
    return _emit(payload)


def build_parser():
    """Module-owned composition root (the engine wires dispatch only)."""
    parser = argparse.ArgumentParser(
        prog="goal_bridge.py",
        description="FEAT-097 goal↔budget bridge — state mapping + "
                    "multi-dimension danger-zone collection + checkpoint "
                    "artifacts + resume authorization")
    parser.add_argument("--project-root", default=".",
                        help="host project root (default: cwd)")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("goal-bridge", help="the bridge CLI (all actions)")
    add_goal_bridge_arguments(p)
    return parser


def main(argv=None) -> int:
    """CLI entry — JSON on stdout; exit 0 ok / 2 refusal (fail-closed)."""
    _configure_stdio()
    args = build_parser().parse_args(argv)
    governance_dir = (Path(getattr(args, "project_root", ".") or ".")
                      / GOVERNANCE_DIR_NAME)
    return cmd_goal_bridge(args, governance_dir=governance_dir)


if __name__ == "__main__":
    sys.exit(main())
