#!/usr/bin/env python3
"""
Flow-unit derivation — FX-190 (0.65.0 loop-engineering, slice 3).

Closes the VAL-006 gap (ADR §7.4): flow units are derived from a target
project's plan-tracker per project type, not just from the ``python_game``
example baked into ``lifecycle-registry.json``.

For each project type, this module reads a target project's plan-tracker and
derives a list of flow units:

  - **game**          → chapters / levels
  - **web-app** / **mobile-app** → stories / screens / modules
  - **library**       → modules / api-surface (public API boundaries)
  - **cli-tool**      → commands (one flow unit per command)  [VAL-006 load-bearing]
  - **ai-agent-plugin** → adapters / skills / manifest
  - **internal-script** → single unit
  - **Fallback** (no decomposition detectable) → ONE unit
    ``{project_id}.whole`` with ``derivation_reason`` set.

It reads ``project_type_gate_presets`` from ``lifecycle-registry.json`` for
``default_flow_unit_type`` and ``unit_templates`` per project type. When the
registry is missing or corrupt, a set of hardcoded defaults is used (ADR §7.4
fail-closed — derivation never raises).

**Produced units are DORMANT.** The ``loop_state`` on each derived unit is the
3-field dormant shape (``{active_loop, loop_count, last_loop_type}``). Loop
activation is FX-189's job (:func:`loop_engine.activate_loop_state`); this
module does NOT import loop_engine at module top-level and does not activate
anything.

**Anchors (same as loop_engine.py / resolve_entry.py):**
  PLUGIN_HOME = Path(__file__).resolve().parent.parent
              (= skills/software-project-governance/, where SKILL.md lives)

The registry file lives at ``PLUGIN_HOME / "core/lifecycle-registry.json"``.

Tolerant parsing contract (ADR §7.4 — "the plan-tracker has NO formal schema
for unit decomposition"):
  The plan-tracker is hand-written markdown. There is no guarantee of any
  particular id format. The derivation must therefore try several heuristics
  in order and fall back gracefully:

    1. Dotted task-id prefixes that name a unit — e.g.
       ``game.chapter.01`` or ``mycli.init``.
    2. Standalone unit-type keywords in task descriptions — e.g.
       "init command", "build command", "Chapter 2".
    3. If nothing decomposable is found → ONE fallback ``{project_id}.whole``
       unit so the caller always gets at least one unit.

Usage:
    from flow_unit_derive import derive_flow_units

    units = derive_flow_units("/path/to/my-cli", "cli-tool", plan_tracker_text)
    # -> [{flow_unit_id: "my-cli.command.init", unit_type: "command", ...}, ...]
"""

import json
import re
from pathlib import Path

# ─── Fixed anchors ─────────────────────────────────────────────
# PLUGIN_HOME is derived from __file__ ONLY to locate the plugin's own
# registry file. Same convention as loop_engine.py / resolve_entry.py.
PLUGIN_HOME = Path(__file__).resolve().parent.parent

# Relative path (from PLUGIN_HOME) to the lifecycle registry that carries
# project_type_gate_presets (default_flow_unit_type + unit_templates).
_LIFECYCLE_REGISTRY_REL = "core/lifecycle-registry.json"


# ─── Hardcoded fallback defaults (used when registry is unavailable) ─────────
# ADR §7.4 fail-closed: if lifecycle-registry.json is missing or corrupt, we
# still need a default unit type per project type. These mirror the registry's
# default_flow_unit_type values exactly (kept in sync manually — verified by
# test_default_unit_types_match_registry when the registry is present).
_DEFAULT_UNIT_TYPES = {
    "game": "chapter",
    "web-app": "story",
    "mobile-app": "story",
    "library": "module",
    "cli-tool": "command",
    "ai-agent-plugin": "skill",
    "internal-script": "script",
}

# Per-type keyword vocabularies used for tolerant (heuristic) parsing. These
# are the unit-template words we look for in the plan-tracker text when no
# structured dotted-id pattern is found. Order matters within each list: the
# FIRST keyword that yields matches wins (so the most specific/preferred unit
# type for that project type is tried first).
_DEFAULT_UNIT_KEYWORDS = {
    "game": ["chapter", "level"],
    "web-app": ["story", "module", "screen"],
    "mobile-app": ["story", "screen", "module"],
    "library": ["module", "api-surface"],
    "cli-tool": ["command"],
    "ai-agent-plugin": ["adapter", "skill", "manifest"],
    "internal-script": ["script", "job"],
}


