# FEAT-028 设计审查报告（Design Review R0）

| 项 | 值 |
|---|---|
| Task | FEAT-028（P1）设计审查 — DSH 宿主兼容性契约层与看护体系 |
| Round | **R0**（无前轮；本报告为初轮结论） |
| Reviewer | Design Reviewer Agent（独立；未参与设计） |
| 被审对象 | `docs/architecture/ADR-018-dsh-host-compatibility-contract.md`（262 行）、`docs/requirements/dsh-compat-design-0.81.0.md`（864 行） |
| 事实输入 | `docs/requirements/dsh-host-dependency-inventory-0.81.0.md`（AUDIT-153，801 行）；另独立回读 20+ 个代码/配置文件 |
| 审查方式 | 只读（Read/Grep/Glob）；未执行任何命令；零写入 |
| **结论** | **NEEDS_CHANGE**（3 P1 BLOCKING / 5 P2 / 10 P3+NOTE；硬门槛全部 PASS） |

## 0. 硬门槛裁决

| 门槛项 | 阈值 | 裁决 | 事实依据 |
|---|---|---|---|
| 候选方案数 | ≥2 | **PASS** | ADR §3.1:104-110 体系级 A~E（5）+ 设计 §2.2 载体 4 + §2.3 放置 4 + §5.1 形态 3 |
| ADR 关键字段完整 | =100% | **PASS** | 日期 `:4`、背景 §1、决策 §2 D-1~D-7、备选 §3.1-3.4、排除理由逐条、影响范围 §4.1-4.3、后续动作 §5 A-1~A-8（7/7） |
| 蓝军挑战 | ≥3 且独立 ID+缓解 | **PASS（判定为不完尽）** | ADR §6:177-185 BT-1~BT-7，各带"回应/缓解"+"残留风险"；缺 4 类（见 §3） |
| 模块无循环依赖 | =0 | **PASS（条件性）** | ADR §8:204-227；条件是 K-8 的 guard 解析不得落在 `dsh_contract` 内（F-15） |
| Bar Raiser 独立评审 | 已执行 | **PASS** | 本 R0 即独立评审（Reviewer 未参与设计，只读工具） |
| 接口契约输入/输出/异常 | 完整 | **PASS（带 F-7 缺口）** | `dsh-doctor` 输出契约 §5.1:551-577（8 阶段字段+退出码 0/1/2+阶段级 try/except）；字段表 §2.4；K-1~K-10；缺 `dsh_contract.load_contract` 签名/异常表 |
| NFR 覆盖 | 性能/安全/可扩展/可维护 | **PASS** | ADR §7:189-198 共 6 行（含可验证性/兼容性） |

## 1. findings 表（F-1..F-15；P1 = BLOCKING）

