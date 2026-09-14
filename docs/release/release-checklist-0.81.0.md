# Release Checklist — 0.81.0 (REL-077)

- **状态**：**M-1 冻结**（2026-09-13）。V8（FEAT-031 `3074120`）与 V10（FIX-313 `61b571c`）均已落地并回填终态；随后进入 M-2 门禁实测。**候选 manifest 落库时序（REVIEW-REL-077-CODE-R1 F-R1-02）**：`core/releases/0.81.0.json`（candidate 态）MUST **与候选打包提交同批入库**——它正是 ledger 派生 `candidate_commit` 的唯一依据，故 M-2 的 ledger 回填发生在该提交之后。
- **版本**：0.81.0（**dsh 宿主兼容性体系化**）｜前置稳定版 **0.80.0**（tag `v0.80.0`）｜候选打包 commit：M-1 打包提交（本 checklist 的冻结提交；其 hash 由 M-2 期由 `release-ledger --version 0.81.0 --no-remote` 从 git 派生后回填）
- **授权链**：**DEC-189**（架构授权）· **DEC-190**（M-0 范围裁决 = 全量 V1~V8 + V10 入槽 0.81.0 + ⑧ 真机验收路径 + ⑨ 发布预授权）· **DEC-191**（`necessary_ids` = 72；`compat_range` 取值推 V8）· **DEC-192**（夹具迁移授权 + K-2 allowlist 0/0）
- **用户原始诉求**（2026-09-13）：dsh 升级适配后出现大量兼容性问题，需系统性分析/设计/实现，并**发布对应版本**；四条硬要求：**① 最小化宿主依赖 ② 必要依赖解耦单点维护 ③ 依赖代码严格校验看护 ④ 依赖边界可调测性**

## Release Scope

| 分组 | 任务 | 版本归属 |
|---|---|---|
| **分析**：依赖面全量清点 | **AUDIT-153**（801 行事实报告：D-01~D-100 依赖点 / G-01~G-18 缺口**逐条实测复现** / C-1~C-25 约束 / R-01~R-19） | 0.81.0 |
| **设计**：体系化兼容架构 | **FEAT-028**（ADR-018 280 行 + 设计规格 1023 行：契约 + 访问器 + K-1~K-13 看护 + S0~S7 诊断 + 切片 V1~V10 + R1 处置） | 0.81.0 |
| **实现 V1** | FEAT-029（契约数据层）+ FIX-317（V1 审查收口） | 0.81.0 |
| **实现 V2** | FEAT-030（消费方改读契约 + K-2 静态扫描） | 0.81.0 |
| **实现 V3** | FIX-315（零校验不得 PASS：`rows_checked==0 ⇒ NOT_RUN` + `coverage` + kind 驱动上屏） | 0.81.0 |
| **实现 V4** | FIX-311（group 语义与 **loader 真实语义**对齐 + G-18 分类自检 + F-R1-03 白名单化） | 0.81.0 |
| **实现 V5+V6+V7** | FIX-316（渲染/解码守卫 G-05/G-07/G-10/D-50/D-56/D-66 + `DSH_HOME` 两实现收敛 + 版本证据看护 + **写入守卫对称化**） | 0.81.0 |
| **实现 V8** | **FEAT-031**（Check 28w K-1~K-13 + `dsh-doctor` S0~S7 + `host-facts` 升级演练 + registry 接线 + 两次 `--regen`） | 0.81.0 |
| **实现 V10** | **FIX-313**（`lib/index.js` catch 清理退化：防误删 CWD 同名目录） | 0.81.0 |
| **并行收口** | FIX-319（Check 18c 粗体误报）+ FIX-321（粗体剥离 run 边界守卫；FIX-319 遗留 F-01） | 0.81.0 |
| **发布治理面** | 真机验收规程、版本规划（含 M-2 前置预检）、回滚方案、特性开关、本 checklist、`core/releases/0.81.0.json` | 0.81.0 |
| **风险挂载** | **RISK-050**（dsh 上游内部面耦合；截止 2026-10-31）。本版把**依赖面枚举 + 契约化 + 零校验门禁 + 单点诊断 + 升级演练**前移，**不声明关闭** | 0.81.0 |
| **如实披露的既有失败** | `check-loop-runtime-claims` 语义面 **BLOCKED**（3 条 `UNSUPPORTED_AFFIRMATIVE` 全在**既有** `docs/reviews/review-FIX-300-CODE-R0.md`，0.66.1 期引入）→ **FIX-320**（本版处置 = 如实披露） | 0.81.0 披露 |

## Change Inventory（**31 commits** — `git log --oneline d87ead8..3074120`，2026-09-13 M-1 冻结核定；**全部切片 V1~V8 + V10 已落地**；表内 #N = 该窗口 `git log --reverse` 第 N 个 commit）

