"""Render the release, projection and architectural validation command results."""

from pathlib import Path
import json
import sys


def cmd_check_release(args, *, check_release_readiness, write_cli_json):
    """Run release readiness checks used by the stage-release workflow."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    skip_execution_gates = getattr(args, "skip_execution_gates", False)
    lineage_mode = getattr(args, "lineage_mode", None) or "candidate"
    result = check_release_readiness(
        version=getattr(args, "version", None),
        require_changelog=getattr(args, "require_changelog", False),
        run_runtime_adapters=getattr(args, "runtime_adapters", False),
        run_execution_gates=not skip_execution_gates,
        lineage_mode=lineage_mode,
        release_commit=getattr(args, "release_commit", None),
        lineage_remote=getattr(args, "lineage_remote", "origin"),
        release_unit=getattr(args, "unit", None),
        require_delivery_evidence=getattr(args, "require_delivery_evidence", False),
    )
    if getattr(args, "json", False):
        write_cli_json(result, indent=2)
        if not result["pass"]:
            sys.exit(1)
        return
    if "release_replay" in result["details"]:
        sys.exit(result["issues"][0])


    print()
    print("=== Release Readiness Check ===")
    if getattr(args, "version", None):
        print(f"  Version: {args.version}")
    print(f"  Runtime adapters: {'enabled' if getattr(args, 'runtime_adapters', False) else 'static'}")
    print(f"  Execution gates: {'skipped' if skip_execution_gates else 'enabled'}")
    print(f"  Lineage mode: {lineage_mode}")
    for label, detail in result["details"].items():
        if detail.get("skipped"):
            # FEAT-016 / RISK-049 ③: an intentionally not-run gate must be
            # disclosed with its reason (WARN semantics) — never a silent
            # absence, never a mis-FAIL of history queries
            # (--skip-execution-gates / BR-4 released-history).
            print(f"  [SKIP] {label.replace('_', ' ')} — "
                  f"{detail.get('skip_reason')}")
            continue
        status = "PASS" if detail["pass"] else "FAIL"
        print(f"  [{status}] {label.replace('_', ' ')}")
        if detail.get("boundary"):
            print(f"    boundary: {detail['boundary']}")
        for gate_result in detail.get("results", []):
            gate_status = "PASS" if gate_result["pass"] else "FAIL"
            exit_code = gate_result["exit_code"]
            print(f"    [{gate_status}] {gate_result['label']} (exit={exit_code})")
        for issue in detail.get("issues", [])[:10]:
            print(f"    - {issue}")
        if len(detail.get("issues", [])) > 10:
            print(f"    ... and {len(detail['issues']) - 10} more")
    if result["pass"]:
        print("\n  Result: PASSED - release readiness checks are green.")
    else:
        print(f"\n  Result: FAILED - {len(result['issues'])} issue(s).")
        sys.exit(1)


def _render_ledger(args, *, host_project_root, plugin_root, repository_context, validate_release_ledger):
    """Validate declarative per-version release manifests and live Git facts."""
    from dataclasses import replace
    from release.context import RepositoryContext

    context = repository_context(host_project_root, timeout=getattr(args, "timeout", 15))
    source = plugin_root()
    if isinstance(context, RepositoryContext):
        context = replace(context, manifest_repository_root=source)
    result = validate_release_ledger(
        context,
        manifests_dir=source / "skills/software-project-governance/core/releases",
        version=getattr(args, "version", None),
        remote=getattr(args, "remote", "origin"),
        verify_remote=not getattr(args, "no_remote", False),
    ).as_dict()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["state"] != "PASS":
        sys.exit({"FAIL": 1, "UNKNOWN": 2, "BLOCKED": 3}.get(result["state"], 1))


def _render_projection(args, *, plugin_root, check_projections, write_projections):
    """Check or atomically write declared artifact projections.

    FIX-405 / RISK-061: the --write face appends an ``sd_integrity`` scan
    over the just-written projection targets (os.access R_OK + takeown/
    icacls remediation template) — restricted-token SD damage surfaces at
    the write moment; a damaged face FAILs the command (exit 1) instead
    of biting the next random access.
    """
    config = Path(args.config).resolve() if getattr(args, "config", None) else None
    if getattr(args, "write", False):
        result = write_projections(plugin_root(), config).as_dict()
        from checks.sd_integrity import projection_face_paths, scan_sd_readability
        # FIX-406 F-1: lift the face error instead of silently scanning an
        # empty path set behind .get("paths", []).
        _face = projection_face_paths(plugin_root(), config)
        _face_error = _face.get("error")
        sd_scan = scan_sd_readability(_face.get("paths", []))
        result["sd_integrity"] = {**sd_scan, "face_error": _face_error}
        if _face_error:
            result["state"] = "FAIL"
            result["issues"] = list(result.get("issues", [])) + [
                f"sd integrity: {_face_error}"]
        elif not sd_scan["pass"]:
            result["state"] = "FAIL"
            result["issues"] = list(result.get("issues", [])) + [
                "sd integrity: {0} unreadable — remediate: {1}".format(
                    path, cmd)
                for path, cmd in zip(sd_scan["unreadable"],
                                      sd_scan["remediation"])]
    else:
        result = check_projections(plugin_root(), config).as_dict()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["state"] != "PASS":
        sys.exit({"FAIL": 1, "UNKNOWN": 2, "BLOCKED": 3}.get(result["state"], 1))


def _render_quality(_args, *, probe_quality_tools):
    """Report optional ruff/mypy availability without overclaiming PASS."""
    result = probe_quality_tools()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["state"] == "FAIL":
        sys.exit(1)


def _ledger_inputs():
    from project_paths import default_host_root, package_root
    from release.context import RepositoryContext
    from release.ledger import validate_release_ledger
    return default_host_root(), package_root, RepositoryContext, validate_release_ledger


def _projection_inputs():
    from project_paths import package_root
    from release.projection import check_projections, write_projections
    return package_root, check_projections, write_projections


def _quality_probe():
    from release.quality import probe_quality_tools
    return probe_quality_tools()


def effective_command(name, native):
    return native


def bind_release_commands(*, ledger, projection, quality, command):
    """Use explicit live CLI bindings when the programmatic compatibility entry is loaded."""
    global _ledger_inputs, _projection_inputs, _quality_probe, effective_command
    _ledger_inputs, _projection_inputs, _quality_probe, effective_command = ledger, projection, quality, command


def cmd_release_ledger(args):
    host, plugin, context, validate = _ledger_inputs()
    return _render_ledger(args, host_project_root=host, plugin_root=plugin,
                          repository_context=context, validate_release_ledger=validate)


def cmd_release_projection(args):
    plugin, check, write = _projection_inputs()
    return _render_projection(args, plugin_root=plugin, check_projections=check, write_projections=write)


def cmd_quality_tools(_args):
    return _render_quality(_args, probe_quality_tools=_quality_probe)
