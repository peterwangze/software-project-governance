"""Full governance report sections for the installed product and its integration checks."""


def section_7_commit_traceability(
    product_gate_active, check_commit_task_references, _print_product_gate_skipped,
):
    issue_count = 0
    if product_gate_active():
        print("\n┌─ Check 7: Commit-Task Traceability ──────────────────┐")
        ct_result = check_commit_task_references(limit=20)
        if "error" in ct_result:
            print(f"│  [INFO] Skipped: {ct_result['error']}")
        else:
            total = ct_result["total_checked"]
            without = ct_result["without_task_id"]
            print(f"│  Recent commits checked: {total}")
            if without > 0:
                issue_count += without
                print(f"│  [WARN] {without} commit(s) without task ID reference:")
                for c in ct_result["issues"]:
                    msg_short = c["message"][:70] + ("..." if len(c["message"]) > 70 else "")
                    print(f"│    - {c['sha']}: {msg_short}")
            else:
                print(f"│  [PASS] All {total} recent commits have task ID references.")
            # Show stats
            with_id = total - without
            print(f"│  With task ID: {with_id}/{total}")
    else:
        _print_product_gate_skipped("Check 7")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_11_manifest(product_gate_active, check_manifest_consistency, _print_product_gate_skipped):
    issue_count = 0
    if product_gate_active():
        print("\n┌─ Check 11: Manifest Consistency ─────────────────────┐")
        mc_result = check_manifest_consistency()
        if mc_result.get("error"):
            print(f"│  [INFO] Skipped: {mc_result.get('error')}")
        else:
            mc_missing = mc_result["missing"]
            mc_untracked = mc_result["untracked"]
            print(f"│  Canonical files in manifest: {mc_result['canonical_count']}")
            print(f"│  Actual files on disk:       {mc_result['actual_count']}")
            if mc_missing:
                issue_count += len(mc_missing)
                print(f"│  [WARN] {len(mc_missing)} file(s) in manifest but missing on disk:")
                for m in mc_missing:
                    print(f"│    - {m}")
            else:
                print(f"│  [PASS] No missing files (all manifest entries exist on disk).")
            if mc_untracked:
                issue_count += len(mc_untracked)
                print(f"│  [WARN] {len(mc_untracked)} file(s) on disk but not in manifest:")
                for u in mc_untracked:
                    print(f"│    - {u}")
            else:
                print(f"│  [PASS] No untracked files (all files covered by manifest).")
    else:
        _print_product_gate_skipped("Check 11")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_15_commit_scope(product_gate_active, check_commit_scope, _print_product_gate_skipped):
    issue_count = 0
    if product_gate_active():
        print("\n┌─ Check 15: Commit Scope Verification ────────────────┐")
        cs_result = check_commit_scope(limit=20)
        if cs_result.get("error"):
            print(f"│  [INFO] Skipped: {cs_result['error']}")
        else:
            cs_issues = cs_result["issues"]
            print(f"│  Recent commits checked: {cs_result['total_checked']}")
            if cs_issues:
                issue_count += len(cs_issues)
                print(f"│  [WARN] {len(cs_issues)} scope discipline issue(s):")
                for v in cs_issues[:10]:
                    detail = v.get("detail", "")
                    sha = v.get("sha", "?")
                    itype = v.get("type", "?")
                    print(f"│    - [{itype}] {sha}: {detail}")
                if len(cs_issues) > 10:
                    print(f"│    ... and {len(cs_issues) - 10} more")
            else:
                print(f"│  [PASS] All recent commits have clean scope discipline.")
    else:
        _print_product_gate_skipped("Check 15")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_24_version(product_gate_active, check_version_consistency, _print_product_gate_skipped):
    issue_count = 0
    if product_gate_active():
        print("\n┌─ Check 24: Version Consistency (FIX-052) ───────────┐")
        vc_issues = check_version_consistency()
        vc_fail = [i for i in vc_issues if not i.startswith("[WARN]")]
        vc_warn = [i for i in vc_issues if i.startswith("[WARN]")]
        if vc_fail:
            issue_count += len(vc_fail)
            print(f"│  [FAIL] {len(vc_fail)} version mismatch(es):")
            for v in vc_fail:
                print(f"│    - {v}")
        else:
            print(f"│  [PASS] All version declarations match SKILL.md.")
        if vc_warn:
            print(f"│  [INFO] {len(vc_warn)} non-blocking drift(s):")
            for w in vc_warn:
                print(f"│    - {w}")
    else:
        _print_product_gate_skipped("Check 24")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_28b_projection_sync(
    product_gate_active, check_projection_sync, _print_product_gate_skipped,
):
    issue_count = 0
    if product_gate_active():
        print("\n┌─ Check 28b: Projection Sync Guard (FIX-086) ─────────┐")
        ps_result = check_projection_sync()
        print(f"│  Source version: {ps_result['source_version'] or 'unknown'}")
        print(f"│  Mirrored files checked: {ps_result['mirrors_checked']}")
        if ps_result.get("mirrors_skipped_untracked"):
            print(f"│  Untracked local projection copies skipped: {ps_result['mirrors_skipped_untracked']}")
        if ps_result["issues"]:
            issue_count += len(ps_result["issues"])
            print(f"│  [FAIL] {len(ps_result['issues'])} projection sync issue(s):")
            for issue in ps_result["issues"][:10]:
                print(f"│    - {issue}")
            if len(ps_result["issues"]) > 10:
                print(f"│    ... and {len(ps_result['issues']) - 10} more")
        else:
            print("│  [PASS] Source, target fixture, native entries, and plugin versions are synchronized.")
    else:
        _print_product_gate_skipped("Check 28b")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_28d_runtime_matrix(
    product_gate_active, check_runtime_readiness_matrix, _print_product_gate_skipped,
):
    issue_count = 0
    if product_gate_active():
        print("\n┌─ Check 28d: Runtime Readiness Matrix (FIX-106) ──────┐")
        rrm_issues = check_runtime_readiness_matrix()
        if rrm_issues:
            issue_count += len(rrm_issues)
            print(f"│  [FAIL] {len(rrm_issues)} runtime/readiness matrix issue(s):")
            for issue in rrm_issues[:10]:
                print(f"│    - {issue}")
            if len(rrm_issues) > 10:
                print(f"│    ... and {len(rrm_issues) - 10} more")
        else:
            print("│  [PASS] Public runtime/readiness matrix matches adapter facts and no-overclaim boundaries.")
    else:
        _print_product_gate_skipped("Check 28d")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_28e_first_session(
    product_gate_active, check_first_session_measurement, _print_product_gate_skipped,
):
    issue_count = 0
    if product_gate_active():
        print("\n┌─ Check 28e: First-Session Measurement (FIX-107) ─────┐")
        fsm_issues = check_first_session_measurement()
        if fsm_issues:
            issue_count += len(fsm_issues)
            print(f"│  [FAIL] {len(fsm_issues)} first-session measurement issue(s):")
            for issue in fsm_issues[:10]:
                print(f"│    - {issue}")
            if len(fsm_issues) > 10:
                print(f"│    ... and {len(fsm_issues) - 10} more")
        else:
            print("│  [PASS] Local demo proof is separated from external first-session measurement.")
    else:
        _print_product_gate_skipped("Check 28e")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_28f_governance_packs(
    product_gate_active, check_governance_packs, _print_product_gate_skipped,
):
    issue_count = 0
    if product_gate_active():
        print("\n┌─ Check 28f: Governance Pack Registry (FIX-108) ──────┐")
        gp_issues = check_governance_packs()
        if gp_issues:
            issue_count += len(gp_issues)
            print(f"│  [FAIL] {len(gp_issues)} governance pack registry issue(s):")
            for issue in gp_issues[:10]:
                print(f"│    - {issue}")
            if len(gp_issues) > 10:
                print(f"│    ... and {len(gp_issues) - 10} more")
        else:
            print("│  [PASS] Governance pack registry is complete, referenced, and no-overclaim safe.")
    else:
        _print_product_gate_skipped("Check 28f")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_28h_readme_guidance(
    product_gate_active, check_readme_pack_guidance, _print_product_gate_skipped,
):
    issue_count = 0
    if product_gate_active():
        print("\n┌─ Check 28h: README Pack Guidance (FIX-109) ──────────┐")
        readme_pack_issues = check_readme_pack_guidance()
        if readme_pack_issues:
            issue_count += len(readme_pack_issues)
            print(f"│  [FAIL] {len(readme_pack_issues)} README pack guidance issue(s):")
            for issue in readme_pack_issues[:10]:
                print(f"│    - {issue}")
            if len(readme_pack_issues) > 10:
                print(f"│    ... and {len(readme_pack_issues) - 10} more")
        else:
            print("│  [PASS] README maps first-run profiles to packs without replacing profiles or overclaiming.")
    else:
        _print_product_gate_skipped("Check 28h")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_28i_pack_status(
    product_gate_active, check_governance_pack_status, _print_product_gate_skipped,
):
    issue_count = 0
    if product_gate_active():
        print("\n┌─ Check 28i: Governance Pack Status Boundary (FIX-111) ┐")
        pack_status_issues = check_governance_pack_status()
        if pack_status_issues:
            issue_count += len(pack_status_issues)
            print(f"│  [FAIL] {len(pack_status_issues)} governance pack status/release issue(s):")
            for issue in pack_status_issues[:10]:
                print(f"│    - {issue}")
            if len(pack_status_issues) > 10:
                print(f"│    ... and {len(pack_status_issues) - 10} more")
        else:
            print("│  [PASS] Status and release surfaces expose pack boundaries without overclaiming.")
    else:
        _print_product_gate_skipped("Check 28i")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_28j_capability_context(check_capability_context):
    issue_count = 0
    print("\n┌─ Check 28j: Capability Context Trace (FIX-115) ──────┐")
    capability_context_issues = check_capability_context()
    if capability_context_issues:
        issue_count += len(capability_context_issues)
        print(f"│  [FAIL] {len(capability_context_issues)} capability context issue(s):")
        for issue in capability_context_issues[:10]:
            print(f"│    - {issue}")
        if len(capability_context_issues) > 10:
            print(f"│    ... and {len(capability_context_issues) - 10} more")
    else:
        print("│  [PASS] Capability selection trace is fact-backed, degraded-safe, and no-overclaim safe.")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_28k_capability_registry(
    product_gate_active, check_capability_registry, _print_product_gate_skipped,
):
    issue_count = 0
    if product_gate_active():
        print("\n┌─ Check 28k: Capability Registry (FIX-116) ───────────┐")
        capability_registry_issues = check_capability_registry()
        if capability_registry_issues:
            issue_count += len(capability_registry_issues)
            print(f"│  [FAIL] {len(capability_registry_issues)} capability registry issue(s):")
            for issue in capability_registry_issues[:10]:
                print(f"│    - {issue}")
            if len(capability_registry_issues) > 10:
                print(f"│    ... and {len(capability_registry_issues) - 10} more")
        else:
            print("│  [PASS] Capability registry separates catalog facts from runtime PASS and governance packs.")
    else:
        _print_product_gate_skipped("Check 28k")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_28l_host_capabilities(check_host_capability_context):
    issue_count = 0
    print("\n┌─ Check 28l: Restricted Host Capability Context (FIX-117) ┐")
    host_capability_issues = check_host_capability_context()
    if host_capability_issues:
        issue_count += len(host_capability_issues)
        print(f"│  [FAIL] {len(host_capability_issues)} restricted host capability issue(s):")
        for issue in host_capability_issues[:10]:
            print(f"│    - {issue}")
        if len(host_capability_issues) > 10:
            print(f"│    ... and {len(host_capability_issues) - 10} more")
    else:
        print("│  [PASS] Restricted-environment capability context degrades honestly without runtime PASS overclaim.")
    print("└──────────────────────────────────────────────────────────┘")
    return issue_count


