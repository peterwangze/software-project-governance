"""Deterministic fixture emitter for the dsh dependency-boundary slices.

FEAT-029 (0.81.0 slice V1), design §5.4 / §6.1 V1⑥ / §7.3:

    python skills/software-project-governance/infra/tests/dsh_fixtures.py \
        --emit-fixture FX-NO-SCHEMA-01 --out <dir>

writes ``<dir>/FX-NO-SCHEMA-01.cordis.yml`` and **the same fixture id produces
byte-identical output on every machine** — that is what makes the acceptance
commands of V3/V4/V5 self-contained instead of depending on a hand-built
composition (§4.4.1⑤ R0 F-11).

Shape of the module:

  * ``FIXTURES`` — id → ``(filename, builder)`` for the fixtures whose bytes are
    fully determined by repository sources today: they are *text mutations* of
    the shipped composition template / patch layer, or minimal compositions
    built from row shapes already measured in AUDIT-153. No consumer behaviour
    is needed to produce them, which is why they belong to the data-layer slice.
  * ``DEFERRED`` — id → ``{slice, reason}`` for the fixtures of §5.6 whose
    bytes need a slice that has not landed yet (V2..V8). ``--emit-fixture``
    reports the owning slice instead of inventing content; the contract's
    ``coverage.entries[].negative_fixtures`` references stay closed over
    ``known_fixture_ids()`` = ``FIXTURES`` ∪ ``DEFERRED`` (§2.8 K-8).

Determinism rules (asserted by ``test_dsh_contract.py``):

  * input text is read as bytes and normalized CRLF → LF before mutation, so a
    checkout with ``core.autocrlf`` cannot change the output;
  * no timestamps, absolute paths, machine names or iteration-order-dependent
    construction enters the payload;
  * output is written as bytes (never through a text-mode newline translation)
    and is UTF-8 except where a fixture's *subject* is invalid UTF-8.
"""

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
_REPO_ROOT = _INFRA_DIR.parents[2]

TEMPLATE = (_REPO_ROOT / "agent-presets" / "governance"
            / "agent.cordis.yml.template")
PATCH_FILE = _REPO_ROOT / "cordis.patch.yml"

# Modules measured by AUDIT-153 (see its §2.4 / §2.8 evidence column):
#   * `@deepseek-ai/dsh-tool-ask-user` — exports no `Config` (D-44), so it is
#     the honest subject for a "row without schema" fixture;
#   * `@deepseek-ai/dsh-tool-todo` — schema-bearing row (D-44), used as the
#     child of a group when the fixture needs one.
NO_SCHEMA_MODULE = "@deepseek-ai/dsh-tool-ask-user"
SCHEMA_MODULE = "@deepseek-ai/dsh-tool-todo"
PERSONA_MODULE = "@deepseek-ai/dsh-persona"
SKILL_FS_MODULE = "@deepseek-ai/dsh-skill-filesystem"

#: Design §4.4.1④: the config key that must be rejected if the row's schema
#: were consulted at all.
BOGUS_KEY = "totallyBogusKeyThatMustBeRejected"
#: Design §4.4.2 / existing `test_dsh_compat.py:754` fixture expression.
THROWING_GROUP_EXPR = '!!js "(() => { throw new Error(\'group-boom\') })()"'


def _template_text():
    """The shipped composition template, CRLF-normalized (LF only)."""
    return (TEMPLATE.read_bytes().decode("utf-8").replace("\r\n", "\n"))


def _patch_text():
    return (PATCH_FILE.read_bytes().decode("utf-8").replace("\r\n", "\n"))


def _replace_once(text, needle, replacement):
    if text.count(needle) != 1:
        raise AssertionError(
            f"expected exactly one occurrence of {needle!r}, found "
            f"{text.count(needle)}")
    return text.replace(needle, replacement)


def _replace_all(text, needle, replacement):
    if needle not in text:
        raise AssertionError(f"expected at least one occurrence of {needle!r}")
    return text.replace(needle, replacement)


# ── composition-level fixtures (base composition + named mutation) ──────────


