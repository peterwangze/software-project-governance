"""Read execution packet documents, generate active packets and check their evidence."""
import governance_store
import json
import re


def _declared_packet_checks(result, packet_path, contract=None, *, plan_path_now, is_incomplete_task_status,
                            parse_current_active_tasks, read_document):
    """Select actual handoffs. Native local work has its own acceptance receipt."""
    from governance_readers import loop_state
    path = packet_path or plan_path_now().parent / "execution-packets.json"
    try:
        packets, _ = read_document(path, missing_ok=True)
        if not packets:
            return []
        tasks = {task["task_id"]: task for task in parse_current_active_tasks()
                 if is_incomplete_task_status(task.get("status", ""))}
        view = loop_state(plan_path_now().parent.parent)
        if view["state"] == "invalid":
            raise ValueError(view["message"])
        for unit in view["units"]:
            if unit["runtime_status"] != "completed":
                for key in (unit["flow_unit_id"], unit["task_id"]):
                    tasks.setdefault(key, {"task_id": key, "status": unit["runtime_status"]})
        selected = []
        for key, task in tasks.items():
            if key not in packets:
                continue
            packet = packets[key]
            if contract and contract != "acceptance_contract" and isinstance(packet, dict):
                required = packet.get("required_contracts", [])
                if isinstance(required, list) and contract not in required and contract not in packet:
                    continue
            result["required_tasks"].append(key)
            selected.append((task, packet))
        return selected
    except (ValueError, OSError) as exc:
        result["pass"] = False
        result["issues"].append(str(exc))
        return []


def _read_execution_packet_document(path, *, missing_ok=False):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if missing_ok:
            return {}, {}
        raise
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("execution packet root must be object")
    if "version" in data and (type(data["version"]) is not int or data["version"] != 1):
        raise ValueError(f"unsupported execution packet version: {data['version']!r}")
    packets = data.get("packets", data)
    if not isinstance(packets, dict):
        raise ValueError("packets must be object")
    from execution_packet import has_native_unit_identity

    for key, packet in packets.items():
        if not governance_store._TASK_ID_RE.fullmatch(key) and not has_native_unit_identity(key, packet):
            raise ValueError("execution packet map must be keyed by its task or native work unit")
    metadata = {k: v for k, v in data.items() if k != "packets"} if "packets" in data else {}
    return packets, metadata


def _load_execution_packets(path=None, *, packet_path_now, read_document=_read_execution_packet_document):
    packet_path = path or packet_path_now()
    try:
        packets, _ = read_document(packet_path)
        return packets, ""
    except FileNotFoundError:
        return {}, f"{packet_path} not found"
    except (OSError, ValueError) as exc:
        return {}, str(exc)


def _execution_packet_field_issues(packet, *, required_fields):
    """Structural field issues for one packet (shared validator — single
    definition of the EXECUTION_PACKET_REQUIRED_FIELDS semantics).

    Consumed by Check 18c (:func:`_validate_execution_packet`) and by the
    FEAT-011 governance-write-guard structural face — no second field
    semantics (FIX-292 dual-source lesson). Pure: no I/O.
    """
    issues = []
    if not isinstance(packet, dict):
        return ["packet must be object"]
    for field, expected_type in required_fields().items():
        value = packet.get(field)
        if not isinstance(value, expected_type):
            issues.append(f"{field} missing or invalid")
            continue
        if expected_type is str and not value.strip():
            issues.append(f"{field} must be non-empty")
        if expected_type is list and (
            not value or not all(isinstance(item, str) and item.strip() for item in value)
        ):
            issues.append(f"{field} must be non-empty string array")
    from execution_packet import OPTIONAL_CONTRACTS
    required = packet.get("required_contracts", [])
    if not isinstance(required, list) or not all(isinstance(name, str) and name in OPTIONAL_CONTRACTS for name in required):
        issues.append("required_contracts must list supported handoff contracts")
    else:
        issues.extend(f"missing required {name}" for name in required if name not in packet)
    # FEAT-092: optional advisory budget field — absent is legal (缺省不写),
    # present must be exactly {max_steps: positive int} (fail-closed on
    # illegal shapes so Check 18c / write-guard surface them).
    budget = packet.get("budget")
    if budget is not None:
        if (not isinstance(budget, dict)
                or set(budget) != {"max_steps"}
                or isinstance(budget.get("max_steps"), bool)
                or not isinstance(budget.get("max_steps"), int)
                or budget["max_steps"] <= 0):
            issues.append(
                "budget must be {max_steps: positive integer} (FEAT-092)")
    return issues

