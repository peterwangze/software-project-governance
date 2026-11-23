"""Validate host adapter manifests and evidence underlying runtime capability claims."""

from dataclasses import dataclass
import shutil


@dataclass(frozen=True)
class CapabilityRules:
    policy: dict
    keys: tuple
    statuses: set


MAINSTREAM_AGENT_ADAPTERS = ["claude", "codex", "gemini", "opencode", "dsh", "pi"]


ADAPTER_REQUIRED_KEYS = [
    "adapter_id",
    "workflow_id",
    "entry_type",
    "support_status",
    "supported_runtime",
    "trigger",
    "inputs",
    "outputs",
    "gate_behavior",
    "validation",
    "native_entry",
    "runtime_e2e",
    "runtime_capabilities",
    "launcher",
]


def _validate_runtime_e2e_block(
        root, manifest_path, runtime_e2e, field_name, allow_unsupported, *, display_path,
):
    """Validate FIX-074 explicit E2E status blocks in adapter manifests."""
    block = runtime_e2e.get(field_name)
    if not isinstance(block, dict):
        return [f"{display_path(manifest_path, root)}: runtime_e2e.{field_name} must be an object"]

    allowed_statuses = {"passed", "blocked"}
    if allow_unsupported:
        allowed_statuses.add("unsupported")

    status = block.get("status")
    failures = []
    if status not in allowed_statuses:
        failures.append(
            f"{display_path(manifest_path, root)}: runtime_e2e.{field_name}.status must be one of {sorted(allowed_statuses)}"
        )
    if not block.get("evidence"):
        failures.append(f"{display_path(manifest_path, root)}: runtime_e2e.{field_name}.evidence required")
    if status == "passed" and (not block.get("command") or not block.get("verified_on")):
        failures.append(
            f"{display_path(manifest_path, root)}: passed runtime_e2e.{field_name} requires command and verified_on"
        )
    if status == "blocked" and not block.get("blocked_reason"):
        failures.append(f"{display_path(manifest_path, root)}: blocked runtime_e2e.{field_name} requires blocked_reason")
    return failures


RUNTIME_CAPABILITY_KEYS = (
    "ask_user_question",
    "sub_agent",
    "tool_calling",
    "browser",
    "mcp",
    "git_hooks",
)


RUNTIME_CAPABILITY_STATUSES = {"native", "degraded", "unsupported"}


ADAPTER_RUNTIME_CAPABILITY_POLICY = {
    "claude": {
        "ask_user_question": {"degraded"},
        "sub_agent": {"native"},
        "tool_calling": {"native"},
        "browser": {"degraded"},
        "mcp": {"degraded"},
        "git_hooks": {"native"},
    },
    "codex": {
        "ask_user_question": {"degraded"},
        "sub_agent": {"degraded"},
        "tool_calling": {"degraded"},
        "browser": {"degraded"},
        "mcp": {"degraded"},
        "git_hooks": {"native"},
    },
    "gemini": {
        "ask_user_question": {"unsupported"},
        "sub_agent": {"unsupported"},
        "tool_calling": {"degraded"},
        "browser": {"unsupported"},
        "mcp": {"degraded"},
        "git_hooks": {"native"},
    },
    "opencode": {
        "ask_user_question": {"unsupported"},
        "sub_agent": {"unsupported"},
        "tool_calling": {"degraded"},
        "browser": {"unsupported"},
        "mcp": {"degraded"},
        "git_hooks": {"native"},
    },
    "dsh": {
        "ask_user_question": {"native"},
        "sub_agent": {"native"},
        "tool_calling": {"native"},
        "browser": {"degraded"},
        "mcp": {"degraded"},
        "git_hooks": {"native"},
    },
    "pi": {
        # DEC-359 upgrade (EVD-1715/1716): extension-bridged ask_user_question
        # and dispatch_agent passed runtime E2E — native with bridged evidence;
        # headless GOV_ASK_USER_HEADLESS is bounded behavior, not a gap.
        "ask_user_question": {"native"},
        "sub_agent": {"native"},
        "tool_calling": {"native"},
        "browser": {"unsupported"},
        "mcp": {"degraded"},
        "git_hooks": {"native"},
    },
}


