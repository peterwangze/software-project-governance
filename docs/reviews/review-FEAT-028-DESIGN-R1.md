# FEAT-028 设计复审报告（Design Review R1）

| 项 | 值 |
|---|---|
| Task | FEAT-028（P1）设计审查 |
| **Round** | **R1**（复审；前轮 = `docs/reviews/review-FEAT-028-DESIGN-R0.md` = **NEEDS_CHANGE**（3 P1 / 5 P2 / 10 P3+NOTE / 4 条 Reviewer 新增蓝军）） |
| Reviewer | Design Reviewer Agent（独立；未参与设计） |
| 被审对象 | `docs/architecture/ADR-018-dsh-host-compatibility-contract.md`（实测 280 行）/ `docs/requirements/dsh-compat-design-0.81.0.md`（实测 1009 行）——任务书称 281/1010，差 1 行为行尾计数口径，不影响结论 |
| 复审方式 | 只读（Read/Grep/Glob）；**未执行任何命令**；全部读取均在仓库内（本轮**未**访问仓库外路径） |
| **结论** | **APPROVED_WITH_NOTES** |

**unresolved_blockers=0**

---

## 1. 完成状态

**COMPLETE** —— 前轮 F-1~F-15 + BT-R-01~04 共 19 条**逐条独立复核完毕**（每条均回读代码/配置，不采信 Architect 对照表）；发现 **7 条本轮新引入/遗留的非阻塞项（N-1~N-7）**；**无剩余 P1 阻塞项**。

## 2. 审查结论

**APPROVED_WITH_NOTES**（`unresolved_blockers=0`）

- 三条 R0 P1 **全部经独立复算确认已修复**（F-1 行集 29 逐行命中；F-2 五个导入期/冻结面 + 两个棘轮 + 两条 `--regen` CLI 均实测可闭合；F-3 J-3 重写后 V2 验收②③④⑦自洽）。
- 四条 Reviewer 蓝军 BT-R-01~04 **均已纳入设计并有可机检判据**（K-2 前置 V2 / K-11 / K-12 / K-13），其中 2 条判据留有精度缺口（N-2/N-3，非阻塞）。
- 硬门槛复核：**全部 PASS**（见 §5）。
- 剩余项均为 P2/P3（精准化、可追溯性、措辞），**不构成阻塞**。

## 3. 逐条比对表（F-1~F-15 + BT-R-01~04）