def _fixture_no_schema_only():
    """FX-NO-SCHEMA-01 — one row whose module exports no `Config`, plus a
    config key that a schema would reject. Design §4.4.1④: the expected
    verdict is `NOT_RUN`, **never** PASS."""
    return (
        "- id: tool-ask-user\n"
        f"  name: '{NO_SCHEMA_MODULE}'\n"
        "  config:\n"
        f"    {BOGUS_KEY}: 12345\n")


def _fixture_no_schema_mixed():
    """FX-NO-SCHEMA-02 — one schema-bearing row (PASS) + one row without a
    schema, so a partially verified run must disclose the unverified row
    (§4.4.1④, C-6)."""
    return (
        "- id: persona\n"
        f"  name: '{PERSONA_MODULE}'\n"
        "  config:\n"
        "    prefix: 'fixture: schema-bearing row (PASS expected)'\n"
        "- id: tool-ask-user\n"
        f"  name: '{NO_SCHEMA_MODULE}'\n"
        "  config:\n"
        f"    {BOGUS_KEY}: 12345\n")


def _fixture_group_name_unresolved():
    """FX-GROUP-01 — `name: cordis:gruop` (the §5.6 typo): only
    `cordis:group` is a measured builtin, so this must be a
    `GROUP_NAME_UNRESOLVED` finding (G02-b, fail-closed)."""
    return (
        "- id: planning\n"
        "  name: cordis:gruop\n"
        "  group: true\n"
        "  config:\n"
        f"    - id: tool-todo\n"
        f"      name: '{SCHEMA_MODULE}'\n")


def _fixture_group_throwing_without_children():
    """FX-GROUP-02 — a group with a throwing `disabled` and **no** children:
    nothing can inherit it, so the loader never evaluates it and this is not a
    finding (G03-c)."""
    return (
        "- id: planning\n"
        "  name: cordis:group\n"
        "  group: true\n"
        f"  disabled: {THROWING_GROUP_EXPR}\n"
        "  config: []\n")


def _fixture_group_throwing_with_children():
    """FX-GROUP-03 — same group, one child: the child's ancestor walk
    evaluates the throwing expression, so the run FAILs **and** the child must
    be disclosed (`rows_inherited_unverified >= 1`, G03-b)."""
    return (
        "- id: planning\n"
        "  name: cordis:group\n"
        "  group: true\n"
        f"  disabled: {THROWING_GROUP_EXPR}\n"
        "  config:\n"
        f"    - id: tool-todo\n"
        f"      name: '{SCHEMA_MODULE}'\n")


def _fixture_same_indent_custom_skill_dirs():
    """FX-CSD-01 — the block sequence at the *same* indentation as its key:
    legal YAML that the hand-written scanner of `launch.py:459` misses
    (`<=` early break, G-05)."""
    template = _template_text()
    block = ("    customSkillDirs:\n"
             "    - '__GOVERNANCE_SKILLS_ROOT__'\n"
             "    - '__GOVERNANCE_SHIMS_ROOT__'\n")
    return _replace_once(
        template,
        "    customSkillDirs:\n"
        "      - '__GOVERNANCE_SKILLS_ROOT__'\n"
        "      - '__GOVERNANCE_SHIMS_ROOT__'\n",
        block)


def _fixture_relative_skill_dir():
    """FX-CSD-02 — a literal relative `customSkillDirs` entry: resolved against
    the dsh process CWD, it silently empties the catalog (§2.3 / G-05 area)."""
    template = _template_text()
    return _replace_once(
        template, "      - '__GOVERNANCE_SHIMS_ROOT__'\n",
        "      - 'adapters/dsh/skill-shims'\n")


def _fixture_rotten_report_bytes():
    """FX-UTF8-01 — a composition whose bytes are not valid UTF-8: the failure
    must be a structured one, not an uncaught `UnicodeDecodeError` (G-10)."""
    return (
        b"- id: persona\n"
        b"  name: '@deepseek-ai/dsh-persona'\n"
        b"  config:\n"
        b"    prefix: '\xff invalid utf-8 fixture'\n")


# ── template-level fixtures ─────────────────────────────────────────────────


