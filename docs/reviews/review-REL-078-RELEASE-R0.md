结论：NEEDS_CHANGE ｜ round=0 ｜ unresolved_blockers=1 ｜ 机录 round 建议 = REVIEW-REL-078-R2

# Review — REVIEW-REL-078-RELEASE-R0（0.82.0 发布候选 · M-3 发布半面独立审查）

## 结论：**NEEDS_CHANGE**

- **round**：R0（REL-078 发布半面首轮，无前轮；机录轮次谱系按 Coordinator 指令 = 全局续 REL-077 的 R6 终态——REVIEW-REL-077-R2/R3/R5 为其 NEEDS_CHANGE 轮、R4/R6 为通过终态，R6 = `APPROVED_WITH_NOTES/unresolved_blockers=0`）
- **blocking**：**F-01（P1）×1** ⇒ 候选载荷完整性缺口：`commands/governance-init.md` 的 bootstrap 模板标记面（3 处 `@bootstrap-version: 0.81.0`）未被 0.82.0 bump 投影覆盖——0.79.0/0.80.0/0.81.0 **连续三代候选打包均同步该面**（`a89341e` 实改三行 0.80.0→0.81.0 逐 hunk 实证），且同批已 bump `adapters/dsh/AGENTS.md.template` 与 agent-presets persona 行，唯独漏掉 canonical 注入模板的同一标记面；Gate 1/2 的检查 face 集实测均**不含**该文件 ⇒ 引擎门禁绿灯下的检查盲区
- **必修项**：3 项（F-01、F-02、F-03）+ 4 项 P3 随批顺手项（F-04~F-07）——见 §7 与 §10
- **审查边界（事实依据红线）**：全程只读审查（git 只读、无 add/commit/restore/reset/worktree）；可执行复现全部在隔离 `DSH_HOME`（`$tmpHome` = %TEMP% 随机目录，用后即删）下进行；依赖 M-2 执行的门禁数值（28u/28v/28w、archguard、check-release、850 OK exit 0 运行面）均为文档级事实，未复现，已逐条标注（§8）
- 返回 Coordinator 的结论与本首行**同一**：`NEEDS_CHANGE`（不做最终发布决策——M-4 用户停点）

---

## 0. 审查对象（基线 HEAD `845c050` + 已暂存未提交候选增量，25 文件 = 21 M + 4 A）

| 产物 | 路径 | 我的复核方式 |
|---|---|---|
| 发布检查清单 | `docs/release/release-checklist-0.82.0.md`（146 行） | Gate 表逐项裁决 + 占位全量扫描归类 + M-0 预检值独立复现 |
| 回滚方案 | `docs/release/rollback-plan-0.82.0.md`（113 行） | 区间端点/拓扑实测 + 勘误注记裁决 + 步骤可执行性 |
| Feature Flags | `docs/release/feature-flags-0.82.0.md`（73 行） | 逐节 + 豁免账本三锚代码面比对 |
| CHANGELOG [0.82.0] | `project/CHANGELOG.md:5-38` | B-1~B-8 覆盖度 + Breaking 显式结论 + 三段如实披露 |
| candidate manifest | `skills/software-project-governance/core/releases/0.82.0.json` | canonical 字节五检 + schema 对照 0.81.0 + `release-ledger` 双版本实跑 |
| 授权链 | DEC-195（范围）/ DEC-196（FIX-313 方向更正）/ DEC-197（标准链，M-4 停点无预授权） | `decision-log.md:133/135/136` 逐条比对交付 |
| 审查证据链 | 本会话 21 任务机录（REVIEW-* 行）+ FIX-324/326 补审 | `evidence-log.md:2090-2173` 逐行核对终态 |
| Change Inventory | `e376ddf..845c050` 14 commits | `git rev-list`/`git log` 全表逐 hash 比对 |

---

## 1. 维度一：发布检查清单（逐项裁决）

### 1.1 Gate 表 16 行逐条裁决

