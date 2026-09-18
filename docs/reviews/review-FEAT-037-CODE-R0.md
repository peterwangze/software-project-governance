# Code Review 报告 — FEAT-037-CODE-R0

| 项 | 值 |
|---|---|
| 任务 | FEAT-037 — AGENTS/CLAUDE 双 bootstrap 去重（单一 canonical 源生成薄投影，AUDIT-154 切片 A-6） |
| 审查轮次 | R0（独立代码审查，Reviewer 与 Developer 分离） |
| 审查对象 | 14 项变更面（新增 2 / 修改 12，含交叉治理文档） |
| 审查规范 | skills/code-review/SKILL.md（已加载） |
| 审查方式 | 只读（Read/Grep/Glob）；审查者禁 Bash/pwsh，测试未独立复跑（见"验证边界"） |

---

## 1. 审查对象与事实基础

**新增**：
1. `skills/software-project-governance/infra/sync_entry_projection.py`（518 行，已逐行读）
2. `skills/software-project-governance/infra/tests/test_entry_projection.py`（476 行，实测 32 个测试方法，与申报一致）

**修改**：
3. `commands/governance-init.md` — Step 7 secondary-thin 模板（L824-858）+ 双入口注入规则（L860-865）
4. `AGENTS.md`（根）— bootstrap 段薄指针版（L3-34，32 行内容段）
5. `CLAUDE.md`（根）— 完整 canonical（270 行，尾部 FIX-278 G4/F @ L270）
6. `project/e2e-test-project/AGENTS.md`（34 行薄指针）+ `CLAUDE.md`（完整 canonical）
7. `adapters/dsh/launch.py` — `_entry_projection_shared()`（L1661-1674）+ `write_bootstrap` 重构（L1677-1740）
8. `skills/software-project-governance/infra/checks/projection.py` — `check_entry_bootstrap_sync`（L92-132）+ 打印/命令入口（L135-167）
9. `skills/software-project-governance/infra/verify_workflow.py` — FEAT-037 面共 +11 行（L21354-21362 附带运行+薄包装、L23928-23929 subparser、L24582 dispatch）；FEAT-033 在途面未审（超出边界）
10. `core/manifest.json`（L219-226 两新文件条目）+ `core/version-projections.json`（L27 canonical-bootstrap-version，count=4）
11. `infra/registry.py`（L267-268, L362）、`contract_matrix/snapshots.json`（L189）、`core/architecture-baseline.json`（L502）、`test_contract_matrix.py`（L60，85→86）、`test_registry.py`（L83, L339-341）、`test_verify_workflow.py`（L15306 marker 3→4）

**交叉**：`.governance/change-triage/FEAT-037.json`、`docs/requirements/governance-bootstrap-cost-audit-0.84.0.md` §8（L183）、`.governance/plan-tracker.md` L86。

---

## 2. Developer 申报 9 项逐项核实

