"""Full governance report sections for review, agent execution, and working policy."""


def section_10_user_questions(
    product_gate_active, check_m5_compliance_with_record_scope, _print_product_gate_skipped,
):
    issue_count = 0
    # FIX-295 (AUDIT-149 N6) / FIX-348: the gate consumes the record-scope
    # wrapper — issues from docs/release/**, docs/reviews/** and
    # docs/requirements/** (record-class text: release/review documents and
    # delivered design docs) are exempted WITH disclosure ([EXEMPT]
    # below, not counted into issue_count); the base scan and every other
    # M5 face (inline-question instructions, structural checks) unchanged.
    if product_gate_active():
        print("\n┌─ Check 10: M5 AskUserQuestion Compliance ────────────┐")
        m5_result = check_m5_compliance_with_record_scope()
        m5_issues = m5_result["issues"]
        if m5_issues:
            blocking = [i for i in m5_issues if i["severity"] == "BLOCKING"]
            errors = [i for i in m5_issues if i["severity"] == "ERROR"]
            warnings = [i for i in m5_issues if i["severity"] == "WARNING"]
            issue_count += len(blocking) + len(errors)
            if blocking:
                print(f"│  [BLOCKING] {len(blocking)} M5 anti-pattern(s) — source files containing")
                print(f"│             inline question instructions (M5.1 violation):")
                for b in blocking:
                    print(f"│    - {b['file']}:{b['line']}: {b['text'][:80]}")
                    print(f"│      Fix: {b['fix']}")
            if errors:
                print(f"│  [ERROR] {len(errors)} M5 structural gap(s):")
                for e in errors:
                    print(f"│    - {e['file']}: {e['text'][:80]}")
            if warnings:
                print(f"│  [WARN] {len(warnings)} M5 coverage warning(s):")
                for w in warnings:
                    print(f"│    - {w['file']}: {w['text'][:80]}")
        else:
            print(f"│  [PASS] No M5 anti-patterns in source files.")
            print(f"│  [PASS] M5 AskUserQuestion rules present in bootstrap.")
            print(f"│  [PASS] interaction-boundary.md has AskUserQuestion bindings.")
        if m5_result.get("record_scope_exempted"):
            exempted = m5_result["record_scope_exempted"]
            print(f"│  [EXEMPT] {len(exempted)} record-doc M5 issue(s) — FIX-295 path "
                  f"whitelist {', '.join(m5_result['record_scope_dirs'])} "
                  f"(record text, not agent instructions; disclosed, not counted):")
            for e in exempted[:8]:
                print(f"│    - {e['file']}:{e['line']}: {e['text'][:70]}")
            if len(exempted) > 8:
                print(f"│    ... and {len(exempted) - 8} more")
        print(f"│  Total M5 checks: {m5_result['total_checks']}")
    else:
        _print_product_gate_skipped("Check 10")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_19_team_review(check_agent_team_review):
    issue_count = 0
    print("\n┌─ Check 19: Agent Team Review ────────────────────────┐")
    atr_result = check_agent_team_review()
    print(f"│  Product-code tasks (completed): {atr_result['total_tasks']}")
    print(f"│  Reviewed: {atr_result['reviewed']}")
    if atr_result.get("ignored_review_entries"):
        print(f"│  Ignored degraded/self-review entries: {len(atr_result['ignored_review_entries'])}")
        for entry in atr_result["ignored_review_entries"][:5]:
            print(f"│    - {entry['source']}: {entry['reason']}")
    if atr_result["unreviewed"] > 0:
        issue_count += atr_result["unreviewed"]
        print(f"│  [FAIL] {atr_result['unreviewed']} product-code task(s) without review evidence:")
        for tid in atr_result["review_gap_tasks"]:
            print(f"│    - {tid}")
    else:
        if atr_result["total_tasks"] > 0:
            print(f"│  [PASS] All product-code tasks have review evidence.")
        else:
            print(f"│  [PASS] No product-code tasks to review.")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_20_agent_activation(check_agent_activation):
    issue_count = 0
    print("\n┌─ Check 20: Agent Activation (Analyst/Architect) ─────┐")
    aa_result = check_agent_activation()
    print(f"│  P0 cross-layer product tasks: {aa_result['total_p0_cross_layer']}")
    print(f"│  Analyst activated: {aa_result['analyst_activated']}")
    if aa_result["analyst_bypassed"] > 0:
        issue_count += aa_result["analyst_bypassed"]
        print(f"│  [FAIL] {aa_result['analyst_bypassed']} task(s) with impact analysis but no Analyst:")
        for tid in aa_result["bypassed_tasks"]:
            print(f"│    - {tid}")
    else:
        if aa_result["total_p0_cross_layer"] > 0:
            print(f"│  [PASS] All P0 cross-layer tasks have Analyst involvement.")
        else:
            print(f"│  [PASS] No P0 cross-layer product tasks to check.")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_21_review_debt(check_review_debt, DEGRADED_FUSE_THRESHOLD):
    issue_count = 0
    print("\n┌─ Check 21: Review Debt / Spawn Gap (FIX-174) ───────┐")
    rd_result = check_review_debt()
    print(f"│  Product-code tasks (all, with evidence): {rd_result['total_tasks']}")
    print(f"│  Review debt (have execution evidence, no review): {rd_result['review_debt_count']}")
    # FIX-174 (DEC-094): spawn-gap (M7.4 step 4.5b) + degraded-fuse (step 4.6).
    if rd_result["review_debt_count"] > 0:
        issue_count += rd_result["review_debt_count"]
        print(f"│  [FAIL] {rd_result['review_debt_count']} product-code task(s) with review debt:")
        for tid in rd_result["review_debt_tasks"]:
            print(f"│    - {tid}")
    if rd_result.get("degraded_fuse_tasks"):
        fuse_count = len(rd_result["degraded_fuse_tasks"])
        issue_count += fuse_count
        print(f"│  [FAIL] {fuse_count} task(s) hit degraded-fuse "
              f"(≥{DEGRADED_FUSE_THRESHOLD} degraded reviews, M7.4 step 4.6):")
        for tid in rd_result["degraded_fuse_tasks"]:
            print(f"│    - {tid}")
    if rd_result["review_debt_count"] == 0 and not rd_result.get("degraded_fuse_tasks"):
        if rd_result["total_tasks"] > 0:
            print(f"│  [PASS] All product-code tasks have review evidence.")
        else:
            print(f"│  [PASS] No product-code tasks to check.")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_22_review_coverage(check_review_coverage):
    issue_count = 0
    print("\n┌─ Check 22: Review Coverage (FIX-037) ────────────────┐")
    rc_result = check_review_coverage()
    print(f"│  Product code tasks: {rc_result['total_tasks']}")
    print(f"│  Tasks with review evidence: {rc_result['reviewed']}")
    print(f"│  Coverage: {rc_result['coverage_pct']}%")
    if rc_result["unreviewed"] > 0:
        issue_count += rc_result["unreviewed"]
        print(f"│  [WARN] {rc_result['unreviewed']} unreviewed product-code task(s):")
        for tid in rc_result["unreviewed_tasks"]:
            print(f"│    - {tid}")
    else:
        if rc_result["total_tasks"] > 0:
            print(f"│  [PASS] Review coverage = 100% — all product-code tasks reviewed.")
        else:
            print(f"│  [PASS] No product-code tasks to check.")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_23_profile(check_profile_consistency):
    issue_count = 0
    print("\n┌─ Check 23: Profile Consistency (FIX-038) ────────────┐")
    pc_result = check_profile_consistency()
    print(f"│  Profile: {pc_result['profile']}")
    if pc_result["issues"]:
        issue_count += len(pc_result["issues"])
        print(f"│  [WARN] {len(pc_result['issues'])} profile consistency issue(s):")
        for issue in pc_result["issues"]:
            print(f"│    - {issue}")
    else:
        print(f"│  [PASS] Profile declaration matches actual structure.")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_28_review_fallback(check_governance_review_fallback_policy):
    issue_count = 0
    print("\n┌─ Check 28: Governance Review Fallback Policy ────────┐")
    gr_result = check_governance_review_fallback_policy()
    print(f"│  Command files checked: {gr_result['files_checked']}")
    if gr_result["optional_skipped"]:
        print(f"│  Optional fixture skipped: {len(gr_result['optional_skipped'])}")
        for skipped in gr_result["optional_skipped"]:
            print(f"│    - {skipped}")
    if gr_result["issues"]:
        issue_count += len(gr_result["issues"])
        print(f"│  [FAIL] {len(gr_result['issues'])} /governance-review fallback policy issue(s):")
        for issue in gr_result["issues"]:
            print(f"│    - [{issue['type']}] {issue['file']}: {issue['detail']}")
    else:
        print("│  [PASS] Reviewer unavailable path blocks or records degraded evidence only.")
        print("│  [PASS] Coordinator self-review fallback is not allowed.")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_29_runtime_triggers(check_m5_runtime_triggers):
    issue_count = 0
    # Best-effort scan of session-snapshot / evidence-log corpus. Falls back to
    # no-verdict when no corpus is available (P1-b). Does not over-claim in CI.
    print("\n┌─ Check 29: M5 Runtime Triggers (FIX-174) ───────────┐")
    m5rt = check_m5_runtime_triggers()
    print(f"│  Scanned segments: {m5rt['scanned_segments']}")
    print(f"│  Verdict: {m5rt['verdict']}")
    if m5rt["violations"]:
        issue_count += len(m5rt["violations"])
        print(f"│  [FAIL] {len(m5rt['violations'])} M5 runtime violation(s):")
        for v in m5rt["violations"]:
            print(f"│    - [{v['trigger']}] {v['source']}: {v['reason']}")
    elif m5rt["warnings"]:
        print(f"│  [WARN] {len(m5rt['warnings'])} M5.4b notification-prefix WARN(s):")
        for w in m5rt["warnings"]:
            print(f"│    - [{w['trigger']}] {w['source']}: {w['reason']}")
    else:
        print(f"│  [{m5rt['verdict']}] {m5rt['reason']}")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_30_review_closure(check_review_closure):
    issue_count = 0
    # Validates M7.4 step 4.6 closure: V1 terminal legality, V2 round
    # continuity, V3 fuse (MAX_ROUNDS=3), V4 APPROVED traceability.
    print("\n┌─ Check 30: Review Closure State Machine (FIX-174) ──┐")
    rc30 = check_review_closure()
    print(f"│  Tasks with review sequences: {rc30['tasks_checked']}")
    print(f"│  Verdict: {rc30['verdict']}")
    if rc30["violations"]:
        issue_count += len(rc30["violations"])
        print(f"│  [FAIL] {len(rc30['violations'])} closure violation(s):")
        for v in rc30["violations"]:
            print(f"│    - [{v['rule']}] {v.get('task_id','')}: {v['reason']}")
    elif rc30["warnings"]:
        print(f"│  [WARN] {len(rc30['warnings'])} closure WARN(s):")
        for w in rc30["warnings"]:
            print(f"│    - [{w['rule']}] {w.get('task_id','')}: {w['reason']}")
    else:
        print(f"│  [{rc30['verdict']}] {rc30['reason']}")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_30c_review_provenance(check_review_machine_provenance):
    issue_count = 0
    # V7: REVIEW rows / review files without the review-record CLI machine
    # marker → FAIL since 0.97.0 (DEC-146 ② escalation delivered by
    # FEAT-089; DEC exemption list absorbs the 2026-08-22 residual rows —
    # DEC-146 ②/DEC-321). V8: NEEDS_CHANGE records without the machine
    # next_round revisit field → FAIL (escalated with V7). V6d tightening:
    # undated records → WARN (never issue_count — DEC-146 ③ baseline).
    # EXEMPTION-SIDE-RECORD: the DEC-146 ④ side record must pin the live
    # exemption list (hash mismatch → FAIL, fail-closed). The escalation
    # decision face (coverage × releases) is recomputable from the stats.
    print("\n┌─ Check 30c: Review Machine Provenance (FIX-260) ────┐")
    mp30c = check_review_machine_provenance()
    _esc30c = mp30c["stats"].get("escalation", {})
    print(f"│  Rows judged: {mp30c['stats']['rows_judged']} "
          f"(machine {mp30c['stats']['rows_machine']}, "
          f"exempted {mp30c['stats'].get('rows_exempted', 0)}, "
          f"undated {mp30c['stats']['rows_undated']}, "
          f"non-review {mp30c['stats'].get('rows_non_review', 0)}); "
          f"files judged: {mp30c['stats']['files_judged']} "
          f"(machine {mp30c['stats'].get('files_machine', 0)}, "
          f"legacy {mp30c['stats']['files_legacy_skipped']}, "
          f"undated {mp30c['stats']['files_undated']}, "
          f"unmatched {mp30c['stats']['files_unmatched']})")
    if _esc30c:
        print(f"│  Escalation (DEC-146 ②, since {_esc30c.get('since_version')}): "
              f"coverage raw {_esc30c['coverage_raw']['numerator']}/"
              f"{_esc30c['coverage_raw']['denominator']} "
              f"({_esc30c['coverage_raw']['pct']}%), exemption-honored "
              f"{_esc30c['coverage_exemption_honored']['numerator']}/"
              f"{_esc30c['coverage_exemption_honored']['denominator']} "
              f"({_esc30c['coverage_exemption_honored']['pct']}%) × "
              f"{_esc30c['releases_since_effective_date']} release(s) since "
              f"{_esc30c.get('effective_date')} → condition_met="
              f"{_esc30c.get('condition_met')}; side record "
              f"{'verified' if _esc30c.get('side_record', {}).get('verified') else 'NOT verified'}")
    print(f"│  Verdict: {mp30c['verdict']}")
    if mp30c.get("violations"):
        issue_count += len(mp30c["violations"])
        shown = mp30c["violations"][:8]
        print(f"│  [FAIL] {len(mp30c['violations'])} machine-provenance "
              f"violation(s) (showing first {len(shown)}):")
        for v in shown:
            print(f"│    - [{v['rule']}] {v.get('task_id','')}: {v['reason']}")
        if len(mp30c["violations"]) > 8:
            print(f"│    ... and {len(mp30c['violations']) - 8} more")
    if mp30c["warnings"]:
        shown = mp30c["warnings"][:8]
        print(f"│  [WARN] {len(mp30c['warnings'])} undated-record WARN(s)"
              f" (V6d tightening, showing first {len(shown)}):")
        for w in shown:
            print(f"│    - [{w['rule']}] {w.get('task_id','')}: {w['reason']}")
        if len(mp30c["warnings"]) > 8:
            print(f"│    ... and {len(mp30c['warnings']) - 8} more")
        print("│  (undated → WARN never increments issue_count — DEC-146 ③ "
              "accepted baseline)")
    if not mp30c.get("violations") and not mp30c["warnings"]:
        print(f"│  [{mp30c['verdict']}] {mp30c['reason']}")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_30b_loop_wiring(product_gate_active, check_loop_wiring_call_sites):
    issue_count = 0
    if product_gate_active():
        wiring_calls = check_loop_wiring_call_sites()
        if wiring_calls["verdict"] != "PASS":
            issue_count += 1
        print(f"│  [{wiring_calls['verdict']}] Check 30b native receipt routing: {wiring_calls['reason']}")
    else:
        print("│  [SKIP] Check 30b native receipt routing; enable with --product-gates")
    return issue_count


