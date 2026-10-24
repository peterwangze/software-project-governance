# 0.99.0 收尾范围与发布缺口盘点（REL-103）

- **日期**：2026-10-16（Asia/Shanghai）。
- **性质**：只读盘点及执行建议；不是发布通过证据，不是 GO 决策。
- **快照锚**：`master@a001057`。本报告只写此文件；不改产品代码、CI、版本号或 `.governance/`。
- **当前治理事实**：always-on × maximum-autonomy；维护与演进第 11 阶段，G11 pending；历史 G9 为 passed-on-entry，不能代替本版发布检查。
- **待澄清边界**：FIX-444/445 经 DEC-342 暂停，DEC-358①仅顺延至 0.99.0，未恢复。Coordinator 已向用户澄清恢复或保持暂停的范围；本文不代为选择，也不静默移出本版。

## 1. 结论与版本事实

0.99.0 仍有实质开发、独立审查、范围确认和整条发布链待完成，不能直接 bump/tag 结账。已完成的 pi 适配、chrys 出列和 CRLF 修复可作为本版确定载荷；其余任务以表中真实状态推进。

| 事实 | 本次核对结果 | 权威来源 |
|---|---|---|
| 已发布版本 | 0.98.0；candidate `a0cb78e` → transition `7f161a6`；tag `v0.98.0` | `core/releases/0.98.0.json`（本表 `core/` 均相对 `skills/software-project-governance/`）；plan-tracker 项目配置及 0.98.0 路线图行 |
| 活跃版本权威 | SKILL frontmatter `version: 0.98.0` | `skills/software-project-governance/SKILL.md:3` |
| 其他版本声明 | core manifest、package、平台声明及根双入口目前仍承载 0.98.0 | `core/version-projections.json`；根 `AGENTS.md`/`CLAUDE.md` bootstrap 标记 |
| 0.99.0 规划载体 | 任务行已分散登记；当前路线图无 0.99.0 行，无 `version-plan-0.99.0.md`；本报告只提供收口建议 | `.governance/plan-tracker.md:66-105` 及版本规划表；`docs/release/` 文件清单 |
| 0.99.0 发布工件 | 尚无 native manifest、CHANGELOG 段、release checklist/rollback/flags 三件套；本地 `v0.99*` tag 查询为空 | `core/releases/`；`project/CHANGELOG.md`；`docs/release/`；`git tag -l 'v0.99*'` |
| 发布后提交窗口 | `v0.98.0..a001057` 共 7 commits；其中 `f392a0b` 为 0.98.0 M-8 收尾，不能冒称 0.99 新产品功能 | `git log v0.98.0..HEAD` / `git rev-list --count v0.98.0..HEAD` |

建议维持 0.98.0 → 0.99.0 MINOR（新增平台能力及体验验收能力，不跳号），最终范围/semver 由 Coordinator 在 M-0 冻结。FEAT-101 删除平台支持必须有移除/迁移说明并独立评估兼容性，不可未经评估写“无破坏性变更”。`core/VERSIONING.md` 允许 pre-1.0.0 Minor 承载有限 Breaking Change；本次不升级 1.0.0，也不据此宣称 RISK-036/039 关闭。

## 2. 全量 0.99.0 任务账（12 行，不含未规划 FEAT-099）

“已交付”仅代表相应任务的实现/审查证据，不表示 0.99.0 发布门已通过。行号按 `a001057` 盘点时热表记录。

