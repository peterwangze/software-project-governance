# FEAT-029 代码审查报告（Code Review R0）

| 项 | 值 |
|---|---|
| Task | FEAT-029（0.81.0 切片 V1：契约数据层落地） |
| Round | **R0**（首次审查，无前轮） |
| 审查对象 | commit `4d93b24`（2026-09-12 21:37:18 +0800）——`5 files changed, 4570 insertions(+), 0 deletions(-)` |
| Reviewer | Code Reviewer Agent（只读审查；本任务获批只读命令例外） |
| 权威规格 | `docs/requirements/dsh-compat-design-0.81.0.md`（1023 行）、`docs/architecture/ADR-018-dsh-host-compatibility-contract.md`（280 行）、事实输入 AUDIT-153（`docs/requirements/dsh-host-dependency-inventory-0.81.0.md`，801 行） |
| **结论** | **APPROVED_WITH_NOTES**（`unresolved_blockers=0`） |

## 0. 审查方法（可复查）

1. `git show 4d93b24 --stat/--name-only` 确认变更面 = 契约 JSON + 访问器 + 测试 + fixture 发射器 + manifest（**零删除**）。
2. 逐行读 `dsh_contract.py`（416 行全文）、`test_dsh_contract.py`（1265 行全文）、`dsh_fixtures.py`（417 行全文）、契约 JSON（2456 行，行块 + 全部命名空间结构化读取）。
3. **独立复算**：模板行集 / group / disabled / 平台条件 / `config_keys` 由审查方**自己的正则**在模板文本上重算（不复用被测模块）；AUDIT-153 必要性分类按 §2 表体 marker 复算；dispositions / `audit_ids` 并集自算；12 个 fixture **跨进程** SHA256 自算；guard 引用独立解析。
4. 把契约每个 `own.*`/`host.*` 标量与**实际源码**逐字对账（`package.json`、`cordis.patch.yml`、`lib/index.js`、`launch.py:352-354`、`verify_workflow.py:6892`、`dsh_compat.py:93/433/542-576`、`adapter-manifest.json`）。
5. 实跑：`test_dsh_contract.py` → **Ran 90, OK**；`test_dsh_adapter.py` → **Ran 43, OK**；`check-manifest-consistency --fail-on-issues` → **PASSED, exit 0**。

## 1. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁决 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | **0** | ✅ PASS |
| 5 维度全覆盖 | = 100% | 5/5 均有独立结论（§3~§7） | ✅ PASS |
| 每条发现标注级别 | = 100% | 6/6（P1×1、P2×2、P3×3） | ✅ PASS |
| 设计一致性检查 | 已完成 | §8/§9/§10/§11（比对 §2.4/§2.5.1/§2.6/§2.8/§2.9/§4.1/§5.4/§6.1 V1/§11.1 + ADR D-1~D-7） | ✅ PASS |
| AI 代码专项 5 项 | 全部完成 | §10 逐项有结论 | ✅ PASS |

## 2. 独立复算结论（审查方自算，未采信 Developer 自述）

