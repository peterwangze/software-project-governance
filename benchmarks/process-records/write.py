# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic==2.12.5"]
# ///
"""Rehearse one evidence-backed task transition. All writes target fresh fixtures.

python write.py [--example | --schema | --request request.json]
With no arguments, compare the two existing CLI writers and a SQLite transaction.
Requires SQLite with STRICT tables and JSON support. Schema and example modes need no database.
"""
import argparse
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import closing
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError, __version__

INFRA = Path(__file__).resolve().parents[2] / "skills/software-project-governance/infra"
sys.path.insert(0, str(INFRA))
from contracts import OPERATION_ID_PATTERN, TASK_TRANSITIONS, require_task_transition  # noqa: E402

TASK = "FIX-951"
CRASH = 71
Text = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]


class Transition(BaseModel):
    """Schema for this experiment; references are project-relative file paths."""
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: int = Field(ge=1, le=1)
    operation_id: str = Field(pattern=f"^{OPERATION_ID_PATTERN}$")
    task_id: str = Field(pattern=r"^[A-Z]+-[0-9]+$")
    expected_revision: int = Field(ge=0)
    from_state: str = Field(json_schema_extra={"enum": list(TASK_TRANSITIONS)})
    to_state: str = Field(json_schema_extra={"enum": list(TASK_TRANSITIONS)})
    alignment: Text = Field(min_length=30)
    finding: Text
    artifact: Text


def example():
    return {
        "schema_version": 1, "operation_id": "op-" + "1" * 32,
        "task_id": TASK, "expected_revision": 0, "from_state": "dev", "to_state": "review",
        "alignment": "让项目维护者按同一次验收观察定位原始证据，并在提交任务审查时保留可复验的依据。",
        "finding": "第一次回放：A | B\n第二次回放：复验一致。", "artifact": "acceptance.txt",
    }


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def connect(root):
    # mode=rw prevents a typo in a reader/worker from creating a second authority.
    db = sqlite3.connect((root / "records.db").resolve().as_uri() + "?mode=rw",
                         uri=True, timeout=5, isolation_level=None)
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA synchronous=FULL")
    return db


def fixture(root, *, native=False):
    root.mkdir()
    (root / "acceptance.txt").write_text("对照样本 A | B\n复验一致。\n", encoding="utf-8")
    if native:
        gov = root / ".governance"
        gov.mkdir()
        (gov / "evidence-log.md").write_text(
            "| ID | 任务 | 类型 | 描述 | 事实依据 | 工件 | 责任 | 日期 | 门 | 结论 |\n"
            "|---|---|---|---|---|---|---|---|---|---|\n", encoding="utf-8")
        (gov / "plan-tracker.md").write_text(
            "## 当前活跃事项\n\n| 优先级 | ID | 事项 | 来源 | 版本 | 验收 | 状态 |\n"
            "|---|---|---|---|---|---|---|\n"
            f"| P1 | {TASK} | 模拟验收 | 用户 | 未规划版本 | 回放 | 进行中 |\n", encoding="utf-8")
    else:
        with closing(sqlite3.connect(root / "records.db")) as db:
            db.executescript("""
                PRAGMA journal_mode=DELETE;
                CREATE TABLE task(id TEXT PRIMARY KEY, state TEXT NOT NULL,
                                  revision INTEGER NOT NULL) STRICT;
                CREATE TABLE evidence(seq INTEGER PRIMARY KEY, operation_id TEXT NOT NULL UNIQUE,
                                      task_id TEXT NOT NULL REFERENCES task(id),
                                      request TEXT NOT NULL CHECK(json_valid(request)),
                                      artifact_sha256 TEXT NOT NULL) STRICT;
                CREATE INDEX by_task ON evidence(task_id, seq);
            """)
            db.execute("INSERT INTO task VALUES(?, 'dev', 0)", (TASK,))
            db.commit()
    return root


def digest_artifact(root, relative):
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(root.resolve()):
        raise ValueError("artifact must be inside the project")
    with path.open("rb") as f:
        digest = hashlib.sha256()
        for block in iter(lambda: f.read(65536), b""):
            digest.update(block)
        return digest.hexdigest()