| # | 文档结论 | 我的独立复核 | 裁决 |
|---|---|---|---|
| 1 | `check-version-consistency` ⟦M-2 回填⟧ + 预期过渡态披露 | **实跑复现**（隔离 DSH_HOME）：`PASSED`，13 文件（SKILL/manifest/marketplace/4 plugin.json/CHANGELOG/plan-tracker/4 hooks）+ AGENTS/CLAUDE bootstrap 标记全 0.82.0；唯一 WARN = plan-tracker 0.81.0（gitignored，M-8 转——与 0.81.0 先例同型，披露**准确**） | **预检转 PASS 成立**（M-2 复跑义务不变） |
| 2 | `check-projection-sync --fail-on-issues` ⟦M-2 回填⟧ | **实跑复现**：`PASSED — 15 mirrors` | **成立** |
| 3 | `check-injection-contract` ⟦M-2 回填⟧ | 未执行（本轮边界） | 未复现（文档级） |
| 4 | `check-manifest-consistency` **M-0 预检 PASS** | **实跑复现**：`[PASS] Manifest and filesystem are consistent.`（717 canonical / 802 actual） | **PASS（预检值复现）** |
| 5 | `cleanup.py --dry-run` 零删除（exit=1 正常终止码） | 未执行；判据与 0.81.0 R0 已证代码常量（`ERR_NOTHING_TO_CLEAN = 1`）一致 | 未复现（文档级） |
| 6 | `archguard-ratchet` 锚 24453 恒等预期，⟦M-2 回填⟧ | 声明为「预期」而非实测；`--regen` 义务按「bump 未触引擎行」豁免（M-0 批 `verify_workflow.py` 零变更——`git diff --cached` 无该文件，成立） | 预期声明合规（M-2 判定） |
| 7 | Check 28w **M-0 预检 PASS**（K-1~K-13） | 未执行；K-12 与 FIX-326① manifest 登记的耦合由 `review-FIX-324-326-CODE-R0.md` §硬门槛表独立复现在案（`Result: PASS, 0 failing`） | 补审报告背书（文档级） |
| 8 | 28u ⟦M-2 回填⟧（隔离 + 并发抖动复跑纪律延续） | 未执行 | 未复现（文档级） |
| 9 | 28v ⟦M-2 回填⟧（5 行 NO_SCHEMA 按 `[NOT_RUN]` 披露） | 未执行 | 未复现（文档级） |
| 9b | `check-agent-adapters` **M-0 预检 PASS** | 未执行；同批 `test_dsh_adapter 53 passed` 由补审报告独立复现在案 | 补审报告背书（文档级） |
| 10 | 全量基线零回归 + **3200 口径注记（B-7）** + 安静窗 850 复跑项 | **discover 计数独立复现**：候选树 `FULL_DISCOVER_COUNT = 3200`、`test_verify_workflow = 850`——与 M-0 声明**同值**；3193→3200 的 +7 差额归因（`21121c5`/`845c050` 新增用例 + live replay 族漂移）机制自洽且「M-2 以当场值为准」兜底；0.81.0 三条已收口红基线（FIX-320 族/日期炸弹/15s 超时）逐条列名并声明「若现即真回归」 | **PASS（口径注记与计数复现成立）** |
| 11 | 三路径渲染 parity ⟦M-2 回填⟧（预期 = `6caf90fe…e55d` 的版本行更新形态，不预填） | 未执行渲染；「窗口渲染语义零变更」由实测支撑（`lib/index.js` 仅注释 + `adapters/dsh/` 窗口 diff 空 + persona 行随 bump 的唯一版本字面量，三时点比对） | 结构支撑复现（字节值 M-2 实测） |
| 12 | 契约 SHA **M-0 预检值** `63B28311…28DF2`（75331 B） | **逐位复现**：staged 工作树 `Get-FileHash` = `63B28311330DCDED6192CC3350C81735F8557E0D6115D570ABCA328853228DF2` / 75331 bytes；HEAD 基线 blob = `96F92485…43FC6E` / 74702 bytes——「0.81.0 基线不再适用」的触碰披露**准确**（FIX-326③ 三处 note） | **PASS（双态逐位）** |
| 13 | `check-release`/`release-ledger` ⟦M-2 回填⟧（后台作业纪律 + 候选态 lineage 不得代替发布完成态） | `release-ledger --version 0.82.0 --no-remote` 实跑 = `FAIL` 恰 1 issue（`candidate_commit: found 0`——manifest 未入库派生不可用）＝ **EVD-1034 gate 13 先例同型「预期前置依赖」**（0.81.0 同期同判）；`trust_level=NATIVE_CANDIDATE`、`lifecycle=candidate`、`events=[]` 均正常 | **预期前置依赖（先例裁决沿用）** |
| 14 | 回滚方案已交付且可执行；区间 = `845c050..<发布 tip>`→**勘误为 `e376ddf..<发布 tip>`**；干跑 M-2/M-5 ≥1 次 | 区间勘误**裁决成立**（§2）；干跑为已声明未来义务（0.81.0 F-04 教训落实，本草案不预填）——与 0.81.0 R0 F-04「宣称已交付却无演练」有本质区别 | **成立（附 F-04 记法 P3）** |
| 15 | `check-loop-runtime-claims` 双模式全绿预期 ⟦M-2 回填⟧ | 未执行；EVD-1051 终态在案（product_release PASS/0 findings/4 豁免）；M-2 复跑义务已声明 | 文档级（EVD 背书） |

### 1.2 占位扫描（⟦…⟧ 全量归类）

- checklist 18 处：L3/L142 为纪律文本自身；L26 `⟦M-1 交付⟧`、L29、L47 `⟦15⟧`、L48 `⟦16⟧`、L67-82 `⟦M-2 回填⟧`×12——**全部为已声明归属的 M-1/M-2 回填面**，与 0.81.0 R0 F-06「冻结产物内残留占位却声称已回填」有本质区别（本文档自我声明为 M-0/M-1 草案）；但冻结纪律与 ⟦16⟧ 的回填时点自相矛盾 ⇒ **F-02（P2）**
- feature-flags：**0 处** ✓；rollback：**0 处 ⟦⟧**（`<发布 tip>` 尖括号占位 + L14「不预先编造」明令）✓
- CHANGELOG L21：`commit hash ⟦M-1 冻结回填⟧` ×1（同 F-02 类，已声明归属）

### 1.3 Change Inventory 校验

