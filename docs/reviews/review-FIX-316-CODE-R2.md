# FIX-316 代码审查报告（Code Review R2 — 复审）

- **任务**：FIX-316（0.81.0 切片 V5+V6+V7）
- **Round**：**R2（复审）**；**前轮引用**：`REVIEW-FIX-316-R1` = NEEDS_CHANGE / `unresolved_blockers=1`（N-1），报告 `docs/reviews/review-FIX-316-CODE-R1.md`（已完整重读作为逐条比对基线）
- **审查对象**：工作树 7 文件（HEAD `85fb309`；`+2562/−147`）：`launch.py`（1833 行）·`lib/index.js`·`cordis.patch.yml`·`adapter-manifest.json`·`test_dsh_compat.py`（3199 行）·`test_dsh_adapter.py`·`dsh_fixtures.py`
- **Reviewer**：Code Reviewer Agent（11 项独立变异 + 4 入口 profile-擦除对照 + `marker_version` 6 例矩阵 + 契约缺陷行为表征 + 披露上屏实测 + 四路 parity + 三套件 + 4 门禁 + `check-governance` A/B；构造/变异一律 `%TEMP%` 副本 + 环境重定向；**真实环境零写**）
- **结论**：**APPROVED_WITH_NOTES / `unresolved_blockers=0`**（P0 = 0；无 P1 及以上未决项；硬门槛 5/5 通过）

## 1. 逐条比对（R1 的 N-1~N-8：8/8 已修复）

| R1 | 级别 | 判定 | 独立证据 | 仍存问题 |
|---|---|---|---|---|
| **N-1** | P1 阻塞 | **已修复** | 子进程 env **全清 4 个 profile 变量** + `DSH_HOME` 一次性 `%TEMP%` 目录，同脚本跑两树：**HEAD `install_preset` rc 0 写 4 文件 / `main([--install])` rc 0**；**R2 四入口**（`install_preset`/`uninstall_preset`/`main([--install])`/`main([--smoke])`）**全 rc 2 + `raised=None` + `traceback=False` + 可行动消息 + `dsh_home_written: []`（零写入）**。并实测出 **HEAD 的 `main([--smoke])` 本就抛栈** ⇒ Developer 所称「第二实例」是**既有缺陷**，R2 一并闭环，**非扩面** | 无 |
| **N-2** | P2 | **已修复** | 变异 M3（删调用方保险丝）→ 仅 `test_caller_fuse_removes_a_staging_tree_the_writer_left_behind` 转红，`test_write_failure_leaves_no_staging_directory` **仍绿**（由 writer 内部清理满足）⇒ **独立证实其「首次实现是假绿」的自查** | 无 |
| **N-3** | P3 | **已修复** | `list_style` 改为入口契约自检；M4（`if False:`）被**具名**用例 `test_unimplemented_list_style_is_a_contract_defect` 抓住 ⇒ 不可静默移除 | 行为面新发现 **N-9（P2）** |
| **N-4** | P3 | **已修复** | docstring 与实现（及审查方 R1 判定）**逐字一致** | 无 |
| **N-5** | P3 | **已修复** | 注释写明「judged **against the baseline**」及理由，与 R1 独立判定完全一致 | 无 |
| **N-6** | P3 | **已修复** | (a) `encodes-as-ascii: True`、`textwrap` 已删、有 `decode("ascii")` 机检；(b) 不可解 `skill-root.txt` **确实上屏**（issue 含 `unreadable` + offset + 回落说明），M6 变异有网 | **N-10（P3）** |
| **N-7** | P3 登记 | **已闭环** | `EVD-1025` 逐项登记 5 项转出 + F-12/F-15 归属；`plan-tracker:96` 新增 **FIX-324** ⇒ R1 指出的「派发正文不构成持久记录」缺口闭合 | 无 |
| **N-8** | P3 | **主判据已修复 + 1 处残余** | 6 例矩阵：**absent → `"0"`（允许）**；**non-utf8 / invalid-json / no-version / empty-version → 四例 `marker_version()` 与 `package_version()` 均 RAISE，且 `write_rendered_preset(version=None)` 返回 False（零写）**；`require_package_version` 已删且被测试断言不存在（防「两套读法」回归）；M5 被抓 | **N-11（P3）** |

**统计**：**已修复 8/8**；新增非阻塞 4 条（N-9 P2 / N-10~N-12 P3）；**新引入的阻塞项 = 0**。

