"""Validate mainstream host loading declarations and evidence-level claims in documentation."""

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class LoadingClaimBoundaries:
    forbidden_claim_terms: list
    forbidden_overclaims: list
    tier2: list


@dataclass(frozen=True)
class HostLoadingRules:
    adapters: dict
    readme_tokens: list
    required_docs: list
    requirements_tokens: list
    tier1: list
    tier2: list


MAINSTREAM_AGENT_LOADING_DOC_PATH = Path(__file__).resolve().parents[3] / "docs/requirements/mainstream-agent-loading-0.47.0.md"


MAINSTREAM_AGENT_LOADING_REQUIRED_DOCS = [
    "README.md",
    "adapters/claude/README.md",
    "adapters/codex/README.md",
    "adapters/gemini/README.md",
    "adapters/opencode/README.md",
    "adapters/dsh/README.md",
    "adapters/pi/README.md",
    "docs/requirements/mainstream-agent-loading-0.47.0.md",
]


MAINSTREAM_AGENT_LOADING_TIER1 = [
    "Codex",
    "Claude Code",
    "Gemini CLI",
    "opencode",
    "DeepSeek Harness",
    "Pi",
]


MAINSTREAM_AGENT_LOADING_TIER2 = [
    "Cursor",
    "GitHub Copilot coding agent",
    "Cline",
    "Windsurf/Cascade",
    "Kiro",
]


MAINSTREAM_AGENT_LOADING_ADAPTERS = {
    "claude": {
        "display": "Claude Code",
        "path": "adapters/claude/README.md",
        "tokens": [
            "Tier 1",
            "Load",
            "Verify",
            "Boundary",
            "skills/software-project-governance/SKILL.md",
            "python adapters/claude/launch.py",
            "check-agent-adapters",
            "check-agent-adapters --runtime",
        ],
    },
    "codex": {
        "display": "Codex",
        "path": "adapters/codex/README.md",
        "tokens": [
            "Tier 1",
            "Load",
            "Verify",
            "Boundary",
            "skills/software-project-governance/SKILL.md",
            ".codex-plugin/plugin.json",
            ".agents/plugins/marketplace.json",
            "python adapters/codex/launch.py",
            "check-agent-adapters",
            "agent-runtime-e2e --agent codex",
        ],
    },
    "gemini": {
        "display": "Gemini CLI",
        "path": "adapters/gemini/README.md",
        "tokens": [
            "Tier 1",
            "Load",
            "Verify",
            "Boundary",
            "GEMINI.md",
            "skills/software-project-governance/SKILL.md",
            "python adapters/gemini/launch.py",
            "gemini-auth-preflight",
            "agent-runtime-e2e --agent gemini",
        ],
    },
    "opencode": {
        "display": "opencode",
        "path": "adapters/opencode/README.md",
        "tokens": [
            "Tier 1",
            "Load",
            "Verification",
            "Boundary",
            "AGENTS.md",
            "skills/software-project-governance/SKILL.md",
            "python adapters/opencode/launch.py",
            "opencode-provider-preflight",
            "agent-runtime-e2e --agent opencode",
        ],
    },
    "dsh": {
        "display": "DeepSeek Harness",
        "path": "adapters/dsh/README.md",
        "tokens": [
            "Tier 1",
            "加载模型",
            "验证",
            "能力边界",
            "skills/software-project-governance/SKILL.md",
            "python adapters/dsh/launch.py",
            "check-agent-adapters",
        ],
    },
    "pi": {
        "display": "Pi",
        "path": "adapters/pi/README.md",
        "tokens": [
            "Tier 1",
            "Load",
            "Verify",
            "Boundary",
            "AGENTS.md",
            "skills/software-project-governance/SKILL.md",
            "python adapters/pi/launch.py",
            "check-agent-adapters",
            "agent-runtime-e2e --agent pi",
        ],
    },
}


MAINSTREAM_AGENT_LOADING_README_TOKENS = [
    "Mainstream Agent Loading",
    "Tier 1 loading guide",
    "Tier 2 compatibility and research rows",
    "docs/requirements/mainstream-agent-loading-0.47.0.md",
    "check-agent-adapters --runtime",
]


