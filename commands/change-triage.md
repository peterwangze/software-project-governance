# change-triage — 变更控制 triage（产品代码新任务强制入账门禁）

> **FIX-237.4 / ADR-017 §4.4**：产品代码新任务（涉及 `skills/**`、`agents/**`、`infra/**`、`commands/**`、`adapters/**` 等）**MUST** 先运行本命令完成五步 triage 并产出机器 triage 记录，之后才允许创建 task。快速通道仅限 `.governance/` 治理记录（FIX-228 边界）。
>
> **FEAT-111 / DEC-377④（prior-art 入账门禁）**：设计/研究类任务族（`FEAT`/`DESIGN`/`RESEARCH`/`AUDIT`——从仓库任务族词汇派生的语义子集）triage 时 **MUST** 附外部输入面（`--prior-art`：先例/竞品/外部证据引用，如 Rust RFC Prior art 节、专利审查 prior-art 检索指南、竞品文档链接）；缺失或占位串（空/`TO_BE_DEFINED`/`待定` 族）→ **拒收**（fail-closed，退出码 2 零写入）。执行/修复类（`FIX`/`REL`/`MAINT` 等族）豁免，记录以 `prior_art_required=false` 披露。Check 32 对生效日（2026-10-29）起的设计/研究类记录强制校验同一面（此前入账的不可变记录与执行族豁免）。

## 命令

```powershell
python skills/software-project-governance/infra/verify_workflow.py change-triage `
  --task FIX-241 --title "..." --priority P2 --version 0.73.0 `
  --depends-on "FIX-237" --files "skills/software-project-governance/infra/x.py" `
  --reason "triage 理由"
```

## 输入参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--task` | ✅ | 新任务 ID（`PREFIX-NNN`，如 `FIX-241`） |
| `--priority` | ✅ | 提议优先级 `P0`/`P1`/`P2`（结合 in-flight + 版本链判定） |
| `--files` | ✅ | 新任务将修改的产品文件（逗号分隔；`.governance/` 快速通道不适用本命令） |
| `--prior-art` | 设计/研究类 ✅ | 外部输入面引用（逗号/分号分隔）。**设计/研究类族（`FEAT`/`DESIGN`/`RESEARCH`/`AUDIT`）必填**：引用先例/竞品/外部证据（如 Rust RFC Prior art 节、专利审查 prior-art 检索指南）；缺失或占位串拒收（FEAT-111 / DEC-377④）；执行/修复族豁免（可自愿携带） |
| `--version` | 否 | 目标版本（semver `X.Y.Z` 或 `未规划版本`，默认 `未规划版本`） |
| `--depends-on` | 否 | 任务族依赖 ID（逗号分隔；`RISK-`/`DEC-`/`REVIEW-` 等跨实体引用自动忽略） |
| `--title` | 否 | 一句话任务标题 |
| `--reason` | 否 | 优先级判定理由 |
| `--project-root` | 否 | 显式宿主项目根（默认 resolve_entry 解析） |

## 五步分析（MUST 全量执行）

1. **依赖分析**：运行 `task-priority-analysis`（task_priority 纯读），快照完整工具输出（`report_json` + `report_text`）到 triage 记录；识别新任务被哪些未完成任务阻塞、依赖环（既有环 = WARNING，新任务自身成环 = 拦截）。
2. **优先级判定**：校验 `P0`/`P1`/`P2`，输出 in-flight 各优先级任务计数 + 版本路线图版本链上下文。
3. **冲突检查**：与 in-flight 任务（既有 triage 记录中的文件集）比对相同文件重叠；已完成任务不构成冲突。
4. **版本适配**：目标版本 MUST 为 semver 或未规划标记；版本基准 = **项目当前版本**（宿主 plan-tracker 版本路线图最高「已发布」行——不是工作流/插件自身版本，两层语义分离，FIX-288）；低于项目当前版本 = ERROR；与版本路线图规划的下一个版本（规划行中高于项目当前版本的最低版本）不一致 = advisory WARN。无版本路线图/无已发布行的宿主跳过下界比较，可正常 triage 入账。
5. **副作用声明**（FIX-271）：检测任务输入（`--files`/`--reason`/验收描述）隐含的仓库外副作用（安装器执行/真实 profile 写入/网络发布）；触及用户真实环境自动附加 R1 审查条件；检测到信号而未声明（`--side-effects`）→ WARN（advisory，不阻塞）。记录落入纯增量字段 `analysis.side_effect`。

## Fail-closed 规则（不满足 = 无记录 + 退出码 2）

- 未知任务族依赖 ID（不在 plan-tracker 中，FIX-171 保守默认）
- 优先级非 `P0`/`P1`/`P2`
- `--files` 为空
- 目标版本低于项目当前版本 / 非 semver
- 新任务自身制造依赖环
- `--task` 非 `PREFIX-NNN`
- **设计/研究类族（`FEAT`/`DESIGN`/`RESEARCH`/`AUDIT`）缺 `--prior-art` 或条目为占位串**（FEAT-111 / DEC-377④——终结「自引问题自修复」自嗨循环的机制性倒逼）

## 产出

- 机器 triage 记录：`.governance/change-triage/{TASK_ID}.json`（含五步分析 + task-priority-analysis 输出快照；FEAT-111 增量键：`prior_art`（引用条目列表）+ `prior_art_required`（设计/研究类 `true` / 执行类 `false` 豁免披露））
- evidence-log 行：`| TRIAGE-{TASK_ID} | {TASK_ID} | 变更控制 | ... | TRIAGED |`（调用快照 = 记录文件中的命令输出 JSON，FIX-237.5）
- Check 32（`check-governance`）验证：CLI 接线存在、记录合法、晚于 normalization 边界的产品代码任务无记录 = FAIL；**2026-10-29 起的设计/研究类记录缺合法 `prior_art` 面 = FAIL**（历史记录与执行族豁免）

## 使用时机

- 任何产品代码新任务入账前（标准路径，FIX-228）
- 任务完成后推荐下一步时，MUST 运行 `task-priority-analysis` 并记录调用快照（FIX-237.5 / M7.4 step 6a）

## 边界

- 快速通道（`.governance/` 治理记录修改）无需本命令
- 本命令不创建 task、不写 plan-tracker——只产出 triage 记录供入账使用
