"""Display the installed plugin and its distance from the source HEAD."""


def report_plugin_freshness(result, product_root):
    """Display the freshness evidence and set the exit status for CI."""
    # Calculate behind count
    import subprocess
    try:
        # Try to find installed commit in git log
        r = subprocess.run(
            ["git", "rev-list", "--count", f"{result['installed_commit']}..HEAD"],
            capture_output=True, text=True, cwd=str(product_root()), timeout=5
        )
        if r.returncode == 0:
            result["commits_behind"] = int(r.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError, ValueError):
        pass

    print()
    print("=== Plugin Freshness Check ===")
    print(f"  Installed: {result['installed_version']} (commit {result['installed_commit']}, {result['installed_date']})")
    print(f"  Source:    {result['source_version']} (commit {result['source_commit']})")
    print(f"  Status:    {result['status']}")
    if result["commits_behind"] > 0:
        print(f"  Behind:    {result['commits_behind']} commit(s)")
    if result["action"]:
        print(f"  Action:    {result['action']}")
    print()

    # Exit with error if outdated (for CI)
    if result["status"] == "OUTDATED":
        import sys
        sys.exit(1)
