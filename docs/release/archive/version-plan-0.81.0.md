# Version Plan — 0.81.0

> **主题**：DSH 宿主兼容性体系化（依赖契约层 + 依赖最小化 + 严格校验看护 + 依赖边界可调测性）
> **状态**：M-1 候选打包完成（M-0 已裁决 DEC-190；实现切片 V1~V8 + V10 全部落地；M-2 门禁实测进行中）
> **规则依据**：`skills/software-project-governance/core/VERSIONING.md`（版本号分配规则 / 版本内容一致性规则 / 版本规划纪律）

## 0. 规划基线事实（治理记录核验，零编造）

| # | 事实 | 证据 |
|---|---|---|
| 1 | 项目当前版本 = **0.80.0**（已发布 2026-09-12 REL-076；本地 tag `v0.80.0` peel `71f73eb`，**未推送**） | plan-tracker `工作流版本` 行；`git tag --list "v0.8*"` |
| 2 | 本版为**计划外新增版本**（0.80.0 路线图行之后无 0.81.0 预留行）⇒ 按「版本号分配规则 3」确认未被预留后占用 | 本文件 §2 + plan-tracker 版本路线图 |
| 3 | 用户指令（2026-09-13）：dsh 升级适配后出现大量兼容性问题，要求**系统性分析、设计与实现**，并授权 Coordinator「按照推荐进行推进，直到当前的兼容性实现闭环并发布对应版本」 | 会话原始诉求；DEC-190 ⑨（M-4 授权范围） |
| 4 | 事实输入 = **AUDIT-153**（`docs/requirements/dsh-host-dependency-inventory-0.81.0.md`，801 行；依赖点 D-01~D-100 / 缺口 G-01~G-18 实测复现 / 约束 C-1~C-25 / 未验证项 R-01~R-19） | EVD-1009 |
| 5 | 设计交付 = **FEAT-028**：ADR-018（280 行）+ `docs/requirements/dsh-compat-design-0.81.0.md`（1023 行） | EVD-1010 |
| 6 | 设计审查链：R0 NEEDS_CHANGE（3 P1 / 5 P2 / 10 P3+NOTE）→ 修复 → **R1 APPROVED_WITH_NOTES / unresolved_blockers=0** | `REVIEW-FEAT-028-R0` / `REVIEW-FEAT-028-R1`；`docs/reviews/review-FEAT-028-DESIGN-R0.md` / `-R1.md` |
| 7 | 审查方独立核实的关键事实（不凭注释）：安装态 dsh = **0.1.5-rc.1**（注释引 rc.2 失真）；三路径渲染 sha256 全等 `00e0d330…3723`（**注**：该值系审查时点、即版本 bump **之前**（0.80.0 时点）的事实；0.81.0 **候选态**实测为 `6caf90fec1f2773eaa0128f0fa5c7a7795b512c8a36d603f5cd6e939ff48e55d`（16796 bytes），与 `00e0d330…3723` 的差异**仅 persona 版本行 1 处**——版本行变更的必然结果）；RISK-050 上游内部面耦合基本清零（`!!js` 0 / id-UPDATE 0 / 宿主平面注册 0） | AUDIT-153 §1/§2；R0 §5/§8 |
| 8 | 用户安装形态 = 源码仓 `link:`（profile 侧声明）；`package.json` 无 `dsh.profile`（真实声明在 `~/.dsh/profiles/web/package.json`） | 用户 2026-09-13 答问；AUDIT-153 D-02 |
| 9 | push 凭据本会话**可用**（`git ls-remote --tags github-https` 成功、`git push --dry-run` 成功）⇒ 0.79.0/0.80.0 两个 tag 与 118 commits 的**补推义务可在本版一并履行** | 本会话命令输出 |

## 1. Release Scope（范围特征与任务化结构）

