# REVIEW-FIX-395-CODE-R1 — 后置代码复审报告（R0 P0-1 修复验证）

> **Round**: R1 · **前轮引用**: `docs/reviews/review-FIX-395-CODE-R0.md`（NEEDS_CHANGE，P0=1/P1=1/P3=3）
> **Task**: FIX-395（P1 · 0.89.0 串行链第三位） · **复审对象**: staged diff `git diff --cached`（+474/−3）：`verify_workflow.py`（+42/−3，与 R0 审查版逐 hunk 恒等）+ `test_fix395_hot_fact_source_writer_terminal.py`（410→432 行，R1 derive 改造）
> **复审基线**: HEAD = 65c8e4b · 仓库根 = D:\AI\agent\claude\coding\project_management_workflow · 复审日期 = 2026-09-26
> **复审性质**: 同一 Reviewer（M7.4/T1 必达）；本质 = 验证修复

## 结论

**APPROVED_WITH_NOTES**（P0 = 0；P1 = 0；P3 = 1 新增注记 + R0 P3×3 处置状态见 §四）

**unresolved_blockers = 0**

R0 唯一阻塞项 P0-1 已按选型 (b) derive 修复且经独立亲验消除；修复面零语义漂移、零新引入。

---

## 一、R0 findings 逐条比对（复审本质：验证修复）

| R0 编号 | 级别 | 内容 | R1 状态 | 依据 |
|---|---|---|---|---|
| P0-1 | **P0 阻塞** | 新测试文件 23 处字面 `0.88.0` 未豁免/未 derive，打破 `test_static_version_pins::RealTreeContractTests::test_real_tree_scan_is_warn_only_and_clean` | **✅ 已修复**（选型 b：derive） | §二 亲验四重证据 |
| P1-1 | P1 | 申报「其余面恒等」不实 + 定向口径漏 static-pin 契约 | **Coordinator 处置中**（超出 Reviewer 范围，注记）：R1 修复申报已如实改口——「FAIL 30=30 恒等」按「仅 stash A 态新文件」口径成立（本复审独立 A/B 双口径均验证，见 §三）；evidence-log 勘正留 Coordinator 落字 |
| P3-1 | P3 | 28c REQ 行 :2239/2241 legacy 读潜在耦合 | 未变（设计外延，留档候选票）——本次 diff 未触碰 :2239/2241（hunk 恒等核验） |
| P3-2 | P3 | FIX-069 面 legacy 读（:1691/1873/1883/1884） | 同上，范围外未动 ✓ |
| P3-3 | P3 | 夹具 REL-088 trailing-group prose 历史形态 | 保留（R0 已判可不改）；docstring :41-48 已同步披露 R1 derive 事实 |

## 二、P0-1 修复核验（亲验四重证据）

### 2.1 实现正确性（逐行 diff + 依据核读）

- `test` 文件 :64 `import resolve_entry`；:72 `_ACTIVE_VERSION = resolve_entry.read_active_version() or "0.0.0"`；:75-79 `_next_minor_version`（minor+1 保 major/patch）；:82 `_NEXT_VERSION`。
- 回退语义核验：`resolve_entry.read_active_version`（resolve_entry.py:82-108）——SKILL.md 缺失/无 frontmatter version 返回 **None** → `or "0.0.0"` 兜底成立；返回值来自 YAML frontmatter 权威锚（:100-104 限缩 frontmatter 块）——与 census「Source version」同源，derive 权威正确。
- 23 处原字面位（R0 报告 §六 P0-1 所列行）逐一改为插值：:110/:122（`plan_version=None` → `or _ACTIVE_VERSION`）、:123-130（dependency_line/overview_tail/project_stage/overview_stage/active_items_intro）、:190（ROADMAP row + tag）、:196-204（六任务行含 swept row `{_ACTIVE_VERSION}→{_NEXT_VERSION}`）、:244-246/:415-417（`_hot_task_ids_for_version(content, _ACTIVE_VERSION)`）、:263-264/:337/:350/:360/:376-378（夹具行与断言 f-string）。**零字面 active 版本残留于代码常量**（probe 实证）。
- 「docstring 不动——AST 跳过」声明核验：`checks/version.py scan_static_version_pins`（:368-418）AST 解析 → `doc_lines` 跳过 docstring（:398-401）、`string_inner` 跳过多行串内部行（:360-364）、注释行跳过（:406）；仅命中含 **active** 版本三段 token 的行（:408-409 `_SEMVER_TOKEN_RE`）。历史字面（0.37.0/0.38.0/0.87.0）与两段形态（0.88/0.89）天然不命中 ✓。豁免台账零新增行（选型 b 无 ratchet 面）✓。
- 语义零变化：8 测试结构/断言/形态与 R0 同构（逐行比对）；当前活体 active=0.88.0 → 派生值≡R0 字面值 → 绿色运行即语义恒等证明。

