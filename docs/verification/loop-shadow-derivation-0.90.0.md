# FEAT-071 — E-1-A 结构锚定派生流水线（影子运行）验证留痕 + B→A 切换判据（0.90.0 批 2）

| 字段 | 值 |
|---|---|
| Task | FEAT-071（P2，0.90.0 批 2——DEC-255 载荷框架） |
| 执行依据 | `.governance/execution-packets.json` FEAT-071 包；DEC-254（A 后手+切换判据随附成文）；DEC-255（批 2=影子对照+八场景/C-10 复跑核验）；ADR-019 §2.2/§2.6；DEC-258（26 阻塞处置）；FEAT-070-R0 P2-1/P2-2/P3-4/P3-5 + FIX-398-R0 P2-1/P3-1/P3-2（同文件族小修面） |
| 执行主体 | Governance Developer Agent（真实仓库仅锁面修改；`.governance/` 治理记录零写——manifest 只读消费） |
| 执行日期 | 2026-09-27（机器时钟权威） |
| 隔离面 | 八场景/C-10 复跑：`%TEMP%\feat071\{repo-copy, wc5, wc6, wc6-120/240, wc6d-250~265, wc7, wc-cert}`；`$env:DSH_HOME=%TEMP%\feat071\home`（FIX-337 纪律：全程未对 `$HOME` 赋值） |
| 状态 | 执行完成——影子运行零副作用实证；28 行对照零分歧；切换判据成文（当前结论：**不可切换**，见 §5）；八场景/C-10 复跑零劣化；R0 小修面 7 项全落地 |

---

## 1. 勘察记录（实现前置，留痕）

### 1.1 影子入口形态（勘察决策）

| 勘察项 | 结论 |
|---|---|
| CLI 语法族 | loop_migration.py 为 **flag 族**（argparse 互斥 action flags：--dry-run/--apply/--rollback + FEAT-070 record 族），无子命令语法先例（与 FEAT-070 勘察记录一致） |
| 影子入口 | 新旗标 **`--shadow-derive`**（assumption_record 预授权形态）→ `derive_structural_units_shadow()`；与 record 族互斥（P2-1 校验覆盖） |
| 返回形态 | JSON-serializable dict（`mode: "shadow-derive"`），无墙钟字段——**输出确定**（两次运行字节一致，幂等可机检） |
| 退出码 | 完成=0；目标不可解析 fail-closed（RISK-040 C4）=1 |

### 1.2 三源结构证据可得性（真实仓实测）

| 源 | 机器记录面 | 实测 | 采集结果 |
|---|---|---|---|
| S1 change-triage | `.governance/change-triage/*.json` `task_id`+`files` 字段（机录） | 189 个记录文件，0 损坏；`skills/software-project-governance` 路径覆盖 8,770 行命中、`adapters/` 覆盖 8+ 文件 | **可用** |
| S2 agent-locks | `.governance/agent-locks.json` `active_tasks[].files`+`target_files`（机录） | active_tasks=FEAT-071 自身（5 文件） | **可用**（覆盖薄——仅活跃锁） |
| S3 任务行修改列 | plan-tracker 活跃事项表行内路径词元（含 `/` 的 repo 相对路径 + 消歧后唯一命中的裸文件名） | 34 行任务行扫描；命中例：FEAT-069 行 `test_evidence_binding_drift.py` → 唯一解析入 `skills/software-project-governance/infra/tests/` | **可用**（弱证据：仅部分行含路径词元） |

采集语义：路径存在性验证（`is_file/is_dir`）；裸文件名全树基名索引解析——**唯一命中才采信，多命中记 `ambiguous_basenames` 永不锚定，零命中记 `unresolved_tokens`**（§2.6 不猜测在采集层即生效）。

### 1.3 公开 API 面（FEAT-070-R0 P3-5 落地）

- 新公开名 **`loop_migration.load_approval_manifest(host_root)`**：docstring 声明消费契约（三态 `absent/corrupt/valid`；corrupt 永不部分消费；只读；唯一合法写入方仍是 record 族）。影子管线经此公开名消费 manifest——**零私有名 import**（测试 `test_public_api_matches_private_loader` 钉护与私有加载器行为恒等）。
- 统一存储声明核对：清单=确认侧权威、runtime=派生面、影子消费**同一结构同一存储**（banner 声明 + P3-4 NFC 边界注明已入 banner）。