MAINSTREAM_AGENT_LOADING_REQUIREMENTS_TOKENS = [
    "Mainstream Agent Loading Readiness 0.47.0",
    "Official Surface Findings",
    "Current Repository Facts",
    "FIX-122",
    "check-mainstream-agent-loading --fail-on-issues",
    "No-Overclaim Boundary",
    "RESEARCH_ONLY / NOT_RUNTIME_VERIFIED",
]


MAINSTREAM_AGENT_LOADING_BOUNDARY_TOKENS = [
    "No official approval",
    "No marketplace approval",
    "No universal/full runtime support",
    "No Codex Desktop marketplace-management E2E PASS",
    "RISK-036 remains open",
]


MAINSTREAM_AGENT_LOADING_FORBIDDEN_CLAIM_TERMS = [
    "official approval",
    "marketplace approval",
    "universal/full runtime support",
    "universal runtime support",
    "full runtime support",
    "codex desktop marketplace-management e2e pass",
    "desktop marketplace e2e pass",
]


MAINSTREAM_AGENT_LOADING_FORBIDDEN_OVERCLAIMS = [
    "tier 2 runtime pass",
    "tier 2 runtime passed",
    "tier 2 runtime verified",
    "tier 2 target-cwd e2e pass",
    "tier 2 target-cwd e2e passed",
    "cursor runtime pass",
    "github copilot coding agent runtime pass",
    "copilot coding agent runtime pass",
    "cline runtime pass",
    "windsurf/cascade runtime pass",
    "windsurf runtime pass",
    "cascade runtime pass",
    "kiro runtime pass",
    "official approval granted",
    "officially approved",
    "marketplace approval granted",
    "marketplace approved",
    "universal runtime support is verified",
    "universal runtime support verified",
    "full runtime support is verified",
    "full runtime support verified",
    "universal/full runtime support is verified",
    "universal/full runtime support verified",
    "codex desktop marketplace-management e2e pass",
    "codex desktop marketplace-management e2e passed",
    "desktop marketplace e2e pass",
    "desktop marketplace e2e passed",
    "automatic best-tool selection",
    "automatically selects the best tool",
    "catalog runtime pass",
    "catalog runtime passed",
    "catalog entry runtime pass",
    "catalog entry runtime passed",
    "1.0.0 production-ready",
    "risk-036 closed",
]