def section_28n_agent_loading(
    product_gate_active, check_mainstream_agent_loading, _print_product_gate_skipped,
):
    issue_count = 0
    if product_gate_active():
        print("\n┌─ Check 28n: Mainstream Agent Loading (FIX-122) ──────┐")
        mainstream_loading_issues = check_mainstream_agent_loading()
        if mainstream_loading_issues:
            issue_count += len(mainstream_loading_issues)
            print(f"│  [FAIL] {len(mainstream_loading_issues)} mainstream agent loading issue(s):")
            for issue in mainstream_loading_issues[:10]:
                print(f"│    - {issue}")
            if len(mainstream_loading_issues) > 10:
                print(f"│    ... and {len(mainstream_loading_issues) - 10} more")
        else:
            print("│  [PASS] README, Tier 1 adapters, and 0.47.0 requirements keep loading guidance synchronized.")
    else:
        _print_product_gate_skipped("Check 28n")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_28o_architecture_health(
    product_gate_active, check_architecture_health, _print_product_gate_skipped,
):
    issue_count = 0
    # G7: advisory-only in 0.58.0. Findings are reported but MUST NOT increment
    # issue_count (which would flip the gate). Only fatal-on-error ERRORs count.
    if product_gate_active():
        print("\n┌─ Check 28o: Architecture Health (ArchGuard/REQ-101) ┐")
        arch = check_architecture_health()
        if arch.get("error"):
            print(f"│  [SKIP] {arch['error']}")
        else:
            s = arch["summary"]
            fatal = bool(arch.get("fatal_on_error"))
            print(f"│  Module/function/constant: {s['errors']} ERROR, {s['warnings']} WARN")
            for f in arch["findings"][:8]:
                loc = f.get("path", "")
                extra = f.get("name") or f.get("count") or f.get("lines", "")
                print(f"│    [{f['severity']}] {f['check']}: {loc} {extra}".rstrip())
            if len(arch["findings"]) > 8:
                print(f"│    ... and {len(arch['findings']) - 8} more")
            if s["errors"] and not fatal:
                print("│  [ADVISORY] fatal_on_error=false — does not block release")
            elif s["errors"] and fatal:
                issue_count += s["errors"]
                print("│  [FATAL] fatal_on_error=true — counting toward gate")
    else:
        _print_product_gate_skipped("Check 28o")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_28p_duplicate_code(product_gate_active, check_duplicate_code, _print_product_gate_skipped):
    if product_gate_active():
        print("\n┌─ Check 28p: Duplicate Code (ArchGuard/REQ-101) ─────┐")
        dup = check_duplicate_code()
        if dup.get("error"):
            print(f"│  [SKIP] {dup['error']}")
        else:
            s = dup["summary"]
            print(f"│  source/projection pairs checked: {dup.get('pairs_checked', 0)}")
            for x in dup.get("exemptions", []):
                reason = x.get("reason", "")
                print(f"│    [EXEMPT] {x.get('path', '')}"
                      + (f" — {reason}" if reason else ""))
            for f in dup["findings"][:8]:
                print(f"│    [{f['severity']}] {f['check']}: {f.get('path','')} dup={f.get('duplicate_pct','')}%")
            if s["errors"] or s["warnings"]:
                print(f"│  {s['errors']} ERROR, {s['warnings']} WARN (advisory)")
    else:
        _print_product_gate_skipped("Check 28p")
    print("└──────────────────────────────────────────────────────┘")
    return 0