| # | 任务 | commit | 终态要点（审查终态 + EVD） |
|---|---|---|---|
| 1 | FEAT-029 / **V1** | `4d93b24` | 契约本体 `host-contract.json`（2456 行）+ `dsh_contract.py`（4 API + 3 异常类）+ 自校验测试 + 夹具发射器；EVD-1011 |
| 2 | AUDIT-153 + FEAT-028 | `4dfde66` | 依赖面清点 801 行 + ADR-018 + 设计规格 1023 行 + R0/R1 审查报告；EVD-1009/1010 |
| 3 | FEAT-029 R0 报告 | `97f0d38` | **APPROVED_WITH_NOTES / 0** |
| 4 | FEAT-030 / **V2** | `1ddb503` | 消费方改读契约（行为保持）——`lib/index.js` 8+3 绑定 + `launch.py` 12 绑定 + `dsh_compat.py` 11 绑定（`PROBE_SCRIPT` 包名/符号抽为 `host.apis` 占位符）+ K-2 静态扫描（8 消费者 / allowlist 0-0）+ per-field 突变矩阵 6 条 + 受权夹具迁移；EVD-1012；DEC-190/DEC-192 |
| 5 | FEAT-030 R0 报告 | `6081285` | NEEDS_CHANGE / 1（P0 F-01 + P1×2） |
| 6 | **FIX-317** | `ba210b9` | V1 审查收口：编码分类 / `recorded` 值校验 / 切片归属 / 覆盖声明；**REVIEW-FIX-317-R0 APPROVED_WITH_NOTES/0**；EVD-1015 |
| 7 | FIX-317/FIX-315 R0 报告 | `8bd4d60` | 两份报告入库 |
| 8 | REL-077 规程 | `135e7df` | 真机验收规程（DEC-190 ⑧ 执行载体） |
| 9 | **FIX-315 / V3** | `b35d1d6` | 零校验不得 PASS（G-01 a~e）；R0 NEEDS_CHANGE/1 → **R1 APPROVED_WITH_NOTES/0**；EVD-1016/1017 |
| 10 | REL-077 文档修复 | `3059aae` | 起草文档 ragged table 修复 + 身份门禁残余阻塞归因（→ FIX-320）；EVD-1018 |
| 11 | **FIX-319** | `3fb90fe` | Check 18c 粗体误报（判据层 3/3 消除 + 9 条反证全 FAIL + 192 条穷举 0 例外）；**APPROVED_WITH_NOTES/0**；遗留 F-01 → FIX-321；EVD-1019 |
| 12 | FEAT-030 / **V2**（R1 返工收口） | `3c37342` | 消费方改读契约（行为保持）+ K-2 扫描；R0 NEEDS_CHANGE/1 → 返工 → **R1 APPROVED_WITH_NOTES/0**（含 N-1 微补）；EVD-1020 |
| 13 | **FIX-321** | `6e3c828` | 双侧 run 边界守卫（放宽面穷举命中 **0**）；**APPROVED_WITH_NOTES/0**；EVD-1021 |
| 14 | **FIX-311 / V4** | `85fb309` | group 语义对齐 loader + G-18 分类自检 + F-R1-03；三处请裁决项全部背书；**APPROVED_WITH_NOTES/0**；EVD-1022 |
| 15 | **FIX-316 / V5+V6+V7** | `2d66d0f` | 渲染解码守卫 + `DSH_HOME` 收敛（20 例 0 分歧）+ 版本证据看护 + **写入守卫对称化**；R0/2 → R1/1 → **R2 APPROVED_WITH_NOTES/0**；EVD-1023/1024/1026 |
| 16 | REL-077 设计同步 | `1c2dc0a` | F-R1-06：`coverage.unreadable_compositions` 补入 G01-b 与 §5.1 S2 投影 + 约束段；EVD-1027 |
| 17 | REL-077 版本规划 | `0060844` | M-2 前置门禁预检（3 项 bump 前已 PASSED；bump 后 MUST 重跑） |
| 18 | REL-077 回滚方案 | `af2b58c` | 回滚影响分类 + 程序 + 数据安全论证 + 7 项验证 + 基线按 `d87ead8` 实测核定 |
| 19 | REL-077 特性开关 | `c15f6df` | 新增 opt-in 开关**为零**；两项行为变更 B-1/B-2；加性检查面 3 项 |
| 20 | REL-077 发布检查清单 | `9e80c6a` | 0.81.0 发布检查清单（M-1 草稿）——Release Scope（AUDIT-153 / FEAT-028 / V1~V10 / FIX-313·319·321 + RISK-050 挂载 + FIX-320 如实披露）+ Change Inventory（当时按 git log 实测 19 commits）+ 行为变更 B-1/B-2 + M-2 门禁表 14 项（含真机项与回填占位）+ M-8 补推义务 |
| 21 | REL-077 CHANGELOG | `2bc2889` | CHANGELOG 新增 0.81.0 条目（M-1 草稿）——按用户诉求四条硬要求组织叙事 + 三步（事实清点→契约架构→五切片落地）+ 并行收口 FIX-319/321 + 两项行为变更 B-1/B-2 + FIX-320 既有失败如实披露 + RISK-050 不声明关闭 + 真机项未回贴前不得声明通过；V8/V10 commit 待回填（由本冻结提交回填 `3074120` / `61b571c`） |
| 22 | REL-077 M-2 执行序 | `a5e7622` | 发布检查清单补 M-2 执行序（门禁顺序 + `check-release` 实测需后台作业 + 两次 `--regen` 的证据与越权停止纪律 + 真机项禁声明纪律 + M-1 冻结前必须消除全部回填占位） |
| 23 | **FIX-313 / V10** | `61b571c` | `lib/index.js` catch 清理的所有权判据重写——非递归 mkdirSync + EEXIST 换名重试（不删）+ 仅创建成功才置 stagingCreated + 只删已证明属己的精确路径 + 无证明则不删并告警 + 8 次熔断；消除「按名前缀误删同名用户目录」与「误删 CWD 同名目录」两类破坏；实际改动面 **+66/−13**（`lib/index.js` 产品代码；3 文件 `--stat` 实测 **+329/−13**）；REVIEW-FIX-313-R0 APPROVED_WITH_NOTES/0；EVD-1028 |
| 24 | REL-077 验收① Honesty Note | `5ea1850` | 发布检查清单补「验收① 证据形态披露（Honesty Note）」——FIX-313/V10 验收① 由独立审查的故障注入复现成立（非机器守卫），机器守卫登记 FIX-325；硬约束：清单 / CHANGELOG 均不得声称验收① 有测试守卫；同批登记实际改动面 +66/−13（F7）与孤儿 staging GC 权衡（F4） |
| 25 | REL-077 M-2 预检（棘轮） | `7c2d717` | 发布检查清单回填 M-2 预检——Coordinator 独立实测 `archguard-ratchet` 全绿（R1 24405 <= anchor、R5 cli 84/84 + segments 71/71 含 Check 28w、R7 regen deterministic 且 committed==fresh 证明两次 `--regen` 幂等）；Check 28w 段注册已由 R5 确认 |
| 26 | REL-077 M-2 预检（Check 28w） | `146a93a` | 发布检查清单回填 M-2 预检——Coordinator 独立实测 Check 28w 全绿（Result PASS / 0 failing criterion；K-1~K-13 逐条结论；K-6 机检 DEC-187 I-1/I-2/I-3；K-9 72 条必要依赖全覆盖；K-11 allowlist 0/0；K-12 单一生成点携带 `unreadable_compositions` 兑现 F-R1-06；K-7 按设计 NOT_RUN）；M-2 需在切片全落地后重跑 |
| 27 | REL-077 dsh-doctor 预检 | `9500d7b` | 发布检查清单补 dsh-doctor 预检（Coordinator 独立实测）——CLI 接口与设计 §5 一致（S0~S7 + 四开关 + `--rehearse`/`--against`/`--allow-host-probe`）；`--offline --selftest` 结果 PASS/exit 0，且 8 阶段逐条演示阶段级崩溃隔离（崩溃阶段降 NOT_RUN、其余 7 阶段照跑、退出码三态正确） |
| 28 | REL-077 测试基线预检 | `e6087de` | 发布检查清单回填 M-2 测试基线预检——Coordinator 独立实测 `test_registry` 77 OK / `test_dsh_compat` 120 OK / `test_dsh_contract` 120 OK / `test_dsh_adapter` 50 OK，证明 V8 的 registry 接线与 V10 的改动均未造成回归（M-2 仍需跑全量含新 2 套件并披露既有失败） |
| 29 | REL-077 测试基线（含 V8 两套件） | `210b200` | 发布检查清单回填 M-2 测试基线——`test_dsh_boundary` 115 OK、`test_dsh_doctor` 70 OK（均在 `DSH_HOME=%TEMP%` 隔离下由 Coordinator 实跑），连同 registry 77 / compat 120 / contract 120 / adapter 50 全绿；既有失败基线（`test_verify_workflow` 3 条 → FIX-320）由 pristine-HEAD 对照独立确认非本版引入；EVD-1030 |
| 30 | REL-077 F-03 发布条件 | `6fa8940` | F-03 发布条件落地——设计 §5.1/§5.5 的「唯一契约证据写入路径」口径收窄为「证据采集 = 单点」+ 新增 `evidence.*` 写入面约束段（契约 `evidence.*` 由维护者在受审提交中更新；未记录时 K-7/S3 一律 NOT_RUN 绝不默认 PASS）；依据 REVIEW-FEAT-031-CODE-R1 F-03 判定（代码侧已闭环、设计侧未落地）与 DEC-193 |
| 31 | **FEAT-031 / V8** | `3074120` | Check 28w `check-dsh-boundary`（K-1~K-13）+ `dsh-doctor` 单点诊断（S0~S7 / 四开关 / 退出码 0-1-2 / 阶段级崩溃隔离）+ `host-facts` 升级演练 + registry 接线 + 两次 `--regen`；REVIEW R0→R1 均 APPROVED_WITH_NOTES/unresolved_blockers=0（发布条件 F-02/F-03 已闭环）；18 文件 +7232；EVD-1032 |