def section_39_completion_gate(check_r1_completion_gate):
    # Downstream machine consumer of change-triage's requires_r1 flag
    # (R0 F-03 / BC-2): a task marked completed with
    # analysis.side_effect.requires_r1=true MUST carry R1 留痕 evidence
    # (one-of-three fact: isolation redirect / backup + verification /
    # per-item user authorization — keyword match). Missing → WARN during
    # the DEC-159 observation window (Check 30c convention: WARN does NOT
    # increment issue_count); tightening condition registered in
    # checks/triage_domain.py — escalation to FAIL after 2 consecutive
    # 0.77.x releases close with zero r1-evidence violations.
    print("\n┌─ Check 39: R1 Completion Gate (FIX-274) ────────────┐")
    cr39 = check_r1_completion_gate()
    st39 = cr39["stats"]
    print(f"│  Triage records scanned: {st39['records_scanned']} "
          f"(requires_r1: {st39['r1_records']}; judged: "
          f"{st39['tasks_judged']} = pass {st39['pass']} + warn "
          f"{st39['warn']}; skipped: {st39['tasks_skipped_incomplete']} "
          f"incomplete + {st39['tasks_skipped_unlanded']} unlanded)")
    print(f"│  Verdict: {cr39['verdict']}")
    if cr39["warnings"]:
        print(f"│  [WARN] {len(cr39['warnings'])} missing R1 evidence row(s):")
        for w in cr39["warnings"][:8]:
            print(f"│    - [{w['rule']}] {w['task_id']}: {w['reason']}")
        if len(cr39["warnings"]) > 8:
            print(f"│    ... and {len(cr39['warnings']) - 8} more")
        print("│  (gradual severity — WARN in the 0.77.x observation window; "
              "escalates to FAIL after 2 consecutive violation-free 0.77.x "
              "releases per DEC-159)")
    else:
        print(f"│  [{cr39['verdict']}] {cr39['reason']}")
    print("└──────────────────────────────────────────────────────┘")
    return 0