def section_28q_technical_debt(product_gate_active, check_technical_debt, _print_product_gate_skipped):
    # Includes hooks content drift (reuses _external_validation_* helpers, G9).
    if product_gate_active():
        print("\n┌─ Check 28q: Technical Debt (ArchGuard/REQ-101) ─────┐")
        debt = check_technical_debt()
        if debt.get("error"):
            print(f"│  [SKIP] {debt['error']}")
        else:
            s = debt["summary"]
            print(f"│  residue/docs/hooks-drift/ledger: {s['errors']} ERROR, {s['warnings']} WARN")
            for f in debt["findings"][:8]:
                loc = f.get("path") or f.get("hook") or f.get("ledger_id") or ""
                print(f"│    [{f['severity']}] {f['check']}: {loc}".rstrip())
            if len(debt["findings"]) > 8:
                print(f"│    ... and {len(debt['findings']) - 8} more")
    else:
        _print_product_gate_skipped("Check 28q")
    print("└──────────────────────────────────────────────────────┘")
    return 0


def section_28r_complexity(product_gate_active, check_complexity, _print_product_gate_skipped):
    if product_gate_active():
        print("\n┌─ Check 28r: Complexity (ArchGuard/REQ-101) ─────────┐")
        cx = check_complexity()
        if cx.get("error"):
            print(f"│  [SKIP] {cx['error']}")
        elif not cx.get("enabled", False):
            print(f"│  [INFO] disabled — {cx.get('note','line-based proxy; see check-architecture-health')}")
        else:
            s = cx["summary"]
            print(f"│  complexity proxy: {s['errors']} ERROR, {s['warnings']} WARN")
            for f in cx["findings"][:8]:
                print(f"│    [{f['severity']}] {f.get('name','')} ({f.get('path','')})".rstrip())
    else:
        _print_product_gate_skipped("Check 28r")
    print("└──────────────────────────────────────────────────────┘")
    return 0


