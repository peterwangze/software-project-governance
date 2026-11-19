"""Measure a disposable analytical export of the same spans as search.py.

Run with a local Python containing duckdb, passing --source <governance-dir>.
Omit --source to use search.py's public demo. No extension download is needed.
"""

import argparse
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory
from time import perf_counter

import duckdb

import search


def measure(source, scratch):
    text_file = scratch / "records.jsonl"
    column_file = scratch / "records.parquet"
    expected = Counter()
    signature = search.snapshot(source)
    started = perf_counter()
    with text_file.open("w", encoding="utf-8", newline="\n") as out:
        for row in search.read_records(source, search.sources(source)):
            record = {k: getattr(row, k) for k in ("kind", "entity", "path", "start", "end", "digest", "body")}
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            if row.entity:
                expected[row.kind, row.entity] += 1
    if search.snapshot(source) != signature:
        raise ValueError("source changed during the export")
    text_ms = (perf_counter() - started) * 1000
    timings = {}
    with closing(duckdb.connect()) as db:
        # Explicit VARCHARs keep dates and identifiers stable across datasets.
        reader = "read_json(?, columns={kind:'VARCHAR', entity:'VARCHAR', path:'VARCHAR', " \
                 "start:'BIGINT', 'end':'BIGINT', digest:'VARCHAR', body:'VARCHAR'}, format='newline_delimited')"
        started = perf_counter()
        db.from_query(f"SELECT * FROM {reader}", params=[str(text_file)]).write_parquet(
            str(column_file), compression="zstd"
        )
        convert_ms = (perf_counter() - started) * 1000
        for label, table, path in (("jsonl", reader, text_file), ("parquet", "read_parquet(?)", column_file)):
            invalid, spans = db.execute(
                f"SELECT count(*) FILTER (WHERE sha256(body) != digest), count(*) FROM {table}",
                [str(path)]).fetchone()
            if invalid:
                raise ValueError(f"{label} lost original span bytes")
            runs = []
            for _ in range(7):
                started = perf_counter()
                groups = db.execute(f"SELECT kind, entity, count(*) FROM {table} "
                                    "WHERE entity <> '' GROUP BY kind, entity", [str(path)]).fetchall()
                runs.append((perf_counter() - started) * 1000)
                if {(kind, key): count for kind, key, count in groups} != expected:
                    raise ValueError(f"{label} changed the grouped results")
            timings[label] = {"bytes": path.stat().st_size, "spans_verified": spans,
                              "median_scan_ms": round(median(runs), 2)}
    return {"duckdb": duckdb.__version__, "source_sha256": signature, "distinct_kind_id": len(expected),
            "jsonl_export_ms": round(text_ms, 2), "parquet_conversion_ms": round(convert_ms, 2), **timings}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="frozen .governance directory (default: public demo)")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="process-records-reporting-") as tmp:
        scratch = Path(tmp)
        source = args.source.resolve(strict=True) if args.source else scratch / "sample"
        if not args.source:
            search.demo(source)
        print(json.dumps(measure(source, scratch), indent=2))
