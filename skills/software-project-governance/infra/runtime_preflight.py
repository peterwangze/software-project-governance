"""Inspect Gemini authentication and OpenCode provider readiness without exposing credentials."""

from dataclasses import dataclass
from pathlib import Path
import json
import locale
import os
import re
import subprocess
import sys


@dataclass(frozen=True)
class CredentialVariables:
    api_key_env_vars: tuple
    gca_credential_env_vars: tuple
    vertex_credential_env_vars: tuple


def _run_version_command(command, *, package_root):
    completed = subprocess.run(
        command,
        shell=True,
        cwd=package_root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = (completed.stdout or completed.stderr or "").strip()
    return completed.returncode, output


GEMINI_API_KEY_ENV_VARS = (
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
)


GEMINI_VERTEX_CONFIG_ENV_VARS = (
    "GOOGLE_GENAI_USE_VERTEXAI",
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_CLOUD_LOCATION",
)


GEMINI_VERTEX_CREDENTIAL_ENV_VARS = (
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_ADC_JSON",
    "GOOGLE_CLOUD_ACCESS_TOKEN",
)


GEMINI_GCA_CONFIG_ENV_VARS = (
    "GCA_AUTH_PROVIDER",
)


GEMINI_GCA_CREDENTIAL_ENV_VARS = (
    "GCA_TOKEN",
)


GEMINI_AUTH_REMEDIATION = (
    "Configure Gemini auth before full agent runtime E2E: set GEMINI_API_KEY "
    "or GOOGLE_API_KEY, configure Vertex credentials (for example "
    "GOOGLE_GENAI_USE_VERTEXAI with GOOGLE_CLOUD_PROJECT/LOCATION and ADC), "
    "configure GCA auth, or login/configure Gemini CLI settings.json with an "
    "auth provider/token type. Do not record secret values in manifests or logs."
)


def _gemini_settings_candidates(home=None):
    home = Path(home) if home else Path.home()
    return [
        home / ".gemini" / "settings.json",
        home / ".config" / "gemini" / "settings.json",
    ]


def _safe_env_present(name, env=None):
    env = env if env is not None else os.environ
    value = env.get(name)
    return value is not None and str(value).strip() != ""


def _detect_gemini_auth_from_settings(path):
    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    auth_key_markers = ("auth", "credential", "token", "provider", "login")
    provider_value_markers = ("oauth", "google", "vertex", "gca", "api_key", "apikey", "gemini")
    stack = [settings]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                key_text = str(key).lower()
                if isinstance(value, (dict, list)):
                    stack.append(value)
                    continue
                value_text = str(value).strip().lower()
                if not value_text:
                    continue
                if any(marker in key_text for marker in auth_key_markers):
                    if "token" in key_text:
                        return f"settings:{path.name}:token_type"
                    if any(marker in value_text for marker in provider_value_markers):
                        return f"settings:{path.name}:auth_provider"
                    return f"settings:{path.name}:auth_config"
        elif isinstance(current, list):
            stack.extend(current)
    return None


def _detect_gemini_env_auth_sources(env, *, safe_env_present, variables):
    env = env if env is not None else os.environ
    sources = []
    for name in variables.api_key_env_vars:
        if safe_env_present(name, env):
            sources.append(f"env:{name}")

    vertex_enabled = str(env.get("GOOGLE_GENAI_USE_VERTEXAI", "")).strip().lower() in {"1", "true", "yes"}
    vertex_has_project = safe_env_present("GOOGLE_CLOUD_PROJECT", env)
    vertex_has_location = safe_env_present("GOOGLE_CLOUD_LOCATION", env)
    vertex_credential_sources = [
        name for name in variables.vertex_credential_env_vars
        if safe_env_present(name, env)
    ]
    if vertex_enabled and vertex_has_project and vertex_has_location and vertex_credential_sources:
        sources.append("env:VERTEX:" + "+".join([
            "GOOGLE_GENAI_USE_VERTEXAI",
            "GOOGLE_CLOUD_PROJECT",
            "GOOGLE_CLOUD_LOCATION",
            *vertex_credential_sources,
        ]))

    gca_has_provider = safe_env_present("GCA_AUTH_PROVIDER", env)
    gca_credential_sources = [
        name for name in variables.gca_credential_env_vars
        if safe_env_present(name, env)
    ]
    if gca_has_provider and gca_credential_sources:
        sources.append("env:GCA:GCA_AUTH_PROVIDER+" + "+".join(gca_credential_sources))
    return sources


def _gemini_auth_preflight(
        env, home, which, version_runner, *, gemini_auth_remediation, detect_gemini_auth_from_settings,
        detect_gemini_env_auth_sources, gemini_settings_candidates, truncate_log,
):
    env = env if env is not None else os.environ
    result = {
        "status": "BLOCKED",
        "command": "python skills/software-project-governance/infra/verify_workflow.py gemini-auth-preflight",
        "version_command": "gemini --version",
        "cli_path": None,
        "version": None,
        "auth_sources": [],
        "blocked_reason": None,
        "remediation": gemini_auth_remediation,
    }

    cli_path = which("gemini")
    if not cli_path:
        result["blocked_reason"] = "Gemini CLI not found on PATH"
        return result
    result["cli_path"] = str(cli_path)

    returncode, version_output = version_runner("gemini --version")
    if returncode != 0:
        result["blocked_reason"] = "Gemini CLI version command failed"
        result["version"] = truncate_log(version_output, limit=200)
        return result
    result["version"] = truncate_log(version_output, limit=200)

    result["auth_sources"].extend(detect_gemini_env_auth_sources(env))

    for path in gemini_settings_candidates(home=home):
        source = detect_gemini_auth_from_settings(path)
        if source:
            result["auth_sources"].append(source)

    if result["auth_sources"]:
        result["status"] = "PASS"
        result["blocked_reason"] = None
    else:
        result["blocked_reason"] = "Gemini auth missing or not configured"
    return result


OPENCODE_LEGAL_DEEPSEEK_MODELS = ("deepseek-v4-pro", "deepseek-v4-flash")


OPENCODE_PROVIDER_MODEL_REMEDIATION = (
    "Configure opencode with a supported DeepSeek model, for example "
    "deepseek-v4-pro or deepseek-v4-flash. Remove ANSI escape/suffix residue "
    "such as deepseek-v4-pro[1m]. Do not record provider API keys or secret "
    "values in manifests, tests, docs, or logs."
)


def _run_opencode_probe_command(command, timeout, *, package_root, e2e_output):
    try:
        completed = subprocess.run(
            command,
            cwd=str(package_root),
            capture_output=True,
            text=True,
            encoding=locale.getpreferredencoding(False),
            errors="replace",
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return 1, str(exc)
    return completed.returncode, e2e_output(completed)


def _opencode_config_candidates(home, root, *, package_root):
    home = Path(home) if home else Path.home()
    root = Path(root) if root else package_root
    return [
        root / "opencode.json",
        root / "opencode.jsonc",
        root / "opencode.toml",
        home / ".config" / "opencode" / "opencode.json",
        home / ".config" / "opencode" / "opencode.jsonc",
        home / ".config" / "opencode" / "opencode.toml",
        home / ".opencode.json",
    ]


def _sanitize_opencode_probe_text(text, *, truncate_log):
    sanitized = re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "<ANSI>", text or "")
    sanitized = re.sub(
        r"(?i)(api[_-]?key|token|secret|authorization|bearer)\s*[:=]\s*['\"]?[^'\"\s,}]+",
        r"\1=<redacted>",
        sanitized,
    )
    sanitized = re.sub(r"\bsk-[A-Za-z0-9._-]+", "<redacted-secret>", sanitized)
    return truncate_log(sanitized, limit=500)


def _opencode_model_scan(text, *, opencode_legal_deepseek_models):
    raw = text or ""
    lowered = raw.lower()
    blocked_markers = []
    if "\x1b" in raw:
        blocked_markers.append("ANSI escape residue")
    if re.search(r"deepseek-v4-(?:pro|flash)\[[0-9;?]*[a-zA-Z]", raw):
        blocked_markers.append("ANSI suffix residue")
    if "unsupported model" in lowered or "not supported" in lowered or "invalid model" in lowered:
        blocked_markers.append("unsupported model output")

    legal_models = [
        model for model in opencode_legal_deepseek_models
        if re.search(rf"(?<![\w.-]){re.escape(model)}(?![\w.-])", raw)
    ]
    invalid_candidates = re.findall(r"deepseek-v4-(?:pro|flash)\[[^\s,;\"'}]+", raw)
    return {
        "legal_models": sorted(set(legal_models)),
        "blocked_markers": sorted(set(blocked_markers)),
        "invalid_candidates": sorted(set(invalid_candidates)),
    }


def _opencode_provider_model_preflight(
        home, root, which, version_runner, probe_runner, config_candidates, *,
        opencode_provider_model_remediation, opencode_config_candidates, opencode_model_scan,
        sanitize_opencode_probe_text,
):
    result = {
        "status": "BLOCKED",
        "command": "python skills/software-project-governance/infra/verify_workflow.py opencode-provider-preflight",
        "version_command": "opencode --version",
        "cli_path": None,
        "version": None,
        "legal_models": [],
        "model_sources": [],
        "blocked_reason": None,
        "remediation": opencode_provider_model_remediation,
    }

    cli_path = which("opencode")
    if not cli_path:
        result["blocked_reason"] = "opencode CLI not found on PATH"
        return result
    result["cli_path"] = str(cli_path)

    returncode, version_output = version_runner("opencode --version")
    if returncode != 0:
        result["version"] = sanitize_opencode_probe_text(version_output)
        result["blocked_reason"] = "opencode CLI version command failed"
        return result
    result["version"] = sanitize_opencode_probe_text(version_output)

    scan_texts = []
    for command in (["opencode", "models"], ["opencode", "model", "list"]):
        code, output = probe_runner(command)
        if output:
            scan_texts.append((f"command:{' '.join(command)}", output))
        if code == 0 and output:
            break

    paths = config_candidates
    if paths is None:
        paths = opencode_config_candidates(home=home, root=root)
    for path in paths:
        path = Path(path)
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        scan_texts.append((f"config:{path.name}", content))

    blocked = []
    for source, text in scan_texts:
        scan = opencode_model_scan(text)
        for model in scan["legal_models"]:
            if model not in result["legal_models"]:
                result["legal_models"].append(model)
        if scan["legal_models"]:
            result["model_sources"].append(source)
        if scan["blocked_markers"] or scan["invalid_candidates"]:
            blocked.append(
                f"{source}: "
                + ", ".join(scan["blocked_markers"] + scan["invalid_candidates"])
            )

    result["legal_models"].sort()
    if blocked:
        result["blocked_reason"] = "opencode provider/model config invalid: " + "; ".join(blocked)
        return result
    if result["legal_models"]:
        result["status"] = "PASS"
        return result

    result["blocked_reason"] = (
        "opencode provider/model config missing supported DeepSeek model "
        "(deepseek-v4-pro or deepseek-v4-flash)"
    )
    return result


def cmd_gemini_auth_preflight(_args, *, gemini_auth_preflight):
    """Check Gemini CLI availability and authentication sources without leaking secrets."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    result = gemini_auth_preflight()
    print("=== Gemini Auth Preflight ===")
    print(f"status: {result['status']}")
    print(f"command: {result['command']}")
    print(f"version_command: {result['version_command']}")
    print(f"cli_path: {result['cli_path'] or 'not found'}")
    if result["version"]:
        print(f"version: {result['version']}")
    if result["auth_sources"]:
        print("auth_sources:")
        for source in result["auth_sources"]:
            print(f" - {source}")
    else:
        print("auth_sources: none")
    if result["blocked_reason"]:
        print(f"blocked_reason: {result['blocked_reason']}")
    print(f"remediation: {result['remediation']}")
    if result["status"] != "PASS":
        sys.exit(1)


def cmd_opencode_provider_preflight(_args, *, opencode_provider_model_preflight, sanitize_opencode_probe_text):
    """Check opencode CLI and DeepSeek provider/model config without leaking secrets."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    result = opencode_provider_model_preflight()
    print("=== opencode Provider/Model Preflight ===")
    print(f"status: {result['status']}")
    print(f"command: {result['command']}")
    print(f"version_command: {result['version_command']}")
    print(f"cli_path: {result['cli_path'] or 'not found'}")
    if result["version"]:
        print(f"version: {result['version']}")
    if result["legal_models"]:
        print("legal_models:")
        for model in result["legal_models"]:
            print(f" - {model}")
    else:
        print("legal_models: none")
    if result["model_sources"]:
        print("model_sources:")
        for source in result["model_sources"]:
            print(f" - {source}")
    else:
        print("model_sources: none")
    if result["blocked_reason"]:
        print(f"blocked_reason: {sanitize_opencode_probe_text(result['blocked_reason'])}")
    print(f"remediation: {sanitize_opencode_probe_text(result['remediation'])}")
    if result["status"] != "PASS":
        sys.exit(1)