## 2. 本轮新发现（均非阻塞）

| # | 级别 | 位置 | 事实（已独立实测） | 影响 | 建议 |
|---|---|---|---|---|---|
| **N-9** | P2 | `launch.py:1151-1155` → `verify_preset_loading:1401`（无 try）→ `smoke_preset` → `main:1808` | 契约 `list_style` 改为 `"flow"` 后：`_shape_violations`/`verify_preset_loading` **抛 `ContractMalformed`**，**`CLI --smoke` → rc 1 且 stderr 带 `Traceback`**；`--install` 不受影响（有 `except Exception`）。R1 该分支是静默 no-op，R2 改为「抛」——方向 fail-closed 正确，但形态是栈；与 `verify_preset_loading` docstring 自述「never throw」及设计 §2.5.1「可行动错误 + 非 0」不一致 | 契约被改成未实现风格时 `--smoke`（28u 上游）以栈失败；属产品缺陷面，无假通过/无写 | 3 行内结构化：`verify_preset_loading` 捕获 `ContractMalformed → issues.append + verdict=FAIL`；`smoke_preset` 顶层捕获 → `[SMOKE] [FAIL]`。**非阻塞**（方向正确 + 消息含字段） |
| **N-10** | P3 | `dsh_fixtures.py:242` 注释 | 注释指向的测试名 `test_witness_fixture_source_is_pure_ascii` **全仓不存在**；性质实际由 `test_dsh_compat.py:2292` 的裸 `decode("ascii")` 断言 | 注释-事实不符（G-08 类），恰出现在修该类同一 hunk | 改注释指向真实用例（含行号） |
| **N-11** | P3 | `launch.py:436`（`if not (ROOT/"package.json").is_file(): return "0"`） | **本轮「旁路」判定的唯一确证残余**：`Path.is_file()` 吞 `OSError` ⇒「**存在但非普通文件**」（目录）被判为「整体缺失」→ 静默落 `"0"`；实测 `write_rendered_preset(version=None)` 返回 True。**真实 install 路径不可达**（走严格 `package_version()`，实测缺 package.json ⇒ rc 1 + 零写），仅 `smoke_preset` 的隔离 home 可达 | 被篡改的 checkout 下 JS 可能每 boot 重建预设 | 1 行硬化：以读写结果判缺失（捕获 `FileNotFoundError` 且 `lexists()` 为假才回 `"0"`，其余 re-raise）；docstring 注明「缺 package.json ⇒ 拒绝（较 HEAD 更严）」 |
| **N-12** | P3 | `test_dsh_contract.py` | 对 `list_style` **0 断言** ⇒ 契约字段的单点守卫落在消费方而非契约面 | 契约面缺自校验 | 补一行 `assertEqual(shape["list_style"], "block-sequence")` |

**未验证项（如实标注）**：`marker_version` 的**断链符号链接**子例未能构造（`os.symlink` 在本环境抛 `OSError`，需特权/开发者模式）⇒ 该子例判「未验证」，以目录形态作代表。

## 3. 硬门槛复核

| 门槛 | 阈值 | 实测 | 裁决 |
|---|---|---|---|
| P0 | = 0 | **0** | ✅ |
| 5 维度 | 100% | 正确性（四入口 fail-closed + 零写；清理链两端被钉住；自检不可静默移除；四类内容不可读全抛）／安全性（不可解析 profile ⇒ 拒；可解析下真实 home 全拒 + 隔离路径真写入成功；11 变异中守卫删除 → 9 红且真实 profile 未被触碰）／可维护性（三处注释-实现对齐；`require_package_version` 合并为单一严格读取器）／性能（+1 次 `is_file()` + 严格读，<1 ms）／测试覆盖（113 → **120**，+7 条；11/11 变异全抓） | ✅ |
| 发现分级 | 100% | N-1~N-8 逐条 + 4 条新发现全带级别 | ✅ |
| 设计一致性 | 已完成 | §6.1 V5/V6/V7 逐条；D-54 与 §3.3 第 11 行一致；G10-b 四入口闭环 | ✅ |
| AI 专项 5 项 | 全部完成 | mock 均为环境/接缝隔离；断言取自契约/真实输入；`os.symlink` 权限不足已如实标注；TODO 0；无过度实现 | ✅ |

