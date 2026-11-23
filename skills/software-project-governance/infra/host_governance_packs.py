"""Validate governance pack definitions, boundary claims and README guidance."""

from dataclasses import dataclass
from pathlib import Path
import json


@dataclass(frozen=True)
class PackRules:
    boundary_tokens: list
    forbidden_overclaims: list
    ids: list
    known_checks: set
    profile_ids: set
    required_fields: list


@dataclass(frozen=True)
class PackReleaseBoundaries:
    release_boundary_path: str
    release_boundary_tokens: list
    status_doc_paths: list


GOVERNANCE_PACKS_PATH = Path(__file__).resolve().parents[3] / "skills/software-project-governance/core/governance-packs.json"


GOVERNANCE_PACK_IDS = [
    "governance-core",
    "quality-gates",
    "release-governance",
    "agent-team",
    "enterprise",
]


GOVERNANCE_PACK_REQUIRED_FIELDS = [
    "id",
    "title",
    "description",
    "default_profiles",
    "capabilities",
    "user_value",
    "files",
    "checks",
    "validation_commands",
    "no_overclaim_boundary",
]


GOVERNANCE_PACK_PROFILE_IDS = {"lite", "standard", "strict"}


GOVERNANCE_PACK_KNOWN_CHECKS = {
    "verify",
    "status",
    "governance-context",
    "check-governance",
    "check-manifest-consistency",
    "check-agent-adapters",
    "check-release",
    "e2e-check",
    "first-run-demo",
    "agent-runtime-e2e",
    "gemini-auth-preflight",
    "opencode-provider-preflight",
    "check-cross-references",
    "check-sequential-ids",
    "check-structural-validity",
    "check-commit-scope",
    "check-goal-alignment",
    "check-user-impact",
    "check-agent-team",
    "check-review-debt",
    "check-version-consistency",
    "check-projection-sync",
    "check-hot-fact-source",
    "check-runtime-readiness-matrix",
    "check-first-session-measurement",
    "check-product-success-contracts",
    "check-acceptance-contracts",
    "check-quality-budget",
    "check-vertical-slices",
    "check-deterministic-scaffolds",
    "check-scaffold-templates",
    "check-interruption-policy",
    "check-user-interruption-policy",
    "generate-deterministic-scaffold",
    "check-locks",
    "check-archive-integrity",
    "check-governance-packs",
    "check-readme-pack-guidance",
    "check-governance-pack-status",
    "check-capability-registry",
    "check-lifecycle-registry",
    "check-flow-unit-runtime",
    "check-loop-health",
    "check-host-capability-context",
    "check-mainstream-agent-loading",
}


GOVERNANCE_PACK_STATUS_DOC_PATHS = [
    "commands/governance-status.md",
    # FEAT-038 (AUDIT-154 A-7): the `/governance` Delivery Trust Snapshot /
    # pack doc-surface contract moved from the router layer into the on-demand
    # Scenario F document; the router layer keeps a pointer, so the
    # pack-status token guard follows the owning document on both faces.
    "commands/governance/scenario-f.md",
    "project/e2e-test-project/commands/governance-status.md",
    "project/e2e-test-project/commands/governance/scenario-f.md",
]


GOVERNANCE_PACK_STATUS_BOUNDARY_TOKENS = [
    "pack membership",
    "pack enabled",
    "task evidence",
    "independent review",
    "quality gates",
    "release gates",
    "official approval",
    "marketplace approval",
    "universal/full runtime support",
    "1.0.0 production-ready",
]


GOVERNANCE_PACK_RELEASE_BOUNDARY_PATH = "docs/requirements/composable-governance-packs-0.44.0.md"


GOVERNANCE_PACK_RELEASE_BOUNDARY_TOKENS = [
    "Pack boundary/no-overclaim detail",
    "Pack membership is not task evidence.",
    "`pack enabled` does not mean task evidence exists.",
    "`pack enabled` does not mean independent review passed.",
    "`pack enabled` does not mean quality gates passed.",
    "`pack enabled` does not mean release gates passed.",
    "`pack enabled` does not mean official approval was granted.",
    "`pack enabled` does not mean marketplace approval was granted.",
    "`pack enabled` does not mean universal/full runtime support is verified.",
    "`pack enabled` does not mean 1.0.0 production-ready.",
]