def _mainstream_loading_line_has_safe_negation(
        lines, index, phrase, *, mainstream_agent_loading_forbidden_claim_terms,
        mainstream_agent_loading_forbidden_overclaims,
):
    line = lines[index]
    lower_line = line.lower()
    phrase_lower = phrase.lower()
    phrase_positions = [match.start() for match in re.finditer(re.escape(phrase_lower), lower_line)]
    if not phrase_positions:
        return False
    clause_separators = ";；.!?！？|:："
    list_item_separators = ",，、;" + clause_separators
    positive_claim_markers = (
        " exists",
        " exist",
        " is ",
        " are ",
        " available",
        " verified",
        " granted",
        " approved",
        " supported",
        " passed",
        " enabled",
        " for all",
        " across all",
        " production-ready",
        " ready",
    )
    strong_negation_markers = (
        "does not claim",
        "do not claim",
        "does not prove",
        "do not prove",
        "does not mean",
        "do not mean",
        "doesn't mean",
        "don't mean",
        "is not a claim of",
        "it is not a claim of",
        "not a claim of",
        "is not evidence of",
        "are not evidence of",
        "not evidence of",
        "without",
    )
    weak_negation_markers = (
        "not",
        "no",
    )

    def list_negation_covers_phrase(phrase_index):
        prefix = lower_line[:phrase_index]
        marker_hits = []
        for marker in strong_negation_markers + weak_negation_markers:
            marker_start = prefix.rfind(marker)
            if marker_start != -1:
                marker_hits.append((marker_start, marker_start + len(marker), marker))
        if not marker_hits:
            return False

        _marker_start, marker_end, marker = max(marker_hits, key=lambda hit: (hit[1], hit[0]))
        candidate_prefix = lower_line[marker_end:phrase_index]
        reduced_prefix = candidate_prefix
        for claim_term in sorted(mainstream_agent_loading_forbidden_claim_terms, key=len, reverse=True):
            reduced_prefix = reduced_prefix.replace(claim_term, "")
        for overclaim in sorted(mainstream_agent_loading_forbidden_overclaims, key=len, reverse=True):
            reduced_prefix = reduced_prefix.replace(overclaim, "")
        reduced_prefix = re.sub(r"\b(and|or)\b", "", reduced_prefix)
        reduced_prefix = re.sub(r"[\s,，、/]+", "", reduced_prefix)
        if reduced_prefix:
            return False

        phrase_end = phrase_index + len(phrase_lower)
        suffix_end_candidates = [
            lower_line.find(separator, phrase_end)
            for separator in list_item_separators
            if lower_line.find(separator, phrase_end) != -1
        ]
        suffix_end = min(suffix_end_candidates) if suffix_end_candidates else len(lower_line)
        local_suffix = lower_line[phrase_end:suffix_end]
        strong_negation = marker in strong_negation_markers
        if not strong_negation and any(marker in f" {local_suffix} " for marker in positive_claim_markers):
            return False
        reduced_suffix = local_suffix
        for claim_term in sorted(mainstream_agent_loading_forbidden_claim_terms, key=len, reverse=True):
            reduced_suffix = reduced_suffix.replace(claim_term, "")
        for overclaim in sorted(mainstream_agent_loading_forbidden_overclaims, key=len, reverse=True):
            reduced_suffix = reduced_suffix.replace(overclaim, "")
        if strong_negation:
            reduced_suffix = re.sub(
                r"\b(is|are|was|were|be|been|being|status|claim|proof|evidence|"
                r"verified|granted|approved|supported|ready|available|passed)\b",
                "",
                reduced_suffix,
            )
        reduced_suffix = re.sub(r"\b(and|or)\b", "", reduced_suffix)
        reduced_suffix = re.sub(r"[\s,，、/]+", "", reduced_suffix)
        return not reduced_suffix

    safe_occurrences = 0
    for phrase_index in phrase_positions:
        clause_start = max((lower_line.rfind(separator, 0, phrase_index) for separator in clause_separators), default=-1) + 1
        clause_end_candidates = [
            lower_line.find(separator, phrase_index + len(phrase_lower))
            for separator in clause_separators
            if lower_line.find(separator, phrase_index + len(phrase_lower)) != -1
        ]
        clause_end = min(clause_end_candidates) if clause_end_candidates else len(lower_line)
        local_clause = lower_line[clause_start:clause_end]
        local_prefix = lower_line[clause_start:phrase_index]
        if any(marker in local_prefix for marker in strong_negation_markers):
            safe_occurrences += 1
            continue
        if re.search(r"\bnot(?:\s+[a-z0-9/-]+){0,3}\s+$", local_prefix):
            safe_occurrences += 1
            continue
        if any(
            marker in local_clause
            for marker in (
                f"no {phrase_lower}",
                f"not {phrase_lower}",
                f"do not claim {phrase_lower}",
                f"does not claim {phrase_lower}",
                f"without {phrase_lower}",
                f"avoid {phrase_lower}",
                f"not a claim of {phrase_lower}",
                f"not evidence of {phrase_lower}",
            )
        ):
            safe_occurrences += 1
            continue
        zh_clause_start = max(
            (lower_line.rfind(separator, 0, phrase_index) for separator in "；。！？|:："),
            default=-1,
        ) + 1
        zh_local_prefix = lower_line[zh_clause_start:phrase_index]
        if any(marker in zh_local_prefix for marker in ("不要", "不得", "不能", "不是", "不声明", "不代表", "不等于")):
            safe_occurrences += 1
            continue
        if (
            phrase_lower in mainstream_agent_loading_forbidden_claim_terms
            or phrase_lower in mainstream_agent_loading_forbidden_overclaims
        ) and list_negation_covers_phrase(phrase_index):
            safe_occurrences += 1
            continue
    previous_non_empty = []
    for previous in reversed(lines[max(0, index - 10):index]):
        if previous.strip():
            previous_non_empty.append(previous.strip().lower())
        if len(previous_non_empty) >= 2:
            break
    if any(
        previous.endswith("is not:")
        or previous.endswith("it is not:")
        or previous.endswith("are not:")
        or previous.endswith("not:")
        for previous in previous_non_empty
    ):
        return True
    if line.lstrip().startswith("-"):
        prior_block = "\n".join(lines[max(0, index - 12):index]).lower()
        if "it is not:" in prior_block or "is not:" in prior_block or "are not:" in prior_block:
            return True
    return safe_occurrences == len(phrase_positions)


