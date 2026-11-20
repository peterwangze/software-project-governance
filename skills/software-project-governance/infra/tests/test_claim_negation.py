"""Capability and lifecycle declarations share one scoped-negation rule."""

import sys
import unittest
from pathlib import Path


INFRA = Path(__file__).resolve().parents[1]
if str(INFRA) not in sys.path:
    sys.path.insert(0, str(INFRA))

import archguard_ratchet
import verify_workflow
from checks import capability_registry


class ClaimNegationTests(unittest.TestCase):
    def test_callers_preserve_negation_scope_and_their_own_vocabulary(self):
        phrase = "risk-036 closed"
        cases = [
            ("no supporting evidence", False),
            (phrase, False),
            (f"NOT {phrase.upper()}", True),
            (f"nobody reported {phrase}", False),
            (f"不声明{phrase}", True),
            (f"{phrase}仍不可发布", True),
            (f"not verified；{phrase}", False),
            (f"no {phrase}; {phrase}", False),
            (f"no {phrase}; not {phrase}", True),
            (f"no official approval, external first-session pilot success, and {phrase}", True),
            (f"no risk-037 closed, planning and confirming {phrase}", True),
        ]
        for text, general in cases:
            with self.subTest(text=text):
                self.assertEqual(verify_workflow._line_has_scoped_claim_negation(text, phrase), general)
                self.assertEqual(capability_registry._line_has_scoped_claim_negation(text, phrase), general)

    def test_layer_matrix_allows_capability_registry_to_import_shared_matcher(self):
        matcher = "infra/claim_negation.py"
        modules = {
            matcher: archguard_ratchet.DEFAULT_MANAGED_MODULES[matcher],
            "infra/checks/capability_registry.py": {"layer": "L3"},
        }
        violations, report = archguard_ratchet.check_r3(modules, INFRA)
        self.assertEqual(violations, [])
        self.assertEqual(report["managed_edges"], 1)

if __name__ == "__main__":
    unittest.main()