| 前轮 | 级别 | **本轮判定** | 独立证据（回读代码/配置，非采信对照表） | 仍存问题 |
|---|---|---|---|---|
| **F-1** `host.rows[]` 28 vs 29 | P1 | **已修复** | grep `^\- id:` = 16（`:45,89,98,102,108,111,118,131,138,143,148,172,197,258,261,268`）+ `^\s+- id:` = 13（`:154,179,182,185,203,206,209,216,224,233,242,247,250`）= **29**，与 E-10 所列行号**逐行一致**；算术 29−3(group)−2(disabled:true)−1(平台短路)=23 ✓；K-3 改全集比对（§2.8:250）；§7.2 期望 `host.rows 29`；§7.3 写死 23 的来源公式 | N-1 命名残留（`platform_expr_rows[]`，P3） |
| **F-2** V8 接线面不完备 | P1 | **已修复** | 独立闭合全部触发点：① `registry.py:658 CHECK_SPECS = _build_check_specs()` 导入期执行 + `:627-633` 集合不等即 raise ✓ 需 `quickscan_registry.py`（实读 `:185-191` `SegmentSpec(check_id, domain, input_deps, modes)`；`:226-230 _excluded()` 校验 reason code；`:538-541`=28u / `:542-546`=28v 均 `"distribution"` + `_excluded("PLUGIN_PACKAGE_ASSET")` ⇒ 设计给出的 `SegmentSpec("28w","distribution",(...),_excluded(...))` 形态**可执行**）；② `test_registry.py:73-74 / :277-279 / :314-317 / :334-344 / :871-874` 四类冻结面；③ `snapshots.json:4 count 70` / `:166 key_count 82` 需 `generator.py --regen`（实读 `:606-622` 存在）；④ `migrated` 精确列表 ✓ 已列 `+dsh-doctor`（5 项）；⑤ 引擎 section 必要性 ✓（`test_registry.py:864-874` declared==observed）；⑥ `archguard_ratchet --regen` 实测注册（`verify_workflow.py:23769-23773` + `archguard_ratchet.py:1046-1061`）；⑦ R1 豁免 `expire_version:"0.81.0"` → 新增 **O-8** 双选项 + A-9 DEC 归属 | N-5 矩阵与切片清单不一致（P3） |
| **F-3** JS 读取点自相矛盾 | P1 | **已修复** | §2.6 J-3 重写为"顶层零 I/O + 模块级 memoized `contractTokens()` + 两个函数内读取点（`ensurePreset` :180 / `renderComposition` :149，后者因 `test_dsh_adapter.py:1139` 直调）"；C-1 行失败语义同步；新增 `FX-JS-03`；V2⑦ 验收。与 J-2/J-5/J-6 无矛盾 | N-6 memoize×突变矩阵进程隔离未写（P3） |
| **F-4** 三类必要依赖无表达 | P2 | **已修复（含 1 项精度残留）** | `own.package.dsh_bundle_patch_key` ✓；`own.checks.exit_codes{smoke,doctor}` ✓；`host.skill_frontmatter.*` ✓——且确认该判据已有可解析既有 guard：`test_dsh_adapter.py:633-648 test_skill_shim_frontmatter_contract`（≥9 shim 逐文件 fence/`name:<stem>`/非空 description） | **N-4**：两处新字段判据未标注 K-id/test-id 归属（P3） |
| **F-5** `required_keys`/`schema_export` 无 V1 来源 | P2 | **已修复** | §2.4 拆**记录式子块**（`"source":"recorded"`；V1 允许为空 + `recorded:false`；禁止人工誊抄）；K-1 只要求"存在不要求非空"；§5.4 只能由 `--record-evidence` 写；未记录时 `NOT_RUN(no-recorded-schema-shape)` | — |
| **F-6** `host.env` 未拆写入/探测侧 | P2 | **已修复** | 拆 `write_side{blank_policy,trim_policy,fallback,tilde_expansion}` / `probe_side{require_explicit,no_fallback}`；G06-b 改写为写入侧三实现一致并显式排除 `dsh_compat`；新增 **G06-b'** 反相断言（未设 `DSH_HOME` 不得读 `~/.dsh`，与 `dsh_compat.py:553-563` + `test_dsh_compat.py:245` 对齐） | — |
| **F-7** 访问器接口规格缺失 | P2 | **已修复** | 新增 §2.5.1：`load_contract(root,*,raw=None)` / `contract_path` / `get` / `reset_cache` + 三异常类 + 逐消费方语义表（含"畸形不得被降级为 NOT_RUN"）；K-1 引用同一分类 | — |
| **F-14** `coverage` 与 62 条无映射 | P2 | **已修复** | 双键 `subject`（契约 JSON path）+ `audit_ids[]`（D-nn）+ 判定规则（⊇ 覆盖、允许一 ID 多 subject、同 subject 重复 → FAIL）；K-8/K-9 均引用 | **N-7**：§4.1 条 1 残留"61 条/62 条"重复句（P3） |
| **F-8** E-10"18 行 config"误推 | P3 | **已修复** | 独立复算：模板 `^\s*config:` = **17**（非 group 14 + group 3），与设计一致；`rows_checked:18` 标注为探针事实、不可由模板推导 | — |
| **F-9** ADR 候选 C 理由③与 I-3 相反 | P3 | **已修复** | ADR §3.1 行 C 已删除错误表述，改述"以契约化 + 三方差分替代"，并附 R0 F-9 更正注 | — |
| **F-10** `baseUrl` 语义未固定 | P3 | **已修复（判据载体待补）** | §2.4 增 `loader_scope_baseurl_shape="file-url"` + `FX-BASEURL-01` | **N-6b**：fixture 构造方式未定义（guard 自注入 `baseUrl`，`dsh_compat.py:433`）（P3） |
| **F-11** 生成式 fixture 验收不可复现 | P3 | **已修复** | `dsh_fixtures.py --emit-fixture <ID> --out <dir>`（同 ID 字节相同）+ §4.4.1⑤ / §7.3 命令自包含 + V1⑥ | — |
| **F-12** fixture 随 npm 发布 | P3 | **已修复（声明形态待补）** | 改 `adapters/dsh/fixtures/`（在 `files` 白名单内、`adapters/` 为 manifest dir 条目 ⇒ cleanup 自动覆盖）+ 显式声明随包发布为有意设计 + 体积预算（≤64 KiB/文件、≤3 版本文件） | **N-1b**：版本化文件名在 `canonical_product_artifacts` 的声明形态未定（P3） |
| **F-13** D-54 双采样未定义 | P3 | **已修复** | §3.3 第 11 行写死：对象 = `_real_home_witness()` 两分量、时刻 = 前 1 次 + 后连续 2 次（间隔 0）、比较式 = `top_level` 名字集合差集 +"疑似变化须复现才 FAIL"、`write_surface` 不容忍竞态；V5⑤ | — |
| **F-15** K-8 解析位置未指明 | NOTE | **已修复** | ADR §8 显式两条前提（K-8 解析在 `checks/dsh_boundary`，`dsh_contract` 不得 import registry；引擎对 `dsh_doctor` 函数内惰性 import）⇒ 0 环结论**有据** | — |
| **BT-R-01** 半迁移 + allowlist 侵蚀 | 新增 | **已纳入（判据一项留有洞）** | K-2 前置 V2（纯正则、不依赖新模块，判定成立）；K-11（`literal`/`reason`/`since_slice` + 棘轮 + `FX-ALLOW-01`）；§8.2 R-9；ADR §6 | **N-2**：`allowlist_budget` 锚点未定（P2） |
| **BT-R-02** 同一事实两个 verdict | 新增 | **已纳入（与 `--offline` 范围冲突）** | K-12 + §5.1 单一裁决纪律（S3/S7 消费 K-7、`coverage` 单生成点）+ `FX-VERDICT-01`；§8.2 R-10 | **N-3**：K-12 与 V8 验收③ 未划定适用域（P2） |
| **BT-R-03** baseline 无 TTL/单调性/synthetic | 新增 | **已纳入（TTL 后果歧义）** | K-13 + `FX-REHEARSE-05` / `FX-BASE-01` + §5.4 生命周期 + U-10 | **N-6c**：TTL 过期后果写为"FAIL/advisory"未定型（P3） |
| **BT-R-04** "行为保持"只证输出等价 | 新增 | **已纳入** | K-2 前置 V2 + per-field 突变矩阵 + 不可观测字段分流 K-2/K-10 + §7.2 与 V2② 措辞澄清 + R-12 | **N-6a**：JS memoize 下突变需进程隔离未写明（P3） |

