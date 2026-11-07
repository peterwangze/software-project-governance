"""FEAT-113 S1 tests — the pure-stdlib asar reader (design §3.3).

Everything here runs on synthetic archives built from bytes inside the test
(§9.3): no dependency on the real ``D:\\app\\dsh`` installation, no unpacking,
no writes outside the test's own scratch directory.
"""

import json
import struct
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent

if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import dsh_asar  # noqa: E402
import dsh_contract  # noqa: E402


def _pad4(text_bytes):
    """The archive pads the header JSON so the content starts 4-aligned."""
    return b"\x00" * ((-len(text_bytes)) % 4)


def _build_archive(entries, *, links=None, trailing=b"", json_pad=None):
    """Serialize a tiny synthetic asar from ``{rel: bytes}`` (+ ``{rel: target}`` links).

    Layout mirrors the real container (verified read-only against
    ``D:\\app\\dsh\\resources\\app.asar``, FEAT-113 §1.3 F1):

    * ``[0:4]``  LE uint32 == 4 (the pickle size prefix)
    * ``[4:8]``  LE uint32 payload size (content base is ``8 + payload``)
    * ``[8:12]`` the payload-size duplicate (header pickle payload size)
    * ``[12:16]``LE uint32 JSON byte length
    * from byte 16 the header JSON, padded to 4-alignment, then file content.

    Returns ``(archive_bytes, {rel: offset_of_content})``.
    """
    links = links or {}
    index = {"files": {}}
    content = bytearray()
    offsets = {}
    for rel, blob in entries.items():
        node = index
        parts = rel.split("/")
        for part in parts[:-1]:
            node = node["files"].setdefault(part, {"files": {}})
        offsets[rel] = len(content)
        node["files"][parts[-1]] = {
            "size": len(blob),
            "offset": str(len(content)),
        }
        content.extend(blob)
    for rel, target in links.items():
        node = index
        parts = rel.split("/")
        for part in parts[:-1]:
            node = node["files"].setdefault(part, {"files": {}})
        node["files"][parts[-1]] = {"link": target}
    text = json.dumps(index).encode("utf-8")
    pad = _pad4(text) if json_pad is None else json_pad
    payload = 8 + len(text) + len(pad)
    header = struct.pack("<IIII", 4, payload, 4 + len(text) + len(pad),
                         len(text))
    blob = header + text + pad + bytes(content) + trailing
    base = 8 + payload
    return blob, {rel: base + off for rel, off in offsets.items()}


class _MemoryFs(dsh_asar.FsPort):
    """Dict-backed FsPort: bytes values are files, ``None`` values are dirs."""

    def __init__(self, files):
        self.files = dict(files)

    def _fetch(self, path):
        try:
            return self.files[str(path)]
        except KeyError:
            raise FileNotFoundError(str(path)) from None

    def exists(self, path):
        return str(path) in self.files

    def is_file(self, path):
        return str(path) in self.files and self.files[str(path)] is not None

    def is_dir(self, path):
        return str(path) in self.files and self.files[str(path)] is None

    def size(self, path):
        value = self._fetch(path)
        return len(value) if value is not None else 0

    def read_head(self, path, count):
        return self._fetch(path)[:count]

    def read_at(self, path, offset, count):
        return self._fetch(path)[offset:offset + count]

    def read_bytes(self, path):
        return self._fetch(path)

    def list_dir(self, path):
        prefix = str(path).rstrip("\\/") + "/"
        names = set()
        for candidate in self.files:
            if candidate.startswith(prefix) and len(candidate) > len(prefix):
                names.add(candidate[len(prefix):].split("/")[0])
        return sorted(names)

    def mtime(self, path):
        return 0.0


