# AI Execution Packet 模板

向外部接收方交接时，所选事务的执行包保存在宿主项目的 `.governance/execution-packets.json`。按计划中的事务 ID 取包，用它对齐改动范围、验收结果和独立审查所需的证据。

## 生成命令

将 `<plugin_home>` 换成已安装的 `software-project-governance` 技能目录（其中有 `SKILL.md`），`<项目目录>` 换成宿主项目根目录，`<TASK_ID>` 换成计划中的实际 ID。从任意工作目录运行下列命令可只读预览完整 JSON。

```sh
python "<plugin_home>/infra/verify_workflow.py" --project-root "<项目目录>" execution-packet --task "<TASK_ID>"
```

用 `--contract product_success_contract`、`--contract vertical_slice` 或 `--contract interruption_policy` 选择接收方明确要求的附加契约。`--quality-dimension reliability` 只登记约定的可靠性阈值，可重复选择其他实际维度。声明的契约和阈值缺失或未证实时保留待验。

读取输出中的 `packets[事务 ID]`。若 `packets` 为空，核对该宿主计划的单元 ID 与活跃状态。需要落盘时，在同一命令末尾加 `--write`，只更新所选事务，保留其他包。旧版直接按事务 ID 存储的包也可通过这个入口读取。

## JSON 结构

计划给出 `goal` 的默认值、优先级和状态。核对 `allowed_change_scope`、`required_evidence`、`next_commands` 和 `done_definition`，为每项 `TO_BE_DEFINED` 填写该事务的事实或待验证项。直接可验收的原生单元复用自身契约。

- 包中有 `intake` 时，在宿主的 `.governance/` 下打开 `intake.record`，可找回受理时记录的范围、验收和需求依据。当前需求来源沿用 `task-priority-analysis` 的裁决。如有 `intake.demand_revisions`，可据此查阅修订依据。旧包可用上述命令预览最新定位。
- 若旧工单缺少验收原文，生成器使用计划中明确标为“验收要求”的列。重跑保留人工契约。由计划自动填入的预期结果在人工编辑前随计划修订。
- 将宿主自己的验收命令填写在 `acceptance_contract.command`。默认 `next_commands` 指向该字段。用 `expected_output` 对照实际输出，运行后填写 `last_run` 和 `demo_evidence`。

## 门禁

`check-governance --fail-on-issues` 的 Check 18c 检查执行包的必需字段。其余契约可按需打开下列模板，或通过同一已安装 CLI 运行对应检查并加 `--fail-on-issues`。

| 契约字段 | 需要确定的内容 | 检查 |
| --- | --- | --- |
| [product_success_contract](product-success-contract.md) | 用户、要完成的事、范围外事项、成功指标、对标基线与完成条件 | 18d · `check-product-success-contracts` |
| [acceptance_contract](executable-acceptance-contract.md) | 用户场景、可运行验收、预期与实际输出、演示证据 | 18e · `check-acceptance-contracts` |
| [quality_budget](quality-budget.md) | 本次适用质量维度的阈值、验证方式、状态、证据与适用例外 | 18f · `check-quality-budget` |
| [vertical_slice](vertical-slice-delivery-packet.md) | 可演示的最小用户场景、改动范围、回滚方式和验证结果 | 18g · `check-vertical-slices` |
| [interruption_policy](user-interruption-policy.md) | 须向用户确认的决策、可自行执行的动作、可逆假设与打断预算 | 18i · `check-interruption-policy` |