## 4. 本轮新发现 findings（N-1~N-7，全部非阻塞）

| 编号 | 级别 | 位置 | 事实 | 建议 |
|---|---|---|---|---|
| **N-1** | P3 | 设计 §3.3 第 7 行（`:340`）vs §2.4 `$host.rows[]`（`:147`） | §3.3 仍写"契约 `host.row_contract.js_scope` + `platform_expr_rows[]`（2 行）"，但 §2.4 字段表**不含** `platform_expr_rows`，平台条件行已由 `host.rows[].platform_conditional`/`enabled_on` 表达 ⇒ 同一事实两个字段名 | 删除 `platform_expr_rows[]` 或以"派生视图，不落盘"标注（禁止作为第二来源） |
| **N-2** | P2 | 设计 §2.8 K-11、§2.1、§7.1、§10 O-9 | K-11 要求 `allowlist_budget` "只降不升，超限 FAIL"，但**未给出 budget 的锚点位置**；若 budget 仅是契约内字段，则同一提交内可同时抬高 budget 与新增条目 ⇒ "只降不升"不可自证（正是 BT-R-01 想封的自我豁免通道） | 把 budget 锚定到**契约之外**（如 `FROZEN_*` 同族常量或 `core/architecture-baseline.json` 的 `--regen` 只降不升机制），或要求 K-11 对外部锚点做等价判定 |
| **N-3** | P2 | 设计 §2.8 K-12、§5.1、§6.1 V8 验收③ | K-12 要求"同一仓库态下 doctor 顶层 verdict 与 `check-dsh-boundary --fail-on-issues` 退出码 MUST 一致"；而 `--offline` 只禁子进程/宿主探测，**文件级 K-7 仍会执行并可 FAIL** ⇒ 漂移态下 `--offline` 会 exit 1，与 V8 验收③"全 NOT_RUN/exit 0"字面冲突 | 加适用范围：K-12 比较在"全阶段非 `--offline` 运行"下成立；`--offline` 的"全 NOT_RUN/exit 0"限定为"文件级判据亦无 FAIL"的干净态 |
| **N-4** | P3 | 设计 §2.4 `own.checks.exit_codes`、`host.skill_frontmatter.*` 判据列 | 两处新字段判据是**文字要求**，未标注归属；已核实该要求已有可解析 guard：`test_dsh_adapter.py:633-648`（≥9 shim 逐文件） | 字段表判据列标注 `guard = test_dsh_adapter.py::test_skill_shim_frontmatter_contract`；`exit_codes` 挂 K-12 或既有退出码用例（`test_dsh_adapter.py:782/806/819/832` + `:1066`） |
| **N-5** | P3 | 设计 §6.2 矩阵 `:781` vs §6.1 V4 行 `:766` | 矩阵把 `infra/tests/dsh_fixtures.py` 标为 V1 与 V4 触碰，而 §6.1 的 V4 触碰文件仅 `dsh_compat.py` + `test_dsh_compat.py`（V5 才是"经 `--emit-fixture` 生成"的切片）⇒ 矩阵与切片清单不一致（不影响并发安全） | 对齐两处（预期正确值 = V1 创建、V5 使用） |
| **N-6** | P3（3 子项） | §6.1 V2④/§5.6；§5.6 FX-BASEURL-01；§5.5 [B]/K-13 | (a) V2 per-field 突变矩阵未写**进程隔离**（J-3 进程内 memoize + J-5 禁止新增导出 ⇒ JS 侧突变必须每突变一新进程，否则实现者可能为加 `reset` 而违反 J-5 或得到假红）；(b) `FX-BASEURL-01` 期望"`!!js` 的 `baseUrl` 非 file-url → finding"，但 `baseUrl` 由探针**自注入**（`dsh_compat.py:433`），组合侧无法提供非 file-url 形态 ⇒ 构造方式未定义；(c) baseline `captured_at` 超 TTL 后果写"FAIL/advisory"未定型 | (a) 写明"突变一律在独立进程内执行（JS）/ `reset_cache()`（Python）"；(b) 改为断言注入值形态或 `new URL(baseUrl)`/`fileURLToPath(baseUrl)` 语义差异；(c) 定型为 FAIL 并给 `[EVIDENCE-STALE]` + FAIL 消息 |
| **N-7** | P3 | 设计 §4.1 条 1（`:386`） | 同句重复出现"**61 条**必要依赖按 `audit_ids` 的并集覆盖判定（…），**62 条**必要依赖按 `audit_ids` 的并集覆盖判定"——数字自相矛盾（K-9 与 O-9 均以 **62** 为准）；且"每个契约条目…有且仅有一条声明"与随后"允许一个 `audit_id` 出现在多个 subject"的口径需显式区分为"同一 `subject` 不得重复" | 删除"61 条"残句；唯一性规则改写为"同一 `subject` 不得重复声明" |

