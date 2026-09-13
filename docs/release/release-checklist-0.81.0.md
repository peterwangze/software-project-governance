# Release Checklist — 0.81.0 (REL-077)

- **状态**：**M-1 草稿**（2026-09-13）。`⟦待 V8 回填⟧` 项在 FEAT-031 与 FIX-313 落地后补齐，随后进入 M-2 门禁实测。
- **版本**：0.81.0（**dsh 宿主兼容性体系化**）｜前置稳定版 **0.80.0**（tag `v0.80.0`）｜候选打包 commit：`⟦待 M-1 冻结⟧`
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
| **实现 V8** | **FEAT-031**（Check 28w K-1~K-13 + `dsh-doctor` S0~S7 + `host-facts` 升级演练 + registry 接线 + 两次 `--regen`） | 0.81.0 ⟦待回填⟧ |
| **实现 V10** | **FIX-313**（`lib/index.js` catch 清理退化：防误删 CWD 同名目录） | 0.81.0 ⟦待回填⟧ |
| **并行收口** | FIX-319（Check 18c 粗体误报）+ FIX-321（粗体剥离 run 边界守卫；FIX-319 遗留 F-01） | 0.81.0 |
| **发布治理面** | 真机验收规程、版本规划（含 M-2 前置预检）、回滚方案、特性开关、本 checklist、`core/releases/0.81.0.json` | 0.81.0 |
| **风险挂载** | **RISK-050**（dsh 上游内部面耦合；截止 2026-10-31）。本版把**依赖面枚举 + 契约化 + 零校验门禁 + 单点诊断 + 升级演练**前移，**不声明关闭** | 0.81.0 |
| **如实披露的既有失败** | `check-loop-runtime-claims` 语义面 **BLOCKED**（3 条 `UNSUPPORTED_AFFIRMATIVE` 全在**既有** `docs/reviews/review-FIX-300-CODE-R0.md`，0.66.1 期引入）→ **FIX-320**（本版处置 = 如实披露） | 0.81.0 披露 |

## Change Inventory（19 commits — `git log --oneline d87ead8..HEAD`，2026-09-13 核定）⟦待 V8/FIX-313 落地后追加⟧

| # | 任务 | commit | 终态要点（审查终态 + EVD） |
|---|---|---|---|
| 1 | FEAT-029 / **V1** | `4d93b24` | 契约本体 `host-contract.json`（2456 行）+ `dsh_contract.py`（4 API + 3 异常类）+ 自校验测试 + 夹具发射器；EVD-1011 |
| 2 | AUDIT-153 + FEAT-028 | `4dfde66` | 依赖面清点 801 行 + ADR-018 + 设计规格 1023 行 + R0/R1 审查报告；EVD-1009/1010 |
| 3 | FEAT-029 R0 报告 | `97f0d38` | **APPROVED_WITH_NOTES / 0** |
| 4 | FEAT-030 R0 报告 | `6081285` | NEEDS_CHANGE / 1（P0 F-01 + P1×2） |
| 5 | **FIX-317** | `ba210b9` | V1 审查收口：编码分类 / `recorded` 值校验 / 切片归属 / 覆盖声明；**REVIEW-FIX-317-R0 APPROVED_WITH_NOTES/0**；EVD-1015 |
| 6 | FIX-317/FIX-315 R0 报告 | `8bd4d60` | 两份报告入库 |
| 7 | REL-077 规程 | `135e7df` | 真机验收规程（DEC-190 ⑧ 执行载体） |
| 8 | **FIX-315 / V3** | `b35d1d6` | 零校验不得 PASS（G-01 a~e）；R0 NEEDS_CHANGE/1 → **R1 APPROVED_WITH_NOTES/0**；EVD-1016/1017 |
| 9 | REL-077 文档修复 | `3059aae` | 起草文档 ragged table 修复 + 身份门禁残余阻塞归因（→ FIX-320）；EVD-1018 |
| 10 | **FIX-319** | `3fb90fe` | Check 18c 粗体误报（判据层 3/3 消除 + 9 条反证全 FAIL + 192 条穷举 0 例外）；**APPROVED_WITH_NOTES/0**；遗留 F-01 → FIX-321；EVD-1019 |
| 11 | **FEAT-030 / V2** | `3c37342` | 消费方改读契约（行为保持）+ K-2 扫描；R0 NEEDS_CHANGE/1 → 返工 → **R1 APPROVED_WITH_NOTES/0**（含 N-1 微补）；EVD-1020 |
| 12 | **FIX-321** | `6e3c828` | 双侧 run 边界守卫（放宽面穷举命中 **0**）；**APPROVED_WITH_NOTES/0**；EVD-1021 |
| 13 | **FIX-311 / V4** | `85fb309` | group 语义对齐 loader + G-18 分类自检 + F-R1-03；三处请裁决项全部背书；**APPROVED_WITH_NOTES/0**；EVD-1022 |
| 14 | **FIX-316 / V5+V6+V7** | `2d66d0f` | 渲染解码守卫 + `DSH_HOME` 收敛（20 例 0 分歧）+ 版本证据看护 + **写入守卫对称化**；R0/2 → R1/1 → **R2 APPROVED_WITH_NOTES/0**；EVD-1023/1024/1026 |
| 15 | REL-077 设计同步 | `1c2dc0a` | F-R1-06：`coverage.unreadable_compositions` 补入 G01-b 与 §5.1 S2 投影 + 约束段；EVD-1027 |
| 16 | REL-077 版本规划 | `0060844` | M-2 前置门禁预检（3 项 bump 前已 PASSED；bump 后 MUST 重跑） |
| 17 | REL-077 回滚方案 | `af2b58c` | 回滚影响分类 + 程序 + 数据安全论证 + 7 项验证 + 基线按 `d87ead8` 实测核定 |
| 18 | REL-077 特性开关 | `c15f6df` | 新增 opt-in 开关**为零**；两项行为变更 B-1/B-2；加性检查面 3 项 |
| 19 | **FEAT-031 / V8** | `⟦待落地⟧` | Check 28w + `dsh-doctor` + `host-facts` + 接线 + 两次 `--regen`；⟦待回填⟧ |
| 20 | **FIX-313 / V10** | `⟦待落地⟧` | `lib/index.js` 清理路径所有者判据；⟦待回填⟧ |