| 项 | 复算方式 | 结果 | 与声明一致 |
|---|---|---|---|
| **模板行数** | 独立正则扫 `agent.cordis.yml.template`（不 import 测试模块）：`^(\s*)- id: (\S+)$` | **29**（顶层 16 + 嵌套 13，无其他缩进） | ✅ |
| 行 id 集合 | 模板 id 集 vs 契约 `row_id` 集 | 完全相等；嵌套→父 group 映射逐条相等 | ✅ |
| group / `disabled:true` / 平台条件 | 独立计数 | 3 / 2 / 2；`config_declared`=17；任一平台 enabled = 23 | ✅ 与设计 §0.2 E-10 逐项一致 |
| `config_keys` | 逐行模板 ↔ 契约 | 26 非 group 行逐行一致（含 group 行 `[]`） | ✅ |
| **dispositions 并集** | 自算所有 `D-nn` 对 `D-01..D-100` | **100 条、100 distinct、无缺无重** | ✅ |
| **`audit_ids` 并集** | 25 条 coverage 并集 | **100**（⊇ necessary 72，missing=[]）；无空 `audit_ids`；无重复 `subject` | ✅ |
| **necessary 复算** | 按 AUDIT-153 §2 表体 marker 逐行复算 | **72 / 22 / 4 / 2 = 100**；§2.11 表体 = 62 / 26 / 4 / 3 = 95 | ✅ 双记两侧均复现 |
| D-10 口径 | 查 AUDIT-153 原文 | D-10 行 marker = 「必要（DEC-187 I-1 硬约束）」；§2.11「历史 3」的第三个正是 D-10（与 D-89/D-92 同列） | ✅ 契约把 D-10 归 necessary、把 "3" 记入 `stated_in_audit_section_2_11` = **DEC-191 的容忍做法，正确** |
| **fixture 字节确定性** | **12/12 跨进程**各起新解释器发射两次比对 SHA256 | **全部逐字节相同** | ✅（比仓内测试更强：仓内只对 FX-NO-SCHEMA-01 做了跨进程比对） |
| guard 解析 | 独立解析 42 条 guard 引用 | **0 条无法解析**（`check-*`/`28u`/`28v` 命中注册面；`file::method` 命中真实测试方法） | ✅ |
| `compat_range` | 读契约 | `null`；`notes.compat_range` 明示"取值前 S3 越界判据不可用，V8 按 NOT_RUN 处理、**不得默认 PASS**"；`test_get_returns_null_fields_instead_of_raising` 断言 null 可解析 | ✅ DEC-191 落地正确 |

## 3. 维度 1：正确性 —— 通过（1 条 P1）

契约 ↔ 实际源码逐项对账**全部相等、无误差**：

| 契约字段 | 对账源 | 结果 |
|---|---|---|
| `own.package.{name,type,main,exports,files,engines_node}` | `package.json` | 六项逐字相等 |
| `own.package.dsh_bundle_patch_key` | `package.json:41-45` | 键 `dsh.bundle.patch` 存在；值以 `own.patch.file` 结尾（测试断言） |
| `own.patch.file` / `shape_invariants` | `cordis.patch.yml` | 4 条不变量在实物上成立（恰 1 条 insert、0 条 `- id:` UPDATE、0 `trust:`、0 `!!js`） |
| `own.render.tokens`（3 条） | `launch.py` × `lib/index.js` 与模板 | 三 token 两侧渲染器均出现；模板 token 集**双向相等** |
| `own.preset.{id,version_marker,skill_root_marker}` | `launch.py:109/111`、`lib/index.js:70` | 逐字相等 |
| `own.checks.exit_codes.smoke` | `launch.py:352-354` | `{0,1,2}` 逐项相等 |
| `own.checks.compat_section_title` | `dsh_compat.py` `CHECK_SECTION_TITLE` | 相等 |
| `own.checks.smoke_section_title` / `upgrade_regression_label` | `verify_workflow.py:16270` / `:6892` | 相等 |
| `own.adapter_manifest.required_fields`（9 项） | `launch.py` `print_manifest` 的访问面 | 9/9 均为真实读取；9/9 存在于 `adapter-manifest.json` |
| `host.install.{scope,cli_package,anchor_rel,env_overrides,profiles_dir_name}` | `dsh_compat.py:134-136/128-129/156` | 逐字相等 |
| `host.install.plane_layout`（2 形态） | `dsh_compat.py:569-575` | 与 `_profile_planes` 一致（含优先序） |
| `host.home.{user_preset_dir,composition_file,composition_globs}` | `dsh_compat.py:160/168` | 逐字相等（含 2 条 glob） |
| `host.row_contract.*` | `dsh_compat.py:550/551`（`:433` `pathToFileURL(file.path).href`） | 逐字相等；`baseUrl` 形态固定为 file-url（R0 F-10 落地正确） |
| `host.apis`（4 包 / 5 符号） | `dsh_compat.py:146-151` + `PROBE_SCRIPT` | 5/5 在 guard 中出现，且全部能在 AUDIT-153 找到锚点（**无幻觉 API**） |
| `host.rows[]` 29 行 | 模板逐行 | 逐行一致（见 §2 复算） |

