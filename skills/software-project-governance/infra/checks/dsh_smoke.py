"""Present the isolated DSH smoke result for governance health and CLI users."""


def _isolation_summary(result, *, show_home):
    isolation = result["isolation"]
    label = "Exit code" if show_home else "exit code"
    fields = [f"{label}: {result['exit_code']}",
              f"real-home writes: {isolation['real_home_writes']}"]
    if show_home:
        fields.append(f"temp DSH_HOME: {isolation['temp_home']} (removed)")
    attributed = isolation.get("attributed_concurrent_writes")
    if attributed:
        fields.append(f"attributed concurrent writes: {attributed} "
                      "(FIX-442 dual-factor, excluded)")
    return "; ".join(fields)


def _emit_diagnostics(details, limit, indent):
    for detail in details[:limit]:
        print(f"{indent}- {detail}")
    if len(details) > limit:
        print(f"{indent}... and {len(details) - limit} more")


def emit_health_result(result):
    """Print Check 28u and return the number of health issues it contributed."""
    print("\n┌─ Check 28u: DSH Preset Session Smoke (FEAT-015) ────┐")
    print("│  " + _isolation_summary(result, show_home=False))
    verdict = result["verdict"]
    if verdict not in ("PASS", "NOT_RUN"):
        verdict = "FAIL"
    print(f"│  [{verdict}] {result['reason']}")
    if verdict == "FAIL":
        _emit_diagnostics(result["details"], 12, "│    ")
        return 1
    return 0


def emit_cli_result(result):
    """Print the standalone smoke result and return its strict CLI exit code."""
    print("\n=== DSH Preset Session Smoke Check (FEAT-015 / RISK-049 ②) ===")
    print("  " + _isolation_summary(result, show_home=True))
    label, status = {"PASS": ("PASSED", 0), "NOT_RUN": ("NOT_RUN", 2)}.get(
        result["verdict"], ("FAILED", 1))
    print(f"\n  Result: {label} — {result['reason']}")
    if status == 1:
        _emit_diagnostics(result["details"], 20, "    ")
    print()
    return status
