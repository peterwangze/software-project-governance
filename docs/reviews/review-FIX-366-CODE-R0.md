# Review — FIX-366 · Code Review · R0

| 项 | 值 |
|---|---|
| 任务 | FIX-366 — release/projection.py 两遍 plan（byte_copy 同批重叠旧态）+ CRLF 连带根因修复 |
| Reviewer | Code Reviewer Agent（串行单席 R0） |
| 依据 | agents/code-reviewer.md + skills/code-review/SKILL.md（均已读） |
| 审查对象 | `docs/reviews/diff-FIX-366.patch`（全文）· `skills/software-project-governance/infra/tests/test_release_projection.py`（全文，untracked）· `skills/software-project-governance/infra/release/projection.py`（修改后全文）· `.governance/change-triage/FIX-366.json` · `skills/software-project-governance/core/version-projections.json`（生产 registry，用于暴露面核实） |
| 结论 | **APPROVED_WITH_NOTES** · **unresolved_blockers=0** · P0=0, P1=1, P2=1, P3=3 |

---

## 一、特别复核点裁决

### 1. 两遍 plan 正确性 — ✅ 通过

**Pass 1（projection.py L190-223）与原 Pass 内计算逐行等价（仅位置移动）**，逐行比对 diff 删除段与新增段：

- `structured_json`：`json.loads(target.read_text(utf-8))` → `_json_pointer_set(deepcopy(...), pointer, version)` → `json.dumps(ensure_ascii=False, indent=2)+"\n"` → encode — **逐 token 一致**（旧 diff L54-56 ≡ 新 L206-208）。
- `transformed_text`：pattern 类型检查 / replacement `{version}` 替换 / `re.subn(count=int(item.get("count",1)), flags=re.MULTILINE)` / count-mismatch ValueError — **逐 token 一致**（旧 diff L59-67 ≡ 新 L214-222），仅两处差异均为有意为之：
  - `read_text` → `read_bytes().decode`（见复核点 2，缺陷机理必需）；
  - count-mismatch 报错消息 `target_rel` → `item.get('target')` — 二者同值（L230 `target_rel = item.get("target")`），消息输出不变。
- 错误升级时序差异（Pass 1 使 pattern 校验错误先于 byte_copy source 缺失检查，不再按列表位置交错）：异常类型均为 ValueError，调用方捕获面一致（check_projections L438 / write_projections L470 均含 ValueError）→ 契约不可观测差异。

**Pass 2 命中/fallback（L225-245）**：
- 命中键一致性：`resolved` 键 = Pass 1 `_safe_repo_path(root, item.get("target"), must_exist=True)` 返回值（L204）；Pass 2 `source`/`target` 走同一函数同一 root（root 于 L118 一次性 resolve）→ 同配置字符串必得相等且同哈希的 Path 键，命中可靠。
- `content = resolved[source] if source in resolved else source.read_bytes()`（L238）：未命中（非本批投影目标）回落磁盘原始字节 = 原行为；命中 = 本批 resolved 内容。
- `resolved[target]`（L240/242）无 KeyError 面：凡 Pass 2 放行的 dict 条目（kind ∈ {structured_json, transformed_text}）Pass 1 必已写入；非 dict / 未知 kind 在两遍均前置 raise。
- **顺序无关性达成**：Pass 1 先全量 resolve，byte_copy 无论列于 transformed 之前/之后均命中——原缺陷正是"同批重叠与顺序无关地失败"（旧实现即便 transformed 在前，byte_copy 仍读磁盘）。生产 registry 实证该重叠真实存在：`canonical-bootstrap-version`（transformed_text，target=`commands/governance-init.md`，count=3，L124-131）与 `fixture-command-governance-init`（byte_copy，source=`commands/governance-init.md`，L132-137）即同批重叠对。
- 目标冲突检测（L232-233）仍在任何写之前 raise，防护不降级。
- I/O 面无放大：transformed/structured 目标仅 Pass 1 读一次（Pass 2 复用内存）；非重叠 byte_copy 照旧读一次磁盘。

### 2. CRLF 修复语义 — ✅ 通过（机理必需，非绕过）

