"""Full governance report sections for delivery contracts, evidence, and acceptance."""


def _report_task_contract(result, count_label, ready, empty, passed):
    print(f"│  {count_label}: {len(result['required_tasks'])}")
    issues = 0
    if result["issues"]:
        issues += len(result["issues"])
        for issue in result["issues"]:
            print(f"│  [FAIL] {issue}")
    for entry in result["entries"]:
        if entry["status"] == "FAIL":
            issues += 1
            print(f"│  [FAIL] {entry['task_id']}: {', '.join(entry['issues'])}")
        else:
            print(f"│  [PASS] {entry['task_id']}: {ready}")
    if not result["required_tasks"]:
        print(f"│  [PASS] {empty}")
    elif not issues:
        print(f"│  [PASS] {passed}")
    return issues


def section_16_goal_alignment(check_goal_alignment):
    issue_count = 0
    print("\n┌─ Check 16: Goal Alignment ───────────────────────────┐")
    ga_result = check_goal_alignment()
    ga_issues = 0
    if not ga_result["has_project_goal"]:
        print(f"│  [WARN] plan-tracker missing 项目目标 field.")
        ga_issues += 1
    else:
        project_goal_short = ga_result["project_goal"][:60]
        print(f"│  [INFO] 项目目标: {project_goal_short}...")
    print(f"│  Impact analysis entries: {len(ga_result['entries'])}")
    ga_exempted = ga_result.get("historical_exempted", [])
    print(f"│  Historical exempted (FIX-371/DEC-227 ✅-terminal + FIX-390 writer-committed, skipped): {len(ga_exempted)}")
    for row in ga_exempted[:8]:
        print(f"│    - {row['task_id']} ({row['evd_id']}): {row['status']}")
    if len(ga_exempted) > 8:
        print(f"│    ... and {len(ga_exempted) - 8} more")
    if ga_result["entries"]:
        for e in ga_result["entries"]:
            if e["status"] == "FAIL":
                ga_issues += 1
                if not e["has_goal"]:
                    print(f"│  [FAIL] {e['task_id']} ({e['evd_id']}): 缺少 目标对齐: 字段")
                else:
                    print(f"│  [FAIL] {e['task_id']} ({e['evd_id']}): 目标对齐: 仅 {e['goal_len']} chars (需 >= 30)")
            elif e["status"] == "PASS":
                print(f"│  [PASS] {e['task_id']} ({e['evd_id']}): {e['goal_len']} chars")
        if ga_result["duplicates"]:
            print(f"│  [WARN] {len(ga_result['duplicates'])} duplicate goal alignment(s) (template reuse):")
            for t1, t2 in ga_result["duplicates"][:5]:
                print(f"│    - {t1} <-> {t2}")
            if len(ga_result["duplicates"]) > 5:
                print(f"│    ... and {len(ga_result['duplicates']) - 5} more")
    else:
        print(f"│  [PASS] No impact analysis entries to check.")
    if ga_issues == 0 and ga_result["has_project_goal"]:
        print(f"│  [PASS] Goal alignment check passed.")
    issue_count += ga_issues
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_17_user_impact(check_user_impact):
    issue_count = 0
    print("\n┌─ Check 17: User Impact ──────────────────────────────┐")
    ui_result = check_user_impact()
    ui_issues = 0
    print(f"│  Impact analysis entries: {len(ui_result['entries'])}")
    ui_exempted = ui_result.get("historical_exempted", [])
    print(f"│  Historical exempted (FIX-371/DEC-227 ✅-terminal + FIX-390 writer-committed, skipped): {len(ui_exempted)}")
    for row in ui_exempted[:8]:
        print(f"│    - {row['task_id']} ({row['evd_id']}): {row['status']}")
    if len(ui_exempted) > 8:
        print(f"│    ... and {len(ui_exempted) - 8} more")
    if ui_result["entries"]:
        for e in ui_result["entries"]:
            if e["status"] == "BLOCKING":
                ui_issues += 1
                issue_count += 1
                for issue in e["issues"]:
                    print(f"│  [BLOCKING] {e['task_id']} ({e['evd_id']}): {issue}")
            elif e["status"] == "FAIL":
                ui_issues += 1
                issue_count += 1
                for issue in e["issues"]:
                    print(f"│  [FAIL] {e['task_id']} ({e['evd_id']}): {issue}")
            elif e["status"] == "WARN":
                for issue in e["issues"]:
                    print(f"│  [WARN] {e['task_id']} ({e['evd_id']}): {issue}")
            else:
                print(f"│  [PASS] {e['task_id']} ({e['evd_id']}): "
                      f"获得={e['obtain']}, 体验变化={e['exp_change']}, "
                      f"迁移指南={e['migration']}")
    else:
        print(f"│  [PASS] No impact analysis entries to check.")
    if ui_issues == 0:
        print(f"│  [PASS] User impact check passed.")
    issue_count += ui_issues
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_18_fact_grounding(check_fact_grounding):
    issue_count = 0
    print("\n┌─ Check 18: Fact Grounding (FIX-080) ─────────────────┐")
    fg_result = check_fact_grounding()
    fg_issues = 0
    print(f"│  Current-release evidence entries: {len(fg_result['entries'])}")
    if fg_result["entries"]:
        for e in fg_result["entries"]:
            if e["status"] == "FAIL":
                fg_issues += 1
                for issue in e["issues"]:
                    print(f"│  [FAIL] {e['task_id']} ({e['evd_id']}): {issue}")
            else:
                print(f"│  [PASS] {e['task_id']} ({e['evd_id']}): 事实依据 {e['fact_len']} chars")
    else:
        print("│  [PASS] No current-release product evidence to check.")
    if fg_issues == 0:
        print("│  [PASS] Fact grounding check passed.")
    issue_count += fg_issues
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_18b_structured_evidence(check_structured_evidence):
    issue_count = 0
    print("\n┌─ Check 18b: Structured Evidence (FIX-083) ───────────┐")
    se_result = check_structured_evidence()
    se_issues = 0
    print(f"│  Current-release product evidence entries: {len(se_result['entries'])}")
    if se_result["entries"]:
        for e in se_result["entries"]:
            if e["status"] == "FAIL":
                se_issues += 1
                for issue in e["issues"]:
                    print(f"│  [FAIL] {e['task_id']} ({e['evd_id']}): {issue}")
            else:
                print(f"│  [PASS] {e['task_id']} ({e['evd_id']}): "
                      f"{e['commands']} command(s), {e['files_changed']} file(s)")
    else:
        print("│  [PASS] No current-release product evidence to check.")
    if se_issues == 0:
        print("│  [PASS] Structured evidence check passed.")
    issue_count += se_issues
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_18c_execution_packets(check_execution_packets):
    print("\n┌─ Check 18c: AI Execution Packet (FIX-084) ───────────┐")
    issues = _report_task_contract(
        check_execution_packets(), "Required active P0/P1 packet(s)", "execution packet ready",
        "No active P0/P1 tasks require execution packets.", "Execution packet check passed.",
    )
    print("└──────────────────────────────────────────────────────┘")
    return issues