def _validate_runtime_capabilities(root, manifest_path, manifest, *, display_path, capabilities_rules):
    """FIX-082: adapters must declare real host capabilities and degraded modes."""
    display = display_path(manifest_path, root)
    capabilities = manifest.get("runtime_capabilities")
    if not isinstance(capabilities, dict):
        return [f"{display}: runtime_capabilities must be an object"]

    failures = []
    adapter_id = manifest.get("adapter_id")
    capability_policy = capabilities_rules.policy.get(adapter_id, {})
    for key in capabilities_rules.keys:
        block = capabilities.get(key)
        if not isinstance(block, dict):
            failures.append(f"{display}: runtime_capabilities.{key} must be an object")
            continue
        status = block.get("status")
        if status not in capabilities_rules.statuses:
            failures.append(
                f"{display}: runtime_capabilities.{key}.status must be one of {sorted(capabilities_rules.statuses)}"
            )
        allowed_statuses = capability_policy.get(key)
        if allowed_statuses and status not in allowed_statuses:
            failures.append(
                f"{display}: runtime_capabilities.{key}.status={status} overclaims adapter policy; "
                f"allowed={sorted(allowed_statuses)}"
            )
        if not block.get("evidence"):
            failures.append(f"{display}: runtime_capabilities.{key}.evidence required")
        if status in {"degraded", "unsupported"} and not block.get("degraded_mode"):
            failures.append(f"{display}: runtime_capabilities.{key}.degraded_mode required when status is {status}")

    closure = capabilities.get("workflow_closure")
    if not isinstance(closure, dict):
        failures.append(f"{display}: runtime_capabilities.workflow_closure must be an object")
        return failures

    closure_status = closure.get("status")
    if closure_status not in {"full", "degraded", "blocked"}:
        failures.append(f"{display}: runtime_capabilities.workflow_closure.status must be full, degraded, or blocked")
    if not closure.get("evidence"):
        failures.append(f"{display}: runtime_capabilities.workflow_closure.evidence required")
    degraded_capabilities = closure.get("degraded_capabilities")
    non_native = [
        key for key in capabilities_rules.keys
        if isinstance(capabilities.get(key), dict)
        and capabilities[key].get("status") in {"degraded", "unsupported"}
    ]
    if non_native:
        if closure_status == "full":
            failures.append(f"{display}: workflow_closure.status=full conflicts with degraded/unsupported capabilities")
        if not isinstance(degraded_capabilities, list):
            failures.append(f"{display}: workflow_closure.degraded_capabilities must list non-native capabilities")
        else:
            missing = [key for key in non_native if key not in degraded_capabilities]
            if missing:
                failures.append(
                    f"{display}: workflow_closure.degraded_capabilities missing {', '.join(missing)}"
                )
    elif closure_status != "full":
        failures.append(f"{display}: workflow_closure.status must be full when all capabilities are native")

    runtime_e2e = manifest.get("runtime_e2e")
    if isinstance(runtime_e2e, dict) and runtime_e2e.get("full_e2e_verified") is False and closure_status == "full":
        failures.append(f"{display}: workflow_closure.status=full requires full_e2e_verified=true or explicit degraded closure")
    return failures


def _validate_codex_runtime_e2e_claim(root, manifest_path, runtime_e2e, *, display_path):
    """FIX-077: Codex full E2E must be real headless codex exec target-cwd evidence."""
    agent_block = runtime_e2e.get("agent_runtime_e2e", {})
    if not isinstance(agent_block, dict):
        return []

    status = agent_block.get("status")
    full_e2e_verified = runtime_e2e.get("full_e2e_verified")
    claim_text = " ".join(
        str(value or "")
        for value in (
            agent_block.get("command"),
            agent_block.get("evidence"),
            agent_block.get("blocked_reason"),
        )
    ).lower()
    app_session_markers = (
        "codex app",
        "current session",
        "current workflow session",
        "timeout attempted separately",
        "attempted separately and timed out",
    )
    blocked_markers = (
        "timed out",
        "timeout",
        "blocked",
        "blocker",
    )
    target_cwd_markers = (
        " -c ",
        "\n-c ",
        "\t-c ",
        "target-cwd",
        "target cwd",
        "cwd",
    )
    headless_markers = (
        "--ephemeral",
        "read-only",
        "read only",
        "headless",
    )
    failures = []
    display = display_path(manifest_path, root)
    if status == "passed":
        if "codex exec" not in claim_text:
            failures.append(
                f"{display}: Codex agent_runtime_e2e.status=passed requires real codex exec evidence"
            )
        if not any(marker in claim_text for marker in target_cwd_markers):
            failures.append(
                f"{display}: Codex agent_runtime_e2e.status=passed requires target-cwd evidence"
            )
        if not any(marker in claim_text for marker in headless_markers):
            failures.append(
                f"{display}: Codex agent_runtime_e2e.status=passed requires headless/read-only/ephemeral evidence"
            )
        if any(marker in claim_text for marker in app_session_markers):
            failures.append(
                f"{display}: Codex agent_runtime_e2e.status=passed must be real codex exec target-cwd evidence, not Codex App/current session or separately timed-out CLI evidence"
            )
        observed = " ".join(str(agent_block.get(key) or "") for key in ("evidence", "blocked_reason")).lower()
        if any(marker in observed for marker in blocked_markers):
            failures.append(
                f"{display}: Codex agent_runtime_e2e.status=passed must not include timeout/blocked evidence"
            )
    if status == "blocked" and full_e2e_verified is not False:
        failures.append(
            f"{display}: Codex blocked agent_runtime_e2e requires full_e2e_verified=false"
        )
    return failures