## 行为变更（面向用户 —— MUST 出现在 CHANGELOG 与升级说明）

详见 `docs/release/feature-flags-0.81.0.md` §2：
- **B-1** `--install` 对缺失/不可读 `package.json`：`rc 0`（写占位 `"0"`）→ **`rc 1` 拒绝**；
- **B-2** 真实 home 形态的 `DSH_HOME` 下 `--install`/`--sync`/`--uninstall`：可用 → **`exit 2` + `[REFUSED]`**（`--dry-run` 仍放行）。

## Candidate Gate Results（M-2 —— Coordinator 回填实测）
⟦待实施切片全部落地后填写⟧

| # | Gate | 预期 | Result |
|---|---|---|---|
| 1 | `check-version-consistency` | PASS（bump 后全投影 = 0.81.0） | ⟦待回填⟧（bump 前预检 **PASSED**） |
| 2 | `check-projection-sync --fail-on-issues` | PASS | ⟦待回填⟧（bump 前预检 **PASSED**） |
| 3 | `check-injection-contract --fail-on-issues` | PASS | ⟦待回填⟧（bump 前预检 **PASSED**） |
| 4 | `check-manifest-consistency --fail-on-issues` | PASS | ⟦待回填⟧ |
| 5 | `cleanup.py --dry-run` | 零删除 | ⟦待回填⟧ |
| 6 | `archguard-ratchet`（**两次 `--regen` 后**） | 无新增 ERROR | **预检 PASSED（Coordinator 独立实测 2026-09-13，V8 在制品状态下）**：`R1 PASS mainfile loc 24405 ≤ anchor 24405（only-down）`、`R2 PASS reverse-dep 47 ≤ 47`、`R3 PASS matrix 12 edges`、`R4 PASS print 1299 ≤ 1299`、**`R5 PASS cli keys 84/84 frozen, segments 71/71 frozen`**（含 Check 28w 段）、`R6 INFO cold import 196（Δ0，advisory）`、**`R7 PASS regen deterministic=True; committed==fresh True`**（即两次 `--regen` **幂等**）；`Result: PASS (0 violations; raw findings before exemptions: 0) — fatal gate green`。⟦M-2 需在全部切片落地后重跑⟧ |
| 7 | **Check 28w** `check-dsh-boundary`（V8 交付） | PASS / 或如实披露豁免 | **部分预检**：`archguard-ratchet` 的 `R5` 已确认 **Check 28w 段已注册并被冻结**（`segments 71/71 frozen`）；28w 自身的判据面 PASS/FAIL ⟦M-2 回填⟧ |
| 8 | `check-dsh-preset-smoke`（28u） | exit 0 + `real-home writes: 0` | ⟦待回填⟧ |
| 9 | `check-dsh-preset-compat`（28v） | `23 / 18 / 5` + exit 0 + `writes: 0` | ⟦待回填⟧ |
| 10 | 全量测试基线 | 无新增失败（**既有失败基线如实披露**） | ⟦待回填⟧ |
| 11 | 三路径渲染 sha256 | `00e0d330…3723` 不变 | ⟦待回填⟧ |
| 12 | 契约 SHA | `96F92485…43FC6E`（或按 V8 决定后的新值 + 说明） | ⟦待回填⟧ |
| 13 | `check-release` / `release-ledger` | 发布记录一致 | ⟦待回填⟧ |
| 14 | 回滚方案 | 已交付且可执行 | **已交付**（`rollback-plan-0.81.0.md`；`⟦待 V8 回填`区间`⟧`） |

