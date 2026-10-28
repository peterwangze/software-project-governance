# Review: FEAT-111 — CODE R0（独立代码审查）

- **Reviewer**: Code Reviewer Agent（独立——非实现作者；只读审查 + 本报告写入；变异检验已精确还原并经 git diff --stat 自证零残留）
- **日期**: 2026-10-28
- **审查对象**: 工作树未提交改动（恰 6 文件，+457/−6）：`change_triage.py`（+99）、`checks/triage_domain.py`（+62）、`verify_workflow.py`（+25）、`tests/test_change_triage.py`（+267）、`commands/change-triage.md`（+8/−1）、`adapters/dsh/skill-shims/change-triage.md`（描述行）
- **验收基线**: TRIAGE-FEAT-111（.governance/change-triage/FEAT-111.json）五条
- **结论**: **APPROVED_WITH_NOTES，unresolved_blockers=0**（P0=0 / P1=0 / P2=0 / P3=4）

## 一、逐项核实证据（独立执行，非采信 Developer 报告）

### 1. diff 纯粹性 — PASS
- `git status --porcelain`：恰 6 个已跟踪文件 ` M`（与派发声称一致——第 6 文件 `checks/triage_domain.py` 见下条裁决）；未跟踪仅 `.codex-sandbox/`（既有 scratch）。
- `git diff --stat`：457 insertions / 6 deletions；逐行读 diff 无无关重构/格式化/行尾漂移。
- **第 6 文件裁决**：`checks/triage_domain.py` 是 Check 32 记录校验的宿主（`validate_triage_record`/`check_change_triage` 所在），验收条款①「Check 32 在新字段面下 PASS」的本体落点即此文件——**属验收本体，非夹带**；锁面已由 Coordinator 机补（op-d30d4360），与 M7.6a 一致。

### 2. 分类表事实性 — PASS
- `PRIOR_ART_REQUIRED_FAMILIES = {FEAT, DESIGN, RESEARCH, AUDIT}`：四前缀全部是 `task_priority._TASK_FAMILY_PREFIXES`（L117-121 权威词汇，20 前缀）的成员——语义子集，零发明前缀；ratchet 测试 `test_required_families_subset_of_task_family_vocabulary` 钉死 `assertLessEqual` 子集关系。
- 实况族量独立统计（.governance/change-triage/ 目录 300 条记录）：FIX=177 / FEAT=89 / REL=31 / AUDIT=3——与声称一致。DESIGN/RESEARCH 为零使用前向兼容成员（权威词汇在册），门禁未来命中即生效，无空转成本。
- 边界注记见 F-02（SYSGAP 等边缘族未入表——语义裁定已披露，单点可调）。

### 3. 自指边界裁决（重点）— **诚实边界设计，非自我洗白**
- 事实：`PRIOR_ART_NORMALIZATION_DATE = 2026-10-29` 只界 Check 32 **记录校验面**；**CLI fail-closed 门禁无日期边界**（`run_triage` 对一切新设计/研究类入账即刻拒收——含门禁作者自己的未来票据）。生产实证：FEAT-111 自身记录 `created_at=2026-10-28`、无 `prior_art` 键，Check 32 全量复跑 PASS（豁免生效且不产生 FAIL 噪声）。
- 对照两风险：①追溯强制会使不可变历史记录永久 FAIL 且无合法修复路径（反模式）；②作者自免。裁决依据：(a) 豁免是**统一边界**（一切 10-28 前记录，非仅本票），沿用仓内 `TRIAGE_NORMALIZATION_DATE`/FIX-174/FIX-233 先例；(b) 记录不可变，重生成=改写历史（更劣）；(c) 本票自身的先例义务**实质履行**并留痕三处——执行包 `competitive_baseline`（Rust RFC 2333 prior_art / WIPO TISC 专利审查基线，实读核验在案）、代码注释（先例出处+活动分型依据）、命令文档示例。结论：门禁对未来的自身作者无豁免、对历史的豁免统一且先例背书——诚实设计。

### 4. 占位判定语义 — PASS
- `is_prior_art_placeholder` = strip 后 **FULL-match**（`_PRIOR_ART_PLACEHOLDER_RE.fullmatch`）；词汇镜像 `PRODUCT_SUCCESS_PLACEHOLDER_RE` 语义族（分隔符形态更宽容：`to[\s_-]*be[\s_-]*defined`、`n[\s/-]*a`）。
- 单一来源核验：intake 拒收（change_triage.run_triage）与 Check 32 记录校验（triage_domain.py）**均 import 消费同一函数**，无第二定义（FIX-292 履行）。
- FULL-match 语义有专门测试钉死：`test_legit_entry_containing_placeholder_word_is_not_rejected`（「Rust RFC 2333 prior_art（本设计无直接 unknown 先例，取其节结构）」通过）——诚实引用含占位族词不误拒。

### 5. 测试真实性 — PASS（变异检验实证）
- 19 新测试三类：PriorArtIntakeTests（8：空/空白/TO_BE_DEFINED/「to be defined」/待定/暂无/n\/a/N\/A/占位 拒收、混合列表单占位拒收、合法写入记录含字段、FIX 豁免披露 false、FIX 自愿携带、ratchet 子集）；PriorArtCheck32Tests（8：缺失/空列表/占位 FAIL、合法 PASS、**边界前豁免**〔含 FEAT-111 自身 10-28 形态〕、无 created_at 保守豁免、FIX 豁免、check_change_triage 集成 FAIL 判定）；PriorArtGateCliTests（3：CLI exit 2 零写入、分号切分写记录、FIX 通过）。断言具体（错误文本/文件存在性/记录内容），非恒真。
- **变异检验**：临时删除分类表 "FEAT" 词条 → PriorArtIntakeTests `FAILED (failures=5)` exit 1（测试真实依赖分类表）；精确还原后 `git diff --stat` 与变异前逐字节一致（6 文件 +457/−6）零残留，复跑 8/8 OK。