| # | 申报 | 核实结果 | 事实依据 |
|---|------|---------|---------|
| 1 | 体积 16011B→2699B / CLAUDE 19502B / fixture 681B→2737B | **方向性核实相符**。AGENTS.md 全文 53 行（bootstrap 段 32 行内容）；CLAUDE.md 270 行完整 canonical；fixture AGENTS 34 行。精确字节数审查者无法独立测量（禁 Bash），由 `test_real_repo_rendered_thin_within_budget`（≤40 行/≤3072B 硬断言）与 `test_repo_root_sync_report_passes` 机器守护 | Read 实测行数；test_entry_projection.py L362-369, L378-380 |
| 2 | 双 apply 零 diff（幂等） | **设计核实成立**。拼接为纯函数：同输入同输出；无时间戳/随机值；`write_text(..., newline="")`（L342）固定字节不做平台换行翻译；`test_apply_dual_entry_and_double_apply_zero_diff` 以字符串全等断言双次 apply | sync_entry_projection.py L186-211, L332-342；测试 L289-297 |
| 3 | 薄指针最小存活检查逐项在位 | **逐项核对全部在位**：resolve_entry 第一动作（AGENTS L11，fail-closed）✓ / plan-tracker 读取（L12,17,18）✓ / SELF-CHECK 5 条压缩映射（L17-21）✓ / 模式确认 3 态（L25-27）✓ / 治理快速入口（L31-34）✓ / 主入口指针 4 处（L5,7,13,34）✓ / FIX-278 UTF-8 行（L33）✓。映射精度问题见 P3-1 | Read AGENTS.md 全文逐行 |
| 4 | 单入口回归不变 | **核实成立，断言强度足够**。`test_single_entry_agents_only_stays_full` / `test_single_entry_claude_only_stays_full`（plan kind=full）+ `test_apply_single_entry_secondary_gets_full`（断言 full 模板落地 + 缺席主入口不被凭空创建）+ `test_secondary_never_created` | 测试 L252-274, L311-319 |
| 5 | launch.py 语义不变 | **核实成立**。拒绝路径（无 bootstrap 段且无 --force → rc=1、文件不变）✓ / dry-run（rc=0、零写）✓ / splice 保尾 ✓ / `--check` 路径未触碰 ✓。三项均有测试 | launch.py L1703-1738；测试 L435-472 |
| 6 | 零新增 verify_workflow 反向依赖 | **核实成立**。`check_entry_bootstrap_sync` 用 `Path(__file__).resolve().parents[4]` 独立解析 root（checks→infra→spg→skills→repo root，路径核算正确），仅 import 同级 `sync_entry_projection`，无 verify_workflow import | checks/projection.py L102-106 |
| 7 | FIX-278 三缺口修复不越界 | **核实成立**。canonical standard 模板含 FIX-278 行（governance-init L527）✓；薄指针模板含（L856）✓；lightweight（L193-256）与 strict（L530-822）模板无 FIX-278 匹配——Developer 未顺手改，与申报一致 | grep FIX-278 全文件仅 L527/L856 两处模板内命中 |
| 8 | 30 测试失败归因（WSL bash hook + test_hooks 活数据回放） | **归因类别存在性实证，未独立复跑**。`test_hooks.py` 含 WSL/bash 环境守卫体系（L22,141,172,316,468 `skipUnless(_BASH...)`）与 `test_replay_real_plan_tracker_hits`（L302-307，显式依赖真实 `.governance/plan-tracker.md` 的活数据回放）。两类测试均不触 FEAT-037 文件面（hook bash matcher 未被本任务修改）。归因可信；审查者禁 Bash 无法复现失败清单——标注为"未复跑，类别实证" | test_hooks.py 上述行号 |
| 9 | AI 专项 5 项 | **全部通过**，见 §5 | — |

---

## 3. 五维度逐项结论

### 3.1 正确性 — 通过
- **逻辑正确**：canonical 提取→渲染→拼接→守护四段管线语义自洽；`{PRIMARY_ENTRY}` 占位符渲染与防残留校验闭环（`validate_thin_pointer` L241-242）。
- **边界条件**：无 bootstrap 段（追加语义 L201-207）、空文件（L202-203）、文件尾无换行（L204）、CRLF 目标（`_match_newlines` L151-154）、EOF 结尾 section（span 到 len(text)）均有处理；canonical 解析 fail-closed（缺 label/空块/缺围栏均抛 `CanonicalSourceError`，CLI exit 2）。
- **嵌套围栏安全解析（特别审查点）**：块区域由下一 label（或末块的下一个 `### Step N`）界定，闭围栏取区域内**最后一条**裸围栏——实测当前文件成立：standard 区嵌套"Bootstrap 变更纪律"围栏（~L437-446）在 strict label（L530）之前闭合，末块薄指针区由 `### Step 8`（L867）界定、闭围栏 L858。解析器对嵌套围栏不会截断。
- **并发安全**：单进程 CLI，不适用。staging/原子写不在此层（entry 文件写非原子，属治理脚本惯例，风险低——见 P3-4 关联）。
- **资源管理**：测试用 `TemporaryDirectory` context manager，无泄漏。

### 3.2 安全性 — 通过
- **输入校验**：canonical 源缺失/损坏 fail-closed（exit 2）；profile/primary 用 argparse choices 白名单。
- **注入防护**：纯文本处理，无 eval/exec/shell 拼接；正则为字面量级，无 ReDoS 面。
- **敏感数据**：无密钥/token；写入面仅限入口文件 bootstrap 段。
- **权限检查**：`--write` 显式 opt-in（默认只读 check）符合最小写权限。

