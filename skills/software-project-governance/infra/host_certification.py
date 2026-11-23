"""Run host runtime certification and classify verified, blocked and failed observations."""

from pathlib import Path
import json
import locale
import os
import re
import shutil
import signal
import subprocess
import sys


def _agent_runtime_e2e_prompt(agent_id):
    return (
        "Read the local governance bootstrap and the native work units. Use an open unit ID, "
        "or any recorded unit ID if all are closed. Use [] only if there are no units. "
        "Answer with exactly these "
        f"machine-readable fields if the workflow is loaded: E2E_PLATFORM={agent_id}; "
        "E2E_AGENT=<workflow role>; E2E_UNIT=<work unit ID or []>; "
        "E2E_MODE=<trigger x permission>. "
        "Do not modify files."
    )


def _agent_runtime_e2e_command_matrix(
        e2e_dir, *, package_root, agent_runtime_e2e_platforms, agent_runtime_e2e_prompt,
        validate_agent_runtime_e2e_passed,
):
    """Return real agent runtime E2E commands for mainstream code agents."""
    e2e_dir = e2e_dir or package_root / "project/e2e-test-project"
    prompts = {
        agent_id: agent_runtime_e2e_prompt(agent_id)
        for agent_id in agent_runtime_e2e_platforms
    }
    return [
        {
            "agent": "claude",
            "label": "Claude real agent target cwd",
            "cwd": e2e_dir,
            "command": [
                "claude",
                "-p",
                prompts["claude"],
                "--permission-mode",
                "default",
                "--allowedTools",
                "Read",
                "--output-format",
                "text",
            ],
            "validator": validate_agent_runtime_e2e_passed,
        },
        {
            "agent": "codex",
            "label": "Codex CLI headless target cwd",
            "cwd": e2e_dir,
            "command": [
                "codex",
                "exec",
                "-C",
                ".",
                "-s",
                "read-only",
                "--ephemeral",
                prompts["codex"],
            ],
            "validator": validate_agent_runtime_e2e_passed,
        },
        {
            "agent": "gemini",
            "label": "Gemini CLI target cwd",
            "cwd": e2e_dir,
            "command": [
                "gemini",
                "--prompt",
                prompts["gemini"],
                "--approval-mode",
                "plan",
                "--output-format",
                "text",
            ],
            "validator": validate_agent_runtime_e2e_passed,
        },
        {
            "agent": "opencode",
            "label": "opencode CLI target cwd",
            "cwd": e2e_dir,
            "command": [
                "opencode",
                "run",
                "--dir",
                ".",
                "--format",
                "json",
                prompts["opencode"],
            ],
            "validator": validate_agent_runtime_e2e_passed,
        },
        {
            # FEAT-100: pi mixed-scope entry (user ruling #3) — real agent-dir
            # read-only credentials + --no-session (zero write surface) +
            # --tools read (read-only subset) + -na (one-shot trust denial;
            # context files load without trust per pi security.md L57).
            "agent": "pi",
            "label": "pi CLI headless target cwd",
            "cwd": e2e_dir,
            "command": [
                "pi",
                "-p",
                prompts["pi"],
                "--tools",
                "read",
                "--no-session",
                "-na",
            ],
            "validator": validate_agent_runtime_e2e_passed,
        },
    ]


