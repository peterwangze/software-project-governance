"""Validate the lock ledger and diagnose cross-agent ownership conflicts."""

import re


def check_agent_locks_format(*, governance_dir):
    """Validate .governance/agent-locks.json existence, JSON validity, and schema integrity.

    Returns a list of WARN-level issue dicts.  Empty list = clean.
    This check is informational-only (WARN) -- format corruption does not block commit.
    Used as a helper by check_agent_lock_consistency() (Check 26, FIX-056 Phase 2).
    Phase 1 format-only check has been subsumed into the full Check 26.
    """
    import json

    issues = []
    locks_path = governance_dir / "agent-locks.json"

    # ── Existence check ──
    if not locks_path.is_file():
        issues.append({
            "type": "missing",
            "detail": ".governance/agent-locks.json not found. Run governance init or create with: {\"active_tasks\": {}, \"file_locks\": {}}"
        })
        return issues

    # ── JSON validity ──
    try:
        with open(locks_path, "r", encoding="utf-8") as f:
            raw = f.read()
        if not raw.strip():
            issues.append({
                "type": "empty",
                "detail": ".governance/agent-locks.json is empty"
            })
            return issues
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        issues.append({
            "type": "invalid_json",
            "detail": f".governance/agent-locks.json is not valid JSON: {e}"
        })
        return issues
    except IOError as e:
        issues.append({
            "type": "io_error",
            "detail": f".governance/agent-locks.json read error: {e}"
        })
        return issues

    # ── Schema check ──
    if not isinstance(data, dict):
        issues.append({
            "type": "not_dict",
            "detail": ".governance/agent-locks.json root must be a JSON object (dict)"
        })
        return issues

    # Required top-level keys
    required_keys = ["active_tasks", "file_locks"]
    for key in required_keys:
        if key not in data:
            issues.append({
                "type": "missing_key",
                "detail": f".governance/agent-locks.json missing required key: '{key}'"
            })

    # active_tasks must be a dict
    if "active_tasks" in data and not isinstance(data["active_tasks"], dict):
        issues.append({
            "type": "type_error",
            "detail": ".governance/agent-locks.json 'active_tasks' must be a JSON object (dict), got " + type(data["active_tasks"]).__name__
        })

    # file_locks must be a dict
    if "file_locks" in data and not isinstance(data["file_locks"], dict):
        issues.append({
            "type": "type_error",
            "detail": ".governance/agent-locks.json 'file_locks' must be a JSON object (dict), got " + type(data["file_locks"]).__name__
        })

    # ── active_tasks entry schema check ──
    if "active_tasks" in data and isinstance(data["active_tasks"], dict):
        for task_id, entry in data["active_tasks"].items():
            if not isinstance(entry, dict):
                issues.append({
                    "type": "schema_violation",
                    "detail": f"agent-locks.json active_tasks['{task_id}'] must be a dict"
                })
                continue
            required_entry_keys = ["spawned_at", "coordinator_session", "target_files"]
            for rk in required_entry_keys:
                if rk not in entry:
                    issues.append({
                        "type": "schema_violation",
                        "detail": f"agent-locks.json active_tasks['{task_id}'] missing required field: '{rk}'"
                    })
            if "target_files" in entry and not isinstance(entry["target_files"], list):
                issues.append({
                    "type": "schema_violation",
                    "detail": f"agent-locks.json active_tasks['{task_id}'].target_files must be a list"
                })

    # ── file_locks entry schema check ──
    if "file_locks" in data and isinstance(data["file_locks"], dict):
        for file_path, entry in data["file_locks"].items():
            if not isinstance(entry, dict):
                issues.append({
                    "type": "schema_violation",
                    "detail": f"agent-locks.json file_locks['{file_path}'] must be a dict"
                })
                continue
            required_entry_keys = ["locked_by", "locked_at", "ttl_seconds", "ttl_reason"]
            for rk in required_entry_keys:
                if rk not in entry:
                    issues.append({
                        "type": "schema_violation",
                        "detail": f"agent-locks.json file_locks['{file_path}'] missing required field: '{rk}'"
                    })
            if "ttl_seconds" in entry and not isinstance(entry["ttl_seconds"], (int, float)):
                issues.append({
                    "type": "schema_violation",
                    "detail": f"agent-locks.json file_locks['{file_path}'].ttl_seconds must be a number"
                })
            # FEAT-013 (RISK-046): optional expected_new flag — the
            # pre-created-file exemption declared at acquire time
            # (agent-locks-acquire --expected-new). Absent = regular
            # existing-file lock (backward compatible: legacy locks PASS).
            if "expected_new" in entry and not isinstance(entry["expected_new"], bool):
                issues.append({
                    "type": "schema_violation",
                    "detail": f"agent-locks.json file_locks['{file_path}'].expected_new must be a boolean when present (FEAT-013 pre-created-file declaration)",
                })

    return issues


