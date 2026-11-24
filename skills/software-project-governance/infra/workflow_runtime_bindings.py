"""Compose runtime probes, loop commands and the web console."""

import workflow_project_roots as paths
import workflow_policy_bindings as policies

from datetime import datetime
import os
import webbrowser


def _e2e_command_matrix():
    from product_fixture_validation import _e2e_command_matrix as run
    return run(
        package_root=paths.ROOT,
        validate_e2e_cleanup=_validate_e2e_cleanup, validate_e2e_gate_g99=_validate_e2e_gate_g99,
        validate_e2e_gates=_validate_e2e_gates, validate_e2e_governance_proxy=_validate_e2e_governance_proxy,
        validate_e2e_status=_validate_e2e_status,
        validate_e2e_verify_known_failure=_validate_e2e_verify_known_failure,
    )


def _e2e_target_cwd_command_matrix(e2e_dir):
    from product_fixture_validation import _e2e_target_cwd_command_matrix as run
    return run(
        e2e_dir, validate_e2e_cleanup=_validate_e2e_cleanup, validate_e2e_gate_g99=_validate_e2e_gate_g99,
        validate_e2e_gates=_validate_e2e_gates, validate_e2e_status=_validate_e2e_status,
    )


def _e2e_target_fixture_checks(e2e_dir):
    import release_check_bindings as release_checks

    from product_fixture_validation import _e2e_target_fixture_checks as run
    return run(
        e2e_dir, package_root=paths.ROOT, extract_plan_workflow_version=release_checks._extract_plan_workflow_version,
        extract_skill_version=release_checks._extract_skill_version,
    )


def _e2e_contract_checks():
    from product_fixture_validation import _e2e_contract_checks as run
    return run(package_root=paths.ROOT)


AGENT_RUNTIME_E2E_PLATFORMS = ("claude", "codex", "gemini", "opencode", "pi")


def _agent_runtime_e2e_prompt(agent_id):
    from host_certification import _agent_runtime_e2e_prompt as run
    return run(agent_id)


def _agent_runtime_e2e_command_matrix(e2e_dir=None):
    from host_certification import _agent_runtime_e2e_command_matrix as run
    return run(
        e2e_dir, package_root=paths.ROOT, agent_runtime_e2e_platforms=AGENT_RUNTIME_E2E_PLATFORMS,
        agent_runtime_e2e_prompt=_agent_runtime_e2e_prompt,
        validate_agent_runtime_e2e_passed=_validate_agent_runtime_e2e_passed,
    )


def _run_e2e_subprocess(command, timeout=30, cwd=None):
    from product_fixture_validation import _run_e2e_subprocess as run
    return run(command, timeout, cwd, package_root=paths.ROOT)


def _e2e_output(result):
    from product_fixture_validation import _e2e_output as run
    return run(result)


def _truncate_log(text, limit=1200):
    from product_fixture_validation import _truncate_log as run
    return run(text, limit)


def _coerce_e2e_text(value):
    from product_fixture_validation import _coerce_e2e_text as run
    return run(value)


def _has_all(text, needles):
    from product_fixture_validation import _has_all as run
    return run(text, needles)


def _e2e_json_object(result):
    from product_fixture_validation import _e2e_json_object as run
    return run(result)


def _valid_e2e_loop_view(view):
    from product_fixture_validation import _valid_e2e_loop_view as run
    return run(view)


def _validate_e2e_status(result):
    from product_fixture_validation import _validate_e2e_status as run
    return run(result, e2e_json_object=_e2e_json_object, valid_e2e_loop_view=_valid_e2e_loop_view)


def _validate_e2e_gates(result):
    from product_fixture_validation import _validate_e2e_gates as run
    return run(result, e2e_json_object=_e2e_json_object, valid_e2e_loop_view=_valid_e2e_loop_view)


def _validate_e2e_gate_g99(result):
    from product_fixture_validation import _validate_e2e_gate_g99 as run
    return run(result, e2e_json_object=_e2e_json_object)