# FIX-319: `allowed_change_scope` is assembled from plan-tracker row text (see
# `build_execution_packet`), which carries markdown emphasis — `**NOT_RUN**`,
# `**契约层**`. Bold uses a PAIRED `**` delimiter, so the old substring
# predicate `"*" in scope.lower()` reported EVERY bold-bearing scope as
# `too broad` (systematic false positive: FIX-315 / FIX-317 / FEAT-031).
#
# Only `**` needs neutralising: the predicate inspects `*` and the whole-repo
# phrases, and `` ` `` / `_` carry no asterisk semantics (stripping them would
# change no verdict). A single `*` is deliberately NOT stripped — in a scope
# string it is far more often a glob (`src/*`, `*.py`, `*foo*`) than italic
# emphasis, so leaving it in place keeps the judgement on the strict side.
# The same decision covers italic emphasis: `*foo*` is NOT neutralised and is
# still reported `too broad` (FIX-319 boundary, restated by FIX-321).
#
# FIX-321 (review FIX-319 F-01): the pairing alone was not enough — a `**` run
# must also be a TRUE run boundary, otherwise `**/tests/**` falls inside one
# span, becomes ` /tests/ ` and PASSes, while its sibling `**/*.py` still FAILs
# (the `/` blocked the span) — an inconsistency, and exactly the laundering the
# predicate's contract forbids. So a `**` run counts as a bold delimiter only
# when it is a MAXIMAL run of exactly two stars that touches neither another
# `*` nor a path separator `/` on EITHER side — the glob tokens are `**/`,
# `/**` and `/**/`. A rejected span is left verbatim, its `*` survives, and the
# scope stays FAIL: an ambiguous boundary always resolves to the strict side.
_MARKDOWN_BOLD_SPAN_RE = re.compile(
    r"(?<![\*/])\*\*(?![\*/])(?P<inner>[^*]+?)(?<![\*/])\*\*(?![\*/])"
)

# Whole-repo phrases, anchored at a WORD START (and case-insensitive) so that
# natural language merely containing the sequence — `install files`,
# `as many files as` — is not misread as an unbounded scope. The start anchor
# alone is enough: the trailing part is left open so the old substring
# coverage of plurals (`any files`, `whole repository`) is preserved.
_TOO_BROAD_SCOPE_PHRASE_RE = re.compile(r"\b(?:any file|all files|whole repo)", re.IGNORECASE)


def _strip_markdown_bold_markers(text, *, span_pattern=_MARKDOWN_BOLD_SPAN_RE):
    """Neutralise PAIRED markdown bold markers, keeping the inner text.

    `**X**` becomes ` X ` — the inner text survives so a genuinely broad bold
    phrase (`**all files**`) is still caught. A single pass is sufficient: the
    inner group excludes `*` and the replacement only inserts the inner text
    plus spaces, so no new `**` pair can appear for a second pass to find.

    FIX-321: only spans whose two `**` runs are TRUE run boundaries are
    neutralised — a maximal two-star run that touches neither `*` nor `/` on
    either side (see `_MARKDOWN_BOLD_SPAN_RE`). Everything else is left
    verbatim, so a glob such as `**/tests/**` or `**/*.py` keeps its `*` and
    stays `too broad`. The slash may live inside the span (`**a/b**` is bold);
    only a slash glued to a delimiter disqualifies it. Ambiguity therefore
    fails closed instead of laundering a wildcard.

    Deliberate boundary (FIX-319, restated by FIX-321): single-`*` emphasis
    (`*foo*`) is NOT stripped either, because in a scope string a lone `*` is
    far more often a glob than italic emphasis — it is reported `too broad`.
    """
    return span_pattern.sub(lambda match: f" {match.group('inner')} ", text)