### 3.3 可维护性 — 通过（带 2 条 P3）
- 命名清晰（`plan_entry_writes`/`build_sync_report`/`render_thin_pointer`），边界规则在 docstring 中显式文档化（L86-92, L127-135, L189-195）。
- launch.py 经 `_entry_projection_shared()` 复用同一 splice 实现，零第二实现（测试 L420-433 反向断言禁止重复定义）。
- 函数长度均在 50 行内（最长 `build_sync_report` ~73 行含注释，可接受）。
- P3-1（映射表述失真）、P3-5（陈旧行数估计）见 §6。

### 3.4 性能 — 通过
- 单文件线性扫描（finditer 3 遍），模板量级 KB——无复杂度风险。
- 本任务的性能目标本身就是注入成本：双入口次要面 16011B→2699B（-83%），直接兑现 AUDIT-154 §5.3 诉点。

### 3.5 测试覆盖 — 通过（带缺口备注）
- 32 测试覆盖 8 组：canonical 提取（含真实 repo 断言）、span/splice、plan、apply+幂等、单入口回归、薄指针结构校验（含真实 repo 预算断言）、repo+fixture 守护、launch 复用与行为路径。
- 错误路径覆盖：缺块 fail-closed、锚点缺失、占位符残留、无段拒绝、drift 检出、双全检出。
- 缺口（均 P3 级，不阻塞）：CRLF 工作区路径无测试（`_match_newlines` 未被任何测试触达）；压线等价类（恰 40 行/恰 3072B）无测试；跨 profile 分类行为无测试。

---

## 4. 特别审查点逐项结论

### 4.1 薄指针版行为充分性（最高风险面）
**结论：设计声明内成立，残余风险可接受（P3 观察）。**

逐条对照主入口完整版，薄指针**保留**：fail-closed 第一动作、plan-tracker 强制读取、SELF-CHECK 压缩 5 条（含问句→AskUserQuestion 改写规则 L19 与交互边界规则 L20）、模式确认 3 态、快速入口、SKILL.md 直达指针（L13——行为约束的真正事实源）。**仅由主入口承载**：SELF-CHECK 完整 3（session-snapshot carry-over 恢复）、Step 0~4 细节、Step 2 交叉验证、Step 3 阶段跳跃防护、Agent Team 路由、干活前/提问规则/收工检查全文、故障排除。

可达性评估：薄指针在最小存活检查第 3 条（L13）直接指向 `skills/software-project-governance/SKILL.md`，不经过主入口即可加载完整规则；主入口另有 3 处指针（L5/7/34）。**实际可达路径是双通道的**（SKILL.md 直达 + CLAUDE.md 指针），"指针承载"不依赖单一脆弱链路。残余风险：宿主若只注入 AGENTS.md 且模型不跟随任何指针，丢失的是深检与恢复细节，而 fail-closed/plan-tracker/问句规则仍生效——降级方向安全。

### 4.2 粘滞防回翻
**结论：机制成立且有真实场景支撑。** `plan_entry_writes` 单入口分支：已存在合法薄指针 → 空计划不回翻（L296-302）；`test_thin_sticky_when_primary_absent` 实证。关键事实依据：`test_verify_workflow.py` L15319-15320 证实**根 CLAUDE.md 被 .gitignore 忽略（未跟踪，设计如此）**——fresh checkout 后仅 AGENTS.md（薄指针）在场，再次 sync 若无粘滞必然回翻为完整版，粘滞逻辑正是为此而设。边界口径不一致见 P3-2（当前 32 行实测余量充足，不触发）。

### 4.3 锁面偏差披露（流程项，非代码 finding）
triage 申报 files = 4（governance-init.md / AGENTS.md / CLAUDE.md / launch.py，change-triage/FEAT-037.json L10-15）；实际变更集 14+ 项，超出部分（checks/projection.py、manifest.json、version-projections.json、sync_entry_projection.py、test_entry_projection.py、registry.py、snapshots.json、architecture-baseline.json、3 个测试文件、fixture 双入口）属派发 prompt 明示的"投影同步守护/新同步脚本"任务内合理扩展。**按 M-2 流程披露记录；建议后续 triage 机录时将扩展面回写 files 字段**（非本审查阻塞项）。