def _validate_gemini_auth_preflight_claim(root, manifest_path, runtime_e2e, *, display_path):
    display = display_path(manifest_path, root)
    preflight = runtime_e2e.get("auth_preflight")
    if not isinstance(preflight, dict):
        return [f"{display}: Gemini runtime_e2e.auth_preflight must be an object"]

    failures = []
    status = preflight.get("status")
    if status not in {"passed", "blocked"}:
        failures.append(f"{display}: Gemini runtime_e2e.auth_preflight.status must be passed or blocked")
    if "gemini-auth-preflight" not in str(preflight.get("command", "")):
        failures.append(f"{display}: Gemini auth_preflight.command must reference gemini-auth-preflight")
    if not preflight.get("verified_on"):
        failures.append(f"{display}: Gemini auth_preflight.verified_on required")
    guidance_text = " ".join(
        str(value or "")
        for value in (
            preflight.get("blocked_reason"),
            preflight.get("remediation"),
            runtime_e2e.get("agent_runtime_e2e", {}).get("blocked_reason")
            if isinstance(runtime_e2e.get("agent_runtime_e2e"), dict) else "",
        )
    ).lower()
    required_guidance = ("gemini_api_key", "google_api_key", "vertex", "gca", "settings")
    missing = [marker for marker in required_guidance if marker not in guidance_text]
    if missing:
        failures.append(
            f"{display}: Gemini blocked guidance must mention GEMINI_API_KEY / GOOGLE_API_KEY / Vertex / GCA / settings auth"
        )
    if status == "blocked":
        if preflight.get("blocked_reason") != "Gemini auth missing or not configured":
            failures.append(f"{display}: Gemini blocked auth_preflight requires exact auth missing blocked_reason")
        agent_e2e = runtime_e2e.get("agent_runtime_e2e")
        agent_runtime_passed = isinstance(agent_e2e, dict) and agent_e2e.get("status") == "passed"
        if runtime_e2e.get("full_e2e_verified") is not False and not agent_runtime_passed:
            failures.append(f"{display}: Gemini blocked auth_preflight requires full_e2e_verified=false")
        if agent_runtime_passed:
            evidence_text = " ".join(
                str(value or "")
                for value in (
                    preflight.get("evidence"),
                    agent_e2e.get("command"),
                    agent_e2e.get("evidence"),
                )
            ).lower()
            if "gemini_cli_trust_workspace" not in evidence_text or "secret" not in evidence_text:
                failures.append(
                    f"{display}: Gemini blocked auth_preflight with passed runtime E2E must document workspace trust and secret-safe boundary"
                )
    return failures