- `git rev-list --count e376ddf..845c050` = **14** ✓；表内 14 个 hash 与 `git log --reverse` **14/14 全等、0 mismatch**、编号 1..14 连续；首/末 = `1db58f5`/`845c050` ✓
- 载荷分解自洽：FIX-338 3 commits（`1db58f5`/`02ad554`/`dfafa95`）+ 0.82.0 载荷 11 commits（`8bd6a8a` 起至 `845c050` 含首尾，FIX-339~346 批）= 14 ✓
- `e376ddf` 语义三重证实：`v0.81.0^{commit}` = `e376ddf`（tag peel 实测）+ 提交主题「0.81.0 transition」+ `release-ledger --version 0.81.0` = `NATIVE_RELEASED` 且 `release_commit = e376ddf` ✓

### 1.4 F-R1-02 数据面处置落地核验（M-1 联动义务）

- roadmap 0.82.0 行（plan-tracker L287）：任务列已**全 token 展开**（`FIX-341/342/343/344/345/346` 全列名，斜杠缩写消除）✓；FIX-335 行（L100）叙事已无「副本 bump 0.82.0」版本 token 牵连 ✓——提案 §1/§2 主路径两项均落地（EVD-1060 声明与热数据一致）
- 「9 条 vs 10 条」口径对账：发布面（CHANGELOG/checklist/rollback）一致写 **9 条 0.38.x 假阳**（EVD-1042 实测口径）；DEC-195/roadmap 规划文本写 10 条 = 诊断期全族（含 1 条 session-snapshot 断言子面，EVD-1041）。规划口径 vs 交付口径差异**有解且发布面自洽**——非缺陷，登记为对账注记

---

## 2. 维度二：回滚方案可执行性（含勘误裁决）

### 2.1 区间锚定勘误裁决（任务指定的本轮核心裁决项）

**裁决：勘误成立（CORRECT），必须维持 `e376ddf..<发布 tip>`，不得回退为原稿 `845c050..<发布 tip>`。** 三重独立证据：

1. **拓扑实测**：`git log e376ddf..845c050` = 14 commits，其中 **11 个 0.82.0 载荷提交（`8bd6a8a`~`845c050`）全部是 `845c050` 的祖先**——若按原稿以 `845c050` 为起点 revert，则全部 0.82.0 引擎改动（FIX-339/341/312/314/342+344/320+322/345/323+325+336/333/332+337/313+346）留在区间外，回不到 0.81.0 行为；
2. **发布 tip 身份**：`v0.81.0^{commit}` = `e376ddf8bd00…`（peel 实测）+ ledger `NATIVE_RELEASED release_commit = e376ddf`——`e376ddf` 是 0.81.0 发布 tip（transition），`845c050` 只是 0.81.0 发布后修复线 + 0.82.0 载荷的当前 HEAD，**不是任何发布态**；
3. **先例同形**：0.81.0 R0 F-01（原稿区间误写两个代表提交 → revert 留下 29 个提交）与本例**完全同形**——rollback L24 勘误注记对教训的引用**准确**，且 F-04 终点纪律（终点必须发布 tip）、干跑义务（§4 #10，M-2/M-5 ≥1 次隔离 worktree）、计数不写死（M-5 现场 `rev-list --count` 取值）、tip 占位不预编造（L14）四条教训**全部落实**。

### 2.2 其余检查项

| 检查项 | 结论 |
|---|---|
| 区间覆盖完整性 | **成立**（`e376ddf..<发布 tip>` 覆盖 FIX-338 3 + 载荷 11 + M-0/M-1/M-2/M-3/M-5 后续批） |
| 计数纪律 | 「计数不写死」**成立**；但载荷 11 commits 的区间记法 `8bd6a8a..845c050` 按 git 语义 = **10**（实测）⇒ **F-04（P3）记法 off-by-one**（11 本身正确，实际 revert 命令不消费该记法，故非 P2） |
| 步骤可执行 | 可执行：取证 → `revert --no-commit e376ddf..<tip>`（或 `checkout v0.81.0`）→ 隔离 `DSH_HOME` 重装；B-2 写入守卫归属 0.81.0 交付的声明与窗口 diff 实测一致（`adapters/dsh/` 窗口 diff 空）✓ |
| 已知缺陷面回归披露 | §1 引擎判定面行 ①~⑤ 五项「回滚即恢复的已知缺陷」逐项如实列出（含 hot fact source 假阳回归、loop-claims 回 BLOCKED）——诚实披露合规 ✓ |
| 数据安全论证 | 与代码事实一致（预设可再生、`real-home writes: 0` 判据延续、治理记录 gitignored 不进窗口、账本回退 = 既有基线非数据丢失）✓ |
| 渲染基线自洽 | `6caf90fe…e55d`（16796 B）跨文档一致（rollback §2.2/§4 #5 ↔ checklist Gate 11）；「回滚后计数回 2983 族是预期结果不是回滚失败」的如实注记 ✓。字节值未复现（渲染执行超出本轮边界，M-2 实测） |
| 不可回滚项 | §5 三项登记合理（tag/治理记录/账本受审历史）✓ |
| 触发条件与决策权 | §6 四条触发 + M-4 用户停点授权语义（DEC-197）一致 ✓ |
| 「渲染字节全程不变」措辞 | L35「渲染产物字节在 0.82.0 全程不变（仅 persona 版本行随 M-1 bump 变化）」字面自相矛盾 ⇒ **F-06（P3）** |