def _append_mainstream_loading_overclaim_issues(
        failures, path, content, root, *, display_path, line_has_scoped_claim_negation,
        mainstream_loading_line_has_safe_negation, claims,
):
    display = display_path(path, root)
    lines = content.splitlines()
    for term in claims.forbidden_claim_terms:
        for index, line in enumerate(lines):
            lower_line = line.lower()
            if (
                term in {"universal runtime support", "full runtime support"}
                and "universal/full runtime support" in lower_line
                and mainstream_loading_line_has_safe_negation(lines, index, "universal/full runtime support")
            ):
                continue
            if term in lower_line and not mainstream_loading_line_has_safe_negation(lines, index, term):
                failures.append(f"{display}: forbidden mainstream agent loading claim `{term}`")
                break
    for phrase in claims.forbidden_overclaims:
        for index, line in enumerate(lines):
            lower_line = line.lower()
            if phrase in lower_line and not mainstream_loading_line_has_safe_negation(lines, index, phrase):
                failures.append(f"{display}: forbidden mainstream agent loading overclaim `{phrase}`")
                break

    tier2_needles = [agent.lower() for agent in claims.tier2]
    for line in lines:
        lower = line.lower()
        if not any(agent in lower for agent in tier2_needles):
            continue
        if "pass" not in lower and "verified" not in lower and "available" not in lower:
            continue
        safe_research_boundary = (
            "no runtime pass" in lower
            or "no adapter manifest or runtime pass" in lower
            or "no adapter manifest and no runtime pass" in lower
            or "do not" in lower and "claim runtime pass" in lower
            or "not_runtime_verified" in lower
            or "not runtime verified" in lower
            or "not runtime pass" in lower
            or "research_only" in lower
            or "research-only" in lower
        )
        if safe_research_boundary:
            continue
        if line_has_scoped_claim_negation(line, "runtime pass"):
            continue
        failures.append(f"{display}: Tier 2 row must not claim runtime PASS/verified/available: {line.strip()}")


def _append_mainstream_loading_common_doc_issues(
        failures, path, content, root, *, require_boundary, display_path,
):
    display = display_path(path, root)
    if "Mainstream Agent Loading" not in content and "Tier 1" not in content:
        failures.append(f"{display}: missing mainstream agent loading guidance")
    if require_boundary:
        lower_content = content.lower()
        for token in (
            "official approval",
            "marketplace approval",
            "universal/full runtime support",
            "codex desktop marketplace-management e2e pass",
        ):
            if token not in lower_content:
                failures.append(f"{display}: missing mainstream loading boundary phrase `{token}`")