# ── pure header parsing (bytes in, values out) ──────────────────────────────
class HeaderParseTests(unittest.TestCase):

    def test_the_real_layout_parses_to_payload_json_size_and_content_base(self):
        blob, offsets = _build_archive({"a.txt": b"hello"})
        header = dsh_asar.parse_header(blob[:16])
        text_len = len(json.dumps({"files": {"a.txt": {
            "size": 5, "offset": "0"}}}).encode("utf-8"))
        self.assertEqual(header.payload_size, 8 + text_len)
        self.assertEqual(header.json_size, text_len)
        self.assertEqual(header.content_base, 8 + header.payload_size)
        # the content really starts at content_base
        self.assertEqual(blob[header.content_base:], b"hello")

    def test_a_short_header_is_rejected_as_truncated(self):
        with self.assertRaises(dsh_asar.AsarError) as caught:
            dsh_asar.parse_header(b"\x04\x00\x00")
        self.assertEqual(caught.exception.code, "ASAR_HEADER_TRUNCATED")

    def test_a_non_four_magic_is_rejected(self):
        head = struct.pack("<IIII", 3, 16, 12, 8)
        with self.assertRaises(dsh_asar.AsarError) as caught:
            dsh_asar.parse_header(head)
        self.assertEqual(caught.exception.code, "ASAR_MAGIC_INVALID")

    def test_the_header_size_prefix_must_be_little_endian_four(self):
        # Big-endian 4 must not be accepted by the little-endian reader.
        head = struct.pack(">IIII", 4, 16, 12, 8)
        with self.assertRaises(dsh_asar.AsarError) as caught:
            dsh_asar.parse_header(head)
        self.assertEqual(caught.exception.code, "ASAR_MAGIC_INVALID")


class IndexParseTests(unittest.TestCase):

    def test_trailing_alignment_padding_is_trimmed_to_the_last_brace(self):
        blob, _ = _build_archive({"a.txt": b"x"})
        header = dsh_asar.parse_header(blob[:16])
        raw = blob[16:16 + header.json_size] + b"  \x00\x00"
        index = dsh_asar.parse_index(raw)
        self.assertIn("a.txt", index["files"])

    def test_invalid_json_is_rejected_with_its_own_code(self):
        with self.assertRaises(dsh_asar.AsarError) as caught:
            dsh_asar.parse_index("{'files': not-json}".encode("utf-8"))
        self.assertEqual(caught.exception.code, "ASAR_JSON_INVALID")

    def test_undecodable_bytes_are_a_json_failure_not_a_traceback(self):
        with self.assertRaises(dsh_asar.AsarError) as caught:
            dsh_asar.parse_index(b"\xff\xfe\xfa")
        self.assertEqual(caught.exception.code, "ASAR_JSON_INVALID")


