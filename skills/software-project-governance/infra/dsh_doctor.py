"""``dsh-doctor`` — the single staged diagnostic entry for the dsh boundary.

FEAT-031 / 0.81.0 slice **V8**; design ``docs/requirements/dsh-compat-design-0.81.0.md``
§5.1 (the entry spec), §5.2 (the S0–S7 stage table), §5.5 (the upgrade
rehearsal) and §5.6 (the negative fixtures).

**Why one entry instead of one more check.** The checks answer "is the boundary
intact?" at *gate* resolution (PASS / FAIL / NOT_RUN, and the question stops
there). This entry answers the other half of REQ-149 — "the user hit a problem,
which layer is it?" — by walking the boundary in the order a defect travels
through it (S0 input → S7 self-upgrade) and reporting, per stage, what was
observed, what was *not* observed and what to do next. The two surfaces are
deliberately different: a gate may not print advice, and a diagnostic entry may
not silently pass.

**The four disciplines that make it trustworthy.**

  * **Stage isolation.** Every stage runs inside its own ``try``/``except``. A
    crashed stage is reported as ``NOT_RUN`` with ``stage_error: true`` and the
    remaining stages still run; the report always carries all eight stage
    records. A doctor that dies on the very defect it was invoked for is worse
    than no doctor (design §5.1, BT-2).
  * **Lazy, isolated imports.** ``dsh_compat`` and ``launch.py`` are reached
    through a subprocess or a function-local import, so "the guard is broken"
    — the most likely reason to call this command — still produces a report.
    The reverse link (``verify_workflow`` → here) is a function-local import
    too, keeping the engine's frozen startup import budget at 196.
  * **Single verdict (R0 BT-R-02 / K-12).** The boundary criteria are computed
    once, by ``checks.dsh_boundary``; this module never re-derives them. It also
    never re-derives the ``coverage`` block — it *projects*
    ``check_dsh_preset_compat()``'s own output, including
    ``unreadable_compositions`` (F-R1-06). Stage verdicts are projections of
    judgments that already have owners; where a judgment has one, the
    ``evidence[]`` entry cites it (``kind: "check", ref: "28w/K-7"``).
  * **Offline is about processes, not about files** (R1 N-3). ``--offline``
    forbids *spawning* anything and forbids host-plane probing; the file-level
    criteria keep running, so a clean repository state still exits 0 while a
    broken one is still caught. K-12's comparison is defined only for a run in
    which every stage actually ran — that is the domain in which the doctor's
    verdict and the boundary exit code are the same claim.

**Exit codes** (design §5.1, aligned with ``SMOKE_EXIT_*`` in ``launch.py``):
``0`` = no stage FAILed (a report of all ``NOT_RUN`` exits 0 — "nothing was
verified" is not "something is broken"); ``1`` = at least one stage FAILed;
``2`` = refused (isolation guard, unauthorised host probe, usage error).

**Writes.** There is exactly one writing path, ``--record-evidence``, and it
only ever writes *inside* a redirected ``DSH_HOME`` plus the file named by
``--out``. Every other invocation is read-only: the checks it calls write
nothing, and ``--rehearse`` compares in-memory records (the synthetic fixtures
of design §5.5 [C] are created by the caller, in a temporary directory).

CLI::

    python …/verify_workflow.py dsh-doctor [--json] [--stage S0..S7]...
        [--offline] [--selftest] [--record-evidence --out <path>]
        [--rehearse <facts.json> [--against <baseline.json>]]
        [--allow-host-probe]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

__all__ = [
    "STAGES",
    "EXIT_OK",
    "EXIT_FAIL",
    "EXIT_REFUSED",
    "run_doctor",
    "run_isolated_smoke",
    "run_self_test",
    "rehearse",
    "main",
]

REPORT_SCHEMA_VERSION = 1
COMMAND_NAME = "dsh-doctor"

#: The shape every ``host-facts-*.json`` record must carry (design §5.4/§5.5).
#: Shared with Check 28w's K-13 judgment, which validates the same records —
#: one vocabulary, declared where the writing happens.
FACTSHEET_REQUIRED_FIELDS = ("captured_at", "dsh_version", "synthetic",
                             "provenance", "plane")

#: The three-state vocabulary and the exit codes design §5.1 fixes.
VERDICT_PASS = "PASS"
VERDICT_FAIL = "FAIL"
VERDICT_NOT_RUN = "NOT_RUN"
EXIT_OK = 0
EXIT_FAIL = 1
EXIT_REFUSED = 2

#: The eight stages, in the order a defect travels through the boundary.
STAGES: Tuple[Tuple[str, str], ...] = (
    ("S0", "input/interface"),
    ("S1", "delivery (preset rendered)"),
    ("S2", "row/config schema"),
    ("S3", "plane/installation"),
    ("S4", "render/parity"),
    ("S5", "host entry"),
    ("S6", "skill catalog/gestures"),
    ("S7", "hooks/self-upgrade"),
)

#: S1/S6 pass texts must carry their qualification (design §5.2 T-3/T-4, R-8):
#: a resolution-level observation is not a user-visible acceptance.
RESOLUTION_ONLY = "resolution-level only — the settings page UI and in-session resolution are NOT verified"

#: The rehearsal preconditions' TTL uses the contract's own threshold.
DEFAULT_TTL_DAYS = 180

#: S4 needs the JS renderer; the coverage claim that names the requirement.
RENDER_REQUIREMENT = "node"

_PACKAGE_VERSION_RE = re.compile(r'"version"\s*:\s*"([^"]+)"')
_TOKEN_RE = re.compile(r"__[A-Za-z0-9_]+__")


class Refused(RuntimeError):
    """The run must not proceed (isolation guard / authorisation / usage)."""


# ── small shared helpers ────────────────────────────────────────────────────


def _repo_root() -> Path:
    """Package root, derived from this file (never the process CWD)."""
    # <pkg>/skills/software-project-governance/infra/dsh_doctor.py
    return Path(__file__).resolve().parents[3]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _load_contract_module():
    """Import the accessor lazily (it is a sibling module, loaded on demand)."""
    infra = Path(__file__).resolve().parent
    if str(infra) not in sys.path:
        sys.path.insert(0, str(infra))
    import dsh_contract  # noqa: PLC0415 — deliberate, lazy

    return dsh_contract


def _load_boundary_module():
    """Import Check 28w lazily and return the module."""
    infra = Path(__file__).resolve().parent
    if str(infra) not in sys.path:
        sys.path.insert(0, str(infra))
    from checks import dsh_boundary  # noqa: PLC0415 — deliberate, lazy

    return dsh_boundary


def _contract_facts() -> Dict[str, Any]:
    """The contract document, or ``{}`` when it cannot be read."""
    try:
        return _load_contract_module().load_contract()
    except Exception:
        return {}


def _get(document: Dict[str, Any], path: str, default: Any = None) -> Any:
    node: Any = document
    for token in re.split(r"\.", path):
        if isinstance(node, dict) and token in node:
            node = node[token]
        else:
            return default
    return node


def _package_version(root: Path) -> Optional[str]:
    match = _PACKAGE_VERSION_RE.search(_read(root / "package.json"))
    return match.group(1) if match else None


def _write_side_home(env: Dict[str, str]) -> Tuple[Optional[Path], List[str]]:
    """Resolve ``DSH_HOME`` the way the contract's *write side* says to.

    A judgeable copy of the write-side policy (design §2.4 ``host.env.write_side``
    — the triple `trimmed-empty-means-unset` / `verbatim-then-platform-resolve` /
    ``<home>/.dsh``), derived from the contract rather than restated: the three
    V6 implementations agree on this table, and S0 is the stage that discloses
    the resulting path so the other stages cannot disagree about it silently.

    Never guesses a path when the variable is explicitly set to something
    unusable — it reports what it saw.
    """
    facts = _contract_facts()
    var = _get(facts, "host.env.home_var", "DSH_HOME")
    fallback_prose = _get(facts, "host.env.write_side.fallback", "<home>/.dsh")
    notes: List[str] = []
    raw = env.get(var)
    if raw is None:
        notes.append(f"{var} is not set — using the declared fallback")
    else:
        trimmed = raw.strip()
        if not trimmed:
            notes.append(
                f"{var} is set to whitespace only; the declared blank policy "
                f"`{_get(facts, 'host.env.write_side.blank_policy', 'trimmed-empty-means-unset')}` "
                f"treats it as unset")
            raw = None
        elif trimmed in _get(facts, "host.env.write_side.tilde_expansion", ["~", "~/", "~\\"]):
            notes.append(f"{var} is the bare tilde form — expanded against HOME")
            raw = str(Path.home())
        elif trimmed.startswith("~"):
            notes.append(f"{var} starts with `~` — expanded against HOME")
            raw = str(Path.home() / trimmed[1:].lstrip("/\\"))
        else:
            raw = trimmed
    if raw:
        return Path(raw), notes
    home = env.get("USERPROFILE") or env.get("HOME")
    if not home:
        return None, notes + ["no HOME/USERPROFILE to expand the declared "
                              f"fallback {fallback_prose!r}"]
    notes.append(f"fallback `{fallback_prose}` expanded to "
                 f"{Path(home) / '.dsh'}")
    return Path(home) / ".dsh", notes


def _which(name: str) -> Optional[str]:
    return shutil.which(name)


def _head(text: Any, limit: int = 400) -> str:
    text = "" if text is None else str(text)
    return text if len(text) <= limit else text[:limit] + "…"


# ── stage machinery ─────────────────────────────────────────────────────────


@dataclass
class StageOutcome:
    """One stage's result (design §5.1's fixed per-stage field set)."""

    stage: str
    title: str
    verdict: str
    reason: str
    credible_face: Dict[str, Any] = field(default_factory=dict)
    evidence: List[Dict[str, str]] = field(default_factory=list)
    remediation: List[Dict[str, str]] = field(default_factory=list)
    stage_error: bool = False
    findings: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        record: Dict[str, Any] = {
            "stage": self.stage,
            "title": self.title,
            "verdict": self.verdict,
            "reason": self.reason,
            "credible_face": self.credible_face,
            "evidence": self.evidence,
            "remediation": self.remediation,
        }
        if self.stage_error:
            record["stage_error"] = True
        if self.findings:
            record["findings"] = self.findings
        return record


@dataclass
class Context:
    """Everything the stages share — built once, read-only."""

    root: Path
    offline: bool
    allow_host_probe: bool
    stages_wanted: Optional[Tuple[str, ...]]
    env: Dict[str, str]
    boundary_report: Optional[Dict[str, Any]] = None
    boundary_issues: Optional[int] = None

    #: Set by S0 so later stages never re-resolve the home differently.
    dsh_home: Optional[Path] = None
    dsh_home_notes: List[str] = field(default_factory=list)

    @property
    def subprocess_allowed(self) -> bool:
        return not self.offline


def _evidence(kind: str, ref: str, detail: str = "") -> Dict[str, str]:
    return {"kind": kind, "ref": ref, "detail": detail}


def _remediation(action: str, command: str = "", expected: str = "") -> Dict[str, str]:
    return {"action": action, "command": command, "expected": expected}


def _boundary_stage(ctx: Context, checks: Sequence[str]) -> Tuple[Dict[str, Any], bool]:
    """The 28w boundary report (computed once per process) and its FAIL flag."""
    if ctx.boundary_report is None:
        try:
            module = _load_boundary_module()
            ctx.boundary_report = module.check_dsh_boundary(ctx.root)
            ctx.boundary_issues = len(module.failed(ctx.boundary_report))
        except Exception as error:
            ctx.boundary_report = {
                "check": "28w",
                "verdict": "FAIL",
                "criteria": [],
                "issues": [f"Check 28w could not run: {type(error).__name__}: {error}"],
                "error": f"{type(error).__name__}: {error}",
            }
            ctx.boundary_issues = 1
    entries = {entry["id"]: entry for entry in ctx.boundary_report.get("criteria", [])}
    failed = False
    detail_bits = []
    for ident in checks:
        entry = entries.get(ident)
        if entry is None:
            detail_bits.append(f"{ident}: no criterion record")
            continue
        if entry["verdict"] == VERDICT_FAIL:
            failed = True
        detail_bits.append(f"{ident}={entry['verdict']}")
    return {
        "verdict": "FAIL" if failed else "PASS",
        "detail": "; ".join(detail_bits),
        "entries": [entries.get(ident) for ident in checks],
    }, failed


# ── S0 ──────────────────────────────────────────────────────────────────────


def stage_s0_input(ctx: Context) -> StageOutcome:
    """S0 — the input/interface plane: what we were called with, and with what.

    By design this stage records facts and can only FAIL on one thing: a
    ``DSH_HOME`` that cannot be resolved at all, which would make every later
    stage's observation ambiguous (design §5.2 S0).
    """
    outcome = StageOutcome("S0", "input/interface", VERDICT_NOT_RUN,
                           "recorded the invocation facts (record-only stage)")
    dsh_home, notes = _write_side_home(ctx.env)
    ctx.dsh_home, ctx.dsh_home_notes = dsh_home, notes
    version = _package_version(ctx.root)
    node = _which("node")
    dsh = _which("dsh")
    outcome.credible_face = {
        "dsh_home": str(dsh_home) if dsh_home else None,
        "dsh_home_notes": notes,
        "package_root": str(ctx.root),
        "package_version": version,
        "node": node,
        "node_version": None,
        "dsh_cli": dsh,
        "offline": ctx.offline,
        "allow_host_probe": ctx.allow_host_probe,
    }
    outcome.evidence.append(_evidence(
        "file", "package.json", f"package root {ctx.root}; version {version}"))
    outcome.evidence.append(_evidence(
        "probe", "DSH_HOME", f"{dsh_home} ({'; '.join(notes) or 'explicit'})"))
    if dsh_home is None:
        outcome.verdict = VERDICT_FAIL
        outcome.reason = ("DSH_HOME could not be resolved (no HOME/USERPROFILE "
                          "for the declared fallback)")
        outcome.findings.append(outcome.reason)
        outcome.remediation.append(_remediation(
            "set DSH_HOME explicitly, or fix the home directory",
            "set DSH_HOME=<dir>", "DSH_HOME resolves to a directory"))
        return outcome
    if node and ctx.subprocess_allowed:
        try:
            proc = subprocess.run([node, "--version"], capture_output=True,
                                  text=True, encoding="utf-8", errors="replace",
                                  timeout=30)
            outcome.credible_face["node_version"] = (proc.stdout or "").strip()
        except (OSError, subprocess.SubprocessError) as error:
            outcome.findings.append(f"node --version failed: {error}")
    elif node and ctx.offline:
        outcome.findings.append("node present but --offline suppresses probing it")
    outcome.reason = (
        f"DSH_HOME={dsh_home}; package {version}; node "
        f"{'present' if node else 'absent'}; dsh CLI "
        f"{'present' if dsh else 'absent'} — record-only stage")
    return outcome


# ── S1 ──────────────────────────────────────────────────────────────────────


def stage_s1_delivery(ctx: Context) -> StageOutcome:
    """S1 — is the preset rendered where the host row puts it, at this version?

    The pass text carries the T-3 qualification: S1 proves the *directory and
    files* are in place. It cannot prove the settings page shows the preset,
    and saying otherwise would be the over-claim design §8.2 R-8 registers.
    """
    outcome = StageOutcome("S1", "delivery (preset rendered)",
                           VERDICT_NOT_RUN, "")
    facts = _contract_facts()
    preset_id = _get(facts, "own.preset.id", "governance")
    marker = _get(facts, "own.preset.version_marker", ".dsh-bundle-version")
    skill_marker = _get(facts, "own.preset.skill_root_marker", "skill-root.txt")
    preset_dir = (ctx.dsh_home / _get(facts, "host.home.user_preset_dir",
                                      ".agent-presets") / preset_id
                  if ctx.dsh_home else None)
    outcome.credible_face = {
        "preset_dir": str(preset_dir) if preset_dir else None,
        "preset_id": preset_id,
        "version_marker": marker,
    }
    if preset_dir is None:
        outcome.verdict = VERDICT_NOT_RUN
        outcome.reason = "no resolved DSH_HOME — the delivery plane is unknown"
        outcome.remediation.append(_remediation(
            "set DSH_HOME, then install the preset",
            "python adapters/dsh/launch.py --sync",
            "the preset directory exists and carries the version marker"))
        return outcome
    outcome.evidence.append(_evidence(
        "file", str(preset_dir), "preset directory (redirected DSH_HOME)"))
    if not preset_dir.is_dir():
        outcome.verdict = VERDICT_FAIL
        outcome.reason = (f"the preset directory {preset_dir} does not exist — "
                          f"the host row has not rendered the preset")
        outcome.findings.append(outcome.reason)
        outcome.remediation.append(_remediation(
            "render and install the preset",
            "python adapters/dsh/launch.py --sync",
            f"{preset_dir} exists and carries {marker}"))
        return outcome
    marker_path = preset_dir / marker
    declared = _package_version(ctx.root)
    installed = _read(marker_path).strip()
    outcome.credible_face["marker_version"] = installed or None
    outcome.credible_face["package_version"] = declared
    if not installed:
        outcome.verdict = VERDICT_FAIL
        outcome.reason = (f"the version marker {marker} is missing from "
                          f"{preset_dir}")
        outcome.findings.append(outcome.reason)
        outcome.remediation.append(_remediation(
            "re-install the preset", "python adapters/dsh/launch.py --sync",
            f"{marker_path} names version {declared}"))
        return outcome
    if declared and installed != declared:
        outcome.verdict = VERDICT_FAIL
        outcome.reason = (f"installed preset version {installed!r} != package "
                          f"version {declared!r} — the preset is stale")
        outcome.findings.append(outcome.reason)
        outcome.remediation.append(_remediation(
            "sync the preset to this package version",
            "python adapters/dsh/launch.py --sync",
            f"{marker_path} names version {declared}"))
        return outcome
    skill_root = preset_dir / skill_marker
    outcome.credible_face["skill_root_marker"] = (
        skill_root.as_posix() if skill_root.is_file() else None)
    if not skill_root.is_file():
        outcome.verdict = VERDICT_FAIL
        outcome.reason = (f"the skill-root marker {skill_marker} is missing — "
                          f"installed hooks cannot find the workflow home")
        outcome.findings.append(outcome.reason)
        outcome.remediation.append(_remediation(
            "re-install the preset so the marker is written",
            "python adapters/dsh/launch.py --sync",
            f"{skill_root} exists and names the workflow home"))
        return outcome
    outcome.verdict = VERDICT_PASS
    outcome.reason = (f"preset {preset_id!r} installed at {preset_dir} with "
                      f"version {installed} and the skill-root marker — "
                      f"{RESOLUTION_ONLY}")
    outcome.evidence.append(_evidence(
        "file", str(marker_path), f"version {installed}"))
    return outcome


# ── S2 ──────────────────────────────────────────────────────────────────────


def _projected_coverage(report: Dict[str, Any]) -> Dict[str, Any]:
    """Project ``check_dsh_preset_compat()``'s ``coverage`` block verbatim.

    A *projection*: the five fields are copied, never recomputed (R0 BT-R-02 —
    a second computation is a second verdict waiting to disagree). The fifth
    field, ``unreadable_compositions``, is a composition-level fact that cannot
    enter the ``rows_*`` histogram (FIX-315 F-R1-06): dropping it would make a
    read failure disappear from exactly the surface that is supposed to disclose
    it.
    """
    coverage = report.get("coverage") or {}
    return {
        "rows_enabled": coverage.get("rows_enabled"),
        "rows_verified": coverage.get("rows_verified"),
        "rows_unverified": coverage.get("rows_unverified"),
        "unreadable_compositions": coverage.get("unreadable_compositions"),
        "unverified_reasons": dict(coverage.get("unverified_reasons") or {}),
    }


def stage_s2_rows(ctx: Context, compat_runner: Optional[Callable[[], Dict[str, Any]]] = None,
                  ) -> StageOutcome:
    """S2 — the row/config schema plane, projected from Check 28v (never recomputed).

    Under ``--offline`` the 28v run still happens (it is a file-level
    judgment over *our own* compositions; only the schema resolution needs node)
    and degrades to its own ``NOT_RUN`` when node or the plane is missing —
    which is a disclosure, not a doctor FAIL.
    """
    outcome = StageOutcome("S2", "row/config schema", VERDICT_NOT_RUN, "")
    if compat_runner is None:
        compat_runner = _default_compat_runner(ctx)
    if compat_runner is None:
        outcome.reason = ("--offline: Check 28v needs node to resolve the "
                          "installed schemas; no subprocess is started")
        outcome.credible_face = _projected_coverage({})
        outcome.remediation.append(_remediation(
            "re-run without --offline to judge the row/config plane",
            "python …/verify_workflow.py check-dsh-preset-compat",
            "a verdict with a coverage denominator"))
        return outcome
    report = compat_runner()
    coverage = _projected_coverage(report)
    outcome.credible_face = coverage
    rows_unverified = coverage.get("rows_unverified")
    unreadable = coverage.get("unreadable_compositions")
    outcome.evidence.append(_evidence(
        "check", "28v",
        f"verdict {report.get('verdict')}; coverage {coverage}"))
    outcome.verdict = report.get("verdict", VERDICT_NOT_RUN)
    if outcome.verdict == VERDICT_FAIL:
        outcome.reason = report.get("reason") or "a row was rejected by the installed schemas"
        outcome.findings.extend(report.get("issues") or [])
        outcome.remediation.append(_remediation(
            "fix the rejected row's config, or align it with the installed plugin's schema",
            "python …/verify_workflow.py check-dsh-preset-compat",
            "every enabled row with a schema accepts its config"))
        return outcome
    if rows_unverified:
        reasons = ", ".join(f"{key}={value}"
                            for key, value in coverage["unverified_reasons"].items())
        outcome.reason = (f"verified {coverage.get('rows_verified')} of "
                          f"{coverage.get('rows_enabled')} enabled row(s); "
                          f"{rows_unverified} NOT verified ({reasons}) — "
                          f"disclosed, never counted as verified")
        if unreadable:
            outcome.reason += (f"; {unreadable} composition(s) unreadable")
        return outcome
    if outcome.verdict == VERDICT_PASS:
        outcome.reason = (f"verified {coverage.get('rows_verified')} of "
                          f"{coverage.get('rows_enabled')} enabled row(s) "
                          f"against the installed schemas")
        if unreadable:
            outcome.reason += (f"; {unreadable} composition(s) unreadable — "
                               f"that face is NOT verified")
        return outcome
    outcome.reason = (report.get("reason")
                      or "Check 28v reported NOT_RUN (no node / no resolvable plane)")
    outcome.remediation.append(_remediation(
        "check node availability and the DSH plane",
        "python …/verify_workflow.py check-dsh-preset-compat",
        "a verdict other than NOT_RUN"))
    return outcome


def _default_compat_runner(ctx: Context) -> Optional[Callable[[], Dict[str, Any]]]:
    """The 28v projection source.

    In-process when the guard is importable (it reads files and spawns the node
    probe only when one is available), and ``None`` under ``--offline``, where
    starting that probe is exactly what must not happen.
    """
    if ctx.offline or not ctx.subprocess_allowed:
        return None
    if _which("node") is None:
        return None

    def runner() -> Dict[str, Any]:
        infra = Path(__file__).resolve().parent
        if str(infra) not in sys.path:
            sys.path.insert(0, str(infra))
        import dsh_compat  # noqa: PLC0415 — deliberate, lazy

        return dsh_compat.check_dsh_preset_compat()

    return runner


# ── S3 ──────────────────────────────────────────────────────────────────────


def stage_s3_plane(ctx: Context) -> StageOutcome:
    """S3 — the plane/installation face: evidence, plane, oracle versions, residue.

    Two disciplines from design §5.1/§5.2 are load-bearing here:

      * the version-evidence half is a **projection of K-7** (``kind: "check",
        ref: "28w/K-7"``), never a re-derivation — the doctor and the gate must
        not be able to disagree about the same fact (R0 BT-R-02);
      * a version **outside** ``compat_range`` is a FAIL, while *unrecorded*
        evidence is a disclosure. ``compat_range`` is unadjudicated in this
        slice (the contract says so), so the out-of-range judgment reports
        ``NOT_RUN`` rather than inventing a verdict.
    """
    outcome = StageOutcome("S3", "plane/installation", VERDICT_NOT_RUN, "")
    facts = _contract_facts()
    ttl = _get(facts, "evidence.verified_on_ttl_days", DEFAULT_TTL_DAYS)
    compat_range = _get(facts, "evidence.compat_range")
    recorded_version = _get(facts, "evidence.dsh_cli_version")
    verified_on = _get(facts, "evidence.verified_on")
    boundary, failed = _boundary_stage(ctx, ("K-7",))
    outcome.evidence.append(_evidence("check", "28w/K-7", boundary["detail"]))
    outcome.credible_face.update({
        "evidence_dsh_cli_version": recorded_version,
        "evidence_verified_on": verified_on,
        "evidence_ttl_days": ttl,
        "compat_range": compat_range,
        "plane_source": _get(facts, "evidence.plane.source"),
        "dsh_home": str(ctx.dsh_home) if ctx.dsh_home else None,
    })
    if failed:
        k7 = (boundary["entries"][0] or {})
        outcome.verdict = VERDICT_FAIL
        outcome.reason = f"K-7 (version evidence): {k7.get('reason', 'failed')}"
        outcome.findings.extend(k7.get("findings") or [])
        outcome.remediation.append(_remediation(
            "reconcile the manifest with the contract, then re-record",
            "python …/verify_workflow.py dsh-doctor --record-evidence",
            "manifest evidence == contract evidence, within TTL"))
        return outcome
    if not ctx.dsh_home or not ctx.dsh_home.is_dir():
        outcome.reason = (f"no DSH_HOME plane to inspect"
                          f"{' (offline)' if ctx.offline else ''}")
        outcome.remediation.append(_remediation(
            "point DSH_HOME at the installation, then re-run",
            "set DSH_HOME=<dir>", "the plane resolves"))
        return outcome
    planes = _profile_planes(ctx)
    outcome.credible_face["planes"] = [str(item) for item in planes]
    outcome.credible_face["other_planes"] = [str(item) for item in planes[1:]]
    residue = _residue_count()
    outcome.credible_face["temp_residue"] = residue
    outcome.evidence.append(_evidence(
        "probe", "plane discovery",
        f"{len(planes)} plane(s): {[str(p) for p in planes] or 'none'}"))
    if not planes:
        outcome.reason = ("no installed plane found under DSH_HOME — this is what "
                          "makes the other stages' NOT_RUN unavoidable")
        outcome.remediation.append(_remediation(
            "install the harness under this DSH_HOME",
            "dsh --version", "a profiles plane resolves"))
        return outcome
    # D-79 is an advisory disclosure about %TEMP% residue; the evidence state is
    # a disclosure about the contract. Reporting the first must not swallow the
    # second, so residue is carried into the reason and the judgments below still
    # run (R0's F-03 remediation lives in the unrecorded branch).
    residue_note = ""
    if residue:
        residue_note = (f"; {residue} stale `spg-dsh-compat-*` temp director(y/ies) "
                        f"under %TEMP% (read-only count, nothing deleted)")
    if verified_on is None:
        outcome.reason = (f"{len(planes)} plane(s) resolved; version evidence is "
                          f"unrecorded (contract `evidence.verified_on` is null) "
                          f"— recorded facts cannot be compared yet"
                          f"{residue_note}")
        outcome.remediation.append(_remediation(
            "record the plane's facts, then land the contract update in the same "
            "reviewed commit (the probe does not machine-mutate the contract)",
            "python …/verify_workflow.py dsh-doctor --record-evidence",
            "the recorded factsheet carries the measured version/plane; the "
            "maintainer writes `evidence.verified_on` / `evidence.dsh_cli_version` "
            "from it in a reviewed commit"))
        return outcome
    if residue_note:
        # Residue with the evidence recorded is still a plain disclosure.
        outcome.reason = (f"{len(planes)} plane(s) resolved; recorded version "
                          f"{recorded_version!r}{residue_note}")
        return outcome
    if compat_range is None:
        outcome.reason = (f"{len(planes)} plane(s) resolved; recorded version "
                          f"{recorded_version!r}; `evidence.compat_range` is "
                          f"unadjudicated — the out-of-range judgment is NOT_RUN "
                          f"(it must not default to PASS)")
        outcome.remediation.append(_remediation(
            "adjudicate the supported dsh version range in the contract",
            "", "`evidence.compat_range` carries a range"))
        return outcome
    if not _version_in_range(recorded_version, compat_range):
        outcome.verdict = VERDICT_FAIL
        outcome.reason = (f"recorded dsh version {recorded_version!r} is outside "
                          f"the declared range {compat_range!r}")
        outcome.findings.append(outcome.reason)
        outcome.remediation.append(_remediation(
            "re-verify against the installed version, then widen the range or "
            "re-record and land the contract update in a reviewed commit",
            "python …/verify_workflow.py dsh-doctor --record-evidence",
            "the recorded version is inside `compat_range`"))
        return outcome
    outcome.verdict = VERDICT_PASS
    outcome.reason = (f"{len(planes)} plane(s) resolved; recorded version "
                      f"{recorded_version!r} inside {compat_range!r}; evidence "
                      f"within the {ttl}-day TTL")
    return outcome


def _profile_planes(ctx: Context) -> List[Path]:
    """The discovered planes — via the guard, or the plain layout when offline.

    The guard's own discovery stays the authority (``dsh_compat._profile_planes``
    is the fail-closed read side); when it cannot be imported the layout the
    contract declares is walked read-only.
    """
    if ctx.dsh_home is None:
        return []
    try:
        infra = Path(__file__).resolve().parent
        if str(infra) not in sys.path:
            sys.path.insert(0, str(infra))
        import dsh_compat  # noqa: PLC0415 — deliberate, lazy

        env = dict(ctx.env)
        env.setdefault("DSH_HOME", str(ctx.dsh_home))
        planes = dsh_compat._profile_planes(env)  # noqa: SLF001 — declared seam
        return [Path(item) for item in planes]
    except Exception:
        facts = _contract_facts()
        dirname = _get(facts, "host.install.profiles_dir_name", "profiles")
        candidates = [ctx.dsh_home / dirname]
        return [item for item in candidates if item.is_dir()]


def _residue_count() -> int:
    """Read-only count of stale ``spg-dsh-compat-*`` temp directories (D-79)."""
    import tempfile

    root = Path(tempfile.gettempdir())
    try:
        return sum(1 for item in root.glob("spg-dsh-compat-*"))
    except OSError:  # pragma: no cover - defensive
        return 0


def _version_in_range(version: Optional[str], compat_range: Any) -> bool:
    """Whether ``version`` satisfies ``compat_range`` (an inclusive pair)."""
    if not version or not isinstance(compat_range, (list, tuple)) or len(compat_range) != 2:
        return False
    low = _version_tuple(compat_range[0])
    high = _version_tuple(compat_range[1])
    current = _version_tuple(version)
    if not low or not high or not current:
        return False
    return _compare_versions(low, current) <= 0 <= _compare_versions(high, current)


_PRERELEASE_ORDER_RE = re.compile(r"^(.*?)(?:-([A-Za-z0-9.]+))?$")


def _version_tuple(value: str) -> Tuple[int, ...]:
    """A comparable key for a dotted version, prereleases ranked below releases.

    ``0.1.5-rc.1`` → ``(0, 1, 5, 0)`` and ``0.1.5`` → ``(0, 1, 5, 1)``: the
    release candidate sorts under the release it precedes, while plain versions
    keep their numeric ordering. Keys of different lengths are padded with
    ``0`` before comparison (:func:`_compare_versions`), so a range test stays
    inclusive at both ends. An unparsable value yields an empty key, which every
    caller reads as "not comparable".
    """
    match = _PRERELEASE_ORDER_RE.match(str(value).strip())
    if not match:
        return ()
    try:
        numbers = tuple(int(part) for part in match.group(1).split("."))
    except ValueError:
        return ()
    return numbers + ((0,) if match.group(2) else (1,))


def _compare_versions(left: Tuple[int, ...], right: Tuple[int, ...]) -> int:
    """Compare two version keys, padding the shorter one with ``0``."""
    width = max(len(left), len(right))
    left_padded = left + (0,) * (width - len(left))
    right_padded = right + (0,) * (width - len(right))
    return (left_padded > right_padded) - (left_padded < right_padded)


# ── S4 ──────────────────────────────────────────────────────────────────────


def stage_s4_render(ctx: Context) -> StageOutcome:
    """S4 — the render/parity face: two renderers, one byte sequence.

    The Python half is the launcher's **own** ``render_composition()``, loaded
    from the file rather than re-substituted here: a second token loop would be
    a second implementation, and "two implementations agree with each other" is
    not the fact this stage exists to establish (it is "the two *delivery paths*
    agree"). The leftover scan then runs over the real render output.

    Offline this is ``NOT_RUN`` *with its reason* — and that reason is the
    disclosure T-6 and G05-d require: the JS side is the half that cannot be
    exercised without a child process, so the Python renderer's own result is
    labelled as such rather than presented as "parity verified".
    """
    outcome = StageOutcome("S4", "render/parity", VERDICT_NOT_RUN, "")
    facts = _contract_facts()
    tokens = _get(facts, "own.render.tokens", {})
    leftover_pattern = _get(facts, "own.render.leftover_scan", "__[A-Za-z0-9_]+__")
    template = ctx.root / _get(facts, "own.preset.template",
                               "agent-presets/governance/agent.cordis.yml.template")
    text = _read(template)
    outcome.credible_face = {
        "template": template.as_posix(),
        "tokens": sorted(tokens),
        "python_render_sha256": None,
        "js_render_sha256": None,
        "leftovers": [],
    }
    if not text:
        outcome.verdict = VERDICT_FAIL
        outcome.reason = f"template missing: {template}"
        outcome.findings.append(outcome.reason)
        return outcome
    try:
        rendered = _python_render(ctx.root)
    except Exception as error:
        outcome.verdict = VERDICT_FAIL
        outcome.reason = (f"the Python renderer could not be exercised: "
                          f"{type(error).__name__}: {error}")
        outcome.findings.append(outcome.reason)
        return outcome
    if not rendered:
        outcome.verdict = VERDICT_FAIL
        outcome.reason = ("the Python renderer returned an empty composition — "
                          "an unresolved token or an unreadable template")
        outcome.findings.append(outcome.reason)
        return outcome
    leftovers = sorted(set(re.findall(leftover_pattern, rendered)))
    outcome.credible_face["leftovers"] = leftovers
    if leftovers:
        outcome.verdict = VERDICT_FAIL
        outcome.reason = (f"tokens left after rendering: {leftovers} — a "
                          f"misspelt or unknown token would ship unresolved")
        outcome.findings.append(outcome.reason)
        outcome.remediation.append(_remediation(
            "fix the token spelling against `own.render.tokens`",
            "python -m unittest discover -s skills/software-project-governance/infra/tests -p test_dsh_contract.py",
            "no `__…__` residue after rendering"))
        return outcome
    node = _which("node")
    python_hash = _sha256_text(rendered)
    outcome.credible_face["python_render_sha256"] = python_hash
    if ctx.offline or not node:
        outcome.reason = (
            f"the Python renderer leaves no token residue (sha256 "
            f"{python_hash[:16]}…); the JS renderer's half of the parity "
            f"judgment is NOT RUN "
            f"({'--offline' if ctx.offline else 'no node'}) — parity is NOT "
            f"verified, and this stage does not assert it")
        outcome.evidence.append(_evidence(
            "probe", "node", "absent or suppressed; JS half unverified"))
        outcome.remediation.append(_remediation(
            "re-run without --offline on a machine with node",
            "python …/verify_workflow.py dsh-doctor --stage S4",
            "both renderers' hashes compared"))
        return outcome
    try:
        js_hash, js_leftovers = _js_render(ctx.root, template, rendered)
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        outcome.verdict = VERDICT_FAIL
        outcome.reason = f"the JS renderer could not be exercised: {error}"
        outcome.findings.append(outcome.reason)
        return outcome
    outcome.credible_face["js_render_sha256"] = js_hash
    if js_leftovers:
        outcome.verdict = VERDICT_FAIL
        outcome.reason = f"the JS renderer left tokens behind: {js_leftovers}"
        outcome.findings.append(outcome.reason)
        return outcome
    if js_hash != python_hash:
        outcome.verdict = VERDICT_FAIL
        outcome.reason = (f"renderer divergence: JS {js_hash[:12]}… != Python "
                          f"{python_hash[:12]}… — the two delivery paths would "
                          f"install different presets")
        outcome.findings.append(outcome.reason)
        outcome.remediation.append(_remediation(
            "align the two renderers on the contract's token table",
            "python -m unittest discover -s skills/software-project-governance/infra/tests -p test_dsh_adapter.py",
            "identical sha256 from both renderers"))
        return outcome
    outcome.verdict = VERDICT_PASS
    outcome.reason = (f"both renderers produce byte-identical output "
                      f"(sha256 {python_hash[:16]}…); no token residue")
    outcome.evidence.append(_evidence("test", "renderer parity",
                                      f"sha256 {python_hash}"))
    outcome.findings.append(
        "the customSkillDirs scanner ↔ probe differential (G05-c) and the "
        "`{{model}}`/`{{cwd}}` interpolation behaviour (T-6) remain unverified "
        "here: the scanner's own result is disclosed as such, not as verified")
    return outcome


def _python_render(root: Path) -> str:
    """The launcher's own ``render_composition()``, loaded from its file.

    Imported by path (not via ``sys.path``) so this module never shadows or is
    shadowed by the launcher, and never triggers the harness's host-row module.
    """
    import importlib.util

    launcher = root / _get(_contract_facts(), "own.paths.launcher",
                           "adapters/dsh/launch.py")
    if not launcher.is_file():
        raise OSError(f"launcher missing: {launcher}")
    spec = importlib.util.spec_from_file_location("_spg_launch_render", launcher)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.render_composition()


def _sha256_text(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _js_render(root: Path, template: Path,
               python_render: Optional[str] = None) -> Tuple[str, List[str]]:
    """Render through ``lib/index.js`` in a child process; return (sha, leftovers).

    A separate process on purpose: the host row is one "please never throw"
    boundary (J-2), so a renderer defect must not be able to take the diagnostic
    run down with it. The child writes nothing — it prints one JSON line.

    When ``python_render`` is given (the launcher's own output), the JS side is
    called with the *same* repository-root argument the launcher resolved for
    itself, so the two args describe the same package root and the hashes are
    comparable. Disagreeing roots would make the parity judgment measure the
    argument rather than the renderers.
    """
    node = _which("node")
    if not node:
        raise OSError("node is not on PATH")
    lib = (root / _get(_contract_facts(), "own.host_row.entry", "lib/index.js"))
    # The import specifier is interpolated into the ``-e`` program rather than
    # taken from argv: `import {…} from <expression>` is not valid module
    # syntax, so a dynamic specifier has to be spelled at build time. The value
    # is a JSON-quoted file URL, so it cannot break out of the string.
    script = (
        f"import {{ renderComposition }} from {json.dumps(lib.resolve().as_uri())};"
        "import { readFileSync } from 'node:fs';"
        "const t = readFileSync(process.argv[1], 'utf8');"
        "const out = renderComposition(t, process.argv[2]);"
        "process.stdout.write(JSON.stringify({text: out.text,"
        " leftovers: out.leftovers}));"
    )
    proc = subprocess.run(
        [node, "--input-type=module", "-e", script, str(template),
         str(root).replace("\\", "/")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=120,
    )
    if proc.returncode != 0:
        raise ValueError((proc.stderr or "").strip()[:200] or "node exited non-zero")
    payload = json.loads(proc.stdout)
    return _sha256_text(payload["text"]), list(payload.get("leftovers") or ())


# ── S5 ──────────────────────────────────────────────────────────────────────


def stage_s5_host_entry(ctx: Context) -> StageOutcome:
    """S5 — the host entry face: refused by default, disclosed as NOT_RUN.

    ``dsh --dump-config`` reads and writes the host's own composition plane, so
    the default is ``NOT_RUN`` and the authorised form requires the caller to
    pass ``--allow-host-probe`` *after* satisfying one of M7.7 R1's three
    options. The doctor does not perform that verification itself — it refuses
    to guess, which is the honest behavior when the guard cannot be checked from
    inside the process it protects.
    """
    outcome = StageOutcome("S5", "host entry", VERDICT_NOT_RUN, "")
    command = _get(_contract_facts(), "host.cli.dump_config_command",
                   "dsh --profile <name> --dump-config")
    outcome.credible_face = {"authorized": ctx.allow_host_probe,
                             "command": command}
    if not ctx.allow_host_probe:
        outcome.reason = ("NOT_RUN(requires --allow-host-probe): the host entry "
                          "plane has no offline path (T-2 untouched), and the "
                          "probe is refused unless R1 isolation/backup/"
                          "authorisation is satisfied first")
        outcome.remediation.append(_remediation(
            "satisfy one of M7.7 R1's three options, then pass "
            "--allow-host-probe",
            f"{command} (before/after diff)",
            "existing rows unchanged and exactly one row added (DEC-188 ②)"))
        outcome.evidence.append(_evidence("probe", "host entry", "refused by default"))
        return outcome
    if ctx.offline:
        outcome.reason = ("--offline forbids the host probe even though "
                          "--allow-host-probe was given")
        return outcome
    dsh = _which("dsh")
    if not dsh:
        outcome.reason = ("the dsh CLI is not on PATH — the authorised probe "
                          "cannot run")
        return outcome
    outcome.verdict = VERDICT_NOT_RUN
    outcome.reason = ("authorised host probe requested: the executer is the "
                      "caller's shell in the current slice (the doctor reports "
                      "the command and the expected diff rather than running an "
                      "opaque host mutation on the user's behalf)")
    outcome.remediation.append(_remediation(
        "run the documented before/after diff and compare the two outputs",
        command, "existing rows unchanged; exactly one row added"))
    outcome.evidence.append(_evidence("file", "own.notes.single_source_of_truth",
                                      "S5 stays NOT_RUN by design (O-7 default off)"))
    return outcome


# ── S6 ──────────────────────────────────────────────────────────────────────


def run_isolated_smoke(root: Optional[Path] = None, timeout: int = 120) -> Dict[str, Any]:
    """Run the isolated preset-session smoke and return its structured result.

    A *dispatcher*, not a second implementation: the smoke itself lives in
    ``verify_workflow.check_dsh_preset_smoke`` (one owner, one implementation —
    reimplementing it here would create the second verdict R0 BT-R-02 forbids).
    Imported function-locally so this module stays importable when the engine is
    the broken component.
    """
    root = Path(root) if root is not None else _repo_root()
    engine = root / "skills" / "software-project-governance" / "infra"
    if str(engine) not in sys.path:
        sys.path.insert(0, str(engine))
    from verify_workflow import check_dsh_preset_smoke  # noqa: PLC0415 — lazy

    return check_dsh_preset_smoke(timeout=timeout)


def _unverified_due_to_env(ctx: Context) -> List[str]:
    """The environment-gated faces of the contract (D-67/D-68 / §4.6).

    Read from ``coverage.entries[].requires`` rather than restated, so the
    coverage declaration stays the single source of what may be skipped — and
    so a green smoke cannot claim to have covered them.
    """
    facts = _contract_facts()
    available = {"node": _which("node") is not None,
                 "dsh-plane": bool(ctx.dsh_home and ctx.dsh_home.is_dir())}
    missing: List[str] = []
    for entry in _get(facts, "coverage.entries", []) or []:
        for requirement in entry.get("requires") or ():
            if available.get(requirement, False):
                continue
            label = f"{requirement} ({entry.get('subject')})"
            if label not in missing:
                missing.append(label)
    return sorted(missing)


def stage_s6_skills(ctx: Context,
                    smoke_runner: Optional[Callable[..., Dict[str, Any]]] = None,
                    ) -> StageOutcome:
    """S6 — the skill catalog / gesture plane, via the isolated smoke."""
    outcome = StageOutcome("S6", "skill catalog/gestures", VERDICT_NOT_RUN, "")
    unverified = _unverified_due_to_env(ctx)
    outcome.credible_face = {"unverified_due_to_env": unverified}
    if ctx.offline or not ctx.subprocess_allowed:
        outcome.reason = ("--offline: the isolated smoke starts a subprocess, so "
                          "the catalog/gesture plane is NOT verified")
        outcome.remediation.append(_remediation(
            "re-run without --offline",
            "python …/verify_workflow.py check-dsh-preset-smoke",
            "the isolated smoke resolves the catalog and the gesture"))
        return outcome
    runner = smoke_runner or run_isolated_smoke
    try:
        result = runner(ctx.root)
    except Exception as error:
        outcome.verdict = VERDICT_FAIL
        outcome.reason = (f"the smoke runner could not be invoked: "
                          f"{type(error).__name__}: {error}")
        outcome.findings.append(outcome.reason)
        return outcome
    isolation = result.get("isolation") or {}
    outcome.credible_face.update({
        "exit_code": result.get("exit_code"),
        "real_home_writes": isolation.get("real_home_writes"),
    })
    outcome.evidence.append(_evidence(
        "test", "check_dsh_preset_smoke",
        f"exit {result.get('exit_code')}; real-home writes "
        f"{isolation.get('real_home_writes')}"))
    if result.get("verdict") == VERDICT_PASS:
        outcome.verdict = VERDICT_PASS
        outcome.reason = (f"{result.get('reason')} — {RESOLUTION_ONLY}")
        if unverified:
            outcome.findings.append(
                "not verified because the environment lacks them: "
                + ", ".join(unverified))
        return outcome
    outcome.verdict = VERDICT_FAIL
    outcome.reason = result.get("reason") or "isolated smoke did not pass"
    outcome.findings.extend((result.get("details") or [])[:10])
    outcome.remediation.append(_remediation(
        "sync the preset and restart the harness",
        "python adapters/dsh/launch.py --sync",
        "the isolated smoke resolves the skill catalog and /governance"))
    return outcome


# ── S7 ──────────────────────────────────────────────────────────────────────


def stage_s7_hooks(ctx: Context) -> StageOutcome:
    """S7 — the hooks/self-upgrade face plus the K-5 projection.

    Advisory where the design says advisory: a project that has not (re)installed
    the hooks is a WARN, not a FAIL — the hooks are a one-time copy into
    ``.git/hooks`` and their absence does not break the boundary. A hook whose
    *path expression* drifted is a FAIL, because that is the contract being
    contradicted, and that judgment is K-5's (projected, not recomputed).
    """
    outcome = StageOutcome("S7", "hooks/self-upgrade", VERDICT_NOT_RUN, "")
    boundary, _failed = _boundary_stage(ctx, ("K-5", "K-11", "K-13"))
    k5 = boundary["entries"][0] or {}
    outcome.evidence.append(_evidence("check", "28w/K-5", boundary["detail"]))
    hooks_dir = ctx.root / "skills" / "software-project-governance" / "infra" / "hooks"
    installed = ctx.root / ".git" / "hooks"
    outcome.credible_face = {
        "source_hooks": sorted(path.name for path in hooks_dir.glob("*")
                               if path.is_file() and not path.name.endswith(".pyc")),
        "installed_hooks": sorted(path.name for path in installed.glob("*")
                                  if path.is_file()) if installed.is_dir() else [],
        "hook_path_check": k5.get("verdict"),
    }
    if k5.get("verdict") == VERDICT_FAIL:
        outcome.verdict = VERDICT_FAIL
        outcome.reason = f"K-5 (hook path expression): {k5.get('reason')}"
        outcome.findings.extend(k5.get("findings") or [])
        outcome.remediation.append(_remediation(
            "align the hooks with the contract's preset root",
            "", "the hook expression equals the declared expression"))
        return outcome
    missing = [name for name in ("pre-commit", "commit-msg", "post-commit")
               if not (installed / name).is_file()]
    if missing:
        outcome.reason = (f"hooks not installed in this repository: {missing} "
                          f"(advisory — the boundary itself is intact)")
        outcome.remediation.append(_remediation(
            "install the governance hooks (one-time copy)",
            'cp "<plugin>/skills/software-project-governance/infra/hooks/"* .git/hooks/',
            "the three hooks exist under .git/hooks/"))
        return outcome
    outcome.verdict = VERDICT_PASS
    outcome.reason = ("the three hooks are installed and their path expression "
                      "equals the contract's; persona/bootstrap version "
                      "projections are checked by `check-projection-sync`")
    return outcome


# ── stage dispatch ──────────────────────────────────────────────────────────

StageRunner = Callable[[Context], StageOutcome]


def _stage_runners(compat_runner: Optional[Callable[[], Dict[str, Any]]] = None,
                   smoke_runner: Optional[Callable[..., Dict[str, Any]]] = None,
                   ) -> Dict[str, StageRunner]:
    return {
        "S0": stage_s0_input,
        "S1": stage_s1_delivery,
        "S2": lambda ctx: stage_s2_rows(ctx, compat_runner=compat_runner),
        "S3": stage_s3_plane,
        "S4": stage_s4_render,
        "S5": stage_s5_host_entry,
        "S6": lambda ctx: stage_s6_skills(ctx, smoke_runner=smoke_runner),
        "S7": stage_s7_hooks,
    }


def _crashed(stage: str, title: str, error: BaseException) -> StageOutcome:
    """The BT-2 degradation: a crashed stage is NOT_RUN, never a dead doctor."""
    return StageOutcome(
        stage=stage, title=title, verdict=VERDICT_NOT_RUN,
        reason=f"stage crashed: {type(error).__name__}: {error}",
        stage_error=True,
        findings=[f"stage crashed: {type(error).__name__}: {error}"],
        credible_face={"crashed": True},
    )


def run_doctor(root: Optional[Path] = None,
               *, offline: bool = False,
               allow_host_probe: bool = False,
               stages: Optional[Sequence[str]] = None,
               env: Optional[Dict[str, str]] = None,
               compat_runner: Optional[Callable[[], Dict[str, Any]]] = None,
               smoke_runner: Optional[Callable[..., Dict[str, Any]]] = None,
               inject: Optional[Dict[str, BaseException]] = None,
               ) -> Dict[str, Any]:
    """Run the S0–S7 stages and return the machine-readable report.

    ``inject`` is the ``--selftest`` seam: a stage named there raises before it
    runs, which is how the crash-isolation rule is itself machine-checked
    instead of asserted.
    """
    root = Path(root) if root is not None else _repo_root()
    wanted = tuple(stages) if stages else tuple(ident for ident, _ in STAGES)
    unknown = [item for item in wanted if item not in dict(STAGES)]
    if unknown:
        raise Refused(f"unknown stage(s): {unknown} (known: "
                      f"{[ident for ident, _ in STAGES]})")
    ctx = Context(
        root=root,
        offline=offline,
        allow_host_probe=allow_host_probe,
        stages_wanted=wanted,
        env=dict(os.environ if env is None else env),
    )
    runners = _stage_runners(compat_runner, smoke_runner)
    records: List[Dict[str, Any]] = []
    prelude: List[Dict[str, Any]] = []
    # F-07: S0 resolves `ctx.dsh_home` for every later stage. A `--stage` subset
    # that omits it used to lose that resolution and blame the *home* ("no
    # resolved DSH_HOME") for a restriction the caller had asked for. S0 is
    # record-only and side-effect free, so running it as an explicit prelude is
    # both safe and the honest behavior — and it is disclosed, not hidden.
    if "S0" not in wanted and any(ident != "S0" for ident in wanted):
        try:
            record = runners["S0"](ctx).as_dict()
        except Exception as error:  # noqa: BLE001 — same degradation as a stage
            record = _crashed("S0", dict(STAGES)["S0"], error).as_dict()
        prelude.append({
            "stage": "S0",
            "title": dict(STAGES)["S0"],
            "why": "resolves ctx.dsh_home for the requested stages",
            "verdict": record["verdict"],
            "reason": record["reason"],
        })
    for ident, title in STAGES:
        if ident not in wanted:
            continue
        injected = (inject or {}).get(ident)
        if injected is not None:
            records.append(_crashed(ident, title, injected).as_dict())
            continue
        try:
            records.append(runners[ident](ctx).as_dict())
        except Exception as error:  # noqa: BLE001 — the whole point of BT-2
            records.append(_crashed(ident, title, error).as_dict())
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "command": COMMAND_NAME,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "host": {
            "dsh_version": _get(_contract_facts(), "evidence.dsh_cli_version"),
            "plane": _get(_contract_facts(), "evidence.plane.source"),
            "node_version": (records[0].get("credible_face", {}).get("node_version")
                             if records else None),
            "dsh_home": str(ctx.dsh_home) if ctx.dsh_home else None,
        },
        "offline": offline,
        "stages": records,
        "prelude": prelude,
    }
    # K-12 (R0 BT-R-02 / R1 N-3): the single-verdict comparison is defined only
    # for a run in which every stage actually ran. Under --offline the boundary
    # report is still rendered as evidence, but it is not compared — the
    # offline run is a *disclosure* about the host plane, not a gate verdict.
    boundary = ctx.boundary_report or {}
    criteria = {entry["id"]: entry["verdict"] for entry in boundary.get("criteria", [])}
    report["boundary"] = {
        "check": "28w",
        "verdict": boundary.get("verdict"),
        "criteria": criteria,
        "compared": (not offline) and all(ident in wanted for ident, _ in STAGES),
    }
    if report["boundary"]["compared"]:
        doctor_failed = any(record["verdict"] == VERDICT_FAIL for record in records)
        boundary_failed = (boundary.get("verdict") == VERDICT_FAIL)
        report["boundary"]["agrees"] = (doctor_failed == boundary_failed)
        if not report["boundary"]["agrees"]:
            records.append(StageOutcome(
                "K-12", "single verdict (doctor ↔ boundary)", VERDICT_FAIL,
                f"doctor/boundary verdict disagreement: doctor="
                f"{'FAIL' if doctor_failed else 'PASS'} boundary="
                f"{boundary.get('verdict')}",
                findings=[f"doctor and Check 28w disagree about the same "
                          f"repository state (boundary issues: "
                          f"{ctx.boundary_issues})"],
                remediation=[_remediation(
                    "fix whichever side is wrong; the two surfaces must agree",
                    "python …/verify_workflow.py check-dsh-boundary --fail-on-issues",
                    "doctor exit code == boundary exit code")],
            ).as_dict())
    else:
        report["boundary"]["agrees"] = None
        reasons = []
        if offline:
            reasons.append("--offline: K-12's comparison is not defined for a run "
                           "that did not execute every stage (R1 N-3); the "
                           "boundary verdict above is reported as evidence only")
        if not all(ident in wanted for ident, _ in STAGES):
            reasons.append(f"partial run (--stage): the comparison needs all "
                           f"{len(STAGES)} stages; requested "
                           f"{sorted(wanted)}")
        report["boundary"]["note"] = "; ".join(reasons)
    report["verdict"] = ("FAIL" if any(record["verdict"] == VERDICT_FAIL
                                       for record in records) else
                         ("PASS" if any(record["verdict"] == VERDICT_PASS
                                        for record in records) else VERDICT_NOT_RUN))
    report["exit_code"] = exit_code_for(report)
    return report


def exit_code_for(report: Dict[str, Any]) -> int:
    """``0`` no FAIL, ``1`` some FAIL — the §5.1 mapping (REFUSED is 2, raised)."""
    return EXIT_FAIL if report.get("verdict") == VERDICT_FAIL else EXIT_OK


# ── --selftest ──────────────────────────────────────────────────────────────


def run_self_test(root: Optional[Path] = None) -> Dict[str, Any]:
    """Inject an exception into each stage in turn; assert the isolation rules.

    The doctor's own negative gate (design §5.1): for every stage, crashing it
    must (a) leave *that* stage ``NOT_RUN`` with ``stage_error``, (b) leave the
    other stages producing their records, (c) leave the total at eight, and
    (d) not turn the top-level verdict green *because of* the crash. A doctor
    that fails these is not a degraded doctor, it is a misleading one.
    """
    root = Path(root) if root is not None else _repo_root()
    cases: List[Dict[str, Any]] = []
    ok = True
    ids = [ident for ident, _ in STAGES]
    for ident in ids:
        report = run_doctor(root, offline=True, inject={ident: Boom(ident)})
        records = {record["stage"]: record for record in report["stages"]}
        crashed = records.get(ident, {})
        case_ok = (
            len(report["stages"]) == len(ids)
            and crashed.get("verdict") == VERDICT_NOT_RUN
            and crashed.get("stage_error") is True
            and all(records[name].get("stage_error") is not True
                    for name in ids if name != ident)
            and report["verdict"] in (VERDICT_NOT_RUN, VERDICT_FAIL, VERDICT_PASS)
        )
        # (d) the crash must not manufacture a PASS on its own: a verdict of
        # PASS is acceptable only when a *non-crashed* stage genuinely passed.
        manufactured = (report["verdict"] == VERDICT_PASS
                        and crash_is_the_only_pass(records, ident))
        case_ok = case_ok and not manufactured
        ok = ok and case_ok
        cases.append({
            "stage": ident,
            "ok": case_ok,
            "stage_count": len(report["stages"]),
            "crashed_verdict": crashed.get("verdict"),
            "crashed_stage_error": crashed.get("stage_error"),
            "verdict": report["verdict"],
            "exit_code": report["exit_code"],
        })
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "command": COMMAND_NAME,
        "selftest": True,
        "ok": ok,
        "cases": cases,
        "verdict": VERDICT_PASS if ok else VERDICT_FAIL,
    }


class Boom(RuntimeError):
    """The injected crash the self-test uses (named so the message is readable)."""

    def __init__(self, stage: str):
        super().__init__(f"injected crash for {stage} (--selftest)")
        self.stage = stage


def crash_is_the_only_pass(records: Dict[str, Dict[str, Any]], ident: str) -> bool:
    """Whether a PASS verdict could only have come from the crashed stage.

    Confirms the intent of ``--selftest``: the crashed stage reported
    ``NOT_RUN`` (never PASS), so a top-level PASS must trace to some other
    stage that really passed.
    """
    return all(record.get("verdict") != VERDICT_PASS
               for name, record in records.items() if name != ident)


# ── --rehearse ──────────────────────────────────────────────────────────────


def rehearse(candidate_path: Path, baseline_path: Path,
             *, ttl_days: Optional[int] = None,
             today: Optional[Any] = None) -> Dict[str, Any]:
    """Replay a recorded host-facts candidate against a baseline (design §5.5).

    The replay reads *recorded facts*, so it can catch contract-surface drift
    (a package that vanished, a module that no longer resolves, an API symbol
    that moved, a config key that stopped being accepted) and it cannot catch
    anything the record does not contain — the honesty boundary §5.5 states. Two
    rules keep it from being reassuring in the wrong direction: a same-version
    replay and a time-reversed pair are FAILs, and every row that came from a
    *synthetic* mutation is labelled, because a synthetic drift proves the
    rehearsal works, not that the upgrade is safe (R0 BT-R-03).
    """
    loads: Dict[str, Any] = {}
    findings: List[str] = []
    for label, path in (("candidate", Path(candidate_path)),
                        ("baseline", Path(baseline_path))):
        try:
            document = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError) as error:
            raise Refused(f"cannot read the {label} fixture {path}: "
                          f"{type(error).__name__}: {error}")
        except ValueError as error:
            raise Refused(f"the {label} fixture {path} is not valid JSON: {error}")
        if not isinstance(document, dict):
            raise Refused(f"the {label} fixture {path} must be a JSON object")
        loads[label] = document
    candidate, baseline = loads["candidate"], loads["baseline"]

    if ttl_days is None:
        facts = _contract_facts()
        ttl_days = _get(facts, "evidence.verified_on_ttl_days", DEFAULT_TTL_DAYS)
    boundary_module = _load_boundary_module()
    preconditions = boundary_module.rehearsal_findings(
        baseline, candidate, ttl_days=ttl_days,
        today=today or datetime.now(timezone.utc).date())
    findings.extend(preconditions)

    drift: List[Dict[str, Any]] = []

    def record(kind: str, subject: str, detail: str, synthetic: bool) -> None:
        drift.append({"kind": kind, "subject": subject, "detail": detail,
                      "synthetic": synthetic})

    base_packages = _factsheet_packages(baseline)
    cand_packages = _factsheet_packages(candidate)
    for name in sorted(set(base_packages) - set(cand_packages)):
        record("contract", f"package:{name}",
               f"package disappeared from the candidate plane "
               f"(was {base_packages[name]})", _synthetic(candidate, name))
    for name in sorted(set(base_packages) & set(cand_packages)):
        if base_packages[name] != cand_packages[name]:
            record("declaration", f"package:{name}",
                   f"version moved {base_packages[name]} → {cand_packages[name]}",
                   _synthetic(candidate, name))
    for name in sorted(set(cand_packages) - set(base_packages)):
        record("declaration", f"package:{name}",
               f"package appeared in the candidate plane "
               f"({cand_packages[name]}) — not previously measured",
               _synthetic(candidate, name))

    base_symbols = set(baseline.get("api_symbols") or ())
    cand_symbols = set(candidate.get("api_symbols") or ())
    for symbol in sorted(base_symbols - cand_symbols):
        record("contract", f"api_symbol:{symbol}",
               "API symbol no longer resolved", _synthetic(candidate, symbol))

    base_rows = _factsheet_rows(baseline)
    cand_rows = _factsheet_rows(candidate)
    for row_id in sorted(set(base_rows) - set(cand_rows)):
        record("contract", f"row:{row_id}",
               "row disappeared from the candidate plane",
               _synthetic(candidate, row_id))
    for row_id in sorted(set(base_rows) & set(cand_rows)):
        base_row, cand_row = base_rows[row_id], cand_rows[row_id]
        if base_row.get("resolved") and not cand_row.get("resolved"):
            record("contract", f"row:{row_id}",
                   "module no longer resolves", _synthetic(candidate, row_id))
        if base_row.get("probe_result") != "reject" and cand_row.get("probe_result") == "reject":
            record("behaviour", f"row:{row_id}",
                   "our config is now REJECTED by the row's schema",
                   _synthetic(candidate, row_id))
        added = sorted(set(cand_row.get("required_keys") or ())
                       - set(base_row.get("required_keys") or ()))
        if added:
            record("behaviour", f"row:{row_id}",
                   f"new required key(s): {added}", _synthetic(candidate, row_id))
        dropped = sorted(set(cand_row.get("accepted_keys") or ())
                         - set(base_row.get("accepted_keys") or ()))
        if dropped:
            record("behaviour", f"row:{row_id}",
                   f"newly accepted key(s) (informational): {dropped}",
                   _synthetic(candidate, row_id))

    facts = _contract_facts()
    declared_version = _get(facts, "evidence.dsh_cli_version")
    declared_verified = _get(facts, "evidence.verified_on")
    if declared_version and candidate.get("dsh_version") and \
            candidate["dsh_version"] != declared_version:
        findings.append(
            f"[EVIDENCE-STALE] the candidate records dsh "
            f"{candidate['dsh_version']} but the contract records "
            f"{declared_version} — re-record the evidence")
    if declared_verified and candidate.get("captured_at") and \
            str(candidate["captured_at"])[10:] not in str(declared_verified):
        findings.append(
            f"[EVIDENCE-STALE] the candidate was captured "
            f"{candidate['captured_at']} but the contract's `verified_on` is "
            f"{declared_verified}")
    if any(item["synthetic"] for item in drift):
        findings.append(
            "this run contains synthetic mutations: it proves the rehearsal "
            "mechanism can see drift, NOT that a real upgrade is safe")
    verdict = VERDICT_FAIL if (findings or _drift_is_material(drift)) else VERDICT_PASS
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "command": COMMAND_NAME,
        "rehearsal": True,
        "candidate": str(Path(candidate_path)),
        "baseline": str(Path(baseline_path)),
        "baseline_version": baseline.get("dsh_version"),
        "candidate_version": candidate.get("dsh_version"),
        "ttl_days": ttl_days,
        "verdict": verdict,
        "exit_code": EXIT_FAIL if verdict == VERDICT_FAIL else EXIT_OK,
        "findings": findings,
        "drift": drift,
        "synthetic_rows": [item["subject"] for item in drift if item["synthetic"]],
    }


def _drift_is_material(drift: Sequence[Dict[str, Any]]) -> bool:
    """Material drift = anything other than an informational addition."""
    return any(item["kind"] in ("contract", "behaviour") for item in drift)


def _synthetic(document: Dict[str, Any], subject: str) -> bool:
    """Whether this record — or the named subject inside it — is synthetic."""
    if document.get("synthetic") is True:
        return True
    for key in ("synthetic_subjects", "synthetic_rows"):
        values = document.get(key)
        if isinstance(values, (list, tuple)) and subject in values:
            return True
    return False


def _factsheet_packages(document: Dict[str, Any]) -> Dict[str, Any]:
    packages = document.get("oracle_packages") or document.get("packages") or {}
    return {str(key): value for key, value in packages.items()} \
        if isinstance(packages, dict) else {}


def _factsheet_rows(document: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    rows = document.get("rows") or ()
    result: Dict[str, Dict[str, Any]] = {}
    if isinstance(rows, dict):
        for key, value in rows.items():
            if isinstance(value, dict):
                value.setdefault("row_id", key)
                result[str(key)] = value
        return result
    for row in rows:
        if isinstance(row, dict):
            key = row.get("row_id") or row.get("module")
            if key:
                result[str(key)] = row
    return result


# ── --record-evidence ───────────────────────────────────────────────────────


def record_evidence(root: Optional[Path] = None,
                    *, out: Optional[Path] = None,
                    env: Optional[Dict[str, str]] = None,
                    ) -> Dict[str, Any]:
    """Probe the plane under a redirected home and write the factsheet.

    The single writing path of the whole slice. Two properties make it safe to
    run on a real machine: it never writes outside ``out`` (and refuses to write
    *into* the package unless asked by absolute path), and the probing part is
    the guard's own read-only discovery — the contract itself is **not** written
    here, because `--record-evidence` in this slice records the *fixture*; the
    contract's ``evidence.*`` fields follow the same measured values and are
    updated by the maintainer in the reviewed commit that lands the fixture
    (a write to the contract from a probe would make the single source of truth
    machine-mutable without review).
    """
    root = Path(root) if root is not None else _repo_root()
    env = dict(os.environ if env is None else env)
    outcome: Dict[str, Any] = {"command": COMMAND_NAME, "record_evidence": True}
    infra = Path(__file__).resolve().parent
    if str(infra) not in sys.path:
        sys.path.insert(0, str(infra))
    import dsh_compat  # noqa: PLC0415 — deliberate, lazy

    install = dsh_compat.locate_dsh_install(env)
    node_modules = install.get("node_modules")
    packages = install.get("oracle_packages") or {}
    if not packages and node_modules:
        try:
            packages = dsh_compat._oracle_versions(Path(node_modules))  # noqa: SLF001
        except Exception:  # pragma: no cover - defensive
            packages = {}
    # The CLI version is read from the anchor the guard itself resolved
    # (`locate_dsh_install` returns the measurement it made) — never restated,
    # never defaulted: an unresolved plane records `null` and says so.
    cli_version = install.get("dsh_version")
    if not cli_version:
        cli_version = _read_cli_version(install)
    facts = _contract_facts()
    composition = (root / _get(facts, "own.preset.template",
                              "agent-presets/governance/agent.cordis.yml.template"))
    compositions = []
    if composition.is_file():
        compositions = [composition.relative_to(root).as_posix()]
    captured_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    document = {
        "schema_version": 1,
        "dsh_version": cli_version,
        "captured_at": captured_at,
        "synthetic": False,
        "provenance": (f"{COMMAND_NAME} --record-evidence; plane="
                       f"{install.get('anchor') or install.get('source') or 'unknown'}; "
                       f"node_modules={node_modules}"),
        "plane": {
            "source": install.get("source"),
            "node_modules": str(node_modules) if node_modules else None,
        },
        "oracle_packages": packages,
        "api_symbols": sorted(dsh_compat.oracle_api_symbols()),
        "rows": _record_rows(root, env),
        # True of this command in every invocation, isolated or not: it reads
        # the plane it resolved (named in `provenance`/`plane`) and writes only
        # the file named by `--out`. The *requirement* to redirect `DSH_HOME`
        # when recording belongs to the operating procedure, not to this field —
        # a note that asserted isolation would be a claim the tool cannot check.
        "notes": ("read-only discovery of the resolved plane (see `provenance` "
                  "and `plane`); the only file this command writes is the one "
                  "named by `--out`"),
    }
    target = Path(out) if out is not None else (
        root / "adapters" / "dsh" / "fixtures"
        / f"host-facts-{cli_version or 'unrecorded'}.json")
    _guard_out_target(target, root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    outcome.update({
        "out": str(target),
        "dsh_version": cli_version,
        "captured_at": captured_at,
        "oracle_packages": packages,
    })
    return outcome


#: The only artifact `--record-evidence` owns (design §5.4).
FACTSHEET_NAME_RE = re.compile(r"^host-facts-.+\.json$")


def _guard_out_target(target: Path, root: Path) -> None:
    """Refuse an ``--out`` that would overwrite something this command does not own.

    `--record-evidence` owns exactly one artifact shape — a
    ``host-facts-*.json`` fixture under ``adapters/dsh/fixtures/``. Everything
    else in the package belongs to another owner, and the contract in particular
    is the single source of truth that this slice deliberately keeps out of a
    probe's reach (F-03's adjudication). Three rules follow, all judged on the
    **resolved** path so a `..` detour is refused like a direct one:

      * the contract itself is always refused;
      * an **existing** file whose name is not a factsheet is never overwritten,
        wherever it lives — "silently replaced a file it does not own" is the
        defect F-06 demonstrated;
      * a new target inside the package must be a factsheet under
        ``adapters/dsh/fixtures/``; a new target outside it is the caller's own
        file system.
    """
    resolved = Path(target).resolve()
    contract = _contract_path(root).resolve()
    if resolved == contract:
        raise Refused(
            f"--out refuses the contract itself ({resolved}) — the contract is "
            f"the single source of truth and changes only in a reviewed commit")
    owned_name = bool(FACTSHEET_NAME_RE.match(resolved.name))
    if resolved.is_file() and not owned_name:
        # An existing file this command did not write is never overwritten —
        # anywhere. "Silently replaced a file it does not own" is the defect
        # the reviewer demonstrated, and location does not excuse it.
        raise Refused(
            f"--out refuses to overwrite {resolved}: this command writes only "
            f"`host-facts-*.json` fixtures")
    try:
        relative = resolved.relative_to(Path(root).resolve())
    except ValueError:
        return  # a new file outside the package: the caller's own file system
    if not owned_name:
        raise Refused(
            f"--out refuses {resolved.name!r} inside the package: this command "
            f"owns only `host-facts-*.json` fixtures "
            f"({relative.as_posix()})")
    if relative.parts[:3] != ("adapters", "dsh", "fixtures"):
        raise Refused(
            f"--out refuses {relative.as_posix()}: host-facts fixtures live "
            f"under `adapters/dsh/fixtures/`")


def _contract_path(root: Path) -> Path:
    """The contract path under ``root``, asked of the accessor (never restated)."""
    infra = Path(__file__).resolve().parent
    if str(infra) not in sys.path:
        sys.path.insert(0, str(infra))
    import dsh_contract  # noqa: PLC0415 — deliberate, lazy

    return dsh_contract.contract_path(root)


def _read_cli_version(install: Dict[str, Any]) -> Optional[str]:
    """The installed CLI version, read from its own package.json."""
    anchor = install.get("anchor")
    if anchor:
        text = _read(Path(anchor))
        match = _PACKAGE_VERSION_RE.search(text)
        if match:
            return match.group(1)
    return None


def _record_rows(root: Path, env: Dict[str, str]) -> List[Dict[str, Any]]:
    """Per-row recorded facts for the compositions this package ships.

    Uses the guard's compatibility report when it can run (it is the component
    that knows a row's module and schema); otherwise records the declared row
    set with ``resolved: null`` — never a hand-written claim about a module.
    """
    facts = _contract_facts()
    declared = [row.get("row_id") for row in _get(facts, "host.rows", []) or []]
    records: List[Dict[str, Any]] = []
    report: Dict[str, Any] = {}
    try:
        if _which("node"):
            infra = Path(__file__).resolve().parent
            if str(infra) not in sys.path:
                sys.path.insert(0, str(infra))
            import dsh_compat  # noqa: PLC0415 — deliberate, lazy

            report = dsh_compat.check_dsh_preset_compat(root, env=env)
    except Exception:
        report = {}
    seen: Dict[str, Dict[str, Any]] = {}
    for composition in report.get("compositions") or ():
        for row in composition.get("rows") or ():
            row_id = row.get("row")
            if row_id and row_id not in seen:
                seen[row_id] = row
    for row_id in declared:
        if row_id is None:
            continue
        measured = seen.get(row_id) or {}
        kind = measured.get("kind")
        records.append({
            "row_id": row_id,
            "module": measured.get("name"),
            "resolved": None if not measured else kind not in
                        ("MODULE_UNRESOLVED", "IMPORT_ERROR"),
            "config_export": None if not measured else kind != "NO_SCHEMA",
            "accepted_keys": [],
            "required_keys": [],
            "probe_result": (None if not measured else
                             ("reject" if kind not in ("PASS", "NO_SCHEMA", "BUILTIN")
                              else "accept")),
            "source": "recorded",
        })
    return records


# ── rendering + CLI ─────────────────────────────────────────────────────────

_GLYPH = {VERDICT_PASS: "[PASS]", VERDICT_FAIL: "[FAIL]",
          VERDICT_NOT_RUN: "[NOT_RUN]"}


def render_report(report: Dict[str, Any], stream=None) -> None:
    """Human-readable rendering (the ``--json`` form is the machine contract)."""
    stream = sys.stdout if stream is None else stream
    if report.get("selftest"):
        print(f"\n=== dsh-doctor --selftest ===", file=stream)
        for case in report["cases"]:
            print(f"  {'ok  ' if case['ok'] else 'FAIL'} {case['stage']}: "
                  f"crashed={case['crashed_verdict']}/stage_error="
                  f"{case['crashed_stage_error']} stages={case['stage_count']} "
                  f"verdict={case['verdict']} exit={case['exit_code']}",
                  file=stream)
        print(f"  Result: {report['verdict']}", file=stream)
        return
    if report.get("rehearsal"):
        print(f"\n=== dsh-doctor --rehearse ===", file=stream)
        print(f"  baseline: {report['baseline']} (dsh {report['baseline_version']})",
              file=stream)
        print(f"  candidate: {report['candidate']} (dsh {report['candidate_version']})",
              file=stream)
        for finding in report["findings"]:
            print(f"  - {finding}", file=stream)
        for item in report["drift"]:
            flag = " [synthetic]" if item["synthetic"] else ""
            print(f"  [{item['kind']}] {item['subject']}: {item['detail']}{flag}",
                  file=stream)
        if not report["drift"] and not report["findings"]:
            print("  no drift between the two records", file=stream)
        print(f"  Result: {report['verdict']}", file=stream)
        return
    print(f"\n=== dsh-doctor ({report.get('command')}) ===", file=stream)
    print(f"  host: {report.get('host')}", file=stream)
    for record in report.get("stages", []):
        print(f"  {_GLYPH.get(record['verdict'], record['verdict'])} "
              f"{record['stage']} {record['title']}: {record['reason']}",
              file=stream)
        for finding in record.get("findings", [])[:4]:
            print(f"      - {finding}", file=stream)
    boundary = report.get("boundary") or {}
    if boundary:
        print(f"  28w boundary: verdict={boundary.get('verdict')} "
              f"compared={boundary.get('compared')} "
              f"agrees={boundary.get('agrees')}", file=stream)
        if boundary.get("note"):
            print(f"      {boundary['note']}", file=stream)
    print(f"  Result: {report.get('verdict')} (exit {report.get('exit_code')})",
          file=stream)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry. Returns the exit code (``0``/``1``/``2``, §5.1)."""
    parser = argparse.ArgumentParser(
        prog=COMMAND_NAME,
        description="Single staged diagnostic entry for the dsh dependency "
                    "boundary (S0–S7).")
    parser.add_argument("--json", action="store_true",
                        help="emit the machine-readable report")
    parser.add_argument("--stage", action="append", default=None,
                        metavar="S0..S7", help="run only these stages (repeatable)")
    parser.add_argument("--offline", action="store_true",
                        help="forbid every subprocess and host-plane probe; "
                             "file-level judgments still run")
    parser.add_argument("--selftest", action="store_true",
                        help="crash each stage in turn and assert the isolation rules")
    parser.add_argument("--record-evidence", action="store_true",
                        help="probe the plane (read-only) and write the "
                             "host-facts fixture named by --out")
    parser.add_argument("--out", default=None,
                        help="destination of --record-evidence (default: "
                             "adapters/dsh/fixtures/host-facts-<version>.json)")
    parser.add_argument("--rehearse", default=None, metavar="CANDIDATE.json",
                        help="replay a recorded candidate against --against")
    parser.add_argument("--against", default=None, metavar="BASELINE.json",
                        help="the baseline record to rehearse against")
    parser.add_argument("--allow-host-probe", action="store_true",
                        help="allow the S5 host probe (requires M7.7 R1 to be "
                             "satisfied first; refused otherwise)")
    parser.add_argument("--fail-on-issues", action="store_true",
                        help="exit 1 when a stage FAILs (the default already does)")
    args = parser.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    try:
        if args.selftest:
            report = run_self_test()
        elif args.record_evidence:
            report = record_evidence(out=Path(args.out) if args.out else None)
        elif args.rehearse:
            if not args.against:
                raise Refused("--rehearse requires --against <baseline.json>")
            report = rehearse(Path(args.rehearse), Path(args.against))
        else:
            report = run_doctor(offline=args.offline, stages=args.stage,
                                allow_host_probe=args.allow_host_probe)
    except Refused as error:
        print(f"dsh-doctor refused: {error}", file=sys.stderr)
        return EXIT_REFUSED
    except Exception as error:  # noqa: BLE001 — never leak a stack as a verdict
        print(f"dsh-doctor could not produce a report: "
              f"{type(error).__name__}: {error}", file=sys.stderr)
        return EXIT_REFUSED

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        render_report(report)
    return int(report.get("exit_code", EXIT_OK))


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess
    sys.exit(main())
