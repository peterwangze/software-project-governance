"""ArchGuard source-size, function and constant checks for plugin and host projects."""

import ast
import fnmatch
import json
import os
import re
import sys
from pathlib import Path


def _archguard_severity(count, warn, error):
    if error is not None and count >= error:
        return "ERROR"
    if warn is not None and count >= warn:
        return "WARN"
    return None


def _archguard_exclusion_match(rel_path, exclusions):
    """Return the first exclusion entry matching rel_path, or None.

    Single matching implementation for every ArchGuard scan face (FIX-350):
    fnmatch on the posix form, supports ``**`` segments. Callers that only
    need the boolean verdict use :func:`_archguard_excluded`; callers that
    must disclose WHICH rule fired (DEC-151: 豁免必披露) take the entry's
    ``reason`` from here.
    """
    posix = str(rel_path).replace("\\", "/")
    for entry in exclusions or []:
        pat = entry.get("path") if isinstance(entry, dict) else entry
        if not pat:
            continue
        # Support a leading **/ by also matching the basename segment.
        if fnmatch.fnmatch(posix, pat):
            return entry
        if pat.startswith("**/"):
            base = pat[3:]
            if fnmatch.fnmatch(Path(posix).name, base):
                return entry
            if fnmatch.fnmatch(posix, base):
                return entry
        # segment-agnostic match: any path containing a segment matching the bare glob
        bare = pat.replace("**/", "").replace("/**", "")
        if bare and any(fnmatch.fnmatch(seg, bare) for seg in posix.split("/")):
            return entry
    return None


def _archguard_excluded(rel_path, exclusions):
    """True if rel_path matches any exclusion glob (fnmatch, supports ** segments)."""
    return _archguard_exclusion_match(rel_path, exclusions) is not None


def _raise_walk_error(exc):
    raise exc


def _archguard_iter_code_files(root, extensions=(".py", ".js", ".ts"), *, installed_plugin=None):
    """Keep host scans inside their source tree and skip a nested plugin installation."""
    root = Path(root)
    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", ".pytest_cache"}
    if installed_plugin is not None:
        skip_dirs.add(".governance")
    for dirpath, dirnames, filenames in os.walk(
        root, onerror=_raise_walk_error if installed_plugin is not None else None
    ):
        parent = Path(dirpath)
        dirnames[:] = [name for name in dirnames if name not in skip_dirs]
        if installed_plugin is not None:
            # A symlink or Windows junction may lead into another project.
            dirnames[:] = [name for name in dirnames if (parent / name).resolve() == parent / name
                           and parent / name != installed_plugin]
        for name in filenames:
            path = parent / name
            if name.endswith(extensions) and (installed_plugin is None or not path.is_symlink()):
                yield path.relative_to(root), path


def scan_architecture(root, schema, *, installed_plugin=None):
    ms = schema.get("module_size", {})
    fs = schema.get("function_size", {})
    mc = schema.get("module_constants", {})
    gate = schema.get("gate_integration", {})
    exclusions = ms.get("exclusions", [])
    ms_warn, ms_error = ms.get("warn_lines"), ms.get("error_lines")
    fn_warn, fn_error = fs.get("warn_lines"), fs.get("error_lines")
    c_warn, c_error = mc.get("warn_count"), mc.get("error_count")
    detect_dup = bool(mc.get("detect_duplicates"))

    findings = []
    const_re = re.compile(r"^[A-Z][A-Z0-9_]+ *=")

    files_scanned = 0
    for rel, abs_path in _archguard_iter_code_files(root, installed_plugin=installed_plugin):
        if _archguard_excluded(rel, exclusions):
            continue
        try:
            text = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            if installed_plugin is not None:
                raise
            continue
        files_scanned += 1
        lines = text.splitlines()
        n_lines = len(lines)

        sev = _archguard_severity(n_lines, ms_warn, ms_error)
        if sev:
            findings.append({
                "check": "module_size", "severity": sev,
                "path": str(rel), "lines": n_lines,
            })

        # Python-only: function size via ast + module constants + duplicate constants
        if str(rel).endswith(".py"):
            # function sizes
            try:
                tree = ast.parse(text)
            except SyntaxError:
                tree = None
            if tree is not None:
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.end_lineno:
                        fn_lines = node.end_lineno - node.lineno + 1
                        sev = _archguard_severity(fn_lines, fn_warn, fn_error)
                        if sev:
                            findings.append({
                                "check": "function_size", "severity": sev,
                                "path": str(rel), "name": node.name,
                                "lines": fn_lines, "lineno": node.lineno,
                            })
            # module constants + duplicates
            const_names = {}  # name -> first line
            dup_names = {}    # name -> list of lines
            for idx, line in enumerate(lines, start=1):
                m = const_re.match(line)
                if not m:
                    continue
                name = m.group(0).split("=")[0].strip()
                if name not in const_names:
                    const_names[name] = idx
                else:
                    dup_names.setdefault(name, [const_names[name]]).append(idx)
            if const_names:
                sev = _archguard_severity(len(const_names), c_warn, c_error)
                if sev:
                    findings.append({
                        "check": "module_constants", "severity": sev,
                        "path": str(rel), "count": len(const_names),
                    })
            if detect_dup:
                for name, ln_list in dup_names.items():
                    findings.append({
                        "check": "duplicate_constant", "severity": "ERROR",
                        "path": str(rel), "name": name, "lines": ln_list,
                    })

    errors = sum(1 for f in findings if f["severity"] == "ERROR")
    warnings = sum(1 for f in findings if f["severity"] == "WARN")
    result = {
        "findings": findings,
        "summary": {"errors": errors, "warnings": warnings},
        "schema_version": schema.get("version"),
        "fatal_on_error": bool(gate.get("fatal_on_error", False)),
    }
    if installed_plugin is not None:
        result["files_scanned"] = files_scanned
    return result