---

## 3. 维度三：CHANGELOG 质量（用户视角）

| 检查项 | 结论 |
|---|---|
| 覆盖度 | **齐全**：五域 12 任务组全景（FIX-312~314/320~326/332~337/339/341~346）+ commit hash 逐条标注 + B-1~B-8 全列（L25-32）+ 升级提示（feature-flags §2 L49 + CHANGELOG L23 指针） |
| Breaking 显式结论 | **达成（0.81.0 R0 F-05 教训落实）**：L36 显式书写「**Breaking changes：无**（VERSIONING.md L11 口径…）」+ MINOR bump 依据（L12 判定规则扩展 + 主题里程碑）；L11 口径比对实测成立（无接口删除/重命名、无默认行为破坏——B-1~B-8 均为判定面/披露面/口径面，B-2 收紧方向为 fail-closed）⇒ 「无 breaking」论证**成立** |
| 三段如实披露 | **齐备**（L34）：① `REVIEW-FIX-333-CODE-R0` accounting 1 条（ragged table 已知基线，随批披露不阻断）；② FIX-346 单机定标口径（空闲 p50×1.5，跨机分层未含）；③ RISK-050 维持打开（2026-10-31）+ dsh 交付面注释级零行为变更声明。三段均与证据链一致 |
| 引注精度 | L36「L37 契约面」引注与现行 VERSIONING.md L37（SKILL.md MUST 规则新增行）不符——系 0.79.0 期继承引注，行号已漂移 ⇒ **F-07（P3）** |
| 投影过渡态披露 | L38「投影前 check-version-consistency 处于预期过渡态」与 Gate 1 实跑结果（已投影、PASSED）衔接一致 ✓ |

---

## 4. 维度四：Feature Flag

| 检查项 | 结论 |
|---|---|
| 「无新增运行时开关」声明 | **成立**：暂存 25 文件 diff 中无任何 flag/opt-in 机制面；B-1~B-8 全部为判定语义/披露机制/口径/守卫证据限定，随版本生效无灰度开关——与代码面一致 |
| 豁免账本治理面描述 | **实质准确**：账本实存 4 条（3×UNSUPPORTED_AFFIRMATIVE@`review-FIX-300-CODE-R0.md` + 1×AMBIGUOUS_SUBJECT_RELATION@`release-checklist-0.81.0.md`——与 §1.1 登记面逐条一致，我实读账本文件）；三锚 fail-closed 代码面证实（digest 锚 `REQUIRED_EXEMPTIONS_SHA256` L114/L1355 + ID 唯一/集合漂移 L1361-1363 + 键面 exact L1368 + `exemptions_applied` 披露 L405）。但 §1.1 括号注把 digest 锚写作「REQUIRED_POLICY_SHA256 + AUTHORITY_POLICY_DIGEST 同族机制」——所引两常量属 authority policy 链锚，账本 digest 锚实为 `REQUIRED_EXEMPTIONS_SHA256` ⇒ **F-05（P3）常量名不精确**（「三锚 fail-closed」结论本身不受影响） |
| D-1 opt-in 缺口维持登记 | **成立**：§4 D-1 明写「显式 opt-in 半边未采——缺口维持登记于 FIX-324（持久归属行）」；plan-tracker L93 FIX-324 持久归属行实存 ✓ |
| 与 0.81.0 对照 | §5「无删除、语义未变」与暂存 diff 无矛盾；`dsh-doctor` 登记面 +1 句为纯声明性（FIX-326①，设计 §2.9.4 边界内——补审报告 §1 逐点核实）✓ |
| B-8 环境限定 | Node ≥22.15 限定语在保守边界声明、§1.2、§2 B-8 三处一致，且「不得声称全引擎覆盖」纪律成文 ✓ |

---

## 5. 维度五：保守边界（no-overclaim）+ 版本号 + 风险

| 检查项 | 结论 |
|---|---|
| 三件套「保守边界声明」段 | **三件齐备**（checklist L5-15 / rollback L5-14 / flags L5-14）：5 个保守 token（no official approval / no marketplace approval / no universal runtime support / no external pilot success / RISK-036 open + **do not claim 1.0.0 production-ready 就地否定**）逐字在场 ✓ |
| B-8 覆盖限定 | 三件 + CHANGELOG 一致携带 Node ≥22.15 限定语 ✓ |
| RISK-050 | 「维持打开、不据此声明关闭」三件 + CHANGELOG 一致；「dsh 交付面注释级零行为变更」与窗口 diff 实测一致（`adapters/dsh/` 空 + `lib/index.js` 仅注释，逐 hunk 核过：orphan staging 权衡 / 行尾注释真实性 / `stagingCreated` 措辞 / scope note，零代码行变更）✓ |
| RISK 复评提案边界 | 三段均标明「不直接改 risk-log，裁决权在 Coordinator」——起草权限边界合规 ✓ |
| 真机措辞纪律 | 「本版无新增真机项」论证 = 窗口交付面零变更（实测支撑）；0.81.0 三项回贴有效（EVD-1040）且 RISK-050 演练明细缺口维持登记；全文档无任何「真机项通过」的未验证声明 ✓；隔离措辞统一为「环境变量重定向至临时目录」✓ |
| 版本号 | 0.81.0 → 0.82.0 单调 +1 MINOR；投影后声明面实测全 0.82.0（Gate 1/2 实跑）✓ |
| manifest candidate 态 | canonical 五检全过（无 BOM / NFC / 键排序 / 紧凑 / **单尾 LF**；494 bytes；canonical roundtrip **字节相等**）；schema 与 0.81.0.json 同构（8 顶层键 + artifacts/trust 子键面一致）；`lifecycle_state=candidate`、`effective_state.lifecycle_state=candidate`、`events=[]`、`provenance=native`、`schema_version=1` ✓ |