**一句话**：把 dsh 兼容性从「散落 6 个消费方的硬编码事实 + 事后发现」转为「**单一机器可读契约 + 零校验不得 PASS 的机检不变量 + 单一分阶段诊断入口 + 升级演练**」，并同时收口 0.80.0 遗留的四个兼容性缺口任务。

| 切片（设计 §6.1） | 任务 | 目标 | 关键交付物 |
|---|---|---|---|
| **V1** | FEAT-029 | 契约数据层 | `adapters/dsh/host-contract.json` + `infra/dsh_contract.py`（4 API + 3 异常类）+ `test_dsh_contract.py` + `dsh_fixtures.py`（`--emit-fixture`）+ manifest 声明 |
| **V2** | FEAT-030 | 消费方改读契约（行为保持）+ **K-2 静态扫描提前** | `launch.py` / `dsh_compat.py` / `lib/index.js` 三消费方收敛；per-field 突变矩阵 |
| **V3** | **FIX-315** | 零校验不得 PASS（G-01） | `dsh_compat.py` 裁决 + `coverage` + 上屏判据；`rows_checked==0 → NOT_RUN`（L1/L2/L3 三层不变量） |
| **V4** | **FIX-311** | group 语义与 loader 对齐（G-02/G-03）+ 分类自检（G-18） | `PROBE_SCRIPT` walk 修复；`:754` 负相改写为归因+披露断言 |
| **V5** | **FIX-316 / FIX-313(a)** | 渲染与解码面守卫（G-05/G-07/G-10/D-66/D-49/D-50/D-54/D-56） | `launch.py` `<=` 边界、`leftovers` 未知 token 扫描、非 UTF-8 解码、孤立 CR 统一、死代码消除 |
| **V6** | **FIX-316** | `DSH_HOME` 三方收敛（G-06） | 写入侧三实现一致（`lib/index.js` / `launch.py` / doctor 记录路径）；探测侧 fail-closed 保持 |
| **V7** | **FIX-316** | 版本与证据看护（G-11/G-12/C-20） | 消除失真版本字面量；`adapter-manifest.json` 指向契约；TTL 过期 FAIL |
| **V8** | FEAT-031 | 契约边界门禁 + 单一诊断入口 + 升级演练 | `checks/dsh_boundary.py`（Check 28w，K-1~K-13）+ `dsh_doctor.py`（S0~S7 + 退出码 0/1/2 + `--offline`/`--selftest`/`--record-evidence`/`--rehearse`）+ `adapters/dsh/fixtures/host-facts-<v>.json`；registry/quickscan/verify 接线 + 两次 `--regen` |
| **V10** | **FIX-313(b)** | 安全面：`lib/index.js` catch 清理退化（G-04，潜在误删 CWD 同名目录） | 显式 staging 变量替代 `dirname(outcome.dir \\|\\| '.')` + 反相 fixture |
| **V9** | **REL-077** | 发布面收尾 | CHANGELOG / release 三件套 / `core/releases/0.81.0.json` / 版本投影核对 |

**需求覆盖**：REQ-146（最小化，V1+V2+设计 §3 逐条裁决）/ REQ-147（契约单点，V1+V2）/ REQ-148（严格校验看护，V3~V7+V8）/ REQ-149（可调测性，V8）——四条全覆盖，无缺项（DEC-190 备选 C 否决理由）。

## 2. Version and SemVer（MINOR 论证）

**结论：0.81.0 = MINOR（功能/能力面新增，无破坏性变更）。**

