"""FEAT-095 — 动作级执法（six-boundary layered enforcement）.

DEC-330 arch 联合裁定「检查必须影响执行权限否则 advisory 无效」——本模块把
检查输出转成**动作级分层执法判定**，供 Coordinator 在六边界动作前同步调用：

  边界（BOUNDARIES，六边界）：
    dispatch-execute（派发执行）/ dispatch-review（派发审查）/
    accept-completion（接受完成）/ merge（合并 commit/组装）/
    release（发布 tag/push）/ goal-resume（goal 续跑）

  三层策略（分层执法，策略表 STRATEGY 与执行器 decide() 分离——
  新增边界/规则/阈值改表不动执行器，见 test_new_boundary_via_table_only）：
    1. 硬阻断 HARD_BLOCK（四类零漏放）：revision-mismatch（修订错配）/
       unauthorized-write（未授权写入）/ duplicate-identity（重复身份）/
       unresolved-blocking-review（相关阻塞复审未闭合——仅修复/复审/取证
       白名单通道豁免，豁免本身是策略表数据 allowlist_exempt）；
    2. 限流升级 THROTTLE：审查债预算 = Σ min(severity,5) ×
       min(age_days,30)（未闭合义务按严重性×年龄），超阈限流新工作准入
       （dispatch-execute / goal-resume 两个 admission 面）；
    3. 提示重建 STALE_NOTICE：展示性冷面（gate/overview/TPA/risk touch
       时效）过期 → 非阻断提示重建（exit 4，动作仍放行）。

  铁边界（违反 = FAIL，均有守护测试）：
    * scoped 语义（DEC-357 口径）：硬阻断与未闭合复审按任务/通道
      scoped；审查债预算是全局新工作准入限流（仅 dispatch-execute /
      goal-resume 两 admission 面），白名单通道（fix/re-review/
      forensics）与用户裁定额度逃生门保留；非 admission 边界无
      限流面（DEC-330 发布验证底线之一为白名单通道不被误冻）；
    * commit 前不设卡：merge 边界 wip_checkpoint=True 始终放行
      （wip-checkpoint-carve-out，优先于一切硬阻断）；
    * 不改各 Check 判定语义：本模块只消费调用方提供的 facts（检查输出
      的投影），不做任何治理检查本身；
    * fail-closed：执法器自身异常（输入类型故障/未知边界/内部错误）→
      保守阻断并披露（reason_code=enforcement-fail-closed），非放行；
    * 零漂移开关：GOVERNANCE_ENFORCEMENT=off → advisory 基线
      （一切放行、零记录、零副作用）；非法值不猜 → 保守阻断披露。

  执法降级披露（M-0 调研结论，docs/research/
  feat-095-harness-enforcement-capability-2026-10-10.md §5-§7 U1-U7）：
  六平台均无已接线的宿主级拦截——本模块是**CLI 级判定面 +
  协议级（SKILL.md「动作级执法」契约段）**，不做任何宿主级拦截能力
  声明；绕过面 = 不调用本判定（RPG 实证 §3.4），协议面 MUST 补位。

  CLI 出口码（三态可区分 + 提示态）：0 = ALLOW；2 = HARD_BLOCK（含
  fail-closed）；3 = THROTTLE；4 = STALE_NOTICE（非阻断提示）。
  执法记录：JSONL 追加 <record-dir>/enforcement-log.jsonl，grep 锚点
  ENFORCEMENT-ACTION，含 decision/reason_code/reason/remedy（解除路径）。

  Composition root: verify_workflow.py 只接线派发（RISK-039 thin-entry
  纪律，goal_bridge/governance_cost 模式）；stdlib-only。
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

__all__ = [
    "ALLOWLIST_CHANNELS",
    "BOUNDARIES",
    "ENFORCEMENT_SWITCH_ENV",
    "EXIT_ALLOW",
    "EXIT_HARD_BLOCK",
    "EXIT_STALE_NOTICE",
    "EXIT_THROTTLE",
    "HARD_BLOCK_RULES",
    "RECORD_ANCHOR",
    "RECORD_FILENAME",
    "STRATEGY",
    "STALE_SURFACES",
    "EnforcementInputError",
    "add_enforcement_check_arguments",
    "build_parser",
    "cmd_enforcement_check",
    "decide",
    "main",
    "review_debt_points",
    "switch_state",
]

# ── 事实源常量（策略表原料——执行器只读不改） ─────────────────────────

BOUNDARIES = (
    "dispatch-execute",    # ① 派发执行
    "dispatch-review",     # ② 派发审查
    "accept-completion",   # ③ 接受完成
    "merge",               # ④ 合并 commit/组装
    "release",             # ⑤ 发布 tag/push
    "goal-resume",         # ⑥ goal 续跑
)

HARD_BLOCK_RULES = (
    "revision-mismatch",
    "unauthorized-write",
    "duplicate-identity",
    "unresolved-blocking-review",
)

ALLOWLIST_CHANNELS = ("fix", "re-review", "forensics")

STALE_SURFACES = ("gate", "overview", "tpa", "risk")

ENFORCEMENT_SWITCH_ENV = "GOVERNANCE_ENFORCEMENT"

RECORD_ANCHOR = "ENFORCEMENT-ACTION"
RECORD_FILENAME = "enforcement-log.jsonl"

EXIT_ALLOW = 0
EXIT_HARD_BLOCK = 2
EXIT_THROTTLE = 3
EXIT_STALE_NOTICE = 4

DECISION_ALLOW = "ALLOW"
DECISION_HARD_BLOCK = "HARD_BLOCK"
DECISION_THROTTLE = "THROTTLE"
DECISION_STALE_NOTICE = "STALE_NOTICE"

_MODE_ENFORCED = "enforced"
_MODE_ADVISORY = "advisory-baseline"

_SWITCH_OFF_WORDS = {"off", "0", "false", "disabled", "no"}
_SWITCH_ON_WORDS = {"on", "1", "true", "enabled", "yes"}


class EnforcementInputError(Exception):
    """Facts/strategy shape violation — the enforcer fails CLOSED on it."""


# ── 策略表（DATA——新增边界/规则/阈值改这里，不动执行器） ─────────────

_RULES = (
    {
        "id": "revision-mismatch",
        "allowlist_exempt": False,
        "reason": "dispatch targets revision {revision} but the governed "
                  "expected revision for {task_id} is {expected}",
        "remedy": "re-align the dispatch revision with the governed "
                  "expected revision (re-read hot facts via "
                  "governance-bootstrap, or advance the expected revision "
                  "through the governed writer first)",
    },
    {
        "id": "unauthorized-write",
        "allowlist_exempt": False,
        "reason": "actor {actor} is not authorized for write path(s) "
                  "{paths}",
        "remedy": "route the write through the agent holding the file "
                  "lock / authorized writer, or extend authorization via "
                  "the governed path first",
    },
    {
        "id": "duplicate-identity",
        "allowlist_exempt": False,
        "reason": "actor identity {actor} is already active",
        "remedy": "release the stale identity/lock (agent-locks release) "
                  "or dispatch under a unique identity",
    },
    {
        "id": "unresolved-blocking-review",
        # scoped 豁免是表数据：修复/复审/取证通道是闭合阻塞复审的路径，
        # 冻结它们会死锁 M7.4 T1 复审必达——白名单只豁免本规则与限流，
        # 不豁免其余硬阻断（修订错配的 re-review 派发仍被拒）。
        "allowlist_exempt": True,
        "reason": "task {task_id} has an unresolved blocking review",
        "remedy": "close the blocking review first (same-Reviewer "
                  "re-review round+1, behavior-protocol M7.4 T1); the "
                  "fix/re-review/forensics channels stay open",
    },
)

_ADMISSION_BOUNDARIES = ("dispatch-execute", "goal-resume")

STRATEGY = {
    "switch_env": ENFORCEMENT_SWITCH_ENV,
    "record_anchor": RECORD_ANCHOR,
    "record_filename": RECORD_FILENAME,
    "boundaries": {
        boundary: {
            "hard_block": True,
            "throttle": ("review-debt-budget"
                         if boundary in _ADMISSION_BOUNDARIES else None),
            "stale_notice": True,
        }
        for boundary in BOUNDARIES
    },
    "hard_block_rules": [dict(rule) for rule in _RULES],
    "thresholds": {"review_debt_budget": 100},
    "staleness_days": {surface: 7 for surface in STALE_SURFACES},
    "allowlist_channels": list(ALLOWLIST_CHANNELS),
    # commit 前不设卡：merge 边界的 WIP checkpoint 始终放行（铁边界，
    # 优先于一切硬阻断——执行器只消费本表数据）。
    "wip_carve_out_boundary": "merge",
}


# ── 执行器（GENERIC——只消费策略表与 facts，无边界特判分支） ──────────

def switch_state(value):
    """Resolve the enforcement switch word → 'on' | 'off' | None (invalid).

    非法值不猜（behavior_profile 词表模式）：空/未设 = on（默认执法）；
    词表内 = on/off；词表外 = None → 调用方保守阻断并披露。
    """
    word = (value or "").strip().lower()
    if not word:
        return "on"
    if word in _SWITCH_OFF_WORDS:
        return "off"
    if word in _SWITCH_ON_WORDS:
        return "on"
    return None


def review_debt_points(obligations):
    """审查债预算 = Σ clamp(severity,1,5) × clamp(age_days,0,30)."""
    total = 0
    for item in obligations or []:
        severity = item.get("severity", 1)
        age = item.get("age_days", 0)
        total += _clamp(_num(severity), 1, 5) * _clamp(_num(age), 0, 30)
    return total


def decide(facts, strategy=None):
    """Judge one boundary action from facts — pure, synchronous, fast.

    Returns a decision dict (decision / reason_code / reason / remedy /
    debt_points / stale_surfaces / boundary / channel / task_id / actor /
    mode).  ANY internal fault (shape violation, unknown boundary under
    the active strategy, unexpected error) fails CLOSED: conservative
    HARD_BLOCK with reason_code=enforcement-fail-closed and a disclosure
    — never a silent allow.
    """
    table = strategy if strategy is not None else STRATEGY
    try:
        return _decide(facts, table)
    except Exception as exc:  # fail-closed：执法器异常保守阻断并披露
        return {
            "decision": DECISION_HARD_BLOCK,
            "reason_code": "enforcement-fail-closed",
            "reason": "enforcer fault — conservative block (fail-closed): "
                      f"{type(exc).__name__}: {exc}",
            "remedy": "fix the enforcement input (facts/strategy shape) "
                      "or report the enforcer fault; do not retry the "
                      "blocked action as-is",
            "boundary": _safe_boundary(facts),
            "channel": _safe_channel(facts),
            "task_id": _safe_task_id(facts),
            "actor": _safe_actor(facts),
            "debt_points": None,
            "stale_surfaces": [],
            "mode": _MODE_ENFORCED,
        }


def _decide(facts, table):
    if not isinstance(facts, dict):
        raise EnforcementInputError("facts must be a JSON object")
    boundary = facts.get("boundary")
    if not isinstance(boundary, str) or boundary not in table["boundaries"]:
        raise EnforcementInputError(
            f"unknown boundary {boundary!r} — not in the strategy table")
    action = facts.get("action") or {}
    state = facts.get("state") or {}
    if not isinstance(action, dict) or not isinstance(state, dict):
        raise EnforcementInputError("action/state must be objects")

    channel = action.get("channel", "normal")
    task_id = action.get("task_id")
    actor = action.get("actor")
    _require_str(channel, "action.channel")
    _require_opt_str(task_id, "action.task_id")
    _require_opt_str(actor, "action.actor")

    # 铁边界：WIP checkpoint commit 始终放行（表数据驱动，优先于硬阻断）。
    wip = action.get("wip_checkpoint", False)
    if not isinstance(wip, bool):
        raise EnforcementInputError("action.wip_checkpoint must be a bool")
    if wip and boundary == table.get("wip_carve_out_boundary"):
        return _decision(
            DECISION_ALLOW, boundary, action,
            reason_code="wip-checkpoint-carve-out",
            reason="WIP checkpoint commit — commit 前不设卡，始终放行",
            remedy="proceed; the assembled-commit face still applies the "
                   "full layered strategy")

    allowlist = tuple(table.get("allowlist_channels", ()))
    allowed_by_channel = channel in allowlist

    # 第 1 层：硬阻断四类零漏放（表顺序求值，首个命中即断）。
    for rule in table["hard_block_rules"]:
        hit = _rule_hit(rule["id"], action, state, table)
        if hit is None:
            continue
        if rule.get("allowlist_exempt") and allowed_by_channel:
            continue  # scoped：白名单通道豁免（数据位），其余规则不豁免
        details = hit
        return _decision(
            DECISION_HARD_BLOCK, boundary, action,
            reason_code=rule["id"],
            reason=rule["reason"].format(**details),
            remedy=rule["remedy"],
            details=details)

    # 第 2 层：审查债预算限流（仅 admission 边界、非白名单通道）。
    obligations = state.get("review_obligations", [])
    _require_obligations(obligations)
    debt = review_debt_points(obligations)
    threshold = _num(table["thresholds"]["review_debt_budget"])
    row = table["boundaries"][boundary]
    if (row.get("throttle") == "review-debt-budget"
            and not allowed_by_channel and debt > threshold):
        return _decision(
            DECISION_THROTTLE, boundary, action,
            reason_code="review-debt-budget-exceeded",
            reason=f"review-debt budget {debt} exceeds threshold "
                   f"{threshold} (unclosed obligations, severity×age)",
            remedy="close overdue review obligations (re-review/fix "
                   "channels stay open) to bring the review-debt budget "
                   "under threshold, or obtain a user ruling to raise it",
            debt_points=debt)

    # 第 3 层：展示性冷面过期 → 提示重建（非阻断）。
    stale = _stale_surfaces(state, table)
    if row.get("stale_notice") and stale:
        return _decision(
            DECISION_STALE_NOTICE, boundary, action,
            reason_code="stale-display-surface",
            reason=f"display surface(s) {stale} stale (touch age over "
                   f"the per-surface staleness budget)",
            remedy="rebuild the stale display surface(s) (Gate 表/项目"
                   "总览/TPA/风险 face refresh) before relying on them; "
                   "the action itself remains permitted",
            debt_points=debt,
            stale_surfaces=stale)

    return _decision(DECISION_ALLOW, boundary, action, debt_points=debt)


def _rule_hit(rule_id, action, state, table):
    """Return formatted details dict when the rule fires, else None.

    类型校验失败在这里抛 EnforcementInputError → decide() 的 fail-closed
    包装捕获（保守阻断披露，绝不静默放行）。
    """
    if rule_id == "revision-mismatch":
        revision = action.get("revision")
        if revision is None:
            return None
        if isinstance(revision, bool) or not isinstance(revision, int):
            raise EnforcementInputError(
                "action.revision must be an int when present")
        expected_map = state.get("expected_revision", {})
        if not isinstance(expected_map, dict):
            raise EnforcementInputError(
                "state.expected_revision must be an object")
        for key, value in expected_map.items():
            if isinstance(value, bool) or not isinstance(value, int):
                raise EnforcementInputError(
                    f"state.expected_revision[{key!r}] must be an int")
        task_id = action.get("task_id")
        if task_id is None or task_id not in expected_map:
            return None
        expected = expected_map[task_id]
        if revision == expected:
            return None
        return {"revision": revision, "task_id": task_id,
                "expected": expected}

    if rule_id == "unauthorized-write":
        paths = action.get("write_paths")
        if not paths:
            return None
        if (not isinstance(paths, list)
                or not all(isinstance(p, str) for p in paths)):
            raise EnforcementInputError(
                "action.write_paths must be a list of strings")
        writers = state.get("authorized_writers", {})
        if not isinstance(writers, dict):
            raise EnforcementInputError(
                "state.authorized_writers must be an object")
        actor = action.get("actor")
        patterns = writers.get(actor) or []
        if (not isinstance(patterns, list)
                or not all(isinstance(p, str) for p in patterns)):
            raise EnforcementInputError(
                "authorized_writers patterns must be a list of strings")
        denied = [p for p in paths
                  if not any(fnmatch.fnmatch(p, pat) for pat in patterns)]
        if not denied:
            return None
        return {"actor": actor, "paths": denied}

    if rule_id == "duplicate-identity":
        actor = action.get("actor")
        if actor is None:
            return None
        active = state.get("active_identities", [])
        if (not isinstance(active, list)
                or not all(isinstance(a, str) for a in active)):
            raise EnforcementInputError(
                "state.active_identities must be a list of strings")
        if actor not in active:
            return None
        return {"actor": actor}

    if rule_id == "unresolved-blocking-review":
        reviews = state.get("unresolved_reviews", [])
        if not isinstance(reviews, list):
            raise EnforcementInputError(
                "state.unresolved_reviews must be a list")
        task_id = action.get("task_id")
        for review in reviews:
            if not isinstance(review, dict):
                raise EnforcementInputError(
                    "unresolved_reviews entries must be objects")
            if (review.get("blocking") is True
                    and review.get("closed") is not True
                    and review.get("task_id") == task_id):
                return {"task_id": task_id}
        return None

    raise EnforcementInputError(f"unknown hard-block rule {rule_id!r}")


def _stale_surfaces(state, table):
    ages = state.get("surface_age_days", {})
    if not isinstance(ages, dict):
        raise EnforcementInputError(
            "state.surface_age_days must be an object")
    budgets = table.get("staleness_days", {})
    stale = []
    for surface, budget in budgets.items():
        age = ages.get(surface)
        if age is None:
            continue
        if isinstance(age, bool) or not isinstance(age, (int, float)):
            raise EnforcementInputError(
                f"surface_age_days[{surface!r}] must be a number")
        if _num(age) > _num(budget):
            stale.append(surface)
    return stale


def _decision(decision, boundary, action, reason_code=None, reason="",
              remedy="", debt_points=None, stale_surfaces=None, details=None):
    payload = {
        "decision": decision,
        "boundary": boundary,
        "channel": action.get("channel", "normal"),
        "task_id": action.get("task_id"),
        "actor": action.get("actor"),
        "reason_code": reason_code,
        "reason": reason,
        "remedy": remedy,
        "debt_points": debt_points,
        "stale_surfaces": stale_surfaces or [],
        "mode": _MODE_ENFORCED,
    }
    if details is not None:
        payload["details"] = details
    return payload


def _require_obligations(items):
    if not isinstance(items, list):
        raise EnforcementInputError(
            "state.review_obligations must be a list")
    for item in items:
        if not isinstance(item, dict):
            raise EnforcementInputError(
                "review_obligations entries must be objects")
        for key in ("severity", "age_days"):
            value = item.get(key)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise EnforcementInputError(
                    f"review_obligations {key!r} must be a number")


def _clamp(value, low, high):
    return max(low, min(high, value))


def _num(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EnforcementInputError(f"expected a number, got {value!r}")
    return value


def _require_str(value, name):
    if not isinstance(value, str):
        raise EnforcementInputError(f"{name} must be a string")


def _require_opt_str(value, name):
    if value is not None and not isinstance(value, str):
        raise EnforcementInputError(f"{name} must be a string or null")


def _safe_boundary(facts):
    try:
        value = facts.get("boundary") if isinstance(facts, dict) else None
        return value if isinstance(value, str) else None
    except Exception:
        return None


def _safe_channel(facts):
    return _safe_action_key(facts, "channel", "normal")


def _safe_task_id(facts):
    return _safe_action_key(facts, "task_id", None)


def _safe_actor(facts):
    return _safe_action_key(facts, "actor", None)


def _safe_action_key(facts, key, default):
    try:
        action = facts.get("action")
        if isinstance(action, dict):
            value = action.get(key, default)
            return value if isinstance(value, str) else default
    except Exception:
        pass
    return default


# ── CLI 面（cmd_enforcement_check——verify_workflow.py 薄接线派发） ────

_EXIT_BY_DECISION = {
    DECISION_ALLOW: EXIT_ALLOW,
    DECISION_HARD_BLOCK: EXIT_HARD_BLOCK,
    DECISION_THROTTLE: EXIT_THROTTLE,
    DECISION_STALE_NOTICE: EXIT_STALE_NOTICE,
}


def _strategy_public(table=None):
    table = table or STRATEGY
    return {
        "boundaries": {
            boundary: {
                "hard_block": row.get("hard_block", True),
                "throttle": row.get("throttle"),
                "stale_notice": bool(row.get("stale_notice")),
            }
            for boundary, row in table["boundaries"].items()
        },
        "hard_block_rules": [rule["id"]
                             for rule in table["hard_block_rules"]],
        "thresholds": dict(table["thresholds"]),
        "staleness_days": dict(table["staleness_days"]),
        "allowlist_channels": list(table.get("allowlist_channels", ())),
        "wip_carve_out_boundary": table.get("wip_carve_out_boundary"),
        "switch_env": table.get("switch_env", ENFORCEMENT_SWITCH_ENV),
        "record_anchor": table.get("record_anchor", RECORD_ANCHOR),
        "exit_codes": {
            "ALLOW": EXIT_ALLOW,
            "HARD_BLOCK": EXIT_HARD_BLOCK,
            "THROTTLE": EXIT_THROTTLE,
            "STALE_NOTICE": EXIT_STALE_NOTICE,
        },
    }


def _emit(payload, record_dir, record_filename=None):
    """Print machine JSON + human stderr line; append the grep-able record.

    记录失败不吞不炸：披露到 payload.record_error（决定已保守作出）。
    """
    row = dict(payload)
    row["anchor"] = RECORD_ANCHOR
    row["ts"] = datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    try:
        name = record_filename or RECORD_FILENAME
        target = Path(record_dir)
        target.mkdir(parents=True, exist_ok=True)
        with open(target / name, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception as exc:
        payload = dict(payload)
        payload["record_error"] = (
            f"enforcement record not written: {type(exc).__name__}: {exc}")
    print(json.dumps(payload, ensure_ascii=False))
    print(
        f"[{RECORD_ANCHOR}] boundary={payload.get('boundary')} "
        f"decision={payload.get('decision')} "
        f"reason_code={payload.get('reason_code')} :: "
        f"{payload.get('reason')} :: remedy: {payload.get('remedy')}",
        file=sys.stderr)
    return payload


def cmd_enforcement_check(args, governance_dir=None, repo_root=None):
    """CLI entry — returns the family exit code (0/2/3/4).

    Exit 0 ALLOW / 2 HARD_BLOCK (incl. fail-closed + invalid switch) /
    3 THROTTLE / 4 STALE_NOTICE (non-blocking rebuild notice).
    Switch off (GOVERNANCE_ENFORCEMENT=off) = advisory baseline: exit 0,
    zero records, zero side effects — behavior identical to a world
    without this face (zero drift).
    """
    if getattr(args, "print_strategy", False):
        print(json.dumps(_strategy_public(), ensure_ascii=False))
        return EXIT_ALLOW

    state = switch_state(os.environ.get(
        getattr(args, "switch_env", None) or ENFORCEMENT_SWITCH_ENV))
    if state is None:
        value = os.environ.get(ENFORCEMENT_SWITCH_ENV)
        payload = {
            "decision": DECISION_HARD_BLOCK,
            "boundary": None,
            "channel": None,
            "task_id": None,
            "actor": None,
            "reason_code": "enforcement-switch-invalid",
            "reason": f"invalid {ENFORCEMENT_SWITCH_ENV}={value!r} — "
                      "fail-closed conservative block (非法值不猜)",
            "remedy": f"set {ENFORCEMENT_SWITCH_ENV} to on/off or unset it",
            "debt_points": None,
            "stale_surfaces": [],
            "mode": _MODE_ENFORCED,
        }
        _emit(payload, getattr(args, "record_dir", None)
              or (str(governance_dir) if governance_dir else None))
        return EXIT_HARD_BLOCK

    facts_path = getattr(args, "facts", None)
    if state == "off":
        # 零漂移：不读 facts、不判定、不落记录——advisory 基线行为。
        payload = {
            "decision": DECISION_ALLOW,
            "boundary": None,
            "channel": None,
            "task_id": None,
            "actor": None,
            "reason_code": "enforcement-disabled",
            "reason": f"{ENFORCEMENT_SWITCH_ENV}=off — advisory baseline "
                      "(zero enforcement side effects)",
            "remedy": "unset the switch (or set on) to re-enable layered "
                      "enforcement",
            "debt_points": None,
            "stale_surfaces": [],
            "mode": _MODE_ADVISORY,
        }
        print(json.dumps(payload, ensure_ascii=False))
        print(f"[{RECORD_ANCHOR}] decision=ALLOW mode={_MODE_ADVISORY} "
              f"({ENFORCEMENT_SWITCH_ENV}=off)", file=sys.stderr)
        return EXIT_ALLOW

    if not facts_path:
        print(json.dumps({
            "decision": DECISION_HARD_BLOCK,
            "reason_code": "enforcement-fail-closed",
            "reason": "--facts <path> is required unless --print-strategy",
            "remedy": "pass --facts with the boundary-action facts JSON",
            "mode": _MODE_ENFORCED,
        }))
        return EXIT_HARD_BLOCK

    try:
        with open(facts_path, "r", encoding="utf-8") as handle:
            facts = json.load(handle)
    except Exception as exc:
        payload = decide(None)  # fail-closed 模板
        payload["reason"] = (
            f"facts file unreadable ({facts_path}): "
            f"{type(exc).__name__}: {exc} — conservative block "
            "(fail-closed)")
        payload["facts_path"] = str(facts_path)
        _emit(payload, getattr(args, "record_dir", None)
              or (str(governance_dir) if governance_dir else None))
        return EXIT_HARD_BLOCK

    payload = decide(facts)
    payload = _emit(payload, getattr(args, "record_dir", None)
                    or (str(governance_dir) if governance_dir else None))
    return _EXIT_BY_DECISION.get(payload["decision"], EXIT_HARD_BLOCK)


def add_enforcement_check_arguments(parser):
    parser.add_argument(
        "--facts", default=None,
        help="Path to the boundary-action facts JSON (boundary/action/"
             "state projection of the check outputs)")
    parser.add_argument(
        "--record-dir", default=None,
        help="Directory for the enforcement-log.jsonl machine record "
             "(default: the engine-resolved governance dir)")
    parser.add_argument(
        "--print-strategy", action="store_true",
        help="Print the strategy table (six boundaries × three layers) "
             "as grep-able JSON and exit 0")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="enforcement",
        description="FEAT-095 action-level enforcement (six boundaries, "
                    "three layers; protocol+CLI face — no host-level "
                    "interception claim)")
    sub = parser.add_subparsers(dest="command")
    face = sub.add_parser("enforcement-check")
    add_enforcement_check_arguments(face)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    return cmd_enforcement_check(args)


if __name__ == "__main__":
    sys.exit(main())
