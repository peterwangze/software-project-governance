# Code Review 报告 — FIX-439（R0 初审）

## 报告头

- **round**: 0（R0 初审，无前轮）
- **审查对象**: 工作树 staged 变更（未 commit），基线 HEAD `c442e07`；以仓库当前文件态实读为审查面
- **审查面声明**: 本 Reviewer 无命令通道（Bash 禁止），**全部结论基于文件态逐行实读 + 逻辑推演**；开发者声称的测试/verify 运行结果均不可复跑，逐项列入「未验证项清单」，不作为通过依据
- **事实源**: `.governance/incidents/incident-20261006-dsh-bootstrap-splice-repeat.md`（已通读）
- **实读文件**: `skills/software-project-governance/infra/sync_entry_projection.py`（全文 717 行）、`adapters/dsh/launch.py`（write_bootstrap 区段 L1660-1799 + grep 全调用面）、`skills/software-project-governance/infra/governance_store.py`（写路径相关区段 L335-460/702-860/998-1311/1324-1760）、`skills/software-project-governance/infra/tests/test_dsh_adapter.py`（L2049-2184 + 夹具 helper）、`skills/software-project-governance/infra/tests/test_verify_workflow.py`（L25004-25098 + helper）、`adapters/dsh/AGENTS.md.template`（全文）、`commands/governance-init.md`（模板段结构 grep）、仓内 `AGENTS.md`/`CLAUDE.md`/e2e fixture 入口（段边界 grep）、`skills/software-project-governance/infra/checks/projection.py`（L85-202）、`skills/software-project-governance/infra/verify_workflow.py`（FIX-439 痕迹 grep——零命中）

## 逐文件实读核验

### 1. `sync_entry_projection.py`（声称落点 ①~⑤ 全部实存）

| 声称 | 实读结果 |
|---|---|
| ① 显式终止符 | ✅ L222-223 `_H1_LINE_RE = (?m)^# [^\n]*\n`、`_HR_LINE_RE = (?m)^-{3,}[ \t]*\r?$`；L268-271 span 计算先取两终止符最小偏移为 `hard_end`，再在其内做 H2 白名单截断。**边界正确性**：Markdown 表格分隔行 `|---|`（管道开头）与 `---|---`（行尾非纯空白）均不匹配 `^-{3,}[ \t]*\r?$`——无误判；YAML front-matter 的 `---` 位于段头 cursor 之前（`search(text, cursor)` 起点后置），不命中；Setext 下划线 `---` 会被匹配但语义为「提前收敛」（不吞宿主内容，fail-closed 方向安全）；H1 判定 `# ` 行首正确（DSH 模板自身 H1 段头由 `start_match` 消费，cursor 后无段内 H1）。**终止符 no-op 声称核验**：DSH 模板（37 行全文实读）与 governance-init.md 全部 canonical 模板块（行首 `-{3,}` 全文 grep 零命中）内部均无 `---`、无段后 H1——对仓内守护面确为 no-op |
| ② `bootstrap_boundary_titles` | ✅ L230-244，H2 标题并集（`_h2_titles` 与 span 内 `group(0).strip()` 口径一致——均含 `## ` 前缀的整行 strip，两处比较口径统一） |
| ③ `bootstrap_h2_singleton_violations` | ✅ L314-333，行锚定 `(?m)^{re.escape(title)}[ \t]*\r?$` 计数，**`!= 1` 双向拒绝**（>1 防残留重复 / =0 防段丢失）——对「模板 H2 在宿主尾段同名出现」count=2 → 拒绝写入保留原文件，fail-closed 方向正确 |
| ④ `BootstrapSpliceError` | ✅ L108-113，`CanonicalSourceError` 子类；`sync_entry_projection.main` L701 捕获父类 → 结构化 ERROR exit 2，无 traceback 泄漏 |
| ⑤ `apply_entry_projection` 统一边界 | ✅ L516-518 用全部 canonical 模板（4 键）H2 并集；L530-537 写前 singleton 守护，**且守护位于 `if not dry_run` 之前——dry-run 也会预演拒绝**（优于 launch 侧，见 F-3） |