def section_18d_product_outcomes(check_product_success_contracts, render_rb2_goal_contract_block):
    print("\n┌─ Check 18d: Product Success Contract (FIX-088) ──────┐")
    issues = _report_task_contract(
        check_product_success_contracts(), "Required active P0/P1 contract(s)", "product success contract ready",
        "No active P0/P1 tasks require product success contracts.", "Product success contract check passed.",
    )
    print("└──────────────────────────────────────────────────────┘")
    render_rb2_goal_contract_block()
    return issues


def section_18e_acceptance(check_acceptance_contracts):
    print("\n┌─ Check 18e: Executable Acceptance Contract (FIX-089) ┐")
    issues = _report_task_contract(
        check_acceptance_contracts(), "Required active P0/P1 acceptance contract(s)", "acceptance contract ready",
        "No active P0/P1 tasks require acceptance contracts.", "Executable acceptance contract check passed.",
    )
    print("└──────────────────────────────────────────────────────┘")
    return issues


def section_18f_quality_budget(check_quality_budget):
    print("\n┌─ Check 18f: Quality Budget Gate (FIX-090) ───────────┐")
    issues = _report_task_contract(
        check_quality_budget(), "Required active P0/P1 quality budget(s)", "quality budget ready",
        "No active P0/P1 tasks require quality budgets.", "Quality budget check passed.",
    )
    print("└──────────────────────────────────────────────────────┘")
    return issues


def section_18g_vertical_slices(check_vertical_slices):
    print("\n┌─ Check 18g: Vertical Slice Delivery Packets (FIX-091) ┐")
    issues = _report_task_contract(
        check_vertical_slices(), "Required active P0/P1 vertical slice(s)", "vertical slice ready",
        "No active P0/P1 tasks require vertical slices.", "Vertical slice check passed.",
    )
    print("└──────────────────────────────────────────────────────┘")
    return issues