**契约无"无来源锚点的事实"**：按类别抽查每个非平凡标量（`@deepseek-ai/dsh-tool-ask-user` 零 Config、`host.host_plane_registries` 三注册表、`shell_env`/`subagents`/`web`、`ctx_logger=optional`、`write_policy`），全部能回到 AUDIT-153 或实际源码。**未发现编造字段。**

**F-1（P1）** 见 §9。**边界条件**：`load_contract` 的 `raw` 旁路缓存路径、`_resolve` 的 `_MISSING` 哨兵（使 `null` 合法值与"未声明"可区分）、重复 `row_id` 拒绝、`ttl_days` 正整数与 `bool` 排除——均逐行读过，逻辑正确。

## 4. 维度 2：安全性 —— 通过（零发现）

- **无真实环境写**：`dsh_contract.py` 只 `read_text` 一个文件；新测试与 fixture **零** `Path.home()` / `expanduser` / `os.environ` / `DSH_HOME` 读取（命中仅为"禁止串清单"文字）。**审查期未观察到任何对 `~/.dsh` 的写。**
- **不探测宿主**：模块只 import `json`/`pathlib`/`typing`/`__future__`；测试断言其源码不含探测构造，并反向自证。`_package_root()` 由 `__file__` 推导，不读 CWD、不读环境变量。
- **无环（R0 F-15 / ADR §8 的 0 环前提成立）**：`dsh_contract` 不 import `registry` / `dsh_compat` / `dsh_doctor`。
- **OWASP 面**：无网络、无注入面（无 shell/eval/SQL）、无硬编码凭据、无用户输入解析；`_tokenize` 对失衡 `[` 返回 `_MISSING` 而非抛未分类异常。契约不含绝对路径/机器名（唯一日期字面量是审计日期 `2026-09-13`，属事实锚点）。

## 5. 维度 3：可维护性 —— 通过（2 条 P2/P3）

- 命名清晰，职责单一（416 行中约 110 行是 `REQUIRED_PATHS` 数据表；最长函数 ~30 行）。
- 每个非自明取值都有设计出处注释（`§2.5.1`/`R0 F-5`/`R0 F-15`/`R0 F-6`），R0/R1 发现编号可回溯；契约以 `_note` 补足 JSON 无注释，并明写"人工誊抄 = 契约缺陷，不是数据"。
- 重复代码为**有意的数据重复**（`slice:["V1"]` 重复约 72 次），换取可机检与可 diff，属可接受代价。
- **F-2（P2）/ F-5（P3）** 见 §9。
- 迁移成本（ADR U-6 要求核对）：`CONTRACT_REL` 常量 1 处 + 契约 `own.paths.accessor` 自指 1 处 + 后续 JS URL / hooks 校验常量各 1 处 ⇒ **≤3 处成立**，可逆性论证未被本次实现推翻。

## 6. 维度 4：性能 —— 通过（零发现）

- **进程内 memoize 正确**：`_CACHE[str(path)]` 按绝对路径缓存，`raw=` 旁路不污染缓存；`test_reset_cache_forces_a_fresh_read` 用真实临时文件证明失效语义。
- **无 O(n²)**：一次 JSON 解析 + `_validate` 单遍（111 条 `REQUIRED_PATHS`）+ 单遍行校验；`_resolve` 的 row-id 线性查找仅 29 行规模。
- 无 N+1 / 无循环内 I/O；契约 73.8 KB，单次解析成本可忽略。
- 并发：无共享可变状态（仅缓存字典）；与设计一致（无并发承诺）。