**薄指针口径不回归核验**：`plan_entry_writes` L462（sticky 检查）、`_classify_entry` L563（第二跳）、`build_sync_report` 经 `_classify_entry` 的 `None` 调用全部保留；实读仓内 `AGENTS.md`（薄指针段内纯 H3，段后直接 `## 项目质量原则`，无 `---`/H1）、`CLAUDE.md`（full 段，段后无 `---`/H1）、e2e fixture 双入口（同构）——`check-entry-bootstrap-sync` 依赖的 `build_sync_report` 行为在新终止符下零变化（文件态证）。

### 2. `adapters/dsh/launch.py` — `write_bootstrap()`

- ✅ L1718 `boundary = shared.bootstrap_boundary_titles(rendered)`（模板自身 H2 全集）+ L1719 `bootstrap_section_span(existing, boundary)`——与 `apply_entry_projection` **共用同一 `bootstrap_boundary_titles` / `bootstrap_section_span` / `replace_bootstrap_section` / `bootstrap_h2_singleton_violations` 四件套**，分叉消除（集合内容不同是正确设计：写什么段就以什么段的 H2 为边界）。
- ✅ L1754-1767：`new_text` 先在内存构造 → singleton 校验 → 违规 print ERROR + `return 1`，**`write_text` 位于 guard 之后**（L1768）——拒绝时零写入发生、原文件字节不动；`newline=""` 保持 FEAT-037 P3-4 字节纪律。
- ✅ 首/else 分支（L1769-1770）：整文件即 rendered，各 H2 天然恰 1 次，无需 guard——两条路径语义闭合。
- ✅ 既有 fail-closed 保留：existing 存在无段且非 force → 拒绝（L1721-1727）；dual-presence note 的 `bootstrap_section_span(primary_text)` 维持 None 口径（正确：canonical full 模板前半纯 H3，`### Step 0` marker 在首个 H2 前命中）。

### 3. `governance_store.py`

- ✅ **evidence md 腿**：锁内时序 L1270 build → **L1284 `_evidence_row_validator`（本票前置）** → L1285 拼字节 → L1286 `_atomic_write_bytes` → L1287 post-write reread（保留为结构校验位，DoD 4）→ L1297 `_ledger_transaction`。`_refuse` = `raise StoreError`（L374-375），被 `_returns_payload` 捕获返回结构化 payload——**拒绝时写与台账均未执行 ⇒ 零持久化 + 零台账**，顺序倒置消除成立。核验 `_build_evidence_row`（L1021-1039）内置仅 shape/newline 校验、不含内容校验——L1284 确为内容校验（目标对齐/事实依据 payload/用户影响镜像）的首个写前防线。
- ✅ **decision md 腿**：同型，L1502 前置 → L1503-1504 写 → L1505 post-write → L1519 台账。
- ✅ **JSON 腿**：dry-run L1642、实跑 L1713 `_decision_row_validator` → L1739 写——既有 build 时校验顺序未被破坏。
- ✅ `_next_row_id`（L738-753）纯读（hot 文本 + archive 扫描），前置校验前调用无写副作用；`_dry_run_append` 零写零台账（既有）。

### 4. `tests/test_dsh_adapter.py` — `BootstrapSpliceFIX439Tests`

- ✅ 断言强度：幂等用例 `read_bytes()` 全文字节比较（L2162-2164）；拒绝用例 `read_bytes() == before` 逐字节保留 + rc==1 + stderr 锚点（L2173-2180）；H2 恰 1 次 = 共享 guard + 独立 `count()==1` 双断言（L2142-2144）；宿主尾段 5 锚点逐项在位（L2147-2149）。
- ✅ 夹具隔离：`_sandbox_td()`（L57-67，系统临时目录 mkdtemp + rmtree 防护）内建 `project/tv/AGENTS.md`，零真实宿主写入；旧版本段由 rendered 头部版本号派生（`replace(match.group(1), "0.88.0")`，L2087-2090）——无字面 pin，FIX-352/353 纪律遵守。
- ✅ span 用例（L2104-2129）同时钉住「收敛于 `---` 前」与「旧段 6 个 H2 全在 span 内」两侧不变量，并端到端断言 splice 后 violations==[]。