GOVERNANCE_PACK_STATUS_FORBIDDEN_OVERCLAIMS = [
    "pack enabled means task evidence exists",
    "pack enabled means independent review passed",
    "pack enabled means quality gates passed",
    "pack enabled means release gates passed",
    "pack enabled means official approval",
    "pack enabled means marketplace approval",
    "pack enabled means universal runtime support",
    "pack enabled means full runtime support",
    "pack enabled means 1.0.0 production-ready",
    "pack membership means task evidence exists",
    "pack membership means independent review passed",
    "pack membership means quality gates passed",
    "pack membership means release gates passed",
    "pack membership means official approval",
    "pack membership means marketplace approval",
    "pack membership means universal runtime support",
    "pack membership means full runtime support",
    "pack membership means 1.0.0 production-ready",
    "pack membership is completion evidence",
    "pack membership is task evidence",
    "pack enabled is task evidence",
]


GOVERNANCE_PACK_BOUNDARY_TOKENS = [
    "No official approval",
    "No marketplace approval",
    "No universal or full runtime support",
    "RISK-036 remains open",
]


GOVERNANCE_PACK_FORBIDDEN_OVERCLAIMS = [
    "officially approved",
    "official approval granted",
    "marketplace approved",
    "marketplace approval granted",
    "universal runtime support is verified",
    "full runtime support is verified",
    "1.0.0 production-ready",
    "pack enabled means release passed",
    "pack enabled means governance review passed",
]


README_PACK_GUIDANCE_REQUIRED_TOKENS = [
    "Packs are capability modules; profiles are governance intensity presets.",
    "Profiles stay `lite` / `standard` / `strict`",
    "registry-first",
    "no physical split",
    "`governance-core`",
    "`quality-gates`",
    "`release-governance`",
    "`agent-team`",
    "`enterprise`",
    "Pack membership is not completion evidence.",
    "`pack enabled` does not mean task evidence exists",
    "independent review passed",
    "quality gates passed",
    "release gates passed",
    "official approval was granted",
    "marketplace approval was granted",
    "universal/full runtime support is verified",
    "Pack 是能力模块，profile 是治理强度预设",
    "profile 仍然只有 `lite` / `standard` / `strict`",
    "Pack 归属不是完成证据",
    "`pack enabled` 不等于任务证据存在",
]


def _governance_pack_text_values(value, *, governance_pack_text_values):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from governance_pack_text_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from governance_pack_text_values(item)


def _governance_pack_file_path(entry):
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        return entry.get("path")
    return None