def _validate_e2e_cleanup(result):
    from product_fixture_validation import _validate_e2e_cleanup as run
    return run(result, e2e_output=_e2e_output)


def _normalize_e2e_verify_failure(line):
    from product_fixture_validation import _normalize_e2e_verify_failure as run
    return run(line)


def _extract_e2e_verify_failures(output):
    from product_fixture_validation import _extract_e2e_verify_failures as run
    return run(output, normalize_e2e_verify_failure=_normalize_e2e_verify_failure)


def _validate_e2e_verify_known_failure(result):
    from product_fixture_validation import _validate_e2e_verify_known_failure as run
    return run(
        result, known_verify_failure_signatures=policies._host_policy('_KNOWN_VERIFY_FAILURE_SIGNATURES'),
        e2e_output=_e2e_output, extract_e2e_verify_failures=_extract_e2e_verify_failures,
    )


def _evaluate_e2e_target_fixture_check(entry):
    import release_check_bindings as release_checks

    from product_fixture_validation import _evaluate_e2e_target_fixture_check as run
    return run(entry, package_root=paths.ROOT, extract_skill_version=release_checks._extract_skill_version)


def _validate_e2e_governance_proxy(result):
    from product_fixture_validation import _validate_e2e_governance_proxy as run
    return run(result, e2e_json_object=_e2e_json_object, valid_e2e_loop_view=_valid_e2e_loop_view)


def _evaluate_e2e_command(entry, runner=_run_e2e_subprocess):
    from product_fixture_validation import _evaluate_e2e_command as run
    return run(entry, runner)


def _evaluate_e2e_contract_check(entry):
    from product_fixture_validation import _evaluate_e2e_contract_check as run
    return run(entry, has_all=_has_all)


def _validate_agent_runtime_e2e_passed(agent_id, result, root=None):
    from host_certification import _validate_agent_runtime_e2e_passed as run
    return run(
        agent_id, result, root, package_root=paths.ROOT, e2e_output=_e2e_output,
        is_valid_agent_runtime_mode=_is_valid_agent_runtime_mode,
        is_valid_agent_runtime_workflow_agent=_is_valid_agent_runtime_workflow_agent,
        parse_agent_runtime_e2e_fields=_parse_agent_runtime_e2e_fields,
    )


def _agent_runtime_e2e_candidate_texts(output):
    from host_certification import _agent_runtime_e2e_candidate_texts as run
    return run(output)


def _parse_agent_runtime_e2e_fields(output):
    from host_certification import _parse_agent_runtime_e2e_fields as run
    return run(output, agent_runtime_e2e_candidate_texts=_agent_runtime_e2e_candidate_texts)


def _is_non_placeholder_agent_runtime_value(value):
    from host_certification import _is_non_placeholder_agent_runtime_value as run
    return run(value)


def _is_valid_agent_runtime_workflow_agent(value):
    from host_certification import _is_valid_agent_runtime_workflow_agent as run
    return run(
        value, agent_runtime_e2e_platforms=AGENT_RUNTIME_E2E_PLATFORMS,
        is_non_placeholder_agent_runtime_value=_is_non_placeholder_agent_runtime_value,
    )


def _is_valid_agent_runtime_mode(value):
    from host_certification import _is_valid_agent_runtime_mode as run
    return run(value, is_non_placeholder_agent_runtime_value=_is_non_placeholder_agent_runtime_value)


def _classify_agent_runtime_blocked(agent_id, output='', exception=None):
    from host_certification import _classify_agent_runtime_blocked as run
    return run(agent_id, output, exception)


def _resolve_agent_runtime_command(command):
    from host_certification import _resolve_agent_runtime_command as run
    return run(command)


def _run_agent_runtime_e2e_subprocess(command, timeout=120, cwd=None):
    from host_certification import _run_agent_runtime_e2e_subprocess as run
    return run(
        command, timeout, cwd, package_root=paths.ROOT,
        cleanup_agent_runtime_process_tree=_cleanup_agent_runtime_process_tree,
        resolve_agent_runtime_command=_resolve_agent_runtime_command,
    )