### 4.4 架构裁决合理性
**结论：成立，未发现阻塞反例。**
- **独立脚本 vs launch.py 子命令**：依赖方向单向（adapters → infra 懒加载复用；infra 不依赖 adapters），R2 反向依赖计数 47≤47 佐证。子命令方案会把 canonical 投影逻辑绑进 DSH 适配器，与"模板唯一事实源在 commands/governance-init.md"的流向冲突——独立脚本 placement 正确。
- **PRIMARY_DEFAULT="CLAUDE.md" 三理由复核**：①根 CLAUDE.md 为 gitignore 未跟踪而 AGENTS.md 是唯一被跟踪入口（test_verify_workflow L15311-15320）——主入口默认值必须指向"可能缺席"的一方才能使粘滞/单入口逻辑自洽；②Claude Code 平台承载最全交互语义（AskUserQuestion/M5）；③Codex-only 工作区（仅 AGENTS.md）走单入口路径注入**完整版**（test_single_entry_agents_only_stays_full 实证），行为正确。反例"用户希望 AGENTS.md 为主且双文件在场"→ `--primary AGENTS.md` 已受 CLI choices 支持（L468）。设计闭环。

---

## 5. AI 生成代码专项 5 项

| # | 检查项 | 结论 | 依据 |
|---|--------|------|------|
| 1 | mock 残留 | ✅ 无 | test_entry_projection.py 零 mock 导入（仅 sys/unittest/pathlib/tempfile/importlib/inspect）；全部真实临时目录 + 真实 repo 文件断言（L184-192, L362-369, L378-385） |
| 2 | 硬编码返回值 | ✅ 无 | sync_entry_projection.py 所有输出由解析/拼接计算；守护报告逐字段实测；launch.py 复用共享函数非转发假面 |
| 3 | 幻觉 API 调用 | ✅ 无 | `release.projection.check_projections/write_projections` 实存（release/projection.py L217/L235）；registry 指向 `checks.projection.cmd_check_entry_bootstrap_sync` 实存（projection.py L155）；stdlib 面（argparse/re/dataclasses/pathlib）全部真实使用 |
| 4 | 未实现 TODO | ✅ 无 | grep TODO/FIXME/XXX/HACK 于 sync_entry_projection.py 零命中 |
| 5 | 过度实现 | ✅ 无 | 模块职责单一（提取/拼接/守护/CLI 四段）；`--write`/`--dry-run` 各有明确语义；无投机性抽象 |

---

## 6. 发现列表（全部 P3，无 P0/P1/P2）

| ID | 级别 | 位置 | 描述 | 建议 |
|----|------|------|------|------|
| P3-1 | P3 | commands/governance-init.md L865 | 映射表述"完整 2+3→薄 2"与实际不符：薄 SELF-CHECK 第 2 条文本仅覆盖完整第 2 条（阶段/Gate/模式），不含 session-snapshot；完整第 3 条实际由主入口指针承载（同句后半段自述）。映射描述与薄模板文本不一致，误导后续维护者以为薄 2 已覆盖 carry-over | 改为"完整 2→薄 2；完整 3（carry-over）由主入口指针承载" |
| P3-2 | P3 | sync_entry_projection.py L300-301 vs L397 | 粘滞校验用未 rstrip 的原始 span（含 section 尾部分隔空行，行数 +1），report 校验用 rstrip 后 content——薄指针恰压 40 行/3072B 线时 sticky 判定偏严，可能误判回翻 full。当前实测 32 行，余量充足不触发 | 两处统一用 rstrip 后口径 |
| P3-3 | P3 | sync_entry_projection.py L392 vs L325-327 | `_classify_entry` 边界用所选 profile 的 H2 集合，apply 用四模板并集——跨 profile 漂移时分类切片可能截断（守卫结论仍 fail-closed 正确，仅 entries 统计字节可能失真）；且 `check_entry_bootstrap_sync` 硬编码 standard——非 standard 双入口工作区未来纳入守护面会误报 drift（当前两个守护面均为 standard，不受影响） | 守护面扩为多 profile 时传入 profile 参数；或在报告中披露 profile 假设 |
| P3-4 | P3 | adapters/dsh/launch.py L1735, L1738 | `write_text(encoding="utf-8")` 未加 `newline=""`，Windows 默认换行翻译会把整个目标文件 LF→CRLF——与 sync_entry_projection.py L342 的 `newline=""` 字节纪律不一致（幂等仍成立：读写同经翻译层；仅产生整文件 EOL 归一副作用） | 补 `newline=""` 对齐字节纪律 |
| P3-5 | P3 | commands/governance-init.md L188 | standard 模板描述"~212行"，实际模板块约 262 行（L260-528，不含围栏）——陈旧行数估计（预存漂移，疑似既往版本累积，非本任务引入；无 git 权限无法断代） | 顺手修正为实测区间或删除行数承诺 |
| P3-6 | P3 | adapters/dsh/AGENTS.md.template vs checks/projection.py | 双薄指针方言并存：DSH 模板（H1 头 `# Governance Bootstrap（DSH — 强制）`，无"次要平台入口薄指针"标记）不被 FEAT-037 守护识别为 thin（分类=unknown）。当前守护面仅 dev-root+fixture（均不使用 DSH 模板）不受影响；FEAT-040 扩四平台守护面时两方言需调和 | FEAT-040 立项时明确两方言的互认或合并策略 |