| 编号 | 级别 | 位置 | 事实（可复查） | 影响 | 建议 |
|---|---|---|---|---|---|
| **F-1** | **P1** | 设计 §2.4:140、§7.2:748；模板 `agent-presets/governance/agent.cordis.yml.template:98-104` | 契约 `host.rows[]` 声明为 28 行（23 enabled + 3 group + 2 `disabled:true`），但模板实为 **29 行**（顶层 16 行 `:45,89,98,102,108,111,118,131,138,143,148,172,197,258,261,268` + 嵌套 13 行 `:154,179,182,185,203,206,209,216,224,233,242,247,250`）。被漏掉的是平台条件行 `tool-bash`（`:98-100 disabled: !!js process.platform === 'win32'`）；非 win32 下被漏的变成 `tool-pwsh` ⇒ **平台无关的结构性缺口** | ① K-3「模板逐行 ↔ 契约 `host.rows[]`，模板多一行 → FAIL」（§2.8:206）在 V1 首跑即 FAIL；② K-2 把**模板**列入消费者集合（§2.8:205），`@deepseek-ai/dsh-tool-bash` 不在契约中 → 契约把自己的模板判为"契约外硬编码"；③ D-30/D-31（必要依赖的 `!!js` 平台形态）在契约行集里无落点 | 把 `host.rows[]` 定义为**平台无关行全集 = 29 行**，每行带 `disabled_expr` + `platform_conditional`（2 行）+ `enabled_on`（可空）；K-3 比对全集；§7.2 期望输出改 `host.rows 29` |
| **F-2** | **P1** | ADR §4.1:136、§8:227；设计 §2.9.4:236-239、§6.1 V8:683 | V8 声明只改 `registry.py`（3 处）+ `verify_workflow.py`（薄 cmd + 28u 委托），但新增段 28w + 新命令 `dsh-doctor` 触发 **5 个未声明的冻结面/导入期守卫**：① `registry.py:658 CHECK_SPECS = _build_check_specs()`（导入期执行）+ `:629-633` 在 FEAT-025 未声明该段时 raise `RegistryError` ⇒ import registry 即失败，必须同改 `infra/quickscan_registry.py`（`:538-542` SegmentSpec 表、`:745 registry_ids()`）；② `tests/test_registry.py:73-74 FROZEN_CLI_KEYS=82/FROZEN_SEGMENTS=70` 与 `:276-283`/`:334-344` 精确集合断言；③ `contract_matrix/snapshots.json:4 count 70`/`:166 key_count 82` 冻结面须 `generator.py --regen`（同型先例见 `test_registry.py:65-72`）；④ `test_registry.py:314-317` 的 `migrated` **精确 4 项列表**因 `dsh_doctor.cmd_dsh_doctor` 非 engine 模块而变化；⑤ `test_registry.py:864 test_matches_the_live_engine_face` 要求注册段在引擎内有实际 section ⇒ 须在 `_run_full_engine_checks` 加 28w section（进入 R4 print 预算，C-15）。另 `archguard_ratchet.py:38-42,895-920`（R7 基线陈旧即 FATAL）要求引擎一改必 `--regen`，牵动 `core/architecture-baseline.json:16-20 anchor_loc 24204`、`:543 import_count 196`，且 `:6` 的 R1 豁免 `expire_version: "0.81.0"` **恰在本版到期** | V8 按其自述文件清单**不可通过**：import 期即 RegistryError，冻结面/迁移列表/棘轮全部转红；"切片可执行性"与"验收可机器判定"两项实质失效 | V8 触碰文件列补 `quickscan_registry.py`、`contract_matrix/snapshots.json`、`tests/test_registry.py`、`core/architecture-baseline.json`，并写明 `registry` 接线 + `generator.py --regen` + `archguard-ratchet --regen` 步骤与 R1 豁免（0.81.0 到期）的续期/退役处置；引擎侧 `dsh_doctor` 必须函数内惰性 import（R6 `import_count` 不增，与 C-15 一致） |
| **F-3** | **P1** | 设计 §2.5 C-1:164、§2.6 J-3:180、J-5:182、§6.1 V2:677；`lib/index.js:83-87,149-163`；`tests/test_dsh_adapter.py:1139-1156` | 设计同时主张（a）契约"**仅在 `ensurePreset()` 内**懒读"、（b）J-5「`renderComposition` 签名不变」、（c）V2 验收②「`test_dsh_adapter.py` 全绿」。但该测试**直接**调用 `renderComposition(template, pkgRoot)`（`:1139`），而 token 表今天来自模块级 `TOKEN_PATHS:83-87`、替换发生在 `:155-160`；若 token 只能从 `ensurePreset` 取得，直调时无 token ⇒ `leftovers ≠ []` ⇒ `:1152` 断言必红 | JS 侧不变量章节（四大审查重点之一）内部自相矛盾；V2"行为保持"验收基线不可同时成立 | 明确定义"两个函数内读取点"（`ensurePreset` 与 `renderComposition` 共用一个模块级 memoized `contractTokens()`，仍保证**顶层零 I/O**），或把该取舍写入 J-3 并补 `FX-JS-03`（契约缺失时 `renderComposition` 的行为断言） |
| **F-4** | P2 | 设计 §2.4:130-154；`package.json:41-45`；`launch.py:653-658`；§5.1:572、§5.2 S6:589 | 62 条必要依赖中 3 类**在字段表里无表达**：① D-01 的 `dsh.bundle.patch` **键名**（`own.package.{name,type,main,exports,files,engines_node}` 不含；K-2 的"config 键名"类别因此无命中目标）；② D-53 的 `--smoke` **退出码契约 0/1/2**（`own.checks.*` 只有 3 个文案字段，退出码只在正文以"与 --smoke 一致"提及）；③ D-62/63/64 的 **skill frontmatter 契约**（`name == 文件名`、非空 `description`，今天仅 `launch.py:653-658` 校验；§5.2 S6 把它列为判定输入却无字段/判据） | REQ-147「必要依赖单点契约」对上述必要项不成立；K-2/K-3 存在结构性盲点 | 补 `own.package.dsh_bundle_patch_key`、`own.cli.exit_codes.{smoke,doctor}`、`host.skill_frontmatter.{name_equals_filename,description_required}` 三组字段 + 对应 K 判据 |
| **F-5** | P2 | 设计 §2.4:140、§5.4:615、§6.1 V1:676；AUDIT-153 §5 G-01 实测 | `host.rows[]` 的 `required_keys[]`/`schema_export` 声明来源为"E-10 逐行核对"，但 E-10/§0.2 只覆盖行数/group/disabled/config 行数/零 schema 行，**未枚举任何一行的 required_keys**（AUDIT 仅有 `dsh-persona.prefix` 必填的反向对照）；per-row accepted/required keys 属安装态 schema 形状，只能由 `dsh-doctor --record-evidence`（V8）记录，而 V1 无前序 | V1 的 K-1/K-3 单元判据与 `coverage.entries[]` 在 V1 阶段**无数据来源**；若实现期人工誊抄，契约即退化为"人工维护的第二事实源"（违 REQ-147） | 二选一：把 `schema_export/required_keys/accepted_keys` 移出 V1 必要字段（V1 只登记可核静态事实），或给 V1 增加 `--record-evidence` 前置并如实标注"需真实平面" |
| **F-6** | P2 | 设计 §4.4.4 G06-b:445；`dsh_compat.py:536-539,553-558,560-562`；`tests/test_dsh_compat.py:245` | G06-b 要求"三实现（`lib/index.js`/`launch.py`/`dsh_compat` 读取方）与上游实测值一致"，而 guard 的读取方**刻意不回落 `~/.dsh`**（`:553-558` 自述、`:560-562 if not raw: return []`，并由 `test_dsh_compat.py:245`"未设不猜"固化）；上游对空/未设值回落默认 | 按字面执行会改掉 guard 的既定安全属性（开始读真实 `~/.dsh`），扩大真实环境探测面，与 ADR §7「安全」行「所有宿主探测默认 NOT_RUN」及 C-19/M7.7 隔离基线冲突；该冲突设计未裁决 | 契约拆 `host.env.write_side.{blank_policy,trim_policy,fallback,tilde_expansion}`（写入侧三实现必须一致）与 `host.env.probe_side.{require_explicit,no_fallback}`；G06-b 差分 gate 只适用写入侧，探测侧保持 fail-closed |
| **F-7** | P2 | 设计 §2.5 C-2:165、§2.8 K-1:204；C-1/C-3 失败语义列 | `dsh_contract.load_contract` 只有导入名与一句职责，无签名/返回结构/异常分类；而四消费方失败语义依赖"文件缺失 / 畸形 / `schema_version` 未知"三态（C-1 → warn+跳过；C-2 → 非 0；C-3 → NOT_RUN；K-1 → FAIL） | 接口契约不完整；实现期易出现"畸形契约被当缺失→NOT_RUN"的静默降级（违 C-6 精神） | 给出签名与异常表（`ContractUnreadable/ContractMalformed/ContractSchemaUnknown`），K-1 判据引用同一分类 |
| **F-14** | P2 | 设计 §4.1:331、§2.8 K-8:211、K-9:212；AUDIT-153 §3.3:323-343 | §4.1-1「每个契约条目（`host.*` 的 **62 条必要依赖聚类** + `own.*` parity 契约）有且仅有一条声明，缺声明 → FAIL」不可判定：K-8 的失败信息用**路径键**形态（`host.rows[persona].config_keys`），而 AUDIT 的 62 条用 **`D-nn` 编号**且多条聚类共用 ID（如 `D-34/D-35` 同时属"18 行"与"customSkillDirs"两个聚类）；两套 ID 空间无映射 | "缺声明 → FAIL"与 K-9 的 ID 覆盖判据均不可机检 ⇒ C-21「可机检且不产生第二事实源」在本条落空 | 契约内显式给 `coverage.entries[].subject`（契约 JSON path）+ `audit_ids[]` 双键；K-8 以 `audit_ids` 覆盖 62 条全集、`subject` 指向路径，并定义重复声明判定 |
| **F-8** | P3 | 设计 §0.2 E-10:38 | "带 config 的行 18 条"与模板不符：含 `config:` 的行 = 14（非 group）+3（group 的 config 为子行列表）= **17**；18 的真实来源是 `rows_checked`（有 `Config` 导出的 enabled 行数 = 23−5） | 易误导契约作者从模板推导 `coverage`/`schema_export`（与 F-5 叠加） | 改为"enabled 23 − 零 schema 5 = checked 18（源码/探针事实，非模板可推导）" |
| **F-9** | P3 | ADR §3.1:108 行 C 的理由③；`core/protocol/plugin-contract.md:254` | C 的排除理由③"与 DEC-187 I-3 的方向相反"与 I-3 原文相反：I-3 明许"允许 import 其公开包、消费其公开服务、声明 `peerDependencies`"；引入上游包不会产生宿主→本插件的反向依赖 | 排除结论不受影响（理由①②充分），但该表述会把 I-3 误读为"禁止 import 宿主包"，成为后续防回流规则的错误依据 | 删除理由③，或改写为"不采纳：以契约化 + 三方差分替代，理由见 C-1 与 AUDIT-153 §3.1 反面证据" |
| **F-10** | P3 | 设计 §2.4:139（`loader_scope=[baseUrl,process,console]`）；`dsh_compat.py:433`；`docs/reviews/review-REL-076-CODE-R0.md:106` | 契约声明 `baseUrl` 在 `!!js` scope 内，但**未固定其取值语义**（探针注 `pathToFileURL(file.path).href` = 文件 URL；rel-076 已登记"文件 URL vs loader 目录 URL"分歧且未复现） | BT-3 缓解①"每字段单一含义"在该字段有残余；`new URL('.', baseUrl)` 类表达式在 guard 与 loader 间可能出现语义差异 | 契约加 `loader_scope_baseurl_shape` 字段 + 一条反相 fixture 固定该语义 |
| **F-11** | P3 | 设计 §4.4.1 ⑤:396、§7.3:754 | 验收命令以 `<FX-NO-SCHEMA-01 生成的组合>` 占位（§5.4 明示生成式 fixture 不落盘），§7.3 自注"fixture 由新测试支撑模块生成 → 待实现 V1/V3" | 判据可判定但**不可直接复现**（V3/V4/V5 验收需人工构造组合，易漂移） | 给 `infra/tests/dsh_fixtures.py` 一个 `--emit-fixture <ID> --out <dir>` 入口，使验收命令自包含 |
| **F-12** | P3 | 设计 §5.4:614；`package.json:31` | 记录式 fixture 拟放 `skills/software-project-governance/infra/tests/fixtures/dsh/`，而 `files` 白名单含 `skills/` ⇒ `host-facts-<v>.json` 会随 npm 包发布 | 发布面混入测试/证据数据（体积与语义噪声），与 §4.2「不改动」面的表述不冲突但未声明 | 改放 `adapters/dsh/fixtures/`（同在 `files` 内、语义更贴宿主事实面），或显式声明接受发布并给体积预算 |
| **F-13** | P3 | 设计 §3.3 第 11 行:290、§4.4 相关 | D-54「双采样确认（连续两次都变才 FAIL）」未定义采样对象与时刻（`top_level` 还是 `.agent-presets`？前后各两次？） | V5 该条验收（`FX-WITNESS-01` 触碰 `settings.yaml` → 不 FAIL）不可机检 | 在 V5 判据中写死采样对象/时刻与比较式 |
| **F-15** | NOTE | ADR §8:204-227、§2.8 K-8 | K-8 的"guard 引用必须能解析到现存 test id 或已注册 check id"需读注册表/测试索引，设计未指明解析发生在访存器还是检查模块 | 若放进 `dsh_contract` 会形成 `registry → checks.dsh_boundary → dsh_contract → registry` 环，"0 环"结论失效 | 在 ADR §8 图注中显式写"解析在 `checks/dsh_boundary` 内完成" |