## 7. 维度 5：测试覆盖 —— 通过（1 条 P1 与 1 条 P3 指向覆盖缺口）

**有效性评估（重点回答"是否存在自证式断言"）——测试总体独立，不是自证式**：

1. **K-3 双向一致是真独立复算**：`_parse_template_rows` 在**模板文本**上运行（不读契约、不 import 被测 JSON），逐行重建 `package`/`disabled_expr`/`config_declared`/`config_keys`/`group` 后与契约逐字段比对；模板多一行或契约多一条都会红。附带"非 0/4 缩进即 raise"的严格性。
2. **K-9 的 72 条基线也独立复算**：`_audit_marker_sets()` 从 AUDIT-153 **原文表体**按 marker 复算，再与契约 `audit_baseline` 逐要素相等断言（审查方独立复现，同得 72/22/4/2）；同一测试**同时**断言 §2.11 的 `stated` = 62 ⇒ "逐行标记 ≠ 汇总口径"被**机检固定**。
3. **反相能力真实存在**：K-1 三异常类各有反相（缺文件/坏 JSON/非对象/未知 schema/删字段/删行字段/重复 row_id，共 7 条）；`test_leftover_scan_pattern_catches_a_misspelt_token` 用两种拼错形态验证正则真的能抓；`test_host_rows_recorded_subblock_is_empty_and_flagged` 逐行断言 29×4 字段为空 ⇒ **人工誊抄必红**（R0 F-5 核心约束被真守住）。
4. **K-8 的一半在单元级已可执行**：42 条 guard 引用解析到真实 test 方法名/注册 check id（0 条失败），`strong` ⇒ 必有 `negative_fixtures`（strong=14/14 满足，无 `none` 的 necessary 条目）。
5. **fixture 12 个**：`FIXTURES`=12 可发射、`DEFERRED`=24 声明 slice；`coverage.negative_fixtures` 全部落在 `known_fixture_ids()` 闭集内。
6. **无 mock**：全文零 `mock`/`patch`（唯一匹配是方法名里的 `hold`）；无 `TODO/FIXME/NotImplemented`。

**覆盖缺口（与 F-1/F-4 呼应）**：契约**编码损坏**这一输入类无测试（`FX-UTF8-01` 只覆盖"组合文件非 UTF-8"，不覆盖契约自身）；`--validate` 入口不存在故无测试。

**新测试的仓库副作用**：`test_fixtures_are_generated_not_committed` 与 `test_emitting_creates_no_repository_files` 证明发射器不落仓；**但前者只查 `git ls-files adapters/dsh`**，抓不到仓库根残留（见 F-6）。

## 8. 范围与设计一致性（已完成）

- **未触碰 V2/V8 文件**：`git show --name-only` 精确为 5 个文件；`launch.py` / `dsh_compat.py` / `lib/index.js` / `verify_workflow.py` / `registry.py` / `quickscan_registry.py` **零改动** ⇒ 设计 §6.2 波次纪律（W1=V1 独占新文件）执行正确。
- **`manifest.json` 两处改动均为既有守卫所必需**：`product.entries` +1（由 `checks/manifest.py:273-274` 强制）；`canonical_product_artifacts.entries` +1（6 必填字段 + `type=="file"` + `required is True` + 磁盘存在 + git 跟踪全部满足）。实测 `check-manifest-consistency --fail-on-issues` → PASSED exit 0。
- **`cleanup_scope.directories` 零改动**（11 元集），与 §2.9.2 的 C-8 "零改动"裁决一致。
- **`validation_commands` 只引用现存可执行命令**（实跑均通过），**无指向 `check-dsh-boundary`/`dsh-doctor` 等未实现命令的引用**。
- **JS 侧不变量未被本次变更影响**（`lib/index.js` 未改）；契约已为 J-3/J-5/J-6/J-7 预置锚点。