_SIZE_LIMITS = {
    "module_size": ("warn_lines", "error_lines"),
    "function_size": ("warn_lines", "error_lines"),
    "module_constants": ("warn_count", "error_count"),
}
_HOST_SECTIONS = (*_SIZE_LIMITS, "gate_integration")


def _read_policy(path):
    try:
        with path.open(encoding="utf-8") as stream:
            policy = json.load(stream)
    except (OSError, ValueError) as exc:
        raise ValueError(f"cannot load architecture policy {path}: {exc}") from exc
    if not isinstance(policy, dict):
        raise ValueError(f"invalid architecture policy {path}: expected a JSON object")
    return policy


def _validate_policy(policy):
    for section in _HOST_SECTIONS:
        if not isinstance(policy.get(section), dict):
            raise ValueError(f"{section} must be an object")
    for section, (warn, error) in _SIZE_LIMITS.items():
        limits = policy[section]
        for key in (warn, error):
            value = limits.get(key)
            if type(value) is not int or value < 1:
                raise ValueError(f"{section}.{key} must be a positive integer")
        if limits[warn] > limits[error]:
            raise ValueError(f"{section}.{warn} exceeds {error}")
    for section, key in (("gate_integration", "fatal_on_error"),
                         ("module_constants", "detect_duplicates")):
        if type(policy[section].get(key)) is not bool:
            raise ValueError(f"{section}.{key} must be a boolean")
    exclusions = policy["module_size"].get("exclusions", [])
    if not isinstance(exclusions, list):
        raise ValueError("module_size.exclusions must be a list")
    for entry in exclusions:
        pattern = entry.get("path") if isinstance(entry, dict) else entry
        if not isinstance(pattern, str) or not pattern.strip():
            raise ValueError("invalid path in module_size.exclusions")


def host_architecture_health(host, plugin, default_path, policy_path):
    """Apply the installed thresholds to host code, with an optional explicit override."""
    policy = _read_policy(default_path)
    _validate_policy(policy)
    # Published product/projection-specific exemptions belong only to the plugin.
    shared_paths = {"**/tests/**", "**/test_*.py", ".governance/**"}
    policy["module_size"]["exclusions"] = [
        entry for entry in policy["module_size"].get("exclusions", [])
        if (entry.get("path") if isinstance(entry, dict) else entry) in shared_paths
    ]
    if policy_path is not None:
        updates = _read_policy(policy_path)
        unknown = updates.keys() - policy.keys()
        if unknown:
            raise ValueError(f"unknown architecture policy key(s): {', '.join(sorted(unknown))}")
        if not any(section in updates for section in _HOST_SECTIONS):
            raise ValueError("policy must specify an architecture-health check or gate")
        for section in _HOST_SECTIONS:
            if section in updates:
                patch = updates[section]
                if not isinstance(patch, dict) or patch.keys() - policy[section].keys():
                    raise ValueError(f"invalid architecture policy fields in {section}")
                policy[section].update(patch)
        _validate_policy(policy)
    return scan_architecture(host, policy, installed_plugin=plugin)


def run_architecture_health(args, host, plugin, default_policy, check_plugin, print_findings):
    """Run REQ-101 ArchGuard module/function/constant-size guard (advisory in 0.58.0)."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("\n=== Architecture Health Check (ArchGuard) ===")
    host_scope = getattr(args, "scope", "plugin") == "host"
    override = getattr(args, "policy", None)
    if host_scope:
        policy_path = host / override if override is not None else None
        print(f"  Host source: {host}\n  Installed policy: {default_policy}")
        if policy_path is not None:
            print(f"  Host policy override: {policy_path}")
        try:
            result = host_architecture_health(host, plugin, default_policy, policy_path)
        except (ValueError, OSError) as exc:
            print(f"  [ERROR] {exc}", file=sys.stderr)
            sys.exit(2)
        print(f"  Source files scanned (.py, .js, .ts): {result['files_scanned']}")
        if not result["files_scanned"]:
            print("  [ERROR] No eligible host source files found", file=sys.stderr)
            sys.exit(2)
    else:
        if override is not None:
            print("  [ERROR] --policy requires --scope host", file=sys.stderr)
            sys.exit(2)
        result = check_plugin()
    if result.get("error"):
        print(f"  [ERROR] {result['error']}")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
        print()
        return
    errors, warnings = print_findings("Architecture Health", result)
    fatal = bool(result.get("fatal_on_error"))
    label = "PASSED" if host_scope and not (errors or warnings) else "ISSUES FOUND"
    print(f"\n  Result: {label} — {errors} ERROR, {warnings} WARN"
          + (" (advisory — does not block release)" if not fatal else ""))
    if getattr(args, "fail_on_issues", False) and fatal and errors > 0:
        sys.exit(1)
    print()