def _fixture_isolated_cr():
    """FX-CR-01 — the shipped template with exactly one isolated CR (no CRLF):
    `lib/index.js` normalizes only `\\r\\n` while the Python renderer's text
    mode normalizes every CR, so the two renderers disagree (D-66/G-10)."""
    return _template_text() + "\n# FX-CR-01 isolated-CR probe: X\rY\n"


def _fixture_misspelt_all_caps_token():
    """FX-TOKEN-01 — `__GOVERNANCE_SKILLS_ROOTS__` (the all-caps misspelling):
    the known-token bail-out of `launch.py:153` cannot see it (G-08)."""
    return _replace_once(
        _template_text(), "__GOVERNANCE_SKILLS_ROOT__",
        "__GOVERNANCE_SKILLS_ROOTS__")


def _fixture_misspelt_mixed_case_token():
    """FX-TOKEN-02 — `__Governance_Repo_Root__`: the mixed-case misspelling
    that the old `[A-Z0-9_]+` leftover scan cannot see (G-07). Both shipped
    occurrences (the header note and the persona body) are renamed, so the
    template really carries no valid repo-root token any more."""
    return _replace_all(
        _template_text(), "__GOVERNANCE_REPO_ROOT__",
        "__Governance_Repo_Root__")


def _fixture_settings_race_probe():
    """FX-WITNESS-01 — the D-54 `settings.yaml` race, as a runnable oracle.

    The emitted artifact is a standard-library-only Python script that drives
    the *launcher's own* witness through the four judgments D-54 fixes, using a
    throwaway home directory it creates itself (never a real DSH home):

      * host rewrite of ``settings.yaml`` (size **and** mtime change) →
        **no failure** (the witness compares names only);
      * host-side file churn in an unrelated subtree → **no failure**;
      * a write into ``.agent-presets`` (the adapter's only write face) →
        **failure**, no resampling tolerance;
      * a new top-level entry → failure on the first sample, waived when the
        resample does not reproduce it.

    It prints a JSON report and exits non-zero unless every line holds, so the
    fixture is machine-checkable end to end rather than a description of a
    judgment (the "可机检" half of design §6.1 V5 acceptance ⑤).
    """
    return _WITNESS_PROBE_SOURCE