def section_18h_scaffolds(check_deterministic_scaffolds):
    issue_count = 0
    print("\n┌─ Check 18h: Weak-LLM Deterministic Scaffolds (FIX-092) ┐")
    scaffold_result = check_deterministic_scaffolds()
    scaffold_issues = len(scaffold_result["issues"])
    print(f"│  Required scaffold type(s): {len(scaffold_result['required_types'])}")
    for issue in scaffold_result["issues"]:
        print(f"│  [FAIL] {issue}")
    for entry in scaffold_result["entries"]:
        if entry["status"] == "FAIL":
            scaffold_issues += 1
            print(f"│  [FAIL] {entry['scaffold_type']}: {', '.join(entry['issues'])}")
        else:
            print(f"│  [PASS] {entry['scaffold_type']}: deterministic scaffold ready")
    if scaffold_issues == 0:
        print("│  [PASS] Deterministic scaffold check passed.")
    issue_count += scaffold_issues
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_18i_interruption_policy(check_interruption_policy):
    issue_count = 0
    print("\n┌─ Check 18i: User Interruption Policy v2 (FIX-093) ───┐")
    interruption_result = check_interruption_policy()
    interruption_issues = len(interruption_result["issues"])
    print(f"│  Policy example(s): {len(interruption_result['examples'])}")
    print(f"│  Active packet policy field(s): {len(interruption_result['required_tasks'])}")
    for issue in interruption_result["issues"]:
        print(f"│  [FAIL] {issue}")
    for example in interruption_result["examples"]:
        if example["actual_action"] == example["expected_action"]:
            print(f"│  [PASS] {example['id']}: {example['actual_action']}")
        else:
            interruption_issues += 1
            print(f"│  [FAIL] {example['id']}: expected {example['expected_action']}, got {example['actual_action']}")
    for entry in interruption_result["entries"]:
        if entry["status"] == "FAIL":
            interruption_issues += 1
            print(f"│  [FAIL] {entry['task_id']}: {', '.join(entry['issues'])}")
        else:
            print(f"│  [PASS] {entry['task_id']}: interruption policy ready")
    if interruption_issues == 0:
        print("│  [PASS] User interruption policy check passed.")
    issue_count += interruption_issues
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_32_change_triage(check_change_triage):
    issue_count = 0
    # Mandatory four-step triage for product-code task intake: the
    # change-triage CLI must stay wired, every record must be valid, and a
    # product-code task with post-normalization evidence but NO triage
    # record FAILs (fail-closed — the task must not have been created).
    print("\n┌─ Check 32: Change-Control Triage (FIX-237.4) ────────┐")
    ct32 = check_change_triage()
    print(f"│  CLI wiring: {ct32['wiring']['reason']}")
    print(f"│  Records checked: {ct32['records_checked']}; "
          f"invalid: {ct32['records_invalid']}")
    print(f"│  Tasks without triage record: {len(ct32['tasks_without_record'])}; "
          f"exempt: {ct32['tasks_exempt']}")
    if ct32["issues"]:
        issue_count += len(ct32["issues"])
        print(f"│  [FAIL] {len(ct32['issues'])} change-control triage issue(s):")
        for issue in ct32["issues"]:
            print(f"│    - {issue}")
    else:
        print("│  [PASS] change-triage wiring + record validity + "
              "intake enforcement OK.")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_34_completion_recommendations(check_completion_recommendation):
    issue_count = 0
    # S1: completed product-code task (dated on/after the effective date)
    # without a recommendation-snapshot row → FAIL. S2: session-snapshot
    # 下次会话优先级 without a snapshot id reference → WARN (gradual). S3:
    # dangling snapshot reference → FAIL.
    print("\n┌─ Check 34: Completion Recommendation (FIX-262) ─────┐")
    cr34 = check_completion_recommendation()
    st = cr34["stats"]
    print(f"│  Completions judged: {st['completions_judged']} "
          f"(snapshots: {st['snapshots_machine']} machine + "
          f"{st['snapshots_legacy']} legacy; section: {st['snapshot_section']})")
    print(f"│  Verdict: {cr34['verdict']}")
    if cr34["violations"]:
        issue_count += len(cr34["violations"])
        print(f"│  [FAIL] {len(cr34['violations'])} violation(s):")
        for v in cr34["violations"][:8]:
            print(f"│    - [{v['rule']}] {v.get('task_id','')}: {v['reason']}")
    elif cr34["warnings"]:
        print(f"│  [WARN] {len(cr34['warnings'])} warning(s):")
        for w in cr34["warnings"]:
            print(f"│    - [{w['rule']}] {w['reason']}")
    else:
        print(f"│  [{cr34['verdict']}] {cr34['reason']}")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_37_release_gates(release_unit_issues, HOST_PROJECT_ROOT):
    issue_count = 0
    # Content-dimension watchdog for the AUDIT-145 G9 blind spot: a release
    # tag must not exist while prerelease gates (rows BEFORE the release
    # gate, row-order derivation — standard 11 / lightweight 7) are pending.
    # G-s1 FAIL (tag predates a passed gate) / G-s2 FAIL (tag exists with a
    # pending gate, conservative) / G-s3 WARN (no git tag but release gate
    # passed with pending prereleases — fail-safe). passed-on-entry is not
    # pending (DEC-153 ④). WARN and FAIL both count into issue_count
    # (Check-36 convention). Standalone runs use candidate mode — the
    # already-published release checks carry released mode via
    # check_release_readiness (BR-4 / DEC-153 ②).
    print("\n┌─ Check 37: Release work-unit evidence ─────┐")
    violations = release_unit_issues(HOST_PROJECT_ROOT)
    for issue in violations:
        print(f"│  [FAIL] {issue}")
    if not violations:
        print("│  [PASS] No unsupported release certification")
    issue_count += len(violations)
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_38_ci_evidence(check_ci_evidence):
    issue_count = 0
    # Content-dimension watchdog for the AUDIT-145 "claimed CI never
    # really ran" blind spot (tv: workflow exists, no remote — DEV-003
    # "本仓无 remote——首次运行/成功率统计待远端仓库后补验"; router: no CI
    # carrier at all). C1 FAIL (claimed BUILT incl. built-not-run
    # admissions, no carrier — multi-path probe: **/.github/workflows/*
    # deep walk over the project's own git tree + .gitlab-ci.yml +
    # Jenkinsfile; nested git repos excluded) / C2 WARN (carrier exists,
    # git remote empty or git unavailable — "CI 未真跑", fail-safe never
    # FAIL) / C3 WARN (claimed RUN locally unprovable — no remote/git OR
    # no carrier at all; DEC-156: run claims never enter the C1 FAIL
    # branch) / C4 PASS (no declaration, no carrier). Scope per DEC-154
    # ②: existence + remote only, no deep workflow/job inspection. WARN
    # and FAIL both count into issue_count (Check-36/37 convention).
    # Facts root = HOST_PROJECT_ROOT (FIX-270 mixed-root fix — never the
    # plugin ROOT).
    print("\n┌─ Check 38: CI Evidence (FIX-267) ───────────────────┐")
    cr38 = check_ci_evidence()
    st38 = cr38["stats"]
    print(f"│  Plan lines scanned: {st38['plan_lines_scanned']} "
          f"(built: {st38['built_claims']}, not-run: "
          f"{st38['built_notrun_claims']}, run: {st38['run_claims']})")
    carrier_desc = "yes" if st38["carrier_exists"] else "no"
    print(f"│  Carrier: {carrier_desc} (workflows: "
          f"{st38['workflow_files']}, gitlab-ci: {st38['gitlab_ci']}, "
          f"jenkinsfile: {st38['jenkinsfile']}; remote: "
          f"{st38['remote_state'] or '—'})")
    print(f"│  Verdict: {cr38['verdict']}")
    if cr38["violations"]:
        print(f"│  [FAIL] {len(cr38['violations'])} violation(s):")
        for v in cr38["violations"][:8]:
            print(f"│    - [{v['rule']}] {v['reason']}")
    if cr38["warnings"]:
        print(f"│  [WARN] {len(cr38['warnings'])} warning(s):")
        for w in cr38["warnings"][:8]:
            print(f"│    - [{w['rule']}] {w['reason']}")
    if not cr38["violations"] and not cr38["warnings"]:
        print(f"│  [{cr38['verdict']}] {cr38['reason']}")
    issue_count += len(cr38["violations"]) + len(cr38["warnings"])
    print("└──────────────────────────────────────────────────────┘")
    return issue_count