# ── entry index + links ─────────────────────────────────────────────────────
class EntryIndexTests(unittest.TestCase):

    def _index(self):
        blob, _ = _build_archive({
            "dsh/node_modules/@deepseek-ai/dsh/package.json":
                b'{"version": "0.2.2-rc.1"}',
        })
        header = dsh_asar.parse_header(blob[:16])
        return dsh_asar.parse_index(blob[16:16 + header.json_size])

    def test_nested_entries_resolve_with_string_offsets_as_ints(self):
        entry = dsh_asar.index_entry(self._index(),
                                     "dsh/node_modules/@deepseek-ai/dsh/package.json")
        self.assertIsInstance(entry.offset, int)
        self.assertEqual(entry.size, len(b'{"version": "0.2.2-rc.1"}'))
        self.assertFalse(entry.unpacked)
        self.assertIsNone(entry.link)

    def test_dot_segments_are_rejected(self):
        with self.assertRaises(dsh_asar.AsarError) as caught:
            dsh_asar.index_entry(self._index(), "dsh/./node_modules")
        self.assertEqual(caught.exception.code, "ASAR_ENTRY_MISSING")

    def test_dotdot_segments_are_rejected(self):
        with self.assertRaises(dsh_asar.AsarError) as caught:
            dsh_asar.index_entry(self._index(), "dsh/../outside")
        self.assertEqual(caught.exception.code, "ASAR_ENTRY_MISSING")

    def test_missing_entries_report_asar_entry_missing(self):
        with self.assertRaises(dsh_asar.AsarError) as caught:
            dsh_asar.index_entry(self._index(), "no/such/file.txt")
        self.assertEqual(caught.exception.code, "ASAR_ENTRY_MISSING")

    def test_links_resolve_to_their_target_and_record_the_chain(self):
        blob, _ = _build_archive(
            {"real.txt": b"payload"},
            links={"alias.txt": "real.txt"})
        header = dsh_asar.parse_header(blob[:16])
        index = dsh_asar.parse_index(blob[16:16 + header.json_size])
        resolved = dsh_asar.resolve_entry(index, "alias.txt")
        self.assertEqual(resolved.entry.size, len(b"payload"))
        self.assertEqual(resolved.link_chain, ("alias.txt", "real.txt"))

    def test_link_cycles_are_detected(self):
        blob, _ = _build_archive(
            {"real.txt": b"payload"},
            links={"a.txt": "b.txt", "b.txt": "a.txt"})
        header = dsh_asar.parse_header(blob[:16])
        index = dsh_asar.parse_index(blob[16:16 + header.json_size])
        with self.assertRaises(dsh_asar.AsarError) as caught:
            dsh_asar.resolve_entry(index, "a.txt")
        self.assertEqual(caught.exception.code, "ASAR_LINK_CYCLE")

    def test_a_five_hop_chain_resolves_inside_the_eight_hop_budget(self):
        # R1 (review finding 1): the budget counts hops, not chain entries —
        # a legal 5-hop chain must resolve (the pre-fix double-append cut it
        # at 4 with a wrong "more than 8" message).
        links = {**{f"l{i}.txt": f"l{i + 1}.txt" for i in range(1, 5)},
                 "l5.txt": "real.txt"}
        blob, _ = _build_archive({"real.txt": b"payload"}, links=links)
        header = dsh_asar.parse_header(blob[:16])
        index = dsh_asar.parse_index(blob[16:16 + header.json_size])
        resolved = dsh_asar.resolve_entry(index, "l1.txt")
        self.assertEqual(resolved.entry.size, len(b"payload"))
        self.assertEqual(resolved.link_chain,
                         ("l1.txt", "l2.txt", "l3.txt", "l4.txt", "l5.txt",
                          "real.txt"))

    def test_a_nine_hop_chain_is_refused_at_the_budget(self):
        links = {**{f"l{i}.txt": f"l{i + 1}.txt" for i in range(1, 9)},
                 "l9.txt": "real.txt"}
        blob, _ = _build_archive({"real.txt": b"payload"}, links=links)
        header = dsh_asar.parse_header(blob[:16])
        index = dsh_asar.parse_index(blob[16:16 + header.json_size])
        with self.assertRaises(dsh_asar.AsarError) as caught:
            dsh_asar.resolve_entry(index, "l1.txt")
        self.assertEqual(caught.exception.code, "ASAR_LINK_CYCLE")
        self.assertIn("more than 8 link hops", str(caught.exception))

    def test_entries_can_be_found_by_path_tail_for_plane_discovery(self):
        index = self._index()
        hits = dsh_asar.find_entry(index, ("@deepseek-ai", "dsh",
                                          "package.json"))
        self.assertEqual(hits, ["dsh/node_modules/@deepseek-ai/dsh/package.json"])


# ── bounded counting (entry_count_cap) ──────────────────────────────────────
class EntryCountTests(unittest.TestCase):

    def test_counting_is_bounded_by_the_cap_from_the_contract(self):
        entries = {f"f{i}.txt": b"x" for i in range(7)}
        blob, _ = _build_archive(entries)
        header = dsh_asar.parse_header(blob[:16])
        index = dsh_asar.parse_index(blob[16:16 + header.json_size])
        self.assertEqual(dsh_asar.count_entries(index, cap=5), 5)
        self.assertEqual(dsh_asar.count_entries(index, cap=100), 7)

    def test_the_default_cap_is_the_contract_fact(self):
        self.assertEqual(
            dsh_contract.get("host.planes.asar.entry_count_cap"), 200000)