> 分类说明（遵"禁止把'设计没写'当'设计错了'"）：**F-1/F-2/F-3** = 设计已写但与既有事实/自身判据矛盾（BLOCKING）；**F-4/F-5/F-6/F-7/F-14** = 设计写了但不足以支撑其声明（须补，非架构问题）；**F-8~F-13/F-15** = 精度/可复现性备注，不阻塞。

## 2. 六维度逐项结论（对应 Coordinator 指定 7 项）

1. **契约 schema 完备性 —— 不完备（2×P1/P2）**。字段表能表达 AUDIT-153 §3.3 的**多数**聚类（包身份/补丁语义/交付路径/18 行 schema/`customSkillDirs`/`cordis:` 前缀/上游 API/`DSH_HOME`/warn-only/token/版本投影与清理），但：① `host.rows[]` 行集与模板不一致（28 vs 29，漏平台条件行）⇒ 与 K-3/K-2 **自相矛盾**（F-1）；② 3 类必要依赖无表达（`dsh.bundle.patch` 键名、`--smoke` 退出码、skill frontmatter 契约）（F-4）；③ `required_keys/schema_export` 无 V1 可达来源（F-5）；④ `coverage.entries[]` 的 ID 空间与"62 条必要依赖"未建立映射（F-14）。"声明了但无消费方"仅 `host.host_plane_registries`（S5 默认 NOT_RUN，设计已如实披露，可接受）。`cordis:`/`!!js`/`isolate`/`group` 语义均已建模 ✓。
2. **JS 侧不变量 J-1~J-7 —— 方向正确但内部矛盾（1×P1）**。J-1（`:58-61` 仅 `node:`）、J-2（`:181-187,227-238` 永不抛）、J-5（导出面 4 项）、J-6（parity 测试 `:1127`）、J-7（marker）与实读完全一致；J-4（不留回退副本）与 REQ-147 一致且 BT-1 已如实登记代价 ✓。**但** J-3/C-1"只在 `ensurePreset` 内懒读"与 J-5"签名不变"+V2②"parity 测试全绿"三者不可能同时成立（测试直调 `renderComposition`）（F-3）。
3. **判据与 loader 真实语义对齐 —— 对齐（独立核实通过）**。G-02/G-03 三条判据经直读安装态 loader `_disabled` 源码核实**全部成立**（不凭注释）；G-01 根因链（`:371-377 → :1000-1026 → :1088-1091` + `unverified` 只在 `:961-965` 生成）**逐环节证实**，G01-e"删除对 loader 行为的断言"方向正确。取舍**未依赖** R-08/R-13/R-15。
4. **切片可执行性与串行链 —— 串行链 PASS / 单切片不可执行（1×P1）**。文件冲突矩阵与波次经逐文件核对：`dsh_compat.py`（V2→V3→V4→V5→V6）、`lib/index.js`（V2→V5→V6→V7）、`launch.py`（V2→V5→V6）在 W2~W6 上**严格串行**，可并行波次（W3/W5/W7）文件互斥 ⇒ **无并发写冲突，结论成立**。但 V8 的**触碰文件集不完备**（F-2）⇒ V8 按现设计**不可执行**。验收判据**基本可机器判定**，仅 FX-* 生成式 fixture 的验收命令不可直接复现（F-11）。
5. **ADR §3 排除理由 —— 成立（1×P3）**。B（不建契约层，违 REQ-147）、C（真依赖，违 C-1 + AUDIT 反面证据）、D（上游无此工件，不可交付）、E（运行时探测，违 REQ-148）四条排除均基于可核事实；JSON/`adapters/dsh/`/`dsh-doctor` 的采用理由成立。core→adapter 数据边**已显式登记**并给可逆性论证（≤3 处）✓。唯一缺陷：C 的理由③与 I-3 原文相反（F-9）。
6. **蓝军挑战 —— 7 条达标但不穷尽**（见 §3）。
7. **与 M7.7 / DEC-187 / DEC-188 一致性 —— 一致**。无 `- id:` UPDATE、无 `disabled:false`、无宿主平面注册、无 `!!js` 自定位、无 `trust: system`；`--allow-host-probe` 前置 R1 三选一且默认关闭（O-7 建议默认关闭）；`--record-evidence` 沿用既有 read-only 模式；N-9 明示不做运行时自愈 ✓。