### 5. `tests/test_verify_workflow.py` — `GovernanceStoreZeroPersistenceFIX439Tests`

- ✅ 零写入断言真实性：`target.read_bytes() == before` 字节级比较（非返回码），且 `assertFalse((gov / "governance-store-ops.json").exists())` 断零台账；夹具 `_governance_temp_dir`（L95-101）隔离。
- ⚠️ 红绿对照落点：**用例 1（目标对齐缺失）是本票 L1284 的真实红绿对照**（build 不查内容、修复前该拒绝只在 post-write reread → 行已持久化 → 必红）；用例 2（获得= 越枚举）实际被 L1188 入口镜像（锁前、FIX-405/406 既有）先拒；用例 3（裸 `|`）被 `_build_decision_row` L1331 内置 shape 校验（写前、既有）先拒——两用例在「无本票修复」世界同样绿，守护价值成立但注释声称的落点不准确（见 F-2）。

### 6. `verify_workflow.py`「零改动」声称

文件态旁证：全文 grep `FIX-439|bootstrap_section_span|bootstrap_boundary_titles|bootstrap_h2_singleton` **零命中**；其 bootstrap 面经 `checks/projection.py` 间接消费 `build_sync_report`（该文件非本票修改面）。对 HEAD 的 diff 无法执行（无命令通道），列未验证项。

## 5 维度逐项结论

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | **通过**（1 项既有 P2 缺口，非本票引入） | 终止符边界逐类推演正确（表格行/`---|---`/front-matter/Setext 均不误伤或不安全方向）；终止符对全部仓内守护面 no-op（实读证）；guard 双向 `!=1` 拒绝 fail-closed；md 双腿校验前置 + 拒绝零持久化零台账（StoreError 机制推演）；JSON 腿未破坏；幂等由字节等价闭合。缺口见 F-1（CRLF，既有）/F-4（窄缝隙） |
| 安全性 | **通过** | `re.escape` 防模式注入；无硬编码密钥/网络/命令面；拒绝路径零写（用户数据保护正确）；原子写+锁+台账既有结构未动；`BootstrapSpliceError` 走结构化 fail-closed 出口 |
| 可维护性 | **通过** | splice 四件套单一实现于 sync_entry_projection，两调用方共享——正是 incident §8 第 1 条的根治形态；异常子类化复用既有 catch 面；注释全部锚定 incident 章节，可追溯性优。小疵：`_match_newlines` 在文件路径链上为死分支（F-1 关联） |
| 性能 | **通过** | span 双终止符各单次线性 search；singleton 校验 O(H2 数 × 文本长) 常数乘线性；validator pre+post 双跑为设计意图（结构 parity），开销可忽略；无 N+1、无新循环 I/O |
| 测试覆盖 | **通过**（2 项 P3 缺口） | 4+3 用例核心路径/边界/错误路径全覆盖，字节级断言真实；缺口：CRLF 宿主形态无用例（F-1 关联）、纯 row-level 拒绝（仅 pre-write validator 可拦的输入类）仅用例 1 一条（F-2） |

## 发现列表

