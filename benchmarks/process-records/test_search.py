"""Public fixture checks for the source-bound, read-only search experiment."""
from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

import search
from decision_repository import write_authority_transition


class SearchBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.work = Path(self.scratch.name).resolve()
        self.root = self.work / "host" / ".governance"
        self.db = self.work / "index.db"
        search.demo(self.root)

    def test_physical_occurrences_typed_edges_and_block_citation(self):
        search.build(self.root, self.db)
        con = search.connect(self.db)
        self.addCleanup(con.close)
        cases = json.loads((search.HERE / "search-cases.json").read_bytes())["demo"]
        gold = json.loads((search.HERE / "search-locators.json").read_bytes())["demo"]
        for case in cases + gold["challenges"]:
            actual = search.verified_query(self.root, con, case)
            expected = Counter() if case["name"].startswith("paraphrased") else search.expected_occurrences(case, gold["locators"])
            self.assertEqual(Counter(tuple(row.locator for row in group) for group in actual), expected)
        hit, = search.verified_query(self.root, con, {"op":"lookup", "q":"DEC-100"})[0]
        self.assertEqual((hit.start, hit.end), (1, 3))
        self.assertEqual(hit.digest, sha256((self.root/hit.path).read_bytes()).hexdigest())
        with self.assertRaises(ValueError):
            search.build(self.root, self.db)

    def test_same_size_source_edit_stales_index_even_when_mtime_restored(self):
        search.build(self.root, self.db)
        path = self.root / "decision-log.md"
        st = path.stat()
        path.write_bytes(path.read_bytes().replace(b"DEC-901", b"DEC-902"))
        os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns))
        con = search.connect(self.db)
        self.addCleanup(con.close)
        with self.assertRaisesRegex(ValueError, "stale index"):
            search.verified_query(self.root, con, {"op":"lookup", "q":"DEC-901"})

    def test_json_authority_never_serves_old_markdown(self):
        search.build(self.root, self.db)
        write_authority_transition(self.root, from_state="MD_ACTIVE", to_state="CUTOVER_FROZEN", expected_epoch=0)
        write_authority_transition(self.root, from_state="CUTOVER_FROZEN", to_state="JSON_ACTIVE", expected_epoch=1)
        con = search.connect(self.db)
        self.addCleanup(con.close)
        with self.assertRaisesRegex(ValueError, "requires MD_ACTIVE"):
            search.verified_query(self.root, con, {"op":"lookup", "q":"DEC-901"})
        with self.assertRaisesRegex(ValueError, "requires MD_ACTIVE"):
            search.build(self.root, self.work / "other.db")
        self.assertFalse((self.work / "other.db").exists())

    def test_lookup_rejects_cache_body_mismatching_original_bytes(self):
        search.build(self.root, self.db)
        changed = sqlite3.connect(self.db)
        try:
            changed.execute("UPDATE records SET body='changed in cache' WHERE entity='DEC-901'")
            changed.commit()
        finally:
            changed.close()
        con = search.connect(self.db)
        self.addCleanup(con.close)
        with self.assertRaisesRegex(ValueError, "original source span"):
            search.verified_query(self.root, con, {"op":"lookup", "q":"DEC-901"})


if __name__ == "__main__":
    unittest.main()