# ═══════════════════════════════════════════════════════════════════════════
# Registry access (fail-closed — mirrors loop_engine.load_loop_registry)
# ═══════════════════════════════════════════════════════════════════════════


def _load_project_type_presets(plugin_home=None):
    """Load ``project_type_gate_presets`` from ``lifecycle-registry.json``.

    Returns a dict mapping ``project_type`` →
    ``{default_flow_unit_type, unit_templates, ...}``. Fail-closed: a missing
    file or invalid JSON yields ``{}`` and never raises (callers then fall
    back to :data:`_DEFAULT_UNIT_TYPES`).
    """
    home = Path(plugin_home) if plugin_home is not None else PLUGIN_HOME
    registry_path = home / _LIFECYCLE_REGISTRY_REL
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    presets = data.get("project_type_gate_presets", {})
    return presets if isinstance(presets, dict) else {}


def _get_preset(project_type, plugin_home=None):
    """Get the preset dict for a project type.

    Returns the matching preset dict, or ``None`` if the project type is
    unknown or the registry cannot be loaded (fail-closed).
    """
    presets = _load_project_type_presets(plugin_home)
    preset = presets.get(project_type)
    return preset if isinstance(preset, dict) else None


def _resolve_default_unit_type(project_type, plugin_home=None):
    """Resolve the default flow-unit type for a project type.

    Prefers the registry's ``default_flow_unit_type``; falls back to the
    hardcoded :data:`_DEFAULT_UNIT_TYPES`. Never raises.
    """
    preset = _get_preset(project_type, plugin_home)
    if preset:
        val = preset.get("default_flow_unit_type")
        if isinstance(val, str) and val.strip():
            return val
    return _DEFAULT_UNIT_TYPES.get(project_type)


def _resolve_unit_keywords(project_type, plugin_home=None):
    """Resolve the ordered list of unit-type keywords to look for.

    Prefers the registry's ``unit_templates`` (in declared order); falls back
    to :data:`_DEFAULT_UNIT_KEYWORDS`. Never raises. Always returns a list.
    """
    preset = _get_preset(project_type, plugin_home)
    if preset:
        templates = preset.get("unit_templates")
        if isinstance(templates, list) and templates:
            # Keep only non-empty string entries, preserving order.
            cleaned = [t for t in templates if isinstance(t, str) and t.strip()]
            if cleaned:
                return cleaned
    return list(_DEFAULT_UNIT_KEYWORDS.get(project_type, []))


# ═══════════════════════════════════════════════════════════════════════════
# project_id derivation + dormant loop_state factory
# ═══════════════════════════════════════════════════════════════════════════


def _derive_project_id(target_root):
    """Derive a stable project_id from target_root.

    Uses the directory's basename, sanitized: lowercased, with runs of
    whitespace / non-alphanumeric characters (except ``.`` and ``-``)
    collapsed to single hyphens. Trailing/leading hyphens are stripped.

    Examples:
        ``/path/to/my-awesome-cli`` → ``my-awesome-cli``
        ``My Cool Project``        → ``my-cool-project``
        ``foo_bar.baz``            → ``foo-bar.baz``  (dots preserved)

    If ``target_root`` is falsy or has no usable name, returns
    ``"unknown-project"``.
    """
    if target_root is None:
        return "unknown-project"
    try:
        name = Path(str(target_root)).name
    except Exception:  # pragma: no cover - defensive
        return "unknown-project"
    if not name:
        return "unknown-project"
    # Lowercase, keep alphanumerics, dots, and hyphens; everything else → '-'.
    sanitized = re.sub(r"[^a-z0-9.\-]+", "-", name.lower())
    # Collapse runs of hyphens and strip leading/trailing ones.
    sanitized = re.sub(r"-{2,}", "-", sanitized).strip("-")
    return sanitized or "unknown-project"