## 5. 硬门槛复核表

| 门槛项 | 阈值 | 裁决 | 事实依据 |
|---|---|---|---|
| 候选方案数 | ≥2 | **PASS** | ADR §3.1 A~E（5）+ 设计 §2.2 载体 4 / §2.3 放置 4 / §5.1 形态 3 |
| ADR 关键字段完整 | =100% | **PASS** | 日期 `:4` / 背景 §1 / 决策 §2 D-1~D-7 / 备选 §3.1-3.4 / 排除理由逐条（含 F-9 更正）/ 影响范围 §4.1-4.3（新增接线/冻结面行 `:140`）/ 后续动作 §5 A-1~**A-9** |
| 蓝军挑战 | ≥3 独立 ID + 缓解 | **PASS（11 条）** | ADR §6 BT-1~BT-7 + **BT-R-01~04**，每条含"回应/缓解"+"残留风险" |
| 模块无循环依赖 | =0 | **PASS（有据）** | ADR §8 显式固定两条前提（K-8 解析在 `checks/dsh_boundary`；引擎惰性 import `dsh_doctor`）；数据文件无出边、`dsh_contract` 仅 stdlib、`registry` 仅存字符串路径（`registry.py:349-420`） |
| 接口契约输入/输出/异常 | 完整 | **PASS** | 新增 §2.5.1（4 API + 3 异常 + 逐消费方）；`dsh-doctor` 输出契约 + 退出码 0/1/2 + 阶段级降级；字段表 §2.4；K-1~K-13 |
| NFR 覆盖 | 性能/安全/可扩展/可维护 | **PASS** | ADR §7（性能行已补 memoize + R6 196；安全行与 R1 三选一一致） |
| Bar Raiser 独立评审 | 已执行 | **PASS** | 本 R1 即独立复审（Reviewer 未参与设计；只读工具） |