- **MINOR 理由**：新增产品能力面（契约文件 + 访问器 + 新 Check 28w + 新命令 `dsh-doctor` + 新 fixture 目录）；对既有用户可见行为**保持**（V2 的验收基线即「三路径渲染 sha256 不变 + 89 tests OK + 28u/28v PASSED」）。
- **非 MAJOR**：不引入破坏性行为变更；DEC-187 I-1/I-2/I-3 零侵入不变量不变；`cordis.patch.yml` 形态不变。
- **非 PATCH**：范围包含新增能力与新增门禁（非纯 bug 修复），按 VERSIONING「版本号分配规则 2」不得占用 PATCH。
- **版本号未被预留核查**：plan-tracker 版本路线图中 **0.81.0 无预留行**（0.80.0 行之后直接接 V-Gate 与里程碑），符合「版本号分配规则 3」；本文件即为事后/规划期登记。
- **Breaking Change 文档化**：本版**无 breaking change**；若实现期出现，MUST 回写本节 + VERSIONING.md + CHANGELOG + 迁移指南（V-Gate 门禁项）。

## 3. 里程碑链 M-0~M-8（对齐 0.79.0/0.80.0 先例）

| 里程碑 | 内容 | 状态 |
|---|---|---|
| **M-0** 范围裁决 | 版本范围（O-1/O-2）+ O-3~O-9 处置 + 真机验收路径 | ✅ 完成 2026-09-13（DEC-190） |
| **M-1** 候选打包 | 实现切片全部落地 + 候选 commit | ✅ 完成 2026-09-13（V1~V8 + V10 全部落地，实现窗末提交 `3074120`（`d87ead8..3074120` 的 tip）；候选打包提交见 M-2 期 ledger 派生） |
| **M-2** 门禁实测 | release 三件套 + 版本投影 + 全套 check（见 §4） | ✅ **实测完成 2026-09-13**（Coordinator 独立实测，见 EVD-1034；14 项逐条结论回填于 `docs/release/release-checklist-0.81.0.md` 的 M-2 表；唯一保留的前置依赖 = `release-ledger` 的 `candidate_commit` 派生要求 candidate manifest 随候选打包提交入库，已显式声明） |
| **M-3** 独立审查 | Design Reviewer（设计侧已 R1 通过）+ Code Reviewer（产品代码）+ Release Reviewer（发布侧） | 🔄 **进行中**：设计半面 R1 通过；产品代码半面 **REVIEW-REL-077-CODE-R0 = NEEDS_CHANGE/1 → 修复 → R1 = APPROVED_WITH_NOTES / unresolved_blockers=0**（通过终态；`docs/reviews/review-REL-077-CODE-R1.md`）；**发布侧 Release Reviewer 待执行** |
| **M-4** 用户授权 | transition + tag + push（**用户 2026-09-13 已预授权**，DEC-190 ⑨） | ⏳ 待执行 |
| **M-5** transition + tag | manifest-only `candidate_to_released` + annotated tag `v0.81.0` | ⏳ 待执行 |
| **M-6** released 态门禁 | `release-ledger --no-remote` = NATIVE_RELEASED PASS + 静态门禁 | ⏳ 待执行 |
| **M-7** 推送 | `git push github-https master v0.81.0` **+ 补推义务** `v0.79.0` `v0.80.0` | ⏳ 待执行 |
| **M-8** 收尾 | CHANGELOG 回填 + session-snapshot + 治理数据归档检测 | ⏳ 待执行 |

### 3.1 回滚边界（显式声明）

- 代码回滚：本版改动集中在 `adapters/dsh/`、`lib/index.js`、`skills/.../infra/{dsh_compat.py,dsh_contract.py,dsh_doctor.py,checks/dsh_boundary.py,registry.py,verify_workflow.py,quickscan_registry.py}`、`core/manifest.json`、`core/architecture-baseline.json`、`contract_matrix/snapshots.json`；**回滚 = revert 到 `v0.80.0`**，无数据迁移、无宿主侧写入、无用户侧配置变更（预设载荷与用户根语义不变）。
- `core/architecture-baseline.json` 与 `contract_matrix/snapshots.json` 为 `--regen` 生成物：回滚时随代码一并 revert。
- **不引入**：无数据库/无外部服务/无安装期脚本/无 `postinstall`。
- 已发布的临时/中间态：无（本版开发期不产生对外可见中间版本）。

## 4. 发布门禁清单（M-2 MUST 逐项实测）