def check_governance_packs(
        root, *, package_root, display_path, governance_pack_file_path, governance_pack_text_values,
        line_has_scoped_claim_negation, manifest_artifact_entries, packs_rules,
):
    """FIX-108: canonical governance pack registry must be factual and checkable."""
    root = root or package_root
    registry_path = root / "skills/software-project-governance/core/governance-packs.json"
    manifest_path = root / "skills/software-project-governance/core/manifest.json"
    failures = []
    display = display_path(registry_path, root)
    if not registry_path.exists():
        return [f"{display}: missing governance pack registry"]

    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{display}: invalid JSON: {exc}"]

    if registry.get("workflow") != "software-project-governance":
        failures.append(f"{display}: workflow must be software-project-governance")
    if registry.get("source_of_truth") is not True:
        failures.append(f"{display}: source_of_truth must be true")
    if registry.get("pack_mode") != "registry-first-no-physical-split":
        failures.append(f"{display}: pack_mode must be registry-first-no-physical-split")

    if not manifest_path.exists():
        failures.append(f"{display}: core/manifest.json is required to make the pack registry a canonical product artifact")
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            artifact_entries = manifest_artifact_entries(manifest)
            registry_artifacts = [
                entry for entry in artifact_entries
                if entry.get("id") == "governance-pack-registry"
                and entry.get("path") == "skills/software-project-governance/core/governance-packs.json"
            ]
            if not registry_artifacts:
                failures.append(
                    f"{display}: core/manifest.json must declare governance-pack-registry as a canonical product artifact"
                )
        except json.JSONDecodeError as exc:
            failures.append(f"{display_path(manifest_path, root)}: invalid JSON: {exc}")

    for token in packs_rules.boundary_tokens:
        if token not in registry.get("no_overclaim_boundary", []):
            failures.append(f"{display}: missing no-overclaim boundary token `{token}`")

    required_pack_ids = registry.get("required_pack_ids")
    if required_pack_ids != packs_rules.ids:
        failures.append(f"{display}: required_pack_ids must be {packs_rules.ids}")

    packs = registry.get("packs")
    if not isinstance(packs, list) or not packs:
        return failures + [f"{display}: packs must be a non-empty list"]

    seen_ids = []
    for pack in packs:
        if not isinstance(pack, dict):
            failures.append(f"{display}: each pack must be an object")
            continue
        pack_id = pack.get("id", "<missing>")
        seen_ids.append(pack_id)
        pack_label = f"{display}: pack {pack_id}"

        for field in packs_rules.required_fields:
            if field not in pack:
                failures.append(f"{pack_label}: missing required field `{field}`")

        if pack_id not in packs_rules.ids:
            failures.append(f"{pack_label}: unknown pack id")

        for field in ("title", "description"):
            if not isinstance(pack.get(field), str) or not pack.get(field, "").strip():
                failures.append(f"{pack_label}: `{field}` must be a non-empty string")

        profiles = pack.get("default_profiles")
        if not isinstance(profiles, list) or not profiles:
            failures.append(f"{pack_label}: default_profiles must be a non-empty list")
        else:
            invalid_profiles = [p for p in profiles if p not in packs_rules.profile_ids]
            if invalid_profiles:
                failures.append(f"{pack_label}: unknown default_profiles {invalid_profiles}")

        for field in ("capabilities", "user_value", "checks", "validation_commands", "no_overclaim_boundary"):
            value = pack.get(field)
            if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
                failures.append(f"{pack_label}: `{field}` must be a non-empty string list")

        files = pack.get("files")
        if not isinstance(files, list) or not files:
            failures.append(f"{pack_label}: files must be a non-empty list")
        else:
            for entry in files:
                rel_path = governance_pack_file_path(entry)
                if not isinstance(rel_path, str) or not rel_path.strip():
                    failures.append(f"{pack_label}: file entry must contain non-empty path")
                    continue
                target = root / rel_path
                if not target.exists():
                    failures.append(f"{pack_label}: referenced file `{rel_path}` does not exist")

        for check in pack.get("checks", []):
            if check not in packs_rules.known_checks:
                failures.append(f"{pack_label}: unknown referenced check `{check}`")

        commands = pack.get("validation_commands", [])
        for command in commands if isinstance(commands, list) else []:
            if "verify_workflow.py" not in command and not command.startswith("python -m unittest"):
                failures.append(f"{pack_label}: validation command must call verify_workflow.py or unittest: `{command}`")

        boundary = " ".join(pack.get("no_overclaim_boundary", []))
        if "does not" not in boundary.lower() and "not " not in boundary.lower():
            failures.append(f"{pack_label}: no_overclaim_boundary must explicitly deny overclaim")

    duplicates = sorted({pack_id for pack_id in seen_ids if seen_ids.count(pack_id) > 1})
    for pack_id in duplicates:
        failures.append(f"{display}: duplicate pack id `{pack_id}`")
    missing_ids = [pack_id for pack_id in packs_rules.ids if pack_id not in seen_ids]
    if missing_ids:
        failures.append(f"{display}: missing required pack id(s): {', '.join(missing_ids)}")
    unknown_ids = [pack_id for pack_id in seen_ids if pack_id not in packs_rules.ids]
    if unknown_ids:
        failures.append(f"{display}: unknown pack id(s): {', '.join(sorted(set(unknown_ids)))}")

    all_text_lines = "\n".join(governance_pack_text_values(registry)).splitlines()
    for phrase in packs_rules.forbidden_overclaims:
        if any(phrase in line.lower() and not line_has_scoped_claim_negation(line, phrase) for line in all_text_lines):
            failures.append(f"{display}: forbidden overclaim wording `{phrase}`")

    return failures