- **缺陷机理确认**：旧 `read_text(encoding="utf-8")` 走 universal-newlines，`\r\n→\n` 静默发生在**内容解析层**，`transformed.encode("utf-8")` 后 resolved 内容整体 LF 化。对生产 registry 中唯一的真实重叠文件 `commands/governance-init.md`（CRLF，count=3 的 bootstrap-version 行），两遍修复若保留 read_text，版本 bump 将把**整文件**重写为 LF——声明的投影只授权替换 3 个版本行，其余每行的字节都被静默改写（P-v1 P7 数据保真违背 + git 全文件噪音），且其 byte_copy 镜像落盘 LF 后与 CRLF 语义漂移。`read_bytes().decode` 使 resolved 内容保原生换行，pattern（`^> @bootstrap-version: …`，无 `$` 锚、不含 `\r`）仅触碰版本 span，`\r` 全保真 → byte_copy 镜像与目标**字节全等**（`_projection_matches` byte_copy 分支为精确等值）。结论：read_bytes 是修复重叠机理的必要组成，非绕开手法。
- **无 skip/mock/放宽/schema 变更**：diff 未触碰契约校验、`declared_legacy_snapshots`、`_projection_matches`；测试无 skip/mock。
- **行为变化面（披露性核实）**：(a) `$` 锚定的 pattern（生产中 hook-* 四条，`^# @version: …$`）作用于 CRLF 文件时，`$` 匹配不到 `\r` 前 → count-mismatch ValueError → fail-closed 响亮 BLOCKED（优于旧版静默 LF 化整文件）；当前 hook 文件为 LF，无生产影响。(b) 非法 UTF-8：`UnicodeDecodeError ⊂ ValueError`，两调用方 except 面均覆盖 → BLOCKED，无未捕获异常。(c) 负例/noop 覆盖：test 3（非重叠回落原始字节，含非 UTF-8 字节 `b"\x00raw-bytes\n"` 透传）+ test 2（二次 write `written==0` 幂等）在位——**但均为 LF fixture，CRLF 路径本身无自动化测试**，见 F-1。
- 开发者声称的 stash 隔离复验（两遍修复保留 read_text 则红、read_bytes 则绿）为 Developer 上报证据，本席无 Bash 权限未独立复跑；机理推导与代码读审一致，采信并标注来源。

### 3. 不变项 — ✅ 全部零改动

| 不变项 | 核实 |
|---|---|
| 函数签名/返回类型 `build_projection_plan(root: Path, config_path: Optional[Path] = None) -> tuple[str, List[PlannedWrite]]`（L117） | ✅ diff 未触碰；返回仍为 sorted(writes) 的 PlannedWrite 列表（L246） |
| `PlannedWrite` dataclass（L17-22） | ✅ 未触碰 |
| schema/契约校验段（L120-188：schema_version、projection_ids/kinds/inventories 三重契约比对、inventory AST 校验、authority 检查） | ✅ 两个 hunk（@@ -187,6 +187,41 @@ / @@ -200,21 +235,11 @@）均始于 L187 之后，该段零改动 |
| `_projection_matches`（L31-34） | ✅ 未触碰 |

### 4. 测试强度 — ✅ 重叠钉住成立；❌ CRLF 半区无护栏（F-1）

- **红态推演（逐测试、对照旧单遍实现）**：test 1 旧实现下 `mirror.bin` 取磁盘旧态 → 断言 new-version 必败（红）；test 2 旧实现下 changed 仅 report.txt（stale mirror 与磁盘相等不入 changed）→ 写后 post-check re-plan 报 mirror drift → 回滚 → `state != PASS`（红）——与 M-1 回滚震荡机理逐环对应；test 3 在旧实现下因 fixture 含重叠对同样红，但其**负例断言本体**（`copy.bin == 原始字节`，含非 UTF-8 透传）是新行为的正向钉住。三测试真实钉住重叠场景，无假绿构造。
- **端到端收敛**：test 2 断言 write PASS + 双文件落盘新版本 + check_projections PASS + 二次 write `written==0`——完整覆盖"写收敛替代回滚震荡"的验收语义，含幂等不变点（replacement 输出仍匹配自身 pattern → re-plan 稳定不动点）。
- **缺口**：三测试 fixture 全 LF（L39/72/73 均 `\n`）→ 若未来回归回 `read_text`，三测试仍全绿，而整文件 LF 化静默复活。CRLF 半区仅由开发者一次性 stash 实验看护，无持久护栏。

### 5. AI 专项 5 项 — 全部完成，零命中

| # | 检查 | 结论 |
|---|------|------|
| 1 | mock 残留 | 无——测试全部真实 tempfile 文件系统操作，无 unittest.mock；`write_projections` 的 `replace` 注入参数未被测试篡改 |
| 2 | 硬编码返回值 | 无——diff 内 content 均由真实读取/转换导出 |
| 3 | 幻觉 API | 无——`read_bytes/decode/re.subn/json.loads/_safe_repo_path/_json_pointer_set` 均为在册真实 API；版本字符串与 triage/target_version（0.87.0）一致 |
| 4 | 未实现 TODO | 无——注释为机理说明非 TODO |
| 5 | 过度实现 | 无——两遍结构为 triage 方案 B（"resolve→transform→copy"）的最小实现，`resolved` dict 单一职责，无投机抽象 |