### 1.4 结构宇宙（文件系统派生，非散文）

| unit_type | 结构规则 | 本仓实测 |
|---|---|---|
| adapter | `adapters/*` 目录 | 6（chrys/claude/codex/dsh/gemini/opencode） |
| skill | `skills/*` 含 SKILL.md 目录 | 26 |
| manifest | **无结构 unit 规则**——manifest-surface 文件仅盘点（9 个：1 skill-core + 2 plugin + 6 adapter-facet）；粒度裁决属人工（§2.6） | 0 个 manifest unit 生成 |

关键设计（DEC-258 预期兑现）：**结构宇宙与散文词元零交叉**——散文派生伪影（adapter.loading 等）在结构输入下**不进入锚定**（§3 对照表 C 类行一致消解）。

## 2. 影子流水线规格（`--shadow-derive`）

```
三源采集(S1/S2/S3) → 结构宇宙(adapters/skills 文件系统规则)
  → task→unit 候选生成(路径前缀映射：adapters/<n>/* → adapter.<n>；skills/<n>/* → skill.<n>；其余=cross-cutting 不锚定)
  → §2.6 唯一性校验(恰一候选=unique 可转自动；多候选=multi 升级确认链；零证据=none fail-closed)
  → 对照人工清单(经 load_approval_manifest 公开 API——join key=(unit_type, NFC+casefold name))
  → 差异归因(证据类型×唯一性结果×与人工决策一致性) + 切换判据输入(机检计数)
```

**影子零副作用硬约束**（测试钉护 `test_zero_side_effect_full_tree_snapshot`）：全仓 byte-snapshot 前后恒等；manifest SHA-256 不变；runtime/archive/evidence/临时文件零新增；无墙钟 → 幂等（两次运行 JSON 字节一致）。真实仓断言实测见 §8.1。

散文降级为显示层：legacy prose 派生（flow_unit_derive）仅报告计数与 id 清单（`prose_face_display_only`），不作为锚定输入；`test_prose_never_produces_candidates_display_layer_only` 钉护（散文富集 host：prose face 报 3 units，结构候选 **0**）。

## 3. 影子对照报告——本仓 28 unit 逐项（结构派生 vs 人工清单）

运行：`python skills/software-project-governance/infra/loop_migration.py --target <repo> --shadow-derive`（真实仓只读）。
清单面：`state=valid, revision=28, confirmed=2, blocked=26, issues=0`；`project_id` 恒等。

**汇总计数**：28 行 = 一致性归因 `consistent_no_evidence×2 + consistent_absence×26`；**DIVERGENCE=0；不可归因行=0**。管线裁决 `structural_match_no_evidence×2 + no_structural_unit×26`。

### 3.1 对照表（28 行——抽查友好：每行含结构对应物列与任务列）