| # | 文件:行号 | 级别 | 问题 | 依据 | 修复建议 |
|---|------|------|------|------|---------|
| F-1 | `adapters/dsh/launch.py:1709`（及 `sync_entry_projection.py:247-250` 关联） | **P2** | CRLF 宿主 AGENTS.md 首次 bootstrap 写入会**全文 EOL 翻转**：`read_text` 默认 universal newlines 把 `\r\n` 归一为 `\n`，`write_text(newline="")` 落盘 LF——非段字节被改写，「non-bootstrap content preserved」在字节层面不成立；`_match_newlines` 的 `\r\n` 检测在文件路径链上永不触发（死分支）。**既有缺陷**（incident 引用的旧代码同构，FEAT-037 P3-4 只修了 write 侧），非本票引入、不破坏本票验收标准②（第二次起字节不变仍成立） | Python TextIOWrapper `newline=None` 读取归一化语义 + 两函数实读 | 读侧改 `open(path, encoding="utf-8", newline="")`（`Path.read_text` 的 newline 参 Python 3.13 才有）保留原始 EOL；作为独立小票遗留 |
| F-2 | `tests/test_verify_workflow.py:25054-25094` | **P3** | 用例 2/3 注释声称击中本票修复点，实际拒绝点在既有防线（L1188 入口镜像 / `_build_decision_row` L1331 内置 shape 校验），「无本票修复必红」仅用例 1 成立——红绿对照面收窄 | 推演两用例输入在各校验层的命中顺序 | 后续补 1 条纯 row-level 拒绝用例（如 目标对齐 <30 字符：入口镜像不查、build 不查、仅 L1284 可拦），使前置校验独立红绿 |
| F-3 | `adapters/dsh/launch.py:1728-1736` | **P3** | dry-run 在 singleton guard 之前返回：dry-run 报「planned write」而实跑可能被 guard 拒绝 exit 1（Scenario C 升级 A 步先 dry-run 后实跑的用户感知分叉）；`apply_entry_projection` 的 dry-run 已做 guard 预演，两处不一致 | 两函数 dry-run 分支位置对比（launch L1728 早退 vs apply L530-537 先 guard） | launch dry-run 分支补 replace + guard 预演（违规时打印预期拒绝） |
| F-4 | `skills/software-project-governance/infra/sync_entry_projection.py:314-333` | **P3** | guard 覆盖窄缝隙：跨版本 H2 改名 + 已损坏文件的双重前提下，旧残留段截断点之后的旧 H2 若全部不在新模板 H2 集，singleton 通过、旧尾巴残留（部分复发形态）。触发前提极窄（incident 实际形态为同名超集，span 整体覆盖自动治愈，已验证） | 白名单截断 + guard 检查集合定义推演 | 未来增强：splice 后追加断言「span 终点后不得紧跟 bootstrap 段内 H2 集合中的任何标题」或 Governance Bootstrap 标题行全文恰 1 次 |
| F-5 | `adapters/dsh/launch.py:1769-1770` | **P3** | `--force` 且无 bootstrap 段时整文件覆盖丢弃宿主全部内容（既有显式授权语义，但丢弃面大于 splice 语境直觉） | 分支实读 | `--force` help 文案明示「整文件覆盖」语义 |
| F-6 | `tests/test_verify_workflow.py:25052/25071/25094` | **P3** | 零台账断言硬编码 `governance-store-ops.json` 文件名：若 `_ledger_path` 改名，`assertFalse` 恒真静默失效 | 断言与 `_ledger_path` 解耦关系 | 改从 `governance_store._ledger_path(gov)` 取路径再断言不存在 |

## AI 代码专项 5 项结论

1. **mock 残留**：无——新增 7 用例零 mock，直调真实模块与真实临时目录（`test_dsh_adapter.py` 顶部 `mock.patch` import 为既有面）✅
2. **硬编码返回值**：无——guard/边界/校验全部返回真实计算结果 ✅
3. **幻觉 API**：无——`bootstrap_boundary_titles`/`bootstrap_h2_singleton_violations`/`BootstrapSpliceError` 及全部 `shared.*` 调用在 sync_entry_projection.py 逐一实存 ✅
4. **未实现 TODO**：无——修改面 grep 无 TODO/FIXME 残留 ✅
5. **过度实现**：无——实现面与 incident §8 五条建议一一对应，`bootstrap_boundary_titles(*sections)` 可变参恰好支撑两个调用点，无多余抽象 ✅

## 蓝军挑战（对抗性推演）