---

## 二、五维度结论

| 维度 | 结论 | 依据 |
|------|------|------|
| 正确性 | ✅ 通过 | 复核点 1/2：两遍等价 + 命中/fallback 语义 + 顺序无关 + 冲突/编码 fail-closed；边界见 F-2/F-3 |
| 安全性 | ✅ 通过 | 所有 Pass 1 读经 `_safe_repo_path`（symlink 穿越拒绝 + 路径逃逸拒绝）覆盖；无新增注入/敏感数据面；UnicodeDecodeError 被 BLOCKED 捕获面兜住 |
| 可维护性 | ✅ 通过（含 F-5 观察） | FIX-366 注释阐明两遍动机；Pass 1/Pass 2 职责分离消除原单遍耦合；函数长度增长约 30 行（预先存在偏长，非本次引入） |
| 性能 | ✅ 通过 | 磁盘读次数不增（transformed 目标 1 次、非重叠 byte_copy 1 次）；额外开销仅 O(n) dict 与 skip 判断 |
| 测试覆盖 | ⚠️ 有缺口（F-1 P1） | 重叠红/绿、端到端收敛、幂等、非重叠负例在位；CRLF 保真路径无自动化测试 |

## 三、发现清单

| ID | 级别 | 位置 | 描述 | 建议 |
|----|------|------|------|------|
| F-1 | **P1 关键** | `skills/software-project-governance/infra/tests/test_release_projection.py:36-73` | CRLF 保真半区（本 diff 一半修复理由）零自动化护栏：fixture 全 LF，回归回 `read_text` 时三测试仍全绿，整文件 LF 化静默复活（数据保真回归不可测出） | 补 CRLF fixture 变体：report.txt 以 `b"version=0.86.0\r\n"` 落盘，断言 (a) transformed 计划内容保 `\r\n`；(b) byte_copy 镜像与目标内容字节全等。可本轮随 R0 返工补齐，或按 P1 遗留计划入账（附关闭期限），由 Coordinator 按 P1 政策裁决 |
| F-2 | **P2 建议** | `skills/software-project-governance/infra/release/projection.py:238` | 链式 byte_copy（source = 另一 byte_copy 的 target）仍读磁盘旧态——`resolved` 只收 in-memory 投影。生产 registry 无此类链（核实：全部 byte_copy source 为 canonical 路径，target 全在 `project/e2e-test-project/` 下，两集合不相交），当前零暴露；未来 registry 出现链式镜像则震荡机理原样复活（P-v1 P5 泛化性边界） | 二选一：resolved 做闭包迭代至不动点（byte_copy target 亦入 resolved）；或最小成本——在 L197 注释披露该边界为已知不支持面并留票 |
| F-3 | P3 讨论 | `projection.py:197-238` | Windows 大小写不一致引用（source/target 字符串大小写不同指同一文件）→ resolved 键 miss → 回落磁盘旧态。现网 config 全部大小写精确一致，纯理论边界 | 知悉即可；如 F-2 采注释方案可并列披露 |
| F-4 | P3 讨论 | `test_release_projection.py:106-130` | test 3 负例断言与重叠 fixture 耦合（旧实现下该测试亦红，红态非由负例独立触发）；test 1 已独立隔离重叠钉住，可接受 | 不要求修改；知识分享记录 |
| F-5 | P3 讨论 | `projection.py:117-246` | `build_projection_plan` 现 ~130 行，超 50 行拆分指引（预先存在，本次 +~30） | 后续重构票候选，不阻塞 |

## 四、硬门槛裁决

| 门槛 | 阈值 | 实测 | 裁决 |
|------|------|------|------|
| P0 阻塞数 | = 0 | 0 | ✅ |
| 5 维度全覆盖 | 100% | 5/5 有结论（§二） | ✅ |
| 每条发现有级别 | 100% | F-1~F-5 均带 P0-P3 | ✅ |
| 设计一致性 | 已完成 | triage FIX-366.json 方案 B「两遍 plan：resolve→transform→copy」与实现一致；files 面与 triage `files` 精确吻合（projection.py + 新测试），无范围蔓延 | ✅ |
| AI 专项 5 项 | 全部完成 | §一.5，零命中 | ✅ |

## 五、证据与验证基础（事实依据红线声明）