| ID / 优先级 | 真实状态 | 需求源与证据锚 | 收尾必做项 |
|---|---|---|---|
| FIX-444 / P1 | **BLOCKED；R3 BLOCKED/3 熔断**，由 FIX-445 承接但未解锁 | plan-tracker:88；TRIAGE-FIX-444（active-defect）；REVIEW-FIX-444-R0~R3；DEC-334/342/358① | 等待明确恢复边界；原合规否定句放行、肯定/混合无依据与缺来源阻断、真实 bash hook 回归、安全边界全保留；不能自动 R4 或改成完成 |
| FIX-445 / P1 | **BLOCKED、暂停**；DESIGN R15 AWN/0 仅分析质量，`implementation_authorized=false`；CODE R6 BLOCKED/3 | plan-tracker:90；TRIAGE-FIX-445（active-defect）；DEC-342（原门与四源验收保持）；DEC-358①；现有 hook/test WIP | 用户明确恢复后仍要解决 W1 语料分配及 R6 三阻断；保留 CPU/CLI/资源约束、完整来源与安全攻击拒绝；关键 hook 用户交付审查边界随原记录执行 |
| FEAT-098 / P2 | **待实施，立项就绪**，不是已交付 | plan-tracker:97；TRIAGE-FEAT-098（machine-signal）；DEC-330/354；EVD-1711；`docs/requirements/analysis-rpg-longhaul-capability-session-f3f46901-0.97.0.md` §2/§3.7 | 先补 execution-packet；实现 E2E 体验契约与 success_metrics、按调用重建成本、返工归因、基线快照；完整回归及独立审查 |
| FIX-447 / P2 | **待实施** | plan-tracker:98；TRIAGE-FIX-447（active-defect）；EVD-1707 C4 残余风险；`.governance/change-triage/FIX-447.json` | 构造或证伪 INVENTORY drift/load_timing 并发复现；排除/稳定化；串行及并发双态验证，不能只拿串行绿结账 |
| FIX-448 / P2 | **待实施** | plan-tracker:99；TRIAGE-FIX-448（machine-signal）；REVIEW-REL-102-R2 P3-2；DEC-358①；change-triage/FIX-448.json | 结构化瘦身热证据表，目标 28s PASS；解释 active_task_ref/missing_task_ref 保留策略；与 FIX-446 不覆写旧档、不丢热证据安全语义联验 |
| FIX-449 / P2 | **待实施** | plan-tracker:100；TRIAGE-FIX-449（machine-signal）；DEC-213③；change-triage/FIX-449.json | 6 处静态版本针派生化或有理由的限域豁免；版本 WARN 清零/回落；测试覆盖 bump 后行为，不能机械改成 0.99.0 再留下下版欠账 |
| FIX-450 / P2 | **待实施；收敛或预算裁定两条合法路径** | plan-tracker:101；TRIAGE-FIX-450（machine-signal）；EVD-1708；DEC-325 为重定标先例，非本版授权 | FEAT-098 新契约加入后量测并瘦身至 skill ≤16000，或具体新 DEC 裁定重定标；resident 硬门不劣化；不得只为过门静默抬阈值 |
| FEAT-100 / P1 | **已实现、审查、提交及本机接线验证** | plan-tracker:103；TRIAGE-FEAT-100（user-named）；EVD-1713~1719；REVIEW-FEAT-100-R0/R1/R2 AWN/0；`cc40646`/`b7be5a5`/`41de8ed`；DEC-359/360 | 编入发布范围、用户视角 changelog 与回滚；如实保留 headless 错误行为及 browser/mcp DEGRADED；不能扩称全运行时支持 |
| FEAT-101 / P1 | **已实现、审查、提交**；任务行同时含“完成 待执行”，投影措辞待校准 | plan-tracker:104；TRIAGE-FEAT-101（user-named）；EVD-1720~1722；REVIEW-FEAT-101-R0 AWN/0；`7db915b`/`a001057` | Coordinator 依据证据机录对齐终态；发布时披露 chrys 移除与迁移；M-1 核对版本一致性文件数 12 / plugin.json 3 |
| FIX-451 / P1 | **已实现、审查、提交**；任务行同有混合“完成 待执行” | plan-tracker:105；TRIAGE-FIX-451（active-defect）；EVD-1723/1724；REVIEW-FIX-451-R0 AWN/0；`930aabc`；DEC-361；RISK-068 已关闭 | 校准终态；发布门复核 CRLF 容忍/纯 LF 恒等/同步态零写入；禁止对暂停 WIP 执行 renormalize |
| FIX-452 / P1 | **诊断中；不是修复完成** | plan-tracker:66；TRIAGE-FIX-452（user-named）；change-triage/FIX-452.json；`.github/workflows/ci.yml` | DevOps 提供原始失败日志、根因、最小修复、独立审查；本地匹配 CI 命令通过及远端 Actions 全绿；本文不代替该 Agent 的日志取证 |
| REL-103 / P1 | **范围盘点中**；本文仅其规划产物 | plan-tracker:67；TRIAGE-REL-103（user-named）；change-triage/REL-103.json | 范围确认、必要实现收齐、版本组装、独立发布审查、候选/发布两态验证、ledger/tag/remote 一致及归档结账 |

