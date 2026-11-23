"""Compare the published readiness matrix and first-session measurements with adapter facts."""

from dataclasses import dataclass
from pathlib import Path
import json
import re


@dataclass(frozen=True)
class ReadinessPlatforms:
    mainstream_agent_adapters: list
    agent_ids: list
    research_only_ids: list


def _load_adapter_manifest(adapter_dir, *, display_path):
    manifest_path = adapter_dir / "adapter-manifest.json"
    if not manifest_path.exists():
        return None, [f"{display_path(manifest_path)}: missing adapter manifest"]
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8")), []
    except json.JSONDecodeError as exc:
        return None, [f"{display_path(manifest_path)}: invalid JSON: {exc}"]


RUNTIME_READINESS_MATRIX_PATH = Path(__file__).resolve().parents[3] / "docs/requirements/runtime-readiness-matrix-0.43.0.md"


RUNTIME_MATRIX_AGENT_IDS = ["claude", "codex", "gemini", "opencode", "dsh", "pi", "cursor", "copilot"]


RUNTIME_MATRIX_RESEARCH_ONLY_IDS = ["cursor", "copilot"]


FIRST_SESSION_MEASUREMENT_PATH = Path(__file__).resolve().parents[3] / "docs/requirements/first-session-measurement-0.43.0.md"


FIRST_SESSION_MEASUREMENT_ALLOWED_STATUSES = {"PASS", "BLOCKED", "NOT_MEASURED"}


def _parse_markdown_table_rows(content, section_title=None):
    if section_title:
        marker = f"## {section_title}"
        start = content.find(marker)
        if start == -1:
            return []
        next_start = content.find("\n## ", start + len(marker))
        content = content[start:next_start if next_start != -1 else len(content)]
    rows = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line.startswith("|") or "---" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) >= 2:
            rows.append(cells)
    return rows


def _matrix_status_for_manifest(manifest):
    runtime_e2e = manifest.get("runtime_e2e", {}) if isinstance(manifest, dict) else {}
    full = runtime_e2e.get("full_e2e_verified")
    agent_status = runtime_e2e.get("agent_runtime_e2e", {}).get("status")
    if full is True and agent_status == "passed":
        return "PASS"
    if agent_status == "blocked":
        return "BLOCKED"
    return "DEGRADED"


def check_runtime_readiness_matrix(
        root, *, package_root, display_path, load_adapter_manifest, matrix_status_for_manifest,
        parse_markdown_table_rows, platforms,
):
    """FIX-106: public runtime/readiness matrix must match adapter facts."""
    root = root or package_root
    matrix_path = root / "docs/requirements/runtime-readiness-matrix-0.43.0.md"
    failures = []
    if not matrix_path.exists():
        return [f"{display_path(matrix_path, root)}: missing public runtime/readiness matrix"]

    content = matrix_path.read_text(encoding="utf-8")
    rows = parse_markdown_table_rows(content, section_title="Summary")
    if not rows:
        failures.append(f"{display_path(matrix_path, root)}: missing `## Summary` runtime/readiness table")
    matrix = {}
    for cells in rows:
        agent_id = cells[0].lower().strip("`* ")
        if agent_id in platforms.agent_ids:
            matrix[agent_id] = " | ".join(cells)

    for agent_id in platforms.agent_ids:
        if agent_id not in matrix:
            failures.append(f"{display_path(matrix_path, root)}: missing matrix row for {agent_id}")

    for adapter_id in platforms.mainstream_agent_adapters:
        adapter_dir = root / "adapters" / adapter_id
        manifest, manifest_failures = load_adapter_manifest(adapter_dir)
        failures.extend(manifest_failures)
        if not manifest:
            continue
        row = matrix.get(adapter_id, "")
        expected_status = matrix_status_for_manifest(manifest)
        if expected_status not in row:
            failures.append(
                f"{display_path(matrix_path, root)}: {adapter_id} row must contain {expected_status} from adapter manifest"
            )
        runtime_e2e = manifest.get("runtime_e2e", {})
        version_command = runtime_e2e.get("version_command", "")
        if version_command and version_command not in row:
            failures.append(
                f"{display_path(matrix_path, root)}: {adapter_id} row missing version command `{version_command}`"
            )
        agent_runtime = runtime_e2e.get("agent_runtime_e2e", {})
        blocked_reason = agent_runtime.get("blocked_reason", "")
        if expected_status == "BLOCKED" and blocked_reason:
            reason_token = blocked_reason.split(";")[0].split(".")[0].strip()
            if reason_token and reason_token not in row:
                failures.append(
                    f"{display_path(matrix_path, root)}: {adapter_id} BLOCKED row missing blocked reason from manifest"
                )
        capabilities = manifest.get("runtime_capabilities", {})
        closure = capabilities.get("workflow_closure", {})
        closure_status = closure.get("status", "").upper()
        if closure_status and closure_status not in row:
            failures.append(
                f"{display_path(matrix_path, root)}: {adapter_id} row missing workflow_closure status {closure_status}"
            )

    for agent_id in platforms.research_only_ids:
        row = matrix.get(agent_id, "")
        if "RESEARCH_ONLY" not in row or "NOT_RUNTIME_VERIFIED" not in row:
            failures.append(
                f"{display_path(matrix_path, root)}: {agent_id} row must be RESEARCH_ONLY and NOT_RUNTIME_VERIFIED"
            )
        forbidden = ["FULL_E2E", "UNIVERSAL", "OFFICIAL_APPROVAL", "MARKETPLACE_APPROVAL"]
        for token in forbidden:
            if token in row:
                failures.append(f"{display_path(matrix_path, root)}: {agent_id} row overclaims {token}")

    required_boundary_tokens = [
        "No official approval",
        "No marketplace approval",
        "No universal/full runtime support",
        "RISK-036 remains open",
    ]
    for token in required_boundary_tokens:
        if token not in content:
            failures.append(f"{display_path(matrix_path, root)}: missing no-overclaim boundary token `{token}`")

    return failures