## 3. Reviewer 独立提出的蓝军挑战（≥3）

| ID | 挑战 | 严重度 | 建议缓解 |
|---|---|---|---|
| **BT-R-01** | **半迁移 + allowlist 侵蚀**：V1 落契约、V2 迁 3 个核心消费方，但**唯一能判"仍在硬编码"的 K-2 要到 V8 才存在**；且 K-2 的豁免是"契约内 `allowlist` + 理由"（§2.1:84、§3.4:310 `allowlist 3`），而 allowlist 本身**无任何判据**（K-8 只约束 `coverage`，不约束 allowlist；无条目数棘轮、无 `reason` 字段要求）⇒ 自我豁免通道敞开 | 中 | ① 把 K-2 的静态扫描**提前到 V2**（纯文本/正则扫描，不依赖新模块，成本极低）；② 新增 K-11：allowlist 条目须含 `reason`+`since_slice`，条数受棘轮约束（只降不升，超限 FAIL） |
| **BT-R-02** | **同一事实两个 verdict**：`dsh-doctor` 顶层结论与 Check 28u/28v/K-7 可能对同一事实给出不同裁决——doctor S3 自测 `dsh_cli_version`/`oracle_packages`（§5.2 S3）与 K-7、S7 分属不同入口；设计未规定 doctor 复用它还是自算。极端情形：用户跑 `dsh-doctor` 见 PASS，而 `check-dsh-boundary --fail-on-issues` 因 K-7 为 FAIL；S2 的 `coverage` 与 28v 报告的 `coverage` 是两个产出面 | 中 | ① doctor 的 S3/S7 **必须消费** K-7 结果而非重新推导；② 新增不变式 fixture：同一仓库态下 `dsh-doctor --json` 顶层 verdict 与 `check-dsh-boundary --fail-on-issues` 的 exit code 必须一致（不一致 → doctor 自身 FAIL）；③ `coverage` 块只保留**一个生成点**（`check_dsh_preset_compat()`），doctor 只投影不重算 |
| **BT-R-03** | **演示性 fixture 与真实升级的时间差**：TTL 只挂在 `evidence.verified_on`（§2.4 evidence 行、§2.7:194），`host-facts-<v>.json`（`--rehearse` 的 baseline）**无 TTL、无单调性、无 synthetic 标记**。首次记录只能落在**当前**平面（0.1.5-rc.1），第一次真实升级前所有演练都是"合成突变自证"；且当 `baseline.dsh_version == new.dsh_version`（操作者忘了换版本）时演练会输出"无漂移"并被读成"升级安全" | 中高 | ① `--rehearse` 在 baseline/new 同版本时 **FAIL**（no-op rehearsal 不得绿）；② 强制 `captured_at` 单调（new > baseline），否则 FAIL；③ 报告逐条标注 `synthetic: true/false`；④ baseline 也纳入 TTL 判据 |
| **BT-R-04** | **V2「行为保持」的可验证性边界**：V2 验收②（三路径 sha256 不变）只证"**输出**不变"，**不能证"无影子副本"**；"读穿证明"靠 V2④ 突变测试，而突变测试只能证明**被突变的字段**被消费（设计未列 per-consumer×per-field 突变矩阵）。且契约字段中有相当一部分（如 `own.package.engines_node`、`own.patches.shape_invariants`）**不产生渲染输出差异**，"替换契约 → 输出改变"对它天然不成立 | 中高 | ① 把 K-2 提前到 V2（同 BT-R-01），使"无影子副本"在 V2 就有静态守卫；② V2 的突变测试改为 per-field 矩阵（至少 tokens / preset id / marker 名 / 行集各一条），并把"不可从输出观测的字段"改由 K-2/K-10 覆盖；③ 在 V2 验收文字里明确"parity 只证输出等价，不证单一事实源" |

