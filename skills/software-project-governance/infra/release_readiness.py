"""Evaluate release-gate evidence and record its ordered issues, warnings and disclosures."""

import re


def version_consistency(details, issues, version_issues):
    version_failures = [issue for issue in version_issues if not issue.startswith("[WARN]")]
    details["version_consistency"] = {
        "pass": not version_failures,
        "issues": version_failures,
        "warnings": [issue for issue in version_issues if issue.startswith("[WARN]")],
    }
    issues.extend(f"version consistency: {issue}" for issue in version_failures)


def pack_status(details, issues, pack_status_issues):
    details["governance_pack_status"] = {
        "pass": not pack_status_issues,
        "issues": pack_status_issues,
        "boundary": (
            "packs are capability modules; profiles are intensity presets; "
            "pack enabled or membership is not task evidence, independent review, "
            "quality gate, release gate, official approval, marketplace approval, "
            "universal/full runtime support, or 1.0.0 production-ready proof"
        ),
    }
    issues.extend(f"governance pack status: {issue}" for issue in pack_status_issues)


def admission(details, issues, version, provenance_rows):
    from checks import provenance_domain as _provenance_gate_mod
    admission = _provenance_gate_mod.check_release_admission(
        provenance_rows, {"version": str(version)})
    details["provenance_release_gate"] = {
        "pass": admission["status"] != "FAIL",
        "status": admission["status"],
        "issues": admission["issues"],
        "warnings": admission["warnings"],
        "machine_signal_payload": admission["machine_signal_payload"],
        "open_user_named": admission["open_user_named"],
        "deferred_user_named": admission["deferred_user_named"],
        "undeclared_payload": admission["undeclared_payload"],
    }
    issues.extend(f"provenance release gate: {issue}"
                  for issue in admission["issues"])
    for warning in admission["warnings"]:
        details.setdefault("release_warnings", []).append(
            f"provenance release gate: {warning}")


def security_descriptors(details, issues, host_root, plugin_root):
    from checks.sd_integrity import release_face_paths, scan_sd_readability
    _sd_face = release_face_paths(host_root, plugin_root)
    _sd_face_error = _sd_face.get("error")
    if _sd_face_error:
        issues.append(f"sd integrity: {_sd_face_error}")
    sd_scan = scan_sd_readability(_sd_face["paths"])
    if _sd_face_error:
        sd_scan["pass"] = False
    sd_issues = [f"{path} unreadable — remediate: {cmd}"
                 for path, cmd in zip(sd_scan["unreadable"], sd_scan["remediation"])]
    details["sd_integrity"] = {**sd_scan, "face_error": _sd_face_error, "issues": sd_issues}
    issues.extend(f"sd integrity: {issue}" for issue in sd_issues)


def agent_adapters(details, issues, adapter_issues, run_runtime_adapters):
    details["agent_adapters"] = {
        "pass": not adapter_issues,
        "issues": adapter_issues,
        "runtime": run_runtime_adapters,
    }
    issues.extend(f"agent adapters: {issue}" for issue in adapter_issues)


def projection_sync(details, issues, projection_result):
    details["projection_sync"] = {
        "pass": projection_result["pass"],
        "issues": projection_result["issues"],
        "mirrors_checked": projection_result["mirrors_checked"],
        "mirrors_discovered": projection_result["mirrors_discovered"],
        "mirrors_skipped_untracked": projection_result["mirrors_skipped_untracked"],
        "source_version": projection_result["source_version"],
    }
    issues.extend(f"projection sync: {issue}" for issue in projection_result["issues"])


def cross_references(details, issues, cross_ref_result):
    cross_ref_issues = (
        [f"dangling reference: {item['source']}:{item['line']} -> {item['target']}" for item in cross_ref_result["dangling"]]
        + [f"deprecated reference: {item['source']}:{item['line']} -> {item['target']}" for item in cross_ref_result["deprecated"]]
        + [f"circular reference: {' -> '.join(cycle)}" for cycle in cross_ref_result["cycles"]]
        # FIX-432 (F-4/F-A2) / FIX-436 F-8 wording: quote-sync issues ride
        # the same gate; the current check_cross_references() always emits
        # the key — .get only tolerates pre-FIX-432/partial dict shapes
        # (e.g. fixtures or older cached results) that lack it.
        + [f"quote sync: {issue}" for issue in cross_ref_result.get("quote_sync", [])]
    )
    details["cross_references"] = {
        "pass": not cross_ref_issues,
        "issues": cross_ref_issues,
    }
    issues.extend(cross_ref_issues)


def archive_integrity(details, issues, archive_result):
    archive_issues = archive_result.get("issues", [])
    details["archive_integrity"] = {
        "pass": not archive_issues,
        "issues": archive_issues,
        "pending_archive_tasks": archive_result.get("pending_archive_tasks", 0),
    }
    issues.extend(f"archive integrity: {issue}" for issue in archive_issues)