| # | 清单 unit | 人工决策 | 结构对应物 | 管线裁决 | 唯一锚定任务 | 归因（agreement） |
|---|---|---|---|---|---|---|
| 1 | adapter.Chrys | **confirmed**（task=adapters/chrys） | adapters/chrys（名称归一：Chrys→chrys，NFC+casefold） | structural_match_no_evidence | —（无） | consistent_no_evidence：结构单元存在且人工确认成立；现行机器证据无法再推导该确认（历史任务早于 change-triage 机录面 0.77 工具），人工项保持权威，**不散文回退**（§2.6） |
| 2 | adapter.opencode | **confirmed**（task=adapters/opencode） | adapters/opencode | structural_match_no_evidence | —（无） | 同上（无需名称归一） |
| 3 | adapter.loading | blocked（散文伪影 A 组） | — | no_structural_unit | — | consistent_absence：纯结构输入下该 unit 不产生——散文词元永不进入锚定（DEC-258「此类项自然消失」机检兑现） |
| 4 | adapter.manifests | blocked（A 组） | — | no_structural_unit | — | consistent_absence（同上） |
| 5 | adapter.agent | blocked（B 组泛指/多候选） | — | no_structural_unit | — | consistent_absence：结构宇宙无名为 agent 的 adapter；人工多候选分析属散文层匹配，结构输入下零候选产生 |
| 6 | adapter.md | blocked（A 组） | — | no_structural_unit | — | consistent_absence |
| 7 | adapter.manifest | blocked（A 组） | — | no_structural_unit | — | consistent_absence |
| 8 | adapter.native | blocked（A 组） | — | no_structural_unit | — | consistent_absence |
| 9 | skill.FEAT-052 | blocked（A 组：task-id 伪影） | — | no_structural_unit | — | consistent_absence |
| 10 | skill.baseUrl | blocked（A 组） | — | no_structural_unit | — | consistent_absence |
| 11 | skill.Agent | blocked（B 组多候选） | — | no_structural_unit | — | consistent_absence（同 5） |
| 12 | skill.Same-Package | blocked（已撤回 hotfix——永不确认，DEC-258(3)） | — | no_structural_unit | — | consistent_absence：撤回引用物无结构对应物 |
| 13 | skill.fixture | blocked（A 组） | — | no_structural_unit | — | consistent_absence |
| 14 | skill.frontmatter | blocked（A 组） | — | no_structural_unit | — | consistent_absence |
| 15 | skill.review | blocked（B 组多候选：7 个 *-review skill） | — | no_structural_unit | — | consistent_absence：结构 skill 名为 code-review 等全名，裸词 review 非结构单元 |
| 16 | skill.entry | blocked（A 组） | — | no_structural_unit | — | consistent_absence |
| 17 | manifest.M-5b | blocked（A 组） | —（manifest 型无结构规则，9 文件仅盘点） | no_structural_unit | — | consistent_absence |
| 18 | manifest.only | blocked（A 组） | — | no_structural_unit | — | consistent_absence |
| 19 | manifest.M-5 | blocked（A 组） | — | no_structural_unit | — | consistent_absence |
| 20 | manifest.check | blocked（A 组） | — | no_structural_unit | — | consistent_absence |
| 21 | manifest.canonical | blocked（B 组多候选：3 manifest surface） | — | no_structural_unit | — | consistent_absence：表面家族存在但 unit 粒度不可结构判定（§2.6 转人工裁决） |
| 22 | manifest.artifact | blocked（A 组） | — | no_structural_unit | — | consistent_absence |
| 23 | manifest.Codex | blocked（B 组多候选） | — | no_structural_unit | — | consistent_absence |
| 24 | manifest.coverage | blocked（A 组） | — | no_structural_unit | — | consistent_absence |
| 25 | manifest.verify-workflow-split-phase1 | blocked（A 组：重构任务名伪影） | — | no_structural_unit | — | consistent_absence |
| 26 | manifest.CI | blocked（A 组） | — | no_structural_unit | — | consistent_absence |
| 27 | manifest.transition | blocked（A 组） | — | no_structural_unit | — | consistent_absence |
| 28 | manifest.adapter | blocked（B 组多候选：6 adapter-manifest） | — | no_structural_unit | — | consistent_absence：6 个 adapter-manifest.json 为父 adapter 的 facet（锚定父单元），非独立 manifest unit |

### 3.2 差异归因摘要

| 归因维度 | 计数 | 说明 |
|---|---|---|
| 与人工决策一致性 | 28/28 一致（0 分歧，0 不可归因） | 管线输出与人工清单**零矛盾**：2 确认项=结构存在但机器证据不可复现（人工项保持权威）；26 阻塞项=结构宇宙零产生（散文伪影/多候选/撤回物全部消解） |
| 证据类型 | confirmed 2 行=三源零覆盖（历史早于机录面）；blocked 26 行=三源零候选（输入不含散文词元的结构性必然） | 唯一性结果维度：无行进入 multi/unique 臂（join 键不存在） |
| 唯一性校验 | 0 行 auto-derivable；本仓无「结构可推导但人工阻塞」的对立行 | §2.6 纪律机器化验证：无猜测、无静默翻转 |