def section_28t_readme_evidence(
    product_gate_active, check_readme_claim_evidence_levels, _print_product_gate_skipped,
):
    # Advisory: adapter user-facing claims must carry evidence-level
    # annotations (live-session / isolation / static — the machine-checkable
    # claim→evidence mapping). fatal_on_error=false — does NOT increment
    # issue_count (28s precedent); escalation to FAIL is the registered
    # tightening path (RISK-049 closure review). Fact source = the plugin
    # package's own README (ROOT) → PLUGIN_PRODUCT (FIX-270 / F-2).
    if product_gate_active():
        print("\n┌─ Check 28t: README Claim→Evidence Levels (FEAT-014) ─┐")
        rel28t = check_readme_claim_evidence_levels()
        st28t = rel28t["stats"]
        print(f"│  claims checked: {st28t['claims_checked']} "
              f"(annotated {st28t['claims_annotated']}); markers: "
              f"{st28t['markers_found']} (live-session "
              f"{st28t['levels']['live-session']}, isolation "
              f"{st28t['levels']['isolation']}, static "
              f"{st28t['levels']['static']})")
        print(f"│  Verdict: {rel28t['verdict']}")
        if rel28t["warnings"]:
            shown28t = rel28t["warnings"][:8]
            print(f"│  [WARN] {len(rel28t['warnings'])} claim-evidence WARN(s)"
                  f" (showing first {len(shown28t)}):")
            for w in shown28t:
                print(f"│    - [{w['rule']}] {w.get('claim_id') or '-'}: "
                      f"{w['reason']}")
            if len(rel28t["warnings"]) > 8:
                print(f"│    ... and {len(rel28t['warnings']) - 8} more")
            print("│  (advisory — fatal_on_error=false; does not block release)")
        else:
            print(f"│  [{rel28t['verdict']}] {rel28t['reason']}")
    else:
        _print_product_gate_skipped("Check 28t")
    print("└──────────────────────────────────────────────────────┘")
    return 0