| # | 门禁 | 命令/判据 | 状态 |
|---|---|---|---|
| 1 | 版本一致性 | `check-version-consistency` PASSED（含 4 plugin.json） | ⏳ |
| 2 | 投影同步 | `check-projection-sync --fail-on-issues` PASSED | ⏳ |
| 3 | 注入契约 | `check-injection-contract` PASSED | ⏳ |
| 4 | 结构清单 | `check-manifest-consistency --fail-on-issues` PASSED | ⏳ |
| 5 | 清理面 | `cleanup.py --dry-run` 零删除 | ⏳ |
| 6 | 棘轮 | `archguard-ratchet`（R1~R7）committed==fresh 且 0 violations | ⏳ |
| 7 | 契约边界 | `check-dsh-boundary --fail-on-issues` PASSED（K-1~K-13） | ⏳（V8 交付） |
| 8 | 冻结面 | `test_registry.py` 全绿（**82→84** / **70→71** / `migrated` +`dsh-doctor`） | V8 一次新增 **2 个 CLI 键**（`check-dsh-boundary` + `dsh-doctor`）与 **1 个检查段**（28w）；`test_registry.py` 的 `FROZEN_CLI_KEYS = 84` / `FROZEN_SEGMENTS = 71` （REVIEW-REL-077-CODE-R1 **F-R1-05** 更正，原稿 82→83 少计 `check-dsh-boundary`） |
| 9 | 预设隔离冒烟 | `check-dsh-preset-smoke`（28u）退出码与文本不变 + `real-home writes: 0` | ⏳ |
| 10 | 预设 schema 兼容 | `check-dsh-preset-compat`（28v）PASSED（`rows_enabled 23`/`rows_checked 18` 口径 + NO_SCHEMA 行为改变后口径同步） | ⏳ |
| 11 | 全量测试 | 冻结树全量 `unittest` 基线对比（新增失败必须逐条归因） | ⏳ |
| 12 | 发布文档 | release 三件套 + CHANGELOG + `core/releases/0.81.0.json` | ⏳ |
| 13 | 回滚方案 | `docs/release/rollback-plan-0.81.0.md` 存在且内部一致 | ⏳ |
| 14 | 真机验收面 | 隔离环境项 + **真机三项（用户手动执行，见 §9）** | ⏳ |

## 5. 入出槽裁决表（DEC-190）

| 项 | 裁决 | 依据 |
|---|---|---|
| V1~V8 + V10 | **入槽 0.81.0** | DEC-190 ①（用户选定「全量」） |
| V9 | 由 REL-077 承载 | DEC-190 ① |
| O-3 `peerDependencies` | **不入**：以 `evidence.compat_range` 版本闸门替代 | DEC-190 ②（U-1 未验证 + C-1 风险面） |
| O-4 契约放置 | `adapters/dsh/` | DEC-190 ③ |
| O-5 层归属迁移 | **本版不迁移**，三者登记为同一待裁决集合 | DEC-190 ③ |
| O-6 `strong` 反相门槛 | 1 个 fixture | DEC-190 ④ |
| O-7 S5 授权探测 | 默认关闭（M7.7 三选一前置，无豁免） | DEC-190 ⑤ |
| O-8 R1 豁免到期 | **顺延 0.82.0**（额度为 0、不赋增长许可；本版 `--regen` 时写新 `expire_version`） | DEC-190 ⑥ |
| O-9 allowlist budget | 初值 3（K-11 棘轮只降不升） | DEC-190 ⑦ |
| R1 非阻塞项 N-1/N-4/N-5/N-7 | **已闭合**（设计 1009→1023 行） | EVD-1010 |
| R1 非阻塞项 N-2/N-3/N-6 | **V8 落地前义务**（已注入 V8 派发规格） | `docs/reviews/review-FEAT-028-DESIGN-R1.md` §4 + 设计 §11.1 |

