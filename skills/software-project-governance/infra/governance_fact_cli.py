"""Render command results for the project ledgers, execution packets and gates."""
import governance_store
import json
import sys


def cmd_execution_packet(args, *, packet_path_now, read_execution_packet_document,
                         generate_execution_packets):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    from contextlib import nullcontext

    budget = getattr(args, "budget", None)
    if budget is not None and (type(budget) is not int or budget <= 0):
        print(f"[ERROR] --budget must be a positive integer (got {budget!r})")
        sys.exit(2)

    wanted = set(args.task) if args.task else None
    note = ""
    try:
        path = packet_path_now().resolve()
        with governance_store._TargetLock(path) if args.write else nullcontext():
            packets, metadata = read_execution_packet_document(path, missing_ok=True)
            contracts = set(getattr(args, "contract", None) or [])
            dimensions = list(dict.fromkeys(getattr(args, "quality_dimension", None) or []))
            if dimensions:
                contracts.add("quality_budget")
            selection = wanted if wanted is not None else set(packets)
            payload = generate_execution_packets(existing=packets, task_ids=selection, governance_dir=path.parent,
                                                 contracts=contracts, quality_dimensions=dimensions)
            generated = payload["packets"]
            if budget is not None:
                for packet in generated.values():
                    packet["budget"] = {"max_steps": budget}
            if not args.write:
                message = json.dumps(payload, ensure_ascii=False, indent=2)
            elif not generated:
                message = "[OK] no active execution packets matched the selected tasks"
            else:
                payload["packets"] = {**packets, **generated}
                if wanted is not None:
                    preserved = len(payload["packets"]) - len(generated)
                    note = (f" (incremental merge: regenerated {', '.join(sorted(generated))};"
                            f" preserved {preserved} other {'entry' if preserved == 1 else 'entries'})")
                document = {**metadata, **payload}
                data = (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
                governance_store._atomic_write_bytes(path, data)
                message = f"[OK] wrote {len(payload['packets'])} execution packet(s) to {packet_path_now()}{note}"
    except (OSError, ValueError, governance_store.StoreError) as exc:
        print(f"[ERROR] {packet_path_now()}: {exc}", file=sys.stderr)
        sys.exit(1)
    print(message)


_workflow_gate_command = None


def bind_gate_command(reader):
    """An active application may replace the legacy gate handler at dispatch time."""
    global _workflow_gate_command
    _workflow_gate_command = reader


def effective_gate_command(name, native):
    return native if _workflow_gate_command is None else _workflow_gate_command(name, native)


def cmd_gate_check(args):
    """Evaluate only an identified unit's current gate using its scoped receipt."""
    from loop_workflow import gate_review
    from resolve_entry import current_host_root
    if not getattr(args, "unit", None) or not getattr(args, "review", None):
        print("gate-check requires --unit and --review from this unit and iteration", file=sys.stderr)
        sys.exit(2)
    try:
        outcome = gate_review(current_host_root(), args.unit, args.gate_id.upper(), args.review)
    except (ValueError, OSError) as exc:
        print(f"gate-check: {exc}", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(outcome, ensure_ascii=False, indent=2))
    if outcome.get("decision") in ("escalate", "iterate") and getattr(args, "fail_on_blocked", False):
        sys.exit(1)


def cmd_check_cross_references(args, *, check_cross_references, check_exploration_sample_advisories):
    """CLI wrapper for cross-reference checking (SYSGAP-008)."""
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    result = check_cross_references()
    print()
    print("=== Cross-Reference Check ===")
    print(f"  Files scanned: {result['total_files_scanned']}")
    print(f"  References extracted: {result['total_refs']}")
    fail = False

    if result["dangling"]:
        fail = True
        print(f"\n  [FAIL] {len(result['dangling'])} dangling reference(s):")
        for d in result["dangling"]:
            print(f"    - {d['source']}:{d['line']} -> {d['target']}")
    else:
        print(f"\n  [PASS] No dangling references.")

    if result["deprecated"]:
        fail = True
        print(f"\n  [FAIL] {len(result['deprecated'])} deprecated path(s):")
        for d in result["deprecated"]:
            print(f"    - {d['source']}:{d['line']}: {d['target']} ({d['deprecated_pattern']})")
    else:
        print(f"\n  [PASS] No deprecated paths.")

    if result["cycles"]:
        fail = True
        print(f"\n  [FAIL] {len(result['cycles'])} circular reference(s):")
        for cycle in result["cycles"]:
            print(f"    - {' -> '.join(cycle)}")
    else:
        print(f"\n  [PASS] No circular references.")

    # FIX-432 (F-4/F-A2) / FIX-436 F-8 wording: citation/note quote-sync
    # guard; the current check_cross_references() always emits the key —
    # .get only tolerates pre-FIX-432/partial dict shapes that lack it.
    quote_sync = result.get("quote_sync", [])
    if quote_sync:
        fail = True
        print(f"\n  [FAIL] {len(quote_sync)} quote-sync issue(s) (FIX-432 F-4/F-A2):")
        for issue in quote_sync:
            print(f"    - {issue}")
    else:
        print(f"\n  [PASS] Citation/note quote sync clean (FIX-432 F-4/F-A2).")

    # FEAT-088 (F-A3): exploration-channel evidence-form guard sub-face.
    channels_face = result.get("exploration_channels", {}) or {}
    channel_issues = channels_face.get("issues", [])
    if channel_issues:
        fail = True
        print(f"\n  [FAIL] {len(channel_issues)} exploration-channel "
              f"evidence-form issue(s) (FEAT-088 F-A3):")
        for issue in channel_issues:
            print(f"    - {issue}")
    else:
        print(f"\n  [PASS] Exploration-channel evidence forms clean "
              f"(FEAT-088 F-A3).")
    for advisory in (channels_face.get("advisories") or [])[:5]:
        print(f"  [ADVISORY] {advisory}")
    layering = channels_face.get("probe_layering") or {}
    if layering:
        print("\n  Probe layering (honesty statement):")
        for label, text in layering.items():
            print(f"    - {label}: {text}")

    # FIX-436 (F-B3 / DEC-317): M10.2 sample-report exploration-block
    # presence advisory — WARN-class, disclosed but never counted toward
    # the exit code (MUST NOT be a blocking FAIL per DEC-317).
    for advisory in check_exploration_sample_advisories():
        print(f"  [ADVISORY] {advisory}")

    print()
    if fail:
        sys.exit(1)


def cmd_check_sequential_ids(args, *, check_sequential_ids):
    """CLI wrapper for sequential ID checking (SYSGAP-009)."""
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    result = check_sequential_ids()
    print()
    print("=== Sequential ID Check ===")
    fail = False

    def _report(prefix, ids, gaps):
        nonlocal fail
        if ids:
            print(f"  {prefix}: {ids[0]:03d}-{ids[-1]:03d} ({len(ids)} entries)")
        else:
            print(f"  {prefix}: no entries found")
        if gaps:
            fail = True
            print(f"    [FAIL] Gaps detected: missing {gaps}")
        else:
            print(f"    [PASS] No gaps.")

    _report("DEC", result["dec_ids"], result["dec_gaps"])
    _report("EVD", result["evd_ids"], result["evd_gaps"])
    _report("RISK", result["risk_ids"], result["risk_gaps"])

    orphans = (result.get("orphan_evidence_refs", []) +
               result.get("orphan_decision_refs", []) +
               result.get("orphan_risk_refs", []))
    if orphans:
        fail = True
        print(f"\n  [FAIL] {len(orphans)} cross-reference(s) to non-existent task IDs: {orphans}")
    else:
        print(f"\n  [PASS] All cross-referenced task IDs exist in plan-tracker.")

    missing_evd = result.get("completed_missing_evidence", [])
    if missing_evd:
        fail = True
        print(f"  [FAIL] {len(missing_evd)} completed task(s) without evidence: {missing_evd}")
    else:
        print(f"  [PASS] All completed tasks have evidence.")

    print()
    if fail:
        sys.exit(1)


def cmd_check_structural_validity(args, *, check_structural_validity):
    """CLI wrapper for structural validity checking (SYSGAP-010)."""
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    issues = check_structural_validity()
    print()
    print("=== Structural Validity Check ===")
    if issues:
        print(f"  [FAIL] {len(issues)} structural issue(s):")
        for v in issues:
            ftype = v.get("type", "unknown")
            ffile = v.get("file", "?")
            detail = v.get("detail", "")
            print(f"    - [{ftype}] {ffile}: {detail}")
        print()
        sys.exit(1)
    print(f"  [PASS] All governance files have valid structure.")
    print()


def cmd_check_commit_scope(args, *, check_commit_scope):
    """CLI wrapper for commit scope verification (SYSGAP-012)."""
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    limit = args.limit if hasattr(args, 'limit') else 20
    result = check_commit_scope(limit=limit)
    print()
    print("=== Commit Scope Verification ===")
    if result.get("error"):
        print(f"  [ERROR] {result['error']}")
        print()
        return
    print(f"  Recent commits checked: {result['total_checked']}")
    issues = result["issues"]
    if issues:
        print(f"\n  [WARN] {len(issues)} scope discipline issue(s):")
        for v in issues:
            itype = v.get("type", "?")
            detail = v.get("detail", "")
            sha = v.get("sha", "?")
            print(f"    - [{itype}] {sha}: {detail}")
    else:
        print(f"\n  [PASS] All recent commits have clean scope discipline.")
    print()


def cmd_check_goal_alignment(args, *, check_goal_alignment):
    """CLI wrapper for goal alignment checking (SYSGAP-023)."""
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    result = check_goal_alignment()
    fail = False
    print()
    print("=== Goal Alignment Check ===")
    if not result["has_project_goal"]:
        print(f"  [WARN] plan-tracker missing 项目目标 field.")
    else:
        project_goal_short = result["project_goal"][:60]
        print(f"  [INFO] 项目目标: {project_goal_short}...")
    print(f"  Impact analysis entries: {len(result['entries'])}")
    exempted = result.get("historical_exempted", [])
    print(f"  Historical exempted (FIX-371/DEC-227 ✅-terminal + FIX-390 writer-committed, skipped): {len(exempted)}")
    for row in exempted:
        print(f"    - {row['task_id']} ({row['evd_id']}): {row['status']}")
    if result["entries"]:
        for e in result["entries"]:
            if e["status"] == "FAIL":
                fail = True
                if not e["has_goal"]:
                    print(f"  [FAIL] {e['task_id']} ({e['evd_id']}): 缺少 目标对齐: 字段")
                else:
                    print(f"  [FAIL] {e['task_id']} ({e['evd_id']}): 目标对齐: 仅 {e['goal_len']} chars (需 >= 30)")
            elif e["status"] == "PASS":
                print(f"  [PASS] {e['task_id']} ({e['evd_id']}): {e['goal_len']} chars")
        if result["duplicates"]:
            print(f"  [WARN] {len(result['duplicates'])} duplicate goal alignment(s):")
            for t1, t2 in result["duplicates"]:
                print(f"    - {t1} <-> {t2}")
    else:
        print(f"  [PASS] No impact analysis entries to check.")
    if not fail and result["has_project_goal"]:
        print(f"  [PASS] All impact analysis entries have valid goal alignment.")
    print()
    if fail:
        sys.exit(1)


def cmd_check_user_impact(args, *, check_user_impact):
    """CLI wrapper for user impact checking (SYSGAP-024)."""
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    result = check_user_impact()
    fail = False
    print()
    print("=== User Impact Check ===")
    print(f"  Impact analysis entries: {len(result['entries'])}")
    exempted = result.get("historical_exempted", [])
    print(f"  Historical exempted (FIX-371/DEC-227 ✅-terminal + FIX-390 writer-committed, skipped): {len(exempted)}")
    for row in exempted:
        print(f"    - {row['task_id']} ({row['evd_id']}): {row['status']}")
    if result["entries"]:
        for e in result["entries"]:
            status_label = {
                "BLOCKING": "BLOCK",
                "FAIL": "FAIL",
                "WARN": "WARN",
                "PASS": "PASS",
            }.get(e["status"], "?")
            if e["status"] in ("BLOCKING", "FAIL"):
                fail = True
                for issue in e["issues"]:
                    print(f"  [{status_label}] {e['task_id']} ({e['evd_id']}): {issue}")
            elif e["status"] == "WARN":
                for issue in e["issues"]:
                    print(f"  [WARN] {e['task_id']} ({e['evd_id']}): {issue}")
            else:
                print(f"  [PASS] {e['task_id']} ({e['evd_id']}): "
                      f"获得={e['obtain']}, 体验变化={e['exp_change']}, "
                      f"迁移指南={e['migration']}")
    else:
        print(f"  [PASS] No impact analysis entries to check.")
    if not fail and not result["blocking"]:
        print(f"  [PASS] All impact analysis entries have valid user impact analysis.")
    print()
    if fail:
        sys.exit(1)


def cmd_check_hot_fact_source(args, *, check_hot_fact_source_consistency):
    """Run hot fact-source consistency guard independently."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    issues = check_hot_fact_source_consistency()
    print("\n=== Hot Fact-Source Consistency Check ===")
    if issues:
        print(f"  Result: FAILED — {len(issues)} issue(s)")
        for issue in issues[:20]:
            print(f"    - {issue}")
        if len(issues) > 20:
            print(f"    ... and {len(issues) - 20} more")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
    else:
        print("  Result: PASSED — hot fact-source sections are synchronized")
    print()
