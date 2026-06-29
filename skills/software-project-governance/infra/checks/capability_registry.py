"""Capability-registry domain checks — extracted from verify_workflow.py in 0.61.0.

Scope (DEC-083 Phase 2 / REQ-103): capability-registry.json schema validation
(FIX-116). Same registry-schema-check pattern as the manifest domain
(Phase 1). Shared helpers (_is_valid_string_list,
_line_has_scoped_claim_negation, _display_path, ROOT) are reached through a
deferred module reference (the _vw() helper, same pattern as manifest.py) so
that verify_workflow.py can import this module at load time without an import
cycle. _manifest_artifact_entries is imported directly from the sibling
checks.manifest module (Phase 1) since it is a cross-domain registry helper.

See docs/requirements/verify-workflow-split-phase2-capability-registry-0.61.0.md
for the design and the line-number baseline used during extraction.
"""

import sys
import json

# NOTE: _manifest_artifact_entries is imported lazily inside the check function
# (see check_capability_registry) rather than at module top level. The top-level
# import was rejected during 0.61.0 because it triggered a circular import
# (verify_workflow -> checks.capability_registry -> checks.manifest, while
# verify_workflow was still initializing). Deferring it to call time breaks the
# cycle, matching the _vw() deferred-access pattern already used here.


# ── Shared-helper access (deferred to avoid import cycle) ──────────
_VW_CACHE = None


def _vw():
    """Return the verify_workflow module (imported lazily, cached).

    Cached so repeated calls reuse the same module reference (REVIEW-FIX-153 P2,
    same pattern as checks.manifest).
    """
    global _VW_CACHE
    if _VW_CACHE is None:
        import verify_workflow  # noqa: WPS433 (deferred import on purpose)
        _VW_CACHE = verify_workflow
    return _VW_CACHE


def _is_valid_string_list(value):
    return _vw()._is_valid_string_list(value)


def _line_has_scoped_claim_negation(line, phrase):
    return _vw()._line_has_scoped_claim_negation(line, phrase)


def _display_path(path, root=None):
    return _vw()._display_path(path, root)


def _root():
    return _vw().ROOT


def _manifest_artifact_entries(manifest):
    """Lazy access to the cross-domain registry helper in checks.manifest."""
    from checks.manifest import _manifest_artifact_entries as _fn  # noqa: WPS433
    return _fn(manifest)


# ── Domain-specific constants (migrated from verify_workflow.py) ───
# All seven constants are capability-registry-only (verified by Explore survey
# of 0.59.0 baseline). CAPABILITY_REGISTRY_PATH was a dead constant (defined,
# never referenced) in verify_workflow.py; kept here as a plain string for
# registry-constant-cluster completeness — NOT a Path, so it never touches
# verify_workflow at import time (REQ-103 D1).
CAPABILITY_REGISTRY_PATH = "skills/software-project-governance/core/capability-registry.json"

CAPABILITY_REGISTRY_ALLOWED_KINDS = {
    "plugin",
    "skill",
    "tool",
    "mcp",
    "browser",
    "sub_agent",
    "script",
    "fallback",
}
CAPABILITY_REGISTRY_ALLOWED_STATUSES = {
    "AVAILABLE",
    "BLOCKED",
    "DEGRADED",
    "NOT_SUPPORTED",
    "NOT_FOUND",
    "RESEARCH_ONLY",
}
CAPABILITY_REGISTRY_REQUIRED_FIELDS = [
    "capability_id",
    "kind",
    "host_surface",
    "scenarios",
    "status",
    "source_facts",
    "validation_command",
    "side_effect_boundary",
    "no_overclaim_boundary",
]
CAPABILITY_REGISTRY_REQUIRED_KINDS = {
    "plugin",
    "skill",
    "tool",
    "mcp",
    "browser",
    "sub_agent",
    "script",
    "fallback",
}
CAPABILITY_REGISTRY_BOUNDARY_TOKENS = [
    "Catalog entry does not mean runtime PASS.",
    "Catalog entry does not mean external capability available.",
    "Governance packs are internal capability modules, not external plugins, skills, tools, MCP servers, browser tools, sub-agents, scripts, or fallbacks.",
    "Do not claim automatic best-tool selection.",
    "Do not claim universal plugin/skill/tool availability.",
    "Do not claim official approval.",
    "Do not claim marketplace approval.",
    "Do not claim 1.0.0 production-ready.",
]
CAPABILITY_REGISTRY_FORBIDDEN_OVERCLAIMS = [
    "catalog entry means runtime pass",
    "catalog entry is runtime pass",
    "catalog entry means external capability available",
    "catalog entry is external capability available",
    "external capability available by catalog",
    "governance pack is external capability",
    "governance packs are external capabilities",
    "governance pack plugin",
    "governance pack tool",
    "governance pack mcp",
    "automatic best-tool selection",
    "automatically selects the best tool",
    "universal plugin availability",
    "universal skill availability",
    "universal tool availability",
    "officially approved",
    "official approval granted",
    "marketplace approved",
    "marketplace approval granted",
    "1.0.0 production-ready",
]


# ── Domain-specific helper (registry-only) ─────────────────────────