**出槽（本版明确不做）**：
- **FIX-312**（归档引擎决策归属假阳，P2）——与本主题无关，维持未规划版本。
- **FIX-314**（`review_record` 键 `(task,round,reviewer)`，P2）——维持未规划版本。
- 0.80.0 遗留的**真机三项验收未验证**面（设置页标签/删除/打开目录、非治理会话无治理技能、治理会话技能完整性）——见 §9，本版以**用户手动执行 + 回贴**方式尝试闭合，未闭合则如实标注未验证。
- RISK-039（架构腐化看护）、RISK-036（官方收录）等与 dsh 兼容性无关的风险——本版不改变其状态。

## 6. RISK-050 挂载（DSH 上游内部面耦合）

| 项 | 内容 |
|---|---|
| 当前状态 | **打开**（截止 2026-10-31），缓解中 |
| 本版处置 | ① 依赖面**首次全量枚举**（AUDIT-153 D-01~D-100）+ 必要性逐条裁决（§3 三类归并）；② 必要依赖**契约化**（V1/V2）使「未枚举但被消费」的隐式依赖成为可机检 FAIL（K-2/K-3）；③ 护栏可信面修正（V3，G-01）使零校验不再产生假绿；④ 单点诊断入口（V8）把「升级后出事定位成本」从多步手工降为一条命令分阶段输出 |
| 本版**不**声明 | 不声明 RISK-050 关闭；上游内部面（行 id / config 键 / 加载语义）的漂移风险**只能被前移发现，不能被消除**——这是风险残留，MUST 在 release 文档如实披露 |
| 关闭条件（不变） | 真实环境验收 + 至少一次真实 dsh 升级演练通过（`--rehearse` 机制 + 用户真机） |

## 7. 风险披露（本版引入）

| # | 风险 | 缓解 | 残留 |
|---|---|---|---|
| R-1 | 契约层成为新单点故障（BT-1） | 无回退副本（J-4）+ 失败面前移（K-1/K-10 + V2 突变测试）+ 任一候选必跑 28u | 契约坏 + CI 未跑 ⇒ 预设静默不交付（表现为"预设消失"，非宿主崩溃） |
| R-2 | 诊断入口自身失败（BT-2） | 阶段级独立 try/except（崩阶段 → NOT_RUN，其余照常）+ 禁止 import `verify_workflow` + `--offline`/`--selftest` | doctor 不可用 ⇒ 退回 `--smoke` 与 28v 两个既有入口 |
| R-3 | JS/Python 双消费者解释分歧（BT-3） | 字段单一含义 + 三路径 sha256 parity 硬门禁 + V2 per-field 突变矩阵 | 语义层分歧仍需 Code Review 兜底 |
| R-9 | 半迁移期无守卫 + allowlist 自我豁免（BT-R-01） | K-2 **提前到 V2**；K-11 allowlist 棘轮（`reason`/`since_slice`） | allowlist budget 锚点（N-2）= V8 前义务 |
| R-10 | 同一事实两个 verdict（BT-R-02） | K-12（doctor ↔ boundary 裁决一致）+ `coverage` 单生成点 | K-12 与 `--offline` 适用域（N-3）= V8 前义务 |
| R-11 | fixture 与真实升级的时间差（BT-R-03） | K-13（同版本 no-op FAIL / `captured_at` 严格递增 / baseline TTL / `synthetic` 标记） | baseline TTL 后果定型（N-6c）= V8 前义务 |
| R-12 | 「行为保持」只证输出等价（BT-R-04） | K-2 + per-field 突变矩阵 + 不可观测字段分流 K-2/K-10 | 突变矩阵进程隔离写法（N-6a）= V8 前义务 |

## 8. No-overclaim 边界