### 2.2 亲跑证据

| # | 项 | 命令/方法 | 结果 |
|---|---|---|---|
| 1 | 契约测试文件全量 | `pytest test_static_version_pins.py -q` | **25 passed, EXIT=0** ✓（R0 失败节点 `test_real_tree_scan_is_warn_only_and_clean` 转绿） |
| 2 | 新套件 | `pytest test_fix395_hot_fact_source_writer_terminal.py -q` | **8 passed** ✓ |
| 3 | 既有 28c 族 + 同族（fix390/393/394 + snapshot_freshness） | `pytest …` | **117 passed + 23 subtests** ✓（S_old 零回归保持） |
| 4 | 活体 check-hot-fact-source | `verify_workflow.py check-hot-fact-source` | **PASSED — 0 issues** ✓（20→0 保持） |
| 5 | census strict A/B（stash 协议第三次，备份+SHA256 恢复校验 vw=True/t=True，staged 恒 +474/−3） | `check-governance --level strict` post/stash/pre | **WARN 27=27 恒等 ✓；static-version-pin 0=0 ✓**；FAIL 51→30，差集恰=hot 簇（20 裸行 + 汇总行 + 明细块），**零其他 FAIL 变化** ✓；簿记行（files 1050→1051、Candidates 1020→1021、K-8 75→76 test files、Inventory hash）为新增文件固有。申报「FAIL 30=30」按其自述口径（仅 stash A 态新文件、双侧 fix 在树）与 post=30 实测吻合——两口径合并即完整闭环 |
| 6 | **自适配实证**（申报「bump 后夹具自适配」的活体证明） | stub `read_active_version→"9.9.0"` 全新导入 probe | `_ACTIVE_VERSION=9.9.0/_NEXT_VERSION=9.10.0`；swept row 目标列/「9.9.0→9.10.0」叙事/「0.87.0→9.9.0」REL-087 叙事/依赖链/阶段行/roadmap tag **全派生** ✓；代码常量零 0.88.0 残留 ✓ |
| 7 | 7 个既有失败节点复跑（R0 归因集稳定性） | `pytest <7 nodes>` | 与 R0/HEAD 归因一致（§四注 2） |

### 2.3 无新引入论证

- `verify_workflow.py` staged diff 与 R0 审查版**逐 hunk 恒等**（@@ -1660,6/-1924,12/-1948,6/-1965,7 四 hunk 头逐一核对）→ 产品代码面 = R0 已审态，零新风险面。
- 测试文件为**叶模块**（`git grep -l "test_fix395"` 无其他引用者）→ 改动只可能影响 static-pin 扫描面（已转绿）与本文件自身（8/8 绿）。
- census post 面（K-8 coverage claims 76 test files PASS、untracked WARN、cross-refs PASS 等）在 A/B 中与 pre 恒等（簿记除外）→ 全树扫描面无新引入。

## 三、申报口径核对（如实记录）

