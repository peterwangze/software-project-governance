# FEAT-031 代码审查报告（Code Review R1 — 复审）

- **任务**：FEAT-031（0.81.0，P1；设计切片 **V8**）
- **Round**：**R1（复审）**；**前轮引用**：`REVIEW-FEAT-031-CODE-R0` = APPROVED_WITH_NOTES / `unresolved_blockers=0` + **发布条件 F-02/F-03**（`docs/reviews/review-FEAT-031-CODE-R0.md`，已完整重读并逐条比对 14 条）
- **审查对象**：工作树 11 M + 5 新（`git diff HEAD --numstat` 与 R0 **逐行一致** ⇒ 返工**全部落在 5 个 untracked 新文件**内）；HEAD 仍 `210b200`；`git stash list` 空
- **文件增长**：`checks/dsh_boundary.py` 1758→**1901** · `dsh_doctor.py` 1810→**1910** · `test_dsh_boundary.py` 1388→**1552**（**131 用例**）· `test_dsh_doctor.py` 977→**1128**（**86 用例**）· fixture 8986→**9348 B**
- **Reviewer**：Code Reviewer Agent（只读；全部探针 `%TEMP%` 副本 + 隔离 home；**仓库 763 tracked 文件 sha256 跑前/跑后零变化**）
- **结论**：**APPROVED_WITH_NOTES / `unresolved_blockers=0`**（P0=0；P1×1〔**非代码缺陷**：设计/DEC 收窄未落地〕；P2×3 新；P3×2 新 + 既有 5 条仍开放登记）

## 1. **F-02 / F-03 发布条件判定（关键）**

| 条件 | 判定 | 依据 |
|---|---|---|
| **F-02**（fixture 诚实性） | **是 ✅ 已闭环** | 审查方以隔离重定向（`DSH_HOME`/`HOME`/`USERPROFILE` 全指 `%TEMP%` + 契约声明的 `DSH_HARNESS_NODE_MODULES`）实跑 `record_evidence`，与提交 fixture **逐字段比对：10 字段中 9 个 IDENTICAL，唯一差异 = `captured_at`**（本就是时间戳）；`provenance` 与工具输出**逐字相同**；`notes` 与代码字面量**逐字相同**且**删除了原先虚假的隔离断言**（并附理由：不可声称工具无法自检的隔离）；`plane.source` 与 `plane.node_modules` **自洽**；**fixture 内无任何真实 home 路径**；跑后隔离 home **空目录**；反回归测试在位 |
| **F-03**（`evidence.*` 写入面） | **否 ❌ 未闭环 → Coordinator 已当场落地 ✅** | 条件 (i) 代码侧：**已达成并实测**（S3 remediation 改为 `…land the contract update in the same reviewed commit (the probe does not machine-mutate the contract)`；两条反回归测试断言旧承诺文本已消失）。条件 (ii) 设计/DEC：审查时**未落地**（设计 `:606`/`:705` 仍写「唯一契约证据写入路径」；`decision-log` 无收窄 DEC）⇒ 判定为否。**该缺口属 Coordinator 侧动作**，已落地：设计 §5.1/§5.5 口径收窄为「**证据采集 = 单点**」+ 新增 `evidence.*` 写入面约束段 + **`DEC-193`**（commit `6fa8940`） |

⇒ **发布判定**：审查方原话「**0.81.0 可以发布，前置 = 落地 F-03 的设计/DEC 收窄**」——**该前置已完成**，发布条件全部满足。

## 2. 逐条比对（R0 的 14 条）