- 本版**不声明**：RISK-050 关闭；dsh 上游兼容性"永久解决"；真机三项验收通过（除非用户手动执行并回贴证据）；`peerDependencies` 已声明；运行时自愈能力（N-9 明示不做）。
- 本版**声明**（须有实测证据支撑）：契约文件存在且被消费（K-2/K-3）；零校验路径不再产生 PASS（L1/L2/L3）；单点诊断入口存在且分阶段输出；依赖面相对基线**收窄**（`elimination.*` 可机器复查）。
- 措辞纪律：涉及真实环境一律使用「**隔离环境安装冒烟（环境变量重定向至临时目录）通过**」；无限定语的「真实安装/真实环境通过」= 违规措辞。

## 9. 待验证项与观察项（显式标注——无事实源支撑的内容禁止假设成事实）

| # | 项 | 状态 | 计划 |
|---|---|---|---|
| U-1 | `peerDependencies` 在 pnpm profile 平面不引入实质安装边 | 未验证 | 隔离 `DSH_HOME` 的一次性 profile 上 `dsh plugin add` 前后 diff（需用户授权） |
| U-2 | 「无 `Config` ⇒ loader 原样透传」 | 不作断言（G01-e 已解除该断言） | 只读 `cordis-plugin-loader` `resolveConfig` 调用点 |
| U-3 | `npm pack --dry-run --json` 零写入 | 未验证 | 临时目录执行 + 写入面比对 |
| U-4 | `$DSH_HOME/.agent-presets/` 是 `resolvedRoots` 第一个 | 未验证（**不作判据**） | 只读上游源码 |
| U-5 | `{{model}}`/`{{cwd}}` 由宿主插值 | 未验证 | live 会话核验（用户侧） |
| U-6~U-9 | 契约迁移成本 ≤3 处 / group 非 `cordis:group` 行为 / `--dump-config` 输出形状 / `host-facts` 字段集完备性 | 未验证 | 分别由 Code Reviewer 核消费点清单、隔离组合探针、用户授权后执行、V8 首次记录 + 4 合成突变校准 |
| **真机三项** | 设置页「自定义」标签 + 删除 + 打开目录；非治理预设会话不含治理技能；治理预设会话技能完整性 | **未验证**（0.80.0 遗留，本版尝试闭合） | 由 Coordinator 提供只读命令 → 用户手动执行 → 回贴输出 → Coordinator 机录 EVD 行（DEC-190 ⑧） |
| **补推义务** | `v0.79.0` / `v0.80.0` tag 与 118 commits 未推送 | 待履行 | M-7 随本版一并推送（凭据本会话实测可用） |

---

*本文件为 0.81.0 规划产物，随 M-0 裁决（DEC-190）产出；M-1~M-8 执行中持续更新。*

---

## M-2 前置门禁实测（Coordinator，2026-09-13 预检）

在实现切片尚未全部落地时先做**只读预检**，用于在 M-2 前提前发现返工点（结果可复现，命令见下）：

| 门禁 | 命令 | 实测（2026-09-13，HEAD 1c2dc0a） |
|---|---|---|
| 版本一致性 | check-version-consistency | **PASSED**——13 个版本声明文件 + 2 个 bootstrap 标记一致（真值源 SKILL.md） |
| 投影同步 | check-projection-sync --fail-on-issues | **PASSED**——15 个镜像文件与版本声明同步 |
| 注入契约 | check-injection-contract --fail-on-issues | **PASSED**——3 文件 / 23 锚点齐全 |

**意义**：发布链上「版本一致性 / 投影同步 / 注入契约」三项在**版本 bump 之前**即已绿，故 0.81.0 的 M-2 剩余待验门禁收敛为：结构清单（check-manifest-consistency）、清理面（cleanup.py --dry-run）、棘轮（**两次 --regen 后**的 rchguard-ratchet）、**Check 28w（V8 交付）**、28u + 28v、全量测试基线、回滚方案。
**注意**：版本 bump（0.80.0 → 0.81.0）后本三项 **MUST 重跑**——上表证明的是「未 bump 前的健康度」，不是 bump 后的终态。