#: See :func:`_fixture_settings_race_probe`. Kept **ASCII-only** (asserted by
#: `test_witness_fixture_source_is_pure_ascii`) and standard-library-only, so the
#: emitted file runs unchanged on any host regardless of its source encoding
#: defaults — the earlier docstring claimed ASCII while carrying an em dash
#: (N-6a), which is exactly the comment-vs-fact drift this suite exists to catch.
_WITNESS_PROBE_SOURCE = '''\
"""FX-WITNESS-01 - D-54 witness-sampling oracle (self-contained).

Usage: python FX-WITNESS-01.py <path/to/adapters/dsh/launch.py>

Creates a throwaway home under the system temp directory, mutates it the way a
live host would, and asserts the four judgments design 3.3 (row 11) fixes.
Exits 0 only when all of them hold.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def load_launch(path):
    spec = importlib.util.spec_from_file_location("launch_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def fresh_home(root):
    home = root / ".dsh"
    preset = home / ".agent-presets" / "governance"
    preset.mkdir(parents=True, exist_ok=True)
    (preset / "agent.cordis.yml").write_text("- id: persona\\n", encoding="utf-8")
    (home / "settings.yaml").write_text("a: 1\\n", encoding="utf-8")
    (home / ".credentials.yaml").write_text("token: x\\n", encoding="utf-8")
    (home / "sessions").mkdir(exist_ok=True)
    return home


def verdict(launch, samples, resample=None):
    return launch.witness_verdict(samples, resample=resample)


def main():
    launch = load_launch(sys.argv[1])
    checks = []

    def record(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    with tempfile.TemporaryDirectory(prefix="fx-witness-01-") as td:
        root = Path(td)

        # 1. host rewrites settings.yaml: size AND mtime move, names do not.
        home = fresh_home(root / "c1")
        before = launch._real_home_witness(home)
        target = home / "settings.yaml"
        stamp = target.stat().st_mtime_ns
        target.write_text("a: 2222222\\n" + "x" * 4096 + "\\n", encoding="utf-8")
        os.utime(target, ns=(stamp + 10 ** 9, stamp + 10 ** 9))
        after = launch._real_home_witness(home)
        result = verdict(launch, (before, after))
        record("settings_yaml_race_is_not_a_failure",
               result["verdict"] == "PASS" and not result["failures"],
               json.dumps(result))
        record("witness_records_no_size_or_mtime",
               before["top_level"] == after["top_level"]
               and not any(":" + str(target.stat().st_size) in entry
                           for entry in after["top_level"]),
               json.dumps(after["top_level"]))

        # 2. host churn inside its own subtree.
        home = fresh_home(root / "c2")
        before = launch._real_home_witness(home)
        (home / "sessions" / "s1.jsonl").write_text("{}\\n", encoding="utf-8")
        after = launch._real_home_witness(home)
        result = verdict(launch, (before, after))
        record("host_subtree_churn_is_not_a_failure",
               result["verdict"] == "PASS", json.dumps(result))

        # 3. a write into the adapter write face: failure, no tolerance.
        home = fresh_home(root / "c3")
        before = launch._real_home_witness(home)
        (home / ".agent-presets" / "governance" / "agent.cordis.yml").write_text(
            "- id: persona\\n- id: tool-skill\\n", encoding="utf-8")
        after = launch._real_home_witness(home)
        result = verdict(launch, (before, after),
                         resample=lambda: launch._real_home_witness(home))
        record("write_surface_change_fails_without_resample",
               result["verdict"] == "FAIL"
               and any("write surface" in f for f in result["failures"]),
               json.dumps(result))

        # 4a. top-level entry appears and is GONE again by the resample:
        # a genuine host race, which must be advisory rather than a failure.
        home = fresh_home(root / "c4")
        before = launch._real_home_witness(home)
        transient = home / "transient.tmp"
        transient.write_text("x\\n", encoding="utf-8")
        after_first = launch._real_home_witness(home)

        def resample():
            transient.unlink()
            return launch._real_home_witness(home)

        result = verdict(launch, (before, after_first), resample=resample)
        record("unreproduced_top_level_change_is_advisory",
               result["verdict"] == "PASS" and bool(result["advisories"])
               and not result["failures"], json.dumps(result))

        # 4b. the same change DOES reproduce -> failure.
        home = fresh_home(root / "c5")
        before = launch._real_home_witness(home)
        (home / "settled.tmp").write_text("x\\n", encoding="utf-8")
        after_first = launch._real_home_witness(home)
        result = verdict(launch, (before, after_first),
                         resample=lambda: launch._real_home_witness(home))
        record("reproduced_top_level_change_fails",
               result["verdict"] == "FAIL"
               and any("top level" in f for f in result["failures"]),
               json.dumps(result))

    failed = [check for check in checks if not check["ok"]]
    print(json.dumps({"fixture": "FX-WITNESS-01", "checks": checks,
                      "verdict": "FAIL" if failed else "PASS"}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: FX-WITNESS-01.py <launch.py>", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main())
'''


def _fixture_patch_with_update_row():
    """FX-PATCH-01 — the patch layer with an `- id: <host row>` UPDATE row:
    violates DEC-187 I-1 and K-6, so the invariant check must FAIL."""
    return (_patch_text()
            + "\n# FX-PATCH-01: an id-targeted UPDATE row must be rejected.\n"
            + "- id: persona\n"
            + "  config:\n"
            + "    prefix: 'FX-PATCH-01 injected UPDATE row'\n")


# ── registries ──────────────────────────────────────────────────────────────

