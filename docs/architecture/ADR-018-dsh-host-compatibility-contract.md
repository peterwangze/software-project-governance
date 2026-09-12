# ADR-018: DSH 宿主兼容性契约层 / 依赖最小化 / 校验看护 / 边界可调测（0.81.0）

- **Status**: Proposed（**R0 = NEEDS_CHANGE（3 P1 / 5 P2 / 10 P3+NOTE + 4 条新增蓝军）；本版已逐条修订，待 R1 复审**——R0 报告 `docs/reviews/review-FEAT-028-DESIGN-R0.md`，处置索引见设计正文 §11；本 ADR 的设计正文见 `docs/requirements/dsh-compat-design-0.81.0.md`）
- **Date**: 2026-09-13
- **Version**: 0.81.0（MINOR）
- **Author**: Architect（FEAT-028 设计；Design Reviewer 后置审查）
- **Deciders**: Coordinator → 用户（M-0 版本范围裁决 = O-1；架构不变量以外无用户强约束）
- **Scope**: REQ-146 / REQ-147 / REQ-148 / REQ-149（用户 2026-09-13 四条硬要求）
- **事实输入（唯一）**: AUDIT-153 = `docs/requirements/dsh-host-dependency-inventory-0.81.0.md`（801 行，HEAD `d87ead8`，2026-09-13）
- **设计正文**: `docs/requirements/dsh-compat-design-0.81.0.md`（本 ADR 的展开；本文件只记录**决策**与**排除**）
- **Supersedes / continues**: 不替换 ADR-017；延续 DEC-187（宿主方架构不变量 I-1/I-2/I-3）、DEC-188 ②（机检判据口径）。执行 AUDIT-153 的下游约束 C-1~C-25，并作为 FIX-315 / FIX-311（G-02/G-03）/ FIX-316 / FIX-313 的**设计授权输入**（实现授权另由 M-0 裁决）
- **Related**: RISK-050（dsh 上游内部面耦合）、`docs/release/release-checklist-0.80.0.md:137`（`dsh_compat.py` 归属未裁决）、`core/protocol/plugin-contract.md:248-266`（I-1/I-2/I-3 承诺与判据）

---

## 1. Background（背景）

### 1.1 触发事实

| 项 | 内容 | 证据 |
|---|---|---|
| 用户诉求 | dsh 升级适配后出现**大量兼容性问题**；需要"针对插件的兼容性设计进行系统性的分析设计和实现"，四条硬要求 = ①尽可能减少对 DSH 宿主的依赖 ②必须的接口/字段依赖解耦、单独维护 ③依赖代码严格校验与看护 ④依赖边界增加可调测性 | 用户 2026-09-13 指令；`plan-tracker.md:583-586` 的 REQ-146~149 原文 |
| 事实清点 | 100 个依赖点（必要 62 / 可弱化 26[表体 25 行 36 ID] / 可消除 4 / 历史 3）；看护盲区 B-1~B-10；缺口 G-01~G-18（9 条已实测复现）；可调测性 S0~S7 中**仅 S2/S6 自动化**，S4 无路径；T-1~T-10 需真机；约束 C-1~C-25 | AUDIT-153（全文） |
| 最近事故 | `@deepseek-ai/dsh-persona` 的 config 键由 `prefix` 变更导致**整棵预设挂载被否决**（真机 `entries 0 → 1`），CI 与 `verify_workflow.py` 全未拦截 | AUDIT-153 头注 + release-checklist:43（FIX-308） |
| 未关闭风险 | RISK-050（dsh 上游内部面耦合）：0.80.0 消除"UPDATE 宿主行 + `!!js` 自定位"一条腿，**另一条腿未消除**——组合仍绑定 23 个 `@deepseek-ai/dsh-*` 行的 Config schema | release-checklist:17、142 |
| 既有偏差 | `dsh_compat.py` 位于 core `infra/` 而职责是 dsh 专属 ⇒ core→dsh 耦合**未裁决** | release-checklist:137 |
| 行集口径（**R0 F-1 修正**） | 预设模板的**平台无关行全集 = 29**（顶层 16 + 嵌套 13），其中 group 3、`disabled: true` 2、平台条件 2 ⇒ 任一平台 enabled = 23、`rows_checked` = 18；含 `config:` 的行 = 17 | 设计正文 §0.2 E-10（逐行复算；旧表述的 28/18 属漏项与误推，已在原处标注新旧差异） |
| 接线冻结面（**R0 F-2 补全**） | 新增段 28w 与新命令 `dsh-doctor` 牵动 5 个未声明的冻结面：`registry.py` 导入期 join（`quickscan_registry.SEGMENTS`）、`test_registry.py` 的 `FROZEN_CLI_KEYS=82`/`FROZEN_SEGMENTS=70`/`migrated` 精确列表、`contract_matrix/snapshots.json`、`core/architecture-baseline.json`（含 `expire_version: "0.81.0"` 的 R1 豁免到期） | 设计正文 §0.2 E-17~E-20；§2.9.4 |

### 1.2 问题的结构性本质（本 ADR 的判断）

三个结构性成因，各自对应一条用户要求：

1. **宿主事实散落**：dsh 的包名/行 id/config 键/路径/环境变量/上游 API 锚点分散硬编码在 `lib/index.js`、`adapters/dsh/launch.py`、`infra/dsh_compat.py`、模板、hooks、manifest 六处（AUDIT-153 §4 盲区 B-1/B-3/B-7/B-10）⇒ 无法"单独维护"（REQ-147）。
2. **结论大于证据**：护栏对 5/23 行**零校验却报 PASS**，且该 PASS 分支在屏幕上完全不显示该事实（G-01）⇒ "严格看护"名不副实（REQ-148 / C-6）。
3. **不可调测**：一次升级后出问题需要"2 个自动化步 + ≥3 个手工步"，且"PASS 但用户仍失败"**今天无路径**（§6.1 S4）⇒ 无法"第一时间发现、低代价适配"（REQ-149）。