### 6. 复跑验证 — PASS（全绿，零新引入）
| 命令 | 结果 |
|---|---|
| `python -m unittest ...test_change_triage` | **Ran 139 tests / OK / exit 0**（30.3s） |
| `python -m unittest ...test_dsh_contract` | **Ran 122 tests / OK / exit 0**（12.6s） |
| `check-governance`（full 面） | **exit 0**；Check 24 无 stale pin；**Check 32 Result PASS — 0 failing criterion**；全仓 3 issues（28s evidence 1978.8KB + 28s decision 263.7KB + WARN 25 scratch——全部存量慢性面，与改动前基线 item-identical，零新引入） |
| `change-triage --help` | `--prior-art` 面在场且文案与命令文档一致（必填族/示例/拒收语义/豁免） |
| test_verify_workflow 全量 1155 | Developer 双跑 OK（323s/413s）采信（两次独立时点 + 本 Reviewer full check-governance 对 Check 32 真实仓库面复验） |

### 7. 文档对同步 — PASS
- `commands/change-triage.md`：门禁注记段 + 参数表 `--prior-art` 行 + 拒收清单 + 产出说明（增量键）四处一致更新；`adapters/dsh/skill-shims/change-triage.md` 仅描述行更新——与既有投影对形态一致（shim 为薄指针）。
- 预存漂移确认：HEAD 版参数表本就缺 `--demand-source/--demand-basis/--acceptance/--side-effects` 四历史参数行（`git show HEAD:` 实证）——**非本票引入**；按 D4 纯度未顺手修，交父裁决（F-03）。

### 8. 五维度结论 + AI 专项
| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | PASS | 前缀分类单点（task_id.split）、fail-closed 早退姿态与既有 intake 条件一致、additive 记录键、空/占位/混合三拒收路径+豁免路径全覆盖 |
| 安全性 | PASS（无新面） | 无输入解析扩展（列表字符串条目仅 strip+判定，不 eval）、无敏感数据、无权限面变化；拒收零写入 |
| 可维护性 | PASS | 单一谓词源（import 消费）、常量就近+依据注释、文档三处同步、ratchet 钉死词汇派生 |
| 性能 | PASS | frozenset 成员判定 O(1)、每任务一次；FULL-match 于短条目；无循环放大 |
| 测试覆盖 | PASS | 核心路径（4 族×required/exempt）+ 边界（空/占位/混合/含占位词的诚实引用/边界日期前后/无 created_at）+ 错误路径（exit 2 零写入）+ CLI 集成；139+122 全绿 |
| AI 专项 5 项 | mock 残留=无（真实 run_triage+CLI subprocess+临时目录）/ 硬编码返回值=无 / 幻觉 API=无（change_triage 导出与 task_priority._TASK_FAMILY_PREFIXES 实存核验）/ 未实现 TODO=无 / 过度实现=无（范围=验收本体；零使用前缀为词汇派生前向兼容且有 ratchet 约束） | |

## 二、发现清单（全部非阻断）

- **F-01 [P3]** `date.fromisoformat` 保守豁免面：`created_at` 若为 datetime 形态（含时间部）将解析失败 → 记录面豁免。现产记录均为 date-only（TRIAGE-FIX-475/FEAT-111 实读核验）；docstring 已披露保守口径、CLI 门禁为主执法面。零现况影响。
- **F-02 [P3]** 分类边界裁定：SYSGAP（系统缺口调研族）/REQ/PLAN 未入 required 表——语义上可argue设计/研究相邻。裁定已注释披露（活动分型先例）；ratchet 保证词汇派生；未来单点调整即可。零现况影响（live 记录仅 FIX/FEAT/REL/AUDIT 四族）。
- **F-03 [P3]** `commands/change-triage.md` 参数表预存漂移（4 历史参数行缺失，`git show HEAD:` 实证非本票引入）——D4 纯度下未顺手修，建议父级以独立小修（治理记录快速通道或文档票）承载。
- **F-04 [P3]** `change_triage.py` 文件尾无换行（`\ No newline at end of file`）——预存形态保持，非本票引入；后续触碰该文件时可顺手补。

## 三、硬门槛裁决

| 门槛 | 结果 |
|---|---|
| P0 阻塞数 | **0** |
| 5 维度全覆盖 | 100%（5/5 有结论） |
| 每条发现带级别 | 100%（F-01~04 全 P3） |
| 设计一致性 | TRIAGE-FEAT-111 五条：①拒收红绿（含 FIX 豁免）满足 ②Check 32 PASS+回归零退化满足 ③自身 prior-art 检查落盘（执行包 competitive_baseline+代码注释+文档三处）满足 ④文档对同步满足 ⑤独立审查即本报告 |
| AI 专项 5 项 | 全部完成、全部无发现 |

## 四、结论

**APPROVED_WITH_NOTES，unresolved_blockers=0**（notes=4，全 P3，均不要求本轮修改）。prior-art 入账门禁实现忠实于 DEC-377④ 意图（机制性倒逼终结自嗨循环）：分类表词汇派生有 ratchet、占位判定 FULL-match 单源、拒收 fail-closed 零写入、自指边界诚实（CLI 面无日期边界+记录面统一豁免+先例义务实质履行）、139+122 测试全绿、full 面 Check 24/32 PASS 零新引入。**round=0 终态（通过）**。
