"""Full governance report sections for governance records, references, and host health."""


def section_1_evidence_completeness(emit_evidence_completeness, check_evidence_completeness):
    issue_count = 0
    print("\n┌─ Check 1: Evidence Completeness ─────────────────────┐")
    issue_count += emit_evidence_completeness(check_evidence_completeness())
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_2_risk_staleness(emit_risk_staleness, check_risk_staleness):
    issue_count = 0
    print("\n┌─ Check 2: Risk Staleness (>7 days) ──────────────────┐")
    issue_count += emit_risk_staleness(check_risk_staleness())
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_2b_decision_premises(check_decision_premise):
    issue_count = 0
    # Same WARN semantics as risk staleness above: a declared premise whose
    # observable count has crossed its threshold and has not been
    # re-reviewed (a review resets the counter baseline) is collapsed —
    # the decision's ranking-suppression authority is stripped (TPA
    # surfaces it as active-defect) until the user re-reviews. Read-only.
    print("\n┌─ Check 2b: Decision Premise (FIX-463) ──────────────┐")
    try:
        _premise_verdict = check_decision_premise()
        _premise_decls = _premise_verdict["declarations"]
        _collapsed = _premise_verdict["collapsed"]
        _premise_detail = _premise_verdict["detail"]
        if _collapsed:
            issue_count += len(_collapsed)
            print(f"│  [WARN] {len(_collapsed)} collapsed premise(s):")
            for _dec_id in _collapsed:
                _detail = _premise_detail[_dec_id]
                print(f"│    - {_dec_id}: premise collapsed — re-review "
                      f"required ({_detail['observable']} "
                      f"{_detail['total']} ≥ threshold "
                      f"{_detail['threshold']}); the decision no longer "
                      f"suppresses ranking (premise review to restore)")
        elif _premise_decls:
            print(f"│  [PASS] {len(_premise_decls)} declared premise(s) "
                  f"standing.")
        else:
            print("│  [PASS] No declared premises (FIX-463 face idle).")
    except (OSError, ValueError) as _premise_exc:
        issue_count += 1
        print(f"│  [WARN] premise face unreadable: {_premise_exc}")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_3_gate_consistency(check_gate_consistency):
    issue_count = 0
    print("\n┌─ Check 3: Gate Consistency ──────────────────────────┐")
    gate_issues = check_gate_consistency()
    if gate_issues:
        for issue in gate_issues:
            if issue["type"] == "loop_receipt":
                issue_count += 1
                print(f"│  [FAIL] {issue['detail']}")
            elif issue["type"] == "completed_tasks_missing_evidence":
                tasks_list = issue["detail"]
                issue_count += len(tasks_list)
                print(f"│  [WARN] Completed tasks without evidence:")
                for tid in tasks_list:
                    print(f"│    - {tid}")
            elif issue["type"] == "orphan_evidence":
                ev_list = issue["detail"]
                print(f"│  [INFO] Evidence entries for non-existent tasks:")
                for eid in ev_list:
                    print(f"│    - {eid}")
            elif issue["type"] == "historical_completed_tasks_missing_evidence":
                tasks_list = issue["detail"]
                print(f"│  [INFO] Archived completed tasks without evidence "
                      f"(historical residue): {tasks_list[:10]}")
                if len(tasks_list) > 10:
                    print(f"│    ... and {len(tasks_list) - 10} more")
    else:
        print("│  [PASS] Gate status and evidence are consistent.")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_4_evidence_quality(emit_evidence_quality, check_evidence_quality):
    issue_count = 0
    print("\n┌─ Check 4: Evidence Quality ─────────────────────────┐")
    issue_count += emit_evidence_quality(check_evidence_quality())
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_5_protocol_compliance(check_protocol_compliance):
    issue_count = 0
    print("\n┌─ Check 5: Protocol Compliance (M8 External) ─────────┐")
    pc_issues = check_protocol_compliance()
    pc_count = 0

    if pc_issues["dri_violations"]:
        pc_count += len(pc_issues["dri_violations"])
        print(f"│  [WARN] {len(pc_issues['dri_violations'])} active task(s) with DRI violations:")
        for v in pc_issues["dri_violations"]:
            print(f"│    - {v['task_id']} ({v['status']}): {', '.join(v['violations'])}")
    else:
        print(f"│  [PASS] All active tasks have unique DRI.")



    if pc_issues["evidence_format"]:
        pc_count += len(pc_issues["evidence_format"])
        print(f"│  [WARN] {len(pc_issues['evidence_format'])} evidence entry(ies) with missing required fields:")
        for v in pc_issues["evidence_format"][:10]:  # Limit output
            print(f"│    - {v}")
        if len(pc_issues["evidence_format"]) > 10:
            print(f"│    ... and {len(pc_issues['evidence_format']) - 10} more")
    else:
        print(f"│  [PASS] All evidence entries have required fields.")

    issue_count += pc_count
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_6_tier_audits(check_tier_audit_completeness):
    issue_count = 0
    print("\n┌─ Check 6: Tier Audit Completeness ───────────────────┐")
    tier_result = check_tier_audit_completeness()
    tiers_defined = len(tier_result["all_details"])
    if tiers_defined == 0:
        print(f"│  [INFO] No Tier definitions found in plan-tracker — skip.")
    else:
        print(f"│  Tiers defined: {tiers_defined}")
        ta_issues = 0

        # Completed tiers WITH audit
        for detail in tier_result["completed_with_audit"]:
            print(f"│  [PASS] Tier {detail['tier_id']}: {detail['completed_count']}/{detail['task_count']} tasks completed, audit {detail['audit_evidence_id']} found.")

        # Completed tiers WITHOUT audit
        for detail in tier_result["completed_without_audit"]:
            ta_issues += 1
            issue_count += 1
            print(f"│  [WARN] Tier {detail['tier_id']}: {detail['completed_count']}/{detail['task_count']} tasks completed but NO audit evidence ({detail['audit_evidence_id']}).")
            for tid, status in detail["task_statuses"].items():
                print(f"│    - {tid}: {status}")

        # Incomplete tiers (informational)
        for detail in tier_result["incomplete_tiers"]:
            pending = detail["task_count"] - detail["completed_count"]
            print(f"│  [INFO] Tier {detail['tier_id']}: {detail['completed_count']}/{detail['task_count']} completed, {pending} pending — audit not yet due.")
            for tid, status in detail["task_statuses"].items():
                if status != "已完成":
                    print(f"│    - {tid}: {status}")

        if ta_issues == 0 and tier_result["completed_without_audit"] == []:
            completed_tiers = len(tier_result["completed_with_audit"])
            if completed_tiers > 0:
                print(f"│  [PASS] All {completed_tiers} completed Tier(s) have audit evidence.")
            else:
                print(f"│  [PASS] No completed Tiers without audit evidence.")

    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_8_risk_escalation(emit_risk_escalation, check_risk_escalation):
    issue_count = 0
    print("\n┌─ Check 8: Risk Escalation Deadline ──────────────────┐")
    issue_count += emit_risk_escalation(check_risk_escalation())
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_9_task_deadlines(check_task_deadline):
    issue_count = 0
    print("\n┌─ Check 9: Task Deadline Enforcement ─────────────────┐")
    td_result = check_task_deadline()
    overdue_tasks = td_result["overdue"]
    if overdue_tasks:
        issue_count += len(overdue_tasks)
        print(f"│  [WARN] {len(overdue_tasks)} active task(s) with plan-complete date passed:")
        for t in overdue_tasks:
            print(f"│    - {t['task_id']} ({t['priority']}, {t['status']}): due {t['plan_complete']} ({t['days_overdue']}d overdue)")
    else:
        print(f"│  [PASS] No active tasks with passed plan-complete dates.")
    print(f"│  Total active tasks checked: {td_result['total_active']}")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_12_cross_references(
    product_gate_active, check_cross_references, check_exploration_sample_advisories,
    _print_product_gate_skipped,
):
    issue_count = 0
    if product_gate_active():
        print("\n┌─ Check 12: Cross-Reference Checking ────────────────┐")
        xr_result = check_cross_references()
        print(f"│  Files scanned: {xr_result['total_files_scanned']}")
        print(f"│  References extracted: {xr_result['total_refs']}")
        xr_issues = 0
        if xr_result["dangling"]:
            xr_issues += len(xr_result["dangling"])
            issue_count += len(xr_result["dangling"])
            print(f"│  [WARN] {len(xr_result['dangling'])} dangling reference(s):")
            for d in xr_result["dangling"][:10]:
                print(f"│    - {d['source']}:{d['line']} -> {d['target']}")
            if len(xr_result["dangling"]) > 10:
                print(f"│    ... and {len(xr_result['dangling']) - 10} more")
        else:
            print(f"│  [PASS] No dangling references found.")
        if xr_result["deprecated"]:
            xr_issues += len(xr_result["deprecated"])
            issue_count += len(xr_result["deprecated"])
            print(f"│  [WARN] {len(xr_result['deprecated'])} deprecated path(s):")
            for d in xr_result["deprecated"][:10]:
                print(f"│    - {d['source']}:{d['line']}: {d['target']} ({d['deprecated_pattern']})")
            if len(xr_result["deprecated"]) > 10:
                print(f"│    ... and {len(xr_result['deprecated']) - 10} more")
        else:
            print(f"│  [PASS] No deprecated path patterns found.")
        if xr_result["cycles"]:
            xr_issues += len(xr_result["cycles"])
            issue_count += len(xr_result["cycles"])
            print(f"│  [WARN] {len(xr_result['cycles'])} circular reference(s):")
            for cycle in xr_result["cycles"]:
                print(f"│    - {' -> '.join(cycle)}")
        else:
            print(f"│  [PASS] No circular references found.")
        # FIX-432 (F-4/F-A2) / FIX-436 F-8 wording: citation/note quote-sync
        # guard; the current check_cross_references() always emits the key —
        # .get only tolerates pre-FIX-432/partial dict shapes that lack it.
        xr_quote = xr_result.get("quote_sync", [])
        if xr_quote:
            xr_issues += len(xr_quote)
            issue_count += len(xr_quote)
            print(f"│  [WARN] {len(xr_quote)} quote-sync issue(s):")
            for issue in xr_quote[:10]:
                print(f"│    - {issue}")
            if len(xr_quote) > 10:
                print(f"│    ... and {len(xr_quote) - 10} more")
        else:
            print(f"│  [PASS] Citation/note quote sync clean (FIX-432 F-4/F-A2).")
        # FEAT-088 (F-A3): exploration-channel evidence-form guard sub-face.
        # Issues count toward the gate; advisories (staleness WARNs) are
        # disclosed but deliberately NOT counted — age is not breakage, and
        # counting heuristics here would be the false-alarm class the ticket
        # forbids (探活失败→降级建议输出不误报).
        xr_channels = xr_result.get("exploration_channels", {}) or {}
        xr_channel_issues = xr_channels.get("issues", [])
        if xr_channel_issues:
            xr_issues += len(xr_channel_issues)
            issue_count += len(xr_channel_issues)
            print(f"│  [WARN] {len(xr_channel_issues)} exploration-channel "
                  f"evidence-form issue(s) (FEAT-088 F-A3):")
            for issue in xr_channel_issues[:10]:
                print(f"│    - {issue}")
            if len(xr_channel_issues) > 10:
                print(f"│    ... and {len(xr_channel_issues) - 10} more")
        else:
            print(f"│  [PASS] Exploration-channel evidence forms clean "
                  f"(FEAT-088 F-A3; native declarations of enrolled adapters "
                  f"carry dated anchors — host-tool liveness itself is NOT "
                  f"probed, see check-exploration-channels).")
        for advisory in (xr_channels.get("advisories") or [])[:5]:
            print(f"│  [ADVISORY] {advisory}")
        # FIX-436 (F-B3 / DEC-317): M10.2 sample-report exploration-block
        # presence advisory — WARN-class, disclosed but deliberately NOT
        # counted (same non-blocking discipline as the advisories above).
        for advisory in check_exploration_sample_advisories():
            print(f"│  [ADVISORY] {advisory}")
        if xr_issues == 0:
            print(f"│  [PASS] Cross-reference graph is clean.")
    else:
        _print_product_gate_skipped("Check 12")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_13_sequential_ids(check_sequential_ids, _print_sequential_id_check):
    issue_count = 0
    print("\n┌─ Check 13: Sequential ID Checking ───────────────────┐")
    si_result = check_sequential_ids()
    issue_count += _print_sequential_id_check(si_result)
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_14_structural_validity(check_structural_validity, blocking_structural_issues):
    issue_count = 0
    print("\n┌─ Check 14: Structural Validity ──────────────────────┐")
    sv_issues = check_structural_validity()
    if sv_issues:
        blocking_sv = blocking_structural_issues(sv_issues)
        issue_count += len(blocking_sv)
        warn_sv = [
            i for i in sv_issues
            if str(i.get("severity", "")).upper() in {"WARN", "WARNING"}
        ]
        label = "WARN" if warn_sv else "INFO"
        if blocking_sv:
            label = "FAIL"
        print(f"│  [{label}] {len(sv_issues)} structural issue(s) "
              f"({len(blocking_sv)} blocking):")
        for v in sv_issues[:10]:
            detail = v.get("detail", "")
            ftype = v.get("type", "unknown")
            ffile = v.get("file", "?")
            line_info = f":{v['line']}" if v.get("line") else ""
            print(f"│    - [{ftype}] {ffile}{line_info}: {detail}")
        if len(sv_issues) > 10:
            print(f"│    ... and {len(sv_issues) - 10} more")
        if not blocking_sv:
            print("│  [PASS] No actionable structural issues in current hot schema.")
    else:
        print(f"│  [PASS] All governance files have valid structure.")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_25_untracked_files(check_untracked_files):
    issue_count = 0
    print("\n┌─ Check 25: Untracked Files ──────────────────────────┐")
    uf_result = check_untracked_files()
    if uf_result["pass"] is None:
        print(f"│  [INFO] Skipped: could not run git ls-files.")
    elif uf_result["pass"] is True:
        print(f"│  [PASS] No untracked files found.")
    else:
        count = uf_result["untracked_count"]
        actionable_entry_files = uf_result.get("actionable_entry_files", [])
        issue_count += len(actionable_entry_files)
        if actionable_entry_files:
            print(f"│  [WARN] {count} untracked file(s) detected "
                  f"({len(actionable_entry_files)} actionable entry surface file(s)):")
        else:
            print(f"│  [WARN] {count} untracked file(s) detected (ordinary scratch/non-blocking):")
        # Group by directory
        by_dir = {}
        for f in uf_result["untracked_files"]:
            d = f.rsplit("/", 1)[0] if "/" in f else "(repo root)"
            by_dir.setdefault(d, []).append(f)
        for d in sorted(by_dir.keys()):
            print(f"│    {d}/")
            for fname in sorted(by_dir[d]):
                basename = fname.rsplit("/", 1)[-1] if "/" in fname else fname
                print(f"│      - {basename}")
        # Category suggestions
        if uf_result["suggest_archive"]:
            print(f"│  ── 应归档到仓库（git add）── {len(uf_result['suggest_archive'])} file(s):")
            for f in uf_result["suggest_archive"]:
                print(f"│    - {f}")
        if actionable_entry_files:
            print(f"│  ── 平台原生入口文件（actionable）── {len(actionable_entry_files)} file(s):")
            for f in actionable_entry_files:
                print(f"│    - {f}")
        if uf_result["suggest_temp_script"]:
            print(f"│  ── 可能是临时脚本，确认后归档或添加到 .gitignore ── {len(uf_result['suggest_temp_script'])} file(s):")
            for f in uf_result["suggest_temp_script"]:
                print(f"│    - {f}")
        if uf_result["suggest_manual"]:
            print(f"│  ── 需人工判断 ── {len(uf_result['suggest_manual'])} file(s):")
            for f in uf_result["suggest_manual"]:
                print(f"│    - {f}")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_26_locks(check_agent_lock_consistency, lock_issue_is_blocking):
    issue_count = 0
    print("\n┌─ Check 26: Agent Lock Consistency (FIX-056) ─────────┐")
    al_result = check_agent_lock_consistency()
    al_issue_count = len(al_result.get("issues", []))
    al_blocking = [i for i in al_result.get("issues", []) if lock_issue_is_blocking(i)]
    if al_result.get("skipped"):
        print(f"│  [INFO] Skipped: {al_result['skipped']}")
    elif al_issue_count == 0:
        print(f"│  [PASS] agent-locks.json schema valid, {al_result['active_task_count']} active task(s), "
              f"{al_result['file_lock_count']} file lock(s).")
    else:
        issue_count += len(al_blocking)
        label = "WARN" if al_blocking else "INFO"
        print(f"│  [{label}] {al_issue_count} lock consistency issue(s) "
              f"({len(al_blocking)} blocking):")
        for issue in al_result["issues"]:
            severity = "BLOCKING" if lock_issue_is_blocking(issue) else "WARN"
            print(f"│    - [{severity}:{issue['type']}] {issue['detail']}")
        if al_result["active_task_count"] > 0 or al_result["file_lock_count"] > 0:
            print(f"│  State: {al_result['active_task_count']} active task(s), "
                  f"{al_result['file_lock_count']} file lock(s).")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_27_archives(check_archive_integrity):
    issue_count = 0
    print("\n┌─ Check 27: Archive Integrity (SYSGAP-030) ───────────┐")
    ai_result = check_archive_integrity()
    print(f"│  Hot tasks (plan-tracker): {ai_result['hot_tasks']}")
    print(f"│  Archived tasks: {ai_result['total_archived_tasks']}")
    print(f"│  Index entries: {ai_result['index_entries']}")
    if ai_result.get("pending_archive_tasks", 0):
        print(f"│  Pending archive tasks: {ai_result['pending_archive_tasks']}")
        print(f"│  Archive triggers: {', '.join(ai_result.get('archive_triggers', [])) or 'none'}")
    if ai_result["issues"]:
        issue_count += len(ai_result["issues"])
        print(f"│  [WARN] {len(ai_result['issues'])} archive integrity issue(s):")
        for issue in ai_result["issues"]:
            print(f"│    - {issue}")
    else:
        archive_detail = (
            "no archive data"
            if ai_result["total_archived_tasks"] == 0
            else f"{ai_result['total_expected']} total tasks, index consistent"
        )
        print(f"│  [PASS] Archive integrity verified — {archive_detail}")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_28c_hot_facts(check_hot_fact_source_consistency, _host_plugin_roots_divergent):
    issue_count = 0
    print("\n┌─ Check 28c: Hot Fact-Source Consistency (FIX-087) ───┐")
    hfs_issues = check_hot_fact_source_consistency()
    if _host_plugin_roots_divergent():
        print("│  [INFO] host mode: plugin-project expectations (0.38.0 roadmap/"
              "REQ-070~074/RISK-033/REL-013 + ### 1.0.0 依赖链) not asserted — "
              "governed object is not the plugin project (FIX-270); generic "
              "section/snapshot consistency still checked.")
    if hfs_issues:
        issue_count += len(hfs_issues)
        print(f"│  [FAIL] {len(hfs_issues)} hot fact-source issue(s):")
        for issue in hfs_issues[:10]:
            print(f"│    - {issue}")
        if len(hfs_issues) > 10:
            print(f"│    ... and {len(hfs_issues) - 10} more")
    else:
        print("│  [PASS] Project configuration, release and requirement records are aligned.")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_28g_governance_context(check_governance_context):
    issue_count = 0
    print("\n┌─ Check 28g: Governance Context Discovery (FIX-112) ──┐")
    context_issues = check_governance_context()
    if context_issues:
        issue_count += len(context_issues)
        print(f"│  [FAIL] {len(context_issues)} governance context issue(s):")
        for issue in context_issues[:10]:
            print(f"│    - {issue}")
        if len(context_issues) > 10:
            print(f"│    ... and {len(context_issues) - 10} more")
    else:
        print("│  [PASS] Governance context discovery is fact-based and not-found safe.")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_28s_data_size(
    check_governance_data_size, _exception_registry_error_note, _exception_note,
):
    # Advisory: guards RISK-039 governance data bloat. Inherits
    # gate_integration.fatal_on_error=false — does NOT increment issue_count.
    print("\n┌─ Check 28s: Governance Data Size (FIX-160) ─────────┐")
    gds = check_governance_data_size()
    if gds.get("error"):
        print(f"│  [SKIP] {gds['error']}")
    elif not gds.get("enabled", False):
        print(f"│  [INFO] disabled — {gds.get('note','')}")
    else:
        s = gds["summary"]
        print(f"│  governance files: {s['errors']} ERROR, {s['warnings']} WARN")
        # FEAT-075 R0 F-2: file-level registry errors disclosed once (first
        # finding line); "" when clean — output unchanged.
        gds_err = _exception_registry_error_note()
        gds_err_shown = not gds_err
        for f in gds["findings"][:8]:
            b = f.get("bytes", 0)
            # FEAT-075: annotation-only exception suffix (原始 FAIL 与真实
            # 字节照报; no registry → line identical to pre-FEAT-075).
            gds_note = _exception_note("governance_data_size", f.get('path',''),
                                       f.get('severity'), bytes_value=b)
            if not gds_err_shown:
                gds_note += ("  " if gds_note else "") + gds_err
                gds_err_shown = True
            print(f"│    [{f['severity']}] {f.get('path','')} {b} bytes ({b/1024:.1f} KB){gds_note}".rstrip())
        if (s["errors"] or s["warnings"]):
            print("│  (advisory — fatal_on_error=false; does not block release)")
    print("└──────────────────────────────────────────────────────┘")
    return 0