### 3.3 结构派生的附加产出（清单之外——B→A 判据的关键输入）

对 204 个有证据任务的候选生成（204 = S1 189 + S2 1 + S3 34 去重并集）：

| 唯一性裁决 | 计数 | 代表例 |
|---|---|---|
| **unique（可转自动候选）** | 156 | 153×`skill.software-project-governance`（change-triage 机录历史）；3×`adapter.dsh`（FEAT-010/037/038） |
| **multi（升级确认链）** | 8 | FEAT-015/029/030/031、FIX-283/309/316/317 → `adapter.dsh`+`skill.software-project-governance` 跨域双候选 |
| **none（fail-closed）** | 40 | AUDIT-153/155、FEAT-001/028/040/067 等（纯文档/分析任务——cross-cutting 不锚定） |

**结论性观察**：结构派生产出的是一个**与人工清单部分不相交的更大候选面**（32 结构单元中 30 个无人工决策）。这既是 E-1 的解（散文噪单元消失），也是切换的真实差距（§5）：现有人工清单只覆盖 prose 面的 28 个词元单元，结构面的 30 个单元尚未经人工确认链入账。

## 4. R0 遗留小修面逐项处置

| 项 | 内容 | 处置 | 看护 |
|---|---|---|---|
| FEAT-070-R0 P2-1 | CLI 旗标互斥缺失（record×record 静默走 approval；record×apply 静默丢 intent） | **已落地**：record 旗标互斥组 + 与 --apply/--rollback/--dry-run/--shadow-derive 互斥 + record 伴随旗标（--approve-task 等）无 record 旗标时拒绝；全部 `parser.error` exit 2 **先于任何文件触碰** | 6 个 CLI 互斥测试 + 既有 precedence 保持钉（apply+rollback 旧语义不回退） |
| FEAT-070-R0 P2-2 | manifest valid + plan 派生失败分支 status=consumed/ambiguity_count=0 误导 | **已落地**：该分支 status=**"indeterminate"** + ambiguity_count=**None**（「未测」≠「零」）；docstring 同步 | test_unit_face_indeterminate_on_plan_failure |
| FEAT-070-R0 P3-4 | NFC 归一边界未注明 | **已落地**：manifest section banner 增 DIGEST BOUNDARY NOTE（NFC 等价字节变体不触发 digest mismatch；威胁模型=意外变更检出，非对抗防篡改） | banner 文本（审查核对面） |
| FEAT-070-R0 P3-5 | 消费入口私有名 | **已落地**：公开 `load_approval_manifest` + 契约 docstring；影子管线即首个消费方 | test_public_api_* 两测 |
| FIX-398-R0 P2-1 | 孤儿清扫 4 安全臂无测试钉护 | **已落地**：manifest missing/corrupt 臂、evidence pre-state 失配臂、runtime.before 非空臂、rmtree 失败臂——4 测试全自包含 fixture | TestOrphanSweepSafetyArms |
| FIX-398-R0 P3-1 | backup= 引用保护测试名实不符（由 skip 满足） | **已落地**：重写为**真引用 fixture**（无 runtime host + 真实 MIGRATION 行 `backup=<name>` → sweep 实跑：引用保护生效；去引用对照臂→清扫生效） | test_migration_row_referenced_backup_kept（重写） |
| FIX-398-R0 P3-2 | .tmp 清扫臂复演空洞 | **已落地**：seed 真 .tmp 断言 `temp_files_removed`（heal 清扫臂）；.tmp 为目录的真 fs 失败臂（non-fatal 记录）；runtime unlink 失败臂（fail-closed guidance，三产物原位） | TestHealTempSweepArms 3 测 |

## 5. B→A 切换判据（DEC-254——成文交付）

> B=人工权威清单（FEAT-070 确认链）；A=结构锚定自动派生。切换=清单权威被结构派生取代的授权翻转（**后续授权票裁决——本票只成文判据，不翻转**）。

### 5.1 可机检判据（每条带命令/命令族）