# ── the reader (FsPort-injectable; default reads real files) ────────────────
class ReaderTests(unittest.TestCase):

    def test_read_bytes_returns_entry_content_by_offset_and_size(self):
        blob, _ = _build_archive({
            "a.txt": b"alpha",
            "nested/b.txt": b"beta-gamma",
        })
        reader = dsh_asar.AsarReader("mem://x.asar", fs=_MemoryFs(
            {"mem://x.asar": blob}))
        self.assertEqual(reader.read_bytes("a.txt"), b"alpha")
        self.assertEqual(reader.read_bytes("nested/b.txt"), b"beta-gamma")

    def test_read_json_decodes_entry_content(self):
        blob, _ = _build_archive({
            "pkg/package.json": b'{"version": "9.9.9"}'})
        reader = dsh_asar.AsarReader("mem://x.asar", fs=_MemoryFs(
            {"mem://x.asar": blob}))
        self.assertEqual(reader.read_json("pkg/package.json")["version"],
                         "9.9.9")

    def test_out_of_range_entries_are_refused(self):
        blob, _ = _build_archive({"a.txt": b"alpha"})
        # a lying index: offset/size beyond the file end
        lying = {"files": {"a.txt": {"size": 10_000, "offset": "99"}}}
        text = json.dumps(lying).encode("utf-8")
        payload = 8 + len(text) + len(_pad4(text))
        archive = (struct.pack("<IIII", 4, payload,
                               4 + len(text) + len(_pad4(text)), len(text))
                   + text + _pad4(text) + b"alpha")
        reader = dsh_asar.AsarReader("mem://x.asar", fs=_MemoryFs(
            {"mem://x.asar": archive}))
        with self.assertRaises(dsh_asar.AsarError) as caught:
            reader.read_bytes("a.txt")
        self.assertEqual(caught.exception.code, "ASAR_ENTRY_OUT_OF_RANGE")

    def test_entries_before_the_content_base_are_refused(self):
        # a lying payload size pushes the content base beyond EOF: every
        # content offset then falls outside [content_base, file_size]
        lying = {"files": {"a.txt": {"size": 4, "offset": "0"}}}
        text = json.dumps(lying).encode("utf-8")
        pad = len(_pad4(text))
        payload = 8 + len(text) + pad + 4_096
        archive = (struct.pack("<IIII", 4, payload,
                               4 + len(text) + pad, len(text))
                   + text + _pad4(text) + b"alpha")
        reader = dsh_asar.AsarReader("mem://x.asar", fs=_MemoryFs(
            {"mem://x.asar": archive}))
        with self.assertRaises(dsh_asar.AsarError) as caught:
            reader.read_bytes("a.txt")
        self.assertEqual(caught.exception.code, "ASAR_ENTRY_OUT_OF_RANGE")

    def test_unpacked_entries_read_from_the_unpacked_sibling(self):
        blob, _ = _build_archive({"a.txt": b""})
        # mark the one entry unpacked by hand
        index = {"files": {"a.txt": {"size": 3, "offset": "0",
                                     "unpacked": True}}}
        text = json.dumps(index).encode("utf-8")
        payload = 8 + len(text) + len(_pad4(text))
        archive = struct.pack("<IIII", 4, payload, 4 + len(text) + len(_pad4(text)),
                              len(text)) + text + _pad4(text)
        fs = _MemoryFs({"mem://x.asar": archive,
                        "mem://x.asar.unpacked/a.txt": b"outside"})
        reader = dsh_asar.AsarReader("mem://x.asar", fs=fs)
        self.assertEqual(reader.read_bytes("a.txt"), b"outside")

    def test_a_truncated_file_is_reported_as_header_truncated(self):
        fs = _MemoryFs({"mem://x.asar": b"\x04\x00"})
        with self.assertRaises(dsh_asar.AsarError) as caught:
            dsh_asar.AsarReader("mem://x.asar", fs=fs)
        self.assertEqual(caught.exception.code, "ASAR_HEADER_TRUNCATED")

    def test_a_missing_file_is_reported_not_raised_as_oserror(self):
        fs = _MemoryFs({})
        with self.assertRaises(dsh_asar.AsarError) as caught:
            dsh_asar.AsarReader("mem://absent.asar", fs=fs)
        self.assertIn(caught.exception.code,
                      ("ASAR_HEADER_TRUNCATED", "ASAR_ENTRY_MISSING"))

    def test_a_file_node_with_size_but_no_offset_is_corrupt(self):
        # R1 (review finding 4): a malformed file node (size>0, no offset,
        # no link, not unpacked) must be refused with a coded error — it used
        # to reach the bounds math as ``content_base + None`` (TypeError).
        lying = {"files": {"a.txt": {"size": 3}}}
        text = json.dumps(lying).encode("utf-8")
        pad = len(_pad4(text))
        payload = 8 + len(text) + pad
        archive = (struct.pack("<IIII", 4, payload, 4 + len(text) + pad,
                               len(text)) + text + _pad4(text) + b"abc")
        reader = dsh_asar.AsarReader("mem://x.asar", fs=_MemoryFs(
            {"mem://x.asar": archive}))
        with self.assertRaises(dsh_asar.AsarError) as caught:
            reader.read_bytes("a.txt")
        self.assertEqual(caught.exception.code, "ASAR_ENTRY_CORRUPT")

    def test_a_zero_size_file_node_without_an_offset_reads_empty(self):
        index = {"files": {"empty.txt": {"size": 0}}}
        text = json.dumps(index).encode("utf-8")
        pad = len(_pad4(text))
        payload = 8 + len(text) + pad
        archive = struct.pack("<IIII", 4, payload, 4 + len(text) + pad,
                              len(text)) + text + _pad4(text)
        reader = dsh_asar.AsarReader("mem://x.asar", fs=_MemoryFs(
            {"mem://x.asar": archive}))
        self.assertEqual(reader.read_bytes("empty.txt"), b"")

    def test_identity_carries_sha_entry_count_and_no_mtime(self):
        blob, _ = _build_archive({
            "a.txt": b"alpha",
            "d/node_modules/@deepseek-ai/dsh/package.json": b"{}",
        })
        fs = _MemoryFs({"mem://x.asar": blob})
        reader = dsh_asar.AsarReader("mem://x.asar", fs=fs)
        identity = reader.identity()
        self.assertEqual(identity["path"], "mem://x.asar")
        self.assertEqual(identity["size"], len(blob))
        # every index node counts (files AND directory nodes), the same
        # bounded walk the real archive's 25418-entry count uses
        self.assertEqual(identity["entry_count"], 6)
        self.assertEqual(identity["content_base"], reader.content_base)
        self.assertTrue(identity["unpacked_present"] is False)
        self.assertNotIn("mtime", identity)
        # header_sha256 is over the trimmed JSON bytes and is stable
        again = dsh_asar.AsarReader("mem://x.asar", fs=fs).identity()
        self.assertEqual(identity["header_sha256"], again["header_sha256"])
        self.assertEqual(len(identity["header_sha256"]), 64)

    def test_identity_honours_an_injected_cap(self):
        entries = {f"f{i}.txt": b"x" for i in range(6)}
        blob, _ = _build_archive(entries)
        reader = dsh_asar.AsarReader("mem://x.asar", fs=_MemoryFs(
            {"mem://x.asar": blob}))
        self.assertEqual(reader.identity(entry_count_cap=4)["entry_count"], 4)

    def test_default_fs_reads_real_files(self):
        import tempfile
        with tempfile.TemporaryDirectory(prefix="spg-asar-") as td:
            path = Path(td) / "real.asar"
            blob, _ = _build_archive({"a.txt": b"from-disk"})
            path.write_bytes(blob)
            reader = dsh_asar.AsarReader(str(path))
            self.assertEqual(reader.read_bytes("a.txt"), b"from-disk")
            self.assertEqual(reader.identity()["entry_count"], 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