def check_mainstream_agent_loading(
        root, *, package_root, append_mainstream_loading_common_doc_issues,
        append_mainstream_loading_overclaim_issues, display_path, parse_markdown_table_rows, loading,
):
    """FIX-122: README and adapter loading guidance must stay synchronized and no-overclaim safe."""
    root = Path(root) if root is not None else package_root
    failures = []
    contents = {}

    for rel_path in loading.required_docs:
        path = root / rel_path
        display = display_path(path, root)
        if not path.is_file():
            failures.append(f"{display}: missing mainstream agent loading artifact")
            continue
        content = path.read_text(encoding="utf-8")
        contents[rel_path] = content
        append_mainstream_loading_overclaim_issues(failures, path, content, root)

    readme_rel = "README.md"
    readme_content = contents.get(readme_rel, "")
    if readme_content:
        readme_path = root / readme_rel
        append_mainstream_loading_common_doc_issues(failures, readme_path, readme_content, root)
        for token in loading.readme_tokens:
            if token not in readme_content:
                failures.append(f"{display_path(readme_path, root)}: missing README mainstream loading token `{token}`")
        for agent in loading.tier1 + loading.tier2:
            if agent not in readme_content:
                failures.append(f"{display_path(readme_path, root)}: missing mainstream agent row/token `{agent}`")
        for agent in loading.tier2:
            rows = [line for line in readme_content.splitlines() if agent.lower() in line.lower()]
            if not rows:
                continue
            joined = " ".join(rows).lower()
            if "compatibility reference only" not in joined or "no adapter manifest" not in joined or "runtime pass" not in joined:
                failures.append(
                    f"{display_path(readme_path, root)}: Tier 2 row for {agent} must say compatibility reference only, no adapter manifest, and no runtime PASS"
                )

    requirements_rel = "docs/requirements/mainstream-agent-loading-0.47.0.md"
    requirements_content = contents.get(requirements_rel, "")
    if requirements_content:
        requirements_path = root / requirements_rel
        append_mainstream_loading_common_doc_issues(failures, requirements_path, requirements_content, root)
        for token in loading.requirements_tokens:
            if token not in requirements_content:
                failures.append(
                    f"{display_path(requirements_path, root)}: missing mainstream loading requirements token `{token}`"
                )
        for agent in loading.tier1 + loading.tier2:
            if agent not in requirements_content:
                failures.append(f"{display_path(requirements_path, root)}: missing requirements row/token `{agent}`")

        official_rows = parse_markdown_table_rows(requirements_content, section_title="Official Surface Findings")
        official_agents = {}
        for cells in official_rows:
            agent = cells[0].strip("`* ")
            if agent in loading.tier1 + loading.tier2:
                official_agents[agent] = cells
        for agent in loading.tier1 + loading.tier2:
            cells = official_agents.get(agent)
            if not cells:
                failures.append(f"{display_path(requirements_path, root)}: missing Official Surface Findings row for {agent}")
                continue
            row_text = " | ".join(cells)
            if "https://" not in row_text:
                failures.append(f"{display_path(requirements_path, root)}: {agent} row missing source citation URL")
            if agent in loading.tier2:
                row_lower = row_text.lower()
                denies_runtime = (
                    "no runtime pass" in row_lower
                    or "no adapter manifest or runtime pass" in row_lower
                    or "no adapter manifest and runtime pass" in row_lower
                    or "not runtime verified" in row_lower
                    or "not_runtime_verified" in row_lower
                    or ("do not" in row_lower and "claim runtime pass" in row_lower)
                )
                if "compatibility row only" not in row_lower or not denies_runtime:
                    failures.append(
                        f"{display_path(requirements_path, root)}: {agent} row must be compatibility-only and deny runtime PASS"
                    )

    for adapter_id, spec in loading.adapters.items():
        rel_path = spec["path"]
        content = contents.get(rel_path, "")
        if not content:
            continue
        path = root / rel_path
        display = display_path(path, root)
        for token in spec["tokens"]:
            if token not in content:
                failures.append(f"{display}: {adapter_id} adapter README missing token `{token}`")
        boundary_lower = content.lower()
        for token in ("official approval", "marketplace approval", "universal/full runtime support"):
            if token not in boundary_lower:
                failures.append(f"{display}: {adapter_id} adapter README missing boundary phrase `{token}`")
        if adapter_id in {"claude", "codex", "gemini", "opencode"} and "pass/degraded" not in boundary_lower:
            failures.append(f"{display}: {adapter_id} adapter README must preserve PASS/DEGRADED runtime boundary")

    return failures


EVIDENCE_LEVEL_MARKER_RE = re.compile(
    r"〔(live-session|isolation|static)[:：]([^\〕]{0,300}?)〕")


ADAPTER_CLAIM_REGISTRY = (
    ("dsh-session-projection",
     re.compile(r"每个会话\*{0,2}中可用|load in every session of that profile"),
     "dsh bundle session projection availability"),
    ("dsh-preset-roster",
     re.compile(r"直接出现在预设选择器|appears in the preset roster"),
     "dsh shipped preset roster appearance"),
    ("dsh-governance-gesture",
     re.compile(r"即加载统一治理入口"),
     "dsh /governance gesture entry load"),
    ("dsh-install-forms-boundary",
     re.compile(r"Both forms were re-verified|两种 plugin add 与 launch\.py 预设安装"),
     "dsh install forms verification boundary"),
)