| # | 判据 | 机检形态 | 当前值 |
|---|---|---|---|
| CJ-1 | 确认项可复现：清单 confirmed 全部被结构证据独立再现（对照表 `consistent_reproduction` 计数 = confirmed 数） | `--shadow-derive` → `switch_judgment_inputs.confirmed_units_reproduced_by_structure == manifest_face.confirmed_count` | **0/2** ❌（历史任务早于机录面，三源零覆盖） |
| CJ-2 | 唯一性纪律：恰一命中才锚定（unique/multi/none 三态钉护，multi 永不自动入账） | pytest：test_loop_structural_derivation（TestUniquenessAndProseDegradation 族） | ✅（33/33 绿） |
| CJ-3 | 差异逐项闭环：对照表零分歧、零不可归因行 | `comparison.agreement_counts` 无 DIVERGENCE / not_comparable；`rows_without_agreement_attribution==0` | ✅（28/28 归因） |
| CJ-4 | 清单-结构覆盖收敛：结构单元全部经人工确认链入账（无「结构有、清单无」悬置面） | `structural_units_without_human_decision == []` | ❌（30/32 悬置：30 个结构单元无人工决策） |
| CJ-5 | 代表性外部宿主（含缺失清单/跨域/漂移用例）影子通过 | 外部宿主 fixture 批（缺失 manifest=absent 臂/corrupt 臂/漂移 stale 臂已有单测骨架；**外部宿主实测未执行**——本票范围=本仓影子） | ❌（未执行——如实留痕） |
| CJ-6 | 回滚可用（链路级回退：清单回退/删除 + 迁移 --rollback 演练绿） | 八场景⑧ + 清单链路回退（apply/rollback 零清单触碰互证） | ✅（S⑧ 绿） |
| CJ-7 | 影子零副作用持续成立 | 零写断言测试 + 幂等测试 | ✅ |

### 5.2 人工复核点（不可机检部分）

1. **切换授权**：B→A 属权威翻转，必须独立授权票（DEC-255(3) 同源纪律——部分前置满足不构成授权）。
2. **名称归一裁决**：`adapter.Chrys`（人工显示态）vs `adapter.chrys`（结构规范名）的 join 归一（NFC+casefold）是否被权威接受为同一 unit 的规范书写。
3. **30 个悬置结构单元的处置**：逐个经确认链入账或明确排除（B 组多候选先例）。
4. **manifest 型 unit 的粒度定义**：结构上不可判定（9 surface 文件），需人工定义 unit 边界后才能结构化。
5. **外部宿主样本选择**：CJ-5 的「代表性」由人裁决。
6. **S⑦ 并发姿态**：并发写纪律继续依赖流程层 agent-locks（FEAT-070-R0 P3-7 口径），切换后同口径继承。

### 5.3 回退路径（若未来切换后回退）

- 清单链路级回退（DEC-258(5)：清单为 gitignored runtime-data 域——回退=链路级清单回退/删除，非 git revert）；
- 迁移面 `--rollback`（ADR §7 行 2；S⑧ 演练绿）；
- 实现面 `git revert` 单票（影子管线只读，无数据面回滚需求）。

### 5.4 当前成熟度评定（如实呈现——**结论：当前不可切换**）

- 机检判据 7 条中 **4 绿（CJ-2/3/6/7）3 红（CJ-1/CJ-4/CJ-5）**。
- 根本差距不是管线能力（唯一性纪律/对照/零副作用全部成立），而是**证据面与决策面尚未重合**：①历史确认项无机器证据可复现（不可证伪也不可证实——保持人工权威恰是 §2.6 的正确行为）；②结构派生揭示的 30 个真实结构单元尚无人工决策；③外部宿主验证未执行。
- **可执行路径**（供后续票参考，非本票承诺）：先以影子输出为工作底稿跑人工确认链补齐 30 单元（同时解决 CJ-4）→ 新任务自入账日起天然产生三源机录证据（CJ-1 对新决策自然成立）→ 外部宿主样本批（CJ-5）→ 授权票裁决。

## 6. 八场景/C-10 影子态复跑核验（隔离副本——批 2 附加面）

隔离面：`%TEMP%\feat071\*` 四副本（repo-copy/wc5/wc7/wc-cert + wc6 系击杀副本）；`DSH_HOME` 重定向 `%TEMP%\feat071\home`；**全程未对 `$HOME` 赋值**。影子派生在场（副本内含本票 loop_migration.py）。