---

## 6. 硬门槛逐条裁决（`agents/release-reviewer.md`）

| 门槛项 | 阈值 | 我的裁决 |
|---|---|---|
| 发布检查清单逐项有证据 | = 100% | **有条件成立**：已声明值（Gate 1/2/4/12/10 计数）全部独立复现成立；未执行面全部如实标 ⟦M-2 回填⟧ 未虚报。但清单自身存在 F-02（冻结纪律自相矛盾）与 F-03（悬空指针）两处文档完整性缺陷，且检查清单未把 F-01 的漏 bump 面纳入任何批次行（盲区） |
| 回滚方案存在且可执行 | 已交付 | **成立**（区间勘误裁决成立；干跑为已声明的 M-2/M-5 义务，草案未虚填演练结果——0.81.0 F-04 教训正确内化） |
| CHANGELOG 用户视角完整 | 关键段全覆盖 | **满足**（B-1~B-8 + 显式 Breaking 无 + 三段披露 + 升级提示） |
| breaking changes 已标注 | = 100% | **满足**（L11 口径论证成立 + 显式结论行在场） |
| Feature Flag 关闭验证 | 全部通过 | **满足**（无新增开关声明与代码面一致；D-1 缺口维持登记；账本三锚实锚） |

---

## 7. Findings

### F-01 — **P1（blocking）** — `commands/governance-init.md` bootstrap 模板标记面漏 bump：3 处 `@bootstrap-version: 0.81.0` 未随 0.82.0 候选更新

- **位置**：`commands/governance-init.md` L197 / L262 / L533（三个 profile 模板实例）；对照面：同批已 bump 的 `adapters/dsh/AGENTS.md.template`（`@bootstrap-version: 0.81.0→0.82.0`）与 `agent-presets/governance/agent.cordis.yml.template`（persona 行 `v0.81.0→v0.82.0`）
- **事实依据（4 条实测链）**：
  1. 暂存 25 文件清单**不含** `commands/governance-init.md`（`git status --porcelain` + `git diff --cached --stat` 双证）；staged 树内该文件 3 处标记仍为 `0.81.0`（`git grep --cached` 实测）
  2. **三代打包先例均同步该面**：`d995df5`（0.79.0 候选）提交信息明列「bootstrap 标记」在 24 文件投影集内；`bcb0d6d`（0.80.0 候选）改该文件 3+/3−；`a89341e`（0.81.0 候选）diff 实证恰 3 处 `@bootstrap-version: 0.80.0→0.81.0`（逐 hunk 读出）
  3. **引擎门禁不覆盖**：`check-version-consistency` 实跑输出明列检查集「13 files + bootstrap markers (AGENTS.md, CLAUDE.md)」——不含 governance-init.md；`check-projection-sync` 15 mirrors 同样不含 ⇒ Gate 1/2 双 PASSED 下该面完全裸奔
  4. **机制后果**：FIX-238.2 陈旧判定 = 模板头 < SKILL frontmatter active_version ⇒ 0.82.0 发布后新装用户首会话即判定陈旧（0.81.0 < 0.82.0），bootstrap 自升级用 canonical 模板重写后头部**仍是 0.81.0** ⇒ 判定永不收敛，每个新装会话重复报升级
- **影响**：候选载荷完整性缺口（发布物自带的初始化模板出生即陈旧且自升级机制空转）；属「范围漂移」类——role 执行原则「任何范围漂移必须阻塞」。产品代码与既有用户零影响（已安装用户的入口文件已由本地 bump 覆盖）
- **建议（最小修复）**：M-1 冻结前随批把三处 `0.81.0`→`0.82.0`（3 行变更）并入候选提交；**或** DEC 显式裁决豁免——但豁免必须同时处理 FIX-238.2 判定语义（否则新装空转仍在）。修复后建议在 `check-version-consistency` 或投影集登记该面（防复发，另立任务候选，非本版义务）

### F-02 — **P2** — checklist 冻结纪律自相矛盾，且 EVD-1060 已宣告「M-1 完成」而占位未消除

- **位置**：`docs/release/release-checklist-0.82.0.md:3`、`:48`、`:142`；对照 `.governance/evidence-log.md:2169`（EVD-1060「M-1 完成，待 M-2 门禁实测」）
- **事实依据**：L142「M-1 冻结前 MUST 消除本清单全部 ⟦待回填⟧/⟦待落地⟧ 占位（**M-0 批 commit hash、候选打包 commit**、`core/releases/0.82.0.json`），否则不得进入 M-2」；而 L48 明写「候选 commit hash **由 M-2 期 `release-ledger …` 派生回填**」——候选提交 hash 在候选提交存在之前不可知，两条规则对同一占位给出不可同时满足的时点要求；且 EVD-1060 已宣告 M-1 完成时 ⟦15⟧/⟦16⟧ 占位仍在场
- **影响**：M-2 进入判据自我矛盾——严格按字面则 M-2 永远不可进入；宽松执行则冻结纪律形同虚设（0.81.0 F-06 型问题正是从占位纪律失守开始的）
- **建议**：把冻结语义收敛为「冻结 = 占位替换为回填指令与归属（M-0 批 hash 于 M-0 批提交后回填；候选 hash 于 M-2 由 ledger 派生回填，`derivation=git_commit_adding_path`）」，修订 L3/L48/L142 三处措辞