**明确边界**：FEAT-099（DSH 宿主执法 PoC）在 plan-tracker:102 为“未规划版本”，不因推荐列表出现而自动入 0.99.0。FIX-444/445 是否继续承载待用户澄清，本文没有作排除决定。0.98.0 已发布载荷也不重新冒称本版新交付。

## 3. 发布阻断面与证据缺口

| 阻断/缺口 | 当前事实 | 解除条件 |
|---|---|---|
| 暂停范围与共享工作树 | 仅两处产品 WIP：`infra/hooks/commit-msg`、`infra/tests/test_hooks.py`；只读 `git diff --numstat` 分别 +743/−2、+855/−2。DEC-342/361 保全边界仍在 | 用户明确恢复或明确保持暂停并给出本版处置；未回答前只能推进独立获授权任务 |
| **bump 会触碰暂停 WIP** | registry `hook-commit-msg` 为 transformed_text；FIX-451 只保证**同步态**零写入，真正版本 bump 会修改匹配区 | 暂停解除后按原链收口，或 Coordinator 建立独立干净发布工作区并证明未混入 WIP；不在共享脏树直接 `release-projection --write`，不把 WIP 顺手带入候选 |
| 未交付载荷 | FEAT-098、FIX-447~450 仍待实施；FIX-452 正在诊断；FIX-444/445 暂停 | 逐票按既定验收+独立 Reviewer 通过；如需改变范围须显式新决定，不把缺失实现记作 PASS |
| 规划与事实源欠账 | 无 0.99 路线图行；101/451 状态措辞混杂；待做票缺完善执行包 | Coordinator 通过权威事务/投影工具校准，补齐 execution-packet 与成功指标，再冻结范围 |
| CI 尚未恢复 | 当前四步为 integrity → manifest → unittest → cross-references；GitHub runner 为 Ubuntu/Python 3.11 | FIX-452 实证恢复；不靠删步、跳过测试、ignore exit code 取得绿灯 |
| 回归不等于全绿 | EVD-1713 历史 4911P/41F（基线 4909P/42F）；EVD-1720 历史 4902P/58F；最新 EVD-1723 历史 4921P/39F，only-in-mine=∅ | M-2 对最终候选重新安静窗全量实测；逐类归因并修复/作具体裁定；这些旧数值只作历史锚，不能写成本次全绿 |
| 健康 FAIL 与预算 | 0.98 的 18d-RB2×2、Check30-V1、28s 经 DEC-358①仅在 **0.98** 披露；skill 17484/16000 为旧实测 report-only 超限 | 0.99 重新采样、按 FIX-448/450 及暂停决定处置；旧 GO 不自动豁免新版本；resident 硬门保持 |
| 基线与冻结面 | 当前只读计数 engine 28214 行；R1 anchor 28270、R4 total 1376；snapshot/golden 后续还会受代码、文件清单与版本变化影响 | 先查漂移、逐轴/逐 commit 归因；需要再生成时走 §5，不能复制 0.98 的旧 anchor 28204 |
| 发布安全证据 | 0.99 rollback 演练、checklist、changelog、flags 边界、兼容性评估、观察计划都尚无证据 | 隔离验证回滚与核心流程，逐项记录真实命令/输出/时间/负责人；发布三件套不能预填全部 PASS |
| native ledger 与远端事实 | 尚无 0.99 candidate/transition/tag | §4 按单父相邻提交顺序完成；候选 PASS 不替代 released PASS；UNKNOWN/BLOCKED 不改写 PASS |

本报告没有执行全量验证、回滚、发布或归档。以上“历史实测”均明确引用已有记录；当前新的门禁结果仍待各执行 Agent 实跑。

## 4. 可执行顺序：先交付范围，再 M-0~M-8 发布

### 4.1 载荷与范围准备

