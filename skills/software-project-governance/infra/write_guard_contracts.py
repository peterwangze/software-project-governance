"""Persisted write-guard filenames, row families and schema markers."""

_EVIDENCE_MACHINE_ROW_FAMILIES = ("TRIAGE", "RECO")

_PLAN_TRACKER_ROW_EXPECTED_SHAPE = (
    "| 优先级 | 任务ID | 标题 | 依赖 | 目标版本 | 闭环路径 | 状态 |"
    "（优先级恰一列且居于任务ID 之前；末列为状态列且必须非空；"
    "行尾不得追加空单元格——AUDIT-149 §4 M1）")

_OPS_LEDGER_RECEIPT_ANCHOR = "operation_id"

_WRITE_GUARD_STATE_FILENAME = ".write-guard-state.json"

_WRITE_GUARD_STATE_SCHEMA_VERSION = 1

_WRITE_GUARD_STATE_TOOL = "governance-write-guard/row-family-reconciliation"

_DEFERRED_LEDGER_FILENAME = ".write-guard-deferred-ledger.jsonl"

_ROW_FAMILY_TEXT_SURFACES = ("evidence-log.md", "decision-log.md",
                             "plan-tracker.md")