**对设计 BT-1~BT-7 穷尽性的判定**：**不完尽**。7 条覆盖了契约单点故障 / doctor 自降级 / 双消费者分歧 / 强度通胀 / fixture 陈旧 / core→adapter 固化 / hooks 复制面，质量较高；缺 4 类"机制之间的缝"：BT-R-01（迁移期守卫缺位 + allowlist 无判据）、BT-R-02（同事实多 verdict）、BT-R-03（baseline 无 TTL/单调性）、BT-R-04（行为保持的可验证性边界）。建议纳入 ADR §6 与 §8.2。

## 4. 依赖图核查结论

**结论：0 环（条件性 PASS）**。依据：数据文件 `adapters/dsh/host-contract.json` 无出边；`dsh_contract` → 仅 stdlib；`dsh_compat` → `dsh_contract`；`checks/dsh_boundary` → `dsh_contract`；`dsh_doctor` → {`dsh_contract`, `dsh_compat`, `launch.py`(子进程)} 且**不 import `verify_workflow`**（ADR §8:226 已固定为结构约束）；`verify_workflow` 只做薄调用。新增边不会反向：`registry._SEGMENT_LOADERS` 只存**字符串路径**，lazy `importlib` 解析，不产生导入边；`_COMMANDS +1` 由引擎薄包装承担。**两处须显式固定否则结论不成立**：① K-8 的 guard 解析位置（F-15，须落在 `checks/dsh_boundary` 内）；② `verify_workflow` 侧 `dsh_doctor` 必须函数内惰性 import（否则触发 R6 `import_count` 与 F-2⑤）。core→adapter 数据边（D-2/BT-6）已**显式登记**，与 `release-checklist-0.80.0.md:137` 的既有偏差同类，可逆性论证（≤3 处路径常量）成立。