1. **先修 FIX-452 CI**：保留四步约束，取原日志、定位失败根因、正常审查/提交，再用相同 SHA 的远端 Actions 证明恢复。可与只读规划并行。
2. **保持暂停隔离**：不写两处 WIP、不 renormalize、不提交 WIP。等待用户范围澄清；FIX-444/445 若恢复，按原完整来源方案/代码审查和性能门推进；若继续暂停，其版本归置只能按明确裁定更新。
3. **完成尚未交付范围**：建议 FIX-447（测试稳定性）→ FIX-448（证据表结构性收敛）→ FIX-449（版本针派生化）→ FEAT-098（体验/成本能力）→ FIX-450（最终注入面量测与收敛）。这是执行建议，不替代任务依赖与文件锁检查；同一 engine/SKILL/快照面串行，严禁不同 Agent 同时 regen。
4. **收齐逐票完成链**：原验收命令、原始结果、仅增量失败归因、独立审查机录、义务闭环及正常提交；101/451 行按真实提交证据校准。不得用“只有基线失败”替代最终发布判定。

### 4.2 发布里程碑（按本版采用的实际工序定义）

历史版本编号略有差异：0.85 计划把 candidate 放 M-1、tag 放 M-5；0.98 实际为 M-1 版本面、M-5a candidate、M-5b transition、M-6 ledger、M-7 tag/push。本版建议沿最近 0.98 实际工序，并显式把 **released 远端门安排在 push 后**，避免拿尚未推送时的 remote 缺失冒充通过。

| 里程碑 | 必做动作及产物 | 进入下一步条件 |
|---|---|---|
| **M-0 范围/准备评估** | 本报告复核→完善正式范围、批次、semver、兼容性/移除说明与时间窗；规划 Release+Design 双审；Coordinator 依据明确授权冻结 roadmap/任务范围；补齐所有准备阻断及基线处置 | 暂停边界已明确；最终范围均有交付证据；新增风险/漂移归因可审；不继承旧版 GO 豁免 |
| **M-1 版本面组装** | 在获授权且与 WIP 隔离的工作区先改唯一权威 SKILL frontmatter 为 0.99.0，再 `release-projection --write`；根双入口/fixture 用 canonical 投影同步；复核版本静态针和镜像；开始最终 CHANGELOG 与三件套 | 版本一致/manifest/projection/入口同步全部通过；写入原子性与 rollback journal 规则有回归证据；未把暂停 WIP 混入提交 |
| **M-2 安静窗全量验证** | `check-release --version 0.99.0 --require-changelog --lineage-mode candidate`；完整 CI 四步与全套件；预算三 profile、archguard/contract matrix、可选质量工具、各载荷验收、隔离回滚及体验冒烟 | 所有 FAIL 逐项真实处置；本版阻断项清零或满足既定正式裁定机制；不使用 `--skip-execution-gates` 作为发布通过 |
| **M-3 双半面审查** | 独立 Code Reviewer 与 Release Reviewer 核对最终载荷/版本面/范围/回滚/兼容性/证据；设计语义面按对应 Design 审查要求；机录精确修订与报告 hash | unresolved_blockers=0，修订/范围绑定有效，所有复审义务闭合；发现变更后按 delta 复审契约重审 |
| **M-4 最终发布决策与文档冻结** | 三件套、CHANGELOG、必要审查报告及验证事实先落盘并提交；Coordinator 只在既有授权不足时请求具体 transition/tag/push 决定，旧 0.98 授权不自动覆盖本版 | 用户已授权本版动作且审核面完整；回滚实际验证有证据；再跑候选门确认完整工件 |
| **M-5a native candidate** | 新建 `core/releases/0.99.0.json`（native、candidate、events=[]、effective_state 派生正确、artifacts 指向已存在最终文档），首次加入 Git；该提交记为 **C**；`release-ledger --version 0.99.0 --no-remote` | NATIVE_CANDIDATE PASS；首次加路径唯一；所有其他改动已在 C 或其祖先，不在 C 后追加文档/修复 |
| **M-5b 唯一 transition** | **紧接 C** 创建提交 **T**，仅修改 0.99 manifest：candidate→released、唯一 candidate_to_released 事件、真实授权 claims/recorded_at、event_integrity、effective_state；只有一个 parent=C | `git show -s --format=%P T` 精确等于 C；`git diff --name-only C T` 仅 manifest；不 merge、不 rename/delete/readd、不重复 transition |
| **M-6 本地 ledger** | `release-ledger --version 0.99.0 --no-remote`；检查 T/唯一事件/integrity/原始 C 及工件可解析性 | NATIVE_RELEASED 本地 PASS。此结果尚不证明远端 tag 已存在 |
| **M-7 tag/push/远端门** | annotated tag `v0.99.0` 指向 T；推送最终分支及 tag（在已配置可用 remote 上优先 atomic）；查询 peeled SHA；`release-ledger --version 0.99.0 --remote <remote>`；`check-release --version 0.99.0 --require-changelog --lineage-mode released --release-commit T --lineage-remote <remote>`；同最终 SHA Actions | 本地/远端 tag 均 peel 到 T；两门 PASS；远端 CI 全绿；网络受限时如实 UNKNOWN/BLOCKED，保留补推义务，不宣称已完全发布 |
| **M-8 版本结账/归档** | 按 taggerdate 权威回填日期/版本与 roadmap 已发布；记录真实发布后冒烟、影响指标/替代成功定义、观察窗口与负责人；归档 dry-run→必要迁移→integrity；风险/完成推荐/session-snapshot 更新 | 无待处理归档或完整性失败；观察义务有真实结果或明确未完状态；最终记录与 tag/ledger/CI 一致，才能称本版收尾 |