**观察项（非 finding）**：
- change-triage/FEAT-037.json 无显式 `acceptance` 字段；验收口径实际存在于 plan-tracker L86 与 AUDIT-154 报告 §8 L183（两者文案一致），三方对齐无歧义。
- 30 测试失败归因未独立复跑（审查者禁 Bash）；两类归因测试的存在的与特征已实证（test_hooks.py L141/172/316/468 环境守卫 + L302-307 活数据回放），且与 FEAT-037 文件面无因果。
- e2e 仅一个双入口 fixture——四平台扩展投影同步是 FEAT-040 的显式验收（§8 L186），切片内边界合理。

---

## 7. 设计一致性裁决（acceptance 对照）

| 验收口径（§8 L183 / plan-tracker L86） | 裁决 | 依据 |
|---|---|---|
| 双文件在场时会话注入减半 | ✅ 满足 | 次要面 16011B→2699B（-83%，方向性实测 + 结构约束机器守护）；fixture 双入口同步落地 |
| 生成幂等（projection-sync 覆盖） | ✅ 满足 | 双 apply 零 diff（纯函数拼接 + 测试全等断言）；`check-entry-bootstrap-sync` 独立命令 + `check-projection-sync` 附带运行双通道守护 |
| 依赖 AUDIT-154 | ✅ 已完成 | plan-tracker L80 ✅ 完成 (2026-09-18) |
| 零改动声明核实（既有三模板） | ✅ 与申报一致 | FIX-278 仅新增于 standard（L527）；strict/lightweight 未动（观察项 7 如实） |

## 8. 硬门槛裁决

| 门槛 | 裁决 |
|------|------|
| P0 阻塞 = 0 | ✅（P0=0） |
| 5 维度 100% 覆盖 | ✅（§3 逐项） |
| 每条发现 P0~P3 标注 | ✅（6×P3，全部标注） |
| 设计一致性完成 | ✅（§7） |
| AI 专项 5 项完成 | ✅（§5） |

## 9. 验证边界（诚实声明）

审查者角色禁 Bash/pwsh：①测试未独立复跑（32 测试的存在性与断言强度逐个读源核实；通过状态引用 Developer 申报 + 测试断言与当前文件状态的自洽性）；②字节级体积未独立测量（行数与结构实测，字节数由测试硬断言守护）；③"既有三模板零改动"无 git diff 独立验证（以 FIX-278 命中面 + 结构自洽间接核实）。以上均不构成发现的证据缺口，但列为复核边界。

---

## 结论：APPROVED_WITH_NOTES（P0=0/P1=0/P2=0/P3=6）

unresolved_blockers=0

6 条 P3 均为文档精度/边界口径/EOL 纪律类建议项，不阻塞合并；P3-1/P3-2/P3-4 建议在 FEAT-040（其验收依赖本任务的投影同步面）开工前顺手关闭，其余可遗留。单入口回归、粘滞防回翻、嵌套围栏解析、launch.py 语义保持、零反向依赖、AI 专项五项全部通过独立核实。