| # | R0 | 状态 | 独立证据 |
|---|---|---|---|
| **F-01** K-7 第三条判据缺失 | P1 | **已修复** | `dsh_boundary.py:992-1145`：`_VERSION_LITERAL_RE` + **契约派生的接受集**（本包版本 / `evidence.dsh_cli_version` / oracle 版本；契约未记录即不接受）。实测：patch 注入 `0.1.5-rc.2` → `FAIL cordis.patch.yml:52`；lib 注入 `0.1.0-rc.6` → `FAIL lib/index.js:576`（**正是 R0 的变异**）；本树 0 命中 ⇒ `NOT_RUN` 而非 FAIL（**无误报**）。第三 clause 在 evidence 未记录时**仍判定**（正确）。残留 → R1-N1 |
| **F-02** fixture 诚实性 | P1 | **已修复 ✅** | 见 §1（发布条件满足） |
| **F-03** `--record-evidence` | P1 | **代码侧已修复 / 设计侧未落地** | 见 §1 |
| **F-04** K-2 扫描面窄 | P2 | **已修复** | `K2_CONSUMERS` 8→**11**（设计声明的 10 路径 + `verify_workflow.py`，后者在设计消费表/DEC-189 内 ⇒ **加严**）；shipped `0 literals (11 consumers scanned)`；向三个新文件副本注入包名字面量 → 均 FAIL 带 `file:line`（`:94`/`:48`/`:54`）；新测试断言 len==11 且含三名 |
| **F-05** `--allow-host-probe` 无效果 | P2 | 未修复（登记 FIX-326） | `--stage S5 --allow-host-probe` → `NOT_RUN`、**exit 0**；§5.1 exit-2 拒绝与 §5.2 授权后判据仍缺 |
| **F-06** `--out` 无守卫 | P2 | **已修复（强而不过强）** | **9/9 守卫矩阵**：契约本体 / `..` 绕行 / **任何既有非 factsheet**（包内外）/ 包内新非 factsheet → **REFUSED**；包内新 factsheet / **既有 factsheet（默认原地重录）** / 包外新文件 / **默认 target** → **ALLOWED** ⇒ 合法重录路径全部保留。**符号链接绕行未验证**（无创建权限，如实声明） |
| **F-07** `--stage` 归因误导 | P2 | **已修复（附 1 新歧义）** | `--stage S1` → S1 **PASS** + `prelude=[S0]`（含 `why`）；全量运行 `prelude=[]`；`--stage S0,S7` `prelude=[]`。残留 → R1-N4 |
| F-08 计数/叙述漂移 | P3 | 部分处置 | `EVD-1029` 现**同时**含旧值（126/24405/1731/1787）与正确值（133/24412/1758/1810）⇒ 追加更正而非改写；设计侧 `83→84` 未更正 |
| F-09 自述测试分类 | P3 | 未修复（自述性质） | 按名称重数：boundary 131 = 正例 38 / 反例 77 / 其他 16；doctor 86 |
| F-10 S2 docstring | P3 | 未修复 | `dsh_doctor.py:520` 仍称 offline 跑 28v（实现 offline 返回 None ⇒ S2=NOT_RUN） |
| F-11 `FX-BASEURL-01` slice 陈旧 | P3 | 未修复（FIX-326） | `dsh_fixtures.py` 未变 |
| F-12 manifest 未登记 `dsh-doctor` | P3 | 未修复（FIX-326） | `native_entry`/`validation` 均无；仅 `evidence` 散文提及 |
| F-13 K-12 第五字段判据过弱 | P3 | 未修复（FIX-326） | `dsh_boundary.py:1807` 仍为整文件字符串存在性 |
| F-14 行尾不一致 | P3 | **已消解** | 五文件现一致 CRLF ⇒ 事实不再成立；`.gitattributes` 会在 add 时归一化 |

## 3. 本轮新发现