## 行为变更（面向用户 —— MUST 出现在 CHANGELOG 与升级说明）

详见 `docs/release/feature-flags-0.81.0.md` §2：
- **B-1** `--install` 对缺失/不可读 `package.json`：`rc 0`（写占位 `"0"`）→ **`rc 1` 拒绝**；
- **B-2** 真实 home 形态的 `DSH_HOME` 下 `--install`/`--sync`/`--uninstall`：可用 → **`exit 2` + `[REFUSED]`**（`--dry-run` 仍放行）。

## Candidate Gate Results（M-2 —— Coordinator 回填实测）

> **M-2 状态**：本表由 M-2 门禁实测逐项回填；已预检项以「预检 PASSED」标注。未回填项在 M-2 完成前不得视为通过。

| # | Gate | 预期 | Result |
|---|---|---|---|
| 1 | `check-version-consistency` | PASS（bump 后全投影 = 0.81.0） | **实测 PASSED — `all version declarations consistent`（exit 0；FAIL=0）**（Coordinator 独立实测 2026-09-13，bump 前为 `FAILED — 2 mismatch(es)`，由 FIX-327 收口）。**如实附注（REVIEW-REL-077-CODE-R1 F-06/F-R1-08）**：该命令同时输出 1 条 `[WARN] plan-tracker workflow version=0.80.0, expected=0.81.0`——该文件位于 gitignored `.governance/`，按发布纪律在 M-8 收尾才转 `0.81.0`（`verify_workflow.py` 把 `[WARN]` 排除出 fail 集，故结论行仍为 PASSED）；另有 `CLAUDE.md` 本地未跟踪副本的 1 条 advisory WARN（`.gitignore:3`，**不修改**）。 |
| 2 | `check-projection-sync --fail-on-issues` | PASS | ⟦待回填⟧（bump 前预检 **PASSED**） |
| 3 | `check-injection-contract --fail-on-issues` | PASS | ⟦待回填⟧（bump 前预检 **PASSED**） |
| 4 | `check-manifest-consistency --fail-on-issues` | PASS | **实测 PASS**（exit 0）：`Canonical files: 689 / Actual files: 770`，`[PASS] Manifest and filesystem are consistent.`（本批零文件增删，天然 PASS） |
| 5 | `cleanup.py --dry-run` | 零删除 | **实测通过（零删除）**：输出 `[CLEANUP-ERR-002] No redundant files found. Plugin installation is clean.`；`exit=1` 是该脚本「无冗余文件」的**正常终止码**（`cleanup.py:26 ERR_NOTHING_TO_CLEAN = 1`），非失败——判据是「零删除」而非退出码 0。 |
| 6 | `archguard-ratchet`（**两次 `--regen` 后**） | 无新增 ERROR | **预检 PASSED（Coordinator 独立实测 2026-09-13，V8 在制品状态下）**：`R1 PASS mainfile loc 24405 ≤ anchor 24405（only-down）`、`R2 PASS reverse-dep 47 ≤ 47`、`R3 PASS matrix 12 edges`、`R4 PASS print 1299 ≤ 1299`、**`R5 PASS cli keys 84/84 frozen, segments 71/71 frozen`**（含 Check 28w 段）、`R6 INFO cold import 196（Δ0，advisory）`、**`R7 PASS regen deterministic=True; committed==fresh True`**（即两次 `--regen` **幂等**）；`Result: PASS (0 violations; raw findings before exemptions: 0) — fatal gate green`。⟦M-2 需在全部切片落地后重跑⟧ |
| 7 | **Check 28w** `check-dsh-boundary`（V8 交付） | PASS / 或如实披露豁免 | **预检 PASSED（Coordinator 独立实测 2026-09-13，V8 在制品状态下）**：`Result: PASS — 0 failing criterion(a)`；逐条：**K-1** PASS（schema_version 1 / 29 host rows / 26 coverage claims / 100 dispositions）· **K-2** PASS（契约外字面量 **0**，扫 8 个声明消费方）· **K-3** PASS（模板行 == 契约 `host.rows[]` = 29）· **K-4** PASS（token 集相等 + 渲染后无 `__…__` 残留）· **K-5** PASS（hook 路径表达式 + 三 hook 读声明 marker）· **K-6** PASS（**exactly-one-insert / no-id-update / no-trust / no-!!js** —— 即 DEC-187 I-1/I-2/I-3 的机检锚）· **K-7 `NOT_RUN`（按设计的三态：`verified_on = null` ⇒ 提示在真实平面跑 `dsh-doctor --record-evidence`）** · **K-8** PASS（26 claims 中 14 strong 各带反相 fixture；守卫引用全部可解析 = 54 测试文件 / 71 段 / 84 命令键）· **K-9** PASS（100 dispositions 恰好覆盖审计基线一次；**72 条必要依赖全部被 claim 覆盖**）· **K-10** PASS（契约入 manifest + 1 个 host-facts fixture + cleanup scope == `PLUGIN_SCOPE_DIRS`）· **K-11** PASS（**allowlist 0/0**，棘轮只降，上界锚在契约外）· **K-12** PASS（**`coverage` 单一生成点且携带 `unreadable_compositions`** —— F-R1-06 义务已兑现；doctor 命令键已注册）· **K-13** PASS（host-facts baseline 成形且在 180 天 TTL 内）。⟦M-2 需在全部切片落地后重跑⟧ |
| 8 | `check-dsh-preset-smoke`（28u） | exit 0 + `real-home writes: 0` | **实测 PASSED**（Coordinator 独立实测 2026-09-13，隔离 `DSH_HOME`）：`Exit code: 0; real-home writes: 0; temp DSH_HOME: …/spg-dsh-smoke-* (removed)`；`Result: PASSED — isolated preset-session smoke PASSED (skill catalog + /governance gesture resolved; real ~/.dsh untouched)`。**⚠️ 门禁抖动登记（如实）**：同日一次运行曾报 `smoke exit 1` + `real-home writes: 1`（差异指纹指向真实 `~/.dsh` 的 `novel-writing` 面）；**连续两次复跑均为 `writes: 0` PASSED** ⇒ 判定为**真实 DSH 会话与冒烟指纹的并发干扰**（隔离失败面之外的 flake），登记为门禁稳定性观察项，**不作本版缺陷**；判据以复跑为准。 |
| 9 | `check-dsh-preset-compat`（28v） | `23 / 18 / 5` + exit 0 + `writes: 0` | **实测 PASSED**（Coordinator 独立实测 2026-09-13，隔离 `DSH_HOME`）：`Compositions: 1; enabled rows: 23; schema-checked rows: 18; NOT verified: 5; inherited-disabled rows: 0; unresolvable-inheritance rows: 0`；`Isolated temp DSH_HOME: …/spg-dsh-compat-home-* (writes: 0)`；oracle 解析自 `DSH_HOME/profiles`（`@deepseek-ai/cordis@4.0.2` / `cordis-plugin-include@1.0.7` / `cordis-plugin-loader@1.0.3` / `js-yaml@4.3.2`），安装态 CLI `0.1.5-rc.1` 仅作 informational；5 行 `NO_SCHEMA` 按 FIX-315 语义以 `[NOT_RUN]` 披露（不得 PASS）。 |
| 10 | 全量测试基线 | 零产品代码回归（**既有失败基线如实披露**，不得写无条件 PASS） | **全量实测（Coordinator 独立实测 2026-09-13；`DSH_HOME` 重定向至 `%TEMP%`）**：命令 `python -m unittest discover -s skills/software-project-governance/infra/tests -t .`；**候选态**（当前工作树，含 0.81.0 bump）`Ran 2983 tests, failures=38, errors=2`（skip=1）；**pristine 基线**（`5e6d8c7` 的临时 worktree，同命令同环境）`Ran 2983 tests, failures=28, errors=9`。**差集逐条归因**：① `test_triage_write_guard.GovernanceWriteGuardPlanTrackerTests.test_live_plan_tracker_flags_only_known_m1_rows` = **真回归**（活体金丝雀数据漂移：FIX-222/223/224 已归档迁出、FIX-279 行形归一）→ **已由 FIX-328 修复，并经 FIX-330 收口**（`test_triage_write_guard.py`：FIX-328 +21/−1 条件 skip；FIX-330 采纳授权候选的方案 (b) `assertEqual(set(), flagged)` 并加面级哨兵门禁，**测试现为 `OK` 且 `skipped=0`**——「活体数据零 M1 命中」是可断言事实而非 skip；FIX-330 同时**经反相实测证伪了 FIX-328/R0 F-1 的「真实灵敏度回退」前提**（不可读分支 `flagged={''}` 非空 ⇒ 改前与 (a) 版都红在 subset 断言，真实缺陷降级为诊断失真），其处置为本版本 1 文件 +63/−5）；② `test_bootstrap_version_marker_injected_into_all_profiles` 与 `test_injection_contract_anchors_include_review_record` = **「版本钉过期」归因经 FIX-328 实验证伪**（二者自 FIX-256/FIX-272 起从 `SKILL.md` frontmatter / `@version-line` 动态锚派生，未改一行；工作树实测二者 **OK**）——其先前失败是「`SKILL.md` 已 bump 而标记面/投影尚未写入」窗口的**瞬时红**（在 `%TEMP%` 副本里回退 `commands/governance-init.md` 标记或 preset 版本行可**逐字复现**当时的失败文本）；③ 其余差集项（`test_the_python_render_is_the_launchers_own_output` 在 pristine 侧失败、`test_host_mode_*`/`test_embedded_*` 在 pristine 侧 error 等）= **pristine 侧**特有，属环境/收集面噪声，**不**升级为候选态回归。**既有失败基线（非本版引入，如实披露，不得写 PASS）**：ⓐ `test_verify_workflow.FIX300DualCaliberAgreementTests` 2 例（`UNSUPPORTED_AFFIRMATIVE` → 历史报告 `docs/reviews/review-FIX-300-CODE-R0.md`，0.66.1 期引入）→ **FIX-320**；ⓑ `test_verify_workflow.LoopRuntimeClaimAdapterTests.test_claim_command_emits_complete_pass_report` 1 例（`check-loop-runtime-claims` 语义面 BLOCKED 族）；ⓒ 环境敏感项（Windows `bash` → wsl.exe；`.governance/` 活体数据依赖）逐条标注为环境/数据耦合，**不计入产品回归**。**Result：零产品代码回归；本批 1 项测试面回归已修（FIX-328）；既有失败基线逐条披露**。**M-2 义务**：FIX-328 落地后 MUST 重取一次全量原始失败清单并逐条贴出（REVIEW-REL-077-CODE-R0 **F-04** 要求），门禁结论以该次重取为准（**已履行**：见 `FIX-328/FIX-330` 的定向复跑与全量差集复核，证据行 EVD-1033/EVD-1034）。**FIX-328 自身 R0 遗留（REVIEW-REL-077-CODE-R1 F-R1-03）**：`REVIEW-FIX-328-CODE-R0 = APPROVED_WITH_NOTES/unresolved_blockers=0`，其 F-1（本批改动引入的测试灵敏度回退：守卫 `plan_tracker_unreadable` 分支 `task_id` 为空 ⇒ 空集断言恒真被 skip 吞掉）/ F-2（(b) 方案排除理由未记录）/ F-3·F-4（P3）→ **FIX-330 返工批**处置。分套件预检（EVD-1030，`DSH_HOME=%TEMP%` 隔离）：`test_registry` 77 OK / `test_dsh_compat` 120 OK / `test_dsh_contract` 120 OK / `test_dsh_adapter` 50 OK / `test_dsh_boundary` 115 OK / `test_dsh_doctor` 70 OK（后两个为 V8 新套件）。 |
| 11 | 三路径渲染 parity | `6caf90fe…e55d`（16796 bytes；相对 0.80.0 差异仅 persona 版本行） | **实测 PASSED（Coordinator 独立实测 2026-09-13，隔离 `DSH_HOME`）**：**三路径渲染 parity 成立** —— `6caf90fec1f2773eaa0128f0fa5c7a7795b512c8a36d603f5cd6e939ff48e55d`（**16796 bytes**；`launch.py` 在两个独立隔离 home 各渲染一次 + JS `renderComposition` 一次，**三者逐字节相同**，JS 侧 `leftovers=[]`）；相对 0.80.0 基线 `00e0d330…3723` 的差异**恰为 persona 版本行 1 处**（`agent-presets/governance/agent.cordis.yml.template` 的 `治理工作流（v0.80.0）` → `（v0.81.0）`，由 `release-projection --write` 写入）——即**版本行变更的必然结果**。实测佐证：把渲染文本中**唯一 1 处** `v0.81.0` 换回 `v0.80.0` 后，sha256 逐字节等于 `00e0d330f3560e10381b54b37a06fe6a626a451e3e70da8126b9c2bc47be3723`（差异行数 = 1）。**措辞纪律**：**不得**表述为「保持 `00e0d330…3723` 不变」。M-2 需在候选打包提交上原样重跑。 |
| 12 | 契约 SHA | `96F92485…43FC6E`（或按 V8 决定后的新值 + 说明） | **实测未变**：`adapters/dsh/host-contract.json` 候选态 sha256 = `96F9248579FCE72592C000D410C0466CBB035D7C7E8D5885941FB6434643FC6E`（**74702 bytes**，`schema_version: 1`；全 40 位对照 `96F92485…43FC6E`）——与 `REVIEW-FEAT-031-CODE-R0/R1` 的硬基线一致，**本版 bump/投影批次未触碰契约字节**。 |
| 13 | `check-release` / `release-ledger` | 发布记录一致 | **部分实测 + 前置依赖显式声明**：① `core/releases/0.81.0.json` 已以 **candidate 态**落地，形态经 R1 逐键裁决正确（与 `8d9110c:core/releases/0.79.0.json` 归一化后**逐字节相等**，494 B）；② `release-ledger --version 0.81.0 --no-remote` 现阶段报 `state: FAIL` + `candidate_commit: expected exactly one commit adding …/0.81.0.json, found 0`，**`trust_level` 已 = `NATIVE_CANDIDATE`** —— R1 裁决此为**预期前置依赖而非缺陷**（`commit_adding_path` 需该文件已入 git 历史；R1 实测该文件 `git ls-files` 为空、`git log -- <path>` = 0 提交）；③ 因此 **M-2 的 ledger 回填义务 = 本候选打包提交（与 `0.81.0.json` 同批）完成后再跑一次**并在本节回填 `state`/`candidate_commit`；④ `check-release --version 0.81.0 --require-changelog --lineage-mode candidate` 以**后台作业**执行（本机实测 240s 无输出，见执行序），其结果同样在候选提交后回填于此。**落库时序（REVIEW-REL-077-CODE-R1 F-R1-02）**：candidate manifest **MUST** 与候选打包提交同批提交——否则 ledger 派生的 `candidate_commit` ≠ 本文档定义的「checklist 冻结提交」。 |
| 14 | 回滚方案 | 已交付且可执行（**回滚区间 = 整个 0.81.0 窗口**） | **已交付且可执行**（`docs/release/rollback-plan-0.81.0.md`；**回滚区间 = `d87ead8..<0.81.0 候选打包提交>`，共 31 commits + 本冻结提交**——实测 `git rev-list --count d87ead8..3074120` = **31**；`d87ead8` = 0.80.0 线 tip，候选打包提交 = 本 checklist 的冻结提交，其 hash 由 M-2 期 `release-ledger --version 0.81.0 --no-remote` 从 git 派生后回填，**不预先编造**。V8 `3074120` / V10 `61b571c` **仅为本区间末两个代表提交，不是区间本身**）——REVIEW-REL-077-CODE-R0 **F-01** 更正：原稿把区间误写为 `61b571c`（V10）+ `3074120`（V8）两个提交，按此 revert 将留下 29 个 0.81.0 提交、回不到 0.80.0 行为。 |