### 1.3 既有资产边界（不可破坏的约束）

| # | 不变量 | 依据 |
|---|---|---|
| B-1 | **零运行时依赖**：`lib/index.js` 的零 import 设计是宿主安全不变量（module-load 失败不得拖垮 dsh boot） | `lib/index.js:92-97`；AUDIT-153 §3.1 反面证据；C-1 |
| B-2 | **warn-only / `apply()` 永不抛** | `lib/index.js:184-187, 227-238`；CODE R0 F2（release-checklist:118） |
| B-3 | **零侵入**：不得新增 `- id: <host row>` UPDATE、`disabled: false` 覆写、宿主平面注册、`!!js` 自定位、`trust: system` | DEC-187 I-1/I-2/I-3；C-2；`plugin-contract.md:256-266` |
| B-4 | **三态政策**：`PASS`/`FAIL`/`NOT_RUN`；`NOT_RUN` 披露未验证事实、不计 gate issue、绝不等于 PASS | `dsh_compat.py:75-77`；C-7 |
| B-5 | **单源交付**：`agent-presets/governance/` 是唯一预设载荷；两条渲染路径（JS/Python）输出字节一致 | FIX-310/DEC-187；AUDIT-153 §2.7 三路径 sha256 实测全等 |
| B-6 | **结构不变量**：`PLUGIN_SCOPE_DIRS` ≡ `cleanup_scope.directories`；`canonical_product_artifacts` 覆盖 dsh 面产物；dsh 面版本串各有一条投影；`LOADER_WHITELIST` 闭集；**以及接入冻结面**（`quickscan SEGMENTS` ↔ `_SEGMENT_LOADERS` 导入期相等、`FROZEN_*` 计数、`contract_matrix/snapshots.json`、`archguard-ratchet` 基线 R7 已提交==fresh） | C-8 / C-9 / C-10 / C-12 / C-14 / C-15（`cleanup.py:46-63,75-114`；`registry.py:182-198,620-633,658`；设计正文 E-17~E-20） |
| B-7 | **C-25 纪律**：AUDIT-153 §7 的 R-01~R-19 未验证项不得当事实使用 | C-25 |

---

## 2. Decision（决策）

### D-1 建立**单一事实源**的机器可读宿主机契约（解决 REQ-147）

- 载体：JSON 数据文件 **`adapters/dsh/host-contract.json`**（`schema_version` + 四个命名空间：`host.*` 宿主事实 / `own.*` 本包 parity 约定 / `evidence.*` 版本证据 / `coverage.*`+`elimination.*` 看护与归并声明）。
- 访问器：**`skills/software-project-governance/infra/dsh_contract.py`**（纯 stdlib 加载与校验，**不做任何宿主探测**）。
- 消费方全部改读契约：`lib/index.js`（懒读，见 D-3）、`adapters/dsh/launch.py`、`infra/dsh_compat.py`、`verify_workflow.py`（结构化替代文本正则）、模板与 hooks（**静态等式判据**，见 D-4）、`adapters/dsh/adapter-manifest.json`（证据面）。
- 机检：新增 **Check 28w `check-dsh-boundary`**（**K-1 / K-3~K-13** 判据，见设计正文 §2.8；**K-2 的文本扫描提前到 V2**，R0 BT-R-01），核心两条 =「契约外硬编码字面量 → FAIL（豁免通道受 K-11 约束）」+「模板行集（**平台无关全集 29 行**）/ token 集 ↔ 契约双向一致」（R0 F-1）。
- **可逆性标注**：**可逆**（迁移到 `core/` 的成本 ≤3 处、无逻辑变更；见 D-2 与设计正文 §9 U-6）。

### D-2 契约放置在**适配层**（`adapters/dsh/`），并显式登记一条 core→adapter 数据边

- 理由（设计正文 §2.3 P-1~P-4）：语义归属（宿主事实属适配层）；结构性成本为零（`adapters/` 已在 cleanup 范围与 `files` 白名单内；JSON 不进 `LOADER_WHITELIST`）；不进技能树/投影申报面；迁移可逆。
- **如实登记的成本**：core `infra/` 读取 `adapters/dsh/host-contract.json` 形成一条 **core→adapter 数据边**，与既有 `dsh_compat.py` 归属偏差（release-checklist:137）**同类**。本设计把它收窄为"一个访问器 + 一个数据文件"（今天 = 3 模块约 30 处硬编码），并在 `dsh_compat.py` 归属 DEC 中一并复审（§5 后续动作 A-3）。
- **可逆性标注**：**可逆**（两个方向迁移都只改路径常量）。

### D-3 保护 JS 侧五条不变量（解决 C-1 风险面）

`lib/index.js` 改造 MUST 同时满足：J-1 零运行时依赖；J-2 warn-only/永不抛；J-3 **顶层零 I/O**（契约读取收敛到模块级 memoized `contractTokens()`，由 `ensurePreset()` 与 `renderComposition()` 两个**函数内**读取点调用——`test_dsh_adapter.py:1138-1156` 直调后者，R0 F-3；顶层同步读会把"缺一个文件"升级为"宿主行 import 失败"）；J-4 **不保留内联回退副本**（保留即第二事实源，违背 REQ-147；契约不可读时跳过同步 + warn）；J-5 导出面与 `renderComposition` 签名不变；J-6 三路径渲染 parity 不变；J-7 幂等标记语义不变。
- **可逆性标注**：**不可逆（语义承诺）**——J-1~J-7 是对宿主的公开承诺，后续变更需新 DEC。

### D-4 依赖最小化：逐条裁决，不以"真依赖"换取"消除"