def section_35_snapshot_freshness(check_snapshot_freshness):
    issue_count = 0
    # Timeline watchdog for the AUDIT-145 "snapshot frozen while governance
    # keeps moving" blind spot (tv/router zero-update cases). S1a missing/
    # unparseable session_date → WARN (fail-safe). S1b snapshot < latest
    # .governance/ commit → WARN (gradual). S1c AND double threshold
    # (age ≥ 7d AND lag ≥ 10 commits) → FAIL. S1d no snapshot → no-verdict.
    # No .governance/ commit baseline (untracked/unversioned) → secondary
    # plan-tracker/evidence-log mtime, FAIL impossible (fail-safe WARN cap);
    # snapshot predating the .governance history (adoption edge) → WARN.
    # Orthogonal to Check 28c (vs latest published release) and Check 34
    # (recommendation closure) — independent judgement, no swallowing.
    print("\n┌─ Check 35: Snapshot Freshness (FIX-268) ─────────────┐")
    cr35 = check_snapshot_freshness()
    st35 = cr35["stats"]
    baseline = st35["commit_date"] or st35["mtime_date"] or "none"
    lag = "—" if st35["lag_commits"] is None else str(st35["lag_commits"])
    age = "—" if st35["age_days"] is None else f"{st35['age_days']}d"
    print(f"│  Snapshot: {st35['session_date'] or '—'} (age: {age}; "
          f"baseline: {baseline}; commit lag: {lag})")
    print(f"│  Verdict: {cr35['verdict']}")
    if cr35["violations"]:
        issue_count += len(cr35["violations"])
        print(f"│  [FAIL] {len(cr35['violations'])} violation(s):")
        for v in cr35["violations"][:8]:
            print(f"│    - [{v['rule']}] {v['reason']}")
    elif cr35["warnings"]:
        print(f"│  [WARN] {len(cr35['warnings'])} warning(s):")
        for w in cr35["warnings"][:8]:
            print(f"│    - [{w['rule']}] {w['reason']}")
    else:
        print(f"│  [{cr35['verdict']}] {cr35['reason']}")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_36_risk_mitigation(
    emit_risk_mitigation_closure, check_risk_mitigation_closure_with_archive,
):
    issue_count = 0
    print("\n┌─ Check 36: Risk Mitigation Closure (FIX-265) ───────┐")
    issue_count += emit_risk_mitigation_closure(check_risk_mitigation_closure_with_archive())
    print("└──────────────────────────────────────────────────────┘")
    return issue_count