def check_first_session_measurement(
        root, *, package_root, first_session_measurement_allowed_statuses, display_path,
        parse_markdown_table_rows,
):
    """FIX-107: separate local demo proof from external first-session measurement."""
    root = root or package_root
    measurement_path = root / "docs/requirements/first-session-measurement-0.43.0.md"
    failures = []
    if not measurement_path.exists():
        return [f"{display_path(measurement_path, root)}: missing first-session measurement evidence"]

    content = measurement_path.read_text(encoding="utf-8")
    rows = parse_markdown_table_rows(content, section_title="Measurement Status")
    if not rows:
        failures.append(f"{display_path(measurement_path, root)}: missing `## Measurement Status` table")
    measurement = {}
    for cells in rows:
        signal = cells[0].lower().strip("`* ")
        if signal in {"local_demo", "external_pilot", "release_note_boundary"}:
            measurement[signal] = cells

    for signal in ("local_demo", "external_pilot", "release_note_boundary"):
        if signal not in measurement:
            failures.append(f"{display_path(measurement_path, root)}: missing measurement row for {signal}")

    local_row = " | ".join(measurement.get("local_demo", []))
    if "PASS" not in local_row or "LOCAL_DEMO_ONLY" not in local_row:
        failures.append(f"{display_path(measurement_path, root)}: local_demo row must be PASS and LOCAL_DEMO_ONLY")
    if "first-run-demo --assert-snapshot" not in local_row:
        failures.append(f"{display_path(measurement_path, root)}: local_demo row missing first-run-demo command")

    external_cells = measurement.get("external_pilot", [])
    external_status = external_cells[1].upper() if len(external_cells) > 1 else ""
    external_row = " | ".join(external_cells)
    external_lower = external_row.lower()
    if external_status not in first_session_measurement_allowed_statuses:
        failures.append(
            f"{display_path(measurement_path, root)}: external_pilot status must be one of "
            f"{sorted(first_session_measurement_allowed_statuses)}"
        )
    if external_status == "PASS":
        local_demo_tokens = ("LOCAL_DEMO_ONLY", "first-run-demo", "local demo")
        if any(token.lower() in external_lower for token in local_demo_tokens):
            failures.append(
                f"{display_path(measurement_path, root)}: external_pilot PASS cannot use local demo evidence"
            )
        if "4/5" not in external_row and "5/5" not in external_row:
            failures.append(
                f"{display_path(measurement_path, root)}: external_pilot PASS requires at least 4/5 measured users"
            )
        pass_required_tokens = [
            ("external pilot", "external pilot evidence"),
            ("Delivery Trust Snapshot", "Delivery Trust Snapshot reached"),
            ("within 5 minutes", "within 5 minutes"),
            ("trust signal", "trust signal named"),
            ("evidence", "evidence location"),
        ]
        for token, label in pass_required_tokens:
            if token.lower() not in external_lower:
                failures.append(
                    f"{display_path(measurement_path, root)}: external_pilot PASS requires {label}"
                )
        if "setup" not in external_lower and "resume" not in external_lower:
            failures.append(
                f"{display_path(measurement_path, root)}: external_pilot PASS requires setup or resume path"
            )
        over_five = [
            match.group(0)
            for match in re.finditer(r"\b([6-9]|[1-9]\d+)\s+minutes?\b", external_lower)
        ]
        if over_five:
            failures.append(
                f"{display_path(measurement_path, root)}: external_pilot PASS exceeds five-minute limit: {', '.join(over_five)}"
            )
    elif external_status == "NOT_MEASURED":
        if "0/5" not in external_row:
            failures.append(f"{display_path(measurement_path, root)}: NOT_MEASURED external_pilot row must state 0/5 measured")
        if "4/5" not in external_row or "within 5 minutes" not in external_row:
            failures.append(
                f"{display_path(measurement_path, root)}: NOT_MEASURED external_pilot row must preserve 4/5 within 5 minutes target"
            )
    elif external_status == "BLOCKED" and "blocked" not in external_lower:
        failures.append(f"{display_path(measurement_path, root)}: BLOCKED external_pilot row requires blocked reason")

    release_row = " | ".join(measurement.get("release_note_boundary", []))
    if "PASS" not in release_row or "TEXT_GUARD" not in release_row:
        failures.append(f"{display_path(measurement_path, root)}: release_note_boundary row must be PASS and TEXT_GUARD")

    required_tokens = [
        "Do not convert local demo PASS into external pilot PASS",
        "local_demo=PASS",
        "external_pilot=NOT_MEASURED",
        "No official approval",
        "No marketplace approval",
        "No universal/full runtime support",
        "RISK-036 remains open",
    ]
    for token in required_tokens:
        if token not in content:
            failures.append(f"{display_path(measurement_path, root)}: missing first-session boundary token `{token}`")

    return failures