- §3.1 可消除 4 条：`D-02` 消除（确认不存在 + 契约登记防回流）、`D-50`+`D-56` 消除（删死分支与 2 个 stdlib import，保留一行显式诊断）、`D-05` **弱化**为机器校验的版本闸门（`evidence.compat_range`），**不加** `peerDependencies`。
- §3.2 可弱化 36 个 ID：逐 ID 裁决（设计正文 §3.3），其中 `登记不修` 仅 `D-90/D-93`。
- **执行 AUDIT-153 的反面证据**：`@deepseek-ai/dsh-home-paths` **不得**成为真依赖（D-16/D-47 一律走"契约化 + 三方差分校验"）。
- **可逆性标注**：**可逆**（逐切片 revert）。

### D-5 看护：把"零校验不得 PASS"做成**结构上不可表达**的不变量（解决 REQ-148 / C-6 / C-21）

- 裁决式新增：`rows_checked == 0 ⇒ verdict = NOT_RUN`（永不 PASS）；报告新增结构化 `coverage` 块（**单一生成点** = `check_dsh_preset_compat()`，doctor 只投影不重算）；PASS 分支按 **`kind`**（而非字符串 `"NOT verified"`）逐行披露未校验行；PASS reason 必须带分母（`verified X of Y enabled rows`）。
- 「可信面 ≤ 校验面」的机检形式：契约为每个条目声明 `target` 强度 + 守卫引用 + 反相 fixture 引用（**双键 `subject`（契约 JSON path）+ `audit_ids[]`（D-nn）**，R0 F-14）；Check 28w 断言 **`strong` 必有反相 fixture、`necessary` 条目不得 `none`、守卫引用必须可解析（解析发生在 `checks/dsh_boundary`，R0 F-15）、`audit_ids` 并集覆盖 62 条必要依赖** ⇒ "声明强于佐证"在结构上不可表达。
- **豁免通道受约束（R0 BT-R-01）**：`allowlist` 每条须含 `reason` + `since_slice`，条数受棘轮预算（K-11，只降不升）；**K-2 提前到 V2** 使"半迁移期"仍有机检。
- **单一裁决一致（R0 BT-R-02）**：doctor 的 S3/S7 MUST 消费 K-7 的结果而非自算；新增 K-12 断言 `dsh-doctor` 顶层 verdict 与 `check-dsh-boundary` 退出码一致。
- 缺口修复设计（逐条判据与 loader 真实语义对齐）：**G-01**（FIX-315）、**G-02/G-03**（FIX-311）、**G-05 / G-07 / G-10**（FIX-316）、**G-06**（FIX-316 / D-16/D-47；**写入侧与探测侧拆分**，R0 F-6）、**G-11/G-12**（C-20）。**C-23 处置 = 改测试**（`test_dsh_compat.py:365`、`:754` 变红属**预期**，且必须在同一提交内改写为新语义断言）。
- **可逆性标注**：**不可逆（语义承诺）**——三态语义与"零校验不得 PASS"不得回退（回退即重犯 G-01）。

### D-6 可调测性：单一诊断入口 + 离线 fixture + 升级演练（解决 REQ-149 / C-16 / C-17 / C-22）

- 命令：**`dsh-doctor`**（registry 命令键；`--json/--stage/--offline/--record-evidence/--rehearse/--allow-host-probe/--selftest`），分 S0~S7 阶段，每阶段机器可读 `verdict + credible_face + evidence + remediation`；退出码 `0/1/2`（与 `--smoke` 的 0/1/2 一致）。
- T-1~T-10 逐条处置：**离线化**（T-8 `npm pack` 面、T-9 witness 弱化、T-10 既有）、**fixture 冻结**（T-1/T-2 授权运行时记录前后态）、**显式 `NOT_RUN` 披露**（T-3~T-7）。
- 升级演练：`host-facts-<version>.json`（记录态宿主事实 + schema 形状冻结）→ `--rehearse <new> --against <baseline>` 差分 → 4 个合成突变作为"演练机制自身"的反相 gate。**基线自身受约束（R0 BT-R-03，K-13）**：同版本 no-op **FAIL**、`captured_at` 严格递增、baseline 纳入 TTL、条目级 `synthetic: true/false` 标记且 synthetic 不得用于判定"升级安全"。**诚实边界**：演练不能替代真机（T-1/T-2），且"下一次升级先看到"的前提是有人在新版 dsh 上跑一次 `--record-evidence`。
- **可逆性标注**：**可逆**（新增入口，无既有依赖；revert 即移除）。

### D-7 实施切片：10 个垂直切片，串行链在三个核心文件上

- V1 契约数据层 → V2 消费方迁移（行为保持 + K-2 文本扫描前置）→ V3 零校验门禁 / V4 group 语义 / V5 渲染与解码面 / V6 `DSH_HOME` 收敛 / V7 版本证据 / V8 边界门禁 + 诊断入口（**含接线冻结面与棘轮**）→ V9 发布面收尾；V10（候选）= G-04/FIX-313(b) 安全面修复。
- 并行安全：`dsh_compat.py` / `launch.py` / `lib/index.js` 构成串行链（DSH 无 worktree 隔离）；**V8 额外独占** `quickscan_registry.py` / `test_registry.py` / `contract_matrix/snapshots.json` / `core/architecture-baseline.json`（冻结面 + `--regen` 驱动，R0 F-2）；可并行波次与 V8 内部步骤顺序见设计正文 §6.2。
- **可逆性标注**：**可逆**（切片彼此独立、单关注点，逐个 revert）。

---

## 3. Alternatives Considered（备选方案与排除理由）

### 3.1 体系级备选（≥2 个候选）