### F-03 — **P2** — checklist「逐项处置报告见下专节」为悬空指针：文内无该节

- **位置**：`docs/release/release-checklist-0.82.0.md:26`（「FIX-324/326 并入批（…逐项处置报告见下专节）」）；对照 `:146`（footer：「见 Release Agent 结构化返回，M-1 期由 Coordinator 决定是否作为附录随批入库」）
- **事实依据**：全文 146 行无「FIX-324/326 并入处置」节；实际处置内容散落三处（adapter-manifest note = 暂存 diff；host-contract 三 note = 暂存 diff + 补审报告 §2；FIX-326② = EVD-1054；FIX-326④ = 无需动作声明只在 footer 口径）
- **影响**：发布门禁文档内的读者可追责引用断裂——外部审查按「下专节」找不到对象（0.81.0 R0 F-06 同类「文档完整性」教训面）
- **建议**：M-1 冻结前二选一：① 补一节 5~10 行的逐项处置表（FIX-324①~⑤ / FIX-326①②③④ 各一行：处置 + 载体 + 证据指针 `review-FIX-324-326-CODE-R0.md`/EVD-1054）；② 把 L26 措辞改为「逐项处置见 `docs/reviews/review-FIX-324-326-CODE-R0.md` 与 checklist footer 移交说明」

### F-04 — **P3** — 回滚窗口载荷计数区间记法 off-by-one（11 vs git 语义 10）

- **位置**：`docs/release/rollback-plan-0.82.0.md:22`、`:24`（「0.82.0 载荷 **11 commits**（`8bd6a8a..845c050` …）」）
- **事实依据**：`git rev-list --count 8bd6a8a..845c050` = **10**（区间语义不含基点）；11 为含 `8bd6a8a` 在内的正确计数，正确的区间记法 = `8bd6a8a^..845c050` 或文字「`8bd6a8a` 起至 `845c050` 含首尾」
- **影响**：低——计数不承载 revert 命令（实际区间 `e376ddf..<发布 tip>`，计数 M-5 现场取值）；但 0.81.0 R0 F-03 教训正是「发布文档计数与实测不符」，同一类痕不应复现
- **建议**：改为 `8bd6a8a^..845c050` 或文字表述

### F-05 — **P3** — feature-flags §1.1 账本 digest 锚常量名不精确

- **位置**：`docs/release/feature-flags-0.82.0.md:27`
- **事实依据**：账本 digest 锚实为 `REQUIRED_EXEMPTIONS_SHA256`（`loop_runtime_claims.py:114`，校验点 `:1355`）；括号注所引 `REQUIRED_POLICY_SHA256`/`AUTHORITY_POLICY_DIGEST` 属 authority policy 链锚（`:109`/`:1263`）。「digest/ID/键面三锚 fail-closed」结论经代码面证实**不受影响**
- **建议**：括号注改为「`REQUIRED_EXEMPTIONS_SHA256`（与 authority 链 `REQUIRED_POLICY_SHA256` 同族机制）」

### F-06 — **P3** — rollback「渲染产物字节全程不变」与括号注自相矛盾

- **位置**：`docs/release/rollback-plan-0.82.0.md:35`
- **事实依据**：「渲染产物字节在 0.82.0 全程不变（仅 persona 版本行随 M-1 bump 变化）」——字节确实因版本行而变；不变的是渲染语义与「差异恰为版本行 1 处」的结构。0.81.0 先例对该点的措辞精度正是 R0 F-01 的教训面
- **建议**：改为「渲染语义零变更：0.82.0 渲染产物与 0.81.0 基线的差异**恰为 persona 版本行 1 处**（M-2 实测回填）」

### F-07 — **P3** — CHANGELOG「L37 契约面」引注行号漂移

- **位置**：`project/CHANGELOG.md:36`
- **事实依据**：现行 `VERSIONING.md:37` = 「SKILL.md MUST 规则新增 | MINOR」行，非契约面；该引注系 0.79.0 期（`d995df5` 提交信息同款「MINOR 定位 L12/L37」）继承，行号随后续版本编辑漂移
- **建议**：改为不依赖行号的表述（如「MUST-bump 表契约面行」）或在 VERSIONING.md 相应行加节锚

---

## 8. 独立复现声明

**我亲自复现（实测成立）**：