## 9. Findings 全表（6 条；无 P0）

| # | 级别 | 位置 | 事实 | 影响 | 建议 |
|---|---|---|---|---|---|
| **F-1** | **P1** | `skills/software-project-governance/infra/dsh_contract.py:385-388` | `raw = path.read_text(encoding="utf-8")` 只捕获 `OSError`；非 UTF-8 契约 → `UnicodeDecodeError` **穿出**三分类。**实测复现**（`good_bytes[:200] + b"\xff\xfe" + good_bytes[200:]` → 裸 `UnicodeDecodeError`，`isinstance(OSError)==False`） | §2.5.1 是三处引用的分类契约（K-1 直接引用）且明令"错误消息 MUST 含 契约路径+异常类+具体字段"。该输入类既不在三分类内、消息不含异常类名；不发生"畸形→NOT_RUN"的错误降级（方向相反），但更糟：无契约 | `except (OSError, UnicodeDecodeError) as error:` → `ContractUnreadable`；补一条反相测试。**1 行改动** |
| **F-2** | P2 | `dsh_contract.py:339-342` | `_validate` 对 `recorded.recorded` 只查键存在，不校验其为布尔 `false`（`recorded.source` 却有值检查） | 现行契约与 90 测试均正确（断言 `is False`×29），非交付缺陷；消费者侧确定性输入下 `recorded: null`/`"false"` 仍通过 K-1 | V8 补 `if recorded.get("recorded") is not False: raise _fail_malformed(...)` |
| **F-3** | P3 | `host-contract.json` `elimination.dispositions[D-05]` | `decision:"weakened"`, `slice:["V1"]`；实际落地面 = `compat_range` 闸门且该值为 `null`（V8 才按 NOT_RUN 处理）。K-9 机检只约束 `removed_at`，D-05 因 weakened 而豁免 | 易被读成"闸门已在 V1 生效" | V8 改为 `slice:["V1","V8"]` 或补 `weakened_at:"V8"` |
| **F-4** | P3 | 设计 §7.2 / ADR-018 §9 vs 实现 | 设计给出的 `dsh_contract.py --validate` 验收入口**未实现**（字符串在仓库中不存在）；功能面已被 90 测试覆盖，§6.1 V1 验收清单未列该入口 | 无功能影响；验收可执行性略低于设计文末描述 | V8 提供薄 CLI，或文档侧收口该行 |
| **F-5** | P3 | `host-contract.json` `evidence.recording.*` | 五字段被 `REQUIRED_PATHS` 强制且被测试断言，但**无任何 `coverage.entries[].subject` 或 disposition 引用**（25 个 subject 全量核过） | 与 §4.1「可信面 ≤ 校验面」的声明闭合精神有缝；有守卫故非僵尸字段 | V8 在 coverage 中补一条声明 |
| **F-6** | P2 | 仓库根 `.tmp-k2-scan.py`（未跟踪，2265 B） | 创建 `2026-09-12 21:41:49`（commit 后约 4 分钟），内容为 K-2 契约外字面量扫描原型；`git ls-files`/`git log --all`/`.gitignore` 均无。**`无 commit 记录，故作者归属不可断言`** | 无运行时影响；但属仓库根残留，且**现有守卫抓不住**（`test_fixtures_are_generated_not_committed` 只查 `adapters/dsh`；`check-manifest-consistency` 实测仍 PASS） | 删除；或 `git add` 作为 V2 的 K-2 实现正式入账 |

## 10. AI 代码专项 5 项（逐一结论）

