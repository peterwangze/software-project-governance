# Scenario D: 会话恢复

`governance-bootstrap --format json` 给出可信根、工作单元及风险。按当前目标选定单元，已有判据、裁决与下一步足够时直接恢复。需要核对状态时使用 `loop status --json --unit <id>`。存在具体材料缺口时用 `loop materials --unit <id> --query "<问题词>"`，按返回的标识定位相关原件。只有交接时间或遗留事项确实影响本次判断时，才核对 `session-snapshot.md` 中对应的 `session_date` 或 `carry_over_tasks` 条目。

按稳定 ID 复读单元和相关子单元，核实最新轮次、裁决、证据以及决策是否仍适用。后续尝试使用原验收条件。快照中的进展描述与实物不一致时展示差异；运行文件损坏时保留现场。风险到期或放行需要授权时经 AskUserQuestion 取得裁决。