1. `v0.81.0^{commit}` = `e376ddf8bd00d6399d18f3b47e2cbc7dcef4d6e3`；`e376ddf` 提交主题 = REL-077 transition。
2. `git rev-list --count`：`e376ddf..845c050` = **14**；`8bd6a8a..845c050` = **10**（记法语义）。Change Inventory 表 **14/14 hash 全等、编号连续**。
3. 窗口 `adapters/dsh/` diff = **空**；`lib/index.js` diff = **仅注释**（4 hunk 逐行核过，零代码行变更）；暂存 `adapters/dsh/` = 3 文件（AGENTS.md.template 版本行 / adapter-manifest.json +1 句 / host-contract.json 3 note）。
4. 契约 SHA 双态逐位：staged = `63B28311…28DF2`（75331 B）；HEAD blob = `96F92485…43FC6E`（74702 B）。
5. Gate 1 `check-version-consistency` = **PASSED**（13 文件 + AGENTS/CLAUDE 标记；plan-tracker 1 WARN 如声明）；Gate 2 = **PASSED**（15 mirrors）；Gate 4 = **PASS**（717/802）——全部隔离 `DSH_HOME` 下实跑。
6. `release-ledger --version 0.82.0 --no-remote` = **FAIL 恰 1 issue**（`candidate_commit: found 0`）+ `NATIVE_CANDIDATE`/`candidate`/`events=[]`；`--version 0.81.0` 对照 = **PASS**/`NATIVE_RELEASED`/`release_commit=e376ddf`。与 EVD-1034 gate 13「文件未入 git ⇒ found 0 属预期前置依赖」先例同判。
7. manifest canonical：494 bytes、无 BOM、单尾 LF、NFC、键排序、紧凑、canonical roundtrip **字节相等**；schema 与 0.81.0.json 同构。
8. 豁免账本实读：`schema_version=1`、**4 条**（3×UNSUPPORTED@review-FIX-300 + 1×AMBIGUOUS@checklist-0.81.0）——与 feature-flags §1.1 登记面逐条一致；三锚代码面（L114/L1355/L1361-1363/L1368/L405）逐点核对。
9. **discover 计数**：候选树全量 = **3200**、`test_verify_workflow` = **850**——与 checklist Gate 10 M-0 声明同值（TestLoader `countTestCases()` 口径，隔离 `DSH_HOME`）。
10. **F-01 证据链**：`git status --porcelain` 25 文件不含 governance-init.md；`git grep --cached @bootstrap-version` = 3×`0.81.0`；`git show a89341e -- commands/governance-init.md` = 恰 3 处 `0.80.0→0.81.0`；`bcb0d6d` 触及 3+/3−；Gate 1 实跑输出明列检查集不含该文件。
11. 占位全量扫描（三件套 + CHANGELOG 头段）+ 逐处归类；`⟦M-1 冻结回填⟧`（CHANGELOG L21）在案。
12. 证据链逐行核对：21 任务 25 条 REVIEW-* 机录行（FIX-339×3/341/312/314×2/342/344/320×2/322×2/345/323/325/336/333×2/332/337/346/313-R1/324/326）终态全部 `APPROVED_WITH_NOTES/unresolved_blockers=0`，无悬空 NEEDS_CHANGE；FIX-343 = M1.2 数据批（EVD-1045）；B-5 三键活体证据 = 四组同轮双机录对（320/322、342/344、323/325/336、332/337）。
13. DEC-195/196/197 逐条与交付比对；F-R1-02 处置两项落地核验（roadmap 全 token 展开 + FIX-335 叙事去牵连）。
14. 三件套保守边界 token 三处逐字在场（含 `do not claim 1.0.0 production-ready`）；「真机」措辞扫描无未验证通过声明。

**我未能独立复现（执行边界外，按 fail-closed 标「文档级事实」）**：

- pristine `845c050` 隔离 worktree 同值 3200（git 只读红线，不建 worktree——该值维持文档级，M-2 复核）；
- 全量测试**运行**面（850 OK exit 0、28u/28v/28w、archguard R1 24453/R7、check-release 静态 13/13+执行面）——M-2 义务；
- 渲染 sha256 字节值 `6caf90fe…e55d`（16796 B）与「差异恰版本行 1 处」——跨文档一致、结构支撑成立，字节值 M-2 实测；
- 时钟注入 2027/2030 双点、`test_dsh_*` 套件计数——已由 `review-FIX-324-326-CODE-R0.md` 独立复现在案（机录 APPROVED_WITH_NOTES/0），本轮不重复执行。

⇒ 本轮 **F-01（blocking）的依据全部来自可复现静态实测**（§8 第 3/10 条）；无任何 finding 依赖未复现数值。

---

## 9. 命令上报（全部只读 + 隔离 DSH_HOME；无任何写操作）