**C→T 相邻约束**：C 创建后若发现需改产品、版本面、CHANGELOG 或审查报告，应先停 transition 并重整候选，而不是在 C 与 T 之间插入普通提交。candidate commit 来源是 Git 中首次加入 manifest 的唯一提交，不能用 JSON 手填另一个 HEAD 改写。

**manifest 序列化**：使用 `infra/release/ledger.py` 的 canonical JSON 及 `event_integrity()`，不要手写假的 hash。当前 canonical bytes 要求 NFC、排序键、紧凑分隔符及末尾一个 LF；事件 integrity 排除自身字段。`facts.release_authorized` 在当前 ledger 校验代码中固定为 false，**不是可手改成 true 的 manifest 开关**；本版真实动作授权应保留在具体用户决定/claims/治理证据中。

## 5. 基线再生成：准入、命令与防误用

盘点时只读事实：registry **27 条 projection records**；version-consistency **12 个版本声明文件 / 3 个 plugin.json**（FEAT-101 后口径），两者不是同一种计数。当前 architecture baseline R1 **28270**、engine **28214**、R4 total **1376**。EVD-1713 已记录 FEAT-100 rider 从 28204→28270，含 +247 前窗欠账披露；DEC-359③记录其溯源义务。新版本不得照抄旧 0.98 checklist 的锚点或无条件再锚。

1. **先查后写**：执行 `archguard-ratchet` 及 generator `--check`/`--self-check`，保存真实漂移与前后测量。R1/R4 增长要逐函数/逐 commit 归属；R2 新反向依赖、R3 禁边/环不能靠重采样吞掉。
2. **有依据才 regen**：合法功能增量须绑定对应任务、独立审查及 sanctioned DEC/rider；参考 DEC-324/326/358③。只允许工具生成提取区，authored exemptions/managed_modules 也不能默默放宽。新锚点起的 only-down 语义必须保留；不是“红了就 regen”。
3. **冻结面串行**：代码/版本/文档文件清单先稳定，再按实际漂移生成 contract snapshot / golden / architecture baseline；新增审查文件进入 manifest glob 后如 golden 再漂移，说明原因并再生成，不能手改结果行。
4. **再生成之后复验**：generator check+self-check、archguard 七轴、相关冻结字面量/负例测试及最终候选门。snapshot 或 baseline 自身提交必须进入独立审查范围。

以下为 Coordinator/执行 Agent 的**待执行命令清单**，本文未执行这些验证/写入命令；均从仓库根运行，逐条保存 exit code 和原输出：