- **双重段头损坏文件**（旧段也带 H1 头、两段间有 `---`）：span 在首个 `---` 截断只换第一段 → 第二段 H2 双份 → guard 拒绝零写入 ✅ fail-closed 兜底成立
- **incident §2 实际损坏形态**（新段+无头旧段相连、H2 同名超集）：白名单使 span 跨过新段整体延伸至 `---` 前，一次 splice 整体替换 = **自动治愈** ✅
- **段中部代码块引用模板文本/H2**：guard 的行锚定计数照常命中双份 → 拒绝 ✅（且为既有 span 风险提供新兜底）
- **空文件/无段 existing**：非 force 即拒 ✅；**`_next_row_id` 写前置副作用**：纯读核验 ✅；**post-write reread 拒绝仍发生在写入后**：属并发披露语义（`manual_intervention`/DISCLOSING），与本票修复的「校验拒绝零持久化」（`schema_violation` 类）分类不同、设计上均正确 ✅
- **front-matter/表格分隔行/Setext 误判**：逐一推演不命中或不安全方向（见维度 1）✅

## 硬门槛裁决表

| 门槛项 | 阈值 | 裁决 |
|---|------|------|
| P0 阻塞问题数 | = 0 | ✅ **0** |
| 5 维度全覆盖 | = 100% | ✅ 逐项有结论（上表） |
| 每条发现标注级别 | = 100% | ✅ F-1~F-6 全部标注（P2×1 / P3×5） |
| 设计一致性检查 | 已完成 | ✅ incident §8 五条建议方向逐条落地；薄指针 `None` 口径三处保留；governance_store JSON 腿既有顺序未破坏 |
| AI 代码专项 5 项 | 全部完成 | ✅ 逐项有结论 |

## 未验证项清单（无命令通道，如实披露——不作为通过依据）

1. 开发者全部运行声称：verify 全套 PASSED、check-cross-references/check-manifest-consistency/check-entry-bootstrap-sync PASS、`test_verify_workflow` 净跑 2 failed（披露集预存）/1059 passed、`test_dsh_adapter` 59 passed + 3 subtests、全套件 84 文件 11 failed/4714 passed、archguard-ratchet 5 violations 预存、clean-tree stash 对照——**均不可复跑**
2. `verify_workflow.py` 对 HEAD `c442e07` 的零改动——无 git 通道；旁证：文件无 FIX-439 痕迹、无 span 直调（内容级证据，非 diff 级）
3. 红绿对照数字（span (0,2482)→(0,2424)、evidence +284B→0、首写双份→恰 1 次）——不可复跑；已用同构夹具的测试断言 + 实现推演替代验证
4. 7 个新增用例的实际执行结果——不可复跑；断言与实现逐行对合，逻辑推演预期全绿

## 最终结论

# APPROVED_WITH_NOTES（unresolved_blockers = 0）

**理由**：审查面五个文件全部逐行实读——incident 三缺陷族的修复在文件态全部成立（①统一段边界+显式终止符+span 收敛 ②幂等字节不变 ③段后置校验拒绝保留原文件 ④md 双腿校验前置·拒绝零持久化零台账·JSON 腿未破坏 ⑤宿主三项校验面固化 ⑥文件态零退化信号），P0=0、P1=0；唯一 P2（F-1 CRLF EOL 翻转）为既有缺陷、非本票引入且不破坏本票验收标准，建议独立小票遗留；P3×5 为测试有效性与边角增强建议。运行结果声称不可复跑项已全部如实标注，通过依据独立于开发者声称。

**遗留建议**（不阻塞）：F-1（独立票：读侧保留原始 EOL）> F-2（补纯 row-level 拒绝用例）> F-3（dry-run 预演 guard）> F-4/F-5/F-6。

---

**给 Coordinator 的返回摘要**：完成状态 = R0 审查完成；结论 = **APPROVED_WITH_NOTES，unresolved_blockers=0**；发现 = P2×1（既有，建议独立票遗留）+ P3×5；未验证项 4 类已披露（全部为不可复跑的运行声称，通过依据为文件态实读+逻辑推演）；本报告全文交由 Coordinator 经 review-record CLI 机录持久化（Reviewer 不写 .governance/）。