def _validate_agent_runtime_e2e_passed(
        agent_id, result, root, *, package_root, e2e_output, is_valid_agent_runtime_mode,
        is_valid_agent_runtime_workflow_agent, parse_agent_runtime_e2e_fields,
):
    output = e2e_output(result)
    if result.returncode != 0:
        return False, f"real agent exited with code {result.returncode}"

    fields = parse_agent_runtime_e2e_fields(output)
    if not fields:
        return False, "real agent output missing structured E2E_PLATFORM/E2E_AGENT/E2E_UNIT/E2E_MODE response"
    from governance_readers import loop_state
    view = loop_state(root or package_root / "project/e2e-test-project")
    if view["state"] == "invalid":
        return False, view["message"]
    current = [u for u in view["units"] if u["runtime_status"] not in ("completed", "withdrawn")]
    expected = {u["flow_unit_id"] for u in current or view["units"]} or {"[]"}
    for response in fields:
        platform = response.get("E2E_PLATFORM", "")
        workflow_agent = response.get("E2E_AGENT", "")
        unit_id = response.get("E2E_UNIT", "")
        mode = response.get("E2E_MODE", "")
        if (
            platform == agent_id
            and is_valid_agent_runtime_workflow_agent(workflow_agent)
            and unit_id in expected
            and is_valid_agent_runtime_mode(mode)
        ):
            return True, (
                f"real agent output includes structured response: "
                f"E2E_PLATFORM={platform}; E2E_AGENT={workflow_agent}; "
                f"E2E_UNIT={unit_id}; E2E_MODE={mode}"
            )
    return False, (
        "real agent output did not include a complete non-placeholder "
        f"E2E response with platform={agent_id}"
    )