def append(db, root, raw, *, interrupt=False):
    record = Transition.model_validate(raw)
    require_task_transition(record.from_state, record.to_state)
    encoded = canonical(record.model_dump())
    old = db.execute("SELECT seq,request FROM evidence WHERE operation_id=?",
                     (record.operation_id,)).fetchone()
    if old:
        if old[1] != encoded:
            raise ValueError("operation_id reused with different intent")
        return {"evidence": old[0], "replayed": True}

    digest = digest_artifact(root, record.artifact)
    seq = db.execute("INSERT INTO evidence(operation_id,task_id,request,artifact_sha256)"
                     " VALUES(?,?,?,?)", (record.operation_id, record.task_id, encoded, digest)).lastrowid
    if interrupt:
        os._exit(CRASH)  # test subprocess dies after evidence insertion, before state update
    updated = db.execute("UPDATE task SET state=?,revision=revision+1"
                         " WHERE id=? AND state=? AND revision=?",
                         (record.to_state, record.task_id, record.from_state, record.expected_revision))
    if updated.rowcount != 1:
        raise ValueError("task state or revision conflict")
    return {"evidence": seq, "replayed": False}


def write(root, raw, *, interrupt=False):
    with closing(connect(root)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        return append(db, root, raw, interrupt=interrupt)


def snapshot(db, task_id):
    task = db.execute("SELECT state,revision FROM task WHERE id=?", (task_id,)).fetchone()
    if task is None:
        raise KeyError(task_id)
    records = [{"evidence": seq, "request": json.loads(doc), "artifact_sha256": digest}
               for seq, doc, digest in db.execute(
                   "SELECT seq,request,artifact_sha256 FROM evidence WHERE task_id=? ORDER BY seq", (task_id,))]
    return {"task_id": task_id, "state": task[0], "revision": task[1], "records": records}


def trace(root, task_id):
    with closing(connect(root)) as db, db:
        db.execute("BEGIN")  # task state and evidence must describe the same committed revision
        return snapshot(db, task_id)


def lookup_operation(root, operation_id):
    with closing(connect(root)) as db:
        row = db.execute("SELECT seq,task_id,artifact_sha256 FROM evidence WHERE operation_id=?",
                         (operation_id,)).fetchone()
    if row is None:
        raise KeyError(operation_id)
    return {"evidence": row[0], "task_id": row[1], "artifact_sha256": row[2]}


def task_card(exported):
    lines = [f"{exported['task_id']}  {exported['state']}  (revision {exported['revision']})"]
    for item in exported["records"]:
        request = item["request"]
        lines.append(f"#{item['evidence']}  {request['from_state']} → {request['to_state']}  {request['artifact']}")
        lines.extend("    " + line for line in request["finding"].splitlines())
    return "\n".join(lines)


def restore(root, exported):
    # Only this experiment's one task, from its known initial state and original attachment.
    with closing(connect(root)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        for saved in exported["records"]:
            if digest_artifact(root, saved["request"]["artifact"]) != saved["artifact_sha256"]:
                raise ValueError("artifact digest differs from export")
            append(db, root, saved["request"])
        if snapshot(db, exported["task_id"]) != exported:
            raise ValueError("replayed export differs from original")


def native_cli(root, *args):
    proc = subprocess.run([sys.executable, "-X", "utf8", str(INFRA / "verify_workflow.py"),
                           "--project-root", str(root), *args], cwd=root, capture_output=True, encoding="utf-8", timeout=60)
    if proc.returncode:
        raise ValueError((proc.stdout + proc.stderr).strip())
    result = json.loads(proc.stdout)
    return result.get("result", result)


def native_write(root, raw, *, interrupt=False):
    # The released engine owns row formatting, evidence ID allocation and both receipts.
    transition = Transition.model_validate(raw)
    e = native_cli(root, "evidence-append", "--task", transition.task_id, "--type", "验收",
                   "--description", "目标对齐：" + transition.alignment, "--basis", transition.finding,
                   "--artifacts", transition.artifact, "--refs", "repo_file:" + transition.artifact,
                   "--date", "2026-11-19", "--operation-id", transition.operation_id)
    if interrupt:
        os._exit(CRASH)
    evidence_id = e.get("row_id")
    if evidence_id is None and e.get("replayed"):
        # The existing idempotent receipt omits row_id. Recover the *specific* effect.
        marker = f"governance-store evidence-append {transition.operation_id}；"
        lines = (root / ".governance/evidence-log.md").read_text(encoding="utf-8").splitlines()
        evidence_id, = [line.split("|", 2)[1].strip() for line in lines if marker in line]
    op_state = "op-" + uuid.uuid5(uuid.NAMESPACE_OID, transition.operation_id + "/state").hex
    native_cli(root, "task-row-update", "--file", str(root / ".governance/plan-tracker.md"),
               "--task", transition.task_id, "--from", transition.from_state, "--to", transition.to_state,
               "--refs", "governance_id=" + evidence_id, "--reason", "依据工件提交审查",
               "--operation-id", op_state)
    return evidence_id


def native_snapshot(root):
    gov = root / ".governance"
    lines = (gov / "evidence-log.md").read_text(encoding="utf-8").splitlines()
    task = (gov / "plan-tracker.md").read_text(encoding="utf-8").splitlines()[-1]
    from task_row_update import detect_row_state
    return {"evidence_ids": [line.split("|")[1].strip() for line in lines if line.startswith("| EVD-")],
            "state": detect_row_state(task)}


def expected_error(action, *args):
    try:
        action(*args)
    except (ValueError, sqlite3.IntegrityError, OSError) as exc:
        return str(exc)
    raise AssertionError(f"{action.__name__} accepted an invalid request")


def writer_child(root, raw, start, result):
    start.wait(timeout=30)
    try:
        result.put(write(root, raw))
    except ValueError as exc:
        result.put(str(exc))


def safety_probes(base):
    raw = example()
    root = fixture(base / "atomic")
    empty = trace(root, TASK)
    ctx = multiprocessing.get_context("spawn")
    crashed = ctx.Process(target=write, args=(root, raw), kwargs={"interrupt": True})
    crashed.start()
    crashed.join(30)
    recovered = trace(root, TASK)
    assert crashed.exitcode == CRASH and recovered == empty
    first = write(root, raw)
    after = trace(root, TASK)
    assert after["state"] == "review" and after["revision"] == 1 and after["records"][0]["request"] == raw
    assert write(root, raw) == {**first, "replayed": True} and trace(root, TASK) == after
    by_op = lookup_operation(root, raw["operation_id"])
    assert by_op["evidence"] == first["evidence"] and by_op["task_id"] == TASK
    assert by_op["artifact_sha256"] == digest_artifact(root, raw["artifact"])
    fresh = {**raw, "operation_id": "op-" + "2" * 32, "from_state": "review",
             "to_state": "dev", "expected_revision": 1}
    bad = {
        "different_intent_same_id": {**raw, "finding": "异议"},
        "unknown_field": {**fresh, "unknown": "?"}, "missing_field": {k: v for k, v in fresh.items() if k != "finding"},
        "invalid_id": {**fresh, "task_id": "bad"}, "unknown_task": {**fresh, "task_id": "FIX-952"},
        "absent_source": {**fresh, "artifact": "absent.txt"}, "escaping_source": {**fresh, "artifact": "../escape"},
        "unknown_version": {**fresh, "schema_version": 2}, "boolean_version": {**fresh, "schema_version": True},
        "wrong_type": {**fresh, "expected_revision": "1"}, "stale_revision": {**fresh, "expected_revision": 0},
        "illegal_transition": {**fresh, "to_state": "committed"},
    }
    for request in bad.values():
        expected_error(write, root, request)
        assert trace(root, TASK) == after

    # Independent connections and competing operation IDs both claim revision 1.
    start, results = ctx.Barrier(3), ctx.Queue()
    children = [ctx.Process(target=writer_child, args=(root, {**fresh, "operation_id": "op-" + key * 32},
                                                       start, results)) for key in ("3", "4")]
    for child in children:
        child.start()
    start.wait(timeout=30)
    for child in children:
        child.join(30)
        assert child.exitcode == 0
    outcomes = [results.get(timeout=2) for _ in children]
    results.close()
    assert sum(isinstance(o, dict) for o in outcomes) == 1 and "task state or revision conflict" in outcomes
    exported = trace(root, TASK)
    assert exported["revision"] == len(exported["records"]) == 2
    restored = fixture(base / "restored")
    restore(restored, json.loads(json.dumps(exported)))
    tampered = fixture(base / "tampered")
    (tampered / "acceptance.txt").write_text("changed", encoding="utf-8")
    assert "digest differs" in expected_error(restore, tampered, exported) and trace(tampered, TASK) == empty
    corrupt = json.loads(json.dumps(exported))
    corrupt["records"][-1]["artifact_sha256"] = "0" * 64
    rollback = fixture(base / "restore-rollback")
    assert "digest differs" in expected_error(restore, rollback, corrupt) and trace(rollback, TASK) == empty
    with closing(connect(root)) as db:
        journal = db.execute("PRAGMA journal_mode").fetchone()[0]
        sync = db.execute("PRAGMA synchronous").fetchone()[0]
        assert journal == "delete" and sync == 2
        check = db.execute("PRAGMA integrity_check").fetchone()[0]
        assert check == "ok" and not db.execute("PRAGMA foreign_key_check").fetchall()
    return {"journal": journal, "synchronous": sync, "crash_exit": crashed.exitcode,
            "after_crash": {"state": recovered["state"], "records": len(recovered["records"])},
            "rejections_preserving_state": list(bad), "concurrent_writers": outcomes,
            "operation_lookup": by_op, "replay_receipt": first["evidence"], "roundtrip_records": len(exported["records"]),
            "modified_attachment_rejected": True, "integrity_check": check}


def timings(base, sample):
    # Each sample includes fixture setup and the complete cold CLI path for one valid request.
    # The native side starts two Python commands and emits both families' independent receipts.
    request_file = base / "timing.json"
    request_file.write_text(json.dumps(sample), encoding="utf-8")
    elapsed = {"existing_two_cli": [], "candidate_one_cli": []}
    for repetition in range(5):
        order = list(elapsed) if repetition % 2 == 0 else list(reversed(elapsed))
        for method in order:
            start = time.perf_counter_ns()
            if method == "existing_two_cli":
                root = fixture(base / f"speed-{repetition}", native=True)
                result = native_write(root, sample)
                assert result == "EVD-1"
            else:
                process = subprocess.run([sys.executable, "-X", "utf8", str(Path(__file__).resolve()),
                                          "--request", str(request_file)], capture_output=True,
                                         encoding="utf-8", timeout=60, check=True)
                assert json.loads(process.stdout)["trace"]["records"][0]["request"] == sample
            elapsed[method].append(round((time.perf_counter_ns() - start) / 1e6, 2))
    return {method: {"milliseconds": values, "median_ms": statistics.median(values)}
            for method, values in elapsed.items()}


def benchmark(base):
    raw = example()
    native = fixture(base / "native", native=True)
    refusal = expected_error(native_write, native, raw)
    pipe = expected_error(native_write, native, {**raw, "finding": "A | B"})
    assert "newline" in refusal and "schema_violation" in pipe
    partial = native_snapshot(native)
    assert partial == {"evidence_ids": [], "state": "dev"}
    plain = {**raw, "finding": "验收结果见原始附件。"}
    native_attachment = native / raw["artifact"]
    native_attachment.write_text(raw["finding"], encoding="utf-8", newline="")
    ctx = multiprocessing.get_context("spawn")
    crashed = ctx.Process(target=native_write, args=(native, plain), kwargs={"interrupt": True})
    crashed.start()
    crashed.join(60)
    partial = native_snapshot(native)
    assert crashed.exitcode == CRASH and partial == {"evidence_ids": ["EVD-1"], "state": "dev"}
    assert native_write(native, plain) == "EVD-1"
    assert native_snapshot(native) == {"evidence_ids": ["EVD-1"], "state": "review"}
    native_write(native, plain)
    assert native_snapshot(native) == {"evidence_ids": ["EVD-1"], "state": "review"}
    assert native_attachment.read_bytes() == raw["finding"].encode("utf-8")
    return {"python": sys.version.split()[0], "sqlite": sqlite3.sqlite_version, "pydantic": __version__,
            "native_multi_line_refusal": json.loads(refusal)["detail"], "native_pipe_refusal": json.loads(pipe)["detail"],
            "native_attachment_bytes_preserved": len(native_attachment.read_bytes()),
            "native_between_commands_after_exit": partial, "native_after_retry": native_snapshot(native),
            "sqlite_guards": safety_probes(base), "timing": timings(base, plain)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--schema", action="store_true")
    group.add_argument("--example", action="store_true")
    group.add_argument("--request", type=Path, help="read a request; always replay against a new demo fixture")
    args = parser.parse_args()
    if args.schema:
        result = Transition.model_json_schema()
    elif args.example:
        result = example()
    else:
        with tempfile.TemporaryDirectory(prefix="spg-record-write-") as tmp:
            base = Path(tmp)
            if args.request:
                root = fixture(base / "demo")
                try:
                    raw = json.loads(args.request.read_text(encoding="utf-8-sig"))
                    receipt = write(root, raw)
                except ValidationError as exc:
                    details = exc.errors(include_input=False, include_url=False)
                    parser.exit(2, canonical({"error": "invalid_fields", "details": details}) + "\n")
                except (sqlite3.Error, ValueError, OSError) as exc:
                    parser.exit(2, canonical({"error": "record_refused", "detail": str(exc)}) + "\n")
                exported = trace(root, raw["task_id"])
                result = {"receipt": {**receipt, **lookup_operation(root, raw["operation_id"])},
                          "trace": exported, "view": task_card(exported)}
            else:
                if not __debug__:
                    parser.error("benchmark checks require Python without -O")
                result = benchmark(base)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