| 方案 | 描述 | 优点 | 缺点 | 裁决 |
|---|---|---|---|---|
| **A（采用）** | 契约层 + 逐条最小化 + 零校验门禁 + 单一诊断入口 四件套（D-1~D-7） | 四条要求各有落点；契约与判据都可机检；诊断入口把"升级后排查"从手工链变为一条命令 | 引入 3 个新模块与 1 个新数据文件；核心文件串行链较长 | **采用** |
| B：只做"最小化"，不做契约层 | 逐条消除/弱化，但不建单一事实源 | 改动最小、风险最低 | 直接违背 REQ-147；散点硬编码正是缺陷本身（B-10）；无法机检"契约外出现 → FAIL" | **排除**：不满足用户要求 ② |
| C：用真依赖消除重复实现 | 把 `@deepseek-ai/dsh-home-paths` 等加为真依赖，复用上游实现以消除三方分歧 | 从根上消除"实现分歧" | ① 违反 B-1（宿主安全不变量：module-load 失败即拖垮 boot）；② AUDIT-153 §3.1 **明确的反面证据** | **排除**：不采纳——以"契约化 + 三方差分校验"替代（理由见 C-1 与 AUDIT-153 §3.1 反面证据）。<br>**R0 F-9 更正**：本条原写作"与 DEC-187 I-3 的方向相反"，与 `plugin-contract.md:254`（I-3 明许 import 公开包 / 消费公开服务 / 声明 `peerDependencies`）**相反**，已删除该表述——引入上游包**不**产生宿主→本插件的反向依赖，理由①②已充分 |
| D：契约由上游 dsh 提供 | 只消费 dsh 发布的官方契约/schema 清单 | 单一事实源在上游、最权威 | 今天不存在此类工件；本插件无法驱动 dsh 发布节奏 ⇒ 不可交付；且"上游给了什么"本身仍是我们要适配的事实 | **排除**：不可交付（无证据表明上游存在该工件） |
| E：运行时动态探测替代静态契约 | 每次运行从安装态 dsh 读取契约 | 永远最新 | ① CI 门禁退化为运行时依赖；② 无安装/无 node 时结论全面 NOT_RUN（看护面反而扩大）；③ 与 warn-only 冲突（运行时要读文件、失败要降级） | **排除**：与 REQ-148「严格看护」相反 |

### 3.2 契约载体备选

见设计正文 §2.2：F-JSON（采用）/ F-PY（排除：JS 无法消费 ⇒ 必然第二事实源）/ F-YAML（排除：Python 侧无硬依赖解析器；`js-yaml` 属宿主平面，作为依赖即引入依赖）/ F-MD（排除：需解析围栏，双格式易漂移）。

### 3.3 契约放置备选

见设计正文 §2.3：`adapters/dsh/`（采用，D-2）；`core/`（排除：语义归属错位 + 进入技能树/投影申报面 + 与待裁决归属相互锁定）；包根（排除：需三处同步且无分层归属）；`infra/`（排除：固化进 core，且 `infra/` 在投影清单内）。

### 3.4 诊断入口命名与形态备选

见设计正文 §5.1：`dsh-doctor`（采用）；扩展 `check-dsh-preset-compat`（排除：gate 与诊断混一入口、退出码语义冲突）；新建 `check-dsh`（排除：与 28u/28v 注册面冲突、命名诱导误用）。

---

## 4. Consequences（影响范围）

### 4.1 产品代码（按切片，均为**候选**；本任务不实现）

| 面 | 文件 | 改动性质 |
|---|---|---|
| 新增数据 | `adapters/dsh/host-contract.json` | 新文件（单一事实源；`host.rows[]` = 平台无关全集 29 行） |
| 新增模块 | `infra/dsh_contract.py`（访问器；含 §2.5.1 的签名与三异常类）、`infra/dsh_doctor.py`（诊断入口）、`infra/checks/dsh_boundary.py`（Check 28w） | 3 个新模块，职责各一句话 |
| 新增测试/fixture | `infra/tests/test_dsh_contract.py`、`test_dsh_doctor.py`、`infra/tests/dsh_fixtures.py`（生成式 fixture 支撑 + `--emit-fixture`）、**`adapters/dsh/fixtures/host-facts-<v>.json`（记录式；R0 F-12：放 `adapters/dsh/` 而非 `skills/**`，随包发布为有意设计 + 体积预算）** | 新增；不新建顶层目录 |
| 修改（核心链） | `lib/index.js`、`adapters/dsh/launch.py`、`infra/dsh_compat.py` | 契约化（行为保持）+ 缺口修复 |
| 修改（接线 / 冻结面，R0 F-2） | `infra/registry.py`（`LOADER_WHITELIST` +2、`_SEGMENT_LOADERS` +1、`_COMMANDS` +1）、**`infra/quickscan_registry.py`（`SEGMENTS` +1；否则导入期 `RegistryError`）**、`infra/verify_workflow.py`（薄 cmd + 28w section + 28u 委托；**函数内惰性 import**）、`infra/tests/test_registry.py`（`FROZEN_CLI_KEYS` 82→83 / `FROZEN_SEGMENTS` 70→71 / `migrated` +1）、`infra/contract_matrix/snapshots.json`（`generator.py --regen`）、**`core/architecture-baseline.json`（`archguard-ratchet --regen` + R1 豁免 `expire_version: "0.81.0"` 到期处置，见 O-8）** | 显式登记（C-12/C-14）+ 冻结面同步 |
| 修改（声明面） | `cordis.patch.yml`（去版本字面量）、`adapters/dsh/adapter-manifest.json`（证据指向契约 + 登记诊断入口）、`core/manifest.json`（canonical 声明 +1 条） | 声明与事实一致（C-20/C-9） |

### 4.2 不改动（明确边界）

- `PLUGIN_SCOPE_DIRS` / `cleanup_scope.directories`（B-6 集合相等保持，零改动）。
- `version-projections.json`（新增投影 **0** 条；`evidence.dsh_cli_version` 是宿主事实，MUST NOT 被投影）。
- `agent-presets/governance/agent.cordis.yml.template` 文本、`adapters/dsh/skill-shims/*`、其它 5 个适配器、`skills/*/SKILL.md` 与 `commands/`。
- 治理记录（本任务由 Coordinator 写入；Architect 只提供 proposed entry）。

