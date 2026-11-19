"""Local retrieval experiment. The source is a governance directory, the DB is disposable.

    python search.py bench                         # published synthetic examples
    python search.py --source <frozen-governance> bench --cases project
    python search.py --source <governance> build --db <new-scratch-file>
    python search.py --source <governance> lookup FIX-504 --db <scratch-file>
    python search.py --source <governance> search 字形 --kind evidence --db <scratch-file>
    python search.py --source <governance> trace FEAT-121 --db <scratch-file>

Search is a case-sensitive literal phrase. A trace follows the EVD owner cell and
a typed governance_id link to the original decision identifier in its artifact cell.
Lookup includes qualified source labels and unresolved suffixes as candidates.
All occurrences are returned without selecting an approved or currently effective row.
Interactive results are content-checked against the source. Store the DB privately.
"""

import argparse
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "skills/software-project-governance/infra"))
from archive_parsing import _is_task_family_id, _split_table_row_escaped_aware
from decision_repository import load_authority, STATE_MD_ACTIVE
from governance_store import StoreError

FAMILIES = {"task": ("plan-tracker.md", "tasks"), "evidence": ("evidence-log.md", "evidence"),
            "risk": ("risk-log.md", "risks"), "decision": ("decision-log.md", "decisions")}
ENTITY = re.compile(r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+")
DEC_HEADER = re.compile(r"^##\s+(DEC-\d+)\s*[:：]")
DEC_SUFFIX = re.compile(r"^(DEC-[0-9]+)([^0-9].*)$")
KNOWN_NOTE = re.compile(r"^(?:[①-⑳]\s*)?[（(]?\s*(?:勘误|补记)(?=$|[，,。)）\s])")
DEC_LINK = re.compile(r"refs\[governance_id:(DEC-\d+)=[^\]]+\]")


def sources(root):
    """The explicit allowlist excludes generated pointer indexes and private receipts."""
    if load_authority(root)["state"] != STATE_MD_ACTIVE:
        raise ValueError("This experiment requires MD_ACTIVE; use decision_repository for this authority.")
    paths = {}
    for kind, (hot, folder) in FAMILIES.items():
        for path in [root / hot, *sorted((root / "archive" / folder).glob("*.md"))]:
            if not path.resolve(strict=True).is_relative_to(root):
                raise ValueError(f"source outside supplied root: {path.name}")
            paths[path.relative_to(root).as_posix()] = kind
    return paths


def snapshot(root):
    files = sources(root)
    digests = [(name, sha256((root / name).read_bytes()).hexdigest()) for name in sorted(files)]
    return sha256(json.dumps(digests, ensure_ascii=False).encode()).hexdigest()


@dataclass(frozen=True)
class Record:
    kind: str
    entity: str
    path: str
    start: int
    end: int
    digest: str
    body: str
    source_id: str = ""
    id_role: str = "untyped"
    owners: tuple = ()
    decisions: tuple = ()

    @property
    def locator(self):
        return (self.path, self.start, self.end, self.digest, self.id_role, self.source_id)


def read_records(root, files):
    for path, kind in files.items():
        lines = (root / path).read_bytes().splitlines(keepends=True)
        texts = [line.decode("utf-8").rstrip("\r\n") for line in lines]
        i = 0
        while i < len(lines):
            start = i
            line = texts[i]
            i += 1
            if not line.strip():
                continue
            entity, source_id, role = "", "", "untyped"
            owners, decisions = (), ()
            heading = DEC_HEADER.match(line) if kind == "decision" else None
            if heading:
                entity = heading[1]
                while i < len(lines) and not texts[i].startswith(("## ", "# ")):
                    i += 1
            elif line.lstrip().startswith("|"):
                cells = _split_table_row_escaped_aware(line.strip())[1:]
                if cells:
                    first = cells[0].strip().strip("*")
                    if kind == "task" and re.fullmatch(r"[Pp]\d+", first) and len(cells) > 1:
                        first = cells[1].strip().strip("*")
                    suffix = DEC_SUFFIX.fullmatch(first) if kind == "decision" else None
                    if suffix:
                        entity, source_id = suffix[1], first
                        role = "related_candidate" if KNOWN_NOTE.match(suffix[2].strip()) else "unresolved_suffix"
                    elif ENTITY.fullmatch(first):
                        if kind == "task" and _is_task_family_id(first):
                            entity = first
                        elif kind == "decision" and re.fullmatch(r"DEC-\d+", first):
                            entity = first
                        elif kind == "risk" and re.fullmatch(r"RISK-\d+", first):
                            entity = first
                        elif kind == "evidence":
                            entity = first
                            if first.startswith("EVD-") and len(cells) > 5:
                                owners = tuple(sorted(set(ENTITY.findall(cells[1]))))
                                decisions = tuple(sorted(set(DEC_LINK.findall(cells[5]))))
            raw = b"".join(lines[start:i])
            yield Record(kind, entity, path, start+1, i, sha256(raw).hexdigest(),
                         raw.decode("utf-8"), source_id or entity,
                         "identifier" if entity and not source_id else role, owners, decisions)


def select_records(records, op, q, kind=None):
    if op == "trace":
        decisions = {}
        for row in records:
            if row.kind == "decision" and row.id_role == "identifier":
                decisions.setdefault(row.entity, []).append(row)
        return [(r, d) for r in records if q in r.owners for key in r.decisions
                for d in decisions.get(key, ())]
    if op == "lookup":
        return [(r,) for r in records if r.entity == q]
    return [(r,) for r in records if (not kind or r.kind == kind) and q in r.body]


def raw_rg(root, files, q):
    run = subprocess.run(["rg", "--no-config", "--files-with-matches", "--null",
                          "--fixed-strings", "--", q, *files], cwd=root, capture_output=True)
    if run.returncode not in (0, 1):
        raise RuntimeError(run.stderr.decode(errors="replace"))
    return {Path(os.fsdecode(p)).as_posix() for p in run.stdout.split(b"\0") if p}


def rg_query(root, files, case):
    op, q, kind = case["op"], case["q"], case.get("kind")
    filtered = {p: k for p, k in files.items() if kind is None or kind == k}
    matched = raw_rg(root, filtered, q)
    records = list(read_records(root, {p: files[p] for p in matched}))
    if op == "trace":
        keys = {d for row in records if q in row.owners for d in row.decisions}
        paths = {p: k for p, k in files.items() if k == "decision"}
        for key in keys:
            matched.update(raw_rg(root, paths, key))
        records = list(read_records(root, {p: files[p] for p in matched}))
    return select_records(records, op, q, kind)


def archive_pointer_query(root, files, key):
    """The project's generated archive/index.md narrows an ID to candidate files."""
    candidates = {p: k for p, k in files.items() if "/" not in p}
    for line in (root / "archive/index.md").read_text(encoding="utf-8").splitlines():
        if line.startswith(f"| {key} |"):
            path = line.rstrip().rstrip("|").rsplit("|", 1)[-1].strip()
            if path in files:
                candidates[path] = files[path]
    return select_records(list(read_records(root, candidates)), "lookup", key)


def build(root, target):
    if target.resolve().is_relative_to(root) or target.exists():
        raise ValueError("choose a new private database path outside the source")
    started = time.perf_counter()
    signature = snapshot(root)
    counts = Counter()
    with tempfile.TemporaryDirectory(dir=target.parent) as temp:
        staging = Path(temp) / "search.db"
        con = sqlite3.connect(staging)
        try:
            con.executescript("""
                CREATE TABLE manifest(signature TEXT NOT NULL);
                CREATE TABLE records(seq INTEGER PRIMARY KEY, kind TEXT, entity TEXT, path TEXT,
                    start INT, end INT, digest TEXT, body TEXT, source_id TEXT, id_role TEXT);
                CREATE TABLE ownership(task TEXT, seq INT, PRIMARY KEY(task,seq));
                CREATE TABLE citations(seq INT, decision TEXT, PRIMARY KEY(seq,decision));
                CREATE INDEX by_entity ON records(entity);
            """)
            con.execute("INSERT INTO manifest VALUES (?)", (signature,))
            for seq, row in enumerate(read_records(root, sources(root)), 1):
                counts[row.kind if row.entity else "untyped_spans"] += 1
                con.execute("INSERT INTO records VALUES(?,?,?,?,?,?,?,?,?,?)", (seq, row.kind, row.entity,
                            row.path, row.start, row.end, row.digest, row.body, row.source_id, row.id_role))
                con.executemany("INSERT INTO ownership VALUES(?,?)", [(o,seq) for o in row.owners])
                con.executemany("INSERT INTO citations VALUES(?,?)", [(seq,d) for d in row.decisions])
            sizes = {}
            for name in ["unicode61", "trigram"]:
                before = con.execute("PRAGMA page_count").fetchone()[0]
                con.execute(f"CREATE VIRTUAL TABLE {name} USING fts5(body, content='records', "
                            f"content_rowid='seq', tokenize='{name}')")
                con.execute(f"INSERT INTO {name}({name}) VALUES('rebuild')")
                con.commit()
                pages = con.execute("PRAGMA page_count").fetchone()[0] - before
                sizes[name] = pages * con.execute("PRAGMA page_size").fetchone()[0]
        finally:
            con.close()
        if snapshot(root) != signature:
            raise ValueError("source changed during build; take a fresh snapshot")
        os.link(staging, target)  # publish only the completed db; never overwrite a caller's file
    return {"source_sha256": signature, "counts": dict(counts), "database_bytes": target.stat().st_size,
            "extra_bytes_by_fts_table": sizes, "build_ms": round((time.perf_counter()-started)*1000,2)}


def connect(db):
    return sqlite3.connect(db.resolve(strict=True).as_uri()+"?mode=ro", uri=True)


def sqlite_query(con, case, engine="hybrid"):
    op, q, kind = case["op"], case["q"], case.get("kind")
    fields = "kind,entity,path,start,end,digest,body,source_id,id_role"
    if op == "trace":
        cols = ",".join(f"{alias}.{col}" for alias in ["e","d"] for col in fields.split(","))
        rows = con.execute(f"SELECT {cols} FROM ownership o JOIN records e ON e.seq=o.seq "
                           "JOIN citations c ON c.seq=e.seq JOIN records d ON d.entity=c.decision "
                           "AND d.kind='decision' AND d.id_role='identifier' WHERE o.task=?", (q,))
        return [(Record(*r[:9]), Record(*r[9:])) for r in rows]
    params = []
    if op == "lookup":
        sql = f"SELECT {fields} FROM records WHERE entity=?"
        params = [q]
    else:
        sql = f"SELECT {fields} FROM records WHERE instr(body,?)>0"
        params = [q]
        if engine != "hybrid" or len(q) >= 3:
            table = "trigram" if engine == "hybrid" else engine
            if table not in ("unicode61", "trigram"):
                raise ValueError("unknown tokenizer")
            sql += f" AND seq IN (SELECT rowid FROM {table} WHERE {table} MATCH ?)"
            params.append('"' + q.replace('"','""') + '"')
        if kind:
            sql += " AND kind=?"
            params.append(kind)
    return [(Record(*r),) for r in con.execute(sql, params)]


def verified_query(root, con, case):
    if con.execute("SELECT signature FROM manifest").fetchone()[0] != snapshot(root):
        raise ValueError("stale index: source names/bytes changed; build a new index")
    hits = sqlite_query(con, case)
    lines = {}
    for group in hits:
        for row in group:
            if row.path not in lines:
                path = (root / row.path).resolve(strict=True)
                if not path.is_relative_to(root):
                    raise ValueError("indexed hit outside the source")
                lines[row.path] = path.read_bytes().splitlines(keepends=True)
            original = b"".join(lines[row.path][row.start-1:row.end])
            if sha256(original).hexdigest() != row.digest or original != row.body.encode("utf-8"):
                raise ValueError("indexed result does not match the original source span")
    return hits


def timed(call, repeats):
    samples = []
    for _ in range(repeats):
        start = time.perf_counter_ns()
        value = call()
        samples.append((time.perf_counter_ns()-start)/1e6)
    return value, round(statistics.median(samples),3)


def expected_occurrences(case, locators):
    return Counter(tuple(tuple(locators[key]) for key in label.split(" > ")) for label in case["expected"])


def benchmark(root, cases, gold, db, repeats):
    files = sources(root)
    report = build(root, db)
    report.update(source_files=len(files), source_bytes=sum((root/p).stat().st_size for p in files),
                  python=sys.version.split()[0], sqlite=sqlite3.sqlite_version, repeats=repeats)
    con = connect(db)
    timings = {"original":{}, "challenge":{}}
    hits_per_case = {"original":[], "challenge":[]}
    try:
        all_cases = [("original", case) for case in cases] + [("challenge", case) for case in gold["challenges"]]
        for group, case in all_cases:
            def scan():
                return select_records(list(read_records(root, files)), case["op"], case["q"], case.get("kind"))
            def reopened():
                fresh = connect(db)
                try:
                    return verified_query(root, fresh, case)
                finally:
                    fresh.close()
            methods = {"text_scan": scan, "sqlite_verified_reopen": reopened,
                       "sqlite_serving": lambda: sqlite_query(con, case)}
            if case["op"] == "lookup" and (root / "archive/index.md").is_file():
                methods["existing_archive_pointers_plus_hot"] = lambda: archive_pointer_query(root, files, case["q"])
            if case["op"] == "search":
                methods["unicode61_only"] = lambda: sqlite_query(con, case, "unicode61")
                methods["trigram_only"] = lambda: sqlite_query(con, case, "trigram")
            if shutil.which("rg"):
                methods["rg_prefilter_then_parse"] = lambda: rg_query(root, files, case)
            observed = {}
            for name, fn in methods.items():
                result, ms = timed(fn, repeats)
                expected = expected_occurrences(case, gold["locators"])
                found = Counter(tuple(row.locator for row in chain) for chain in result)
                common = sum((expected & found).values())
                metric = {"expected": sum(expected.values()), "found": sum(found.values()),
                          "correct": common, "exact": expected == found, "median_ms": ms}
                timings[group].setdefault(name, []).append(metric)
                observed[name] = metric
            hits_per_case[group].append({"name":case["name"], "op":case["op"], "methods":observed})
        for group, engines in timings.items():
            summary = {}
            for name, scores in engines.items():
                right = sum(s["correct"] for s in scores)
                exp, found = (sum(s[k] for s in scores) for k in ("expected","found"))
                summary[name] = {"exact_cases": sum(s["exact"] for s in scores), "cases":len(scores),
                    "expected":exp, "found":found, "correct":right,
                    "recall":round(right/exp,3) if exp else None, "precision":round(right/found,3) if found else None,
                    "median_of_case_medians_ms": round(statistics.median(s["median_ms"] for s in scores),3)}
            if group == "original":
                report.update(summary=summary, cases=hits_per_case[group])
            else:
                report["challenge"] = {"summary":summary, "cases":hits_per_case[group]}
        report["id_collisions"] = dict(con.execute("SELECT 'nonunique_ids',count(*) FROM "
            "(SELECT entity FROM records WHERE entity<>'' GROUP BY entity HAVING count(*)>1)"))
        report["fingerprint_verified_after_run"] = snapshot(root) == report["source_sha256"]
        if not report["fingerprint_verified_after_run"]:
            raise ValueError("source changed during benchmark")
        return report
    finally:
        con.close()


def demo(root):
    inputs = {"plan-tracker.md":"| **P1** | FIX-901 | 复核工单 |\n",
              "decision-log.md":"| DEC-901 | 首条切片的取锁由协调者执行 |\n"
                                "| DEC-902 | 首次登记 |\n| DEC-902 | 同号的另一行 |\n"
                                "| DEC-902①（勘误） | 文字更正 |\n| DEC-902 后续待定 | 待判别 |\n",
              "evidence-log.md":"| EVD-901 | FIX-901 | QA | 复核字形对照 | 原文里的 DEC-100 只是提及 | refs[governance_id:DEC-901=resolvable] |\n",
              "risk-log.md":"| RISK-900 | 同号新记录 |\n",
              "archive/risks/earlier.md":"| RISK-900 | 同号旧记录 |\n",
              "archive/decisions/earlier.md":"## DEC-100: 已归档\n\n> | DEC-100 | 样例的早期决定 |\n",
              "archive/index.md":"| DEC-100 | 已归档 | archive/decisions/earlier.md |\n"
                                 "| RISK-900 | 示例 | archive/risks/earlier.md |\n"}
    for path, body in inputs.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body.encode("utf-8"))


