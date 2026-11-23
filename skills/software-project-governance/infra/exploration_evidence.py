"""Validate per-host exploration channel evidence, anchors and sample coverage."""

from dataclasses import dataclass
from datetime import date
from datetime import datetime
from pathlib import Path
import json
import re
import sys


@dataclass(frozen=True)
class ChannelRules:
    dated_adapters: tuple
    evidence_date: re.Pattern
    stale_days: int
    keys: tuple
    statuses: tuple
    manifests: tuple


QUOTE_SYNC_ADAPTER_MANIFESTS = (
    "adapters/claude/adapter-manifest.json",
    "adapters/codex/adapter-manifest.json",
    "adapters/gemini/adapter-manifest.json",
    "adapters/opencode/adapter-manifest.json",
    "adapters/dsh/adapter-manifest.json",
    "adapters/pi/adapter-manifest.json",
)


CONSULT_DRAW_MARKER = "生成≠咨询"


def _check_quote_sync_issues(*, package_root, consult_draw_marker, quote_sync_adapter_manifests):
    """FIX-432 (F-4 / F-A2): citation/paraphrase sync guard, fail-closed.

    Missing or unparsable canonical surfaces are issues, never silent skips.
    """
    issues = []
    bp_path = package_root / "skills/software-project-governance/references/behavior-protocol.md"
    skill_path = package_root / "skills/software-project-governance/SKILL.md"
    try:
        bp_text = bp_path.read_text(encoding="utf-8")
    except OSError:
        return [f"quote sync: {bp_path.as_posix()} unreadable (fail-closed)"]
    try:
        skill_text = skill_path.read_text(encoding="utf-8")
    except OSError:
        return [f"quote sync: {skill_path.as_posix()} unreadable (fail-closed)"]

    # F-4: M10.4 trigger citation must be verbatim-present in SKILL.md.
    m = re.search(
        r"任务级触发入口位于 SKILL\.md「Agent 分发路由」表后一行：「(.*?)」",
        bp_text,
    )
    if not m:
        issues.append(
            "quote sync: behavior-protocol.md M10.4 trigger-citation anchor line "
            "missing or reworded (fail-closed; update citation and guard regex together)"
        )
    elif m.group(1) not in skill_text:
        issues.append(
            "quote sync: M10.4 citation no longer verbatim in SKILL.md injection "
            "surface — sync the SKILL.md trigger line and the M10.4 citation in one change"
        )

    # F-A2: canonical consult-draw marker must live in M10.3 AND in all six notes.
    if consult_draw_marker not in bp_text:
        issues.append(
            f"quote sync: canonical consult-draw marker '{consult_draw_marker}' no "
            "longer present in behavior-protocol.md M10.3 (fail-closed; move the rule "
            "marker, the six adapter notes and this guard together)"
        )
    else:
        for rel in quote_sync_adapter_manifests:
            path = package_root / rel
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                note = (payload.get("exploration_channels") or {}).get("note", "")
            except (OSError, json.JSONDecodeError):
                issues.append(f"quote sync: {rel} unreadable or invalid JSON (fail-closed)")
                continue
            if consult_draw_marker not in note:
                issues.append(
                    f"quote sync: {rel} exploration_channels.note lost canonical marker "
                    f"'{consult_draw_marker}' (paraphrase drift, F-A2)"
                )
    return issues


EXPLORATION_CHANNEL_KEYS = ("discover", "inspect", "consult", "validate")


EXPLORATION_CHANNEL_STATUSES = ("native", "degraded", "unsupported")


CHANNEL_EVIDENCE_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


CHANNEL_ANCHOR_DATE_STRICT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


CHANNEL_DATE_ANCHOR_ADAPTERS = ("dsh",)


CHANNEL_EVIDENCE_STALE_DAYS = 180