| 场景 | 结果 | 关键实测 |
|---|---|---|
| ① dry-run | **PASS** | exit 0 / 612ms；`plan_hash=949bd7bf…655c2` 与 FEAT-068 实证**逐字节一致**（结构同一性不变量跨批保持）；validation_issues=0 |
| ② unit 划分核对（影子态） | **PASS（形态升级）** | `--shadow-derive` exit 0 / 374ms：28 行对照零分歧；**manifest SHA-256 前后不变**；runtime 零产生——FEAT-068 场景②的人工歧义发现面现由影子管线机检承载 |
| ③ apply | **PASS** | exit 0 / 263ms；28 units；恰 1 行 MIGRATION-0.65.0；plan-tracker 字节不变 |
| ④ 成功认证 | **PASS** | apply 后 check-governance 输出与 pristine 基线**逐行 IDENTICAL（diff=0）**；26 issues 全为迁移前既有契约面（REL-093 占位符等） |
| ⑤ 失败迭代 | **PASS（4/4 臂）** | ⑤a 错 hash exit 1 零写；⑤b 跨 target hash 绑定 exit 1（per-target 不变量保持）；⑤c wc5 自 hash apply exit 0（28 units）；⑤d 幂等拒绝 exit 1 |
| ⑥ 中断恢复 | **PASS（附新窗口类观察）** | 120ms 读/派生段：零半态；**240ms 实锤新窗口类=backup 写序列中途**（孤目录仅 0B plan-tracker.md）→ 孤儿不可验证 → 重入 applied=true 且孤儿**保留+披露**（E-5 P7 纪律真实生效）；250/320ms 完整态；**wc6d 微秒窗（runtime/行双 replace 间）本次活体未命中**——确定性覆盖由复演测试承载（`test_replay_wc6d_runtime_landed_self_heals` 绿）；各态重入全部收敛 |
| ⑦ 并发写入 | **PASS（附姿态观察）** | 本次三进程良性交错：3× exit 0、**恰 1 行 MIGRATION、runtime 单一、末写者收敛、零双提交零损坏**；串行重入幂等拒绝 exit 1。FEAT-068 的 PermissionError fail-closed 臂未复现（调度相关；写路径代码本批零触碰——影子管线只读）。并发纪律继续依赖流程层 agent-locks（P3-7 既有口径）——如实留痕 |
| ⑧ 回滚演练（N-3 门） | **PASS** | `rolled_back=true`（restored_from=正确备份）；runtime 移除；MIGRATION 0 行+恰 1 行 ROLLBACK-0.65.0；循环闭证：wc-cert 重新 apply exit 0（28 units）→ 再回滚 exit 0 |
| C-10（八分支看护+CLI 正反例） | **PASS** | wc5 迁移态副本：Check 3b `[PASS]` → runtime 单字节篡改 → `[FAIL] runtime_face_unreadable`（exit 1，fail-closed）→ 字节还原 → `[PASS]`（exit 0）；八分支 pytest 看护族（FEAT-069 交付）全绿 |

**复跑结论：影子派生在场时全链回归零劣化**（场景②形态由人工核对升级为机检对照；其余场景结果与 FEAT-068 基线等价或更强；两处姿态观察如实留痕，均为既有代码路径的环境性表现，非本票引入）。

## 7. 硬门槛自检

### 7.1 影子零副作用（真实仓断言）

| 断言 | 实测 |
|---|---|
| manifest SHA-256 前后不变 | `22A6A5D7…0397EC` 三次影子运行+两次 dry-run 前后恒等 ✓ |
| runtime 文件 | 前后均不存在（未产生）✓ |
| 全仓 snapshot | fixture 测试 `test_zero_side_effect_full_tree_snapshot` 全仓字节快照恒等 ✓ |
| 幂等 | 两次运行输出字节一致 ✓ |
| 计时 | shadow 343–400ms vs dry-run 500–612ms（同量级且更快；秒级门槛达成） |

### 7.2 回归门