| # | 命令（摘要） | 退出码 | 结论摘要 |
|---|---|---|---|
| 1 | `git rev-parse "v0.81.0^{commit}"` / `git log -1 e376ddf` | 0 | peel = e376ddf；transition 提交 |
| 2 | `git rev-list --count e376ddf..845c050 / 8bd6a8a..845c050` | 0 | 14 / 10 |
| 3 | `git log --format="%h %s" e376ddf..845c050` | 0 | 14 hash 与表全等；1db58f5→845c050 |
| 4 | `git diff --stat e376ddf 845c050 -- adapters/dsh/`；`git diff e376ddf 845c050 -- lib/index.js` | 0 | 空 / 仅注释 |
| 5 | `git diff --cached --stat -- adapters/dsh/`；`git status --porcelain` | 0 | 3 文件 / 候选 25 文件（21M+4A） |
| 6 | `Get-FileHash host-contract.json`；`git cat-file blob 845c050:…` 导出后哈希 | 0 | 63B28311…（75331B）/ 96F92485…（74702B） |
| 7 | `release-ledger --version 0.82.0 --no-remote` / `--version 0.81.0`（`$env:DSH_HOME=%TEMP%\$tmpHome`） | 1 / 0 | FAIL candidate_commit found 0（预期前置依赖）/ PASS NATIVE_RELEASED |
| 8 | python canonical 五检（NFC/排序/紧凑/LF/BOM + 0.81.0 schema 对照） | 0 | 全过；roundtrip 字节相等 |
| 9 | `check-version-consistency` / `check-projection-sync --fail-on-issues` / `check-manifest-consistency --fail-on-issues`（隔离 DSH_HOME） | 0/0/0 | PASSED（1 WARN）/ PASSED 15 / PASS 717-802 |
| 10 | discover 计数脚本（`TestLoader.discover` + `countTestCases`，隔离 DSH_HOME） | 0 | FULL=3200；verify 模块=850 |
| 11 | `git show a89341e/bcb0d6d -- commands/governance-init.md` + `git log --oneline -3 -- <file>` | 0 | 三代候选均触及；a89341e 恰 3 处标记 bump |
| 12 | `git grep --cached`（0.81.0 残留声明面 / @bootstrap-version）；`git show :SKILL.md` frontmatter | 0 | 无残留声明面；frontmatter 0.82.0；governance-init 3×0.81.0（F-01） |
| 13 | ⟦⟧ 占位扫描 + 保守 token/「真机」措辞扫描（UTF-8 显式读取） | 0 | 见 §1.2/§5 |
| 14 | 豁免账本实读 + `loop_runtime_claims.py` 锚面 grep | 0 | 4 条；三锚+披露代码面证实 |

未执行任何 `git add/commit/restore/reset/checkout/stash/revert/worktree`；未运行任何测试套件（仅 TestLoader 计数）；所有 python 门禁/ledger 运行均使用一次性 `%TEMP%` 隔离 `DSH_HOME`（用后删除）；未触碰 `$HOME/.dsh` 与仓库外持久路径。

---

## 10. 发布就绪裁决

**裁决：不具备进入 M-2 收口/M-4（用户停点）的条件——1 项 P1 blocking（候选载荷完整性）。**

理由：F-01 属发布物自带的初始化模板出生即陈旧 + 自升级不收敛的用户可见缺陷，且是连续三代打包先例都覆盖的面在本次缺位（范围漂移类，role 执行原则必须阻塞）。产品代码、版本号、manifest canonical、CHANGELOG、flag 面、回滚方案设计、no-overclaim 措辞、授权链一致性**均未发现实质缺陷**；已声明实测值抽检（Gate 1/2/4/12、discover 3200/850、契约双态 SHA、ledger 双版本）**全部复现成立**——本轮属「载荷完整性 + 文档一致性」类阻塞，非架构/功能类阻塞。

**最小阻塞项清单（修完即可发起本审查 R1）**

| # | 动作 | 覆盖 finding | 判据（修复验收） |
|---|---|---|---|
| 1 | M-1 冻结前把 `commands/governance-init.md` 三处 `@bootstrap-version: 0.81.0→0.82.0` 随批入库（或 DEC 显式豁免 + 陈旧判定语义同步处理） | F-01 | staged 树 `git grep --cached "@bootstrap-version: 0.81.0"` = 0 命中（历史 release 报告引文除外） |
| 2 | 收敛冻结纪律语义（L3/L48/L142）：冻结 = 占位替换为回填指令；候选 hash 由 M-2 ledger 派生 | F-02 | 三处措辞不再给出不可满足的时点要求；与 EVD-1060「M-1 完成」状态自洽 |
| 3 | 消除「见下专节」悬空指针（补逐项处置节或改指 `review-FIX-324-326-CODE-R0.md`） | F-03 | checklist 内无文内无法解析的引用 |
| 4 | （随批顺手）F-04 记法 / F-05 常量名 / F-06 措辞 / F-07 引注 | F-04~F-07 | 各处与实测一致 |

**推荐次序**：1 → 2 → 3 → 4 → 同一 Release Reviewer R1 复审（报告头部声明 round 并逐条比对本轮 findings 修复状态；机录轮次由 review-record 机制按 Coordinator 指定承接）。M-2 门禁实测（含安静窗 850 复跑、check-release 后台作业、渲染 parity、archguard 复跑）与真机/演练义务维持已声明安排；RISK-050 维持打开；**M-4 停点前任何文档不得声明 M-2/M-3 未实测项通过**（本轮已核：现无此类声明）。

---

*审查方：Release Reviewer Agent（只读 + 隔离 DSH_HOME 复现）｜审查对象版本：0.82.0（REL-078）｜基线 HEAD `845c050` + 已暂存未提交候选（25 文件）｜结论：**NEEDS_CHANGE**｜unresolved_blockers=1（F-01）｜机录 round 建议 = REVIEW-REL-078-R2（Coordinator 以 review-record 持久化；NEEDS_CHANGE 非终态，返工后必须发起下一轮复审，不得以任何形式跳过复审标记通过）*