def section_33_injection_contract(
    product_gate_active, check_injection_contract, emit_injection_budget_section,
    _print_product_gate_skipped,
):
    issue_count = 0
    # Existence-only anchor check over the deterministic injection surfaces
    # (DSH persona template / entry SKILL / DSH thin pointer). Never asserts
    # full-text equality; never performs behavior detection (DEC-143 boundary
    # stays with REQ-107/108/113).
    #
    # FEAT-039 / AUDIT-154 A-8 rides inside this segment (no new segment id —
    # the registry's 71-segment vocabulary and the contract-matrix face stay
    # untouched): the SAME surfaces also get a size budget. Anchors answer
    # "is the contract still injected?", the budget answers "at what cost?" —
    # AUDIT-154 §5.3: a quality gate with no budget gate lets slimming
    # rebound. The budget's own hard/advisory posture lives in
    # BUDGET_TIER_POLICY; today the resident tier is advisory (slice-A
    # relaxed window), so over-budget surfaces are reported with per-surface
    # overshoot instead of blocking this segment.
    if product_gate_active():
        print("\n┌─ Check 33: Injection Contract (FIX-253/REQ-112) ────────────────────┐")
        ic33 = check_injection_contract()
        print(f"│  Files checked: {ic33['files_checked']}; anchors: {ic33['anchors_checked']}"
              + (f"; {ic33['staged_summary']}" if ic33["staged_summary"] else ""))
        if ic33["issues"]:
            issue_count += len(ic33["issues"])
            print(f"│  [FAIL] {len(ic33['issues'])} injection-contract issue(s):")
            for issue in ic33["issues"]:
                print(f"│    - {issue}")
        else:
            print("│  [PASS] persona/SKILL/AGENTS injection surfaces carry the contract anchors.")
        ib33 = emit_injection_budget_section()
        if ib33["issues"]:
            issue_count += len(ib33["issues"])
            print(f"│  [FAIL] {len(ib33['issues'])} injection-budget issue(s):\n"
                  + "\n".join(f"│    - {issue}" for issue in ib33["issues"]))
        elif ib33["verdict"] == "ADVISORY":
            print(f"│  [ADVISORY] resident set {ib33['tokens']} tok, budget "
                  f"{ib33['budget_tokens']} tok; gated over-budget tiers: "
                  f"{', '.join(ib33['gated_over_budget_tiers']) or 'none'}")
        else:
            print(f"│  [PASS] resident injection set {ib33['tokens']} tok "
                  f"<= budget {ib33['budget_tokens']} tok.")
    else:
        _print_product_gate_skipped("Check 33")
    print("└──────────────────────────────────────────────────────────────────────┘")
    return issue_count


