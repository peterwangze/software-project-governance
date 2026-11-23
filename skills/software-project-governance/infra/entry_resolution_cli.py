"""Invoke the installed entry resolver with bounded time and classified diagnostics."""

from typing import NamedTuple

import os
import subprocess
import sys


class ResolverPolicy(NamedTuple):
    """The replaceable policy values for this check."""

    canonical_marker: str
    resolver_relative_path: str
    timeout_env: str
    resolve_exit_other: int
    resolve_exit_python_missing: int
    resolve_exit_file_not_found: int
    resolve_exit_timeout: int
    resolve_exit_store_stub: int


def _resolve_resolve_timeout(raw, *, default_seconds, positive_timeout):
    """FIX-238.3: resolve the resolve_entry timeout from an env-var value.

    SPG_RESOLVE_TIMEOUT (positive integer seconds, default 15s); invalid
    values fall back to the default (FIX-234 precedent) instead of crashing.
    """
    return positive_timeout(raw, default_seconds)


def cmd_resolve_entry(
    args, *, definition_policy, product_root, resolve_resolve_timeout,
):
    """Thin bounded invocation of resolve_entry.py with classified
    fail-closed diagnostics (file-not-found / timeout / python-missing /
    store-stub). Prints the JSON envelope on stdout on success."""
    script = product_root / definition_policy.resolver_relative_path
    if not script.is_file():
        print(
            f"spg-bootstrap-error: file-not-found — resolve_entry.py missing at {script}",
            file=sys.stderr,
        )
        sys.exit(definition_policy.resolve_exit_file_not_found)
    try:
        content = script.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(
            f"spg-bootstrap-error: file-not-found — cannot read {script}: {exc}",
            file=sys.stderr,
        )
        sys.exit(definition_policy.resolve_exit_file_not_found)
    if definition_policy.canonical_marker not in content:
        print(
            "spg-bootstrap-error: store-stub — resolve_entry.py exists but is not "
            "the canonical resolver (missing FX-130 marker); reinstall the plugin",
            file=sys.stderr,
        )
        sys.exit(definition_policy.resolve_exit_store_stub)
    timeout = resolve_resolve_timeout(os.environ.get(definition_policy.timeout_env, ""))
    command = [sys.executable, str(script), "--json"]
    if getattr(args, "project_root", None):
        command += ["--project-root", args.project_root]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        print(
            f"spg-bootstrap-error: timeout — resolve_entry did not finish within "
            f"{timeout}s (SPG_RESOLVE_TIMEOUT); raise the value or inspect the host",
            file=sys.stderr,
        )
        sys.exit(definition_policy.resolve_exit_timeout)
    except FileNotFoundError as exc:
        print(f"spg-bootstrap-error: python-missing — {exc}", file=sys.stderr)
        sys.exit(definition_policy.resolve_exit_python_missing)
    if completed.returncode != 0:
        print(
            f"spg-bootstrap-error: resolve_entry exited {completed.returncode}",
            file=sys.stderr,
        )
        if completed.stderr:
            sys.stderr.write(completed.stderr)
        sys.exit(definition_policy.resolve_exit_other)
    sys.stdout.write(completed.stdout)