| # | 级别 | 位置 | 事实（已实测） | 建议 |
|---|---|---|---|---|
| **R1-N1** | **P2** | `checks/dsh_boundary.py:1002` | **`v` 前缀版本字面量完全逃逸 K-7 第三 clause**：干净副本内 `# pinned at v0.1.5-rc.2` → K-7 **NOT_RUN（0 命中）**（`\b` 在 `v` 与 `0` 之间不成立 ⇒ 正则匹配不到）；裸写法正常 FAIL。**无测试、无注释声明该限制** | `v?\d+\.\d+\.\d+(?:-[A-Za-z0-9.]+)?` + 一条反例测试（一字符修复） |
| **R1-N2** | **P2（纪律）** | 治理记录 | **本轮重录命令无 R4 逐条上报行**（`EVD-1032+` 不存在；全库检索 `DSH_HARNESS_NODE_MODULES` 零命中）。历史违规已在 `EVD-1031` 补登；**本轮为第二例同类遗漏** | **Coordinator 已补登**（`EVD-1032`）；FIX-326 内加「重录 SOP 必带 R4 行」 |
| **R1-N3** | **P2（潜在，当前不可达）** | `dsh_doctor.py:668-693` | **S3 只修了一半**：以 patched `_residue_count` 实测同一事实两结果 —— **residue=0 → `FAIL`（版本越界）；residue=3 → `NOT_RUN`**（advisory 残留吞掉设计 §5.2 明写的「越界 → FAIL」）。**本机 `_residue_count()` 实测 = 14**（历史 28u/28v 遗留的 `spg-dsh-compat-*`）⇒ 一旦 evidence 记录 + `compat_range` 落地，该掩盖即为活缺陷 | 与已修分支同法：把 residue 披露**并入各分支 reason**（不再提前 return） |
| **R1-N4** | P3 | `dsh_doctor.py:1238-1256, 1280` | prelude 的 S0 verdict **不计入顶层 verdict/exit code** ⇒ 同一事实两结果（`--stage S1` 且 home 不可解析 → prelude S0 **FAIL** 而 `verdict=NOT_RUN`、**exit 0**；`--stage S0` 同环境 → FAIL/exit 1）；`prelude` 为**新增顶层键**（设计 §5.1 报告形状未记载） | 二选一并登记：计入 verdict，或加 `counted_in_verdict=false` + 同步设计 §5.1 |
| **R1-N5** | P3 | `dsh_doctor.py:1592-1594` | `record_evidence` docstring 仍称「refuses to write into the package **unless asked by absolute path**」，与实现不符（默认无 `--out` 即写包内 fixtures） | 按 `_guard_out_target` 三规则重写 |

## 4. 独立复现结论（⑥ 项 + 硬基线）

① **F-01 + 窄豁免**：**判定「窄豁免可接受」**——引用豁免（`§\s*$` / `^[.\d]`）是**语法排除**而非版本豁免，存在必要且最小（本树 `lib/index.js` 确含 `§2.5.1`，零豁免必误报；实测 `§2.5.1`/`2.5.1.3` 均不判负）；零豁免的替代方案需语义判断，**成本高于收益、不推荐**；四组件链豁免**有测试背书**且 dsh 版本恒三组件 ⇒ 可接受取舍；**`v` 前缀逃逸非设计意图 ⇒ 缺陷（R1-N1）**；「容忍契约已记录的版本」**自纠正**（重录后旧字面量即 FAIL，已实测）。
② **F-04 的 11 消费者**：与设计声明集合**一致且为超集**；0 误报、三处注入均带 `file:line` 检出。
③ **F-06 是否过强**：**不过强**——所有合法路径 ALLOWED，仅拒「非其所有之物」，与设计 §5.4「fixture 命名/位置是契约的一部分」一致；符号链接面**未实测**（如实标未验证）。
④ **F-07 prelude**：原误归因已消（S1 不再报 "no resolved DSH_HOME"），但引入 R1-N4 的 verdict/exit 不一致与未登记顶层键。
⑤ **S3 连带修正**：**对「未记录证据」支成立**（residue=14 时 reason 同时含两条披露 + remediation 在位 ✓），**对「越界 FAIL」支不成立**（R1-N3）。
⑥ **两个新套件在空隔离 home**：`131 OK` / `86 OK`，**跑后 home 仍空**；九套件全绿（registry 77 / compat 120 / contract 120 / adapter 50 / quickscan 82 / contract_matrix 27 / archguard 38）；**「依赖 ambient `DSH_HOME`」缺陷不复现**。