def check_readme_pack_guidance(
        root, *, package_root, governance_pack_ids, readme_pack_guidance_required_tokens, display_path,
        line_has_scoped_claim_negation,
):
    """FIX-109: README first-run guidance must map profiles to packs without overclaim."""
    root = root or package_root
    readme_path = root / "README.md"
    display = display_path(readme_path, root)
    if not readme_path.exists():
        return [f"{display}: missing README"]

    content = readme_path.read_text(encoding="utf-8")
    failures = []
    for token in readme_pack_guidance_required_tokens:
        if token not in content:
            failures.append(f"{display}: missing README pack guidance token `{token}`")

    for pack_id in governance_pack_ids:
        if f"`{pack_id}`" not in content:
            failures.append(f"{display}: missing pack id `{pack_id}` in README guidance")

    profile_rows = {
        "**lite**": ["`governance-core`"],
        "**standard**": ["`governance-core`", "`quality-gates`", "`release-governance`", "`agent-team`"],
        "**strict**": ["`governance-core`", "`quality-gates`", "`release-governance`", "`agent-team`", "`enterprise`"],
    }
    readme_lines = content.splitlines()
    for profile, pack_tokens in profile_rows.items():
        matching_lines = [
            line for line in readme_lines
            if profile in line and all(pack_token in line for pack_token in pack_tokens)
        ]
        if not matching_lines:
            failures.append(
                f"{display}: profile {profile} guidance missing pack mapping {', '.join(pack_tokens)}"
            )

    forbidden_pack_enabled_claims = [
        "pack enabled means release passed",
        "pack enabled means governance review passed",
        "pack enabled means quality gates passed",
        "pack enabled means official approval",
        "pack enabled means marketplace approval",
        "pack enabled means universal runtime support",
    ]
    lower_content = content.lower()
    for phrase in forbidden_pack_enabled_claims:
        if phrase in lower_content:
            failures.append(f"{display}: forbidden README pack overclaim `{phrase}`")

    direct_claims = [
        "officially approved",
        "official approval granted",
        "marketplace approved",
        "marketplace approval granted",
        "universal runtime support is verified",
        "full runtime support is verified",
        "1.0.0 production-ready",
    ]
    for phrase in direct_claims:
        if any(phrase in line.lower() and not line_has_scoped_claim_negation(line, phrase)
               for line in readme_lines):
            failures.append(f"{display}: forbidden README pack overclaim `{phrase}`")

    return failures


def _append_pack_overclaim_issues(
        failures, path, content, root, *, governance_pack_status_forbidden_overclaims, display_path,
        line_has_scoped_claim_negation,
):
    display = display_path(path, root)
    lines = content.splitlines()
    for phrase in governance_pack_status_forbidden_overclaims:
        for line in lines:
            if phrase in line.lower() and not line_has_scoped_claim_negation(line, phrase):
                failures.append(f"{display}: forbidden pack status overclaim `{phrase}`")
                break

    direct_claims = [
        "officially approved",
        "official approval granted",
        "marketplace approved",
        "marketplace approval granted",
        "universal runtime support is verified",
        "full runtime support is verified",
        "1.0.0 production-ready",
    ]
    for phrase in direct_claims:
        for line in lines:
            if phrase in line.lower() and not line_has_scoped_claim_negation(line, phrase):
                failures.append(f"{display}: forbidden pack status overclaim `{phrase}`")
                break


def _append_missing_status_boundary_issues(
        failures, path, content, root, *, governance_pack_status_boundary_tokens, display_path,
):
    display = display_path(path, root)
    boundary_lines = [line for line in content.splitlines() if "Pack boundary:" in line]
    if not boundary_lines:
        failures.append(f"{display}: missing status pack boundary line")
        return

    for index, line in enumerate(boundary_lines, start=1):
        lower = line.lower()
        for token in governance_pack_status_boundary_tokens:
            if token not in lower:
                failures.append(
                    f"{display}: status pack boundary line {index} missing token `{token}`"
                )


def check_governance_pack_status(
        root, *, package_root, append_missing_status_boundary_issues, append_pack_overclaim_issues,
        display_path, release,
):
    """FIX-111: status and release surfaces must disclose pack boundaries without overclaim."""
    root = root or package_root
    failures = []

    for rel_path in release.status_doc_paths:
        path = root / rel_path
        display = display_path(path, root)
        if not path.exists():
            failures.append(f"{display}: missing pack-aware status contract")
            continue
        content = path.read_text(encoding="utf-8")
        if "Pack boundary:" in content:
            append_missing_status_boundary_issues(failures, path, content, root)
        append_pack_overclaim_issues(failures, path, content, root)

    release_path = root / release.release_boundary_path
    release_display = display_path(release_path, root)
    if not release_path.exists():
        failures.append(f"{release_display}: missing release pack boundary document")
    else:
        release_content = release_path.read_text(encoding="utf-8")
        for token in release.release_boundary_tokens:
            if token not in release_content:
                failures.append(f"{release_display}: missing release pack boundary token `{token}`")
        append_pack_overclaim_issues(failures, release_path, release_content, root)

    return failures