| 专项 | 结论 | 证据 |
|---|---|---|
| mock 残留 | **无** | 零 `unittest.mock`、零 `patch(`；打真实文件/真实子进程 |
| 硬编码返回值 | **无** | 无"输入无关返回常量"的函数；fixture 常量是设计要求的载荷（`totallyBogusKeyThatMustBeRejected` 出自 §4.4.1④） |
| 幻觉 API | **无** | 契约 4 包 5 符号全部有锚点；访问器只用 stdlib；测试用的 `subprocess`/`hashlib`/`tempfile` 均为真实 API |
| 未实现 TODO | **无** | 零 `TODO/FIXME/XXX/HACK`；"待实现"以结构化方式表达（`recorded: false`、`paths_pending:["doctor"]`、`DEFERRED` 带 slice+reason） |
| 过度实现 | **无越界，但存在 5 处"刻意多余"的登记式字段**（§11 逐项判定为可接受） | 未触碰 V2/V8 文件，未新增目录，未新增宿主探测 |

## 11. Developer 主动申报的 3 处自增字段（逐项判定）

| 申报项 | 判定 | 依据 |
|---|---|---|
| `own.host_row.{entry,export_surface,apply_never_throws,warn_only,top_level_io,runtime_dependencies}` | **可接受**（P3 级命名空间讨论项） | 有设计出处（D-13/J-5 导出面 §2.6 J-5；D-23 + J-1/J-2；J-3 顶层零 I/O）；语义属本包自身不变量（写 `own.*` 而非 `host.*` 正确）；把 D-13/D-23 从 disposition 文本提升为可机检字段，**不引入第二事实源**（值由测试对 `lib/index.js` 现算） |
| `own.paths_pending: ["doctor"]` | **可接受** | 把"V8 未落地"变成**可机检跳过**（`test_own_paths_exist_unless_declared_pending`），使 §2.4 `$own.paths.*` 存在性判据仍成立而无须虚构 `dsh_doctor.py`；V8 落地后删除即可 —— 有明确**退场条件** |
| `own.adapter_manifest.required_fields` / `own.preset.write_policy` / `host.row_contract.ctx_logger` / `host.host_plane_registries` | **可接受** | 均有**逐字**设计出处：§3.3 第 23 行（D-60）/ 第 6 行（D-22，逐字相同）/ 第 3 行（D-14，逐字相同）/ 第 8 行（D-45 + 必备 `verification: unverified (R-09)`，已带） |

> 单一事实源结论：四处均**未复制宿主 schema/行语义**，只把"我方承诺"与"设计已裁定的声明"结构化；无第二来源。

## 12. V1 刻意为空项核对（R0 F-5 核心约束）

- 29/29 行的 `recorded.{schema_export, required_keys, accepted_keys, probe_result}` 全空 + `source:"recorded"` + `recorded:false` —— 独立脚本逐一核过，并被测试逐行断言。
- `evidence.{recorded_on, verified_on, plane.source, plane.node_modules, dsh_cli_version, compat_range}` 全 `null`；`oracle_packages` = `{}`。
- **未发现人工誊抄痕迹**：无任何"某行某键被接受/拒绝"的实测值；`required_keys` 全 `[]`，`probe_result` 全 `null`。唯一带实测来源说明的 `evidence.notes.dsh_cli_version_current_measurement` **刻意只写指针不写值**（指向 AUDIT-153 §1.1 = `0.1.5-rc.1`，值不入契约）——**正确**，避免 `0.1.5-rc.1` 字面量进入契约后成为失真源（且符合 §2.9.3 投影纪律）。
- 契约无 `generated_at`/时间戳/机器路径。

## 13. DEC-191 落地核对