## 真机验收（用户手动三项 —— DEC-190 ⑧）

规程：`docs/release/real-machine-acceptance-0.81.0.md`（三项 + 只读复核命令 + 回贴格式）。
**状态**：⟦待用户回贴⟧。**在回贴之前，本 checklist 与 release 文档 MUST NOT 声明真机项通过**；未回贴项 MUST 标「未验证」。

## M-8 收尾义务

- **补推义务**：`v0.79.0`、`v0.80.0` tag **从未推送** ⇒ 本版 M-7 推送时 MUST 一并补推；
- 发布后：`core/releases/0.81.0.json` 落库 + `release-ledger` 核对 + `session-snapshot` 更新 + plan-tracker 版本行转 `released`。

---

*草稿结束（M-1）。`⟦待回填⟧` 项在 FEAT-031 / FIX-313 落地、M-2 门禁实测、真机回贴后补齐。*

## M-2 执行序（Coordinator 实测约束）

- **顺序**：先跑只读/廉价门禁（1~5、8~10），再跑**产物生成**类（6 的两次 \--regen\ 必须在所有实现改动落地之后），最后跑 7（Check 28w）与 13（\check-release\）。
- **实测约束（2026-09-13）**：\check-release\ 本机 **240s 超时且无输出** ⇒ M-2 中该门禁 MUST 以**后台作业**（un_in_background\）执行并轮询 \job_output\，不得按普通门禁节奏调度；其余门禁的实测耗时均在 1 分钟内。
- **产物生成类门禁的纪律**：
  - 两次 \--regen\ MUST 给出「前后差异摘要」+「第二次无变化（幂等）」两项证据；
  - 若 \--regen\ 试图写**未授权路径** ⇒ **停下报告**，不得越权写入；
  - 棘轮（6）以**两次 \--regen\ 之后**的状态为准。
- **真机项（第 14 行之外的独立交付面）**：由用户在真实 dsh 环境手动执行三项并回贴；**回贴前严禁在任何 release 文档/CHANGELOG 中声明真机项通过**。
- **冻结纪律**：M-1 冻结前 MUST 把 Change Inventory 的 \⟦待落地⟧\/\⟦待回填⟧\ 占位**全部消除**（V8/V10 的 commit hash 与终态），否则不得进入 M-2。

## 验收① 证据形态披露（FIX-313 / V10，Honesty Note）

`REVIEW-FIX-313-CODE-R0` 判 **F1（P1）**：设计 §6.1 V10 的**验收①（G-04：`resolveDshHome()` 抛错路径下 CWD 的 `governance.staging-*` 不被删除）没有任何机器守卫**——审查方以**部分回归变异 M5** 证明：整个 adapter 套件 **50 项全绿而 CWD 误删依旧发生**。

**Coordinator 采处置路径②（显式记录 + 登记跟进）**：

1. **本版验收①由外部证据成立**：审查方在 `%TEMP%` 副本内以 **ESM `registerHooks` 故障注入**端到端复现（场景 S2/S3/S4），给出修前 RED / 修后 GREEN 对照——**证据可复现**，但**不是**随仓库交付的机器守卫。
2. **机器守卫登记为 `FIX-325`**（补 CWD 反相 fixture；Windows 需 Node ≥22.15，仓声明 engines≥20 ⇒ 需 skip/NOT_RUN 政策；建议同时把零捕获力的自证式用例改写为碰撞 guard，一次关闭 F1/F2/F3）。
3. **⚠️ 硬约束（审查方明确要求）**：本清单、`project/CHANGELOG.md` 与任何发布注记 **MUST NOT 声称「验收① 有测试守卫」**——那是不实陈述。准确表述只能是「**由独立审查的故障注入复现成立，机器守卫待 FIX-325**」。
4. **规模注记（F7）**：V10 实际改动面 **+66/−13 行**（设计稿估为 1-3 行）；发布注记 MUST 按实际改动面描述。超出设计下限属**必要扩展**——修前的前置 `rmSync` 本身具破坏性，不做换名重试无法达成「只删已证明属己」。
5. **权衡登记（F4）**：V10 修复后**失去唯一的孤儿 staging 目录 GC 路径** ⇒ `<dshHome>/.agent-presets/` 内崩溃遗留的孤儿会累积。这是 **P7（安全）优先于整洁**的有意取舍；机器守卫与权衡文档化一并归 `FIX-325`。