```powershell
$spgInfra = 'skills/software-project-governance/infra'
$spgVerify = Join-Path $spgInfra 'verify_workflow.py'

# 读面检查，先解释漂移
python $spgVerify archguard-ratchet
python "$spgInfra/contract_matrix/generator.py" --check
python "$spgInfra/contract_matrix/generator.py" --self-check
python $spgVerify release-projection

# 仅在范围/基线裁定、文件锁与 WIP 隔离齐备后执行写面
python "$spgInfra/contract_matrix/generator.py" --regen
python "$spgInfra/contract_matrix/generator.py" --golden
python $spgVerify archguard-ratchet --regen
python $spgVerify release-projection --write
python "$spgInfra/sync_entry_projection.py" --project . --source-root . --profile standard --primary CLAUDE.md --write
python "$spgInfra/sync_entry_projection.py" --project project/e2e-test-project --source-root . --profile standard --primary CLAUDE.md --write

# 写面之后必须重新检查；选择实际发生漂移的生成器，勿无谓更新金样时间戳
python $spgVerify check-version-consistency
python $spgVerify check-manifest-consistency --fail-on-issues
python $spgVerify check-projection-sync
python $spgVerify release-projection
python "$spgInfra/contract_matrix/generator.py" --check
python "$spgInfra/contract_matrix/generator.py" --self-check
python $spgVerify archguard-ratchet

# M-2 全量与预算；check-release 自带 verify/health/e2e/unittest，不跳执行门
python $spgVerify
python $spgVerify check-governance --fail-on-issues
python $spgVerify e2e-check
python -m unittest discover -s "$spgInfra/tests" -v
python -m pytest "$spgInfra/tests"
python $spgVerify check-cross-references
python $spgVerify check-injection-budget --profile lightweight --format json --fail-on-issues
python $spgVerify check-injection-budget --profile standard --format json --fail-on-issues
python $spgVerify check-injection-budget --profile strict --format json --fail-on-issues
python $spgVerify quality-tools
python $spgVerify check-release --version 0.99.0 --require-changelog --lineage-mode candidate

# M-8 归档：先解释 dry-run；有待迁移项才执行 migrate --auto
python "$spgInfra/archive.py" migrate --auto --dry-run
python $spgVerify check-archive-integrity
```

可选 Ruff/mypy 未安装只记 NOT_RUN；执行错误记 FAIL。预算 `--budget-tokens` 是诊断能力，不能临时传更大值当成达标。若 FIX-450 选择重定标，必须修改权威政策/对应测试并保留真实 DEC 与结构性代价披露。

## 6. 发布文档必须承接的实际内容

- **CHANGELOG**：pi 新增与实际能力等级/headless 边界；chrys 移除及迁移指引；CRLF/投影修复；真实 CI 根因与恢复；最终获确认且实际交付的体验/成本/并发/归档/版本针/预算成果；明确依赖变化、breaking/removed 项和未解决限制。
- **checklist**：最终逐票清单与 commit 窗口、命令原输出、真实 FAIL/WARN/NOT_RUN 处置、candidate/released 两态、SoD 双审精确修订、remote/tag/CI SHA 对账；静态文件存在不等于验证通过。
- **rollback**：区分未打 tag、已打未推、已推三态；回滚产品与 adapter 注册/本机 pi settings 的实际备份路径；chrys 支持恢复步骤；`.governance` 权威账本/sidecar 与旧版本读兼容性；隔离测试中实跑并记录耗时，禁止覆盖用户数据或重指已发布 tag。
- **flags/声明边界**：既有 `GOVERNANCE_ENFORCEMENT=off` 与其他实际 flags 如实记录；pi browser/mcp 降级、协议/CLI 层执法与宿主拦截能力分别说清；不得凭本版支持平台变化宣称官方批准或 1.0 readiness。
- **发布后验证与观察**：至少定义一个本项目可验证的成功标准（例如同最终 SHA 的 CI 全绿及核心治理/adapter 冒烟无劣化），并按实际适用的观察窗口履行；若观察尚未完成必须保留未完义务，不提前记“无异常”。

## 7. 本报告边界自检

- 已覆盖所有 12 条 0.99.0 任务，保留暂停范围待澄清，未擅自删除、解锁或宣称完成。
- 只写本报告；未改 `.governance/`、两处暂停 WIP、CI、版本声明、tag 或远端。
- 未执行验证或生成发布三件套；所有历史通过/失败均给出来源，新的发布结论仍待执行与独立审查。
- 下一站：Coordinator 合并 FIX-452 实证及用户暂停范围回答→完成范围内载荷→正式规划/发布审查→M-0~M-8 收口。