## 真机验收（用户手动三项 —— DEC-190 ⑧）

规程：`docs/release/real-machine-acceptance-0.81.0.md`（三项 + 只读复核命令 + 回贴格式）。
**状态**：⟦待用户回贴⟧。**在回贴之前，本 checklist 与 release 文档 MUST NOT 声明真机项通过**；未回贴项 MUST 标「未验证」。

## M-8 收尾义务

- **补推义务**：`v0.79.0`、`v0.80.0` tag **从未推送** ⇒ 本版 M-7 推送时 MUST 一并补推；
- 发布后：`core/releases/0.81.0.json` **由 candidate 态转为 released 态**（其 **candidate 态随候选打包提交落库**——见 F-R1-02）+ `release-ledger` 核对 + `session-snapshot` 更新 + plan-tracker 版本行转 `released`。

---

*M-1 冻结完成（2026-09-13）。Change Inventory 已按 `git log --oneline d87ead8..3074120` 实测 **31 commits** 关闭——编号 1..31 连续、无重复行、无截断半句；V8（FEAT-031 `3074120`）与 V10（FIX-313 `61b571c`）终态已回填。候选打包 commit 的 hash 待 M-2 期由 `release-ledger --version 0.81.0 --no-remote` 从 git 派生后回填（**该派生要求 `core/releases/0.81.0.json` 已随本候选打包提交入库**——manifest 未入库时 ledger 报 `candidate_commit … found 0`，此为预期前置依赖，REVIEW-REL-077-CODE-R1 F-R1-02）；「Candidate Gate Results」的 M-2 门禁实测与真机三项回贴仍为待办（未回填 / 未回贴项不得视为通过）。*