def _cleanup_agent_runtime_process_tree(process):
    from host_certification import _cleanup_agent_runtime_process_tree as run
    return run(process)


def _evaluate_agent_runtime_e2e_command(entry, timeout=120, runner=_run_agent_runtime_e2e_subprocess):
    from host_certification import _evaluate_agent_runtime_e2e_command as run
    return run(
        entry, timeout, runner, classify_agent_runtime_blocked=_classify_agent_runtime_blocked,
        coerce_e2e_text=_coerce_e2e_text, e2e_output=_e2e_output, truncate_log=_truncate_log,
    )


def cmd_agent_runtime_e2e(args):
    from host_certification import cmd_agent_runtime_e2e as run
    return run(
        args, package_root=paths.ROOT, agent_runtime_e2e_platforms=AGENT_RUNTIME_E2E_PLATFORMS,
        agent_runtime_e2e_command_matrix=_agent_runtime_e2e_command_matrix,
        evaluate_agent_runtime_e2e_command=_evaluate_agent_runtime_e2e_command,
    )


def cmd_gemini_auth_preflight(_args):
    import host_check_bindings as host_checks

    from runtime_preflight import cmd_gemini_auth_preflight as run
    return run(_args, gemini_auth_preflight=host_checks._gemini_auth_preflight)


def cmd_opencode_provider_preflight(_args):
    import host_check_bindings as host_checks

    from runtime_preflight import cmd_opencode_provider_preflight as run
    return run(
        _args, opencode_provider_model_preflight=host_checks._opencode_provider_model_preflight,
        sanitize_opencode_probe_text=host_checks._sanitize_opencode_probe_text,
    )


def cmd_e2e_check(_args):
    from product_fixture_validation import cmd_e2e_check as run
    return run(
        _args, plugin_root=paths.PLUGIN_ROOT, package_root=paths.ROOT, e2e_command_matrix=_e2e_command_matrix,
        e2e_contract_checks=_e2e_contract_checks,
        e2e_target_cwd_command_matrix=_e2e_target_cwd_command_matrix,
        e2e_target_fixture_checks=_e2e_target_fixture_checks, evaluate_e2e_command=_evaluate_e2e_command,
        evaluate_e2e_contract_check=_evaluate_e2e_contract_check,
        evaluate_e2e_target_fixture_check=_evaluate_e2e_target_fixture_check,
    )


def cmd_check_flow_unit_runtime(args):
    from loop_commands import cmd_check_flow_unit_runtime as run
    return run(args, host_root=paths.HOST_PROJECT_ROOT, product_root=paths.ROOT)


def cmd_check_loop_health(args):
    from loop_commands import cmd_check_loop_health as run
    return run(args, host_root=paths.HOST_PROJECT_ROOT)


def _format_rollup(result):
    from loop_commands import _format_rollup as read
    return read(result)


def _format_telemetry(report, json_out=False):
    from loop_commands import _format_telemetry as read
    return read(report, json_out, write_json=write_cli_json)


def cmd_loop_rollup(args):
    from loop_commands import cmd_loop_rollup as run
    return run(args, host_root=paths.HOST_PROJECT_ROOT, format_rollup=_format_rollup)


def write_cli_json(payload, *, indent=None):
    from loop_commands import write_cli_json as read
    return read(payload, indent=indent)


def cmd_loop(args):
    from loop_commands import cmd_loop as run
    return run(args, host_root=paths.HOST_PROJECT_ROOT, write_json=write_cli_json)


def cmd_loop_telemetry(args):
    from loop_commands import cmd_loop_telemetry as run
    return run(args, host_root=paths.HOST_PROJECT_ROOT, format_telemetry=_format_telemetry)


def _web_console_open_url(url, *, timeout):
    return policies._host_policy("urllib").request.urlopen(url, timeout=timeout)


