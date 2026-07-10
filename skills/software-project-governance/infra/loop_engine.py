#!/usr/bin/env python3
"""
Loop-engineering registry loader — FX-188 (0.65.0 loop-engineering, slice 1).

Read-only loader for ``core/loop-engineering-registry.json``. This module is
the first slice of the loop-engineering version: it declares and exposes the
loop topology / fuse / pause-point schema. It does NOT activate any runtime
loop behavior, does NOT modify gate judgment, and does NOT auto-fire any
back-edge.

**Why a separate module (not folded into verify_workflow.py):**

  - The loader must be importable without pulling in verify_workflow.py
    (avoid the import cycle, and keep this cheap for read-only consumers).
    This mirrors resolve_entry.py's "MUST NOT import verify_workflow.py"
    constraint.
  - Fail-closed contract is identical to ``_load_lifecycle_registry`` in
    verify_workflow.py: missing/corrupt JSON returns ``(None, [diagnostic])``
    and never raises.

**Anchors (same as resolve_entry.py line 45):**

  PLUGIN_HOME = Path(__file__).resolve().parent.parent
              (= skills/software-project-governance/, where SKILL.md lives)

The registry file lives at ``PLUGIN_HOME / "core/loop-engineering-registry.json"``.

Usage:
    from loop_engine import load_loop_registry, get_loop_gate_semantics

    data, issues = load_loop_registry()
    if data is None:
        # issues explains why; fail-closed — never raises.
        ...
    g6 = get_loop_gate_semantics("G6")
"""

import json
from pathlib import Path

# ─── Fixed anchors ─────────────────────────────────────────────
# PLUGIN_HOME is derived from __file__ ONLY to locate the plugin's own
# executables and registry files. Same convention as resolve_entry.py.
PLUGIN_HOME = Path(__file__).resolve().parent.parent

# Relative path (from PLUGIN_HOME) to the loop-engineering registry.
_LOOP_REGISTRY_REL = "core/loop-engineering-registry.json"


def _loop_registry_path(plugin_home):
    """Resolve the registry path from an (optional) plugin_home override."""
    home = Path(plugin_home) if plugin_home is not None else PLUGIN_HOME
    return home / _LOOP_REGISTRY_REL


def load_loop_registry(plugin_home=None):
    """Load loop-engineering-registry.json.

    Returns ``(data_or_None, issues_list)``. Fail-closed on missing/corrupt:
    a missing file or invalid JSON yields ``(None, [diagnostic_string])``
    and never raises.

    Mirrors the ``_load_lifecycle_registry`` contract in verify_workflow.py.
    """
    registry_path = _loop_registry_path(plugin_home)
    try:
        display = str(registry_path)
    except Exception:  # pragma: no cover - defensive
        display = "<loop-engineering-registry>"
    if not registry_path.exists():
        return None, [f"{display}: missing loop-engineering registry"]
    try:
        text = registry_path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, [f"{display}: cannot read loop-engineering registry: {exc}"]
    try:
        return json.loads(text), []
    except json.JSONDecodeError as exc:
        return None, [f"{display}: invalid JSON: {exc}"]


def _entry_by_id(entries, key, value):
    """Linear search for ``{key: value}`` in a list of dict entries."""
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if isinstance(entry, dict) and entry.get(key) == value:
            return entry
    return None


def get_loop_gate_semantics(gate_id, plugin_home=None):
    """Return the loop_gate_semantics entry for a gate (G1-G11).

    Returns the matching dict, or ``None`` if the gate id is absent or the
    registry cannot be loaded (fail-closed).
    """
    data, _issues = load_loop_registry(plugin_home)
    if data is None:
        return None
    return _entry_by_id(data.get("loop_gate_semantics"), "gate_id", gate_id)


def get_pause_point(pp_id, plugin_home=None):
    """Return a PausePoint declaration by id.

    Returns the matching dict, or ``None`` if absent or the registry cannot
    be loaded (fail-closed).
    """
    data, _issues = load_loop_registry(plugin_home)
    if data is None:
        return None
    pause_points = data.get("pause_points")
    if not isinstance(pause_points, dict):
        return None
    entry = pause_points.get(pp_id)
    return entry if isinstance(entry, dict) else None


def get_fuse(fuse_id, plugin_home=None):
    """Return a LoopFuse declaration by id.

    Returns the matching dict, or ``None`` if absent or the registry cannot
    be loaded (fail-closed).
    """
    data, _issues = load_loop_registry(plugin_home)
    if data is None:
        return None
    fuses = data.get("loop_fuses")
    if not isinstance(fuses, dict):
        return None
    entry = fuses.get(fuse_id)
    return entry if isinstance(entry, dict) else None