## M-2 执行序（Coordinator 实测约束）

- **顺序**：先跑只读/廉价门禁（1~5、8~10），再跑**产物生成**类（6 的两次 \--regen\ 必须在所有实现改动落地之后），最后跑 7（Check 28w）与 13（\check-release\）。
- **实测约束（2026-09-13）**：\check-release\ 本机 **240s 超时且无输出** ⇒ M-2 中该门禁 MUST 以**后台作业**（un_in_background\）执行并轮询 \job_output\，不得按普通门禁节奏调度；其余门禁的实测耗时均在 1 分钟内。
- **产物生成类门禁的纪律**：
  - 两次 \--regen\ MUST 给出「前后差异摘要」+「第二次无变化（幂等）」两项证据；
  - 若 \--regen\ 试图写**未授权路径** ⇒ **停下报告**，不得越权写入；
  - 棘轮（6）以**两次 \--regen\ 之后**的状态为准。
- **真机项（第 14 行之外的独立交付面）**：由用户在真实 dsh 环境手动执行三项并回贴；**回贴前严禁在任何 release 文档/CHANGELOG 中声明真机项通过**。
- **冻结纪律**：M-1 冻结前 MUST 把 Change Inventory 的 \⟦待落地⟧\/\⟦待回填⟧\ 占位**全部消除**（V8/V10 的 commit hash 与终态），否则不得进入 M-2。