def _capability_registry_text_values(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _capability_registry_text_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _capability_registry_text_values(item)


# ── Core check function ────────────────────────────────────────────

def check_capability_registry(root=None):
    """FIX-116: external capability registry must be factual and no-overclaim safe."""
    root = root or _root()
    registry_path = root / "skills/software-project-governance/core/capability-registry.json"
    manifest_path = root / "skills/software-project-governance/core/manifest.json"
    failures = []
    display = _display_path(registry_path, root)
    if not registry_path.exists():
        return [f"{display}: missing capability registry"]

    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{display}: invalid JSON: {exc}"]

    if registry.get("workflow") != "software-project-governance":
        failures.append(f"{display}: workflow must be software-project-governance")
    if registry.get("source_of_truth") is not True:
        failures.append(f"{display}: source_of_truth must be true")
    if registry.get("registry_mode") != "registry-first-no-physical-plugin-split":
        failures.append(f"{display}: registry_mode must be registry-first-no-physical-plugin-split")

    allowed_kinds = registry.get("allowed_kinds")
    if set(allowed_kinds or []) != CAPABILITY_REGISTRY_ALLOWED_KINDS:
        failures.append(f"{display}: allowed_kinds must be {sorted(CAPABILITY_REGISTRY_ALLOWED_KINDS)}")
    allowed_statuses = registry.get("allowed_statuses")
    if set(allowed_statuses or []) != CAPABILITY_REGISTRY_ALLOWED_STATUSES:
        failures.append(f"{display}: allowed_statuses must be {sorted(CAPABILITY_REGISTRY_ALLOWED_STATUSES)}")

    boundary = registry.get("no_overclaim_boundary", [])
    if not _is_valid_string_list(boundary):
        failures.append(f"{display}: no_overclaim_boundary must be a non-empty string list")
        boundary = []
    for token in CAPABILITY_REGISTRY_BOUNDARY_TOKENS:
        if token not in boundary:
            failures.append(f"{display}: missing no-overclaim boundary token `{token}`")

    if not manifest_path.exists():
        failures.append(f"{display}: core/manifest.json is required to make the capability registry a canonical product artifact")
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            artifact_entries = _manifest_artifact_entries(manifest)
            registry_artifacts = [
                entry for entry in artifact_entries
                if isinstance(entry, dict)
                and entry.get("id") == "capability-registry"
                and entry.get("path") == "skills/software-project-governance/core/capability-registry.json"
            ]
            if not registry_artifacts:
                failures.append(
                    f"{display}: core/manifest.json must declare capability-registry as a canonical product artifact"
                )
        except json.JSONDecodeError as exc:
            failures.append(f"{_display_path(manifest_path, root)}: invalid JSON: {exc}")

    capabilities = registry.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        return failures + [f"{display}: capabilities must be a non-empty list"]

    seen_ids = []
    seen_kinds = set()
    for capability in capabilities:
        if not isinstance(capability, dict):
            failures.append(f"{display}: each capability must be an object")
            continue
        capability_id = capability.get("capability_id", "<missing>")
        seen_ids.append(capability_id)
        label = f"{display}: capability {capability_id}"

        for field in CAPABILITY_REGISTRY_REQUIRED_FIELDS:
            if field not in capability:
                failures.append(f"{label}: missing required field `{field}`")

        kind = capability.get("kind")
        seen_kinds.add(kind)
        if kind not in CAPABILITY_REGISTRY_ALLOWED_KINDS:
            failures.append(f"{label}: unknown kind `{kind}`")

        status = capability.get("status")
        if status not in CAPABILITY_REGISTRY_ALLOWED_STATUSES:
            failures.append(f"{label}: unknown status `{status}`")

        for field in ("capability_id", "host_surface", "validation_command", "side_effect_boundary"):
            if not isinstance(capability.get(field), str) or not capability.get(field, "").strip():
                failures.append(f"{label}: `{field}` must be a non-empty string")

        for field in ("scenarios", "source_facts", "no_overclaim_boundary"):
            if not _is_valid_string_list(capability.get(field)):
                failures.append(f"{label}: `{field}` must be a non-empty string list")

        command = capability.get("validation_command", "")
        if isinstance(command, str) and command.strip():
            if "verify_workflow.py" not in command:
                failures.append(f"{label}: validation_command must use verify_workflow.py")
            if "check-capability-registry" not in command and kind in {"mcp", "script"}:
                failures.append(f"{label}: validation_command for {kind} must include check-capability-registry")
        boundary_text = " ".join(capability.get("no_overclaim_boundary", []))
        if "Catalog entry" not in boundary_text and "not" not in boundary_text.lower() and "Do not" not in boundary_text:
            failures.append(f"{label}: no_overclaim_boundary must explicitly prevent overclaim")

        capability_text = " ".join(_capability_registry_text_values(capability)).lower()
        if kind == "fallback" and "governance pack" in capability_text and status == "AVAILABLE":
            failures.append(f"{label}: fallback capability must not use governance pack catalog as external availability")

    missing_kinds = sorted(CAPABILITY_REGISTRY_REQUIRED_KINDS - seen_kinds)
    if missing_kinds:
        failures.append(f"{display}: missing required kind(s): {', '.join(missing_kinds)}")
    duplicates = sorted({item for item in seen_ids if seen_ids.count(item) > 1})
    for capability_id in duplicates:
        failures.append(f"{display}: duplicate capability_id `{capability_id}`")

    text_values = list(_capability_registry_text_values(registry))
    for text in text_values:
        lowered = text.lower()
        for phrase in CAPABILITY_REGISTRY_FORBIDDEN_OVERCLAIMS:
            if phrase in lowered and not _line_has_scoped_claim_negation(text, phrase):
                failures.append(f"{display}: forbidden capability overclaim `{phrase}`")

    return failures


# ── CLI entry (REQ-103 D4) ─────────────────────────────────────────

def cmd_check_capability_registry(args):
    """Run external capability registry consistency guard."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    issues = check_capability_registry()
    print("\n=== Capability Registry Check ===")
    if issues:
        print(f"  Result: FAILED — {len(issues)} issue(s)")
        for issue in issues[:20]:
            print(f"    - {issue}")
        if len(issues) > 20:
            print(f"    ... and {len(issues) - 20} more")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
    else:
        print("  Result: PASSED — capability registry is factual and no-overclaim safe")
    print()
