# Scenario D: 会话恢复

`governance-bootstrap --format json` 给出可信根、工作单元及风险。根据 `session-snapshot.md` 的 `session_date` 和 `carry_over_tasks` 找到原意、工件位置与待确认事项。快照过期或缺失时，工作单元仍可由 `loop status --json` 恢复。

按稳定 ID 复读单元和相关子单元，核实最新轮次、裁决、证据以及决策是否仍适用。后续尝试使用原验收条件。快照中的进展描述与实物不一致时展示差异；运行文件损坏时保留现场。风险到期或放行需要授权时经 AskUserQuestion 取得裁决。