### dsh-doctor 预检（Coordinator 独立实测 2026-09-13，V8 在制品状态下）

**CLI 接口**（实测 `--help`）：`--json` / `--stage S0..S7` / `--offline` / `--selftest` / `--record-evidence` / `--out` / `--rehearse CANDIDATE.json` / `--against BASELINE.json` / `--allow-host-probe` / `--fail-on-issues` —— 与设计 §5 的 S0~S7 + 四开关一致。

**`dsh-doctor --offline --selftest` → `Result: PASS`（exit 0）**，且 8 个阶段逐条演示了**阶段级崩溃隔离**：

```
ok   S0: crashed=NOT_RUN/stage_error=True stages=8 verdict=PASS exit=0
ok   S1: crashed=NOT_RUN/stage_error=True stages=8 verdict=PASS exit=0
ok   S2..S7: crashed=NOT_RUN/stage_error=True stages=8 verdict=FAIL exit=1
```

⇒ ① 某个阶段崩溃时**该阶段降级为 `NOT_RUN` 而非整体崩溃**，其余 7 个阶段照常执行（`stages=8`）；② 退出码三态语义正确（健康 `0` / 可行动失败 `1`）；③ `--offline` 生效。这正是设计 §5 与 BT「诊断入口本身失败时的降级」的要求。