**硬基线（全部保持）**：三路径 `00e0d330f3560e10381b54b37a06fe6a626a451e3e70da8126b9c2bc47be3723`（S4 parity PASS）· 28u exit 0 + `real-home writes: 0` · 28v `18/23 + 5 NOT verified (NO_SCHEMA=5)` + exit 0 + `writes: 0` · 契约 SHA `96F92485…43FC6E` **未变** · Check 28w `PASS — 0 failing criterion`（**K-2 现报 11 consumers**；K-7 NOT_RUN）· ratchet `R1 24412≤24412 / R2 47≤47 / R4 1299≤1299 / R5 84/84 + 71/71 / R6 196 Δ0 / R7 regen deterministic + committed==fresh` · 763 tracked 文件 sha256 **零变化** · `check-governance` = 96 issues，**产品面关键词零命中**（唯一正则命中为 `RISK-036` 内假阳），差异全为治理记录类 ⇒ **零产品回归**。

## 5. 硬门槛复核

| 门槛 | 阈值 | 实测 | 判定 |
|---|---|---|---|
| P0 阻塞 | = 0 | **0** | PASS |
| 5 维度覆盖 | 100% | 逐项有结论 | PASS |
| 每条发现标级别 | 100% | **19/19**（14 比对 + 5 新） | PASS |
| 设计一致性 | 已完成 | F-01/F-04/F-06/F-07 已回设计面；**F-03 当时未闭合（现由 Coordinator 落地）** | 完成 |
| AI 专项 5 项 | 全部完成 | mock 0 / 硬编码 0（接受集**派生自契约**）/ **幻觉 API 0**（`dsh_contract.contract_path(root)` 签名匹配）/ TODO 0 / 过度实现 0（守卫强而不过强，已实证） | PASS |

## 6. 审查方自报的过程偏离（如实披露）

其**第一轮九套件运行漏写 `DSH_HOME` 重定向**，实际以 **ambient 真实 `DSH_HOME`** 运行（约 4 分钟、退出码全 0）。**影响核查**：`~/.dsh/.agent-presets/governance` 4 文件 mtime 仍为 **09:29:17**（早于本轮）、`~/.agent-presets` **不存在**、`~/.dsh` 近 25 分钟改动文件**全为 harness 自身运行时状态**（`settings.yaml`/`stats/*`/`sessions/*`/`storages/*`）⇒ **治理预设零写入**；随后以真隔离 home 重跑并取得报告引用的全部数据。

## 7. 结论与下一步

**APPROVED_WITH_NOTES / `unresolved_blockers=0`**；**发布条件 F-02 ✅ / F-03 ✅（Coordinator 已落地设计收窄 + `DEC-193`）** ⇒ **FEAT-031 可提交、0.81.0 可进入发布链**。

**剩余登记项（不阻断发布）**：R1-N1（一字符正则）/ R1-N3（分支顺序）建议并入 FIX-326 或发布前小修；R1-N4/R1-N5/F-10 为 P3 文档/语义面；F-05/F-11/F-12/F-13 已在 FIX-326。

## 8. 真实环境命令上报表（R4）

7 类命令全部只读或落 `%TEMP%`；九套件在 `%TEMP%` 隔离 home（跑后仍空，131/86/77/120/120/50/82/27/38 全 OK）；`check-dsh-boundary`/28u/28v/`archguard-ratchet`/`dsh-doctor`/`check-governance` 只读（内部报 `writes: 0`）；变异 harness 仅对副本；`record_evidence(out=%TEMP%)` **未用默认 target、未触碰仓库 fixture**；**763 tracked 文件 sha256 零变化**。**R1 依据**：除已披露的第一轮误用 ambient home 外，全部真实平面相关运行采用 **(a) 隔离环境**；**零真实 `~/.dsh`/`~/.agent-presets` 写**；零破坏性 git 命令。

---

*报告结束（R1，APPROVED_WITH_NOTES / unresolved_blockers=0；发布条件 F-02 ✅ / F-03 ✅）。*