def section_41_priority_inversion(_provenance_rows_for_governance):
    issue_count = 0
    # Host-rooted facts (plan-tracker + .governance triage/revision
    # streams) — never in _PLUGIN_PRODUCT_CHECK_IDS. INV-1 FAILs only on
    # a PROVEN same-P-level inversion (FEAT-080 R0-revision qualifier);
    # INV-X discloses cross-level pressure as WARN (the D1 known
    # tolerance — the sort never crosses P levels; the terminal
    # interception lives with the release gate); INV-2 fails on a parked
    # user-named item while machine-signal fills the recommended board.
    print("\n┌─ Check 41: Priority Inversion Guard (FEAT-080/ADR-021) ─┐")
    from checks.provenance_domain import check_priority_inversion
    rows41 = _provenance_rows_for_governance()
    if not rows41:
        print("│  [SKIP] plan-tracker 不可读或零任务行——反倒挂判定无判定面")
    else:
        inv41 = check_priority_inversion(rows41)
        cov41 = inv41["coverage"]
        print(f"│  Rows judged: {cov41['total']} (labeled: "
              f"{cov41['labeled']}, coverage {cov41['ratio']:.0%})")
        if inv41["status"] == "FAIL":
            issue_count += len(inv41["issues"])
            print(f"│  [FAIL] {len(inv41['issues'])} issue(s):")
            for issue in inv41["issues"][:8]:
                print(f"│    - {issue}")
            if len(inv41["issues"]) > 8:
                print(f"│    ... and {len(inv41['issues']) - 8} more")
        elif inv41["status"] == "SKIP":
            print("│  [SKIP] " + (inv41["warnings"][0] if inv41["warnings"]
                                else "coverage 0"))
        else:
            print("│  [PASS] 无同级倒挂（INV-1）/停放倒挂（INV-2）命中")
        for warning in inv41["warnings"][:6]:
            if inv41["status"] != "SKIP":
                print(f"│  [WARN] {warning}")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_42_discovery_closure(_collect_session_closure_events, _DEFERRED_LEDGER_FILENAME):
    # DEC-288 M2 effectiveness criterion, machine form
    # ``session_closure_rate == 1.0 ∧ deferred_detections == 0``. Event
    # sources = today's evidence/risk row families (deterministic column
    # matching — see _collect_session_closure_events) PLUS the B4 M2
    # observation ledger's fired deferred_hit entries (FEAT-081: the
    # deferred count is a REAL signal now, not a structural zero);
    # <100% is WARN in the observation window (渐进 FAIL 翻转经
    # decision-log 入账, ADR §3.2.1 姿态), never silently skipped. SKIP
    # 语义分态 (CR-R1-2): vacuum (无观测义务) vs orchestration_fallback
    # (检测面数据缺失——台账不可读/行族读取失败) are attributed and
    # disclosed distinctly; a deferred signal suppresses SKIP entirely.
    print("\n┌─ Check 42: Discovery Closure Rate (FEAT-080/ADR-021) ──┐")
    from checks.provenance_domain import session_closure_rate
    from checks.loop_gate_processor import (
        SKIP_ORCHESTRATION_FALLBACK as _SKIP_FALLBACK_42,
        classify_observation_face as _classify42,
    )
    events42, window_note42, face_state42 = _collect_session_closure_events()
    rate42 = session_closure_rate(events42)
    skip42 = _classify42(rate42["problems_raised"],
                         rate42["deferred_detections"],
                         face_state42["anomaly"])
    if skip42 is not None and skip42["skip_kind"] != _SKIP_FALLBACK_42:
        print(f"│  [SKIP] {skip42['reason']}（skip_kind=vacuum；"
              f"{window_note42}）")
    elif skip42 is not None:
        # Orchestration fallback — disclosed WARN, never a plain SKIP and
        # never a silent zero (CR-R1-2: 编排异常兜底 ≠ 真空面).
        print(f"│  {window_note42}")
        print(f"│  [WARN] {skip42['reason']}")
        print("│  deferred 检测面数据缺失——按降级披露（不静默），修复台账/"
              "行族读取后复跑（ADR-021 §2.4 / FEAT-081 CR-R1-2）")
    else:
        print(f"│  {window_note42}")
        print(f"│  problems raised: {rate42['problems_raised']}; closed: "
              f"{rate42['closed']}; rate: "
              f"{rate42['session_closure_rate']:.0%}; deferred detections: "
              f"{rate42['deferred_detections']}（词集检测面 B4 已落地——"
              "台账信号路径，FEAT-081）")
        if rate42["compliant"]:
            print("│  [PASS] session_closure_rate == 1.0 ∧ "
                  "deferred_detections == 0（DEC-288 M2 生效判据）")
        else:
            print("│  [WARN] 闭环率 <100% 或 deferred 检测 >0——观察期 WARN "
                  "起步，渐进 FAIL 翻转经 decision-log 入账（ADR-021 §3.2.3）")
            for unclosed in rate42["unclosed_ids"][:5]:
                print(f"│    - unclosed: {unclosed}")
            if rate42["deferred_detections"]:
                print(f"│    - deferred_registration ×"
                      f"{rate42['deferred_detections']}：详见 "
                      f".governance/{_DEFERRED_LEDGER_FILENAME}"
                      "（三键台账，词集/窗口经 RT-5 数据回流调优）")
    print("└──────────────────────────────────────────────────────┘")
    return 0