def check_agent_lock_consistency(*, current_governance_dir, check_agent_locks_format, lock_issue_is_blocking):
    """Comprehensive agent lock consistency check (FIX-056 Phase 2).

    Checks:
      - Format/schema validity (delegates to check_agent_locks_format)
      - Task existence: locked_by task_ids must exist in plan-tracker
      - Orphan locks: file_locks referencing task_ids not in active_tasks
      - Expired locks: locked_at + ttl_seconds < now
      - Multi-lock conflict: same file locked by multiple active tasks

    Returns a dict with keys:
      - skipped: str if check was skipped (agent-locks.json missing), else None
      - active_task_count: number of active_tasks entries
      - file_lock_count: number of file_locks entries
      - issues: list of WARN-level issue dicts (type + detail)
    """
    import json
    from datetime import datetime, timezone

    result = {
        "skipped": None,
        "active_task_count": 0,
        "file_lock_count": 0,
        "issues": [],
    }

    locks_path = current_governance_dir() / "agent-locks.json"

    # ── Format check (Phase 1, reused) ──
    fmt_issues = check_agent_locks_format()
    for fi in fmt_issues:
        result["issues"].append({
            "type": f"format_{fi['type']}",
            "detail": fi["detail"],
        })

    # If format is broken, skip consistency checks (can't parse data)
    if not locks_path.is_file():
        result["skipped"] = "agent-locks.json not found — lock consistency check skipped."
        return result

    try:
        with open(locks_path, "r", encoding="utf-8") as f:
            raw = f.read()
        if not raw.strip():
            result["skipped"] = "agent-locks.json is empty — lock consistency check skipped."
            return result
        data = json.loads(raw)
    except (json.JSONDecodeError, IOError, UnicodeDecodeError):
        result["skipped"] = "agent-locks.json is unparseable — lock consistency check skipped."
        return result

    if not isinstance(data, dict):
        result["skipped"] = "agent-locks.json root is not a dict — lock consistency check skipped."
        return result

    active_tasks = data.get("active_tasks", {})
    file_locks = data.get("file_locks", {})

    if not isinstance(active_tasks, dict):
        active_tasks = {}
    if not isinstance(file_locks, dict):
        file_locks = {}

    result["active_task_count"] = len(active_tasks)
    result["file_lock_count"] = len(file_locks)

    # If nothing active, skip consistency checks
    if not active_tasks and not file_locks:
        return result

    # ── Load plan-tracker task IDs ──
    plan_task_ids = set()
    try:
        pt_path = current_governance_dir() / "plan-tracker.md"
        if pt_path.is_file():
            pt_content = pt_path.read_text(encoding="utf-8")
            # Match task IDs in any table cell.  Active task tables often use
            # a priority first column, e.g. | **P1** | FIX-066 | ...
            for line in pt_content.split("\n"):
                if not line.lstrip().startswith("|"):
                    continue
                for task_id in re.findall(r"\b([A-Z]+-\d+)\b", line):
                    plan_task_ids.add(task_id)
    except Exception:
        pass  # Can't read plan-tracker — skip task-existence check

    now = datetime.now(timezone.utc)

    # ── Check 1: Task existence — every locked_by / active_tasks key must be in plan-tracker ──
    all_lock_task_ids = set()

    for task_id in active_tasks.keys():
        all_lock_task_ids.add(task_id)
        if plan_task_ids and task_id not in plan_task_ids:
            result["issues"].append({
                "type": "task_not_in_plan",
                "detail": f"active_tasks['{task_id}'] is not found in plan-tracker.md — lock references an unregistered task.",
            })

    for file_path, entry in file_locks.items():
        if isinstance(entry, dict):
            locker = entry.get("locked_by", "")
            if locker:
                all_lock_task_ids.add(locker)
                if plan_task_ids and locker not in plan_task_ids:
                    result["issues"].append({
                        "type": "task_not_in_plan",
                        "detail": f"file_locks['{file_path}'].locked_by='{locker}' is not found in plan-tracker.md.",
                    })

    # ── Check 2: Orphan locks — file_locks.locked_by not in active_tasks ──
    active_task_ids = set(active_tasks.keys())
    for file_path, entry in file_locks.items():
        if isinstance(entry, dict):
            locker = entry.get("locked_by", "")
            if locker and locker not in active_task_ids:
                result["issues"].append({
                    "type": "orphan_lock",
                    "detail": f"file_locks['{file_path}'] is locked by '{locker}' which has no active_tasks entry (orphan lock).",
                })

    # ── Check 3: Expired locks ──
    for file_path, entry in file_locks.items():
        if not isinstance(entry, dict):
            continue
        locked_at_str = entry.get("locked_at", "")
        ttl = entry.get("ttl_seconds", 0)
        if locked_at_str and ttl:
            try:
                locked_at = datetime.fromisoformat(locked_at_str.replace("Z", "+00:00"))
                expiry = locked_at.timestamp() + float(ttl)
                if now.timestamp() > expiry:
                    locker = entry.get("locked_by", "unknown")
                    elapsed = int(now.timestamp() - locked_at.timestamp())
                    result["issues"].append({
                        "type": "expired_lock",
                        "detail": (f"file_locks['{file_path}'] expired (locked by '{locker}', "
                                   f"TTL {ttl}s, elapsed {elapsed}s) — stale lock should be cleaned up."),
                    })
            except (ValueError, TypeError, OverflowError):
                pass

    # Also check active_tasks expiry (based on spawned_at + max TTL 600s)
    for task_id, entry in active_tasks.items():
        if not isinstance(entry, dict):
            continue
        spawned_at_str = entry.get("spawned_at", "")
        if spawned_at_str:
            try:
                spawned_at = datetime.fromisoformat(spawned_at_str.replace("Z", "+00:00"))
                # Use 600s as max reasonable TTL for any task
                if (now - spawned_at).total_seconds() > 600:
                    result["issues"].append({
                        "type": "expired_task",
                        "detail": (f"active_tasks['{task_id}'] spawned at {spawned_at_str} "
                                   f"({int((now - spawned_at).total_seconds())}s ago) — may be stale."),
                    })
            except (ValueError, TypeError, OverflowError):
                pass

    # ── Check 4: Multi-lock conflict — same file locked by multiple active tasks ──
    file_to_lockers = {}
    for file_path, entry in file_locks.items():
        if isinstance(entry, dict):
            locker = entry.get("locked_by", "")
            if locker and locker in active_task_ids:
                file_to_lockers.setdefault(file_path, set()).add(locker)

    for file_path, lockers in file_to_lockers.items():
        if len(lockers) > 1:
            result["issues"].append({
                "type": "multi_lock_conflict",
                "detail": (f"file_locks['{file_path}'] is locked by multiple active tasks: "
                           f"{sorted(lockers)} — potential concurrent write conflict."),
            })

    for issue in result["issues"]:
        issue["severity"] = "BLOCKING" if lock_issue_is_blocking(issue) else "WARN"

    return result