def _agent_runtime_e2e_candidate_texts(output):
    """Return text payloads from agent output while preserving plain text logs."""
    candidates = []
    for line in (output or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            event = json.loads(stripped)
        except json.JSONDecodeError:
            candidates.append(line)
            continue
        if not isinstance(event, dict):
            candidates.append(line)
            continue
        extracted = False
        part = event.get("part")
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            candidates.append(part["text"])
            extracted = True
        if isinstance(event.get("text"), str):
            candidates.append(event["text"])
            extracted = True
        if not extracted:
            candidates.append(line)
    return candidates or [output or ""]


def _parse_agent_runtime_e2e_fields(output, *, agent_runtime_e2e_candidate_texts):
    """Extract E2E field groups from semicolon/newline-delimited agent output."""
    groups = []
    current = {}
    for candidate in agent_runtime_e2e_candidate_texts(output):
        for match in re.finditer(r"\b(E2E_PLATFORM|E2E_AGENT|E2E_UNIT|E2E_MODE)\s*=\s*([^;\r\n]+)", candidate or ""):
            key, value = match.group(1), match.group(2).strip()
            if key == "E2E_PLATFORM" and "E2E_PLATFORM" in current:
                groups.append(current)
                current = {}
            current[key] = value
            if {"E2E_PLATFORM", "E2E_AGENT", "E2E_UNIT", "E2E_MODE"}.issubset(current):
                groups.append(current)
                current = {}
    if current:
        groups.append(current)
    return groups


def _is_non_placeholder_agent_runtime_value(value):
    value = (value or "").strip()
    lowered = value.lower()
    if not value:
        return False
    if value.startswith("<") and value.endswith(">"):
        return False
    placeholder_markers = ("placeholder", "work unit id or []", "trigger x permission")
    return not any(marker in lowered for marker in placeholder_markers)


def _is_valid_agent_runtime_workflow_agent(
        value, *, agent_runtime_e2e_platforms, is_non_placeholder_agent_runtime_value,
):
    if not is_non_placeholder_agent_runtime_value(value):
        return False
    return value.strip().lower() not in agent_runtime_e2e_platforms


def _is_valid_agent_runtime_mode(value, *, is_non_placeholder_agent_runtime_value):
    if not is_non_placeholder_agent_runtime_value(value):
        return False
    parts = [part.strip() for part in value.split(" x ")]
    if len(parts) != 2 or not all(is_non_placeholder_agent_runtime_value(part) for part in parts):
        return False
    trigger_mode, permission_mode = parts
    return (
        trigger_mode in {"always-on", "on-demand", "silent-track"}
        and permission_mode in {"maximum-autonomy", "default-confirm"}
    )


def _classify_agent_runtime_blocked(agent_id, output='', exception=None):
    """Return blocked_reason for known environment/runtime blockers."""
    lowered = (output or "").lower()
    if isinstance(exception, FileNotFoundError):
        return f"{agent_id} runtime command not found on PATH"
    if isinstance(exception, PermissionError):
        return f"{agent_id} runtime command could not start due to OS permission/path resolution"
    if agent_id == "codex" and isinstance(exception, subprocess.TimeoutExpired):
        return "Codex CLI target-cwd command timed out"
    if agent_id == "codex" and "timed out" in lowered:
        return "Codex CLI target-cwd command timed out"
    if agent_id == "gemini":
        auth_markers = [
            "gemini_api_key",
            "google_api_key",
            "api key",
            "auth",
            "authenticate",
            "authentication",
            "credential",
            "login",
            "vertex",
            "gca",
        ]
        if any(marker in lowered for marker in auth_markers):
            return (
                "Gemini auth missing or not configured; configure GEMINI_API_KEY, "
                "GOOGLE_API_KEY, Vertex credentials, GCA auth, or Gemini settings auth."
            )
    if agent_id == "opencode":
        if isinstance(exception, subprocess.TimeoutExpired):
            return (
                "opencode CLI target-cwd command timed out; increase timeout "
                "or inspect partial tool use before classifying as provider/model invalid"
            )
        if "timed out" in lowered or "timeout" in lowered:
            return (
                "opencode CLI target-cwd command timed out; increase timeout "
                "or inspect partial tool use before classifying as provider/model invalid"
            )
        invalid_model_markers = [
            "deepseek-v4-pro[1m]",
            "invalid model",
            "model not",
            "unsupported model",
            "not supported",
        ]
        if any(marker in lowered for marker in invalid_model_markers):
            return "opencode provider/model config invalid"
    return None


def _resolve_agent_runtime_command(command):
    """Resolve PATH/PATHEXT shims before Popen, especially npm .cmd shims on Windows."""
    if not command:
        return command
    resolved = shutil.which(command[0])
    if not resolved:
        return command
    return [resolved, *command[1:]]


def _run_agent_runtime_e2e_subprocess(
        command, timeout, cwd, *, package_root, cleanup_agent_runtime_process_tree,
        resolve_agent_runtime_command,
):
    command = resolve_agent_runtime_command(command)
    popen_kwargs = {}
    if os.name != "nt":
        popen_kwargs["start_new_session"] = True
    process = subprocess.Popen(
        command,
        cwd=str(cwd or package_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding=locale.getpreferredencoding(False),
        errors="replace",
        **popen_kwargs,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        cleanup_agent_runtime_process_tree(process)
        stdout, stderr = process.communicate()
        raise subprocess.TimeoutExpired(
            exc.cmd,
            exc.timeout,
            output=stdout,
            stderr=stderr,
        ) from exc
    return subprocess.CompletedProcess(
        command,
        process.returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _cleanup_agent_runtime_process_tree(process):
    """Best-effort cleanup for agent runtime shims and their child process trees."""
    pid = getattr(process, "pid", None)
    if not pid:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
            )
            return
        except (subprocess.SubprocessError, OSError):
            pass
    else:
        try:
            os.killpg(pid, signal.SIGKILL)
            return
        except (OSError, ProcessLookupError):
            pass
    try:
        process.kill()
    except OSError:
        pass


def _evaluate_agent_runtime_e2e_command(
        entry, timeout, runner, *, classify_agent_runtime_blocked, coerce_e2e_text, e2e_output, truncate_log,
):
    """Execute one real agent runtime command and normalize pass/blocked/fail."""
    agent_id = entry["agent"]
    command = entry["command"]
    cwd = entry.get("cwd")
    try:
        try:
            result = runner(command, timeout=timeout, cwd=cwd)
        except TypeError:
            result = runner(command)
    except subprocess.TimeoutExpired as exc:
        output = coerce_e2e_text(exc.stdout) + "\n" + coerce_e2e_text(exc.stderr)
        blocked_reason = classify_agent_runtime_blocked(agent_id, output, exc)
        status = "BLOCKED" if blocked_reason else "FAIL"
        return {
            "agent": agent_id,
            "label": entry["label"],
            "status": status,
            "exit_code": None,
            "command": command,
            "cwd": cwd,
            "message": blocked_reason or f"unclassified timeout: {exc}",
            "blocked_reason": blocked_reason,
            "log_summary": truncate_log(output or str(exc)),
        }
    except (OSError, FileNotFoundError) as exc:
        blocked_reason = classify_agent_runtime_blocked(agent_id, "", exc)
        status = "BLOCKED" if blocked_reason else "FAIL"
        return {
            "agent": agent_id,
            "label": entry["label"],
            "status": status,
            "exit_code": None,
            "command": command,
            "cwd": cwd,
            "message": blocked_reason or f"subprocess did not start: {exc}",
            "blocked_reason": blocked_reason,
            "log_summary": truncate_log(str(exc)),
        }

    output = e2e_output(result)
    ok, message = entry["validator"](agent_id, result, root=cwd)
    if ok:
        return {
            "agent": agent_id,
            "label": entry["label"],
            "status": "PASS",
            "exit_code": result.returncode,
            "command": command,
            "cwd": cwd,
            "message": message,
            "blocked_reason": None,
            "log_summary": truncate_log(output),
        }

    blocked_reason = classify_agent_runtime_blocked(agent_id, output)
    if blocked_reason:
        return {
            "agent": agent_id,
            "label": entry["label"],
            "status": "BLOCKED",
            "exit_code": result.returncode,
            "command": command,
            "cwd": cwd,
            "message": blocked_reason,
            "blocked_reason": blocked_reason,
            "log_summary": truncate_log(output),
        }

    return {
        "agent": agent_id,
        "label": entry["label"],
        "status": "FAIL",
        "exit_code": result.returncode,
        "command": command,
        "cwd": cwd,
        "message": message,
        "blocked_reason": None,
        "log_summary": truncate_log(output),
    }


def cmd_agent_runtime_e2e(
        args, *, package_root, agent_runtime_e2e_platforms, agent_runtime_e2e_command_matrix,
        evaluate_agent_runtime_e2e_command,
):
    """Run real agent runtime E2E command matrix against e2e-test-project."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    target = Path(getattr(args, "target", None) or package_root / "project/e2e-test-project")
    timeout = getattr(args, "timeout", 120)
    requested_agents = set(getattr(args, "agent", None) or agent_runtime_e2e_platforms)
    matrix = [
        entry for entry in agent_runtime_e2e_command_matrix(target)
        if entry["agent"] in requested_agents
    ]
    if not target.exists():
        print(f"[FAIL] target not found: {target}")
        sys.exit(1)

    results = [
        evaluate_agent_runtime_e2e_command(entry, timeout=timeout)
        for entry in matrix
    ]

    print("=== Agent Runtime E2E Harness ===")
    print(f"Target: {target}")
    print(f"Timeout: {timeout}s")
    print("Schema: status in PASS/BLOCKED/FAIL; BLOCKED means known environment or agent-runtime configuration blocker.\n")

    for result in results:
        command = " ".join(str(part) for part in result["command"])
        print(f"[{result['status']}] {result['agent']}: {result['label']} (exit={result['exit_code']})")
        print(f"  cwd: {result['cwd']}")
        print(f"  command: {command}")
        print(f"  message: {result['message']}")
        if result["blocked_reason"]:
            print(f"  blocked_reason: {result['blocked_reason']}")
        if result["log_summary"]:
            print(f"  log_summary: {result['log_summary']}")

    pass_count = sum(1 for r in results if r["status"] == "PASS")
    blocked_count = sum(1 for r in results if r["status"] == "BLOCKED")
    fail_count = sum(1 for r in results if r["status"] == "FAIL")
    print(
        "\n=== Result: "
        f"pass={pass_count}, blocked={blocked_count}, fail={fail_count}, total={len(results)} ==="
    )
    if fail_count:
        print("ACTION: Fix unclassified harness/runtime failures above.")
        sys.exit(1)
    print("Agent runtime E2E harness completed; blocked entries are environment/configuration evidence, not harness failures.")