def _anchor_date_or_none(value, *, channel_anchor_date_strict_re=CHANNEL_ANCHOR_DATE_STRICT_RE, timestamp_type=datetime):
    """A strict YYYY-MM-DD that is also a real calendar date, else ``None``."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not channel_anchor_date_strict_re.match(text):
        return None
    try:
        return timestamp_type.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def check_exploration_channels(root=None, *, package_root=None, calendar_date=date,
                               anchor_date_or_none=_anchor_date_or_none, channel_rules=None):
    """FEAT-088 (F-A3): exploration-channel evidence-form guard, fail-closed.

    Reads the six adapter manifests' ``exploration_channels`` blocks and
    judges, per the M10.3 four-channel vocabulary: structural conformance
    (channels present, status vocabulary, non-empty mapping/evidence) for
    every adapter, plus the dated-evidence-anchor requirement for the
    native declarations of enrolled adapters. Layer (b) probes are strictly
    read-only (anchor-document resolution). Returns a dict with ``issues``
    (gate-counted), ``advisories`` (WARN-only, never counted),
    ``adapters`` (per-adapter face), ``probe_layering`` (the honesty
    statement above, machine-restated) and ``pass``.
    """
    if package_root is None:
        package_root = Path(__file__).resolve().parents[3]
    if channel_rules is None:
        channel_rules = ChannelRules(
            dated_adapters=CHANNEL_DATE_ANCHOR_ADAPTERS, evidence_date=CHANNEL_EVIDENCE_DATE_RE,
            stale_days=CHANNEL_EVIDENCE_STALE_DAYS, keys=EXPLORATION_CHANNEL_KEYS,
            statuses=EXPLORATION_CHANNEL_STATUSES, manifests=QUOTE_SYNC_ADAPTER_MANIFESTS,
        )
    base = Path(root) if root is not None else package_root
    issues = []
    advisories = []
    faces = {}
    for rel in channel_rules.manifests:
        adapter_id = Path(rel).parent.name  # adapters/<id>/adapter-manifest.json
        face = {"manifest": rel, "dated_anchor_required":
                adapter_id in channel_rules.dated_adapters}
        faces[adapter_id] = face
        path = base / rel
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
            issues.append(
                f"exploration channels: {rel} unreadable or invalid JSON "
                f"({type(error).__name__}: {error}) (fail-closed)")
            face["error"] = True
            continue
        node = payload.get("exploration_channels")
        if not isinstance(node, dict):
            issues.append(
                f"exploration channels: {rel} has no exploration_channels "
                f"block (fail-closed)")
            face["error"] = True
            continue
        channels = node.get("channels")
        if not isinstance(channels, dict):
            issues.append(
                f"exploration channels: {rel} exploration_channels.channels "
                f"is missing or not an object (fail-closed)")
            face["error"] = True
            continue
        missing = [key for key in channel_rules.keys if key not in channels]
        extra = sorted(key for key in channels if key not in channel_rules.keys)
        if missing:
            issues.append(
                f"exploration channels: {rel} is missing channel "
                f"declaration(s) {missing} (M10.3 fixes exactly four)")
        if extra:
            issues.append(
                f"exploration channels: {rel} declares channel(s) unknown to "
                f"M10.3: {extra}")
        face["native_anchored"] = {}
        for key in channel_rules.keys:
            channel = channels.get(key)
            if not isinstance(channel, dict):
                if key in channels:
                    issues.append(
                        f"exploration channels: {rel} channels.{key} is not "
                        f"an object")
                continue
            status = channel.get("status")
            if status not in channel_rules.statuses:
                issues.append(
                    f"exploration channels: {rel} channels.{key}.status="
                    f"{status!r} is outside the M10.3 vocabulary "
                    f"{list(channel_rules.statuses)}")
            for field in ("mapping", "evidence"):
                value = channel.get(field)
                if not isinstance(value, str) or not value.strip():
                    issues.append(
                        f"exploration channels: {rel} channels.{key}.{field} "
                        f"is missing or empty")
            if status != "native":
                continue
            # ── dated-anchor face: layer (a) form + layer (b) probes ──
            verified_on = channel.get("verified_on")
            evidence_text = channel.get("evidence") or ""
            inline_dates = channel_rules.evidence_date.findall(evidence_text)
            anchor_date = anchor_date_or_none(verified_on)
            if verified_on is not None and anchor_date is None:
                issues.append(
                    f"exploration channels: {rel} channels.{key}.verified_on="
                    f"{verified_on!r} is not a valid YYYY-MM-DD calendar date")
            if anchor_date is not None and inline_dates \
                    and verified_on.strip() not in inline_dates:
                issues.append(
                    f"exploration channels: {rel} channels.{key} evidence "
                    f"prose date(s) {sorted(set(inline_dates))} disagree with "
                    f"verified_on={verified_on.strip()!r} — two forms of the "
                    f"same fact must not drift")
            if face["dated_anchor_required"] and anchor_date is None \
                    and not inline_dates:
                issues.append(
                    f"exploration channels: {rel} channels.{key} is declared "
                    f"native without a dated evidence anchor (F-A3): add "
                    f"verified_on (YYYY-MM-DD, optionally evidence_ref) or an "
                    f"inline date in the evidence text (the dated-E2E "
                    f"convention); or declare the channel degraded/unsupported "
                    f"honestly with a degraded_mode per EXP-03 — honest "
                    f"degradation is legal, capability masquerade is not")
            ref = channel.get("evidence_ref")
            if ref is not None and not isinstance(ref, str):
                issues.append(
                    f"exploration channels: {rel} channels.{key}.evidence_ref "
                    f"must be a repository-relative path string")
            elif isinstance(ref, str) and ref.strip():
                ref_norm = ref.strip().replace("\\", "/")
                ref_path = base / ref_norm
                if not ref_path.is_file():
                    issues.append(
                        f"exploration channels: {rel} channels.{key}."
                        f"evidence_ref '{ref_norm}' does not exist in the "
                        f"repository (dangling dated anchor)")
                elif anchor_date is not None:
                    # FIX-436 (F-C1, option b / DEC-317(2)): the corroboration
                    # below is a DOCUMENT-WIDE substring match — deliberately
                    # weaker than the §-level granularity the evidence prose
                    # may claim ("evidence_ref §3(c) saw …"). A heuristic
                    # §-neighborhood rule would fire definite FAILs on legal
                    # shapes (the false-alarm class this guard forbids), so
                    # the boundary is disclosed here and in
                    # probe_layering.feasible_probe; §-level positioning stays
                    # human-review territory.
                    try:
                        ref_text = ref_path.read_text(
                            encoding="utf-8", errors="replace")
                    except OSError:
                        ref_text = ""
                    if verified_on.strip() not in ref_text:
                        issues.append(
                            f"exploration channels: {rel} channels.{key} "
                            f"anchor date {verified_on.strip()!r} is not "
                            f"present in evidence_ref '{ref_norm}' — the dated "
                            f"claim is not corroborated by the cited document")
            face["native_anchored"][key] = {
                "verified_on": verified_on.strip()
                if isinstance(verified_on, str) else verified_on,
                "inline_date_only": anchor_date is None and bool(inline_dates),
                "age_days": ((calendar_date.today() - anchor_date).days
                             if anchor_date is not None else None),
            }
            if anchor_date is not None:
                age = (calendar_date.today() - anchor_date).days
                if age > channel_rules.stale_days:
                    advisories.append(
                        f"exploration channels: {rel} channels.{key} anchor "
                        f"is {age} days old (> {channel_rules.stale_days}): "
                        f"re-verify from a live session and re-date the anchor; "
                        f"if the channel is unavailable at runtime, record "
                        f"判定=受限 per EXP-03 (M10.2) — never mark offline "
                        f"knowledge as channel results")
    return {
        "issues": issues,
        "advisories": advisories,
        "adapters": faces,
        "dated_anchor_adapters": list(channel_rules.dated_adapters),
        "probe_layering": {
            "static_evidence_form": (
                "native declarations of enrolled adapters must carry dated "
                "anchors (this check, FAIL-able)"),
            "feasible_probe": (
                "evidence_ref existence + anchor-date corroboration in the "
                "cited document (read-only, DOCUMENT-WIDE substring match, "
                "NOT section-scoped — a date present anywhere in the cited "
                "document corroborates, so the §-level granularity claimed "
                "by evidence prose is human-review territory; FIX-436 "
                "F-C1/DEC-317(2); the only live checks a CLI process can "
                "honestly perform here)"),
            "not_probeable": (
                "host-session tool liveness (web_search / route_agent) is "
                "NOT probed and NOT claimed — harness-layer tools are "
                "outside a CLI process's reach; runtime drift is governed by "
                "the manifest degraded_mode + EXP-03 and by re-dating the "
                "anchor from a live session"),
        },
        "pass": not issues,
    }


EXPLORATION_SAMPLE_REPORTS = (
    "docs/research/feat-086-prospective-samples-2026-10-04.md",
    "docs/research/feat-087-channel-loss-samples-2026-10-05.md",
)


def check_exploration_sample_advisories(root, *, package_root, exploration_sample_reports):
    """FIX-436 (F-B3 / DEC-317): WARN-class presence advisory, never FAIL.

    Returns advisory strings (empty when every known sample report still
    carries an ``exploration:`` block). Callers MUST render these as
    non-counting advisories.
    """
    base = Path(root) if root is not None else package_root
    advisories = []
    for rel in exploration_sample_reports:
        try:
            text = (base / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            advisories.append(
                f"exploration samples: {rel} unreadable — cannot verify "
                f"the M10.2 exemplar exploration blocks (advisory, FIX-436 "
                f"F-B3/DEC-317)")
            continue
        if not re.search(r"(?m)^exploration:", text):
            advisories.append(
                f"exploration samples: {rel} carries no `exploration:` "
                f"block — the M10.2 schema's committed usage examples "
                f"should not lose their trace blocks (advisory, FIX-436 "
                f"F-B3/DEC-317; honest-vs-lazy omission stays "
                f"human-judged)")
    return advisories


def cmd_check_exploration_channels(args, *, check_exploration_channels):
    """CLI wrapper for the exploration-channel evidence-form guard (FEAT-088).

    The manifest machine-check face behind F-A3: dated-anchor form rules for
    native declarations of enrolled adapters, read-only anchor-document
    probes, WARN-only staleness advisories, and the probe-layering honesty
    statement (what this check can and cannot verify — it never claims to
    have probed host-session tool liveness).
    """
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    result = check_exploration_channels()
    print()
    print("=== Exploration-Channel Evidence-Form Check (FEAT-088 F-A3) ===")
    print(f"  Adapters requiring dated anchors: "
          f"{result['dated_anchor_adapters']}")
    if result["issues"]:
        print(f"  [FAIL] {len(result['issues'])} issue(s):")
        for issue in result["issues"]:
            print(f"    - {issue}")
    else:
        print("  [PASS] All channel declarations conform (structure for all "
              "six adapters; dated anchors on enrolled native declarations).")
    if result["advisories"]:
        print(f"  [ADVISORY] {len(result['advisories'])} staleness advisory(ies) "
              f"(WARN-only, not counted):")
        for advisory in result["advisories"]:
            print(f"    - {advisory}")
    print("\n  Probe layering (honesty statement):")
    for label, text in (result.get("probe_layering") or {}).items():
        print(f"    - {label}: {text}")
    if result["issues"] and getattr(args, "fail_on_issues", False):
        sys.exit(1)