def cmd_check_agent_locks(_args, *, check_agent_lock_consistency, lock_issue_is_blocking):
    """Standalone subcommand: check-locks — run agent lock consistency check."""
    result = check_agent_lock_consistency()

    if result.get("skipped"):
        print(f"[INFO] {result['skipped']}")
        return

    print(f"Active tasks: {result['active_task_count']}")
    print(f"File locks:   {result['file_lock_count']}")

    issues = result.get("issues", [])
    if not issues:
        print("Result: PASS — agent-locks.json is clean.")
    else:
        blocking = [i for i in issues if lock_issue_is_blocking(i)]
        print(f"\n{len(issues)} lock issue(s), {len(blocking)} blocking:")
        for issue in issues:
            severity = "BLOCKING" if lock_issue_is_blocking(issue) else "WARN"
            print(f"  [{severity}:{issue['type']}] {issue['detail']}")
        result_label = "WARN" if blocking else "INFO"
        print(f"\nResult: {result_label} — {len(issues)} lock consistency issue(s).")


def cmd_agent_locks_acquire(args, *, governance_dir, host_root, check_agent_locks_format):
    """Thin entry — agent-locks-acquire CLI (FEAT-013 / RISK-046 root fix).

    All validation and writing live in
    :func:`change_triage.acquire_dispatch_locks` (RISK-039 thin-entry
    discipline): pre-write path existence + expected-new exemption +
    same-day change-triage files cross-check (mismatch WARN-disclosed,
    never blocking). This glue injects the host paths and the Check 26
    post-write self-validation — the writer proves its own output
    against the SAME schema the FEAT-011 write guard consumes (no second
    schema definition). Exit 0 = written (WARNs may accompany on stderr);
    exit 2 = fail-closed refusal (nothing written).
    """
    from change_triage import agent_locks_acquire_cli
    agent_locks_acquire_cli(
        args, governance_dir=governance_dir, repo_root=host_root,
        post_write_check=check_agent_locks_format)