FIXTURES = {
    "FX-NO-SCHEMA-01": ("FX-NO-SCHEMA-01.cordis.yml", _fixture_no_schema_only),
    "FX-NO-SCHEMA-02": ("FX-NO-SCHEMA-02.cordis.yml", _fixture_no_schema_mixed),
    "FX-GROUP-01": ("FX-GROUP-01.cordis.yml", _fixture_group_name_unresolved),
    "FX-GROUP-02": ("FX-GROUP-02.cordis.yml",
                    _fixture_group_throwing_without_children),
    "FX-GROUP-03": ("FX-GROUP-03.cordis.yml",
                    _fixture_group_throwing_with_children),
    "FX-CSD-01": ("FX-CSD-01.cordis.yml",
                  _fixture_same_indent_custom_skill_dirs),
    "FX-CSD-02": ("FX-CSD-02.cordis.yml", _fixture_relative_skill_dir),
    "FX-UTF8-01": ("FX-UTF8-01.cordis.yml", _fixture_rotten_report_bytes),
    "FX-CR-01": ("FX-CR-01.cordis.yml.template", _fixture_isolated_cr),
    "FX-TOKEN-01": ("FX-TOKEN-01.cordis.yml.template",
                    _fixture_misspelt_all_caps_token),
    "FX-TOKEN-02": ("FX-TOKEN-02.cordis.yml.template",
                    _fixture_misspelt_mixed_case_token),
    "FX-PATCH-01": ("FX-PATCH-01.cordis.patch.yml", _fixture_patch_with_update_row),
    "FX-WITNESS-01": ("FX-WITNESS-01.py", _fixture_settings_race_probe),
}

#: Fixtures named by §5.6 whose content needs a slice that has not landed.
#: Emitting one reports the owning slice instead of inventing bytes; the entry
#: keeps `coverage.entries[].negative_fixtures` a closed vocabulary.
DEFERRED = {
    "FX-PKG-01": {"slice": "V8",
                  "reason": "needs the package-identity mutation harness of "
                            "Check 28w (K-2/K-10), design §4.2 cluster 1"},
    "FX-PKG-02": {"slice": "V8",
                  "reason": "needs the package-identity mutation harness of "
                            "Check 28w (K-2/K-10), design §4.2 cluster 1"},
    "FX-PATH-01": {"slice": "V8",
                   "reason": "needs the preset-path rename harness of Check 28w "
                             "(K-5), design §4.2 cluster 3"},
    "FX-ROW-KEY-01": {"slice": "V8",
                      "reason": "row config-key mutation is consumed by the V8 "
                                "boundary check; V1 emits compositions only"},
    "FX-API-01": {"slice": "V8",
                  "reason": "removing an oracle API symbol requires the "
                            "isolated plane of `dsh-doctor` S2/S3"},
    "FX-BASEURL-01": {"slice": "V2",
                      "reason": "`baseUrl` shape is asserted inside the guard's "
                                "probe context, not by a composition file "
                                "(design §2.4 R0 F-10)"},
    "FX-JS-01": {"slice": "V2",
                 "reason": "JS-side contract-missing mutation needs the V2 "
                           "`lib/index.js` read path"},
    "FX-JS-02": {"slice": "V2",
                 "reason": "JS-side malformed-contract mutation needs the V2 "
                           "`lib/index.js` read path"},
    "FX-JS-03": {"slice": "V2",
                 "reason": "direct `renderComposition` call with a missing "
                           "contract (R0 F-3), consumed by V2"},
    "FX-HOME-01": {"slice": "V6",
                   "reason": "DSH_HOME case table of the three-way differential "
                             "gate (G-06 / D-16 / D-47)"},
    "FX-HOME-02": {"slice": "V6",
                   "reason": "DSH_HOME case table of the three-way differential "
                             "gate (G-06 / D-16 / D-47)"},
    "FX-HOME-03": {"slice": "V6",
                   "reason": "DSH_HOME case table of the three-way differential "
                             "gate (G-06 / D-16 / D-47)"},
    "FX-RESIDUE-01": {"slice": "V8",
                      "reason": "pre-seeded `spg-dsh-compat-*` residue is read "
                                "by `dsh-doctor` S3 (D-79)"},
    "FX-VER-01": {"slice": "V7",
                  "reason": "persona version-string drift fixture (D-94) lands "
                            "with the V7 evidence slice"},
    "FX-WIRE-01": {"slice": "V8",
                   "reason": "a removed segment registration only exists once "
                             "Check 28w is wired"},
    "FX-ALLOW-01": {"slice": "V8",
                    "reason": "the allowlist budget/ratchet judgment is K-11, "
                              "landing with Check 28w"},
    "FX-VERDICT-01": {"slice": "V8",
                      "reason": "doctor ↔ boundary verdict disagreement is K-12, "
                                "landing with `dsh-doctor`"},
    "FX-BASE-01": {"slice": "V8",
                   "reason": "rehearsal-baseline time-order/TTL judgment is "
                             "K-13, landing with `dsh-doctor --rehearse`"},
    "FX-REHEARSE-01": {"slice": "V8",
                       "reason": "rehearsal mutation of a recorded "
                                 "`host-facts-<v>.json` (design §5.5 [C])"},
    "FX-REHEARSE-02": {"slice": "V8",
                       "reason": "rehearsal mutation of a recorded "
                                 "`host-facts-<v>.json` (design §5.5 [C])"},
    "FX-REHEARSE-03": {"slice": "V8",
                       "reason": "rehearsal mutation of a recorded "
                                 "`host-facts-<v>.json` (design §5.5 [C])"},
    "FX-REHEARSE-04": {"slice": "V8",
                       "reason": "rehearsal mutation of a recorded "
                                 "`host-facts-<v>.json` (design §5.5 [C])"},
    "FX-REHEARSE-05": {"slice": "V8",
                       "reason": "same-version no-op rehearsal must FAIL (K-13); "
                                 "it needs `dsh-doctor --rehearse`"},
}