| 申报 | 实测 | 裁决 |
|---|---|---|
| 「test_static_version_pins 25 passed EXIT=0」 | 25 passed, exit=0 | ✓ 属实 |
| 「census WARN 27=27 恒等」 | 27=27 | ✓ 属实 |
| 「static-pin WARN 0（post 在盘 0 命中）」 | 0=0（pre 无文件/post 0 命中）；pre 侧 0 命中归因于对照组无本文件——申报已自披露 | ✓ 属实（口径如其所注） |
| 「FAIL 30=30 恒等」 | 其口径（仅 stash A 文件）下成立；本复审独立全 stash 口径为 51→30（差=恰 hot 簇，即 R0 已证 −20+1） | ✓ 两口径合并自洽 |
| 「新套件 8/8」 | 8 passed | ✓ |
| 「全树未豁免命中 23→0」 | 契约测试转绿 + static-pin 0=0 | ✓ |
| 「测试语义零变化」 | 派生值≡R0 字面（活体 active 未变）+ 8/8 绿 + 结构同构 | ✓ |
| staged +474/−3 | +474/−3（vw +42/−3 恒等 + test 432） | ✓ |

## 四、注记（不阻塞）

1. **P3-4（新，P3 讨论级）**：`_next_minor_version`（test :75-79）假定三段 `X.Y.Z`（`split(".")` 三元解包），而 `_FRONTMATTER_VERSION_RE`（resolve_entry.py:53-56）允许 2~4 段；若未来 frontmatter 版本偏离三段约定，模块导入期即 ValueError（响亮失败，非静默）。当前仓内版本约定恒三段、不可达；如需加固可在 derive 处收敛 `read_active_version` 输出形态。不阻塞。
2. 本次 A/B **pre 侧**多出 1 条 untracked WARN（`_r1_probe.py`）为复审 probe 恰在 pre 窗口在盘所致（本复审自造噪声，probe 已删）；不影响 WARN 27=27 主判定（untracked-file 块为 WARN 面 disclosure，两侧均非 static-pin 族）。如实留痕。
3. R0 P1-1（申报勘正）与 P3-1/2（同族候选票）在 Coordinator 处置轨道，非本复审范围；R1 修复申报已体现口径改口。

## 五、硬门槛裁决（R1）

| 门槛 | 阈值 | 实测 | 裁决 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | **0** | ✓ |
| R0 findings 逐条比对 | 100% | §一（P0-1 已修复/P1-1 处置中注记/P3×3 未变） | ✓ |
| 前轮报告引用 + round 声明 | 必须 | 本报告头部 | ✓ |
| 5 维度 + AI 五项（增量面） | 完成 | 修复仅触测试叶模块：正确性（§2.1）/安全性（无新面）/可维护性（derive 正确形态）/性能（导入期一次计算）/测试覆盖（契约 25P+8/8+117P）逐项结论于 §二；AI 五项增量面无 mock/硬编码/幻觉 API/TODO/过度实现（derive 即 R0 建议形态） | ✓ |

**终局：APPROVED_WITH_NOTES（unresolved_blockers=0）** — 复审链达通过终态，Check 30 可消费；遗留 = R0 P1-1 evidence 勘正与 P3-1/2 候选票（Coordinator 轨道，带计划遗留）。

---

## 附：复审操作留痕

- 全程未改产品代码/staged/.governance；stash 协议第三次执行，恢复后 SHA256 对照预备份逐一相同（vw=True/t=True），staged 恒 +474/−3，stash list 空。
- 自适配 probe（`_r1_probe.py`）用后即删（Test-Path False 实证）；其存在曾使 A/B pre 侧 untracked WARN +1（注记 2 如实披露）。
- census 原始输出：`%TEMP%\r1_census_pre.txt` / `%TEMP%\r1_census_post.txt`；R1 备份目录 `%TEMP%\fix395r1-backup` 已清理。