def release_docs(details, issues, version, release_docs_issues):
    details["release_docs"] = {
        "pass": not release_docs_issues,
        "issues": release_docs_issues,
        "version": version,
    }
    issues.extend(f"release docs: {issue}" for issue in release_docs_issues)


def release_delivery(details, issues, current_host_root, release_unit, version, lineage_mode, require_delivery_evidence):
    # Release certification belongs to the candidate/version being shipped.
    if lineage_mode == "candidate":
        from loop_workflow import release_issues
        scoped_issues = release_issues(current_host_root(), release_unit, version)
        details["release_loop"] = {"pass": not scoped_issues, "unit": release_unit, "issues": scoped_issues}
        issues.extend(scoped_issues)

    # Delivery acceptance also applies when broader execution gates are disabled.
    from delivery_acceptance import evaluate_delivery_acceptance

    delivery_acceptance = evaluate_delivery_acceptance(
        current_host_root(),
        release_version=version,
        required=require_delivery_evidence,
        released_history=lineage_mode == "released")
    details["delivery_acceptance"] = delivery_acceptance
    issues.extend(f"delivery acceptance: {issue}" for issue in delivery_acceptance["issues"])


def release_blockers(details, issues, version, blocker_issues):
    issues.extend(f"1.0.0 blocker: {issue}" for issue in blocker_issues)
    details["one_dot_zero_blockers"] = {
        "pass": not blocker_issues, "issues": blocker_issues,
        "required": version == "1.0.0", "version": version,
    }


def execution_gates(details, issues, required, results):
    failures = [result["issue"] for result in results if result.get("issue")]
    issues.extend(f"execution gate: {failure}" for failure in failures)
    details["execution_gates"] = {
        "pass": not failures, "issues": failures, "required": required, "results": results,
    }


def project_ci(details, issues, ci):
    ci_issues = [item["reason"] for item in ci["violations"]]
    details["project_ci_evidence"] = {
        **ci, "pass": not ci_issues, "issues": ci_issues,
        "skipped": ci["verdict"] == "no-verdict", "skip_reason": ci["reason"],
    }
    issues.extend(f"project CI: {issue}" for issue in ci_issues)


def dsh_upgrade(details, issues, plugin_release, run_execution_gates, lineage_mode, run_regression):
    dsh_regression_skipped_reason = None
    dsh_regression_results = []
    dsh_regression_issues = []
    dsh_regression_isolation = None
    if not plugin_release:
        dsh_regression_skipped_reason = "DSH preset regression applies to the governance plugin release."
    elif not run_execution_gates:
        dsh_regression_skipped_reason = (
            "execution gates skipped (--skip-execution-gates); the dsh "
            "upgrade regression command set was not run — WARN disclosure, "
            "not a release verdict")
    elif lineage_mode == "released":
        dsh_regression_skipped_reason = (
            "released-history check (BR-4 / DEC-153 ②); the dsh upgrade "
            "regression targets the candidate working tree and is not run "
            "for already-published version queries — WARN disclosure")
    else:
        dsh_regression = run_regression()
        dsh_regression_results = dsh_regression["results"]
        dsh_regression_issues = dsh_regression["issues"]
        dsh_regression_isolation = dsh_regression.get("isolation")
        issues.extend(f"dsh upgrade regression: {issue}"
                      for issue in dsh_regression_issues)
    details["dsh_upgrade_regression"] = {
        "pass": not dsh_regression_issues,
        "skipped": dsh_regression_skipped_reason is not None,
        "skip_reason": dsh_regression_skipped_reason,
        "required": dsh_regression_skipped_reason is None,
        "results": dsh_regression_results,
        "issues": dsh_regression_issues,
        "isolation": dsh_regression_isolation,
        "boundary": (
            "isolated temp-DSH_HOME preset install/load smoke; proves the "
            "packaged preset session boots in a redirected home with zero "
            "real-home writes — not a live marketplace upgrade"),
    }


def changelog(details, issues, version, require_changelog, changelog_path, display_path):
    changelog_issues = []
    if version:
        if not re.fullmatch(r"\d+\.\d+\.\d+", version):
            changelog_issues.append(f"release version `{version}` is not semver X.Y.Z")
        if require_changelog:
            if not changelog_path.exists():
                changelog_issues.append(f"{display_path(changelog_path)}: missing changelog")
            else:
                changelog_content = changelog_path.read_text(encoding="utf-8")
                if f"## [{version}]" not in changelog_content:
                    changelog_issues.append(f"{display_path(changelog_path)}: missing changelog entry ## [{version}]")
    elif require_changelog:
        changelog_issues.append("--require-changelog requires --version")

    details["changelog"] = {
        "pass": not changelog_issues,
        "issues": changelog_issues,
        "required": require_changelog,
        "version": version,
    }
    issues.extend(changelog_issues)