### 4.3 用户可见影响

| 面 | 影响 |
|---|---|
| 预设交付 | 无可见变化（渲染输出字节不变；三条路径 sha256 不变） |
| 失败可见性 | **变好**：零 schema 行不再静默（屏幕出现 `[NOT_RUN]` 披露）；PASS 带分母 |
| 升级适配 | **变快**：`dsh-doctor` 一条命令分阶段定界；`--rehearse` 在 CI 预览影响 |
| 兼容性闸门 | 新增：实测 dsh 版本越出 `compat_range` → FAIL（替代缺 `peerDependencies` 的版本闸门） |
| 风险 | 契约损坏时预设不交付（warn-only，不影响宿主 boot）——见 §6 BT-1 |

---

## 5. Follow-up Actions（后续动作）

| # | 动作 | 归属 | 前置 |
|---|---|---|---|
| A-1 | **Design Review R0**：独立 Reviewer 审查本 ADR + 设计正文（重点：契约 schema 完备性、JS 不变量 J-1~J-7、判据与 loader 语义对齐、切片串行链可执行性） | Design Reviewer | — |
| A-2 | **M-0 版本范围裁决**（设计正文 §10 O-1~**O-9**；尤其 O-1 全量 V1~V9 vs 最小集 V1~V3+V8） | Coordinator → 用户 | A-1 |
| A-3 | **`dsh_compat.py` 归属 DEC**：把 {`dsh_compat.py`, `dsh_doctor.py`, `dsh_contract.py`} 与契约放置（O-4/O-5）合并裁决；本设计已给出 ≤3 处迁移成本 | Coordinator → 用户 | A-2 |
| A-4 | **实现（切片 V1~V9，可选 V10）**：Developer/Governance Developer 执行，逐片 Code/Test/Release Reviewer 审查；V8 MUST 按设计正文 §6.2 的六步顺序执行（声明 → 引擎 → `--regen`×2 → 冻结计数 → R1 豁免） | Agent Team | A-2 |
| A-5 | **U-1~U-11 验证**：尤其 U-2（读 loader 源码确认"无 Config ⇒ 透传"断言，低成本只读）、U-3（`npm pack --dry-run` 零写入）、U-11（28w 的 `SegmentSpec` 输入面/disposition 规则） | Analyst / Developer | 与 A-4 并行 |
| A-6 | **升级 SOP 写入**：每次 dsh 升级后 MUST 跑 `dsh-doctor --record-evidence` + `--rehearse`（并遵守 K-13：同版本 no-op 不得绿）；写入 `adapters/dsh/README.md` 与 release checklist 模板 | Release | A-4 |
| A-7 | **0.81.0 发布面**：CHANGELOG / release docs / 版本投影核对（V9） | Release | A-4 |
| A-8 | **向用户如实转述的边界**：本版**不**完成 0.80.0 遗留真机三项验收（N-1）、**不**关闭 RISK-050、**不**迁移 `dsh_compat.py` 归属 | Coordinator | — |
| **A-9** | **架构基线 R1 豁免到期处置（O-8）**：`core/architecture-baseline.json:6` 的 `rule: "R1"` / `expire_version: "0.81.0"` 恰在本版到期 ⇒ MUST 由 DEC 显式裁决 (a) 续期到 0.82.0 或 (b) 退役该条目；不得静默留在过期状态 | Coordinator → 用户（DEC） | A-2 |

---

## 6. Blue Team Challenges（蓝军挑战）

> 门槛：≥3 条，每条独立 ID + 缓解。以下 **11 条**：BT-1~BT-7 为初版（前 3 条为指定必覆盖面），**BT-R-01~BT-R-04 为 R0 审查方独立提出并要求纳入**（R0 判定原 7 条"覆盖质量较高但不穷尽"——缺"机制之间的缝"）。