def _dormant_loop_state():
    """Build a fresh DORMANT loop_state dict (the 3-field shape).

    This is the dormant shape that shipped with FX-188's example data. FX-189's
    :func:`loop_engine.activate_loop_state` expands it to the 5-field activated
    shape; FX-190 deliberately produces ONLY the dormant shape because derived
    units are data, not runtime-activated units.
    """
    return {
        "active_loop": False,
        "loop_count": 0,
        "last_loop_type": None,
    }


def _make_unit(project_id, unit_type, name, title=None, project_type=None,
               derivation_reason=None):
    """Construct a single flow-unit dict conforming to flow_unit_schema.

    All units are emitted at the default starting stage (``initiation`` /
    ``planning`` subphase, ``backlog`` gate lane) — derived units begin life
    unscheduled. The caller (or a future migration) may advance them.

    Args:
        project_id: Sanitized project id (the prefix of flow_unit_id).
        unit_type: One of the schema's allowed_unit_types
            (chapter/level/command/module/story/screen/adapter/skill/script/...).
        name: The unit's machine-readable name within the project, e.g.
            ``"init"`` for a command or ``"01"`` for a chapter. Becomes the
            tail of ``flow_unit_id``.
        title: Optional human-readable title. Defaults to a Title-Cased
            rendering of ``"{unit_type} {name}"``.
        project_type: The originating project_type (recorded for traceability).
        derivation_reason: Optional explanation of why this unit was produced
            (set on fallback units).

    Returns:
        A dict with all 15 flow_unit_schema.required_fields populated, plus
        ``derivation_reason`` when supplied.
    """
    safe_name = str(name).strip() if name is not None else "unit"
    flow_unit_id = "{pid}.{ut}.{nm}".format(
        pid=project_id, ut=unit_type, nm=safe_name
    )
    if title is None:
        # Title-case the unit type and append the name. e.g. "Command init",
        # "Chapter 01". Keeps it human-readable without over-engineering.
        title = "{ut_t} {nm}".format(
            ut_t=str(unit_type).capitalize(), nm=safe_name
        )
    unit = {
        "flow_unit_id": flow_unit_id,
        "title": title,
        "unit_type": unit_type,
        "project_type": project_type,
        "lifecycle_mode": "dynamic-flow-gate",
        "current_stage": "initiation",
        "current_subphase": "planning",
        "gate_lane": "backlog",
        "gate_references": [],
        "allowed_next_transitions": [],
        "dependencies": [],
        "blockers": [],
        "evidence_refs": [],
        "loop_state": _dormant_loop_state(),
        "runtime_status_source": "example-data-only",
    }
    if derivation_reason is not None:
        unit["derivation_reason"] = derivation_reason
    return unit