| 门 | 结果 | 证据 |
|---|---|---|
| 新测试 | **PASS** | test_loop_structural_derivation.py 33/33（候选/唯一性/散文降级/零副作用/幂等/公开 API/P2-2/CLI 互斥/对照语义含 DIVERGENCE 臂） |
| 复演族 | **PASS** | test_migration_commit_window.py 23/23（16 原有 + 7 新增：P2-1 四臂+P3-1 重写+P3-2 三臂） |
| 相邻族 | **PASS** | test_loop_migration 28/28；test_loop_unit_manifest 25/25；test_evidence_binding_drift+test_flow_unit_derive+test_loop_migration_plan 92/92 |
| -k loop 族 | **PASS 547/547** | 唯一历史失败=`test_claim_command_emits_complete_pass_report` 的 **subprocess.TimeoutExpired**：其 26s 预算系 FIX-346 于 payload≈15.4MB 时代校准；payload 增至 25,258,238B（**+64%，跨批 0.87→0.90 累积，非单票引入**）→ 空闲实测 CLI 墙钟 24/25/24s（p50=24s，余量仅 8%），family 热态两次越界。**DEC-262 裁决后已按 FIX-346 同源纪律收口：26s→36s**（同会话 3 次实测 p50×1.5），注释载明溯源；收口后该测试单测 PASS（24.51s）+ **-k loop 547/547 全绿**（317.64s） |
| DEC-261 预算再校准 | **已执行（Coordinator 授权扩锁）** | checks/loop_runtime_claims.py `max_candidate_bytes` 24MiB→32MiB（33,554,432，与 max_semantic_payload_bytes 同族同值）；注释载明实测溯源（满载荷 25,258,238B@candidate_count 1054；HEAD 0d31ea2 余量仅 ~7.6KB；本票授权增量 +~105KB 逐项）；FIX-369 公式 ceil(×1.2)=30,309,886→32MiB；baseline-register 已登记（gate `check-loop-runtime-claims.candidate-bytes`，value=25,258,238，row_digest edf0ebfd…，registry `.governance/baselines.json`——Coordinator 明示授权的机器写入）；裁决后 claims 族 66/66 绿 |
| cross-refs | PASS | 无悬空/循环引用 |
| manifest consistency | PASS | 新文件经 manifest glob 权威覆盖，零 manifest 编辑 |
| check-governance（真实仓） | PASS | exit 0；26 issues=迁移前既有契约面（与副本 pristine 一致），零新增 |
| archguard R1~R6 | PASS（36/38） | R7 触发：`baseline-stale`——committed 基线（0d31ea2 regen）与本票结构增量（loop_migration.py +37,775B/新测试文件 43,693B/影子报告 24,116B/loop_runtime_claims.py DEC-261 注释块）不一致。**按纪律上报裁决，未自行 regen**（DEC-260 先例：sanctioned regen 分离提交，建议随本票 commit 后由 Coordinator 执行） |

### 7.3 无 AI 幻觉自查

全部结论有命令退出码/源码行锚/哈希对照支撑；测试零 mock 残留（唯一 mock=对称 start/stop 的故障注入臂）；负例（篡改→FAIL、错误 hash→拒、多候选→拒绝锚定）与正例双向实证；无 TODO 残留。

## 8. 边界声明

- 本票不翻转任何权威：清单 confirmed/blocked 决策零触碰（影子只读消费）；B→A 切换判据仅为成文交付，切换属后续授权票。
- 本仓 `.governance/` 治理记录零写（manifest/plan-tracker/evidence-log/decision-log/risk-log 均只读）；治理写回（evidence/decision/risk entries）由 Coordinator 执行。
- 八场景/C-10 全部发生于 `%TEMP%\feat071\*` 隔离副本；副本可直接丢弃即回滚；副本内 runtime 为验证治具产物，不含生产承诺。
- S⑥ wc6d 活体未命中与 S⑦ 良性交错两处观察为环境调度表现，已如实留痕；对应机制由确定性测试钉护。
- 本文档不修改 ADR-019 语义；§5 判据为 DEC-254 的操作化成文，语义缺口返回 Coordinator/用户（ADR-019 §9）。