## 验收① 证据形态披露（FIX-313 / V10，Honesty Note）

`REVIEW-FIX-313-CODE-R0` 判 **F1（P1）**：设计 §6.1 V10 的**验收①（G-04：`resolveDshHome()` 抛错路径下 CWD 的 `governance.staging-*` 不被删除）没有任何机器守卫**——审查方以**部分回归变异 M5** 证明：整个 adapter 套件 **50 项全绿而 CWD 误删依旧发生**。

**Coordinator 采处置路径②（显式记录 + 登记跟进）**：

1. **本版验收①由外部证据成立**：审查方在 `%TEMP%` 副本内以 **ESM `registerHooks` 故障注入**端到端复现（场景 S2/S3/S4），给出修前 RED / 修后 GREEN 对照——**证据可复现**，但**不是**随仓库交付的机器守卫。
2. **机器守卫登记为 `FIX-325`**（补 CWD 反相 fixture；Windows 需 Node ≥22.15，仓声明 engines≥20 ⇒ 需 skip/NOT_RUN 政策；建议同时把零捕获力的自证式用例改写为碰撞 guard，一次关闭 F1/F2/F3）。
3. **⚠️ 硬约束（审查方明确要求）**：本清单、`project/CHANGELOG.md` 与任何发布注记 **MUST NOT 声称「验收① 有测试守卫」**——那是不实陈述。准确表述只能是「**由独立审查的故障注入复现成立，机器守卫待 FIX-325**」。
4. **规模注记（F7）**：V10 实际改动面 **+66/−13 行**（设计稿估为 1-3 行）；发布注记 MUST 按实际改动面描述。超出设计下限属**必要扩展**——修前的前置 `rmSync` 本身具破坏性，不做换名重试无法达成「只删已证明属己」。
5. **权衡登记（F4）**：V10 修复后**失去唯一的孤儿 staging 目录 GC 路径** ⇒ `<dshHome>/.agent-presets/` 内崩溃遗留的孤儿会累积。这是 **P7（安全）优先于整洁**的有意取舍；机器守卫与权衡文档化一并归 `FIX-325`。