def _validate_opencode_provider_model_preflight_claim(
        root, manifest_path, runtime_e2e, *, opencode_legal_deepseek_models, display_path,
):
    display = display_path(manifest_path, root)
    preflight = runtime_e2e.get("provider_model_preflight")
    if not isinstance(preflight, dict):
        return [f"{display}: opencode runtime_e2e.provider_model_preflight must be an object"]

    failures = []
    status = preflight.get("status")
    if status not in {"passed", "blocked"}:
        failures.append(f"{display}: opencode provider_model_preflight.status must be passed or blocked")
    if "opencode-provider-preflight" not in str(preflight.get("command", "")):
        failures.append(f"{display}: opencode provider_model_preflight.command must reference opencode-provider-preflight")
    if not preflight.get("verified_on"):
        failures.append(f"{display}: opencode provider_model_preflight.verified_on required")
    models = preflight.get("legal_models")
    if status == "passed":
        if not isinstance(models, list) or not set(models).intersection(opencode_legal_deepseek_models):
            failures.append(f"{display}: opencode passed provider_model_preflight requires deepseek-v4-pro or deepseek-v4-flash")
        agent_status = runtime_e2e.get("agent_runtime_e2e", {}).get("status")
        if agent_status == "passed" and runtime_e2e.get("full_e2e_verified") is not True:
            failures.append(f"{display}: opencode passed agent_runtime_e2e requires full_e2e_verified=true")
    if status == "blocked" and runtime_e2e.get("full_e2e_verified") is not False:
        failures.append(f"{display}: opencode blocked provider_model_preflight requires full_e2e_verified=false")

    guidance_text = " ".join(
        str(value or "")
        for value in (
            preflight.get("blocked_reason"),
            preflight.get("remediation"),
            preflight.get("evidence"),
        )
    ).lower()
    if status == "blocked" and not all(marker in guidance_text for marker in opencode_legal_deepseek_models):
        failures.append(f"{display}: opencode blocked guidance must mention deepseek-v4-pro and deepseek-v4-flash")
    return failures