def main():
    cli = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    cli.add_argument("--source", type=Path, help="frozen governance directory (bench defaults to synthetic sample)")
    actions = cli.add_subparsers(dest="action", required=True)
    bench = actions.add_parser("bench")
    bench.add_argument("--cases", choices=["project","demo"], default="demo")
    bench.add_argument("--repeats", type=int, default=3)
    for name in ["build","lookup","search","trace"]:
        cmd = actions.add_parser(name)
        cmd.add_argument("--db", required=True, type=Path)
        if name != "build":
            cmd.add_argument("q")
        if name == "search":
            cmd.add_argument("--kind", choices=FAMILIES)
    args = cli.parse_args()
    with tempfile.TemporaryDirectory() as workspace:
        scratch = Path(workspace)
        if args.source:
            root = args.source.resolve(strict=True)
        elif args.action == "bench" and args.cases == "demo":
            root = scratch / "sample"
            demo(root)
        else:
            cli.error("supply --source for this action or case set")
        if args.action == "bench":
            if args.repeats < 1:
                cli.error("--repeats must be positive")
            cases = json.loads((HERE/"search-cases.json").read_bytes())[args.cases]
            gold = json.loads((HERE/"search-locators.json").read_bytes())[args.cases]
            output = benchmark(root, cases, gold, scratch/"bench.db", args.repeats)
        elif args.action == "build":
            output = build(root, args.db)
        else:
            if not args.q.strip():
                cli.error("query must not be empty")
            con = connect(args.db)
            try:
                hits = verified_query(root, con, {"op":args.action, "q":args.q, "kind":getattr(args,"kind",None)})
            finally:
                con.close()
            output = [[{"kind":r.kind, "id":r.entity, "source_id":r.source_id, "id_role":r.id_role,
                        "path":r.path, "start":r.start, "end":r.end,
                        "sha256":r.digest, "text":r.body.strip()} for r in group] for group in hits]
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, sqlite3.Error, ValueError, StoreError, RuntimeError) as error:
        sys.exit(str(error))