def _web_console_url(host="127.0.0.1", port=5173):
    from web_console import _web_console_url as read
    return read(host, port)


_WEB_INSTALL_TIMEOUT_DEFAULT = 120


_WEB_INSTALL_TIMEOUT_ENV = "SPG_WEB_INSTALL_TIMEOUT"


def _resolve_positive_timeout(raw, default):
    from operational_cli import _resolve_positive_timeout as read
    return read(raw, default)


def _resolve_web_install_timeout(raw):
    from web_console import _resolve_web_install_timeout as read
    return read(
        raw, default_seconds=_WEB_INSTALL_TIMEOUT_DEFAULT,
        positive_timeout=_resolve_positive_timeout,
    )


def _web_console_is_live(url, timeout=1.5):
    from web_console import _web_console_is_live as read
    return read(url, timeout, web_console_probe=_web_console_probe)


def _web_console_probe(url, timeout=1.5):
    from web_console import _web_console_probe as read
    return read(url, timeout, open_url=_web_console_open_url)


def _web_console_paths():
    from web_console import _web_console_paths as read
    return read(product_root=paths.ROOT)


def _write_web_console_process(paths, process):
    from web_console import _write_web_console_process as read
    return read(paths, process)


def cmd_web_console(args):
    from web_console import cmd_web_console as run
    return run(
        args, host_root=lambda: paths.HOST_PROJECT_ROOT, product_root=lambda: paths.ROOT,
        install_timeout=lambda: _resolve_web_install_timeout(os.environ.get(_WEB_INSTALL_TIMEOUT_ENV, "")),
        display_path=lambda path: paths._display_path(path), web_console_is_live=lambda url: _web_console_is_live(url),
        web_console_paths=lambda: _web_console_paths(), web_console_probe=lambda url: _web_console_probe(url),
        web_console_url=lambda host, port: _web_console_url(host, port),
        write_web_console_process=lambda paths, process: _write_web_console_process(paths, process),
        open_browser=lambda url: webbrowser.open(url), now=lambda: datetime.now(),
    )


_RESOLVE_TIMEOUT_DEFAULT = 15


_RESOLVE_TIMEOUT_ENV = "SPG_RESOLVE_TIMEOUT"


_RESOLVE_ENTRY_REL = "skills/software-project-governance/infra/resolve_entry.py"


_RESOLVE_ENTRY_CANONICAL_MARKER = "Deterministic /governance entry resolver (FX-130)"


_RESOLVE_EXIT_OTHER = 1


_RESOLVE_EXIT_PYTHON_MISSING = 2


_RESOLVE_EXIT_FILE_NOT_FOUND = 3


_RESOLVE_EXIT_TIMEOUT = 4


_RESOLVE_EXIT_STORE_STUB = 5


def _resolve_resolve_timeout(raw):
    from entry_resolution_cli import _resolve_resolve_timeout as read
    return read(
        raw, default_seconds=_RESOLVE_TIMEOUT_DEFAULT,
        positive_timeout=_resolve_positive_timeout,
    )


def cmd_resolve_entry(args):
    from entry_resolution_cli import ResolverPolicy, cmd_resolve_entry as run
    policy = ResolverPolicy(
        canonical_marker=_RESOLVE_ENTRY_CANONICAL_MARKER,
        resolver_relative_path=_RESOLVE_ENTRY_REL,
        timeout_env=_RESOLVE_TIMEOUT_ENV,
        resolve_exit_other=_RESOLVE_EXIT_OTHER,
        resolve_exit_python_missing=_RESOLVE_EXIT_PYTHON_MISSING,
        resolve_exit_file_not_found=_RESOLVE_EXIT_FILE_NOT_FOUND,
        resolve_exit_timeout=_RESOLVE_EXIT_TIMEOUT,
        resolve_exit_store_stub=_RESOLVE_EXIT_STORE_STUB,
    )
    return run(
        args, definition_policy=policy, product_root=paths.ROOT,
        resolve_resolve_timeout=_resolve_resolve_timeout,
    )