def check_agent_adapter_contract(
        root, run_runtime, *, package_root, adapter_required_keys, mainstream_agent_adapters, display_path,
        load_adapter_manifest, run_version_command, validate_codex_runtime_e2e_claim,
        validate_gemini_auth_preflight_claim, validate_opencode_provider_model_preflight_claim,
        validate_runtime_capabilities, validate_runtime_e2e_block,
):
    """FIX-071: mainstream agent adapters must be explicit and not overclaim coverage."""
    root = root or package_root
    failures = []
    reports = []

    for adapter_id in mainstream_agent_adapters:
        adapter_dir = root / "adapters" / adapter_id
        readme_path = adapter_dir / "README.md"
        launch_path = adapter_dir / "launch.py"
        for path in [readme_path, launch_path]:
            if not path.exists():
                failures.append(f"{display_path(path, root)}: missing adapter asset")

        manifest, manifest_failures = load_adapter_manifest(adapter_dir)
        failures.extend(manifest_failures)
        if not manifest:
            continue

        for key in adapter_required_keys:
            if key not in manifest:
                failures.append(f"{display_path(adapter_dir / 'adapter-manifest.json', root)}: missing `{key}`")

        if manifest.get("adapter_id") != adapter_id:
            failures.append(
                f"{display_path(adapter_dir / 'adapter-manifest.json', root)}: adapter_id must be `{adapter_id}`"
            )
        if manifest.get("workflow_id") != "software-project-governance":
            failures.append(
                f"{display_path(adapter_dir / 'adapter-manifest.json', root)}: workflow_id must be software-project-governance"
            )
        if manifest.get("launcher") != f"adapters/{adapter_id}/launch.py":
            failures.append(
                f"{display_path(adapter_dir / 'adapter-manifest.json', root)}: launcher path mismatch"
            )

        support_status = manifest.get("support_status", "")
        runtime_e2e = manifest.get("runtime_e2e", {})
        native_entry = manifest.get("native_entry", {})
        manifest_path = adapter_dir / "adapter-manifest.json"
        malformed_runtime_e2e = False
        failures.extend(validate_runtime_capabilities(root, manifest_path, manifest))
        if not isinstance(native_entry, dict) or not native_entry:
            failures.append(f"{display_path(adapter_dir / 'adapter-manifest.json', root)}: native_entry must be non-empty")
        if not isinstance(runtime_e2e, dict) or not runtime_e2e.get("command") or not runtime_e2e.get("version_command"):
            failures.append(f"{display_path(adapter_dir / 'adapter-manifest.json', root)}: runtime_e2e command/version_command required")
            runtime_e2e = {}
            malformed_runtime_e2e = True
        else:
            failures.extend(
                validate_runtime_e2e_block(
                    root, manifest_path, runtime_e2e, "target_cwd_e2e",
                    allow_unsupported=(support_status == "not-supported-current-release"),
                )
            )
            failures.extend(
                validate_runtime_e2e_block(
                    root, manifest_path, runtime_e2e, "agent_runtime_e2e",
                    allow_unsupported=(support_status == "not-supported-current-release"),
                )
            )
            if adapter_id == "codex":
                failures.extend(validate_codex_runtime_e2e_claim(root, manifest_path, runtime_e2e))
            if adapter_id == "gemini":
                failures.extend(validate_gemini_auth_preflight_claim(root, manifest_path, runtime_e2e))
            if adapter_id == "opencode":
                failures.extend(validate_opencode_provider_model_preflight_claim(root, manifest_path, runtime_e2e))
            if runtime_e2e.get("full_e2e_verified") is True:
                target_status = runtime_e2e.get("target_cwd_e2e", {}).get("status")
                agent_status = runtime_e2e.get("agent_runtime_e2e", {}).get("status")
                if target_status != "passed" or agent_status != "passed":
                    failures.append(
                        f"{display_path(manifest_path, root)}: full_e2e_verified=true requires target_cwd_e2e and agent_runtime_e2e passed"
                    )

        if support_status == "not-supported-current-release":
            if runtime_e2e.get("e2e_level") != "unsupported":
                failures.append(
                    f"{display_path(adapter_dir / 'adapter-manifest.json', root)}: unsupported adapter runtime_e2e.e2e_level must be unsupported"
                )
            if manifest.get("no_full_coverage_claim") is not True:
                failures.append(
                    f"{display_path(adapter_dir / 'adapter-manifest.json', root)}: unsupported adapter must set no_full_coverage_claim=true"
                )
            if not manifest.get("unsupported_reason"):
                failures.append(
                    f"{display_path(adapter_dir / 'adapter-manifest.json', root)}: unsupported adapter must explain unsupported_reason"
                )
            reports.append((adapter_id, "UNSUPPORTED", manifest.get("unsupported_reason", "")))
            continue

        if support_status != "runtime-verified":
            failures.append(
                f"{display_path(adapter_dir / 'adapter-manifest.json', root)}: support_status must be runtime-verified or not-supported-current-release"
            )
            continue

        if manifest.get("no_full_coverage_claim") is True:
            failures.append(
                f"{display_path(adapter_dir / 'adapter-manifest.json', root)}: runtime-verified adapter must not keep no_full_coverage_claim=true"
            )
        if runtime_e2e.get("e2e_level") not in ("runtime-version-probe", "real-agent-target-cwd"):
            failures.append(
                f"{display_path(adapter_dir / 'adapter-manifest.json', root)}: runtime-verified adapter runtime_e2e.e2e_level must be runtime-version-probe or real-agent-target-cwd"
            )
        if manifest.get("no_full_coverage_claim") is True and runtime_e2e.get("full_e2e_verified") is True:
            failures.append(
                f"{display_path(adapter_dir / 'adapter-manifest.json', root)}: no_full_coverage_claim=true conflicts with full_e2e_verified=true"
            )
        if not runtime_e2e.get("verified_on") or not runtime_e2e.get("evidence"):
            failures.append(
                f"{display_path(adapter_dir / 'adapter-manifest.json', root)}: runtime-verified adapter must include verified_on and evidence"
            )
        if malformed_runtime_e2e:
            reports.append((adapter_id, "FAIL", "invalid runtime_e2e"))
            continue

        if run_runtime:
            command_name = runtime_e2e.get("command", "")
            if not shutil.which(command_name):
                failures.append(f"{adapter_id}: runtime command `{command_name}` not found on PATH")
                reports.append((adapter_id, "FAIL", "command not found"))
                continue
            returncode, output = run_version_command(runtime_e2e["version_command"])
            if returncode != 0:
                failures.append(f"{adapter_id}: runtime command failed: {runtime_e2e['version_command']}")
                reports.append((adapter_id, "FAIL", output))
            else:
                reports.append((adapter_id, "PASS", output))
        else:
            reports.append((adapter_id, "STATIC", support_status))

    for adapter_id, status, detail in reports:
        print(f"[{status}] agent adapter {adapter_id}: {detail}")
    for failure in failures:
        print(f"[FAIL] agent adapter contract: {failure}")
    if not failures:
        print("[OK] agent adapter contracts synchronized")
    return failures