def emitted_fixture_ids():
    """Ids whose bytes this slice can produce, sorted for stable output."""
    return sorted(FIXTURES)


def deferred_fixture_ids():
    return sorted(DEFERRED)


def known_fixture_ids():
    """The closed vocabulary the contract's `negative_fixtures` may name."""
    return sorted(set(FIXTURES) | set(DEFERRED))


def deferred_reason(fixture_id):
    entry = DEFERRED.get(fixture_id)
    if entry is None:
        raise KeyError(fixture_id)
    return f"{entry['slice']}: {entry['reason']}"


def fixture_bytes(fixture_id):
    """The fixture payload as bytes (deterministic for a given id)."""
    if fixture_id in FIXTURES:
        payload = FIXTURES[fixture_id][1]()
        return payload if isinstance(payload, bytes) else payload.encode("utf-8")
    if fixture_id in DEFERRED:
        raise ValueError(
            f"fixture {fixture_id} is not emittable in this slice — "
            f"{deferred_reason(fixture_id)}")
    raise ValueError(
        f"unknown fixture id {fixture_id!r}; known ids: "
        f"{', '.join(known_fixture_ids())}")


def emit_fixture(fixture_id, out_dir):
    """Write one fixture into ``out_dir`` and return the written path."""
    if fixture_id not in FIXTURES:
        fixture_bytes(fixture_id)  # raises, naming the owning slice / known ids
    filename = FIXTURES[fixture_id][0]
    destination = Path(out_dir)
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / filename
    target.write_bytes(fixture_bytes(fixture_id))
    return target


def _describe():
    lines = ["Emittable fixtures:"]
    for fixture_id in emitted_fixture_ids():
        lines.append(f"  {fixture_id} -> {FIXTURES[fixture_id][0]}")
    lines.append("Deferred fixtures (owning slice):")
    for fixture_id in deferred_fixture_ids():
        lines.append(f"  {fixture_id} -> {deferred_reason(fixture_id)}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Emit a deterministic dsh dependency-boundary fixture.")
    parser.add_argument("--emit-fixture", metavar="ID",
                        help="fixture id, e.g. FX-NO-SCHEMA-01")
    parser.add_argument("--out", metavar="DIR",
                        help="output directory (created when missing)")
    parser.add_argument("--list", action="store_true",
                        help="list emittable and deferred fixture ids")
    args = parser.parse_args(argv)

    if args.list:
        print(_describe())
        return 0
    if not args.emit_fixture or not args.out:
        parser.print_usage(sys.stderr)
        print("error: --emit-fixture <ID> --out <DIR> are both required",
              file=sys.stderr)
        return 2
    try:
        written = emit_fixture(args.emit_fixture, args.out)
    except (ValueError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(f"wrote {written}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
