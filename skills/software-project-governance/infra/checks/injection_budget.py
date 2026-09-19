"""FEAT-039 / AUDIT-154 slice A-8 — injection-size budget gate.

AUDIT-154 §5 ("诉点 3"): the workflow ships quality gates but owns no budget
gate for its OWN injected surfaces — "预算不守护则瘦身必然回弹" (a slimming
pass with no guard rebounds). This module prices the ACTUAL LOADED SET, i.e. a
multi-file SUM over the surfaces a session really carries, so splitting a
surface across files can never evade the budget.

Four measurement decisions, each deliberate:

1. **Tokenizer (documented approximation — no external tokenizer dependency).**
   The host already prices context with a fixed-density heuristic
   (``@deepseek-ai/dsh-token-meter``: ``ceil(chars / 4)``); the report quotes it
   as ``tokens_host`` so the numbers stay comparable with DSH's own accounting.
   The BUDGET uses a three-class calibration instead: one token per CJK
   character, the host's 4-chars-per-token (rounded up) for ASCII, and 0.4
   token per non-CJK/non-ASCII character. A real BPE tokenizer spends ≈1 token
   per Han character, so pricing Chinese at 4 chars/token would under-report
   3-4x — blind exactly where the cost lives. Both numbers are reported per
   surface; only the calibrated one is budgeted.

2. **Canonical sources (not the dogfood instances) — one boundary definition.**
   Entry surfaces are priced from the ``governance-init.md`` Step 7 templates —
   the generation source ``check-entry-bootstrap-sync`` already guards — so the
   gate cannot be moved by editing one workspace's entry file. Live workspaces
   stay out of the budget (``check-entry-bootstrap-sync`` owns that consistency
   face). The block boundary is not re-derived here either: the slice is
   delegated to ``sync_entry_projection``, the module that renders the platform
   entry files, so the price and the shipped text cannot disagree (R1 of
   review-FEAT-039: a private boundary rule priced trailing spec prose into the
   thin pointer and kept the markdown fence markup in every template).

3. **Tiers.** ``resident`` = the static set injected before any user
   interaction (persona + the selected entry template + the dual-entry thin
   pointer + the agent-instructions payload); ``skill`` / ``command`` =
   on-demand progressive loads, measured for visibility but never summed into
   the resident number (AUDIT-154 §8 keeps the static budget separate from the
   bootstrap / tool-return budget, which FEAT-033 already enforces at 8192
   bytes — registered here rather than re-implemented).

4. **Hard gate (FEAT-050, DEC-211③ — slice-A window closed).** The threshold
   is 6K tokens (arch target: 4K). The slice-A advisory window existed because
   the standard/strict entry templates exceeded 6K; the FEAT-041 slimming pass
   brought all three profiles under it (EVD-1104 baseline: lightweight 4,216 /
   standard 5,694 / strict 5,966), so an over-budget resident set is now an
   issue + FAIL — future growth fails closed instead of rebounding silently.
   The ``skill``/``command`` tiers stay report-only: their budget face is a
   separate scheduled task and is NOT folded into the resident gate here.

Layer placement: this is a measurement + render leaf (``checks`` package), not
engine code. The ArchGuard ratchet forbids growing the engine's own LOC and
print calls, so the engine keeps only dispatch wiring (``bootstrap_aggregate``
and ``checks.projection`` precedent).
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

#: Default product root when no caller passes one: ``infra/checks/`` → the
#: repo/plugin root (four levels up) — the same resolution the sibling check
#: modules use, so a bare CLI invocation measures the installed package and
#: never the caller's cwd.
_DEFAULT_ROOT = Path(__file__).resolve().parents[4]

#: Resident budget, now a HARD gate (FEAT-050 / DEC-211③; arch target: 4K).
#: EVD-1104 post-slimming baseline: all three profiles fit under it.
INJECTION_BUDGET_TOKENS = 6000
INJECTION_BUDGET_DEFAULT_PROFILE = "lightweight"
INJECTION_BUDGET_PROFILES = ("lightweight", "standard", "strict")

#: Canonical Step 7 template labels (``commands/governance-init.md``). These
#: are the AMBIGUITY anchor only (a dropped or duplicated label must fail
#: closed); the block EXTENT comes from ``canonical_entry_templates`` — the
#: authority that renders the entry files — so this table never re-defines a
#: boundary.
ENTRY_TEMPLATE_MARKERS = {
    "lightweight": "**lightweight profile 注入模板**",
    "standard": "**standard profile 注入模板**",
    "strict": "**strict profile 注入模板**",
    "secondary-thin": "**secondary-thin 注入模板**",
}

#: Persona anchor: the ``prefix:`` block scalar of THIS plugin entry is the
#: rendered session persona; the anchor chain makes the coupling explicit and
#: fail-closed.
PERSONA_PLUGIN_NAME = "@deepseek-ai/dsh-persona"
PERSONA_PREFIX_FIRST_LINE = "You are a coding agent powered by"
PERSONA_ANCHOR_LOOKBEHIND = 4

#: Scope discriminator for the resolver dispatch (kept as data so the surface
#: table stays declarative and a new scope fails closed instead of guessing).
INJECTION_SURFACE_SCOPE_PERSONA_PREFIX = "persona-prefix"
INJECTION_SURFACE_SCOPE_TEMPLATE_BLOCK = "template-block"
INJECTION_SURFACE_SCOPE_FULL_FILE = "full-file"

INJECTION_BUDGET_SURFACES = (
    {
        "name": "persona",
        "path": "agent-presets/governance/agent.cordis.yml.template",
        "layer": "dsh-persona",
        "tier": "resident",
        "scope": INJECTION_SURFACE_SCOPE_PERSONA_PREFIX,
        "profile": None,
        "note": "persona prompt block (session-injected text; YAML host "
                "config and comments are not injected)",
    },
    {
        "name": "entry-template",
        "path": "commands/governance-init.md",
        "layer": "entry-primary",
        "tier": "resident",
        "scope": INJECTION_SURFACE_SCOPE_TEMPLATE_BLOCK,
        "profile_key": "profile",
        "profile_candidates": INJECTION_BUDGET_PROFILES,
        "note": "canonical Step 7 entry template (profile-selected)",
    },
    {
        "name": "secondary-entry-template",
        "path": "commands/governance-init.md",
        "layer": "entry-secondary-thin",
        "tier": "resident",
        "scope": INJECTION_SURFACE_SCOPE_TEMPLATE_BLOCK,
        "profile": "secondary-thin",
        "profile_candidates": ("secondary-thin",),
        "note": "thin-pointer projection — only present in dual-entry "
                "workspaces",
    },
    {
        "name": "agent-instructions",
        "path": "adapters/dsh/AGENTS.md.template",
        "layer": "dsh-agent-instructions",
        "tier": "resident",
        "scope": INJECTION_SURFACE_SCOPE_FULL_FILE,
        "profile": None,
        "note": "agent-instructions payload (whole file)",
    },
    {
        "name": "entry-skill",
        "path": "skills/software-project-governance/SKILL.md",
        "layer": "skill",
        "tier": "skill",
        "scope": INJECTION_SURFACE_SCOPE_FULL_FILE,
        "profile": None,
        "note": "entry skill — loaded when the skill is invoked",
    },
    {
        "name": "command-doc",
        "path": "commands/governance.md",
        "layer": "command",
        "tier": "command",
        "scope": INJECTION_SURFACE_SCOPE_FULL_FILE,
        "profile": None,
        "note": "governance command routing layer — the default payload of the "
                "/governance command entry (FEAT-038); the scenario/overview "
                "documents it defers to are NOT part of the default surface",
    },
)

#: Per-tier gate posture. ``hard`` counts into ``issues`` and can FAIL the
#: command; ``advisory`` is reported and can only yield the ADVISORY verdict;
#: ``report-only`` is measurement only. The resident tier flipped from
#: ``advisory`` to ``hard`` in FEAT-050 (DEC-211③): the EVD-1104 post-slimming
#: baseline holds all three profiles within budget, so an over-budget resident
#: set now blocks (any rebound fails closed). The skill tier stays
#: ``report-only`` — a separate budget face, not folded into the resident
#: gate (pinned by test).
BUDGET_TIER_POLICY = {
    "resident": {
        "description": "static injection surface (before any user interaction)",
        "gate": "hard",
    },
    "skill": {
        "description": "progressive load — entry skill",
        "gate": "report-only",
    },
    "command": {
        "description": "progressive load — command documentation",
        "gate": "report-only",
    },
}

#: FEAT-033 output-budget face registered (not re-implemented) here.
TOOL_RETURN_BUDGET_MODULE = "skills/software-project-governance/infra/bootstrap_aggregate.py"
TOOL_RETURN_BUDGET_CONSTANT = "MAX_JSON_BYTES"
TOOL_RETURN_BUDGET_ENFORCER = "_enforce_projection_budget"
TOOL_RETURN_BUDGET_EXPECTED = 8192

_CJK_CHAR_RE = re.compile(
    r"[\u3000-\u303f\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff00-\uffef]")


def count_cjk_chars(text):
    """Count CJK/full-width characters (the script-aware pricing arm)."""
    return sum(1 for char in text if _CJK_CHAR_RE.match(char))


def count_ascii_chars(text):
    """Count ASCII characters (priced at the host's 4-chars-per-token rate)."""
    return sum(1 for char in text if ord(char) < 128)


def estimate_surface_tokens_host(text):
    """Price text with the DSH host's fixed density heuristic (``chars / 4``).

    Mirrors ``@deepseek-ai/dsh-token-meter``'s ``CHARS_PER_TOKEN = 4`` so the
    report is comparable with the host's own context accounting.
    """
    return -(-len(text) // 4)


def surface_content_hash(text):
    """Drift anchor of a resolved surface: ``sha256[:16]`` of its own text.

    Token counts cannot see an equal-length content swap (same size, different
    bytes), so every surface also carries a fingerprint a baseline can pin; the
    first 16 hex characters are enough to detect drift and short enough for the
    table. An unresolved surface is already an explicit issue + FAIL and
    therefore carries no hash.
    """
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def estimate_surface_tokens(text):
    """Price text for the BUDGET (script-aware, never looser than the host).

    Three character classes: CJK = 1 token per character (what a BPE
    tokenizer actually spends on Han text); ASCII = the host's 4-chars-per-
    token, rounded up; everything else (Cyrillic, Greek, emoji, …) = 0.4 token
    per character, rounded up. Documented approximation — deliberately no
    external tokenizer dependency.
    """
    cjk = count_cjk_chars(text)
    ascii_chars = count_ascii_chars(text)
    other = len(text) - cjk - ascii_chars
    return cjk + -(-ascii_chars // 4) + -(-other * 2 // 5)


def tokenizer_calibration():
    """The documented tokenizer assumption (quoted verbatim in every report)."""
    return {
        "calibration": "CJK character = 1 token; ASCII = ceil(chars/4); "
                       "other = ceil(chars*2/5); no external tokenizer "
                       "dependency",
        "host_baseline": "DSH host meter: ceil(chars/4) "
                         "(reported as tokens_host for comparison)",
        "why": "Han text costs ≈1 token/char under a real BPE tokenizer, so "
               "the host density would under-report CJK surfaces 3-4x; the "
               "ASCII arm IS the host rate, so the calibrated number is never "
               "below the host number",
        "authority": "@deepseek-ai/dsh-token-meter CHARS_PER_TOKEN = 4",
    }


def find_marker_line(text, marker):
    """1-based line number of the single line containing ``marker``.

    Ambiguity is an error, not a guess: two matches (or none) raise, so a
    renamed/duplicated template heading can never silently re-slice a block.
    """
    hits = [index for index, line in enumerate(text.splitlines(), 1)
            if marker in line]
    if len(hits) != 1:
        raise ValueError(
            f"marker {marker!r} must appear on exactly one line, found "
            f"{len(hits)}")
    return hits[0]


def _extract_marked_block_range(text, start_line, end_line, max_lines=None):
    """De-indent and return the block strictly between two 1-based lines."""
    lines = text.splitlines()
    block = lines[start_line:end_line - 1]
    if not block or (max_lines is not None and len(block) > max_lines):
        return ""
    filled = [line for line in block if line.strip()]
    if not filled:
        return ""
    indent = min(len(line) - len(line.lstrip()) for line in filled)
    return "\n".join(
        (line[indent:] if line.strip() else "")
        for line in block
    ).strip("\n")


def extract_marked_block(text, start_marker, end_marker, max_lines=None):
    """Slice the block between two line markers, EXCLUDING the marker lines.

    Returns "" (fail-closed) when a marker is missing/ambiguous or the slice is
    absurd (end not after start, or longer than ``max_lines``) — pricing a
    wrong slice would be worse than reporting the surface as unresolved. The
    returned slice is de-indented and newline-stripped so the measurement is
    stable against formatting drift.
    """
    try:
        start = find_marker_line(text, start_marker)
        end = find_marker_line(text, end_marker)
    except ValueError:
        return ""
    if end <= start + 1:
        return ""
    return _extract_marked_block_range(text, start, end, max_lines=max_lines)


def extract_persona_prefix_from_template(text, display="<text>"):
    """Extract the injected persona prompt from the composition template.

    The persona is the ``prefix:`` block scalar of the ``persona`` plugin
    entry — the exact text the host injects. The block is anchored three ways
    (the persona plugin name appears within the lookbehind window, a
    ``config:`` line precedes it, and the body opens with the rendered
    persona's first sentence); any mismatch yields "" so the surface is
    reported unresolved instead of being priced from the wrong scalar. YAML
    comments above the entry are host metadata and are NOT injected, which is
    why the whole file must never be priced as the persona.
    """
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not re.match(r"^\s*prefix:\s*\|-?\s*$", line):
            continue
        window = lines[max(0, index - PERSONA_ANCHOR_LOOKBEHIND):index]
        if not any(PERSONA_PLUGIN_NAME in item for item in window):
            continue
        if not any(re.match(r"^\s*config:\s*$", item) for item in window):
            continue
        indent = len(line) - len(line.lstrip())
        end = None
        for probe in range(index + 1, len(lines)):
            candidate = lines[probe]
            if candidate.strip() and (len(candidate) - len(candidate.lstrip())) <= indent:
                end = probe
                break
        if end is None:
            end = len(lines)
        block = lines[index + 1:end]
        filled = [item for item in block if item.strip()]
        if not filled:
            continue
        base = min(len(item) - len(item.lstrip()) for item in filled)
        body = "\n".join(
            (item[base:] if item.strip() else "")
            for item in block
        ).strip("\n")
        if body.startswith(PERSONA_PREFIX_FIRST_LINE):
            return body
    print(f"  [WARN] {display}: persona prefix block not found — "
          f"anchors: {PERSONA_PLUGIN_NAME!r} + 'config:' + "
          f"{PERSONA_PREFIX_FIRST_LINE!r}")
    return ""


def canonical_entry_templates(text):
    """The Step 7 templates EXACTLY as the entry projection ships them.

    Single definition, deliberately delegated: ``sync_entry_projection`` is the
    module that renders the platform-native entry files and that
    ``check-entry-bootstrap-sync`` validates the live entries against, so its
    boundary rule — a block runs from its label to the LAST bare fence of the
    region, nested fences included — IS the injected text. The import is
    function-local (the ``checks.projection`` pattern) so the engine's
    cold-import face does not grow (ArchGuard R6).

    Fail-closed: a canonical source that cannot be parsed returns ``{}``; the
    caller then reports the surface unresolved instead of pricing a guess.
    """
    try:
        from sync_entry_projection import (
            CanonicalSourceError, extract_canonical_templates)
    except ImportError:  # pragma: no cover - infra/ is always importable
        return {}
    try:
        return extract_canonical_templates(text)
    except CanonicalSourceError:
        return {}


def load_injection_surface(surface, root=None):
    """Resolve one surface to the text that is actually injected.

    Fail-closed: a missing file, an unreadable source, an unknown scope, or a
    failed anchor resolution all return "" (never a fallback to another file
    or to a whole-file read). "" is reported as an explicit issue by
    ``check_injection_budget``.
    """
    root = Path(root) if root is not None else _DEFAULT_ROOT
    display = surface["path"]
    path = root / surface["path"]
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    scope = surface["scope"]
    if scope == INJECTION_SURFACE_SCOPE_FULL_FILE:
        return text
    if scope == INJECTION_SURFACE_SCOPE_PERSONA_PREFIX:
        return extract_persona_prefix_from_template(text, display=display)
    if scope == INJECTION_SURFACE_SCOPE_TEMPLATE_BLOCK:
        profile = surface.get("profile")
        marker = ENTRY_TEMPLATE_MARKERS.get(profile or "")
        if marker is None:
            return ""
        try:
            find_marker_line(text, marker)
        except ValueError:
            return ""
        # The extent is the canonical projection's own slice (label → closing
        # fence, nested fences included); an unparsable source yields "" here.
        return canonical_entry_templates(text).get(profile, "")
    return ""


def check_tool_return_budget(root=None):
    """FEAT-039 ②: register (not re-implement) the tool-return size budget.

    FEAT-033 already caps the ``governance-bootstrap`` projection at
    ``MAX_JSON_BYTES`` bytes. This face makes that an assertion on that
    module's own source: the constant is the expected 8192 and the enforcer
    ``_enforce_projection_budget`` is still the callable the projection
    payload is passed through. A silently widened budget therefore FAILs here
    instead of vanishing from the audit.
    """
    root = Path(root) if root is not None else _DEFAULT_ROOT
    path = root / TOOL_RETURN_BUDGET_MODULE
    result = {
        "path": TOOL_RETURN_BUDGET_MODULE,
        "constant": TOOL_RETURN_BUDGET_CONSTANT,
        "enforcer": TOOL_RETURN_BUDGET_ENFORCER,
        "expected_bytes": TOOL_RETURN_BUDGET_EXPECTED,
        "max_json_bytes": None,
        "enforced": False,
        "issues": [],
    }
    if not path.is_file():
        result["issues"].append(
            f"{TOOL_RETURN_BUDGET_MODULE}: missing — the governance-bootstrap "
            "output budget (FEAT-033) cannot be asserted")
        return result
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        result["issues"].append(
            f"{TOOL_RETURN_BUDGET_MODULE}: unreadable ({exc.__class__.__name__})")
        return result
    match = re.search(
        r"(?m)^%s\s*=\s*([0-9]+)\s*$" % re.escape(TOOL_RETURN_BUDGET_CONSTANT),
        source)
    if not match:
        result["issues"].append(
            f"{TOOL_RETURN_BUDGET_MODULE}: {TOOL_RETURN_BUDGET_CONSTANT} "
            "declaration not found")
        return result
    result["max_json_bytes"] = int(match.group(1))
    if result["max_json_bytes"] != TOOL_RETURN_BUDGET_EXPECTED:
        result["issues"].append(
            f"{TOOL_RETURN_BUDGET_CONSTANT} is {result['max_json_bytes']} "
            f"bytes, expected {TOOL_RETURN_BUDGET_EXPECTED} (FEAT-033)")
    result["enforced"] = bool(re.search(
        r"(?m)^def\s+%s\s*\(" % re.escape(TOOL_RETURN_BUDGET_ENFORCER), source))
    if not result["enforced"]:
        result["issues"].append(
            f"{TOOL_RETURN_BUDGET_MODULE}: {TOOL_RETURN_BUDGET_ENFORCER} "
            "not found — the output budget is declared but not enforced")
    return result


def set_injection_budget_surface_profiles(profile):
    """Bind every profile-selected surface to ``profile`` (surface copies only).

    The module table is never mutated: a shallow copy per surface keeps
    concurrent ``--profile`` invocations from leaking selection between runs.
    """
    resolved = []
    for surface in INJECTION_BUDGET_SURFACES:
        item = dict(surface)
        if item.get("profile_key") == "profile":
            item["profile"] = profile
        resolved.append(item)
    return tuple(resolved)


def normalize_token_budget(value):
    """Validate/clamp a token budget (fail-closed on non-integers)."""
    if value is None:
        return INJECTION_BUDGET_TOKENS
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"budget-tokens must be an integer, got {value!r}")
    if number <= 0:
        raise ValueError(f"budget-tokens must be positive, got {number}")
    return number


def injection_budget_tier_gate(tier):
    """Gate posture of a tier (unknown tier = hard: fail-closed)."""
    return BUDGET_TIER_POLICY.get(tier, {}).get("gate", "hard")


def check_injection_budget(root=None, profile=None, budget_tokens=None):
    """FEAT-039: price the actual injected set and verdict it against budget.

    Returns a structured report: per-surface bytes/chars/CJK/both token prices,
    tier aggregates, ``over_budget_tiers``, ``issues`` (only from hard-gated
    tiers) and one of the verdicts PASS / ADVISORY / FAIL. Surfaces that fail
    to resolve are explicit issues, never zero-priced silently.
    """
    root = Path(root) if root is not None else _DEFAULT_ROOT
    profile = profile or INJECTION_BUDGET_DEFAULT_PROFILE
    if profile not in INJECTION_BUDGET_PROFILES:
        raise ValueError(
            f"unknown profile {profile!r}; expected one of "
            f"{INJECTION_BUDGET_PROFILES}")
    budget = normalize_token_budget(budget_tokens)

    rows = []
    for surface in set_injection_budget_surface_profiles(profile):
        text = load_injection_surface(surface, root)
        cjk = count_cjk_chars(text)
        tokens = estimate_surface_tokens(text)
        rows.append({
            "name": surface["name"],
            "path": surface["path"],
            "layer": surface["layer"],
            "tier": surface["tier"],
            "scope": surface["scope"],
            "profile": surface.get("profile"),
            "note": surface.get("note", ""),
            "bytes": len(text.encode("utf-8")),
            "chars": len(text),
            "cjk": cjk,
            "tokens": tokens,
            "tokens_host": estimate_surface_tokens_host(text),
            "sha256_16": surface_content_hash(text),
            "budget_tokens": budget,
            "resolved": bool(text),
            "over_budget": bool(text) and tokens > budget,
            "status": ("unresolved" if not text
                       else "over" if tokens > budget else "ok"),
        })

    issues = []
    for row in rows:
        if not row["resolved"]:
            issues.append(
                f"{row['path']}: surface {row['name']!r} did not resolve to a "
                "measurable body (fail-closed) — the canonical source moved, "
                "was renamed, or an anchor broke")

    tiers = {}
    for name, policy in BUDGET_TIER_POLICY.items():
        rows_in_tier = [row for row in rows if row["tier"] == name]
        tokens = sum(row["tokens"] for row in rows_in_tier)
        tiers[name] = {
            "tier": name,
            "description": policy["description"],
            "gate": policy["gate"],
            "surfaces": [row["name"] for row in rows_in_tier],
            "bytes": sum(row["bytes"] for row in rows_in_tier),
            "cjk": sum(row["cjk"] for row in rows_in_tier),
            "tokens": tokens,
            "tokens_host": sum(row["tokens_host"] for row in rows_in_tier),
            "budget_tokens": budget,
            "over_budget": tokens > budget,
        }
    # Surfaces whose tier is not declared anywhere: never drop them silently.
    for row in rows:
        if row["tier"] not in BUDGET_TIER_POLICY:
            issues.append(
                f"{row['name']}: tier {row['tier']!r} is not declared in "
                "BUDGET_TIER_POLICY (fail-closed)")

    over_budget_tiers = [name for name, tier in tiers.items()
                         if tier["over_budget"]]
    # Only advisory/hard tiers can move the verdict; report-only tiers are
    # measurement (AUDIT-154 §8 keeps the static budget separate).
    gated_over_budget_tiers = [
        name for name in over_budget_tiers
        if injection_budget_tier_gate(name) != "report-only"
    ]

    for name, tier in tiers.items():
        if not tier["over_budget"]:
            continue
        headline = (f"'{name}' tier over budget: {tier['tokens']} > "
                    f"{budget} tokens by {tier['tokens'] - budget} "
                    f"(surfaces: {', '.join(tier['surfaces'])})")
        if injection_budget_tier_gate(name) == "hard":
            issues.append(headline + " — hard gate")
        elif injection_budget_tier_gate(name) == "advisory":
            tier["note"] = (headline + " — advisory-gated (reported, not "
                            "blocking)")
        else:
            tier["note"] = (headline + " — report-only (measured for "
                            "visibility; not part of the resident budget)")

    # The headline numbers are the resident tier's own. A policy table that no
    # longer declares ``resident`` must surface as an explicit issue — the
    # three-tier contract is fail-closed, so this is never a bare KeyError.
    resident_tier = tiers.get("resident")
    if resident_tier is None:
        issues.append(
            "BUDGET_TIER_POLICY declares no 'resident' tier — the headline "
            "resident number cannot be derived (fail-closed)")

    verdict = "FAIL" if issues else (
        "ADVISORY" if gated_over_budget_tiers else "PASS")
    return {
        "profile": profile,
        "budget_tokens": budget,
        "tokenizer": tokenizer_calibration(),
        "surfaces": rows,
        "tiers": tiers,
        "tokens": (resident_tier or {}).get("tokens", 0),
        "tokens_host": (resident_tier or {}).get("tokens_host", 0),
        "grand_total_tokens": sum(row["tokens"] for row in rows),
        "grand_total_tokens_host": sum(row["tokens_host"] for row in rows),
        "over_budget_tiers": over_budget_tiers,
        "gated_over_budget_tiers": gated_over_budget_tiers,
        "missing": sum(1 for row in rows if not row["resolved"]),
        "issues": issues,
        "verdict": verdict,
        "tool_return_budget": check_tool_return_budget(root),
    }


def format_budget_report(result, indent="  ", frame=None):
    """Render the per-surface budget table (acceptance ①: WHERE, HOW MUCH).

    ``frame`` prefixes every emitted line (the aggregate check draws inside a
    box); ``indent`` stays the report's own column offset either way, so the
    table alignment is identical in both renderings — the check section and the
    standalone subcommand cannot disagree about a number.

    The over-budget summary is printed as TWO labelled lines — gated (moves the
    verdict) and report-only (measurement) — because the verdict is decided by
    ``gated_over_budget_tiers`` alone (P2-1 of review-FEAT-039); every per-tier
    note below them is prefixed with its own gate posture.
    """
    prefix = "" if frame is None else frame
    lines = [
        f"{indent}Injection Budget (FEAT-039 / AUDIT-154 A-8) — profile="
        f"{result['profile']}, budget={result['budget_tokens']} tok",
        f"{indent}{'Surface':<26} {'Tier':<9} {'Bytes':>7} {'Chars':>7} "
        f"{'CJK':>6} {'Tok':>6} {'HostTok':>8} {'Budget':>7} "
        f"{'Status':<10} Sha256[:16]",
    ]
    for row in result["surfaces"]:
        lines.append(
            f"{indent}{row['name']:<26} {row['tier']:<9} {row['bytes']:>7} "
            f"{row['chars']:>7} {row['cjk']:>6} {row['tokens']:>6} "
            f"{row['tokens_host']:>8} {result['budget_tokens']:>7} "
            f"{row['status']:<10} {row['sha256_16'] or '-'}")
    for name, tier in result["tiers"].items():
        lines.append(f"{indent}TOTAL {name:<20} {tier['bytes']:>7} {'':>7} "
                     f"{tier['cjk']:>6} {tier['tokens']:>6} "
                     f"{tier['tokens_host']:>8}")
    lines.append(f"{indent}TOTAL {'all surfaces (diagnostic)':<20} "
                 f"{'':>7} {'':>7} {'':>6} {result['grand_total_tokens']:>6} "
                 f"{result['grand_total_tokens_host']:>8}")
    lines.append(f"{indent}Tokenizer: {result['tokenizer']['calibration']}")
    lines.append(f"{indent}Baseline:  {result['tokenizer']['host_baseline']}")
    gated_over = result["gated_over_budget_tiers"]
    report_only_over = [name for name in result["over_budget_tiers"]
                        if name not in gated_over]
    lines.append(f"{indent}Over budget — gated (moves the verdict): "
                 f"{', '.join(gated_over) or 'none'}")
    lines.append(f"{indent}Over budget — report-only (measurement): "
                 f"{', '.join(report_only_over) or 'none'}")
    for name, tier in result["tiers"].items():
        if tier["over_budget"] and tier.get("note"):
            lines.append(f"{indent}[{tier['gate'].upper()}] {tier['note']}")
    guard = result["tool_return_budget"]
    lines.append(f"{indent}Tool-return budget (registered, not "
                 f"re-implemented): {guard['constant']}="
                 f"{guard['max_json_bytes']} bytes, enforcer="
                 f"{guard['enforcer']} "
                 f"{'present' if guard['enforced'] else 'MISSING'}")
    if prefix:
        print("\n".join(prefix + line for line in lines))
    else:
        print("\n".join(lines))


def emit_check_section(indent="  ", frame="│  ", result=None):
    """Print the budget report inside the engine's Check 33 box.

    ``result`` lets the caller supply an already-computed report (the engine
    reaches this through its owned ``ROOT``); omitting it measures here.
    """
    result = result if result is not None else check_injection_budget()
    format_budget_report(result, indent=indent, frame=frame)
    return result


def add_arguments(parser):
    """FEAT-039 CLI surface (engine wires only — ArchGuard R1/R4 discipline)."""
    parser.add_argument(
        "--budget-tokens", type=int, default=None,
        help=f"Token budget for the resident injection tier "
             f"(default {INJECTION_BUDGET_TOKENS}; resident hard gate "
             f"(FEAT-050), arch target 4K)")
    parser.add_argument(
        "--profile", default=INJECTION_BUDGET_DEFAULT_PROFILE,
        choices=list(INJECTION_BUDGET_PROFILES),
        help="Which canonical entry template to price "
             f"(default {INJECTION_BUDGET_DEFAULT_PROFILE})")
    parser.add_argument("--format", default="text", choices=["text", "json"],
                        help="Report format (default text)")
    parser.add_argument(
        "--fail-on-issues", action="store_true",
        help="Exit with non-zero code when the budget is violated by a "
             "hard-gated tier or a surface fails to resolve")


def cmd_check_injection_budget(args):
    """FEAT-039 / AUDIT-154 slice A-8: injection-size budget gate.

    Exit contract mirrors the other ``check-*`` commands: the verdict is always
    printed and ``--fail-on-issues`` turns a FAIL verdict into exit 1 — the
    CI-wirable form. CI wiring (no new CI system): every commit/PR already runs
    the ``check-governance`` aggregate, which prints this report inside Check
    33; a pipeline that needs its own exit code runs this subcommand with
    ``--fail-on-issues``, and a job that needs to assert values reads
    ``--format json`` (``verdict`` / ``tiers``).
    """
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    profile = (getattr(args, "profile", None)
               or INJECTION_BUDGET_DEFAULT_PROFILE)
    raw_budget = getattr(args, "budget_tokens", None)
    budget = normalize_token_budget(raw_budget)
    if raw_budget is None:
        print(f"\n  Budget: default {budget} tokens "
              f"(resident hard gate; arch target 4K)")
    else:
        print(f"\n  Budget: {budget} tokens (explicit --budget-tokens)")
    print("\n=== Injection Budget Check (FEAT-039 / AUDIT-154 A-8) ===")
    result = check_injection_budget(profile=profile, budget_tokens=budget)
    if getattr(args, "format", "text") == "json":
        print(json.dumps({k: v for k, v in result.items()
                          if k != "issues"}, ensure_ascii=False, indent=2))
    else:
        format_budget_report(result, indent="  ")
    if result["issues"]:
        print(f"\n  Result: FAILED — {len(result['issues'])} issue(s)")
        for issue in result["issues"][:20]:
            print(f"    - {issue}")
        if len(result["issues"]) > 20:
            print(f"    ... and {len(result['issues']) - 20} more")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
    elif result["verdict"] == "ADVISORY":
        # Unreachable while every non-report-only tier is ``hard`` (an
        # over-budget hard tier lands in ``issues`` → FAIL above); kept as the
        # data-driven arm for a future ``advisory`` policy row, so an ADVISORY
        # verdict can never fall through to the PASSED line (fail-open text).
        resident = result["tiers"].get("resident") or {}
        if resident.get("over_budget"):
            print(f"\n  Result: ADVISORY — resident set {resident['tokens']} tok "
                  f"> budget {result['budget_tokens']} tok "
                  f"(+{resident['tokens'] - result['budget_tokens']}); "
                  "gated over-budget tiers: "
                  f"{', '.join(result['gated_over_budget_tiers'])}")
        else:
            print(f"\n  Result: ADVISORY — resident set "
                  f"{resident.get('tokens', 0)} tok <= budget "
                  f"{result['budget_tokens']} tok, but these tiers exceed it "
                  "and are reported as reduction candidates; gated "
                  "over-budget tiers: "
                  f"{', '.join(result['gated_over_budget_tiers'])}")
    else:
        print(f"\n  Result: PASSED — resident injection set {result['tokens']} "
              f"tok <= budget {result['budget_tokens']} tok")
    print()