- **本席独立核实（只读）**：diff 全文逐行比对、修改后 projection.py 全文（L1-537）、测试文件全文、生产 version-projections.json 暴露面核实、triage JSON；红/绿推演为基于测试逻辑对旧实现的逐步演绎。
- **Developer 上报、本席未独立复跑（无 Bash 权限，如实标注）**：红态 3 failed（stash 隔离）→ 绿态 3 passed；指定回归 50+6、相邻 92+29、check_projections(ROOT)=PASS 零漂移、manifest/cross-refs PASS、stash 隔离 CRLF 连带复验。上述上报与代码读审结论逻辑一致，无矛盾。
- 「绕开手法可撤」声明核实：diff 无 skip/mock/放宽/schema 变更，测试为真实行为断言 ✅。

## 六、结论

**APPROVED_WITH_NOTES**（unresolved_blockers=0）：P0=0，硬门槛全过；F-1（P1）建议本轮补 CRLF 回归测试或按 P1 遗留计划入账，F-2（P2）建议以注释披露或闭包迭代收口，均不构成阻塞。复审协议提示：若 Coordinator 令 Developer 补 F-1/F-2 后复审，复审轮 MUST 逐条比对本清单并声明 R1 引用（code-reviewer.md 复审四条）。

---

# R1 复审（复审轮 · 引用 R0）

| 项 | 值 |
|---|---|
| 轮次 | R1（引用 R0：本文档 §三 发现清单 F-1~F-5） |
| 复审对象 | `tests/test_release_projection.py`（新增 L133-156 CRLF 测试，套件 3→4）· `release/projection.py` L238-240（F-2 披露注释，无行为变更） |
| **R1 结论** | **APPROVED**（unresolved_blockers=0；P0=0、未解决 P1=0） |

## R0 findings 逐条比对

| R0 ID | 级别 | 比对结果 | 依据 |
|-------|------|---------|------|
| F-1 | P1 | ✅ **已修复** | `test_crlf_transformed_content_stays_byte_faithful`（L133-156）：fixture 以 CRLF 字节落盘（`# report\r\nversion=0.86.0\r\ntail\r\n`）；断言① plan 内容 == `new_crlf`（transformed 保 `\r\n`）、断言② `mirror.bin` 计划内容 == 同一 CRLF 字节（镜像与 resolved 字节全等）。红态推演核实：回归回 `read_text` 时 universal-newlines 剥 `\r` → 两断言同时变红（LF 化内容 ≠ CRLF 期望）——与 Developer stash 上报（1 failed）一致；绿态推演：`read_bytes().decode` 保 `\r\n`，pattern 不触碰 `\r`，两断言按修复代码必绿。与 R0 §三 F-1 建议的 (a)+(b) 双断言逐点对应，无 mock/skip。护栏缺口闭合 |
| F-2 | P2 | ✅ **已披露（按 R0 给出的最小成本方案）** | projection.py L238-240 注释：「review-FIX-366 F-2: chain byte_copy (source = another byte_copy target) reads disk as-is by design — no current registry chain; resolved only carries in-memory projection targets.」表述与代码事实一致；L241 fallback 逻辑与 R0 逐字相同，零行为变更 |
| F-3 | P3 | ⏸ **维持遗留（未修复，符合预期）** | L241 仍为大小写敏感键命中回落磁盘——讨论级理论边界，R0 即裁定不要求修改 |
| F-4 | P3 | ⏸ **维持遗留（未修复，符合预期）** | test 3 未改动（R0 裁定：test 1 已隔离重叠钉住，可接受） |
| F-5 | P3 | ⏸ **维持遗留（未修复，符合预期）** | 函数长度基本不变（+3 行注释）——预先存在偏长，重构票候选 |

## 新引入检查

R0→R1 增量仅一处测试方法 + 三行注释：注释内容与代码事实核对无误；新测试复用共享 fixture 后覆写 report/mirror 为 CRLF（config/manifest 契约不变，ids 仍 text+mirror），构造合法；无新问题引入。非发现级观察：L131-132 类内双空行为无害格式噪音，不计 finding。

## R1 硬门槛裁决

P0=0 ✅ · 5 维度维持 R0 结论（测试覆盖维度缺口已由 F-1 修复闭合→✅）· findings 全带级 ✅ · 设计一致（files 面未超出 triage 声明）✅ · AI 专项 5 项复查零命中 ✅。

## R1 结论

**APPROVED**（unresolved_blockers=0）：F-1 已修复、F-2 已披露、F-3~F-5 按 R0 裁定维持 P3 遗留（讨论级，不阻塞）。FIX-366 代码审查链通过终态。Developer 上报的回归数据（指定三套件 54 passed + 6 subtests、stash 红态 1 failed）为 Developer 证据，本席只读未复跑，与代码读审推演一致。