## 5. 独立核对的设计断言（抽检命中）

Reviewer 未依赖设计文档自述，逐条回读代码/配置核对，命中率高；设计对 AUDIT-153 的**三处修正经独立验证为正确**：

- ① `cleanup.py:204-214` 对 **dir 条目递归展开为 canonical**，而 `manifest.json:235` 已声明 `adapters/` ⇒ 新文件**不会**被当残留，"manifest 登记不是防删除必要条件"的 C-9 口径修正**成立**；
- ② §3.2 计数（26 vs 25 行 / 36 ID）不一致确实存在（AUDIT §2.11 亦不自洽：62+26+4+3=95≠100），改以逐 ID `removed_at/weakened_at` 为验收信号是正确处置；
- ③ §2.9.3 不改 `PROJECTION_SYNC_PATTERNS` 的理由**成立**（`manifest.json:48-61` 的 `member_match:"exact"` 会因加一条而 FAIL）。

**loader 真实语义独立核实（不凭注释/文档）**：`@deepseek-ai/cordis-plugin-loader/lib/index.js:363-369` = `_disabled(options){ if (options.group) return false; if (this.disabledOf(options)) return true; while(entry){ if (this.disabledOf(entry.options)) return true; … } }` ⇒ **G03-a/G03-b/G03-c 与 loader 真实语义一致**；`:271 builtins[name.slice(7)]` 支持 `cordis:` 内建语义（G02-b 取 fail-closed 严于 loader，且设计明确声明"不声称 loader 会失败"——正确）；`resolveConfig` 确由 `@deepseek-ai/cordis` 导出，`host.apis` 声明成立。**R-08/R-13/R-15 未被当作事实使用**：R-15 已被 G01-e 显式解除断言；R-13 未被任何判据使用；R-08 仅用离线代理 + 未验证披露。

