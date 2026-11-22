# 授权修订与反证：隔离重放

从[正常运行入口](./lifecycle.md)开始；生产项目先由项目核实指定自然人的原回复，登记授权回执，再导入修订。下面是可执行的合成夹具：`Lin`、消息、决策及 QA 观察均为演示数据，不构成真实用户授权或独立审查。脚本实际重新打开 CSV 并计算总额；生产验收应由独立验证者经成品正常入口保存实测原件。

将代码保存为 `replay.py`，从可写的测试目录运行 `python replay.py <已安装技能的infra/verify_workflow.py绝对路径>`。仅在当前目录新建 `approval-example-*` 子目录，保留全部证据，不修改现有项目。每个 `cli(...)` 都启动新进程，失败即停止。示例无提交、安装、发布操作；`release_version` 仅为成品契约字段，根单元没有 `--release-version`。

```python
import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path
import subprocess
import sys
import uuid

tool = Path(sys.argv[1]).resolve(strict=True)
root = (Path.cwd() / ("approval-example-" + uuid.uuid4().hex)).resolve()
root.mkdir()
(root / ".governance").mkdir()

def sha(name):
    return hashlib.sha256((root / name).read_bytes()).hexdigest()

def put(name, text):
    (root / name).write_bytes(text.encode("utf-8"))
    return sha(name)

def record(name, value):
    return put(name, json.dumps(value, ensure_ascii=False, indent=2))

def cli(*args, ok=True):
    p = subprocess.run([sys.executable, "-X", "utf8", str(tool),
                        "--project-root", str(root), *args], cwd=root,
                       capture_output=True, encoding="utf-8", timeout=30)
    assert (p.returncode == 0) == ok, p.stdout + p.stderr
    return json.loads(p.stdout)

def status():
    return cli("loop", "status", "--unit", "invoice", "--json")

original = {"total": "Reopen CSV and reconcile every row to 19.99"}
put("invoice.csv", "item,amount,currency\nA,15.00,USD\nB,4.99,USD\n")
contract = dict(schema_version=1, goal_id="invoice", release_version="1.0.0",
                artifact="invoice.csv", entrypoint="Open invoice.csv",
                producer="Developer", verifier="Customer QA", criteria=original)
contract_sha = record(".governance/delivery-contract.json", contract)
receipt = dict(schema_version=1, contract_sha256=contract_sha,
               artifact_sha256=sha("invoice.csv"), entrypoint=contract["entrypoint"],
               verifier="Customer QA", results={}, revisions=[])

def observe(key, sample):
    with (root / "invoice.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert sum(Decimal(r["amount"]) for r in rows) == Decimal("19.99")
    if key == "currency":
        assert all(r["currency"] == "USD" for r in rows)
    evidence = key + ".log"
    digest = put(evidence, f"{sample}: reopened two rows; total 19.99; currencies USD\n")
    receipt["results"][key] = dict(status="PASS", evidence=evidence, evidence_sha256=digest)
    record(".governance/delivery-receipt.json", receipt)

cli("loop", "start", "--unit", "invoice", "--authority", "Lin",
    "--intent", "I need to audit the exported invoice", "--goal", "Deliver invoice",
    "--acceptance", "Reopen CSV and reconcile every row to 19.99",
    "--tier", "middle", "--gate", "G9", "--product-goal", "invoice",
    "--criteria", json.dumps(original))
put("trial.log", "Compared reopening CSV with the screen total; both rows are needed.\n")
cli("loop", "learn", "--unit", "invoice", "--id", "rows", "--kind", "decision",
    "--observation", "Both rows are present", "--action", "Keep row export",
    "--validation", "Reopen and reconcile all rows", "--evidence", "trial.log",
    "--criterion", "total", "--candidate", "invoice.csv")
observe("total", "original sample")
cli("loop", "accept", "--unit", "invoice")
assert status()["learning"][0]["revalidation"]["status"] == "passed"

# A reporter challenges the result without permission or changed criteria.
event = dict(id="challenge", kind="counterevidence", unit="invoice", base_revision=0,
             actor="Reporter", reason="Check the second-row case again", criteria=original)
challenge_sha = record("challenge.json", event)
cli("loop", "revise", "--unit", "invoice", "--evidence", "challenge.json")
assert status()["runtime_status"] != "completed"
receipt["revisions"] = [challenge_sha]
record(".governance/delivery-receipt.json", receipt)
cli("loop", "accept", "--unit", "invoice", ok=False)  # Old observation is insufficient.
observe("total", "replayed second-row counterexample")
cli("loop", "accept", "--unit", "invoice")

# Only this fixture manufactures a response. Production preserves the real message.
quote = "Keep the 19.99 reconciliation and also show USD for every row."
response_sha = put("human-response.txt", quote + "\n")
approved = dict(id="add-currency", kind="authorization", unit="invoice", base_revision=1,
                actor="Lin", reason="Add currency display; recheck currency on the reopened CSV",
                criteria={"currency": "Every reopened row displays USD"},
                response=dict(message_id="fixture-message-001", source="human-response.txt",
                              sha256=response_sha, quote=quote))
approved_sha = record("approved.json", approved)
# Minimal fresh-project decision ledger, matching the registered decider and JSON digest.
put(".governance/decision-log.md",
    "| ID | Date | Decider | Content | Reason |\n| --- | --- | --- | --- | --- |\n"
    f"| DEC-001 | 2026-11-22 | Lin | Approved {approved_sha} | Source fixture-message-001 |\n")
cli("loop", "revise", "--unit", "invoice", "--evidence", "approved.json", "--decision", "DEC-001")
cli("loop", "accept", "--unit", "invoice", ok=False)  # Receipt predates authorization.
receipt["revisions"].append(approved_sha)
observe("currency", "authorized currency recheck")
cli("loop", "accept", "--unit", "invoice")
final = status()
assert final["runtime_status"] == "completed"
assert final["root_contract"]["original_criteria"] == original
assert final["root_contract"]["criteria"] == dict(original, **approved["criteria"])
assert final["root_contract"]["revision"] == 2

# The accepted file changes later: a new candidate cannot be added to a completed unit.
put("invoice.csv", "item,amount,currency\nA,15.00,USD\nB,4.99,USD\n\n")
stale = cli("loop", "status", "--unit", "invoice", "--json", ok=False)
assert stale["runtime_status"] == "unverified"
assert stale["learning"][0]["revalidation"]["status"] == "stale"
replacement = ("loop", "learn", "--unit", "invoice", "--id", "rows-v2",
               "--kind", "decision", "--observation", "Reopened the changed CSV; both rows remain",
               "--action", "Use the updated CSV", "--validation", "Reopen, reconcile and check USD",
               "--evidence", "trial-v2.log", "--criterion", "total",
               "--candidate", "invoice.csv", "--supersedes", "rows")
put("trial-v2.log", "Changed CSV reopened; two rows still total 19.99 and display USD.\n")
cli(*replacement, ok=False)
cli("loop", "recheck", "--unit", "invoice")
cli(*replacement)
cli("loop", "accept", "--unit", "invoice", ok=False)  # Old artifact digest is insufficient.
receipt["artifact_sha256"] = sha("invoice.csv")
observe("total", "replacement CSV total recheck")
observe("currency", "replacement CSV currency recheck")
cli("loop", "accept", "--unit", "invoice")
assert status()["learning"][-1]["revalidation"]["status"] == "passed"
print("PASS: revisions and postcompletion candidate recovery rechecked:", root)
```

预期：先通过原验收；反证重开后，仅补 `revisions` 仍拒绝旧观察，重放原样本后恢复；授权增加 `currency` 后旧回执再次拒绝，新增实测回执后通过。完成后改变 CSV 会使状态失效，直接登记候选被拒绝；`recheck` 重开、`--supersedes rows` 登记替代选择、更新制品摘要并重新观察后恢复通过。查看输出目录中的 `challenge.json`、`approved.json`、`human-response.txt`、决策表及运行回执，可沿两层摘要复核原回复与确切变更。无需给反证者指定 `authority`；授权所需的 `actor` 必须是根创建时指定的 `Lin`。

主管可向用户简报：「原目标的逐行核对已通过；原总额判据保留。Lin 经 DEC-001 授权增加 USD 显示，反证样本与新增条件已复验；后来更换的 CSV 也已重新验收。当前制品对应回执可查。」按需展开 `root_contract.original_criteria/criteria/revisions`、原回复标识和引文、`learning[].candidate_sha256` 与 `revalidation.evidence_ref`、受影响单元及未测边界。真实项目须以实际结果替换这段夹具报告。