def section_28u_dsh_smoke(product_gate_active, check_dsh_preset_smoke, _print_product_gate_skipped):
    issue_count = 0
    # RISK-049 closure standard (2): "安装后 preset 会话可用" as a repeatable
    # gate instead of reasoning. Blocking: a preset session that cannot load
    # its skill catalog or /governance gesture is a user-facing defect, not an
    # advisory. Runs in a temp DSH_HOME created by the check (M7.7 (a)
    # isolation); fact source = the plugin package's own launch.py +
    # agent-presets/ → PLUGIN_PRODUCT (FIX-270 / F-2).
    if product_gate_active():
        from checks.dsh_smoke import emit_health_result

        issue_count += emit_health_result(check_dsh_preset_smoke())
    else:
        _print_product_gate_skipped("Check 28u")
    print("└──────────────────────────────────────────────────────┘")
    return issue_count


def section_28v_dsh_schema(product_gate_active, _print_product_gate_skipped):
    issue_count = 0
    # A dsh upgrade silently invalidated one shipped-preset row (key `text` vs
    # dsh-persona's required `prefix`) and the WHOLE preset mount was rejected,
    # so users could not start a session. Neither the retired Check 40
    # (FIX-310 manifest guard — number retired, never reused; ADR-021
    # §2.2.3 RT-4) nor Check 28u compares a composition row against the
    # plugin set a mount actually uses; this gate does, with the loader's
    # own dialect/evaluate and the resolved cordis `resolveConfig` (no
    # schema is copied). Fact source = the plugin package's own
    # compositions → PLUGIN_PRODUCT (FIX-270); no node / no resolvable
    # plugin set → NOT_RUN, never a silent PASS. Body rendering and
    # the full rationale live in dsh_compat (R4: orchestration output belongs
    # to the render layer).
    if product_gate_active():
        from dsh_compat import emit_check_section

        issue_count += emit_check_section()
    else:
        _print_product_gate_skipped("Check 28v")
    return issue_count


def section_28w_dsh_boundary(product_gate_active, _print_product_gate_skipped):
    issue_count = 0
    # The contract `adapters/dsh/host-contract.json` is the single machine-
    # readable statement of what this plugin consumes from the dsh host. V2
    # moved the consumers onto it; this gate is what makes the move judgeable
    # (K-1…K-13, design §2.8): contract shape, template ↔ row-set equivalence
    # in both directions, token equality, the hooks' path expression, the patch
    # invariants, version-evidence consistency + TTL, coverage-claim backing,
    # disposition completeness, the structural declarations, the allowlist
    # ratchet, the single-verdict anchor and the rehearsal baseline. Its fact
    # source is the plugin package's own dsh surface → PLUGIN_PRODUCT (FIX-270).
    # Body rendering lives in `checks/dsh_boundary` (C-15/R4: the monolith's
    # print budget does not grow; this wrapper is one statement) and the import
    # is function-local for the same reason 28v's is — the engine's frozen
    # startup import budget (R6, 196 modules) must not move.
    if product_gate_active():
        from checks.dsh_boundary import emit_check_section

        issue_count += emit_check_section()
    else:
        _print_product_gate_skipped("Check 28w")
    return issue_count