| ID | 挑战 | 回应 / 缓解 | 残留风险 |
|---|---|---|---|
| **BT-1** | **契约层本身成为新的单点故障**：契约缺失/畸形/字段拼错 ⇒ 预设不再交付，而 0.80.0 之前至少有内联常量兜底 | ① 设计**刻意不保留回退副本**（J-4）——因为保留即第二事实源，会让"单一事实源"承诺失效；② 但把失败面**前移**：契约在 `files` 白名单内（D-06）+ K-1/K-10 门禁 + V2 突变测试；③ 任一发布候选 MUST 先跑 28u（隔离渲染冒烟）——契约损坏时 28u 必然 FAIL ⇒ **打包缺陷在 CI 拦住**；④ JS 侧失败只 warn 不抛 ⇒ 宿主 boot 不受影响；⑤ S1 阶段给出可行动 remediation（`--sync`） | 契约损坏 + CI 未跑 ⇒ 预设静默不交付（用户侧表现为"预设消失"而非"宿主崩"） |
| **BT-2** | **诊断入口本身失败时的降级**：最需要诊断的时刻（护栏/渲染器已坏、node 缺失、契约损坏）恰恰是 doctor 最容易崩的时刻 | ① 阶段级独立 try/except：崩溃阶段 → `NOT_RUN(stage crashed)`，其余阶段照常输出，报告**恒含 8 条阶段**；② **不 import `verify_workflow`**（避免循环依赖），对 `dsh_compat`/`launch.py` 惰性 import + 子进程隔离；③ `--offline` 在无 node/无 dsh 机器上全 NOT_RUN 且 exit 0（不误报 FAIL）；④ `--selftest` 逐阶段注入异常，作为 doctor 自身的反相 gate；⑤ 顶层 verdict 不因阶段崩溃变绿 | doctor 进程自身不可用（解释器/文件系统级）⇒ 只能退回 `launch.py --smoke` 与 `check-dsh-preset-compat` 两个既有入口 |
| **BT-3** | **JS/Python 双消费者对同一契约的解释分歧**：同一字段被一侧按路径、另一侧按字符串处理（例如 token 相对路径的斜杠/尾分隔符、`trim` 语义），重演 D-65 类"两条交付路径写出不同预设" | ① 契约字段**单一含义**（每字段在 §2.4 表里只有一种语义与一个类型）；② **三路径 sha256 parity 测试**（`test_dsh_adapter.py:1127`）是硬门禁；③ V2 新增"突变测试"证明两侧都真读契约、无影子副本；④ `DSH_HOME` 语义分歧单列专门判据（G-06 三方差分 gate）；⑤ JS 侧"最小解释面"：只读 `own.render.tokens` / 路径 / 标记名，**不解释**行语义（行语义只在 Python 侧） | 新增契约字段时若只改一侧 ⇒ 由 parity/突变测试抓住；但**语义**层分歧需 Code Review 人工判断（已列 V2 审查者 = Code Reviewer） |
| **BT-4** | **覆盖强度声明通胀**：契约里每条都写 `strong`，看护体系自我感觉良好，实际抓不住漂移 | ① K-8 机检：`strong` **必须**有反相 fixture 引用，`necessary` 条目不得声明 `none`，所有 `guard` 引用必须能解析到现存 test/check id；② 强度声明**只存在于契约一个文件**（无第二台账 ⇒ 无第二事实源，符合 C-21）；③ 反相 fixture 采用"改前红、改后绿"的红绿实证（V3/V5 验收项） | fixture 的**有效性**（是否真能抓住该漂移）无法机器证明 ⇒ 需 Test Reviewer 评估（已列审查者） |
| **BT-5** | **fixture 陈旧制造虚假安全感**：`host-facts-*.json` 半年未重录，演练永远绿，用户以为"CI 覆盖了升级风险" | ① `verified_on` + TTL（默认 180 天）→ 过期 **FAIL**（不是 WARN）；② S3 输出 `[EVIDENCE-STALE]` + remediation；③ §5.5 的**诚实边界**写入交付文档（演练 ≠ 真机；"先看到"以一次真实 `--record-evidence` 为前提）；④ V9 的升级 SOP 把重录列为升级后的必做步骤 | 长期不升级的场景下证据必然过期——这正是判据要暴露的状态，但需要人执行重录 |
| **BT-6** | **core→adapter 数据边被固化**：契约放 `adapters/` 后，core 读 adapters 成为既成事实，将来"core 不得依赖 dsh/adapters"的裁决更难落地 | ① 收窄为"一个访问器 + 一个数据文件"（今天 = 3 模块约 30 处硬编码，耦合面净减）；② 在 ADR（D-2）与契约 `own.notes` 显式登记为**已知偏差候选**；③ 迁移成本已量化（≤3 处、无逻辑变更）并列入 A-3 的一并裁决 | 若裁决要求迁移，需要一次额外切片（成本已知且小，但仍是额外工作） |
| **BT-7** | **hooks 静态校验只在本仓 CI 生效**：用户仓的 hooks 是一次性复制的副本，本设计选择"不改 hooks 运行时、只做静态等式判据"，用户仓的旧 hook 不受任何守卫 | ① 既有 `hooks_drift` 检查已报"陈旧"（release-checklist:133）；② 本设计**拒绝**让 hooks 引入运行时契约依赖（shell 无 JSON 解析能力，加解析即引入新耦合）；③ V9 迁移说明要求用户重装 hooks（一次性命令）；④ hook 的降级路径已存在（`find_spg_home` 候选链） | 用户仓 hook 与新版契约并存：仅影响 hook 的 dsh 路径发现（退化而非崩溃） |
| **BT-R-01**（R0 新增） | **半迁移期守卫缺位 + allowlist 侵蚀**：V1 落契约、V2 迁三个核心消费方，但唯一能判"仍在硬编码"的 K-2 要到 V8 才存在；且 K-2 的豁免（契约内 `allowlist` + 理由）**本身无判据**（无 `reason` 要求、无条数棘轮）⇒ 自我豁免通道敞开 | 迁移期的"已完成"是自述而非机检；契约面可被 allowlist 逐步侵蚀 | ① **K-2 的文本扫描提前到 V2**（纯正则，不依赖新模块）；② **K-11**：allowlist 条目须含 `literal` + `reason` + `since_slice`，条数受棘轮预算（只降不升，初值 3，O-9）；③ `FX-ALLOW-01` 反相；④ 设计 §8.2 R-9 | 迁移后 allowlist 仍可被**有理由地**扩大（棘轮只约束数量，理由质量由评审把关） |
| **BT-R-02**（R0 新增） | **同一事实两个 verdict**：`dsh-doctor` 顶层结论与 Check 28u/28v/K-7 可能对同一事实给出不同裁决（doctor 自算 `dsh_cli_version`/`oracle_packages`/TTL，而 K-7 独立判负）；`coverage` 也存在两个产出面（28v 与 doctor S2） | 用户看到"doctor PASS 但 gate FAIL"，诊断可信度崩塌 | ① doctor 的 **S3/S7 消费 K-7 结果**（不重算）、S2 **投影** `coverage`（**单一生成点** = `check_dsh_preset_compat()`）；② **K-12**：同一仓库态下 doctor 顶层 verdict 与 `check-dsh-boundary --fail-on-issues` 退出码 MUST 一致，不一致 → doctor 自身 FAIL；③ `FX-VERDICT-01` 反相；④ 设计 §8.2 R-10 | `evidence[]` 内的自由文本措辞仍可能不同（不影响裁决）；一致性判据覆盖 `verdict` 与 `coverage` 两个可观测面 |
| **BT-R-03**（R0 新增） | **演练基线的"沉默失效"**：TTL 只挂在 `evidence.verified_on`，而 `host-facts-<v>.json`（`--rehearse` 的 baseline）**无 TTL、无单调性、无 synthetic 标记**；当 `baseline.dsh_version == new.dsh_version`（忘换版本）时演练输出"无漂移"并被读成"升级安全" | 虚假安全感：CI 全绿而真机坏 | ① **K-13**：同版本 no-op **FAIL**、`captured_at` 严格递增、baseline 纳入 TTL；② 条目级 `synthetic: true/false`，synthetic 不得用于判定"升级安全"；③ `FX-REHEARSE-05` / `FX-BASE-01` 反相；④ 设计 §8.2 R-11 与 §9 U-10 | 真实 after 仍需一次真实平面记录（设计 §5.5 诚实边界 2，不可自动化） |
| **BT-R-04**（R0 新增） | **"行为保持"的可验证性边界**：V2 的三路径 sha256 不变只证**输出**不变，**不证"无影子副本"**；且部分契约字段（`own.package.engines_node`、`own.patch.shape_invariants`）不产生渲染输出差异 ⇒ "替换契约 → 输出改变"对它天然不成立 | V2 的"迁移完成"被高估，残余硬编码可长期潜伏 | ① K-2 提前到 V2（静态守卫）；② V2 的突变测试改为 **per-field 突变矩阵**（tokens / preset id / marker 名 / 行集各一条）；③ **不可从输出观测的字段**明确改由 K-2/K-10 覆盖；④ V2 验收文字显式写"parity 只证输出等价，不证单一事实源"；⑤ 设计 §8.2 R-12 | 突变矩阵覆盖 4 类关键字段；其余字段依赖静态扫描，存在"读契约但不影响输出且未被扫描"的理论缝隙（低） |