| 裁定 | 落地证据 | 裁决 |
|---|---|---|
| ① `necessary_ids` 取 **72** 并双记 §2.11 的 62 | `necessary_ids` len=72（按 AUDIT-153 §2 marker 复算，逐 ID 相等）；`count_reconciliation.stated_in_audit_section_2_11.necessary=62`；`derived_from_section_2_markers.necessary=72`；测试同时断言两者 | ✅ 正确且可复现 |
| ①附带：fail-closed 超集语义 | `coverage.audit_ids` 并集 = 100 ⊇ 72（missing=[]），同时覆盖设计引用的 62 ⇒ K-9 判据强于设计 | ✅ |
| ② `compat_range = null`（值推迟 V8） | 契约 `evidence.compat_range: null`；`notes.compat_range` 明写"V8 按 NOT_RUN 处理，不得默认 PASS"；`evidence.recording.note` 补写"null = 未记录 ⇒ 依赖它的判据按 NOT_RUN" | ✅ 语义到位 |
| ②附带：可否机检 | **V1 无可执行机制**（S3 属 V8），已用三处结构化声明表达 | ⚠️ 文档级到位、机检留 V8（登记为 V8 义务，不致 FAIL） |

## 14. 结论

**`APPROVED_WITH_NOTES`（`unresolved_blockers=0`）**

- 零 P0；硬门槛全通过；**无 BLOCKING 问题** ⇒ 不作为 NEEDS_CHANGE 退回返工。
- 唯一 P1（F-1）**不改变任何已交付结论的正确性**，只把"契约编码损坏"从可分类失败降级为裸异常；建议按 V2/V8 邻域的小片修复（1 行 + 1 反相测试），不必阻断本切片。
- 两条 P2（F-2 访问器值校验、F-6 仓库根残留脚本）建议与 V2 同批处理。
- 独立复算结论：模板 29 行（16+13）逐行一致、dispositions 100/100、`audit_ids` 并集 100 ⊇ 72、72/62 双记可复现、12/12 fixture 跨进程逐字节相同、42/42 guard 引用可解析 —— 交付物与设计/事实输入之间**未发现事实偏差**。

## 15. 真实环境命令上报表（R4）

本任务**零真实环境写操作**；全部命令只读/单元测试，且 `DSH_HOME` 已重定向至临时目录：

| # | 命令 | 退出码 | 影响路径 |
|---|---|---|---|
| 1 | `git show 4d93b24 --stat --format=...` | 0 | 只读 |
| 2 | `git show 4d93b24 -- <manifest.json>` | 0 | 只读 |
| 3 | `git status --porcelain` / `git diff --stat` / `git ls-files --error-unmatch .tmp-k2-scan.py` / `git log --all -- …` | 0 / 1（paths 未匹配，预期） | 只读 |
| 4 | `$env:DSH_HOME="$env:TEMP\spg-review-probe-029"; python -m unittest … -p test_dsh_contract.py -v` | **0（Ran 90, OK）** | 临时目录；未读/未写 `~/.dsh` |
| 5 | 同法 `-p test_dsh_adapter.py` | **0（Ran 43, OK）** | 同上（内部用 `tempfile` 临时 home） |
| 6 | `verify_workflow.py check-manifest-consistency --fail-on-issues` | **0（PASSED）** | 只读仓库 |
| 7 | `python -c "import json …"` 系列（契约解析/复算/guard 解析/模板复算/marker 复算） | 多处 0；1 次 `SyntaxError`（引号转义失误，无副作用） | 只读 |
| 8 | 12×2 次 `dsh_fixtures.py --emit-fixture … --out $env:TEMP\spg-fx-{a,b}` + `Get-FileHash`，随后删除两个临时目录 | 0 | **仅 `%TEMP%`**；仓库零写入 |
| 9 | 1 次非 UTF-8 契约探针（`tempfile.TemporaryDirectory()` 内构造） | 0 | **仅临时目录**；用于复现 F-1 |

**写操作声明**：审查方对仓库**零写入**（`git diff --stat` 为空；契约 SHA256 = `BC2BDE0E…B67E3577` 与审查前一致）。期间一次 `edit` 调用因 `old_string == new_string` 被工具拒绝，未产生任何文件变更。对 `$HOME` 下配置目录、`$DSH_HOME`、`~/.dsh` **零操作**。**未验证项（NOT_VERIFIED）**：无。

---

*报告结束（R0，APPROVED_WITH_NOTES / unresolved_blockers=0）。*