def _is_too_broad_scope_text(text, *, strip_markers, phrase_search):
    """True when an `allowed_change_scope` blob declares an unbounded scope.

    FIX-319: markdown bold is stripped first. A *surviving* `*` is a genuine
    wildcard — standalone (`*`), attached (`src/*`, `*.py`) or glob
    (`**/*.py`, `**/tests/**`, `/**`) — and stays `too broad`; stripping must
    never launder it. FIX-321 makes that guarantee mechanical rather than
    incidental: `_strip_markdown_bold_markers` refuses any span whose `**`
    runs are not true run boundaries, so a recursive-directory glob can no
    longer land inside one.
    """
    stripped = strip_markers(text)
    if "*" in stripped:
        return True
    return bool(phrase_search(stripped))


def _validate_execution_packet(task, packet, *, field_issues, broad_scope, placeholder_search):
    issues = field_issues(packet)
    if not isinstance(packet, dict):
        return issues  # HEAD-identical early exit: ["packet must be object"]
    if packet.get("task_id") and packet.get("task_id") != task["task_id"]:
        issues.append("task_id does not match active task")
    if any(not isinstance(packet.get(field), list) or not all(isinstance(value, str) for value in packet[field])
           for field in ("allowed_change_scope", "required_evidence", "done_definition")):
        return issues
    allowed_text = " ".join(packet["allowed_change_scope"])
    if allowed_text and broad_scope(allowed_text):
        issues.append("allowed_change_scope is too broad")
    for field in ("goal", "allowed_change_scope", "required_evidence", "next_commands", "done_definition"):
        values = packet.get(field, [])
        if isinstance(values, str):
            values = [values]
        if isinstance(values, list) and any(isinstance(value, str) and placeholder_search(value)
                                            for value in values):
            issues.append(f"{field} contains a placeholder")
    return issues


def generate_execution_packets(existing=None, *, task_ids=None, governance_dir=None, contracts=(),
                               quality_dimensions=(), plan_path_now, active_execution_packet_tasks,
                               is_incomplete_task_status, packet_builder, parse_current_active_tasks):
    from execution_packet import generate_packet_document
    existing = existing or {}
    if any(not isinstance(packet, dict) for packet in existing.values()):
        raise ValueError("each execution packet must be object")
    from functools import partial
    tasks = active_execution_packet_tasks()
    if task_ids:
        known = {task["task_id"] for task in tasks}
        tasks.extend(task for task in parse_current_active_tasks() if task["task_id"] in task_ids - known
                     and is_incomplete_task_status(task.get("status", "")))
    return generate_packet_document(tasks, task_ids=task_ids, existing=existing,
                                    governance_dir=governance_dir or plan_path_now().parent,
                                    build_packet=partial(packet_builder(), contracts=contracts,
                                                         quality_dimensions=quality_dimensions))


def check_execution_packets(packet_path=None, *, declared_packet_checks, validate_packet):
    result = {
        "required_tasks": [],
        "entries": [],
        "missing": [],
        "issues": [],
        "pass": True,
    }
    for task, packet in declared_packet_checks(result, packet_path, None):
        task_id = task["task_id"]
        issues = validate_packet(task, packet)
        status = "PASS" if not issues else "FAIL"
        if issues:
            result["pass"] = False
        result["entries"].append({"task_id": task_id, "status": status, "issues": issues})
    return result