---

## 7. Non-Functional Requirements（非功能覆盖）

| NFR | 设计措施 |
|---|---|
| **性能** | 契约读取为一次 JSON 解析且**进程内 memoize**（`contractTokens()`；`lib/index.js` 顶层零 I/O，两个函数内读取点共用同一缓存）；`dsh-doctor` 默认复用既有 check 结果，`--offline` 不做子进程；不新增常驻进程；引擎侧 `dsh_doctor` 惰性 import ⇒ R6 启动模块数保持 196 |
| **安全** | 契约只读（写入仅 `--record-evidence`，需真实平面 + 隔离 `DSH_HOME`）；所有宿主探测默认 `NOT_RUN`，`--allow-host-probe` 前置 R1 三选一（隔离/备份+校验/用户授权）；不删除用户目录（G-09 残留只读计数）；`lib/index.js` 仍零依赖、无网络、不写 `~/.dsh` 以外路径 |
| **可维护性** | 宿主事实集中在单一文件，评审 diff 可读；每个新模块职责一句话（访问器 / 诊断入口 / 边界门禁）；切片单关注点（D4）且可逐个 revert |
| **可扩展性** | 新增宿主行/包名只需改契约 + 模板（K-3 双向一致保证不漏）；新增诊断阶段 = 加一个 stage 函数（S0~S7 契约化输出）；新增钻取面 = 加一个 `coverage.entries[]` 声明 |
| **可验证性** | 四件机检（设计正文 §7）：依赖面收窄 / 契约被消费 / 零校验不再 PASS / 有单点诊断入口；每条都给出具体命令与期望输出（新命令标注「待实现」） |
| **兼容性** | 渲染输出字节不变（三条路径 sha256 不变）；`--smoke`/28u 退出码语义不变；三态政策不变（C-7）；不改任何宿主行、不新增宿主平面注册（B-3） |

---

## 8. 模块边界与依赖图（无循环依赖）

```text
                      adapters/dsh/host-contract.json   (纯数据；无出边)
                                ▲
                                │ 只读
              ┌─────────────────┼───────────────────────────┐
              │                 │                           │
  infra/dsh_contract.py   lib/index.js                infra/hooks/*  ← 无运行时读；
   (访问器，无宿主探测；     (宿主行；memoized              仅由 Check 28w 静态等式校验
    不 import registry)      contractTokens()，
                            顶层零 I/O)
              ▲                 │
              │                 └─ 不 import 任何非 node: 模块（J-1）
    ┌─────────┼──────────────┐
    │         │              │
infra/dsh_compat.py  infra/dsh_doctor.py   infra/checks/dsh_boundary.py
 (schema 护栏)        (诊断入口 S0~S7)        (Check 28w 判据 K-1~K-13；
    │                    │  └─ 惰性/子进程调用         K-8 的 guard 解析在此完成)
    │                    │     adapters/dsh/launch.py --smoke
    │                    └─ 不 import verify_workflow（避免环）
    └────────┬───────────┴──────────────┬────────────────┘
             ▼                          ▼
       infra/registry.py  ←── thin ──  infra/verify_workflow.py（引擎；薄调用；
                                         对 dsh_doctor 函数内惰性 import）
```

- **模块职责（每模块 ≤3 句话）**：`dsh_contract.py` = 加载并校验宿主机契约、提供只读访问、不探测宿主；`dsh_doctor.py` = 按 S0~S7 编排诊断、输出机器可读 verdict 与 remediation、承载升级演练与证据记录；`checks/dsh_boundary.py` = 执行 K-1~K-13 边界判据并返回 gate 结果。
- **依赖性分析结论：无循环依赖（0 环），两处必须显式固定否则结论不成立（R0 F-15 / F-2）**：
  ① **K-8 的 `guard` 解析（读注册表与测试索引）MUST 在 `checks/dsh_boundary` 内完成**——若放进 `dsh_contract`，将形成 `registry → checks.dsh_boundary → dsh_contract → registry` 环；
  ② **`verify_workflow` 对 `dsh_doctor` MUST 函数内惰性 import**（顶层 import 会把 `dsh_doctor`/`dsh_compat` 拉进引擎启动集，触发 R6 `import_count` 与棘轮双红）。
  其余依据：数据文件无出边；`dsh_contract` 只依赖 stdlib；`dsh_compat` → `dsh_contract` 单向；`dsh_doctor` → {`dsh_contract`, `dsh_compat`, `launch.py`(子进程)} 单向且**禁止** import `verify_workflow`；`checks/dsh_boundary` → `dsh_contract` 单向；`verify_workflow` 只做薄调用。