**独立复现要点**：① 四入口 × profile 全清 → 成立（含 HEAD 对照，回归定性成立）；② **未引入新失败面**：可解析 profile 矩阵（unset/blank/bare-home/real-dsh/subdir → 全 REFUSE；isolated → rc 0 且**真的写出 4 文件预设**）⇒ 未误拒合法路径；③ N-2「假绿」自查由变异独立证实；④ **N-8 旁路判定**：内容层不可读**必抛**（4/4 例），残余仅 N-11 一态；⑤ N-6(b) 披露真的走 issue 通道且 M6 有网；⑥ N-3 自检不可静默移除；⑦ 硬基线全成立。
**Coordinator 三项偏离的独立复核**：① N-8 形态 **接受**（消除「两套读法」旁路，主判据达成）；② N-1 smoke 第二实例 **接受**（同族 + HEAD 本就抛栈）；③ N-3 选第二项 **接受**（双面判据需新解析器 = 扩面；所选形态可测且不静默，代价即 N-9）。

**硬基线（R2 自跑）**：三套件 **120 / 120 / 47 OK**；**四路渲染 sha256 全等** `00e0d330…3723`；契约 sha256 **未变**；28u exit 0 + `real-home writes: 0`；28v `1/23/18/5` + exit 0；`check-governance --summary-only --level strict` **BASE(HEAD) 48 / WT 48 FAIL，`Compare-Object` 为空**；manifest-consistency（canonical 681 的 +1 与 R1 报告落盘同步，非 diff 引起）/ projection-sync / cleanup / agent-adapters 全通过。

## 4. 事故专项复评（R2 增量）

R1 的 N-1 是本片唯一一次「修复引入的新缺陷」，其成因（守卫成为**首个**触碰 `Path.home()` 的调用点）已被**双向关闭**：守卫内 try/except + `smoke_preset` 前置 try/except；且以「可解析 profile 矩阵」证明**未把合法路径一起拒掉**。**零真实 home 写入**第三轮再次成立（`<home>\.agent-presets` exists=False、真实预设 sha/大小/mtime 三轮不变、守卫删除变异下真实 profile oracle 三次采样一致、噪声底 = 0）⇒ 红绿流程自身不再构成写入 hazard。

**一处自查纠错（审查方如实披露）**：末轮命令中误删本 shell 的 `USERPROFILE`，导致该次真实 home 读数落到 `D:\.dsh\…`（不存在）而作废；已在后续独立命令中按正确 env 重测并以此为准（结论：真实 home 未变）。

## 5. 结论与下一步

**APPROVED_WITH_NOTES / `unresolved_blockers=0`** —— FIX-316 可进入提交/闭环流程。剩余 **N-9（P2）+ N-10/N-11/N-12（P3）** 按 **FIX-324** 批登记（其中 **N-11 是本轮「旁路」判定中唯一确证的窄残余**，真实 install 路径不可达）。

**审查方一句话**：R1 唯一阻塞项 N-1（含 Developer 自查发现的 smoke 第二实例）**四入口实测闭环**（HEAD 对照 rc 0 / R2 rc 2 + 无栈 + 零写），N-2~N-8 逐条实证修复（11/11 变异全抓、N-2 的「假绿」自查经独立证实、N-8 的「内容不可读必抛」6 例矩阵达成），三项偏离独立复核均可接受。

## 6. 真实环境命令上报表（R4）

10 类命令全部只读或落 `%TEMP%`：真实 profile 仅只读采样（审前/审后各一次）；4 入口 profile-擦除对照用**子进程 env 全清** + 一次性 `DSH_HOME`；`main(["--install"])`/`main(["--smoke"])` 仅在 `%TEMP%` 副本下运行；11 项变异在 `%TEMP%\MUT` 副本（守卫变异**故意不加**外部重定向以检验测试自身隔离）；所有 python 调用设 `PYTHONDONTWRITEBYTECODE=1`；`%TEMP%\fix316-r2`（394.6 MB）已清理（先确认无 reparse point）。**未触碰** Developer 的事故/恢复痕迹、`~/.dsh` 任何内容、仓库任何文件（`git status` 仅 7 个在制文件 + 2 份前轮报告；契约 sha 未变）。**真实 home 写操作 = 0 次。**

---

*报告结束（R2，APPROVED_WITH_NOTES / unresolved_blockers=0）。*