def _fallback_single_unit(project_id, project_type=None,
                          reason="no-decomposable-structure-found"):
    """Create ONE fallback unit ``{project_id}.whole``.

    Used when no decomposable structure can be detected in the plan-tracker,
    or when the project type is unrecognized. Guarantees the caller always
    receives at least one flow unit.

    The unit's ``unit_type`` is ``"script"`` (a neutral, schema-allowed type
    meaning "an undifferentiated whole") and a ``derivation_reason`` field is
    attached explaining why the fallback fired.
    """
    return _make_unit(
        project_id,
        "script",
        "whole",
        title="{pid} (whole project)".format(pid=project_id),
        project_type=project_type,
        derivation_reason=reason,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Tolerant plan-tracker parsing helpers
# ═══════════════════════════════════════════════════════════════════════════


def _normalize_text(text):
    """Defensively coerce plan-tracker input to a string.

    Never raises. ``None`` / non-string inputs become ``""``.
    """
    if text is None:
        return ""
    if isinstance(text, str):
        return text
    try:
        return str(text)
    except Exception:  # pragma: no cover - defensive
        return ""


def _dedupe_preserve_order(names):
    """Remove duplicates from a list while preserving first-seen order."""
    seen = set()
    out = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _find_dotted_unit_names(text, keywords):
    """Find unit names embedded in dotted task-id prefixes.

    Scans for tokens shaped ``<word>.<keyword>.<name>`` (case-insensitive),
    where ``<keyword>`` is one of the provided unit-type keywords. Returns the
    list of ``<name>`` captures in first-seen order, deduplicated.

    Examples (keyword=["command"]):
        ``mycli.init``         → (NO match — "init" is the name but there is no
                                  explicit "command" token between prefix and
                                  name; handled by the prefix-name heuristic
                                  below in :func:`_derive_cli_tool_units`)
        ``mycli.command.init`` → match, name="init"
        ``tool.command.build`` → match, name="build"

    Examples (keyword=["chapter"]):
        ``game.chapter.01`` → match, name="01"
        ``game.chapter.02`` → match, name="02"
    """
    if not text or not keywords:
        return []
    names = []
    for kw in keywords:
        # Match: boundary, optional prefix token(s) ending in '.', the keyword,
        # a literal '.', then a capture of the unit name (letters, digits,
        # underscore, hyphen). re.escape the keyword so e.g. "api-surface"
        # matches literally.
        pattern = r"(?:^|[\s\W])\w+(?:\.\w+)*\." + re.escape(kw) + r"\.([A-Za-z0-9_\-]+)"
        for m in re.findall(pattern, text, flags=re.IGNORECASE):
            if m:
                names.append(m)
    return _dedupe_preserve_order(names)


def _find_keyword_names(text, keywords):
    """Find unit names from keyword mentions in descriptions.

    Scans for phrases like ``"<name> <keyword>"`` or ``"<keyword> <name>"``
    (with ``:`` / ``-`` also accepted as separators), case-insensitive::

        "init command"   (keyword-second) → name="init"
        "command init"   (keyword-first)  → name="init"
        "Chapter 2"      (keyword-first)  → name="2"
        "module: auth"   (keyword-first)  → name="auth"

    Returns the list of captured names in first-seen order, deduplicated.

    Non-double-count guarantee: for each keyword we run ONE ``finditer`` pass
    over a combined pattern (``<name> <kw>`` OR ``<kw> <name>``). Because
    ``re.finditer`` yields non-overlapping matches left-to-right, a sentence
    like ``"the build command compiles"`` matches ``"build command"`` ONCE
    (capturing ``build``) and never re-matches ``"command compiles"`` — the
    ``command`` token is consumed by the first match. A naive two-pass
    ``findall`` approach (one for each form) would wrongly emit both
    ``build`` and ``compiles`` here.
    """
    if not text or not keywords:
        return []
    names = []
    stopwords = {
        "the", "a", "an", "of", "and", "for", "to", "in", "is", "are",
        "this", "that", "with", "each", "all", "new",
    }
    kwset = {k.lower() for k in keywords}
    for kw in keywords:
        # Form A "<name> <kw>" (keyword-second) — preferred at a given position
        # because CLI docs say "the init command". Tried first via alternation
        # order so leftmost-longest non-overlapping semantics prefer it.
        form_a = (
            r"\b([A-Za-z][A-Za-z0-9_\-]*)\b[\s:\-]+\b" + re.escape(kw) + r"\b"
        )
        # Form B "<kw> <name>" (keyword-first) — e.g. "Chapter 2", "module: auth".
        form_b = (
            r"\b" + re.escape(kw) + r"\b[\s:\-]+([A-Za-z0-9][A-Za-z0-9_\-]*)"
        )
        combined = "(?:" + form_a + "|" + form_b + ")"
        for m in re.finditer(combined, text, flags=re.IGNORECASE):
            # group(1) = form A capture, group(2) = form B capture.
            name = m.group(1) if m.group(1) is not None else m.group(2)
            low = name.lower()
            # Reject stopwords and other unit keywords ("command command").
            if low in kwset or low in stopwords:
                continue
            names.append(name)
    return _dedupe_preserve_order(names)


def _build_units_from_names(project_id, unit_type, names, project_type=None):
    """Build a list of flow-unit dicts from a list of unit names.

    Returns an empty list if ``names`` is empty.
    """
    units = []
    for nm in names:
        units.append(
            _make_unit(project_id, unit_type, nm, project_type=project_type)
        )
    return units


# ═══════════════════════════════════════════════════════════════════════════
# Per-type derivation handlers
#
# Each handler takes ``(plan_tracker_text, project_id, plugin_home=None)`` and
# returns a list of flow-unit dicts (possibly empty — the dispatcher handles
# the empty → fallback transition). Handlers MUST NOT raise; they tolerate
# arbitrary text input.
# ═══════════════════════════════════════════════════════════════════════════


def _derive_game_units(plan_tracker_text, project_id, plugin_home=None):
    """Derive chapter/level flow units from a game plan-tracker.

    Game plan-trackers typically carry task ids like ``game.chapter.01`` or
    prose mentioning "Chapter N". One flow unit is emitted per detected
    chapter/level, using the project type's ``default_flow_unit_type``
    (normally ``"chapter"``).

    Returns an empty list if no chapter/level structure is detectable (the
    caller then falls back to a single whole-project unit).
    """
    text = _normalize_text(plan_tracker_text)
    keywords = _resolve_unit_keywords("game", plugin_home) or ["chapter", "level"]
    default_type = _resolve_default_unit_type("game", plugin_home) or "chapter"

    # Strategy 1: dotted task-id prefixes (game.chapter.01, game.level.02).
    names = _find_dotted_unit_names(text, keywords)
    # Strategy 2: keyword mentions in prose ("Chapter 1", "level: boss").
    if not names:
        names = _find_keyword_names(text, keywords)
    return _build_units_from_names(project_id, default_type, names, "game")


def _derive_cli_tool_units(plan_tracker_text, project_id, plugin_home=None):
    """Derive command flow units from a CLI-tool plan-tracker.

    VAL-006 load-bearing case: a CLI tool's commands are its natural flow
    units. This handler looks for:

      1. Explicit dotted ids ``<prefix>.command.<name>`` (e.g.
         ``mycli.command.init``).
      2. ``<prefix>.<name>`` task ids where ``<prefix>`` looks like a CLI
         binary name (e.g. ``mycli.init``, ``mycli.build``,
         ``mycli.deploy``). The middle segment must NOT itself be a generic
         unit word (otherwise we'd mis-parse ``mycli.module.x``).
      3. Prose mentions like "init command", "build command", or
         "command: deploy".

    Returns one ``command`` unit per detected command, or an empty list if
    none found.
    """
    text = _normalize_text(plan_tracker_text)
    keywords = _resolve_unit_keywords("cli-tool", plugin_home) or ["command"]

    names = []

    # Strategy 1: explicit "<prefix>.command.<name>" dotted ids.
    names.extend(_find_dotted_unit_names(text, ["command"]))

    # Strategy 2: generic "<prefix>.<name>" two-segment ids where prefix looks
    # like a cli binary name. We require the prefix to contain a hyphen or the
    # literal token "cli"/"tool" so we don't mis-grab arbitrary dotted prose.
    # Capture (prefix, name) and keep the name.
    # Examples that match: "mycli.init", "my-cli.build", "deploy-tool.run".
    two_seg = re.compile(
        r"(?i)(?:^|[\s\W])([A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*)"
        r"(?:cli|tool)?"
        r"\.([A-Za-z][A-Za-z0-9_\-]*)"
    )
    # Restrict the prefix so we don't sweep up normal sentences. A prefix is
    # considered a CLI binary candidate if it (or prefix+suffix) contains
    # "cli"/"tool", OR the prefix has a hyphen, OR an unhyphenated prefix is
    # immediately followed by a verb-like command name. To keep this robust
    # and avoid false positives from prose, we gate on: the prefix token ends
    # with "cli"/"tool" OR contains a hyphen, OR the line also contains the
    # word "command" nearby. Simplest reliable gate: prefix ends in cli/tool
    # OR contains '-', and the captured name is not a stopword.
    stop = {"command", "module", "the", "a", "an", "and", "of", "for", "v"}
    for m in two_seg.findall(text):
        prefix, nm = m[0].lower(), m[1].lower()
        if nm in stop or prefix in stop:
            continue
        looks_like_cli = (
            prefix.endswith("cli")
            or prefix.endswith("tool")
            or "-" in prefix
        )
        if looks_like_cli:
            names.append(m[1])

    # Strategy 3: keyword mentions ("init command", "build command",
    # "command: deploy"). This is the most tolerant path and catches the
    # common "the X command" phrasing.
    names.extend(_find_keyword_names(text, keywords))

    names = _dedupe_preserve_order(names)
    return _build_units_from_names(project_id, "command", names, "cli-tool")


def _derive_library_units(plan_tracker_text, project_id, plugin_home=None):
    """Derive module flow units from a library plan-tracker.

    Libraries have public API modules. Looks for ``lib.module.<name>`` /
    ``lib.api-surface.<name>`` dotted ids or prose like "module: auth",
    "the auth module". Returns ``module`` (or the registry default) units.
    """
    text = _normalize_text(plan_tracker_text)
    keywords = _resolve_unit_keywords("library", plugin_home) or ["module", "api-surface"]
    default_type = _resolve_default_unit_type("library", plugin_home) or "module"

    names = _find_dotted_unit_names(text, keywords)
    if not names:
        names = _find_keyword_names(text, keywords)
    return _build_units_from_names(project_id, default_type, names, "library")


def _derive_web_app_units(plan_tracker_text, project_id, project_type="web-app",
                          plugin_home=None):
    """Derive story/screen/module flow units from a web/mobile plan-tracker.

    Looks for ``app.story.<name>`` dotted ids or prose like "story: login",
    "the login story", "screen: dashboard". Returns ``story`` (or the registry
    default) units. Shared by web-app and mobile-app.
    """
    text = _normalize_text(plan_tracker_text)
    keywords = (
        _resolve_unit_keywords(project_type, plugin_home)
        or ["story", "module", "screen"]
    )
    default_type = (
        _resolve_default_unit_type(project_type, plugin_home) or "story"
    )

    names = _find_dotted_unit_names(text, keywords)
    if not names:
        names = _find_keyword_names(text, keywords)
    return _build_units_from_names(project_id, default_type, names, project_type)


def _derive_mobile_app_units(plan_tracker_text, project_id, plugin_home=None):
    """Derive story/screen flow units from a mobile-app plan-tracker."""
    return _derive_web_app_units(
        plan_tracker_text, project_id, project_type="mobile-app",
        plugin_home=plugin_home,
    )


def _derive_ai_agent_plugin_units(plan_tracker_text, project_id, plugin_home=None):
    """Derive adapter/skill/manifest flow units from an ai-agent-plugin tracker.

    Looks for ``plugin.adapter.<name>``, ``plugin.skill.<name>``,
    ``plugin.manifest.<name>`` dotted ids or prose like "the auth adapter",
    "skill: code-review". Each detected unit is typed by the keyword that
    matched it (adapter/skill/manifest), so a plugin with both an adapter and
    a skill produces units of two different unit_types.
    """
    text = _normalize_text(plan_tracker_text)
    keywords = (
        _resolve_unit_keywords("ai-agent-plugin", plugin_home)
        or ["adapter", "skill", "manifest"]
    )

    units = []
    # For this project type we iterate keyword-by-keyword so each unit's
    # unit_type reflects the keyword that found it (adapter vs skill vs
    # manifest), rather than collapsing all to a single default type. Within
    # each keyword we prefer structured dotted ids and only fall back to
    # keyword-prose when the dotted form found nothing — this avoids
    # re-extracting a trailing word from a dotted name (e.g. for
    # "plugin.skill.code-review" + "code review skill" prose, the dotted
    # "code-review" wins and we don't ALSO emit a spurious "review").
    for kw in keywords:
        names = _find_dotted_unit_names(text, [kw])
        if not names:
            names = _find_keyword_names(text, [kw])
        units.extend(_build_units_from_names(project_id, kw, names, "ai-agent-plugin"))
    # Dedupe by flow_unit_id (a name could theoretically be found under two
    # keywords); preserve first occurrence.
    seen = set()
    deduped = []
    for u in units:
        fuid = u["flow_unit_id"]
        if fuid not in seen:
            seen.add(fuid)
            deduped.append(u)
    return deduped


def _derive_internal_script_units(project_id, plugin_home=None):
    """An internal-script is always a single whole unit.

    Returns exactly one ``{project_id}.whole`` unit of ``unit_type: "script"``.
    There is nothing to decompose.
    """
    return [
        _make_unit(
            project_id,
            "script",
            "whole",
            title="{pid} (whole script)".format(pid=project_id),
            project_type="internal-script",
            derivation_reason="internal-script-is-single-unit",
        )
    ]


def _internal_script_handler(plan_tracker_text, project_id, plugin_home=None):
    """Dispatcher adapter for internal-script (ignores plan-tracker text).

    internal-script is a single unit by definition, so the plan-tracker text
    is irrelevant. This wrapper exists so all handlers in :data:`_HANDLERS`
    share the uniform ``(text, project_id, plugin_home)`` signature.
    """
    return _derive_internal_script_units(project_id, plugin_home)


# ─── Dispatcher ────────────────────────────────────────────────────────────

# Maps project_type → handler. Handlers all share the signature
# (plan_tracker_text, project_id, plugin_home=None) -> list[dict].
# internal-script ignores plan_tracker_text (single unit by definition).
_HANDLERS = {
    "game": _derive_game_units,
    "cli-tool": _derive_cli_tool_units,
    "library": _derive_library_units,
    "web-app": _derive_web_app_units,
    "mobile-app": _derive_mobile_app_units,
    "ai-agent-plugin": _derive_ai_agent_plugin_units,
    "internal-script": _internal_script_handler,
}


# ═══════════════════════════════════════════════════════════════════════════
# Main entry point
# ═══════════════════════════════════════════════════════════════════════════


def _read_plan_tracker(target_root):
    """Best-effort read of ``<target_root>/.governance/plan-tracker.md``.

    Returns the file text, or ``""`` if the file is missing/unreadable. Never
    raises (fail-closed: missing tracker → empty text → fallback unit).
    """
    try:
        pt = Path(str(target_root)) / ".governance" / "plan-tracker.md"
    except Exception:  # pragma: no cover - defensive
        return ""
    try:
        return pt.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def derive_flow_units(target_root, project_type, plan_tracker_text=None,
                      plugin_home=None):
    """Derive flow units from a target project's plan-tracker.

    Closes the VAL-006 gap (ADR §7.4): for each project type, reads the target
    project's plan-tracker and derives flow units (chapters / commands /
    modules / stories / etc.) instead of relying solely on the ``python_game``
    example baked into the registry.

    Args:
        target_root: Path to the target project root. Used (a) to derive the
            ``project_id`` (the sanitized directory basename) and (b) to read
            the plan-tracker when ``plan_tracker_text`` is None.
        project_type: One of
            ``game|web-app|mobile-app|library|cli-tool|ai-agent-plugin|internal-script``.
            An unrecognized type yields the safe single-unit fallback.
        plan_tracker_text: Optional pre-loaded plan-tracker text. If ``None``,
            the text is read from ``<target_root>/.governance/plan-tracker.md``
            (missing file → empty text → fallback unit).
        plugin_home: Optional override for locating
            ``lifecycle-registry.json``. Mainly for tests.

    Returns:
        list of flow-unit dicts, each conforming to
        ``flow_unit_schema.required_fields`` with a DORMANT ``loop_state``.
        Always returns at least 1 unit — if nothing decomposable is found, a
        single ``{project_id}.whole`` fallback unit is returned with
        ``derivation_reason: "no-decomposable-structure-found"``.

    Never raises: registry / file read errors are swallowed (fail-closed) and
    yield the fallback unit.
    """
    project_id = _derive_project_id(target_root)

    # Load plan-tracker text if not supplied.
    if plan_tracker_text is None:
        plan_tracker_text = _read_plan_tracker(target_root)
    text = _normalize_text(plan_tracker_text)

    # Unknown project type → safe fallback (never raises, always 1 unit).
    if not isinstance(project_type, str) or project_type not in _HANDLERS:
        return [_fallback_single_unit(project_id, project_type)]

    handler = _HANDLERS[project_type]
    try:
        units = handler(text, project_id, plugin_home)
    except Exception:  # pragma: no cover - defensive: handlers must not raise
        units = []

    # Always return at least one unit.
    if not units:
        return [_fallback_single_unit(project_id, project_type)]
    return units


if __name__ == "__main__":  # pragma: no cover - manual CLI smoke
    import argparse

    parser = argparse.ArgumentParser(
        description="Derive flow units from a target project's plan-tracker."
    )
    parser.add_argument("target_root", help="Path to the target project root.")
    parser.add_argument(
        "project_type",
        choices=sorted(list(_HANDLERS.keys())),
        help="Project type.",
    )
    parser.add_argument(
        "--plugin-home",
        default=None,
        help="Optional override for locating lifecycle-registry.json.",
    )
    args = parser.parse_args()
    result = derive_flow_units(
        args.target_root, args.project_type, plugin_home=args.plugin_home
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