- **对既有结构的遵守**：`LOADER_WHITELIST` 显式 +2 条（C-12）；`_SEGMENT_LOADERS` +1 **且必须同步 `quickscan_registry.SEGMENTS`**（导入期 `RegistryError`，R0 F-2）；无新顶层目录（C-8 零改动；记录式 fixture 落 `adapters/dsh/fixtures/`）。

---

## 9. Machine-checkable Acceptance（验收摘要）

| 目标 | 判据（详见设计正文 §7） | 状态 |
|---|---|---|
| 依赖面收窄了 | `check-dsh-boundary --fail-on-issues` → `outside-contract host literals: 0 (allowlist 3/3)`；`eliminated: D-02/D-50/D-56` | **待实现**（K-2 部分 → V2；其余 → V8） |
| 契约被消费了 | K-2~K-5 全绿 + 三路径 sha256 不变（**只证输出等价**）+ **per-field 突变矩阵**（4 类字段）+ 契约 `--validate` 报 `host.rows 29` | 部分**既有**，其余**待实现**（V1/V2） |
| 零校验不再 PASS | `rows_checked==0 ⇒ NOT_RUN`（报告级/渲染级/披露级三层不变式测试）+ `FX-NO-SCHEMA-01` 经 `--emit-fixture` 可复现 | **待实现**（V1 fixture / V3 行为） |
| 有单点诊断入口 | `dsh-doctor --json` → 8 阶段 + 退出码 0/1/2 + `--selftest` + `--rehearse` 4 突变 + `FX-REHEARSE-05`/`FX-BASE-01` 按 K-13 FAIL + `FX-VERDICT-01` 按 K-12 判 doctor 自身 FAIL + `FROZEN_CLI_KEYS=83`/`FROZEN_SEGMENTS=71` | **待实现**（V8） |

**Deviation 声明（如实）**：以上四条中三条依赖本 ADR 批准后的实现；本 ADR **不声称**任何机检已通过。AUDIT-153 的既有实测（三路径 sha256 全等、28v PASSED、28u PASSED）是**现状事实**，不是本设计的成果。**R0 修订声明**：本 ADR 与设计正文已按 `review-FEAT-028-DESIGN-R0.md` 逐条修订（F-1~F-15 + BT-R-01~04；对照表见设计正文 §11），修订**不改架构方向**，只修复"设计已写但与既有守卫/自身判据冲突"的三处 P1 与五处证据不足项。

---

## 10. 未验证假设（不得当事实使用）

| # | 假设 | 影响 | 验证计划 |
|---|---|---|---|
| U-1 | `peerDependencies` 在 dsh 的 pnpm profile 平面不会引入实质安装/解析边 | D-04 的声明方向被推迟 | 隔离 `DSH_HOME` 一次性 profile 上 `dsh plugin add` 前后 diff（需授权） |
| U-2 | 「无 `Config` 导出 ⇒ loader 原样透传」 | G-01 文案已改为**不断言** loader 行为（判据不依赖它） | 读 `cordis-plugin-loader` 的 `resolveConfig` 调用点（只读） |
| U-3 | `npm pack --dry-run --json` 零写入 | T-8 离线化判据的前置 | 临时目录执行 + 前后写入面比对 |
| U-4 | `$DSH_HOME/.agent-presets/` 是 `resolvedRoots` 的**第一个** | **本设计未把它作为判据** | 读 `dsh-agent-presets/lib/index.js:1300-1330` |
| U-5 | `{{model}}`/`{{cwd}}` 由宿主插值 | T-6 只做占位符存在的离线代理 | live 会话核验 |
| U-6 | 契约迁移到 `core/` 成本 ≤3 处 | D-2 可逆性论证 | V1 落地后由 Code Reviewer 核消费点清单 |
| U-7 | group 行非 `cordis:group` 时 loader 行为 | G02-b 取 fail-closed（不声称 loader 会失败） | 隔离组合下调用 loader 探测 |
| U-8 | 授权后 `--dump-config` 输出形状稳定 | S5 默认 NOT_RUN | 用户授权后一次性执行 |
| U-9 | `host-facts` 字段集足以表达"哪些行会坏" | 演练完备性 | V8 首次记录 + 4 个合成突变校准 |
| **U-10** | K-13 的"同版本 no-op 一律 FAIL"不误伤合法场景（同版本重录后演练） | 设计期裁定；**不预置** `--allow-same-version` 逃生门（避免重开"演练可绿"的漏洞） | V8 落地后收集反馈；如需开放须走 DEC（设计正文 §9 U-10） |
| **U-11** | Check 28w 的 `SegmentSpec("28w", …)` 输入 token 面与 disposition 规则（`_excluded("PLUGIN_PACKAGE_ASSET")` vs `_RETAIN`）可与 `28u`/`28v` 对齐 | 按最近邻形态推断，未逐条核验 FEAT-025 的 disposition 规则 | V8 实现首步核对，使 `test_segment_set_matches_the_quickscan_registry` 绿 |

> 上述假设与 AUDIT-153 §7 的 R-01~R-19 的关系：U-2/U-4/U-5 分别对应 R-15/R-13/R-08（**未验证**，本设计已避免依赖）；其余为本设计新引入的假设。

---

*ADR 结束。设计正文：`docs/requirements/dsh-compat-design-0.81.0.md`。本任务未修改任何产品代码或治理记录。*