## 6. 深度发现（摘要）

- 设计对 AUDIT-153 的三处**事实纠正**均经独立验证为正确——本设计质量的核心证据，AUDIT 的"结论大于证据"问题被设计正确吸收。
- 设计的**自我诚实度高**：§9 未验证假设 U-1~U-9 自陈、§4.5 未纳入缺口逐条列明、§8.1 非目标明确"不冒充 0.80.0 真机验收"、ADR §9 Deviation 声明"不声称任何机检已通过"。
- 三条 P1 全部属于"**设计已写但与既有守卫/自身判据冲突**"，均可定点修复，**不需要重新设计架构**。

## 7. 后续动作建议

1. **退回 Architect 修复 F-1/F-2/F-3**（阻塞项），并把 F-4~F-7/F-14 一并纳入（同一次修订成本更低）。
2. 修复后 **re-spawn 同一 Design Reviewer 复审（R1）**，逐条标注"已修复/未修复/新引入"（M7.4 step 4.6）。
3. 建议把 BT-R-01~04 写入 ADR §6（蓝军表）与 §8.2（新风险表），并在 V2/V8 验收补对应 fixture。
4. M-0 范围裁决建议：若压关键路径选 O-1(b) V1~V3+V8，须注意 V8 单独仍受 F-2 约束（冻结面/棘轮），且 V1 数据来源（F-5）在无 V8 `--record-evidence` 时更紧张。

---

*报告结束（R0，NEEDS_CHANGE）。本次审查未修改任何文件；未执行任何命令；对用户真实环境零写入。*