## 6. 复审方法与深度结论

**复审方法（可复查）**：① 全文重读 R0 报告作为比对基线；② 对每条 P1/P2 声明**复算**（模板行集两条 grep + 行号逐一对齐；`registry.py` 导入期 join 链与四个冻结面；两条 `--regen` CLI 存在性；JS 侧 J-3 与 V2 验收自洽性）；③ 逐条核对 R1 新增证据行 E-17~E-22；④ 对 K-11/K-12/K-13 检验可判定性/失败信息可定位性/是否引入第二事实源；⑤ 补充核对两测试文件 `def test_` 计数 = `test_dsh_adapter.py` **46** + `test_dsh_compat.py` **43** = **89** ⇒ §6.1 V2① "Ran 89, OK" 准确，但 §7.2 单跑行写 "Ran 43 tests" 与实测 46 不符（并入 N-6 口径项）。

**六维度复核**：设计合理性 PASS（模块职责各≤1 句、接口最小化、字段单一含义除 N-1 命名残留）；技术债务评估 PASS（刻意债务均显式登记并有偿还路径，K-1~K-13 每条对应一个已存在问题面）；安全与合规 PASS（写入/探测侧拆分后 guard 的"不猜 `~/.dsh`"属性被明文固定并加反相断言；真实环境操守未变）；可演进性 PASS（契约可版本化 + 三异常类 fail-closed；回滚路径逐切片；V8 冻结面/棘轮步骤化后可执行）；依赖图 0 环 PASS（两条前提已显式固定）。

**本轮未能独立验证的事项（如实登记，未写成事实）**：① `contract_matrix/generator.py` 的 `--golden`/`--self-check` 与 28w 段面新增的交互（仅验证 `--regen` 存在与快照计数面，应由 V8 验收⑧ 兜底）；② `canonical_product_artifacts` 是否支持 `type:"dir"`/glob 条目（抽检均为 `type:"file"`，未穷举全节）；③ 设计给出的 `SegmentSpec("28w", …)` 的 **input token 清单与 disposition 语义**（形态可执行已验，token 内容未核——与设计自陈 U-11 一致）；④ §2.9.4 引用 `28v` input token 面"对齐"的逐 token 等价性（未逐项比对）。

## 7. 结论与后续动作

**结论：APPROVED_WITH_NOTES（unresolved_blockers=0）** —— 三条 P1 经独立复算确认修复，四条 Reviewer 蓝军已纳入且判据可机检，硬门槛全通过；剩余 N-1~N-7 为非阻塞精度/追溯项。

后续动作建议（全部非阻塞）：

1. **V1/V2 落地时即闭合 N-1、N-4、N-5、N-7**（文档/字段表一行级修正，与切片同批做最省成本）。
2. **V8 落地前闭合 N-2、N-3、N-6**（K-11 锚点位置、K-12 适用域、突变矩阵进程隔离 + FX-BASEURL-01 构造 + baseline TTL 后果定型）。
3. **M-0（A-2）范围裁决**：O-1(a)/(b) 均可；若选 (b)（V1~V3+V8），须注意 V8 仍需按 §6.2 六步顺序执行（含两次 `--regen` 与 O-8 的 R1 豁免 DEC）——这不是新约束，是 F-2 修复后的既成事实。
4. **本报告可作 G5/设计完成的独立评审证据**；复审链到此结束（无 NEEDS_CHANGE，无需 round 2，远未触及 M7.4 熔断）。

---

## 8. 真实环境命令上报表

**无任何命令执行**（本轮未调用 pwsh/Bash；工具仅 Read/Grep/Glob）。**未访问仓库外路径**（与 R0 不同：R0 曾只读 npx 缓存内 loader 源码，本轮不需要）。对用户真实环境（`$HOME`/`$DSH_HOME`）**零读写**。

*报告结束（R1，APPROVED_WITH_NOTES / unresolved_blockers=0）。本次复审未修改任何文件、未执行任何命令、对用户真实环境零写入；全部读取均在仓库内。*
