"""FEAT-080 (f) / FEAT-078 R0 F-1: zero-drift — the LIVING ADR link.

The per-letter pinning of the injected clause texts lives in
``test_dsh_adapter.py`` (frozen-baseline vs shipped files); what ONLY this
suite provides is the third leg of the triangle: **ADR-021 itself vs the
shipped surfaces**, character-for-character, with the frozen texts
extracted from the ADR AT RUNTIME. ADR wording edits therefore redden this
suite immediately — the frozen baseline and the ADR can no longer drift
apart unnoticed (the gap FEAT-078 R0 F-1 diagnosed when the check existed
only as a .governance/tmp/ script).

Face-list adaptations the ADR itself sanctions (§2.1: 序数仅描述——the
persona bullet face drops the ``N. `` ordinal and the ``**`` bold wrapper)
are DERIVED from the ADR string programmatically, never hand-retyped, so
the check stays a true ADR diff.

Run:
    python -m unittest skills/software-project-governance/infra.tests.test_injection_zerodrift -v
"""

import re
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
_REPO_ROOT = _INFRA_DIR.parents[2]

ADR = _REPO_ROOT / "docs/architecture/ADR-021-meta-mechanisms.md"
FACES = {
    "behavior-protocol.md": _REPO_ROOT
    / "skills/software-project-governance/references/behavior-protocol.md",
    "SKILL.md": _REPO_ROOT
    / "skills/software-project-governance/SKILL.md",
    "persona-template": _REPO_ROOT
    / "agent-presets/governance/agent.cordis.yml.template",
    "governance-init.md": _REPO_ROOT / "commands/governance-init.md",
    "AGENTS.md.template": _REPO_ROOT / "adapters/dsh/AGENTS.md.template",
}


def _extract_adr_line(line_prefix):
    """The blockquote body under ``line_prefix`` — the frozen text itself."""
    for line in ADR.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith(line_prefix):
            return line.strip()[2:].strip()
    raise AssertionError(
        f"ADR frozen line not found: {line_prefix!r} — the ADR is the "
        f"authority this whole suite pins against; a missing frozen line "
        f"is a red ADR edit, never a test bug")


def _persona_body(compressed):
    """ADR-sanctioned bullet adaptation derived FROM the ADR string."""
    body = re.sub(r"^\d+\.\s*", "", compressed)
    body = body.replace("**", "", 1)
    return body.replace("**", "", 1)


class InjectionZeroDriftTests(unittest.TestCase):
    """17 faces, one authority: every designated surface carries the
    ADR-frozen clause texts character-for-character (M1 §2.1 + M2 §3.1)."""

    @classmethod
    def setUpClass(cls):
        cls.adr = ADR.read_text(encoding="utf-8")
        cls.m1_full = _extract_adr_line("> 5. **推荐必标需求源（DEC-286(7)/DEC-287(5)）**")
        cls.m1_comp = _extract_adr_line("> 5. **推荐必标需求源**：推荐与排序呈现逐项标注需求源")
        cls.m2_full = _extract_adr_line("> 6. **发现即闭环（DEC-286(1)(2)(6)）**")
        cls.m2_comp = _extract_adr_line("> 6. **发现即闭环**：问题在触发点当场闭环")
        cls.texts = {key: path.read_text(encoding="utf-8")
                     for key, path in FACES.items()}
        import sys
        if str(_INFRA_DIR) not in sys.path:
            sys.path.insert(0, str(_INFRA_DIR))
        from sync_entry_projection import extract_canonical_templates
        cls.templates = extract_canonical_templates(
            cls.texts["governance-init.md"])

    def test_face_behavior_protocol_carries_both_canonical_texts(self):
        text = self.texts["behavior-protocol.md"]
        self.assertIn(self.m1_full, text)
        self.assertIn(self.m2_full, text)

    def test_face_skill_carries_both_compressed_items(self):
        text = self.texts["SKILL.md"]
        self.assertIn(self.m1_comp, text)
        self.assertIn(self.m2_comp, text)

    def test_face_persona_carries_adapted_bodies_and_extra_anchor(self):
        text = self.texts["persona-template"]
        self.assertIn(_persona_body(self.m1_comp), text)
        self.assertIn(_persona_body(self.m2_comp), text)
        # persona-only extra anchor (ADR-021 §2.1 file table: persona 另加)
        self.assertIn("用户点名", text)

    def test_face_entry_templates_carry_compressed_all_profiles(self):
        for profile in ("lightweight", "standard", "strict"):
            self.assertIn(self.m1_comp, self.templates[profile],
                          f"{profile} M1 compressed")
            self.assertIn(self.m2_comp, self.templates[profile],
                          f"{profile} M2 compressed")

    def test_face_thin_and_agents_carry_keyword_pointers(self):
        for keyword in ("推荐必标需求源", "发现即闭环"):
            self.assertIn(keyword, self.templates["secondary-thin"],
                          f"secondary-thin pointer {keyword}")
            self.assertIn(keyword, self.texts["AGENTS.md.template"],
                          f"AGENTS.md.template pointer {keyword}")


if __name__ == "__main__":
    unittest.main()