def check_readme_claim_evidence_levels(
        readme_path, *, package_root, adapter_claim_registry, evidence_level_marker_re,
):
    """FEAT-014 / RISK-049 ①: README adapter claim→evidence level check.

    Two machine judgments over the public README and packaged DSH adapter guide:

    1. UNANNOTATED — every line matching a registry claim pattern MUST
       carry ≥1 valid evidence-level marker 〔level: detail〕 on the same
       line (per-line granularity; the marker binds the claim to its
       evidence level — the machine-checkable mapping).
    2. INTEGRITY — every marker must name a registered level; live-session
       and isolation details MUST contain an ISO date (their verification
       event). static is the explicit no-execution-evidence label and does
       not require a date.

    Advisory WARN (Check 28t, 28s precedent — fatal_on_error=false): WARNs
    do not increment check-governance all_issues; escalation to FAIL is the
    registered tightening path (RISK-049 closure review).

    Returns {"verdict": "PASS"|"WARN"|"no-verdict", "reason", "warnings",
    "stats"} — never raises; a missing README is no-verdict.
    """
    paths = ([Path(readme_path)] if readme_path is not None else
             [package_root / "README.md", package_root / "adapters" / "dsh" / "README.md"])
    result = {
        "verdict": "no-verdict",
        "reason": "",
        "warnings": [],
        "stats": {
            "claims_checked": 0, "claims_annotated": 0,
            "markers_found": 0, "markers_invalid": 0,
            "levels": {"live-session": 0, "isolation": 0, "static": 0},
        },
    }
    warnings = result["warnings"]
    stats = result["stats"]
    for path in paths:
        if not path.is_file():
            result["reason"] = f"{path} not found — Check 28t has nothing to judge"
            return result
        content = path.read_text(encoding="utf-8")
        # 1. Marker integrity (every marker anywhere in the README).
        for marker_match in evidence_level_marker_re.finditer(content):
            level, detail = marker_match.group(1), marker_match.group(2)
            stats["markers_found"] += 1
            stats["levels"][level] += 1
            if level in ("live-session", "isolation") \
                    and not re.search(r"\d{4}-\d{2}-\d{2}", detail):
                stats["markers_invalid"] += 1
                warnings.append({
                    "rule": "INTEGRITY",
                    "claim_id": None,
                    "reason": "evidence-level marker 〔{0}: {1}〕 lacks the "
                              "required ISO verification date ({0} claims MUST "
                              "cite their verification date)".format(
                                  level, detail),
                })

        # 2. Registry claims must carry a marker on the claim line.
        for lineno, line in enumerate(content.splitlines(), 1):
            for claim_id, pattern, description in adapter_claim_registry:
                if not pattern.search(line):
                    continue
                stats["claims_checked"] += 1
                if evidence_level_marker_re.search(line):
                    stats["claims_annotated"] += 1
                else:
                    warnings.append({
                        "rule": "UNANNOTATED",
                        "claim_id": claim_id,
                        "reason": "{3} L{0}: adapter claim `{1}` ({2}) lacks "
                                  "an evidence-level marker "
                                  "〔live-session|isolation|static: …〕 — the "
                                  "RISK-049 ① claim→evidence mapping".format(
                                      lineno, claim_id, description, path),
                    })

    if warnings:
        result["verdict"] = "WARN"
        result["reason"] = (
            "{0} README claim-evidence mapping WARN(s) — advisory "
            "(RISK-049 ①; escalation path registered)".format(
                len(warnings)))
    elif stats["claims_checked"]:
        result["verdict"] = "PASS"
        result["reason"] = (
            "{0} registry claim(s) all carry valid evidence-level "
            "markers ({1} marker(s): live-session {2} / isolation {3} / "
            "static {4})".format(
                stats["claims_checked"], stats["markers_found"],
                stats["levels"]["live-session"],
                stats["levels"]["isolation"], stats["levels"]["static"]))
    else:
        result["reason"] = (
            "no registry adapter claims found in README — nothing to judge")
    return result
